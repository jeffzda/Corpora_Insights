#!/usr/bin/env python3
"""Single Opus 4.7 call that consolidates ~4,150 parent labels from 50
independent Pass-1 runs into a canonical mechanism vocabulary.

The voice-audit-style Jaccard clustering used in the per-batch analyser
over-fragments the vocabulary because phrasing varies between runs
("Regulatory framework absence or technology-novel gap" vs "Regulatory
framework misfit to current technology" — same class, Jaccard ~0.20).
Asking Opus to consolidate gives a much cleaner frequency table.

Inputs:
  closure/output/parent_ensemble/parsed_runs.jsonl

Outputs:
  closure/output/parent_ensemble/canonical_vocabulary.json — canonical
      classes with member labels and per-class frequency
  closure/output/parent_ensemble/canonical_vocabulary_meta.json — call meta
  closure/output/parent_ensemble/canonical_vocabulary.md — human-readable
      summary with frequency tiers and canonical class list

Cost: ~$2 (155k input × $5/M + 50k output × $25/M @ 1M-context Opus 4.7).
Wall: ~3-5 min streaming.
"""
from __future__ import annotations
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[2]
PARSED_RUNS = ROOT / 'closure/output/parent_ensemble/parsed_runs.jsonl'
OUT = ROOT / 'closure/output/parent_ensemble/canonical_vocabulary.json'
META = ROOT / 'closure/output/parent_ensemble/canonical_vocabulary_meta.json'
SUMMARY_MD = ROOT / 'closure/output/parent_ensemble/canonical_vocabulary.md'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 128000
PRICE_IN_PER_M = 5
PRICE_OUT_PER_M = 25


PROMPT_TEMPLATE = """# Canonical mechanism vocabulary derivation

## Context

You are consolidating parent-archetype labels from 50 independent runs of the same upstream task. Each run was given the same 1,141 mechanism-level failure clusters and asked to derive an emergent parent vocabulary. The 50 runs produced {n_labels} parent labels in total, with substantial phrasing variation across runs even when the underlying mechanism class is identical.

Your job is to consolidate these {n_labels} labels into a canonical mechanism vocabulary — i.e., identify the distinct mechanism classes the runs collectively name, and map each input label to exactly one canonical class (or to 'no fit' if it doesn't match any class).

## Constraints

1. **Mechanism class, not name overlap.** Two labels with different names that describe the same structural mechanism class belong in the same canonical class. Two labels with similar names that describe structurally distinct mechanisms (e.g. "Regulatory framework gap" vs "Regulatory process latency") belong in different canonical classes.

2. **Tightness over breadth.** A canonical class should describe a single mechanism class. If you have to use "or" to span structurally distinct mechanisms, split into multiple canonical classes.

3. **Emergent count.** Return as many canonical classes as the data warrants. Don't force-merge to reach a target count.

4. **No-fit is allowed.** If a label doesn't cleanly fit any canonical class, mark it `class_id: "none"` rather than stretching a class to absorb it.

5. **Use the run+parent_id stable identifier in your output.** Each label below is tagged `[run_NN:pXX]`. Use that exact string in your assignments list.

6. **Every input label must appear exactly once in the assignments list.** Output count must equal input count ({n_labels}).

## Output

Strict JSON, no extra text:

```json
{{
  "canonical_classes": [
    {{
      "class_id": "c01",
      "name": "<short noun phrase, 3-7 words>",
      "definition": "<one sentence: what mechanism this class names>",
      "mechanism_criterion": "<one sentence: what must be true for a label to belong here>"
    }}
  ],
  "assignments": [
    {{"label_id": "run_01:p03", "class_id": "c01"}},
    {{"label_id": "run_02:p07", "class_id": "c01"}},
    ...
  ],
  "notes": "<optional observations>"
}}
```

Number canonical classes c01, c02, ... in order of estimated population (most-populated class first).

## Input — {n_labels} parent labels from 50 runs

Each line is `[run_NN:pXX] name | mechanism_criterion`:

{labels_block}
"""


def parse_json(raw: str) -> dict | None:
    raw = raw.strip()
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[1] if '\n' in raw else raw
        if raw.endswith('```'):
            raw = raw.rsplit('```', 1)[0]
    s, e = raw.find('{'), raw.rfind('}')
    if s < 0 or e <= s:
        return None
    try:
        return json.loads(raw[s:e+1])
    except Exception as ex:
        print(f"  JSON parse error: {ex}", flush=True)
        return None


