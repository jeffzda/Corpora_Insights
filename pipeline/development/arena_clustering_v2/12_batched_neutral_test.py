#!/usr/bin/env python3
"""Phase 4d-test — batched Pass 1 with NEUTRAL prompt (Arm D).

Completes the 2x2 of (batched vs per-record) × (defensive vs neutral prompt).
Existing arms in attention_ab/:
  Arm A — batched + defensive (replicates original sweep prompt)
  Arm B — per-record + defensive
  Arm C — per-record + neutral
This script adds Arm D — batched + neutral.

The neutral prompt drops the "CRITICAL: Do NOT force-fit" warning and the
bullet list of mechanism-vs-vocabulary don'ts. Otherwise identical structure
to the defensive prompt: same catalogue rendering, same record format,
same JSON output schema.

After this run, all four pairwise comparisons are available:
  A vs D — does the defensive warning suppress batched classifications too?
  C vs D — pure attention test (prompt held neutral, method varies)
  B vs C — already done; defensive→neutral in per-record context
  A vs B — already done; batched→per-record under defensive prompt
"""
import argparse
import json
import time
from pathlib import Path

import anthropic

import importlib.util
_06_path = Path(__file__).resolve().parent / '06_classify_and_cluster_orphans.py'
_spec = importlib.util.spec_from_file_location('p06', _06_path)
p06 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p06)
_10_path = Path(__file__).resolve().parent / '10_attention_ab_test.py'
_spec = importlib.util.spec_from_file_location('p10', _10_path)
p10 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p10)

OUT_DIR = Path(__file__).resolve().parent.parent / 'output'
SWEEP_DIR = OUT_DIR / 'sweep'
INPUT = OUT_DIR / 'filter_input.jsonl'
WORKING_CATALOGUE = SWEEP_DIR / 'cluster_catalogue.json'
ASSIGNMENTS = SWEEP_DIR / 'corpus_assignments.jsonl'
AB_DIR = SWEEP_DIR / 'attention_ab'

# Neutral batched prompt — same task scope as p06.build_classify_prompt but
# with defensive language stripped.
NEUTRAL_BATCHED_HEADER = """You are classifying ARENA renewable-energy project records against a catalogue of failure-mode clusters.

For each record, your goal is to assign it to one of the listed clusters if one of them reasonably describes the causal failure mechanism the record discusses. If no existing cluster fits, return cluster_id="orphan".

# CATALOGUE OF FAILURE-MODE CLUSTERS"""

NEUTRAL_BATCHED_FOOTER = """# OUTPUT FORMAT

Return JSON only:
{
  "assignments": [
    {"record_id": "ARENA-DLV-XXXX-NNNN", "cluster_id": "c042"},
    {"record_id": "ARENA-DLV-XXXX-NNNN", "cluster_id": "orphan"},
    ...
  ]
}

One assignment per input record, in input order. cluster_id must be either an existing catalogue id (e.g. "c042") or the literal string "orphan"."""


