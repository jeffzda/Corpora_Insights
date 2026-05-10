#!/usr/bin/env python3
"""Category-selection ensemble — 10 reps of direct per-class selection without
threshold framing. Same model, same input, same PM-purpose framing as the
threshold-judgement ensemble (33/34); the only difference is the prompt asks
the model to pick canonical classes directly rather than recommend a frequency
threshold.

Pairs with 34_threshold_judgement_ensemble.py — same 126 canonical classes,
same Opus 4.7, same single-shot pattern. Cross-comparison surfaces whether
selection-mode produces tighter / looser / more-or-less-stable parent sets
than threshold-mode.

Output:
  closure/output/parent_ensemble/category_selection_ensemble.{json,md,html}
  closure/output/parent_ensemble/category_selection_rep_NN.{json,raw.txt}
"""
from __future__ import annotations
import json, time, subprocess, sys
from pathlib import Path
from collections import Counter, defaultdict
import statistics
import anthropic

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT/'closure/output/parent_ensemble/canonical_vocabulary.json'
PROMPT_FILE = ROOT/'closure/prompts/category_selection.md'
OUT_DIR = ROOT/'closure/output/parent_ensemble'
OUT_JSON = OUT_DIR/'category_selection_ensemble.json'
OUT_MD = OUT_DIR/'category_selection_ensemble.md'
OUT_HTML = OUT_DIR/'category_selection_ensemble.html'
THRESHOLD_ENSEMBLE = OUT_DIR/'threshold_judgement_ensemble.json'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 32000
N_REPS = 10


def parse_json(raw):
    r = raw.strip()
    if r.startswith('```'):
        r = r.split('\n',1)[1]
        if r.endswith('```'): r = r.rsplit('```',1)[0]
    s, e = r.find('{'), r.rfind('}')
    if s>=0 and e>s:
        try: return json.loads(r[s:e+1])
        except Exception as ex: print(f"parse error: {ex}")
    return None


