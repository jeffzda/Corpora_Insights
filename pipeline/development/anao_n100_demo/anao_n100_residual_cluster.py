#!/usr/bin/env python3
"""ANAO N=100 — Phase 4e: residual orphan clustering.

Mirrors corpora/arena/clustering_v2/code/14_residual_orphan_cluster.py
condensed to a single chunk (195 residuals fit in one Pass 2 call).

The 195 records left orphan after the singleton sweep all rejected the
matured 189-cluster catalogue. Through iterative sweep + singleton sweep,
they have NEVER been tested together — each iteration's Pass 2 only saw
that iteration's orphans. This script gives them one chance to form
≥3-record clusters from each other.

New clusters get appended to the catalogue. Records that still don't
form clusters are written as true singletons.
"""
import json
import re
import time
from pathlib import Path

import anthropic

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = ROOT / 'corpora/anao/n100_demo/output'
INPUT = OUT_DIR / 'anao_n100_filter_input.jsonl'
SWEEP_DIR = OUT_DIR / 'sweep'
CATALOGUE = SWEEP_DIR / 'cluster_catalogue.json'
RESIDUAL_IN = SWEEP_DIR / 'reclassify' / 'residual_orphans.json'

RES_DIR = SWEEP_DIR / 'residual'
RES_DIR.mkdir(parents=True, exist_ok=True)
NEW_CATALOGUE = RES_DIR / 'catalogue_after_residual.json'
ASSIGNMENTS_OUT = RES_DIR / 'residual_assignments.jsonl'
NEW_CLUSTERS_OUT = RES_DIR / 'residual_new_clusters.json'
TRUE_SINGLETONS = RES_DIR / 'true_singletons.json'
RAW_OUT = RES_DIR / 'residual_raw.txt'
META_OUT = RES_DIR / 'meta.json'

MODEL = 'claude-sonnet-4-6'
MAX_TOKENS = 64_000


ORPHAN_CLUSTER_PROMPT = """You are extending the catalogue of FAILURE-MODE CLUSTERS for the ANAO performance audit corpus.

The records below are TRUE RESIDUAL ORPHANS — they did not match any cluster in a 189-cluster catalogue across two prior classification passes. They have never been tested together as a cohort. Your job is to identify any NEW failure-mode clusters these orphans collectively support.

CRITICAL: Cluster by MECHANISM, not by agency / programme / topic / sector vocabulary. Two records share a cluster only if they describe the SAME causal pathway.

THRESHOLD RULE: A cluster must be supported by at least 3 records. Do NOT propose a cluster justified by 1 or 2 records — leave them out of your output.

For each new cluster, output:
- cluster_id: must NOT collide with the existing catalogue (use c500+ range)
- canonical_name: 4-12 word descriptive name
- mechanism_signature: 1 sentence ("X causes Y because Z" OR "Y because Z")
- supporting_record_ids: list of 3+ record_ids from the orphan set

Rules:
- It IS expected that most residuals will remain unclustered — they are residual for a reason.
- Avoid agency-specific vocabulary in the canonical_name and signature.

# OUTPUT FORMAT — STRICT

Return a single JSON object and NOTHING ELSE. The first character must be `{`, the last must be `}`. No prose, markdown fences, or commentary.

Schema:
{
  "clusters": [
    {
      "cluster_id": "c501",
      "canonical_name": "...",
      "mechanism_signature": "...",
      "supporting_record_ids": ["ANAOM-...", "ANAOM-...", "ANAOM-..."]
    }
  ]
}

# RESIDUAL ORPHANS"""


def stream_call(client, prompt, raw_path=None):
    raw_f = open(raw_path, 'w') if raw_path else None
    started = time.time()
    last_print = 0; last_chars = 0; text_chars = 0
    parts = []; msg = None
    try:
        with client.messages.stream(
            model=MODEL, max_tokens=MAX_TOKENS, temperature=0.0,
            messages=[{'role':'user','content':prompt}],
        ) as stream:
            for ev in stream.text_stream:
                if raw_f: raw_f.write(ev); raw_f.flush()
                parts.append(ev); text_chars += len(ev)
                now = time.time()
                if now - last_print >= 5:
                    rate = (text_chars-last_chars)/max(now-last_print,1)
                    print(f'  [{int(now-started)}s] {text_chars:,} chars +{rate:.0f} c/s', flush=True)
                    last_print = now; last_chars = text_chars
            msg = stream.get_final_message()
    finally:
        if raw_f: raw_f.close()
    return ''.join(parts), msg


def parse_tolerant(text):
    m = re.search(r'```json\s*(.*?)(?:```|$)', text, re.DOTALL)
    body = m.group(1).strip() if m else text.strip()
    try: return json.loads(body)
    except json.JSONDecodeError:
        first = body.find('{'); last = body.rfind('}')
        if first >= 0:
            try: return json.loads(body[first:last+1])
            except: pass
    return {}


