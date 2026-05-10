#!/usr/bin/env python3
"""Phase 4d-test — neutral-prompt per-record classification (Arm C).

Test whether the over-conservatism observed in script 10's Arm B (per-record
classification with "do not force-fit" instruction + bullet list of mechanism-vs-
vocabulary warnings) is driven by the prompt's defensive framing.

Re-runs per-record classification on the SAME iter-30/70/110 records that script
10 already covered (Arm A batched, Arm B per-record-with-defensive-prompt). The
catalogue snapshots are reconstructed identically.

Comparison:
  - Arm A (batched, original sweep prompt): from iter_K_arm_A.jsonl
  - Arm B (per-record, defensive prompt):   from iter_K_arm_B.jsonl
  - Arm C (per-record, NEUTRAL prompt):     this script

Output: iter_K_arm_C.jsonl + summary_C_vs_others.json + disagreements_C.md
"""
import argparse
import asyncio
import json
import re
import time
from pathlib import Path

import anthropic

import importlib.util
_06_path = Path(__file__).resolve().parent / '06_classify_and_cluster_orphans.py'
_spec = importlib.util.spec_from_file_location('p06', _06_path)
p06 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p06)
_08_path = Path(__file__).resolve().parent / '08_final_singleton_sweep.py'
_spec = importlib.util.spec_from_file_location('p08', _08_path)
p08 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p08)
_10_path = Path(__file__).resolve().parent / '10_attention_ab_test.py'
_spec = importlib.util.spec_from_file_location('p10', _10_path)
p10 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p10)

OUT_DIR = Path(__file__).resolve().parent.parent / 'output'
SWEEP_DIR = OUT_DIR / 'sweep'
INPUT = OUT_DIR / 'filter_input.jsonl'
WORKING_CATALOGUE = SWEEP_DIR / 'cluster_catalogue.json'
ASSIGNMENTS = SWEEP_DIR / 'corpus_assignments.jsonl'
AB_DIR = SWEEP_DIR / 'attention_ab'

# Neutral prompt — no "do not force-fit", no bullet list of don'ts
NEUTRAL_HEADER = """You are classifying an ARENA renewable-energy project record against a catalogue of failure-mode clusters.

Your goal: assign the record to one of the listed clusters if one of them reasonably describes the causal failure mechanism the record discusses. If no existing cluster fits, the record remains unassigned (return "orphan").

# CATALOGUE OF FAILURE-MODE CLUSTERS"""

NEUTRAL_FOOTER_TEMPLATE = """\

# RECORD TO CLASSIFY

## {rid}  [axes: {axes}; v: {valence}]
narrative: {narrative}
{evidence_line}

# OUTPUT FORMAT

Return JSON only — first character `{{`, last character `}}`, no prose.

{{"cluster_id": "c042"}}     ← any cluster_id from the catalogue
{{"cluster_id": "orphan"}}   ← if no listed cluster fits this record"""


def build_neutral_catalogue_block(catalogue):
    lines = []
    for c in catalogue:
        lines.append(f"\n[{c['cluster_id']}] {c['canonical_name']}")
        lines.append(f"  mechanism: {c['mechanism_signature']}")
    return NEUTRAL_HEADER + ''.join(lines)


def build_neutral_record_text(r):
    rid = r['record_id']
    narr = (r.get('narrative') or '').strip()
    evi = (r.get('evidence') or '').strip()
    axes = []
    for ax in ['is_occurrence','is_mechanism','is_specification','is_lesson','is_recommendation']:
        if r.get(ax) == 'yes':
            axes.append(ax[3:])
    evidence_line = f"evidence: {evi[:600]}" if (evi and evi != narr) else ""
    return NEUTRAL_FOOTER_TEMPLATE.format(
        rid=rid, axes=','.join(axes), valence=r.get('valence',''),
        narrative=narr, evidence_line=evidence_line,
    )


