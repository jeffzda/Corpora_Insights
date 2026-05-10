#!/usr/bin/env python3
"""Decompose the 91 non-atomic canonical classes into the atomic sub-classes
that runs collectively name.

Premise (Jeff, 2026-05-04): the 126-class canonical vocabulary is a
granularity-blurred union — every core class has runs treating it as 2-4
distinct mechanism classes. Construct the "real superset" by taking each
run-level split as a separate atomic label.

Method: single Opus 4.7 call with all 91 non-atomic canonical classes and
their member labels. For each canonical class, Opus identifies the
recurring atomic sub-classes (drawn from the run-level distinctions),
naming them and assigning member labels.

Atomic classes (35) pass through as 1:1 atomic.

Cost: ~$4-6. Input ~125k tokens, output ~125k tokens at 1M-context Opus 4.7.
"""
from __future__ import annotations
import json
import re
import time
from collections import defaultdict
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[2]
VOCAB = ROOT / 'closure/output/parent_ensemble/canonical_vocabulary.json'
PARSED_RUNS = ROOT / 'closure/output/parent_ensemble/parsed_runs.jsonl'
OUT = ROOT / 'closure/output/parent_ensemble/atomic_subclass_decomposition.json'
META = ROOT / 'closure/output/parent_ensemble/atomic_subclass_decomposition_meta.json'
SUMMARY_MD = ROOT / 'closure/output/parent_ensemble/atomic_subclass_decomposition.md'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 128000
PRICE_IN_PER_M = 5
PRICE_OUT_PER_M = 25


