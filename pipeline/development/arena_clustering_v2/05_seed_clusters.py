#!/usr/bin/env python3
"""Phase 4a — Initial seed: stratified ~500-record sample → Sonnet single call
→ initial cluster catalogue with canonical names + descriptions.

Stratification: 8 top kb_categories × 4 axis-combos × ~15 records/cell = ~480.

Output:
- output/seed_sample.jsonl — the 500 records used
- output/cluster_catalogue.json — frozen initial cluster catalogue
- output/seed_response_raw.txt — the model's raw response (audit trail)
"""
import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path

import anthropic

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = Path(__file__).resolve().parent.parent / 'output'
INPUT = OUT_DIR / 'filter_input.jsonl'
SAMPLE_OUT = OUT_DIR / 'seed_sample.jsonl'
CATALOGUE_OUT = OUT_DIR / 'cluster_catalogue.json'
RAW_OUT = OUT_DIR / 'seed_response_raw.txt'

TOP_CATEGORIES = [
    "Distributed energy resources",
    "Solar energy, Solar PV R&amp;D",
    "Hydrogen energy",
    "Battery storage",
    "Renewables for industry",
    "Electric vehicles",
    "Demand response",
    "Bioenergy / Energy from waste",
]

# 4 axis-combos for failure-mode coverage
AXIS_COMBOS = [
    ('occ_mech', lambda r: r.get('is_occurrence')=='yes' and r.get('is_mechanism')=='yes'),
    ('mech_only', lambda r: r.get('is_mechanism')=='yes' and r.get('is_occurrence')=='no'),
    ('occ_only', lambda r: r.get('is_occurrence')=='yes' and r.get('is_mechanism')=='no'),
    ('lesson_or_rec', lambda r: (r.get('is_lesson')=='yes' or r.get('is_recommendation')=='yes')
                                 and (r.get('is_mechanism')=='yes' or r.get('is_occurrence')=='yes')),
]

PER_CELL = 15  # 8 cats × 4 combos × 15 = 480


def stratified_sample(rows, seed=42):
    rng = random.Random(seed)
    by_cell = defaultdict(list)
    for r in rows:
        cat = r.get('project') or ''  # placeholder; we use kb_category from per_doc lookup
    # Re-load per-doc for kb_category
    V1 = ROOT / 'corpora/arena/output/per_doc'
    rec_to_cat = {}
    for f in V1.glob('doc_*.json'):
        d = json.load(open(f))
        for r in d.get('records', []):
            rec_to_cat[r['id']] = r.get('kb_category', '')

    by_cell = defaultdict(list)
    for r in rows:
        cat = rec_to_cat.get(r['record_id'], '')
        if cat not in TOP_CATEGORIES:
            continue
        for combo_name, pred in AXIS_COMBOS:
            if pred(r):
                by_cell[(cat, combo_name)].append(r)
                break  # first matching combo only

    # Sample per cell
    sample = []
    for (cat, combo), pool in by_cell.items():
        rng.shuffle(pool)
        take = min(PER_CELL, len(pool))
        for r in pool[:take]:
            r['_seed_cat'] = cat
            r['_seed_combo'] = combo
            sample.append(r)
    rng.shuffle(sample)
    return sample