def main():
    canonical = json.load(CANONICAL.open())['canonical_classes']
    sorted_classes = sorted(canonical, key=lambda c: -c['frequency'])
    canonical_by_id = {c['class_id']: c for c in canonical}

    lines = []
    for c in sorted_classes:
        cid = c['class_id']
        freq = c['frequency']
        name = (c.get('name') or '').strip()
        defn = (c.get('definition') or '').strip().replace('\n',' ')
        crit = (c.get('mechanism_criterion') or '').strip().replace('\n',' ')
        lines.append(f"[{cid}] freq={freq:.0%} — {name} :: {defn} :: {crit}")
    canonical_block = '\n'.join(lines)
    template = PROMPT_FILE.read_text()
    prompt = template.replace('{canonical_block}', canonical_block)
    print(f"prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"running {N_REPS} reps with {MODEL}...\n", flush=True)
    rep_results = []
    total_cost = 0; total_wall = 0
    for i in range(N_REPS):
        rep_id = i + 1
        print(f"--- rep_{rep_id:02d} ---", flush=True)
        started = time.time()
        parts = []
        with client.messages.stream(
            model=MODEL, max_tokens=MAX_TOKENS,
            messages=[{"role":"user","content":prompt}],
        ) as stream:
            for ev in stream.text_stream:
                parts.append(ev)
            msg = stream.get_final_message()
        raw = ''.join(parts)
        wall = time.time() - started
        cost = msg.usage.input_tokens/1e6*5 + msg.usage.output_tokens/1e6*25
        total_cost += cost; total_wall += wall
        raw_path = OUT_DIR/f'category_selection_rep_{rep_id:02d}.raw.txt'
        raw_path.write_text(raw)
        parsed = parse_json(raw)
        if not parsed:
            print(f"  PARSE FAILED on rep_{rep_id:02d}; raw at {raw_path}", flush=True)
            rep_results.append({'rep': rep_id, 'parse_failed': True, 'cost': cost, 'wall': wall})
            continue
        rep_results.append({
            'rep': rep_id, 'cost': round(cost,3), 'wall': round(wall,1),
            'in_tok': msg.usage.input_tokens, 'out_tok': msg.usage.output_tokens,
            'judgement': parsed,
        })
        rep_json = OUT_DIR/f'category_selection_rep_{rep_id:02d}.json'
        rep_json.write_text(json.dumps(rep_results[-1], indent=2))
        ns = parsed.get('n_selected')
        print(f"  done: {wall:.0f}s, ${cost:.3f}, n_selected={ns}", flush=True)

    print(f"\nTotal cost: ${total_cost:.3f}, wall {total_wall:.0f}s\n", flush=True)

    # ---- Cross-rep analysis ----
    valid_reps = [r for r in rep_results if 'judgement' in r]
    n_reps = len(valid_reps)

    n_selected = [r['judgement'].get('n_selected') for r in valid_reps if r['judgement'].get('n_selected') is not None]

    n_selected_stats = {
        'n_reps': n_reps,
        'min': min(n_selected) if n_selected else None,
        'max': max(n_selected) if n_selected else None,
        'mean': round(statistics.mean(n_selected),1) if n_selected else None,
        'median': statistics.median(n_selected) if n_selected else None,
        'sd': round(statistics.stdev(n_selected),1) if len(n_selected)>1 else 0,
        'values': n_selected,
    }

    # Cross-rep selection rate per class
    selection_count = Counter()
    for r in valid_reps:
        sel = r['judgement'].get('selected_class_ids', [])
        for cid in sel:
            selection_count[cid] += 1

    consensus_selected = [cid for cid, n in selection_count.items() if n == n_reps]
    contested = [(cid, n) for cid, n in selection_count.items() if 0 < n < n_reps]
    contested.sort(key=lambda x: -x[1])

    # Classes never selected
    never_selected = [cid for cid in canonical_by_id if cid not in selection_count and cid != 'none']

    # Deliberated-class verdicts (cross-rep)
    delib_verdicts = defaultdict(lambda: {'include':0, 'exclude':0, 'mentions':0, 'reasons':[]})
    for r in valid_reps:
        for d in r['judgement'].get('deliberated_classes', []) or []:
            cid = d.get('class_id')
            if not cid: continue
            v = (d.get('verdict','') or '').lower().strip()
            delib_verdicts[cid]['mentions'] += 1
            if 'include' in v: delib_verdicts[cid]['include'] += 1
            elif 'exclude' in v: delib_verdicts[cid]['exclude'] += 1
            if d.get('reason'):
                delib_verdicts[cid]['reasons'].append(d['reason'])

    # Compare to threshold ensemble
    threshold_consensus = []
    threshold_n_classes_stats = None
    if THRESHOLD_ENSEMBLE.exists():
        td = json.load(open(THRESHOLD_ENSEMBLE))
        threshold_consensus = td.get('consistent_above_threshold', [])
        threshold_n_classes_stats = td.get('n_classes_stats')

    # Build aggregate
    aggregate = {
        'n_reps': n_reps,
        'total_cost': round(total_cost, 3),
        'total_wall_seconds': round(total_wall, 1),
        'n_selected_stats': n_selected_stats,
        'consensus_selected': consensus_selected,
        'n_consensus': len(consensus_selected),
        'contested_classes': [{'class_id': cid, 'n_selected': n,
                                'frequency': canonical_by_id[cid]['frequency'],
                                'name': canonical_by_id[cid]['name']}
                              for cid, n in contested],
        'never_selected_classes': never_selected,
        'deliberated_verdicts': {cid: dict(v) for cid, v in delib_verdicts.items()},
        'reps': [{'rep': r['rep'],
                  'n_selected': r['judgement'].get('n_selected'),
                  'rationale_excerpt': (r['judgement'].get('rationale','') or '')[:200],
                  'deliberated': r['judgement'].get('deliberated_classes', []),
                  'notes_excerpt': (r['judgement'].get('notes','') or '')[:300]}
                  for r in valid_reps],
    }
    OUT_JSON.write_text(json.dumps(aggregate, indent=2))

    md = ['# Category-selection ensemble — 10 reps (no threshold framing)',
          '',
          f'10 single-shot Opus 4.7 judgements asking the model to **directly select** the canonical classes that best serve the PM-facing diagnostic vocabulary purpose. No threshold variable in the prompt — the model makes per-class judgements without the pressure of finding a frequency cutoff.',
          '',
          'Pairs with the threshold-judgement ensemble (script 34) — same 126 input classes, same model, same PM-purpose framing. Comparison below.',
          '',
          f'**Total cost:** ${total_cost:.2f}, {total_wall:.0f}s wall.',
          '',
          '## n_selected distribution across 10 reps',
          '',
          '| stat | value |',
          '|---|---:|',
          f'| n_reps | {n_selected_stats["n_reps"]} |',
          f'| min | {n_selected_stats["min"]} |',
          f'| max | {n_selected_stats["max"]} |',
          f'| mean | {n_selected_stats["mean"]} |',
          f'| median | {n_selected_stats["median"]} |',
          f'| sd | {n_selected_stats["sd"]} |',
          '',
          f'**All n_selected values:** {", ".join(str(n) for n in n_selected)}',
          '',
          ]

    if threshold_n_classes_stats:
        md += ['## Comparison to threshold-judgement ensemble',
               '',
               '| stat | threshold-mode | selection-mode |',
               '|---|---:|---:|',
               f'| min | {threshold_n_classes_stats["min"]} | {n_selected_stats["min"]} |',
               f'| max | {threshold_n_classes_stats["max"]} | {n_selected_stats["max"]} |',
               f'| mean | {threshold_n_classes_stats["mean"]} | {n_selected_stats["mean"]} |',
               f'| median | {threshold_n_classes_stats["median"]} | {n_selected_stats["median"]} |',
               f'| sd | {threshold_n_classes_stats["sd"]} | {n_selected_stats["sd"]} |',
               '',
               f'**Threshold-mode consensus (above-threshold in all 10 reps):** {len(threshold_consensus)} classes',
               f'**Selection-mode consensus (selected in all 10 reps):** {len(consensus_selected)} classes',
               '']
        # Class-level overlap between consensuses
        overlap = set(threshold_consensus) & set(consensus_selected)
        only_threshold = set(threshold_consensus) - set(consensus_selected)
        only_selection = set(consensus_selected) - set(threshold_consensus)
        md += [f'**Consensus overlap:** {len(overlap)} classes in both consensus sets',
               f'**Only-threshold-consensus:** {len(only_threshold)} classes',
               f'**Only-selection-consensus:** {len(only_selection)} classes',
               '']

    md += ['## Per-rep recommendations',
           '',
           '| rep | n_selected | rationale excerpt |',
           '|---:|---:|---|']
    for r in valid_reps:
        j = r['judgement']
        rat = (j.get('rationale','') or '').replace('\n',' ')[:150]
        md.append(f"| {r['rep']} | {j.get('n_selected','?')} | {rat}... |")

    md += ['',
           '## Cross-rep agreement on selection',
           '',
           f'**Classes selected in ALL {n_reps} reps:** {len(consensus_selected)}',
           '',
           f'**Contested classes** (selected in some reps but not all): {len(contested)}',
           '',
           '| class | n selected | freq | name |',
           '|---|---:|---:|---|']
    for c in aggregate['contested_classes'][:30]:
        md.append(f"| {c['class_id']} | {c['n_selected']}/{n_reps} | {c['frequency']:.0%} | {c['name']} |")
    md.append('')

    md += [f'**Classes never selected (across {n_reps} reps):** {len(never_selected)}', '']

    md += ['## Deliberated-class verdicts (model-flagged borderline)',
           '',
           '| class | freq | mentions | include / exclude | name |',
           '|---|---:|---:|---:|---|']
    delib_sorted = sorted(delib_verdicts.items(), key=lambda kv: -kv[1]['mentions'])
    for cid, v in delib_sorted[:25]:
        if cid not in canonical_by_id: continue
        c = canonical_by_id[cid]
        md.append(f"| {cid} | {c['frequency']:.0%} | {v['mentions']}/{n_reps} | {v['include']} / {v['exclude']} | {c['name']} |")
    md.append('')

    md += ['## Headline read',
           '',
           f'n_selected variance across {n_reps} reps: range [{n_selected_stats["min"]}, {n_selected_stats["max"]}], mean {n_selected_stats["mean"]}, sd {n_selected_stats["sd"]}.',
           '',
           f'**Consensus selected set** (in every rep): {len(consensus_selected)} classes — the methodologically-defensible v2 candidate set under selection-mode.',
           f'**Contested boundary**: {len(contested)} classes selected in some reps but not all.',
           f'**Never selected**: {len(never_selected)} classes the model agreed to exclude.',
           '',
           'If the selection-mode consensus differs from the threshold-mode consensus (script 34), that\'s the more interesting finding — it shows the framing of the task changes which classes get included, beyond just changing the cutoff.',
           '']

    OUT_MD.write_text('\n'.join(md))
    proc = subprocess.run(
        [sys.executable, MD2HTML, 'Category-selection ensemble — 10 reps (no threshold)',
         'Broad Learnings · direct-selection vs threshold-driven comparison'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    OUT_HTML.write_text(proc.stdout)

    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print(f"wrote {OUT_HTML}")
    print(f"\nn_selected range: {n_selected_stats['min']}–{n_selected_stats['max']}")
    print(f"consensus selected: {len(consensus_selected)}")
    print(f"contested: {len(contested)}")
    print(f"never selected: {len(never_selected)}")
    if threshold_consensus:
        ov = len(set(threshold_consensus) & set(consensus_selected))
        print(f"consensus overlap with threshold-mode: {ov}")


if __name__ == '__main__':
    main()
