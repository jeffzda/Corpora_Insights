#!/usr/bin/env python3
"""Phase 4b — TEST RUN on a single 500-record batch.

Two-pass architecture:
- Pass 1 (classification): each record → cluster_id from catalogue OR 'orphan'
- Pass 2 (orphan clustering): combinatorial pass on Pass-1 orphans → new
  cluster labels (locked into catalogue, will be used in subsequent batches)

Records are treated as fresh inputs. The seed-run produced ONLY catalogue
labels (no record assignments), so all 25,479 filter-input records are
fresh classification candidates here.
"""
import argparse
import json
import random
import re
import time
from pathlib import Path

import anthropic

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = Path(__file__).resolve().parent.parent / 'output'
INPUT = OUT_DIR / 'filter_input.jsonl'
CATALOGUE = OUT_DIR / 'cluster_catalogue.json'

OUT_ASSIGNMENTS = OUT_DIR / 'test_batch_assignments.json'
OUT_ORPHAN_CLUSTERS = OUT_DIR / 'test_batch_orphan_clusters.json'
OUT_RAW_PASS1 = OUT_DIR / 'test_batch_raw_pass1.txt'
OUT_RAW_PASS2 = OUT_DIR / 'test_batch_raw_pass2.txt'

CLASSIFY_PROMPT_HEADER = """You are classifying ARENA renewable-energy project records against an existing catalogue of failure-mode clusters.

For each record, decide: does its causal failure mechanism match one of the catalogue entries? If yes, return that cluster_id. If no clear match exists in the catalogue, return cluster_id="orphan".

CRITICAL: Do NOT force-fit. It is better to mark a record as 'orphan' than to assign it to a cluster that doesn't actually capture its mechanism. Orphans will be processed by a separate clustering pass that may create new clusters for them. Force-fitting damages the catalogue.

Match on MECHANISM, not on:
- Project name, technology vocabulary, equipment models
- Surface text similarity
- Topic similarity (just because both are about "voltage" doesn't mean same mechanism)

Two records share a cluster only if they describe the SAME causal pathway.

# CATALOGUE OF FAILURE-MODE CLUSTERS"""

CLASSIFY_PROMPT_FOOTER = """\
# OUTPUT FORMAT

Return JSON only:
{
  "assignments": [
    {"record_id": "ARENA-DLV-XXXX-NNNN", "cluster_id": "c042"},
    {"record_id": "ARENA-DLV-XXXX-NNNN", "cluster_id": "orphan"},
    ...
  ]
}

One assignment per input record, in input order. cluster_id must be either an existing catalogue id (e.g. "c042") or the literal string "orphan"."""

ORPHAN_CLUSTER_PROMPT = """You are extending the catalogue of FAILURE-MODE CLUSTERS for the ARENA renewable-energy project corpus.

The records below were rejected as 'orphans' by the classifier — they did not match any existing catalogue cluster's mechanism. Your job is to identify any NEW failure-mode clusters these orphans collectively support, and to return any genuinely singleton records as singletons.

CRITICAL: Cluster by MECHANISM, not by project / equipment / topic / domain vocabulary. Two records share a cluster only if they describe the SAME causal pathway, even with different surface vocabulary.

THRESHOLD RULE: A cluster must be supported by at least 3 records. Do NOT propose a cluster justified by 1 or 2 records — simply leave those records out of your output. Records you don't list will be treated as singletons by post-processing; you do not need to enumerate them. They may join an existing cluster or seed a new one in subsequent batches when more matching records arrive.

For each new cluster you identify, output:
- cluster_id: must NOT collide with existing catalogue ids; use a high range starting from c500
- canonical_name: 4-12 word descriptive name (locks forever)
- mechanism_signature: 1 sentence ("X causes Y because Z" OR "Y because Z")
- supporting_record_ids: list of 3+ record_ids from the orphan set that share this mechanism

DO NOT emit a singletons list. Records you do not place in any cluster are automatically treated as singletons by post-processing — listing them wastes output tokens.

Rules:
- It IS expected that many orphans will remain unclustered — that is the correct behaviour for genuinely unique mechanisms or patterns with only 1-2 examples in this batch.
- Avoid project-specific vocabulary in the canonical_name and signature.
- The catalogue is only for patterns with ≥3 evidence.

# OUTPUT FORMAT — STRICT

Return a single JSON object and NOTHING ELSE. Do not write any prose, explanation, numbered candidate lists, working notes, or per-record commentary before, during, or after the JSON. The very first character of your response must be `{` and the last character must be `}`. No markdown fences. No "Let me work through this..." preamble. Reason internally; emit only the result.

Schema:
{
  "clusters": [
    {
      "cluster_id": "c501",
      "canonical_name": "4-12 word descriptive name",
      "mechanism_signature": "1 sentence — 'X causes Y because Z' OR 'Y because Z'",
      "supporting_record_ids": ["ARENA-DLV-XXXX-NNNN", "ARENA-DLV-XXXX-NNNN", "ARENA-DLV-XXXX-NNNN"]
    }
  ]
}

No record_id may appear in more than one cluster. Any orphan record not placed in a cluster is implicitly a singleton — do not list it. Cluster supporting_record_ids must contain at least 3 ids drawn from the input orphan set.

# ORPHAN RECORDS"""