PROMPT = """# Atomic sub-class decomposition

## Context

You previously consolidated 4,150 parent-archetype labels from 50 independent runs into 126 canonical mechanism classes. A coherence test shows that 91 of those 126 classes are *non-atomic* — at least one run produced 2+ distinct parent labels falling under them, meaning the run treated those as separate mechanism classes. The canonical class is *coarser* than what individual runs treat as atomic.

Your task now: for each non-atomic canonical class, identify the atomic sub-classes that the runs collectively name. The runs together expose the boundaries the canonical layer merged. Treat each recurring sub-distinction as a separate atomic label, naming it.

## Constraints

1. **Use the runs' own boundaries.** If 14 of 20 splitting runs distinguish "forecast inaccuracy" from "model-assumption error" within the canonical class "Model, simulation, and forecast inaccuracy", those are two atomic sub-classes. Don't add distinctions runs didn't make.

2. **Tightness over breadth.** A sub-class describes one distinct mechanism. If you have to use "or" to span structurally distinct mechanisms, split.

3. **Use original label_ids in member assignments.** Each label below is tagged `[run_NN:pXX]`. Use that exact string in your sub_class member lists.

4. **Every member label of the canonical class must be assigned to exactly one sub-class.** If a label doesn't cleanly fit any sub-class you've identified, create a separate sub-class for it.

5. **Sub-class count is emergent.** Some canonical classes will decompose into 2; others into 4-5; some may decompose into 1 if the labels are all paraphrases of one concept and any "splits" runs made were re-merging adjacent concepts.

6. **Number sub-classes per canonical class.** For canonical class c04, sub-classes are c04.s1, c04.s2, etc. Number in order of frequency (most-populated sub-class first).

## Output

Strict JSON, no extra text:

```json
{
  "decompositions": [
    {
      "canonical_class_id": "c04",
      "canonical_name": "Model, simulation, and forecast inaccuracy",
      "n_runs_present": 50,
      "sub_classes": [
        {
          "subclass_id": "c04.s1",
          "name": "<short noun phrase>",
          "criterion": "<one sentence: what distinguishes this from sibling sub-classes>",
          "member_label_ids": ["run_NN:pXX", ...]
        }
      ],
      "notes": "<optional: anything about this canonical class's internal structure>"
    }
  ]
}
```

## Input — 91 non-atomic canonical classes with their member labels

For each canonical class, all member labels are listed as `[label_id] name | criterion`.

{decomposition_block}
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
    print("Loading canonical vocabulary + parsed runs...", flush=True)
    V = json.load(VOCAB.open())
    canonical = V['canonical_classes']

    # Load full label info from parsed runs
    label_info = {}
    for line in PARSED_RUNS.open():
        run = json.loads(line)
        run_id = run['custom_id']
        for p in run.get('parents', []):
            pid = p.get('parent_id', '')
            label_info[f'{run_id}:{pid}'] = {
                'name': (p.get('name') or '').replace('|', '/').strip(),
                'criterion': (p.get('mechanism_criterion') or '').replace('|', '/').replace('\n', ' ').strip(),
            }
    print(f"  {len(label_info):,} labels indexed across runs", flush=True)

    # Find non-atomic classes
    non_atomic = []
    atomic = []
    for c in canonical:
        members = c.get('member_label_ids', [])
        by_run = defaultdict(list)
        for lid in members:
            by_run[lid.split(':')[0]].append(lid)
        if any(len(v) > 1 for v in by_run.values()):
            non_atomic.append(c)
        else:
            atomic.append(c)
    print(f"  {len(non_atomic)} non-atomic classes to decompose")
    print(f"  {len(atomic)} atomic classes (pass through 1:1)", flush=True)

    # Build decomposition block
    blocks = []
    for c in non_atomic:
        cid = c['class_id']
        name = c['name']
        defn = c.get('definition', '')
        n_runs = c['n_runs_present']
        members = c['member_label_ids']
        block = [f"\n### {cid}: {name} (in {n_runs}/50 runs, {len(members)} member labels)"]
        block.append(f"Definition: {defn}")
        block.append(f"Member labels:")
        for lid in members:
            li = label_info.get(lid, {})
            block.append(f"  [{lid}] {li.get('name', '?')} | {li.get('criterion', '')}")
        blocks.append('\n'.join(block))
    decomposition_block = '\n'.join(blocks)

    prompt = PROMPT.replace('{decomposition_block}', decomposition_block)
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

    decomps = parsed.get('decompositions', [])
    print(f"\n  decompositions returned: {len(decomps)} (input had {len(non_atomic)} non-atomic classes)")

    # Validate: for each non-atomic class, verify decomposition covers all member labels
    decomp_lookup = {d['canonical_class_id']: d for d in decomps}
    coverage_issues = []
    for c in non_atomic:
        cid = c['class_id']
        d = decomp_lookup.get(cid)
        if not d:
            coverage_issues.append({'canonical': cid, 'issue': 'no decomposition'})
            continue
        expected = set(c['member_label_ids'])
        seen = set()
        for sc in d.get('sub_classes', []):
            for lid in sc.get('member_label_ids', []):
                seen.add(lid)
        missing = expected - seen
        extra = seen - expected
        if missing or extra:
            coverage_issues.append({
                'canonical': cid,
                'n_missing': len(missing), 'n_extra': len(extra),
                'missing_sample': sorted(missing)[:3],
                'extra_sample': sorted(extra)[:3],
            })

    if coverage_issues:
        print(f"  ! {len(coverage_issues)} canonical classes have coverage issues:")
        for ci in coverage_issues[:10]:
            print(f"    {ci}")

    # Build flat atomic vocabulary: 35 atomic + (sum over non-atomic of sub-classes)
    flat_atomic = []
    for c in atomic:
        flat_atomic.append({
            'subclass_id': c['class_id'],
            'parent_canonical_class_id': c['class_id'],
            'name': c['name'],
            'definition': c.get('definition', ''),
            'criterion': c.get('mechanism_criterion', ''),
            'is_atomic_pass_through': True,
            'n_runs_present': c['n_runs_present'],
            'frequency': c['frequency'],
            'member_label_ids': c['member_label_ids'],
        })
    n_subclasses_added = 0
    for d in decomps:
        cid = d['canonical_class_id']
        canonical_runs_total = next((c['n_runs_present'] for c in non_atomic if c['class_id'] == cid), 0)
        for sc in d.get('sub_classes', []):
            # Compute n_runs_present for this sub-class from its member_label_ids
            sc_runs = {lid.split(':')[0] for lid in sc.get('member_label_ids', [])}
            flat_atomic.append({
                'subclass_id': sc.get('subclass_id', f"{cid}.s?"),
                'parent_canonical_class_id': cid,
                'parent_canonical_name': d.get('canonical_name', ''),
                'name': sc.get('name', '?'),
                'criterion': sc.get('criterion', ''),
                'is_atomic_pass_through': False,
                'n_runs_present': len(sc_runs),
                'frequency': round(len(sc_runs) / 50, 3),
                'member_label_ids': sc.get('member_label_ids', []),
            })
            n_subclasses_added += 1

    flat_atomic.sort(key=lambda s: -s['n_runs_present'])

    # Tier counts on the new fine-grained vocabulary
    tier_counts = {'core_>=90%': 0, 'high_70-89%': 0, 'boundary_40-69%': 0, 'rare_20-39%': 0, 'singleton_<20%': 0}
    for s in flat_atomic:
        f = s['frequency']
        if f >= 0.9: tier_counts['core_>=90%'] += 1
        elif f >= 0.7: tier_counts['high_70-89%'] += 1
        elif f >= 0.4: tier_counts['boundary_40-69%'] += 1
        elif f >= 0.2: tier_counts['rare_20-39%'] += 1
        else: tier_counts['singleton_<20%'] += 1

    out_data = {
        'n_canonical_input': len(canonical),
        'n_canonical_atomic_passthrough': len(atomic),
        'n_canonical_non_atomic_decomposed': len(non_atomic),
        'n_subclasses_produced_from_decomposition': n_subclasses_added,
        'n_total_atomic_vocabulary': len(flat_atomic),
        'tier_counts': tier_counts,
        'coverage_issues': coverage_issues,
        'decompositions': decomps,
        'flat_atomic_vocabulary': flat_atomic,
    }
    OUT.write_text(json.dumps(out_data, indent=2))
    META.write_text(json.dumps({
        'model': MODEL,
        'input_tokens': in_tok, 'output_tokens': out_tok,
        'cost_usd': round(cost, 4),
        'wall_seconds': round(wall, 1),
        'stop_reason': msg.stop_reason,
        'prompt_chars': len(prompt), 'output_chars': len(raw),
    }, indent=2))
    print(f"  wrote {OUT}")
    print(f"  wrote {META}")

    # === Markdown summary ===
    lines = [
        f"# Atomic Sub-Class Decomposition",
        f"",
        f"Decomposes the 91 non-atomic canonical classes into atomic sub-classes,",
        f"using runs' own boundary choices as the source of within-class distinctions.",
        f"The 35 atomic canonical classes pass through unchanged.",
        f"",
        f"Cost: ${cost:.2f}, wall {wall:.0f}s, {in_tok:,} in / {out_tok:,} out tokens.",
        f"",
        f"## Vocabulary expansion",
        f"",
        f"| Stage | n classes |",
        f"|---|---:|",
        f"| Canonical (script 20) | {len(canonical)} |",
        f"|   ├─ Atomic (pass through) | {len(atomic)} |",
        f"|   └─ Non-atomic (decomposed) | {len(non_atomic)} |",
        f"| Sub-classes produced from decomposition | {n_subclasses_added} |",
        f"| **Total atomic vocabulary** | **{len(flat_atomic)}** |",
        f"",
        f"Vocabulary growth factor: {len(flat_atomic) / len(canonical):.2f}× over canonical 126.",
        f"",
        f"## Frequency tiers (atomic vocabulary)",
        f"",
        f"| Tier | n classes |",
        f"|---|---:|",
    ]
    for t in ['core_>=90%', 'high_70-89%', 'boundary_40-69%', 'rare_20-39%', 'singleton_<20%']:
        lines.append(f"| {t} | {tier_counts[t]} |")

    lines += [
        f"",
        f"## Top decompositions (canonical classes split into the most sub-classes)",
        f"",
        f"| Canonical | n_runs | n sub-classes | Names |",
        f"|---|---:|---:|---|",
    ]
    decomps_with_count = [(d, len(d.get('sub_classes', []))) for d in decomps]
    decomps_with_count.sort(key=lambda x: -x[1])
    for d, n in decomps_with_count[:20]:
        names = ' / '.join(sc.get('name', '?') for sc in d.get('sub_classes', []))
        lines.append(f"| **{d['canonical_class_id']}: {d.get('canonical_name', '?')}** | "
                     f"{d.get('n_runs_present', '?')} | {n} | {names} |")

    lines += [
        f"",
        f"## All atomic-vocabulary sub-classes (sorted by frequency)",
        f"",
        f"| ID | Runs | Freq | Name | Parent canonical |",
        f"|---|---:|---:|---|---|",
    ]
    for s in flat_atomic:
        parent_name = s.get('parent_canonical_name', '') if not s['is_atomic_pass_through'] else '(atomic pass-through)'
        lines.append(f"| {s['subclass_id']} | {s['n_runs_present']}/50 | {s['frequency']*100:.0f}% | "
                     f"**{s['name']}** | {parent_name[:60]} |")

    SUMMARY_MD.write_text('\n'.join(lines))
    print(f"  wrote {SUMMARY_MD}")
    print(f"\n=== SUMMARY ===")
    print(f"Canonical input:  {len(canonical)}")
    print(f"  atomic (pass through): {len(atomic)}")
    print(f"  decomposed: {len(non_atomic)} → {n_subclasses_added} sub-classes")
    print(f"Total atomic vocabulary: {len(flat_atomic)}")
    print(f"Tier counts: {tier_counts}")


if __name__ == '__main__':
    main()
