#!/usr/bin/env python3
"""Rate each of the 4,150 parent-archetype labels (50 runs × ~83 parents avg) on
a 1-5 abstraction scale via single Opus 4.7 call.

Tests Jeff's hypothesis (2026-05-05): abstraction level varies *within* each
run, not just across runs. If true, every run will show a wide within-run
distribution of abstraction ratings, regardless of n_parents.

Output: 4,150 ratings tied to (run_id, parent_id), then aggregated per-run
to characterise within-run abstraction distribution.

Cost: ~$2 (155k input × $5/M + 40k output × $25/M @ 1M-context Opus 4.7).
"""
from __future__ import annotations
import json
import re
import time
from collections import defaultdict
from pathlib import Path
import statistics

import anthropic

ROOT = Path(__file__).resolve().parents[2]
PARSED_RUNS = ROOT / 'closure/output/parent_ensemble/parsed_runs.jsonl'
OUT = ROOT / 'closure/output/parent_ensemble/abstraction_ratings.json'
META = ROOT / 'closure/output/parent_ensemble/abstraction_ratings_meta.json'
SUMMARY_MD = ROOT / 'closure/output/parent_ensemble/abstraction_ratings.md'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 128000
PRICE_IN_PER_M = 5
PRICE_OUT_PER_M = 25