async def classify_neutral(records, catalogue_block, valid_ids, concurrency, label):
    client = anthropic.AsyncAnthropic()
    sem = asyncio.Semaphore(concurrency)
    started = time.time()
    out = []

    async def one(r):
        async with sem:
            try:
                resp = await client.messages.create(
                    model='claude-sonnet-4-6', max_tokens=64, temperature=0.0,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": catalogue_block,
                             "cache_control": {"type": "ephemeral"}},
                            {"type": "text", "text": build_neutral_record_text(r)},
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iters', type=str, default='30,70,110')
    ap.add_argument('--concurrency', type=int, default=20)
    args = ap.parse_args()
    target_iters = [int(x) for x in args.iters.split(',')]

    catalogue_full = json.load(open(WORKING_CATALOGUE))['clusters']
    rows = [json.loads(l) for l in open(INPUT)]
    rid_to_record = {r['record_id']: r for r in rows}
    assignments = [json.loads(l) for l in open(ASSIGNMENTS)]
    creation_iter = p10.build_creation_iter_map(assignments)

    summary = {'iters': {}}
    for K in target_iters:
        print(f"\n=== Iter {K} (Arm C — neutral prompt) ===", flush=True)
        cat_K = p10.reconstruct_catalogue(catalogue_full, creation_iter, K)
        valid_ids = {c['cluster_id'] for c in cat_K}
        records, _ = p10.load_records_for_iter(assignments, K, rid_to_record)
        block = build_neutral_catalogue_block(cat_K)
        print(f"  catalogue at iter-{K}: {len(cat_K)} clusters; cached prefix {len(block):,} chars", flush=True)

        t0 = time.time()
        arm_C = asyncio.run(classify_neutral(records, block, valid_ids, args.concurrency, f'iter{K}-C'))
        wall = time.time() - t0
        (AB_DIR / f'iter_{K}_arm_C.jsonl').write_text(
            '\n'.join(json.dumps(r) for r in arm_C))

        # Compare with stored Arm A (batched) and Arm B (defensive per-record)
        A = {x['record_id']: x['cluster_id']
             for x in (json.loads(l) for l in open(AB_DIR/f'iter_{K}_arm_A.jsonl'))}
        B = {x['record_id']: x['cluster_id']
             for x in (json.loads(l) for l in open(AB_DIR/f'iter_{K}_arm_B.jsonl'))
             if x.get('cluster_id') is not None}
        C = {x['record_id']: x['cluster_id'] for x in arm_C if x.get('cluster_id') is not None}

        rids_all = set(A) & set(B) & set(C)
        c_clf = sum(1 for r in rids_all if C[r] != 'orphan')
        b_clf = sum(1 for r in rids_all if B[r] != 'orphan')
        a_clf = sum(1 for r in rids_all if A[r] != 'orphan')

        # Reverse_C: A classified, C orphan (analog of Reverse for new prompt)
        reverse_C = [r for r in rids_all if A[r]!='orphan' and C[r]=='orphan']
        # Recovery_C: A orphan, C classified
        recovery_C = [r for r in rids_all if A[r]=='orphan' and C[r]!='orphan']
        # Cross_C: both A and C classify, differ
        cross_C = [r for r in rids_all if A[r]!='orphan' and C[r]!='orphan' and A[r]!=C[r]]
        # Agree_C: both A and C classify, same
        agree_C = [r for r in rids_all if A[r]!='orphan' and C[r]!='orphan' and A[r]==C[r]]
        # Compare C vs B (the defensive prompt): how does dropping the warning shift things?
        c_class_b_orph = [r for r in rids_all if C[r]!='orphan' and B[r]=='orphan']
        b_class_c_orph = [r for r in rids_all if B[r]!='orphan' and C[r]=='orphan']
        same_class_BC = [r for r in rids_all if B[r]!='orphan' and C[r]!='orphan' and B[r]==C[r]]
        diff_class_BC = [r for r in rids_all if B[r]!='orphan' and C[r]!='orphan' and B[r]!=C[r]]

        # cost
        c_in = sum(r.get('input_tokens',0) for r in arm_C)
        c_out = sum(r.get('output_tokens',0) for r in arm_C)
        c_cw = sum(r.get('cache_creation_tokens',0) for r in arm_C)
        c_cr = sum(r.get('cache_read_tokens',0) for r in arm_C)
        c_cost = (c_in/1e6)*3 + (c_out/1e6)*15 + (c_cw/1e6)*3.75 + (c_cr/1e6)*0.30

        summary['iters'][K] = {
            'catalogue_size': len(cat_K),
            'records': len(rids_all),
            'arm_A_classified': a_clf, 'arm_B_classified': b_clf, 'arm_C_classified': c_clf,
            'reverse_C_vs_A': len(reverse_C),
            'recovery_C_vs_A': len(recovery_C),
            'cross_C_vs_A': len(cross_C),
            'agree_C_vs_A': len(agree_C),
            'C_classified_B_orphan': len(c_class_b_orph),
            'B_classified_C_orphan': len(b_class_c_orph),
            'BC_same_cluster': len(same_class_BC),
            'BC_different_cluster': len(diff_class_BC),
            'arm_C_cost': round(c_cost, 3), 'arm_C_wall': round(wall, 1),
        }
        print(f"  Arm A classified: {a_clf}/{len(rids_all)}")
        print(f"  Arm B (defensive per-record) classified: {b_clf}/{len(rids_all)}")
        print(f"  Arm C (NEUTRAL per-record) classified:   {c_clf}/{len(rids_all)}  ← did the warning suppress these?")
        print(f"  C vs A (batched): reverse={len(reverse_C)}  recovery={len(recovery_C)}  cross={len(cross_C)}  agree={len(agree_C)}")
        print(f"  C vs B (defensive): C-only-classifies {len(c_class_b_orph)}  B-only-classifies {len(b_class_c_orph)}  same {len(same_class_BC)}  diff {len(diff_class_BC)}")
        print(f"  Cost: ${c_cost:.2f}, wall {wall:.0f}s")

    (AB_DIR / 'summary_C_vs_others.json').write_text(json.dumps(summary, indent=2))
    print(f"\n=== SUMMARY ===")
    for K, c in summary['iters'].items():
        print(f"  iter {K}: A={c['arm_A_classified']}, B={c['arm_B_classified']}, C={c['arm_C_classified']}  "
              f"(C reverse {c['reverse_C_vs_A']} vs A, recovery {c['recovery_C_vs_A']} vs A)")


if __name__ == "__main__":
    main()