def stream_call(client, prompt, model='claude-sonnet-4-6', max_tokens=128_000,
                 raw_path=None, label='call'):
    """Stream with progress prints + incremental save. Returns the streamed text whether
       or not raw_path is set."""
    raw_f = open(raw_path, 'w', encoding='utf-8') if raw_path else None
    started = time.time()
    last_print = 0
    last_chars = 0
    text_chars = 0
    parts = []
    msg = None
    try:
        with client.messages.stream(
            model=model, max_tokens=max_tokens, temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for ev in stream.text_stream:
                if raw_f: raw_f.write(ev); raw_f.flush()
                parts.append(ev)
                text_chars += len(ev)
                now = time.time()
                if now - last_print >= 5:
                    rate = (text_chars - last_chars) / max(now - last_print, 1)
                    print(f"  [{label}] [{int(now - started)}s] {text_chars:,} chars  +{rate:.0f} c/s",
                          flush=True)
                    last_print = now; last_chars = text_chars
            msg = stream.get_final_message()
    finally:
        if raw_f: raw_f.close()
    text = ''.join(parts)
    return text, msg


def parse_json_tolerant(text):
    m = re.search(r'```json\s*(.*?)(?:```|$)', text, re.DOTALL)
    body = m.group(1).strip() if m else text.strip()
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        first = body.find('{'); last = body.rfind('}')
        if first >= 0:
            try: return json.loads(body[first:last+1])
            except: pass
        # Try to extract complete objects from a truncated array
        objects = []
        arr_start = body.find('[')
        if arr_start >= 0:
            depth = 0; obj_start = -1
            for i, ch in enumerate(body[arr_start+1:], start=arr_start+1):
                if ch == '{':
                    if depth == 0: obj_start = i
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0 and obj_start >= 0:
                        try: objects.append(json.loads(body[obj_start:i+1]))
                        except: pass
                        obj_start = -1
        return {'_recovered': objects}


def build_classify_prompt(catalogue, records):
    cat_lines = []
    for c in catalogue:
        cat_lines.append(f"\n[{c['cluster_id']}] {c['canonical_name']}")
        cat_lines.append(f"  mechanism: {c['mechanism_signature']}")
    rec_lines = []
    for r in records:
        rid = r['record_id']
        narr = (r.get('narrative') or '').strip()
        evi = (r.get('evidence') or '').strip()
        axes = []
        for ax in ['is_occurrence','is_mechanism','is_specification','is_lesson','is_recommendation']:
            if r.get(ax) == 'yes':
                axes.append(ax[3:])
        rec_lines.append(f"\n## {rid}  [axes: {','.join(axes)}; v: {r.get('valence','')}]")
        rec_lines.append(f"narrative: {narr}")
        if evi and evi != narr:
            rec_lines.append(f"evidence: {evi[:600]}")
    return CLASSIFY_PROMPT_HEADER + ''.join(cat_lines) + "\n\n# RECORDS TO CLASSIFY" + \
           ''.join(rec_lines) + "\n\n" + CLASSIFY_PROMPT_FOOTER


def build_orphan_prompt(orphan_records):
    lines = []
    for r in orphan_records:
        rid = r['record_id']
        narr = (r.get('narrative') or '').strip()
        evi = (r.get('evidence') or '').strip()
        axes = []
        for ax in ['is_occurrence','is_mechanism','is_specification','is_lesson','is_recommendation']:
            if r.get(ax) == 'yes':
                axes.append(ax[3:])
        lines.append(f"\n## {rid}  [axes: {','.join(axes)}; v: {r.get('valence','')}]")
        lines.append(f"narrative: {narr}")
        if evi and evi != narr:
            lines.append(f"evidence: {evi[:600]}")
    return ORPHAN_CLUSTER_PROMPT + ''.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n-records', type=int, default=200,
                    help='Batch size. Start small (200) when catalogue is thin; '
                         'ramp later when most records hit existing clusters.')
    ap.add_argument('--seed', type=int, default=11)
    ap.add_argument('--include-seed-singletons', action='store_true',
                    help='If set, drag seed singletons into the orphan pool. '
                         'Default: hold them out — they will be swept in a final '
                         'pass against the matured catalogue.')
    args = ap.parse_args()

    print(f"Loading catalogue + filter input...", flush=True)
    catalogue = json.load(open(CATALOGUE))['clusters']
    rows = [json.loads(l) for l in open(INPUT)]
    print(f"  catalogue: {len(catalogue)} clusters", flush=True)
    print(f"  records pool: {len(rows):,}", flush=True)

    rng = random.Random(args.seed)
    test_batch = rng.sample(rows, args.n_records)
    print(f"  test batch: {len(test_batch)} records (seed {args.seed})", flush=True)

    client = anthropic.Anthropic()

    # Pass 1 — classification
    print(f"\n=== PASS 1: classification ===", flush=True)
    p1_prompt = build_classify_prompt(catalogue, test_batch)
    print(f"  prompt size: {len(p1_prompt):,} chars (~{len(p1_prompt)//4:,} tok)", flush=True)
    p1_text, p1_msg = stream_call(client, p1_prompt, raw_path=OUT_RAW_PASS1, label='pass1')
    if p1_msg:
        print(f"  pass 1 tokens: {p1_msg.usage.input_tokens:,} in / {p1_msg.usage.output_tokens:,} out", flush=True)
        cost = p1_msg.usage.input_tokens/1e6*3 + p1_msg.usage.output_tokens/1e6*15
        print(f"  pass 1 cost: ${cost:.3f} sync, ${cost*0.5:.3f} batch", flush=True)

    p1_parsed = parse_json_tolerant(p1_text)
    assignments = p1_parsed.get('assignments') or p1_parsed.get('_recovered') or []
    if assignments and 'record_id' in assignments[0]:
        # Build assignment lookup
        rid_to_cluster = {a['record_id']: a['cluster_id'] for a in assignments}
        n_classified = sum(1 for v in rid_to_cluster.values() if v != 'orphan')
        n_orphan = sum(1 for v in rid_to_cluster.values() if v == 'orphan')
        print(f"  classified: {n_classified}  orphan: {n_orphan}  (total {len(rid_to_cluster)})", flush=True)
        # Cluster usage stats
        from collections import Counter
        cluster_usage = Counter(v for v in rid_to_cluster.values() if v != 'orphan')
        print(f"  unique clusters touched: {len(cluster_usage)} of {len(catalogue)}", flush=True)
        print(f"  top 5 most-assigned clusters in this batch:", flush=True)
        for cid, n in cluster_usage.most_common(5):
            cname = next((c['canonical_name'] for c in catalogue if c['cluster_id']==cid), '?')
            print(f"    [{cid}] {n}× — {cname[:65]}", flush=True)
    else:
        print(f"  PARSE ERROR — got: {str(p1_parsed)[:300]}", flush=True)
        return

    # Save pass 1 output
    OUT_ASSIGNMENTS.write_text(json.dumps({
        'meta': {'pass1_input_tok': p1_msg.usage.input_tokens, 'pass1_output_tok': p1_msg.usage.output_tokens,
                 'n_classified': n_classified, 'n_orphan': n_orphan},
        'assignments': assignments,
    }, indent=2, ensure_ascii=False))

    # Pass 2 — orphan clustering on this batch's orphans only.
    # Seed singletons are held out by default and swept at the end of corpus
    # against the matured catalogue. Pass --include-seed-singletons to inject
    # them (legacy behaviour).
    test_batch_orphans = [r for r in test_batch if rid_to_cluster.get(r['record_id']) == 'orphan']
    orphan_records = list(test_batch_orphans)
    print(f"  Test-batch orphans: {len(test_batch_orphans)}", flush=True)

    if args.include_seed_singletons:
        print(f"\n=== Loading seed singletons for orphan pool ===", flush=True)
        raw = open(OUT_DIR / 'seed_response_raw.txt').read()
        sm = re.search(r'```json\s*(.*?)```', raw, re.DOTALL)
        sbody = sm.group(1) if sm else raw
        try:
            sparsed = json.loads(sbody)
            seed_singleton_ids = set(sparsed.get('singletons', []))
        except:
            seed_singleton_ids = set()
        in_cluster = set()
        for c in catalogue:
            in_cluster.update(c.get('supporting_record_ids', []))
        seed_singleton_ids -= in_cluster
        test_rids = {r['record_id'] for r in test_batch}
        seed_singleton_ids -= test_rids
        rid_to_record_all = {r['record_id']: r for r in rows}
        seed_singleton_records = [rid_to_record_all[rid] for rid in seed_singleton_ids
                                    if rid in rid_to_record_all]
        orphan_records += seed_singleton_records
        print(f"  Seed singletons added: {len(seed_singleton_records)}", flush=True)
    else:
        print(f"  Seed singletons HELD OUT (default) — final sweep at end of corpus", flush=True)
    print(f"  Combined orphan pool: {len(orphan_records)}", flush=True)

    if not orphan_records:
        print(f"\n  No orphans; pass 2 skipped.", flush=True)
        return

    print(f"\n=== PASS 2: orphan clustering ({len(orphan_records)} records) ===", flush=True)
    p2_prompt = build_orphan_prompt(orphan_records)
    print(f"  prompt size: {len(p2_prompt):,} chars", flush=True)
    p2_text, p2_msg = stream_call(client, p2_prompt, raw_path=OUT_RAW_PASS2, label='pass2')
    if p2_msg:
        print(f"  pass 2 tokens: {p2_msg.usage.input_tokens:,} in / {p2_msg.usage.output_tokens:,} out", flush=True)
        cost = p2_msg.usage.input_tokens/1e6*3 + p2_msg.usage.output_tokens/1e6*15
        print(f"  pass 2 cost: ${cost:.3f} sync, ${cost*0.5:.3f} batch", flush=True)

    p2_parsed = parse_json_tolerant(p2_text)
    new_clusters = p2_parsed.get('clusters') or p2_parsed.get('_recovered') or []
    raw_singletons = p2_parsed.get('singletons') or []
    print(f"  new orphan clusters proposed: {len(new_clusters)}", flush=True)

    # Reconciliation: every orphan must end up either in a cluster or as a
    # singleton. Models routinely under-list singletons (just observed: 0
    # listed when 105 expected). So we compute singletons as the set
    # difference: orphan_pool - all_cluster_members.
    orphan_pool_ids = {r['record_id'] for r in orphan_records}
    in_cluster_ids = set()
    for c in new_clusters:
        in_cluster_ids.update(c.get('supporting_record_ids') or [])
    # Drop records from clusters that were never in the orphan pool
    # (model occasionally hallucinates ids); also drop dups.
    for c in new_clusters:
        sup = c.get('supporting_record_ids') or []
        c['supporting_record_ids'] = [r for r in sup if r in orphan_pool_ids]
    in_cluster_ids = {r for c in new_clusters for r in c.get('supporting_record_ids') or []}
    # Re-enforce ≥3 threshold post-pruning
    new_clusters = [c for c in new_clusters if len(c.get('supporting_record_ids') or []) >= 3]
    in_cluster_ids = {r for c in new_clusters for r in c.get('supporting_record_ids') or []}
    reconciled_singletons = sorted(orphan_pool_ids - in_cluster_ids)
    n_listed = len(set(raw_singletons) & orphan_pool_ids)
    n_recon = len(reconciled_singletons)
    print(f"  singletons listed by model: {n_listed}; reconciled total: {n_recon}", flush=True)

    OUT_ORPHAN_CLUSTERS.write_text(json.dumps({
        'meta': {'n_orphans': len(orphan_records), 'pass2_input_tok': p2_msg.usage.input_tokens,
                 'pass2_output_tok': p2_msg.usage.output_tokens,
                 'n_clusters': len(new_clusters), 'n_singletons_reconciled': n_recon,
                 'n_singletons_listed_raw': n_listed},
        'clusters': new_clusters,
        'singletons': reconciled_singletons,
    }, indent=2, ensure_ascii=False))

    print(f"\n=== SAMPLE OF PASS 1 ASSIGNMENTS ===", flush=True)
    # Show a sample of classified records (mixed clusters)
    print(f"\n5 random non-orphan assignments:")
    classified_sample = [a for a in assignments if a['cluster_id'] != 'orphan']
    rng.shuffle(classified_sample)
    rid_to_record = {r['record_id']: r for r in test_batch}
    for a in classified_sample[:5]:
        r = rid_to_record[a['record_id']]
        cname = next((c['canonical_name'] for c in catalogue if c['cluster_id']==a['cluster_id']), '?')
        print(f"\n  {a['record_id']} → {a['cluster_id']} ({cname[:55]})")
        print(f"    narrative: {(r['narrative'] or '')[:140]}")

    print(f"\n=== SAMPLE OF NEW ORPHAN CLUSTERS ===", flush=True)
    for c in new_clusters[:8]:
        print(f"\n  [{c.get('cluster_id','?')}] {c.get('canonical_name','')}")
        print(f"    {c.get('mechanism_signature','')}")


if __name__ == "__main__":
    main()