SEED_PROMPT = """You are building an initial catalogue of FAILURE-MODE CLUSTERS for the ARENA renewable-energy project corpus.

Each input record is a piece of extracted insight from a project document. The records below have all been pre-tagged as failure-mode-relevant (negative valence + occurrence-or-mechanism). Read all records and infer the set of failure-mode clusters that exist in this sample.

CRITICAL: Cluster by MECHANISM (the 'how' or 'why' something fails), NOT by:
- Project name or technology vocabulary
- Equipment models or feeder identifiers
- Domain (solar/wind/battery/etc) — the same mechanism can occur across domains

Two records share a cluster if they describe the SAME causal pathway, even if the projects, equipment, and surface vocabulary differ.

YOUR JOB: produce a CATALOGUE of failure-mode cluster LABELS. Each cluster must be supported by at least 3 records sharing the same causal mechanism. Records that don't have at least 2 other records sharing their mechanism should be returned as singletons — listed by record_id but NOT promoted to a cluster definition.

You are NOT assigning records to clusters in this step beyond identifying which records justified each cluster (no full member lists), and you are NOT writing descriptions yet (those come later, after all assignment is done across the full corpus).

For each cluster you identify, output:
- cluster_id: c001, c002, ... (zero-padded 3 digits)
- canonical_name: 4-12 word descriptive name (locks forever; do not change later)
- mechanism_signature: 1 sentence of the abstracted causal logic. Either form is fine:
  - "X causes Y because Z" (when there is a clear triggering condition)
  - "Y because Z" (when the cause is the property/condition itself, with no separate trigger)
- supporting_record_ids: list of 3+ record_ids from the input that share this mechanism (just the ids, no descriptions). Used to verify the ≥3 threshold and to seed downstream classification.

Then list every record that did NOT get grouped into a cluster as a singleton, by record_id.

CRITICAL THRESHOLD RULE:
- Do NOT propose a cluster supported by fewer than 3 records. A pattern observed in 1 or 2 records is a hypothesis, not a cluster — leave those records as singletons.
- Singletons may later become clusters when subsequent batches contribute matching records.

Rules:
- Aim for clusters that are tightly mechanism-bound, not breadth-bound.
- Prefer specificity over breadth. "Voltage regulation under high PV" is too broad. "Traditional voltage-regulation solutions exhausted before 100% PV hosting capacity" is the right resolution.
- DO NOT cluster by project, equipment model, or technology domain — the test is mechanism, not topic.
- Avoid project-specific vocabulary in the canonical_name and signature. The label should generalise.
- It is fine — preferred, even — to leave many records as singletons. The catalogue is only for patterns with ≥3 evidence.

Output valid JSON, schema:
{
  "clusters": [
    {
      "cluster_id": "c001",
      "canonical_name": "...",
      "mechanism_signature": "...",
      "supporting_record_ids": ["ARENA-DLV-XXXX-NNNN", "ARENA-DLV-XXXX-NNNN", "ARENA-DLV-XXXX-NNNN"]
    }
  ],
  "singletons": ["ARENA-DLV-XXXX-NNNN", "ARENA-DLV-XXXX-NNNN", ...]
}

# Records to cluster"""