PROMPT_TEMPLATE = """# Abstraction-level rating of parent-archetype labels

## Context

You are rating {n_labels} parent-archetype labels produced across 50 independent runs of a parent-derivation task. Each label names a failure-mode mechanism class. Your job is to assign each label a single abstraction-level rating on a 1-5 scale, where the question is: *how broad or narrow is the mechanism class this label names?*

## Calibration anchors

- **5 = most broad** — covers an entire failure family that subdivides into many distinct mechanisms. Examples: "Information failure", "Coordination failure", "Physical limits".
- **4 = broad** — names a recognisable mechanism family with multiple structurally-distinct sub-types. Examples: "Material, chemical, and physical-property limits", "Regulatory framework gap or absence", "Multi-party coordination overhead".
- **3 = mid** — names a coherent mechanism class. The mechanism is one structural pathway, not a family of pathways. Examples: "Inverter-based resource grid-interaction failure", "Lab-to-field translation failure", "Workforce skills shortage".
- **2 = specific** — names a particular causal pathway within a known mechanism class, with named conditions or actors. Examples: "Caustic stress-corrosion cracking of casing in unset cement", "FCAS revenue compression as new entrants saturate thin markets".
- **1 = most specific** — names a single concrete mechanism instance, often with project-specific or condition-specific detail. Rare in this dataset; most labels are 2-5.

## Task

For each label below, return its abstraction rating (1-5) and a brief reason (≤ 12 words).

**Use the entire scale.** This dataset spans wide abstraction ranges; if many labels cluster at 4, but some are clearly broader (5) or narrower (3), distinguish them.

**Distinguish abstraction from frequency.** A label that appears in every run isn't necessarily abstract; it might be a specific mechanism that's common in the corpus. Rate the *mechanism's structural breadth*, not how often the label appears.

## Output

Strict JSON, no extra text. Compact format — no reasoning, just label_id and rating. Output every input label exactly once:

```json
{{
  "ratings": [
    {{"id": "run_01:p03", "a": 4}},
    {{"id": "run_01:p04", "a": 3}}
  ]
}}
```

Use exactly the keys `id` and `a` (single character) for compactness. The output should be approximately 30-40k characters total — keep it tight.

## Input — {n_labels} parent labels

Each line is `[run_NN:pXX] name | mechanism_criterion`.

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

    # Build label list and lookup
    labels = []
    label_run = {}  # label_id -> run_id
    for r in runs:
        run_id = r['custom_id']
        for p in r.get('parents', []):
            pid = p.get('parent_id', '')
            name = (p.get('name') or '').replace('|', '/').strip()
            crit = (p.get('mechanism_criterion') or '').replace('|', '/').replace('\n', ' ').strip()
            lid = f'{run_id}:{pid}'
            labels.append((lid, name, crit))
            label_run[lid] = run_id

    print(f"  {len(labels)} labels across {len(runs)} runs", flush=True)

    block = '\n'.join(f"  [{lid}] {name} | {crit}" for lid, name, crit in labels)
    prompt = PROMPT_TEMPLATE.format(n_labels=len(labels), labels_block=block)
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

    parsed = parse_json(raw)
    if not parsed:
        OUT.with_suffix('.raw.json').write_text(json.dumps({'raw_response': raw}, indent=2))
        raise SystemExit(f"! Parse failed; raw saved to {OUT.with_suffix('.raw.json')}")

    ratings = parsed.get('ratings', [])
    print(f"\n  ratings returned: {len(ratings)} (input had {len(labels)} labels)")

    # Validate (accept both 'id'/'a' compact and 'label_id'/'abstraction' verbose)
    def get_id(r): return r.get('id') or r.get('label_id')
    def get_rating(r): return r.get('a') if 'a' in r else r.get('abstraction')

    expected = {lid for lid, _, _ in labels}
    seen = {get_id(r) for r in ratings}
    missing = expected - seen
    extra = seen - expected
    if missing: print(f"  ! {len(missing)} input labels missing from output: {sorted(missing)[:5]}...")
    if extra: print(f"  ! {len(extra)} extra label_ids in output: {sorted(extra)[:5]}...")

    # Per-run distribution
    by_run = defaultdict(list)
    for r in ratings:
        lid = get_id(r); a = get_rating(r)
        if lid in label_run and a is not None:
            by_run[label_run[lid]].append(a)

    # Compute within-run statistics
    run_stats = []
    for rid, vals in by_run.items():
        if not vals: continue
        run_stats.append({
            'run': rid,
            'n_parents': len(vals),
            'min': min(vals), 'max': max(vals),
            'mean': round(statistics.mean(vals), 2),
            'sd': round(statistics.stdev(vals), 2) if len(vals) > 1 else 0,
            'p10': sorted(vals)[max(0, int(len(vals)*0.10))],
            'p90': sorted(vals)[min(len(vals)-1, int(len(vals)*0.90))],
            'distribution': {k: vals.count(k) for k in [1,2,3,4,5]},
        })
    run_stats.sort(key=lambda r: r['n_parents'])

    out_data = {
        'n_labels_input': len(labels),
        'n_ratings_received': len(ratings),
        'n_missing': len(missing),
        'n_extra': len(extra),
        'overall_distribution': {k: sum(s['distribution'].get(k, 0) for s in run_stats) for k in [1,2,3,4,5]},
        'per_run': run_stats,
        'all_ratings': ratings,
    }
    OUT.write_text(json.dumps(out_data, indent=2))
    META.write_text(json.dumps({
        'model': MODEL, 'input_tokens': in_tok, 'output_tokens': out_tok,
        'cost_usd': round(cost, 4), 'wall_seconds': round(wall, 1),
        'stop_reason': msg.stop_reason,
        'prompt_chars': len(prompt), 'output_chars': len(raw),
    }, indent=2))
    print(f"  wrote {OUT}")
    print(f"  wrote {META}")

    # === Summary ===
    overall = out_data['overall_distribution']
    total = sum(overall.values())
    print(f"\n=== Overall abstraction distribution across {total} labels ===")
    for k in [1,2,3,4,5]:
        n = overall.get(k, 0)
        print(f"  rating {k}: {n:>5}  ({n/total*100:.0f}%)")

    print(f"\n=== Per-run within-run sd (sorted by n_parents) ===")
    print(f"{'run':10} {'n_par':>6} {'min':>4} {'max':>4} {'mean':>5} {'sd':>5} {'distribution(1/2/3/4/5)':>25}")
    print('-' * 75)
    for s in run_stats:
        d = s['distribution']
        dstr = f"{d.get(1,0)}/{d.get(2,0)}/{d.get(3,0)}/{d.get(4,0)}/{d.get(5,0)}"
        print(f"{s['run']:10} {s['n_parents']:>6} {s['min']:>4} {s['max']:>4} {s['mean']:>5.2f} {s['sd']:>5.2f}  {dstr:>22}")

    # Markdown summary
    lines = [
        f"# Within-Run Abstraction-Level Distribution",
        f"",
        f"4,150 parent labels rated 1-5 by Opus 4.7 (1=most specific, 5=most broad).",
        f"Cost: ${cost:.2f}, wall {wall:.0f}s.",
        f"",
        f"## Overall distribution",
        f"",
        f"| Rating | n labels | % |",
        f"|---:|---:|---:|",
    ]
    for k in [1,2,3,4,5]:
        n = overall.get(k, 0)
        lines.append(f"| {k} | {n} | {n/total*100:.0f}% |")

    lines += [
        f"",
        f"## Within-run abstraction distributions (sorted by n_parents, ascending)",
        f"",
        f"If abstraction is fixed per run: each row should be concentrated at one rating value.",
        f"If abstraction varies within run: every row spans multiple rating values with sd > 0.5.",
        f"",
        f"| Run | n_par | min | max | mean | sd | dist (1/2/3/4/5) |",
        f"|---|---:|---:|---:|---:|---:|---|",
    ]
    for s in run_stats:
        d = s['distribution']
        dstr = f"{d.get(1,0)}/{d.get(2,0)}/{d.get(3,0)}/{d.get(4,0)}/{d.get(5,0)}"
        lines.append(f"| {s['run']} | {s['n_parents']} | {s['min']} | {s['max']} | {s['mean']:.2f} | {s['sd']:.2f} | {dstr} |")

    SUMMARY_MD.write_text('\n'.join(lines))
    print(f"\n  wrote {SUMMARY_MD}")


if __name__ == '__main__':
    main()