def build_neutral_batched_prompt(catalogue, records):
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
    return NEUTRAL_BATCHED_HEADER + ''.join(cat_lines) + "\n\n# RECORDS TO CLASSIFY" + \
           ''.join(rec_lines) + "\n\n" + NEUTRAL_BATCHED_FOOTER


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iters', type=str, default='30,70,110')
    args = ap.parse_args()
    target_iters = [int(x) for x in args.iters.split(',')]

    catalogue_full = json.load(open(WORKING_CATALOGUE))['clusters']
    rows = [json.loads(l) for l in open(INPUT)]
    rid_to_record = {r['record_id']: r for r in rows}
    assignments = [json.loads(l) for l in open(ASSIGNMENTS)]
    creation_iter = p10.build_creation_iter_map(assignments)
    client = anthropic.Anthropic()

    summary = {'iters': {}}
    for K in target_iters:
        print(f"\n=== Iter {K} (Arm D — batched + NEUTRAL prompt) ===", flush=True)
        cat_K = p10.reconstruct_catalogue(catalogue_full, creation_iter, K)
        valid_ids = {c['cluster_id'] for c in cat_K}
        records, _ = p10.load_records_for_iter(assignments, K, rid_to_record)
        prompt = build_neutral_batched_prompt(cat_K, records)
        print(f"  catalogue: {len(cat_K)} clusters; prompt {len(prompt):,} chars", flush=True)

        t0 = time.time()
        text, msg = p06.stream_call(client, prompt, raw_path=None, label=f'iter{K}-D')
        wall = time.time() - t0
        parsed = p06.parse_json_tolerant(text)
        raw_assignments = parsed.get('assignments') or parsed.get('_recovered') or []
        rid_to_cid = {a['record_id']: a['cluster_id'] for a in raw_assignments
                      if isinstance(a, dict) and 'record_id' in a}
        out_rows = []
        for r in records:
            cid = rid_to_cid.get(r['record_id'], 'orphan')
            if cid != 'orphan' and cid not in valid_ids:
                cid = 'orphan'
            out_rows.append({'record_id': r['record_id'], 'cluster_id': cid})
        (AB_DIR / f'iter_{K}_arm_D.jsonl').write_text(
            '\n'.join(json.dumps(r) for r in out_rows))

        # Compare with stored arms
        A = {x['record_id']: x['cluster_id']
             for x in (json.loads(l) for l in open(AB_DIR/f'iter_{K}_arm_A.jsonl'))}
        B = {x['record_id']: x['cluster_id']
             for x in (json.loads(l) for l in open(AB_DIR/f'iter_{K}_arm_B.jsonl'))
             if x.get('cluster_id') is not None}
        C = {x['record_id']: x['cluster_id']
             for x in (json.loads(l) for l in open(AB_DIR/f'iter_{K}_arm_C.jsonl'))
             if x.get('cluster_id') is not None}
        D = {r['record_id']: r['cluster_id'] for r in out_rows}
        rids = set(A) & set(B) & set(C) & set(D)

        def n_clf(M, r): return M[r] not in (None, 'orphan')
        a_n = sum(1 for r in rids if n_clf(A, r))
        b_n = sum(1 for r in rids if n_clf(B, r))
        c_n = sum(1 for r in rids if n_clf(C, r))
        d_n = sum(1 for r in rids if n_clf(D, r))

        # A vs D: defensive→neutral batched
        ad_a_only = [r for r in rids if n_clf(A,r) and not n_clf(D,r)]
        ad_d_only = [r for r in rids if n_clf(D,r) and not n_clf(A,r)]
        ad_both_same = [r for r in rids if n_clf(A,r) and n_clf(D,r) and A[r]==D[r]]
        ad_both_diff = [r for r in rids if n_clf(A,r) and n_clf(D,r) and A[r]!=D[r]]
        # C vs D: per-record vs batched, neutral prompt held constant
        cd_c_only = [r for r in rids if n_clf(C,r) and not n_clf(D,r)]
        cd_d_only = [r for r in rids if n_clf(D,r) and not n_clf(C,r)]
        cd_both_same = [r for r in rids if n_clf(C,r) and n_clf(D,r) and C[r]==D[r]]
        cd_both_diff = [r for r in rids if n_clf(C,r) and n_clf(D,r) and C[r]!=D[r]]

        cost = msg.usage.input_tokens/1e6*3 + msg.usage.output_tokens/1e6*15
        summary['iters'][K] = {
            'catalogue_size': len(cat_K), 'records': len(rids),
            'A_clf': a_n, 'B_clf': b_n, 'C_clf': c_n, 'D_clf': d_n,
            'AD_A_only_classifies': len(ad_a_only),
            'AD_D_only_classifies': len(ad_d_only),
            'AD_same_cluster': len(ad_both_same),
            'AD_diff_cluster': len(ad_both_diff),
            'CD_C_only_classifies': len(cd_c_only),
            'CD_D_only_classifies': len(cd_d_only),
            'CD_same_cluster': len(cd_both_same),
            'CD_diff_cluster': len(cd_both_diff),
            'D_cost': round(cost, 3), 'D_wall': round(wall, 1),
        }
        print(f"  Classified counts: A={a_n}, B={b_n}, C={c_n}, D={d_n} (out of {len(rids)})")
        print(f"  A vs D (batched, defensive vs neutral): A-only {len(ad_a_only)}, "
              f"D-only {len(ad_d_only)}, same {len(ad_both_same)}, diff {len(ad_both_diff)}")
        print(f"  C vs D (neutral, per-record vs batched): C-only {len(cd_c_only)}, "
              f"D-only {len(cd_d_only)}, same {len(cd_both_same)}, diff {len(cd_both_diff)}")
        print(f"  Cost: ${cost:.3f}, wall {wall:.0f}s")

    (AB_DIR / 'summary_2x2.json').write_text(json.dumps(summary, indent=2))
    print(f"\n=== 2x2 SUMMARY (classified counts out of 200) ===")
    print(f"            | Batched | Per-record")
    print(f"  Defensive |   A     |    B")
    print(f"  Neutral   |   D     |    C")
    print()
    for K, c in summary['iters'].items():
        print(f"  iter {K}: A={c['A_clf']:>3}  B={c['B_clf']:>3}  C={c['C_clf']:>3}  D={c['D_clf']:>3}")


if __name__ == "__main__":
    main()
