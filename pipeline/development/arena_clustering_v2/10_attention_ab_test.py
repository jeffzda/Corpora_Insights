#!/usr/bin/env python3
"""Phase 4d-test — attention-degradation A/B test at fixed catalogue snapshots.

Design (per notes_attention_test.md):

For one or more target iterations K:
  1. Reconstruct the iter-K-start catalogue (seed + clusters with creation_iter < K)
  2. Pull the 200 records from that iter (corpus_assignments.jsonl filter)
  3. ARM A: batched Pass 1 — same prompt as the original sweep
  4. ARM B: per-record cached Pass 1 — dedicated call per record
  5. Compare

Metrics:
  - Replication fidelity (Arm A vs original assignments) → confirms temp=0 reproducibility
  - Recovery rate (Arm A "orphan" → Arm B "classified") → ATTENTION RECOVERY
  - Cross-disagreement (both classify but different cluster) → precision difference
  - Asymmetric (Arm B "orphan" but Arm A "classified") → noise floor

Procurement-probity invariant: cluster signatures are immutable. The reconstructed
iter-K catalogue is therefore the EXACT same text the original sweep saw at iter K.

Outputs (in clustering_v2/output/sweep/attention_ab/):
  - iter_K_arm_A.jsonl, iter_K_arm_B.jsonl
  - summary.json
  - disagreements.md
"""
import argparse
import asyncio
import json
import re
import time
from collections import defaultdict
from pathlib import Path

import anthropic

import importlib.util
_06_path = Path(__file__).resolve().parent / '06_classify_and_cluster_orphans.py'
_spec = importlib.util.spec_from_file_location('p06', _06_path)
p06 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p06)
_08_path = Path(__file__).resolve().parent / '08_final_singleton_sweep.py'
_spec = importlib.util.spec_from_file_location('p08', _08_path)
p08 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p08)

OUT_DIR = Path(__file__).resolve().parent.parent / 'output'
SWEEP_DIR = OUT_DIR / 'sweep'
INPUT = OUT_DIR / 'filter_input.jsonl'
WORKING_CATALOGUE = SWEEP_DIR / 'cluster_catalogue.json'
ASSIGNMENTS = SWEEP_DIR / 'corpus_assignments.jsonl'
AB_DIR = SWEEP_DIR / 'attention_ab'
AB_DIR.mkdir(exist_ok=True)


def reconstruct_catalogue(catalogue, cluster_creation_iter, target_iter):
    """Return clusters that existed at the START of target_iter:
       - All seed clusters (cluster_id < c500): always present
       - All orphan-pass clusters with creation_iter < target_iter
    """
    out = []
    for c in catalogue:
        cid = c['cluster_id']
        try:
            num = int(cid[1:])
        except:
            continue
        if num < 500:
            out.append(c)
        else:
            cre = cluster_creation_iter.get(cid)
            if cre is not None and cre < target_iter:
                out.append(c)
    # Sort by cluster_id for prompt determinism
    out.sort(key=lambda c: int(c['cluster_id'][1:]) if c['cluster_id'][1:].isdigit() else 9999)
    return out


def build_creation_iter_map(assignments):
    """Earliest iter where each cluster_id ≥ c500 appears as new_cluster status."""
    out = {}
    for a in assignments:
        cid = a.get('cluster_id'); status = a.get('status')
        if cid and status == 'new_cluster':
            try: num = int(cid[1:])
            except: continue
            if num >= 500:
                if cid not in out or a['iteration'] < out[cid]:
                    out[cid] = a['iteration']
    return out