def build_record_block(records):
    lines = []
    for r in records:
        rid = r['record_id']
        cat = r.get('_seed_cat', '')
        combo = r.get('_seed_combo', '')
        narr = (r.get('narrative') or '').strip()
        evi  = (r.get('evidence') or '').strip()
        axes = []
        for ax in ['is_occurrence','is_mechanism','is_specification','is_lesson','is_recommendation']:
            if r.get(ax) == 'yes':
                axes.append(ax[3:])
        v = r.get('valence', '')
        lines.append(f"\n## {rid}  [cat: {cat[:30]}]  [axes: {','.join(axes)}; v: {v}]")
        lines.append(f"narrative: {narr}")
        if evi and evi != narr:
            lines.append(f"evidence: {evi[:600]}")
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='claude-sonnet-4-6')
    ap.add_argument('--max-tokens', type=int, default=128_000)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    print(f"Loading filter input...", flush=True)
    rows = [json.loads(l) for l in open(INPUT)]
    print(f"  {len(rows):,} records available", flush=True)

    print(f"Stratified sampling...", flush=True)
    sample = stratified_sample(rows)
    print(f"  Sampled {len(sample)} records", flush=True)
    cell_counts = defaultdict(int)
    for r in sample:
        cell_counts[(r['_seed_cat'][:30], r['_seed_combo'])] += 1
    print(f"  Per-cell distribution:")
    for (cat, combo), n in sorted(cell_counts.items()):
        print(f"    {cat:<32} {combo:<14}  {n}")

    SAMPLE_OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in sample))
    print(f"  Wrote {SAMPLE_OUT}", flush=True)

    record_block = build_record_block(sample)
    full_prompt = SEED_PROMPT + "\n\n" + record_block
    print(f"\nPrompt size: {len(full_prompt):,} chars (~{len(full_prompt)//4:,} tokens)", flush=True)

    if args.dry_run:
        print("Dry run; not submitting.", flush=True)
        return

    print(f"\nSubmitting to {args.model} (streaming, save-as-we-go, with retries)...", flush=True)
    import time as _t
    client = anthropic.Anthropic()
    # Open RAW_OUT for incremental writes — we'll have partial output even if stream dies
    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    raw_f = open(RAW_OUT, 'w', encoding='utf-8')
    started = _t.time()
    last_print = 0
    last_chars = 0
    text_chars = 0
    in_tok = out_tok = 0
    msg = None
    try:
        with client.messages.stream(
            model=args.model,
            max_tokens=args.max_tokens,
            temperature=0.0,
            messages=[{"role": "user", "content": full_prompt}],
        ) as stream:
            for ev in stream.text_stream:
                raw_f.write(ev)
                raw_f.flush()  # disk every chunk
                text_chars += len(ev)
                now = _t.time()
                if now - last_print >= 5:
                    rate = (text_chars - last_chars) / max(now - last_print, 1)
                    # Read last 80 chars from disk to preview
                    raw_f.flush()
                    with open(RAW_OUT, 'r', encoding='utf-8') as pf:
                        pf.seek(max(0, text_chars - 100))
                        preview = pf.read().replace('\n',' ')[-80:]
                    print(f"  [{int(now - started)}s] streamed {text_chars:,} chars  "
                          f"(+{rate:.0f} chars/s)  preview: {preview}", flush=True)
                    last_print = now
                    last_chars = text_chars
            msg = stream.get_final_message()
        in_tok = msg.usage.input_tokens
        out_tok = msg.usage.output_tokens
    except Exception as e:
        print(f"\n  STREAM FAILED at {int(_t.time()-started)}s with {text_chars:,} chars saved: {e}",
              flush=True)
        print(f"  Partial output is in {RAW_OUT}; will attempt to parse what's there.", flush=True)
    finally:
        raw_f.close()
    text = open(RAW_OUT, 'r', encoding='utf-8').read()
    cost_sync = in_tok/1e6 * 3.0 + out_tok/1e6 * 15.0
    print(f"  Input tokens:  {in_tok:,}", flush=True)
    print(f"  Output tokens: {out_tok:,}", flush=True)
    print(f"  Cost: ${cost_sync:.2f} sync (~${cost_sync*0.5:.2f} batch)", flush=True)

    print(f"  Raw response (full or partial): {RAW_OUT}", flush=True)

    # Tolerant parser — partial JSON likely if stream died
    m = re.search(r'```json\s*(.*?)(?:```|$)', text, re.DOTALL)
    body = m.group(1).strip() if m else text.strip()
    parsed = None
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        # Truncated; extract complete cluster objects up to last valid }
        # Find array opening
        arr_start = body.find('[')
        if arr_start >= 0:
            # Walk through, collecting balanced { ... } objects
            depth = 0
            obj_start = -1
            objects = []
            for i, ch in enumerate(body[arr_start+1:], start=arr_start+1):
                if ch == '{':
                    if depth == 0: obj_start = i
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0 and obj_start >= 0:
                        try:
                            obj = json.loads(body[obj_start:i+1])
                            objects.append(obj)
                        except: pass
                        obj_start = -1
            parsed = {'clusters': objects}
            print(f"  RECOVERED {len(objects)} complete cluster objects from partial JSON", flush=True)
    if parsed is None:
        raise SystemExit("Could not parse any clusters from response")

    catalogue = parsed.get('clusters', [])
    print(f"\n  Parsed {len(catalogue)} initial clusters", flush=True)

    sizes = [len(c.get('member_record_ids', [])) for c in catalogue]
    print(f"  Cluster size distribution:")
    print(f"    min: {min(sizes)}, max: {max(sizes)}, median: {sorted(sizes)[len(sizes)//2]}")
    print(f"    singletons: {sum(1 for s in sizes if s == 1)}")
    print(f"    size >= 5: {sum(1 for s in sizes if s >= 5)}")

    # Save catalogue
    out = {
        'meta': {
            'model': args.model,
            'temperature': 0.0,
            'n_seed_records': len(sample),
            'input_tokens': in_tok,
            'output_tokens': out_tok,
            'cost_usd_sync': round(cost_sync, 2),
        },
        'clusters': catalogue,
    }
    CATALOGUE_OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\nWrote {CATALOGUE_OUT}", flush=True)

    print(f"\nTop 12 largest seed clusters:")
    catalogue_sorted = sorted(catalogue, key=lambda c: -len(c.get('member_record_ids', [])))
    for c in catalogue_sorted[:12]:
        print(f"  [{c.get('cluster_id','?')}] {len(c.get('member_record_ids',[])):>3}  "
              f"{c.get('canonical_name','')[:75]}")


if __name__ == "__main__":
    main()