def main():
    print("Loading parsed runs...", flush=True)
    runs = [json.loads(l) for l in PARSED_RUNS.open()]
    print(f"  {len(runs)} runs loaded")

    # Build label list and lookup
    label_records = []  # list of {label_id, run_id, parent_id, name, criterion}
    for r in runs:
        run_id = r['custom_id']
        for p in r.get('parents', []):
            pid = p.get('parent_id', '')
            name = (p.get('name') or '').replace('|', '/').strip()
            crit = (p.get('mechanism_criterion') or '').replace('|', '/').replace('\n', ' ').strip()
            label_records.append({
                'label_id': f'{run_id}:{pid}',
                'run_id': run_id,
                'parent_id': pid,
                'name': name,
                'criterion': crit,
            })
    print(f"  {len(label_records)} parent labels total across {len(runs)} runs")

    # Build labels block
    lines = []
    for lr in label_records:
        lines.append(f"  [{lr['label_id']}] {lr['name']} | {lr['criterion']}")
    labels_block = '\n'.join(lines)

    prompt = PROMPT_TEMPLATE.format(n_labels=len(label_records), labels_block=labels_block)
    print(f"  Prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tokens)", flush=True)

    print(f"\nCalling {MODEL} (max_tokens={MAX_TOKENS:,})...", flush=True)
    client = anthropic.Anthropic()
    parts = []
    started = time.time()
    last_print = started; last_chars = 0; text_chars = 0
    with client.messages.stream(
        model=MODEL, max_tokens=MAX_TOKENS,
        messages=[{'role': 'user', 'content': prompt}],
    ) as stream:
        for ev in stream.text_stream:
            parts.append(ev); text_chars += len(ev)
            now = time.time()
            if now - last_print >= 5:
                rate = (text_chars - last_chars) / max(now - last_print, 1)
                print(f"  [{int(now-started)}s] {text_chars:,} chars  +{rate:.0f} c/s",
                      flush=True)
                last_print = now; last_chars = text_chars
        msg = stream.get_final_message()
    raw = ''.join(parts)
    wall = time.time() - started

    in_tok = msg.usage.input_tokens
    out_tok = msg.usage.output_tokens
    cost = in_tok/1e6 * PRICE_IN_PER_M + out_tok/1e6 * PRICE_OUT_PER_M
    print(f"\n  Wall: {wall:.0f}s  in/out: {in_tok:,}/{out_tok:,}  cost ${cost:.3f}", flush=True)
    print(f"  Stop reason: {msg.stop_reason}", flush=True)
    if msg.stop_reason != 'end_turn':
        print(f"  ! Stop reason was {msg.stop_reason!r} — output may be truncated", flush=True)

    parsed = parse_json(raw)
    if not parsed:
        OUT.with_suffix('.raw.json').write_text(json.dumps({'raw_response': raw}, indent=2))
        raise SystemExit(f"! Parse failed; raw saved to {OUT.with_suffix('.raw.json')}")

    canonical = parsed.get('canonical_classes', [])
    assigns = parsed.get('assignments', [])
    notes = parsed.get('notes', '')

    # Validate: every input label appears in assignments exactly once
    expected_ids = {lr['label_id'] for lr in label_records}
    seen_ids = [a.get('label_id') for a in assigns]
    seen_set = set(seen_ids)
    missing = expected_ids - seen_set
    extra = seen_set - expected_ids
    duplicated = [lid for lid, n in Counter(seen_ids).items() if n > 1]

    valid_class_ids = {c.get('class_id') for c in canonical} | {'none'}
    bad_class_assigns = [a for a in assigns if a.get('class_id') not in valid_class_ids]

    print(f"\n  canonical classes: {len(canonical)}")
    print(f"  assignments returned: {len(assigns)} (input had {len(label_records)} labels)")
    if missing: print(f"  ! {len(missing)} input labels missing from assignments: {sorted(missing)[:5]}...")
    if extra: print(f"  ! {len(extra)} assignment label_ids not in input: {sorted(extra)[:5]}...")
    if duplicated: print(f"  ! {len(duplicated)} duplicated label_ids in assignments: {duplicated[:5]}...")
    if bad_class_assigns: print(f"  ! {len(bad_class_assigns)} assignments have unknown class_id: "
                                f"{[a.get('class_id') for a in bad_class_assigns[:5]]}...")

    # Build frequency table: class_id -> set of run_ids that contributed at least one label
    class_to_runs = defaultdict(set)
    class_to_labels = defaultdict(list)
    label_lookup = {lr['label_id']: lr for lr in label_records}
    for a in assigns:
        lid = a.get('label_id')
        cid = a.get('class_id')
        if lid not in label_lookup or cid == 'none' or cid not in valid_class_ids:
            continue
        run_id = label_lookup[lid]['run_id']
        class_to_runs[cid].add(run_id)
        class_to_labels[cid].append(lid)

    # Per-canonical-class frequency
    n_runs = len(runs)
    canonical_with_freq = []
    for c in canonical:
        cid = c['class_id']
        n_runs_present = len(class_to_runs.get(cid, set()))
        canonical_with_freq.append({
            **c,
            'n_runs_present': n_runs_present,
            'n_labels_assigned': len(class_to_labels.get(cid, [])),
            'frequency': round(n_runs_present / n_runs, 3),
            'member_label_ids': class_to_labels.get(cid, []),
        })
    canonical_with_freq.sort(key=lambda c: -c['n_runs_present'])

    # Tier counts
    tier_counts = Counter()
    for c in canonical_with_freq:
        f = c['frequency']
        if f >= 0.90: tier_counts['core_>=90%'] += 1
        elif f >= 0.70: tier_counts['high_70-89%'] += 1
        elif f >= 0.40: tier_counts['boundary_40-69%'] += 1
        elif f >= 0.20: tier_counts['rare_20-39%'] += 1
        else: tier_counts['singleton_<20%'] += 1

    union_at = {1: 0, 5: 0, 10: 0, 25: 0, 45: 0}
    for c in canonical_with_freq:
        n = c['n_runs_present']
        for k in union_at:
            if n >= k: union_at[k] += 1

    # Save outputs
    OUT.write_text(json.dumps({
        'canonical_classes': canonical_with_freq,
        'n_total_classes': len(canonical_with_freq),
        'tier_counts': dict(tier_counts),
        'union_size_at_min_runs': union_at,
        'parse_validation': {
            'n_labels_input': len(label_records),
            'n_assignments_output': len(assigns),
            'n_missing_from_assignments': len(missing),
            'n_extra_in_assignments': len(extra),
            'n_duplicated_in_assignments': len(duplicated),
            'n_bad_class_id': len(bad_class_assigns),
        },
        'notes': notes,
    }, indent=2))
    META.write_text(json.dumps({
        'model': MODEL,
        'input_tokens': in_tok,
        'output_tokens': out_tok,
        'cost_usd': round(cost, 4),
        'wall_seconds': round(wall, 1),
        'stop_reason': msg.stop_reason,
        'prompt_chars': len(prompt),
        'output_chars': len(raw),
    }, indent=2))
    print(f"  wrote {OUT}")
    print(f"  wrote {META}")

    # === Markdown summary ===
    lines = [
        f"# Pass-1 Ensemble Canonical Vocabulary",
        f"",
        f"Consolidated by Opus 4.7 from {len(label_records)} parent labels across 50 independent Pass-1 runs.",
        f"Cost: ${cost:.2f}, wall {wall:.0f}s, {in_tok:,} in / {out_tok:,} out tokens.",
        f"",
        f"## Frequency tiers",
        f"",
        f"Distinct canonical mechanism classes: **{len(canonical_with_freq)}**",
        f"",
        f"| Tier | n classes |",
        f"|---|---:|",
    ]
    for t in ['core_>=90%', 'high_70-89%', 'boundary_40-69%', 'rare_20-39%', 'singleton_<20%']:
        lines.append(f"| {t} | {tier_counts.get(t, 0)} |")
    lines += [
        f"",
        f"## Union-vocabulary size at minimum-runs threshold",
        f"",
        f"| Min runs | n classes |",
        f"|---:|---:|",
    ]
    for k, n in sorted(union_at.items()):
        lines.append(f"| ≥ {k} | {n} |")
    lines += [
        f"",
        f"## All canonical classes (sorted by frequency)",
        f"",
        f"| Runs | Freq | Class | Definition |",
        f"|---:|---:|---|---|",
    ]
    for c in canonical_with_freq:
        lines.append(f"| {c['n_runs_present']}/{n_runs} | {c['frequency']*100:.0f}% | "
                     f"**{c['name']}** | {c.get('definition','')[:140]} |")

    if notes:
        lines += [f"", f"## Notes from the consolidator", f"", notes]

    SUMMARY_MD.write_text('\n'.join(lines))
    print(f"  wrote {SUMMARY_MD}")
    print(f"\n=== Tier summary ===")
    for t, n in tier_counts.most_common():
        print(f"  {t:25} {n:>4}")
    print(f"\nTOTAL canonical classes: {len(canonical_with_freq)}")


if __name__ == '__main__':
    main()