def load_records_for_iter(assignments, target_iter, rid_to_record):
    rows = [a for a in assignments if a['iteration'] == target_iter]
    records = [rid_to_record[a['record_id']] for a in rows if a['record_id'] in rid_to_record]
    # Reconstruct original Pass 1 outcomes from the recorded `status`+`cluster_id`:
    # - status=='classified'        → orig P1 = cluster_id (matched existing)
    # - status=='new_cluster'       → orig P1 = 'orphan' (then Pass 2 made cluster)
    # - status=='pending_singleton' → orig P1 = 'orphan' (Pass 2 didn't form cluster)
    orig_p1 = {}
    for a in rows:
        if a['status'] == 'classified':
            orig_p1[a['record_id']] = a['cluster_id']
        else:
            orig_p1[a['record_id']] = 'orphan'
    return records, orig_p1


async def per_record_classify(model, records, catalogue_block, valid_ids, concurrency, label):
    client = anthropic.AsyncAnthropic()
    sem = asyncio.Semaphore(concurrency)
    started = time.time()
    out = []

    async def one(r):
        async with sem:
            try:
                resp = await client.messages.create(
                    model=model, max_tokens=64, temperature=0.0,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": catalogue_block,
                             "cache_control": {"type": "ephemeral"}},
                            {"type": "text", "text": p08.build_record_text(r)},
                        ]
                    }],
                )
                text = resp.content[0].text if resp.content else ''
                parsed = p08.parse_response(text)
                cid = (parsed or {}).get('cluster_id', None)
                if cid != 'orphan' and cid not in valid_ids:
                    cid = 'orphan'
                return {'record_id': r['record_id'], 'cluster_id': cid or 'orphan',
                        'input_tokens': resp.usage.input_tokens,
                        'output_tokens': resp.usage.output_tokens,
                        'cache_creation_tokens': getattr(resp.usage, 'cache_creation_input_tokens', 0),
                        'cache_read_tokens': getattr(resp.usage, 'cache_read_input_tokens', 0)}
            except Exception as e:
                return {'record_id': r['record_id'], 'cluster_id': None, 'error': str(e)}

    tasks = [asyncio.create_task(one(r)) for r in records]
    n = 0
    for fut in asyncio.as_completed(tasks):
        result = await fut; out.append(result); n += 1
        if n % 50 == 0:
            print(f"    [{label}] {n}/{len(records)}  ({n/(time.time()-started):.1f}/s)", flush=True)
    return out


def batched_classify(records, catalogue_K, label):
    """Replicate the original sweep's Pass 1 batched call."""
    client = anthropic.Anthropic()
    prompt = p06.build_classify_prompt(catalogue_K, records)
    print(f"    [{label}] batched call, prompt {len(prompt):,} chars", flush=True)
    text, msg = p06.stream_call(client, prompt, raw_path=None, label=label)
    parsed = p06.parse_json_tolerant(text)
    assignments = parsed.get('assignments') or parsed.get('_recovered') or []
    rid_to_cid = {a['record_id']: a['cluster_id'] for a in assignments
                  if isinstance(a, dict) and 'record_id' in a}
    valid = {c['cluster_id'] for c in catalogue_K}
    out = []
    for r in records:
        cid = rid_to_cid.get(r['record_id'], 'orphan')
        if cid != 'orphan' and cid not in valid:
            cid = 'orphan'  # defensive
        out.append({'record_id': r['record_id'], 'cluster_id': cid})
    return out, msg