def build_orphan_block(records):
    lines = []
    for r in records:
        rid = r['record_id']
        narr = (r.get('narrative') or '').strip()
        evi = (r.get('evidence') or '').strip()
        axes = []
        for ax in ['is_occurrence','is_mechanism','is_specification','is_lesson','is_recommendation']:
            if r.get(ax) == 'yes': axes.append(ax[3:])
        lines.append(f"\n## {rid}  [axes: {','.join(axes)}; v: {r.get('valence','')}]")
        lines.append(f"narrative: {narr}")
        if evi and evi != narr:
            lines.append(f"evidence: {evi[:600]}")
    return '\n'.join(lines)


def main():
    catalogue = json.load(CATALOGUE.open())
    residual_ids = json.load(RESIDUAL_IN.open())
    rows = [json.loads(l) for l in INPUT.open()]
    rid_to_record = {r['record_id']: r for r in rows}
    residual_records = [rid_to_record[r] for r in residual_ids if r in rid_to_record]
    print(f'catalogue: {len(catalogue["clusters"])} clusters', flush=True)
    print(f'residual orphans: {len(residual_records):,}', flush=True)

    prompt = ORPHAN_CLUSTER_PROMPT + build_orphan_block(residual_records)
    print(f'prompt: {len(prompt):,} chars (~{len(prompt)//4:,} input tokens)', flush=True)

    client = anthropic.Anthropic()
    started = time.time()
    text, msg = stream_call(client, prompt, raw_path=RAW_OUT)
    wall = time.time() - started
    cost = msg.usage.input_tokens/1e6*3 + msg.usage.output_tokens/1e6*15
    print(f'done: {wall:.0f}s  {msg.usage.input_tokens:,}in/{msg.usage.output_tokens:,}out  ${cost:.3f}', flush=True)

    parsed = parse_tolerant(text)
    new_clusters = parsed.get('clusters', [])
    print(f'new clusters proposed: {len(new_clusters)}', flush=True)

    # Reconcile new cluster_ids: use unused range above existing
    nci = catalogue.get('next_cluster_id',
                         max([int(c['cluster_id'][1:]) for c in catalogue['clusters']] + [0]) + 1)
    placed_ids = set()
    new_assigns = []
    accepted = []
    for nc in new_clusters:
        members = nc.get('supporting_record_ids', [])
        if len(members) < 3: continue
        new_id = f'c{nci:03d}'
        cat_entry = {
            'cluster_id': new_id,
            'canonical_name': nc.get('canonical_name', '?'),
            'mechanism_signature': nc.get('mechanism_signature', ''),
            'created_iter': 'residual',
            'seed_members': members,
        }
        catalogue['clusters'].append(cat_entry)
        accepted.append(cat_entry)
        for rid in members:
            new_assigns.append({'record_id': rid, 'cluster_id': new_id, 'method': 'residual_pass2'})
            placed_ids.add(rid)
        nci += 1
    catalogue['next_cluster_id'] = nci

    # Persist
    NEW_CATALOGUE.write_text(json.dumps(catalogue, indent=2, ensure_ascii=False))
    with ASSIGNMENTS_OUT.open('w') as f:
        for a in new_assigns: f.write(json.dumps(a) + '\n')
    NEW_CLUSTERS_OUT.write_text(json.dumps(accepted, indent=2, ensure_ascii=False))

    true_singletons = sorted(rid for rid in residual_ids if rid not in placed_ids)
    TRUE_SINGLETONS.write_text(json.dumps(true_singletons, indent=2))

    META_OUT.write_text(json.dumps({
        'n_residual_input': len(residual_records),
        'n_new_clusters': len(accepted),
        'n_records_placed': len(new_assigns),
        'n_true_singletons': len(true_singletons),
        'placement_rate': round(len(new_assigns)/max(len(residual_records),1), 3),
        'final_catalogue_size': len(catalogue['clusters']),
        'cost_usd': round(cost, 4),
        'wall_seconds': round(wall, 1),
        'input_tokens': msg.usage.input_tokens, 'output_tokens': msg.usage.output_tokens,
    }, indent=2))

    print(f'\n=== residual clustering done ===')
    print(f'  new clusters: {len(accepted)}')
    print(f'  records placed: {len(new_assigns)}')
    print(f'  true singletons: {len(true_singletons)}')
    print(f'  final catalogue: {len(catalogue["clusters"])}')
    print(f'  cost: ${cost:.2f}')
    if accepted:
        print(f'\nfirst 5 new clusters:')
        for c in accepted[:5]:
            print(f"  [{c['cluster_id']}] {c['canonical_name']}  ({len(c['seed_members'])} members)")


if __name__ == '__main__':
    main()
