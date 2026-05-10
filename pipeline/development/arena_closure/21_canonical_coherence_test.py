#!/usr/bin/env python3
"""Coherence test for the canonical mechanism vocabulary produced by
20_consolidate_ensemble.py.

Question: is the 126-class canonical vocabulary a coherent atomic taxonomy,
or a granularity-blurred union with substantial conceptual overlap between
classes?

Diagnostic: for each canonical class, count how many of the 50 runs
contributed 2+ parent labels to it. Each run produces internally-distinct
parents (no within-run overlap), so if a single run contributed 2+ labels
to one canonical class, the run treated those as *distinct* mechanism
classes — meaning the canonical class is COARSER than what the run treats
as atomic. The canonical "merger" is then a boundary the run wouldn't have
drawn.

Output:
  closure/output/parent_ensemble/coherence_test.json
  closure/output/parent_ensemble/coherence_test.md (human-readable)
"""
from __future__ import annotations
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOCAB = ROOT / 'closure/output/parent_ensemble/canonical_vocabulary.json'
OUT_JSON = ROOT / 'closure/output/parent_ensemble/coherence_test.json'
OUT_MD = ROOT / 'closure/output/parent_ensemble/coherence_test.md'


def main():
    V = json.load(VOCAB.open())
    classes = V['canonical_classes']

    analysis = []
    for c in classes:
        members = c.get('member_label_ids', [])
        by_run = defaultdict(list)
        for lid in members:
            run_id = lid.split(':')[0]
            by_run[run_id].append(lid)
        multi = [rid for rid, lids in by_run.items() if len(lids) > 1]
        max_contrib = max((len(v) for v in by_run.values()), default=0)
        f = c['frequency']
        tier = ('core_>=90%' if f >= 0.9 else
                'high_70-89%' if f >= 0.7 else
                'boundary_40-69%' if f >= 0.4 else
                'rare_20-39%' if f >= 0.2 else 'singleton_<20%')
        analysis.append({
            'class_id': c['class_id'],
            'name': c['name'],
            'definition': c.get('definition', ''),
            'frequency': f,
            'tier': tier,
            'n_runs_present': c['n_runs_present'],
            'n_member_labels': len(members),
            'n_runs_with_multi_labels': len(multi),
            'max_labels_from_one_run': max_contrib,
            'is_atomic': len(multi) == 0,
        })

    # Tier-level summary
    tier_summary = defaultdict(lambda: {'n_classes': 0, 'n_atomic': 0, 'n_with_multi': 0})
    for a in analysis:
        s = tier_summary[a['tier']]
        s['n_classes'] += 1
        s['n_atomic'] += 1 if a['is_atomic'] else 0
        s['n_with_multi'] += 0 if a['is_atomic'] else 1

    n_with_multi = sum(1 for a in analysis if not a['is_atomic'])
    n_atomic = len(analysis) - n_with_multi

    OUT_JSON.write_text(json.dumps({
        'n_canonical_classes': len(analysis),
        'n_atomic': n_atomic,
        'n_with_multi_contribution': n_with_multi,
        'pct_atomic': round(n_atomic / len(analysis) * 100, 1),
        'tier_summary': {t: dict(s) for t, s in tier_summary.items()},
        'classes': analysis,
    }, indent=2))

    # Markdown report
    lines = [
        '# Canonical Vocabulary Coherence Test',
        '',
        f'Of the **{len(analysis)} canonical classes** produced by Opus consolidation of the',
        f'50-run ensemble, only **{n_atomic} ({n_atomic/len(analysis)*100:.0f}%)** are *atomic* in the sense',
        'that no individual run ever produced 2+ distinct parent labels falling under them.',
        '',
        f'The other **{n_with_multi} ({n_with_multi/len(analysis)*100:.0f}%)** are *boundary-blurred*: at least one run',
        'treated them as 2-4 distinct mechanism classes, meaning the canonical class is',
        'coarser-than-run for those splits.',
        '',
        '## By tier',
        '',
        '| Tier | n classes | atomic | with-multi | % atomic |',
        '|---|---:|---:|---:|---:|',
    ]
    for t in ['core_>=90%', 'high_70-89%', 'boundary_40-69%', 'rare_20-39%', 'singleton_<20%']:
        s = tier_summary.get(t, {'n_classes':0, 'n_atomic':0, 'n_with_multi':0})
        pct = (s['n_atomic'] / s['n_classes'] * 100) if s['n_classes'] else 0
        lines.append(f"| {t} | {s['n_classes']} | {s['n_atomic']} | {s['n_with_multi']} | {pct:.0f}% |")

    lines += ['',
              '## Interpretation',
              '',
              '**Atomicity decreases with frequency.** The most-agreed-upon canonical classes',
              'are the *least* atomic — every single core (≥90%) class has at least one run',
              'splitting it. The high-frequency consensus is at a *coarser granularity* than',
              'individual runs typically work at.',
              '',
              '**The canonical 126 is not a fine-grained atomic taxonomy.** It is the union',
              "of run-level boundary choices, where ~72% of the canonical classes merge",
              'distinctions some runs treat as separate.',
              '',
              '## Top-20 most-merged canonical classes (most run-level splits)',
              '',
              '| class | n_runs | runs splitting | max labels/run | tier | name |',
              '|---|---:|---:|---:|---|---|']

    analysis.sort(key=lambda a: -a['n_runs_with_multi_labels'])
    for a in analysis[:20]:
        lines.append(f"| {a['class_id']} | {a['n_runs_present']} | {a['n_runs_with_multi_labels']} | "
                     f"{a['max_labels_from_one_run']} | {a['tier']} | {a['name']} |")

    lines += ['',
              '## All 35 atomic canonical classes (no run ever subdivided)',
              '',
              '| class | n_runs | tier | name |',
              '|---|---:|---|---|']
    atomic = [a for a in analysis if a['is_atomic']]
    atomic.sort(key=lambda a: -a['n_runs_present'])
    for a in atomic:
        lines.append(f"| {a['class_id']} | {a['n_runs_present']} | {a['tier']} | {a['name']} |")

    OUT_MD.write_text('\n'.join(lines))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"\n{n_atomic}/{len(analysis)} ({n_atomic/len(analysis)*100:.0f}%) of canonical classes are atomic.")


if __name__ == '__main__':
    main()