def compare(arm_A, arm_B, orig_p1, catalogue_K_ids):
    A = {x['record_id']: x['cluster_id'] for x in arm_A}
    B = {x['record_id']: x['cluster_id'] for x in arm_B if x.get('cluster_id') is not None}
    n = len(set(A) & set(B))
    a_orph = [r for r in A if A[r] == 'orphan']
    a_clf = [r for r in A if A[r] != 'orphan']
    b_orph = [r for r in B if B[r] == 'orphan']
    b_clf = [r for r in B if B[r] != 'orphan']
    # Replication: A vs orig
    repl_match = sum(1 for r in A if r in orig_p1 and A[r] == orig_p1[r])
    # Recovery: A orphan → B classified
    recovered = [r for r in a_orph if r in B and B[r] != 'orphan']
    # Reverse: A classified → B orphan
    reverse = [r for r in a_clf if r in B and B[r] == 'orphan']
    # Cross-class: both classify, differ
    cross = [r for r in a_clf if r in B and B[r] != 'orphan' and A[r] != B[r]]
    # Both classify, agree
    same_class = [r for r in a_clf if r in B and B[r] != 'orphan' and A[r] == B[r]]
    return {
        'n_records': n,
        'replication_match_to_original': repl_match,
        'replication_match_pct': round(100*repl_match/len(orig_p1), 2),
        'A_classified': len(a_clf), 'A_orphan': len(a_orph),
        'B_classified': len(b_clf), 'B_orphan': len(b_orph),
        'A_orphan_B_classified_recovered': len(recovered),
        'A_classified_B_orphan': len(reverse),
        'cross_class_disagreement': len(cross),
        'both_classified_same_cluster': len(same_class),
        'recovered_record_ids': recovered[:30],
        'reverse_record_ids': reverse[:30],
        'cross_record_ids': cross[:30],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iters', type=str, default='30,70,110')
    ap.add_argument('--concurrency', type=int, default=20)
    args = ap.parse_args()
    target_iters = [int(x) for x in args.iters.split(',')]

    print("Loading data...", flush=True)
    catalogue_full = json.load(open(WORKING_CATALOGUE))['clusters']
    rows = [json.loads(l) for l in open(INPUT)]
    rid_to_record = {r['record_id']: r for r in rows}
    assignments = [json.loads(l) for l in open(ASSIGNMENTS)]
    creation_iter = build_creation_iter_map(assignments)
    print(f"  full catalogue: {len(catalogue_full)} clusters", flush=True)
    print(f"  cluster creation_iter map: {len(creation_iter)} orphan-pass clusters", flush=True)
    print(f"  target iters: {target_iters}", flush=True)

    summary = {'iters': {}, 'meta': {'concurrency': args.concurrency}}
    all_disagreements = []

    for K in target_iters:
        print(f"\n=== Iter {K} ===", flush=True)
        cat_K = reconstruct_catalogue(catalogue_full, creation_iter, K)
        cat_K_ids = {c['cluster_id'] for c in cat_K}
        records, orig_p1 = load_records_for_iter(assignments, K, rid_to_record)
        print(f"  catalogue at iter-{K} start: {len(cat_K)} clusters", flush=True)
        print(f"  records in iter {K}: {len(records)}", flush=True)
        if not records:
            continue

        # Arm A: batched
        print(f"  → ARM A (batched Sonnet, replicate Pass 1)", flush=True)
        t0 = time.time()
        arm_A, msg_A = batched_classify(records, cat_K, f'iter{K}-A')
        a_wall = time.time() - t0
        a_cost = msg_A.usage.input_tokens/1e6*3 + msg_A.usage.output_tokens/1e6*15
        (AB_DIR / f'iter_{K}_arm_A.jsonl').write_text(
            '\n'.join(json.dumps(r) for r in arm_A))

        # Arm B: per-record cached
        print(f"  → ARM B (per-record cached Sonnet)", flush=True)
        catalogue_block = p08.build_catalogue_block(cat_K)
        print(f"     cached prefix: {len(catalogue_block):,} chars", flush=True)
        t0 = time.time()
        arm_B = asyncio.run(per_record_classify(
            'claude-sonnet-4-6', records, catalogue_block, cat_K_ids,
            args.concurrency, f'iter{K}-B'))
        b_wall = time.time() - t0
        # cost
        b_in = sum(r.get('input_tokens',0) for r in arm_B)
        b_out = sum(r.get('output_tokens',0) for r in arm_B)
        b_cw = sum(r.get('cache_creation_tokens',0) for r in arm_B)
        b_cr = sum(r.get('cache_read_tokens',0) for r in arm_B)
        b_cost = (b_in/1e6)*3 + (b_out/1e6)*15 + (b_cw/1e6)*3.75 + (b_cr/1e6)*0.30
        (AB_DIR / f'iter_{K}_arm_B.jsonl').write_text(
            '\n'.join(json.dumps(r) for r in arm_B))

        comp = compare(arm_A, arm_B, orig_p1, cat_K_ids)
        comp.update({
            'catalogue_size_at_iter_K': len(cat_K),
            'arm_A_cost': round(a_cost, 3), 'arm_A_wall': round(a_wall, 1),
            'arm_B_cost': round(b_cost, 3), 'arm_B_wall': round(b_wall, 1),
        })
        summary['iters'][K] = comp
        print(f"  Replication (A vs original): {comp['replication_match_to_original']}/{len(orig_p1)}"
              f" ({comp['replication_match_pct']:.1f}%)")
        print(f"  ARM A: {comp['A_classified']} classified, {comp['A_orphan']} orphan")
        print(f"  ARM B: {comp['B_classified']} classified, {comp['B_orphan']} orphan")
        print(f"  RECOVERY (A-orphan → B-classified): {comp['A_orphan_B_classified_recovered']}")
        print(f"  REVERSE  (A-classified → B-orphan): {comp['A_classified_B_orphan']}")
        print(f"  CROSS    (both classify, differ):   {comp['cross_class_disagreement']}")
        print(f"  AGREE    (both classify, same):     {comp['both_classified_same_cluster']}")
        print(f"  Cost: A ${comp['arm_A_cost']}, B ${comp['arm_B_cost']}")

        # Build disagreement records for inspection
        cid_to_meta = {c['cluster_id']: c for c in catalogue_full}
        for category, ids in [('RECOVERED', comp['recovered_record_ids'][:7]),
                                ('REVERSE',   comp['reverse_record_ids'][:5]),
                                ('CROSS',     comp['cross_record_ids'][:5])]:
            A_map = {x['record_id']: x['cluster_id'] for x in arm_A}
            B_map = {x['record_id']: x['cluster_id'] for x in arm_B}
            for rid in ids:
                r = rid_to_record.get(rid, {})
                all_disagreements.append({
                    'iter': K, 'category': category, 'record_id': rid,
                    'narrative': (r.get('narrative') or '')[:300],
                    'arm_A_cid': A_map.get(rid), 'arm_B_cid': B_map.get(rid),
                    'arm_A_cluster': cid_to_meta.get(A_map.get(rid), {}).get('canonical_name'),
                    'arm_B_cluster': cid_to_meta.get(B_map.get(rid), {}).get('canonical_name'),
                })

    (AB_DIR / 'summary.json').write_text(json.dumps(summary, indent=2))

    # Markdown disagreements sheet
    md = ["# Attention A/B disagreement inspection", ""]
    for d in all_disagreements:
        md.append(f"\n## iter {d['iter']} | {d['category']} | {d['record_id']}")
        md.append(f"narrative: {d['narrative']}")
        md.append(f"\n**Arm A (batched) → {d['arm_A_cid']}**  {d['arm_A_cluster'] or ''}")
        md.append(f"**Arm B (per-record) → {d['arm_B_cid']}**  {d['arm_B_cluster'] or ''}")
        md.append("")
    (AB_DIR / 'disagreements.md').write_text('\n'.join(md))

    print(f"\n=== ATTENTION A/B SUMMARY ===")
    for K, c in summary['iters'].items():
        print(f"  iter {K} (cat={c['catalogue_size_at_iter_K']}): "
              f"recovery {c['A_orphan_B_classified_recovered']}/{c['A_orphan']} "
              f"({100*c['A_orphan_B_classified_recovered']/max(c['A_orphan'],1):.1f}% of orphans) | "
              f"cross-class {c['cross_class_disagreement']}/{c['B_classified']} ({100*c['cross_class_disagreement']/max(c['B_classified'],1):.1f}%)")


if __name__ == "__main__":
    main()
