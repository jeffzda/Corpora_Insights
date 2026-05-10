#!/usr/bin/env python3
"""Run 9 additional reps of the clean threshold-selection judgement to
characterise variance. Combined with the rep-1 result already on disk,
gives a 10-rep ensemble.

Synchronous sequential calls (Opus 4.7, ~$0.11 each, ~30s each, 9 calls
≈ $1 / 5 min wall). Parses each response, aggregates cross-rep statistics,
and writes the analysis to disk.

Output:
  closure/output/parent_ensemble/threshold_judgement_ensemble.{json,md,html}
  closure/output/parent_ensemble/threshold_judgement_rep_NN.{json,raw.txt}
"""
from __future__ import annotations
import json, time, subprocess, sys, re
from pathlib import Path
from collections import Counter, defaultdict
import statistics
import anthropic

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT/'closure/output/parent_ensemble/canonical_vocabulary.json'
PROMPT_FILE = ROOT/'closure/prompts/threshold_selection.md'
OUT_DIR = ROOT/'closure/output/parent_ensemble'
OUT_JSON = OUT_DIR/'threshold_judgement_ensemble.json'
OUT_MD = OUT_DIR/'threshold_judgement_ensemble.md'
OUT_HTML = OUT_DIR/'threshold_judgement_ensemble.html'
EXISTING_REP1 = OUT_DIR/'threshold_judgement.json'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 32000
N_NEW_REPS = 9   # rep_02 through rep_10
START_REP = 2


def parse_json(raw):
    r = raw.strip()
    if r.startswith('```'):
        r = r.split('\n',1)[1]
        if r.endswith('```'): r = r.rsplit('```',1)[0]
    s, e = r.find('{'), r.rfind('}')
    if s>=0 and e>s:
        try: return json.loads(r[s:e+1])
        except Exception: pass
    return None


def main():
    canonical = json.load(CANONICAL.open())['canonical_classes']
    sorted_classes = sorted(canonical, key=lambda c: -c['frequency'])

    # Build canonical_block (same as 33)
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
    print(f"running {N_NEW_REPS} additional reps with {MODEL}...\n", flush=True)
    rep_results = []
    total_cost = 0; total_wall = 0
    for i in range(N_NEW_REPS):
        rep_id = START_REP + i  # rep_02..rep_10
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

        # Save raw
        raw_path = OUT_DIR/f'threshold_judgement_rep_{rep_id:02d}.raw.txt'
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
        # Save per-rep json
        rep_json = OUT_DIR/f'threshold_judgement_rep_{rep_id:02d}.json'
        rep_json.write_text(json.dumps(rep_results[-1], indent=2))
        thr = parsed.get('recommended_threshold')
        nc = parsed.get('n_classes_included')
        print(f"  done: {wall:.0f}s, ${cost:.3f}, threshold={thr}, n_classes={nc}", flush=True)

    print(f"\nTotal cost: ${total_cost:.3f}, wall {total_wall:.0f}s\n", flush=True)

    # ---- Cross-rep analysis ----
    # Load rep-1 from existing file
    all_reps = []
    if EXISTING_REP1.exists():
        rep1 = json.load(open(EXISTING_REP1))
        rep1_normalised = {
            'rep': 1,
            'cost': rep1.get('cost_sync'),
            'wall': rep1.get('wall_seconds'),
            'judgement': rep1.get('judgement', {}),
        }
        all_reps.append(rep1_normalised)
    all_reps.extend(r for r in rep_results if 'judgement' in r)
    print(f"Aggregating {len(all_reps)} reps total (incl. existing rep_01)", flush=True)

    # Threshold distribution
    thresholds = [r['judgement'].get('recommended_threshold') for r in all_reps if r['judgement'].get('recommended_threshold') is not None]
    n_classes = [r['judgement'].get('n_classes_included') for r in all_reps if r['judgement'].get('n_classes_included') is not None]

    threshold_stats = {
        'n_reps': len(thresholds),
        'min': min(thresholds) if thresholds else None,
        'max': max(thresholds) if thresholds else None,
        'mean': round(statistics.mean(thresholds), 3) if thresholds else None,
        'median': statistics.median(thresholds) if thresholds else None,
        'sd': round(statistics.stdev(thresholds), 3) if len(thresholds)>1 else 0,
        'values': thresholds,
    }
    n_classes_stats = {
        'min': min(n_classes) if n_classes else None,
        'max': max(n_classes) if n_classes else None,
        'mean': round(statistics.mean(n_classes), 1) if n_classes else None,
        'median': statistics.median(n_classes) if n_classes else None,
        'sd': round(statistics.stdev(n_classes), 1) if len(n_classes)>1 else 0,
        'values': n_classes,
    }

    # Borderline-class agreement: which classes show up across reps' borderline lists?
    # Tally include/exclude verdicts per class_id
    bc_verdicts = defaultdict(lambda: {'include':0, 'exclude':0, 'mentions':0, 'reasons': []})
    for r in all_reps:
        for b in r['judgement'].get('borderline_classes', []) or []:
            cid = b.get('class_id')
            if not cid: continue
            v = b.get('verdict','').lower().strip()
            bc_verdicts[cid]['mentions'] += 1
            if 'include' in v: bc_verdicts[cid]['include'] += 1
            elif 'exclude' in v: bc_verdicts[cid]['exclude'] += 1
            if b.get('reason'):
                bc_verdicts[cid]['reasons'].append(b['reason'])

    # For each class, compute "passes threshold" rate across reps (i.e. it's above the recommended threshold in this rep)
    canonical_by_id = {c['class_id']: c for c in canonical}
    above_threshold_count = Counter()
    for r in all_reps:
        thr = r['judgement'].get('recommended_threshold')
        if thr is None: continue
        for c in canonical:
            if c['frequency'] >= thr:
                above_threshold_count[c['class_id']] += 1

    # Classes consistently above threshold across all reps
    n_reps = len(all_reps)
    consistent_above = [cid for cid, n in above_threshold_count.items() if n == n_reps]
    contested = [(cid, n) for cid, n in above_threshold_count.items() if 0 < n < n_reps]
    contested.sort(key=lambda x: -x[1])

    # Save aggregate
    aggregate = {
        'n_reps': len(all_reps),
        'total_cost': round(total_cost, 3),
        'total_wall_seconds': round(total_wall, 1),
        'threshold_stats': threshold_stats,
        'n_classes_stats': n_classes_stats,
        'borderline_verdicts': {cid: dict(v) for cid, v in bc_verdicts.items()},
        'consistent_above_threshold': consistent_above,
        'n_consistent': len(consistent_above),
        'contested_classes': [{'class_id': cid, 'n_above': n,
                                'frequency': canonical_by_id[cid]['frequency'],
                                'name': canonical_by_id[cid]['name']}
                              for cid, n in contested],
        'reps': [{'rep': r['rep'],
                  'threshold': r['judgement'].get('recommended_threshold'),
                  'n_classes': r['judgement'].get('n_classes_included'),
                  'rationale_excerpt': (r['judgement'].get('rationale','') or '')[:200],
                  'borderline': r['judgement'].get('borderline_classes', []),
                  'notes_excerpt': (r['judgement'].get('notes','') or '')[:300]}
                  for r in all_reps],
    }
    OUT_JSON.write_text(json.dumps(aggregate, indent=2))

    # Build MD
    md = ['# Threshold-judgement ensemble — 10 reps',
          '',
          f'10 single-shot Opus 4.7 judgements on the same 126-canonical-class input. Same prompt, same model, no temperature variation. Tests how reproducible the threshold-selection judgement is across reps.',
          '',
          f'**Total cost (rep 02-10):** ${total_cost:.2f}, {total_wall:.0f}s wall.',
          '',
          '## Threshold distribution across 10 reps',
          '',
          '| stat | value |',
          '|---|---:|',
          f'| n_reps | {threshold_stats["n_reps"]} |',
          f'| min | {threshold_stats["min"]} |',
          f'| max | {threshold_stats["max"]} |',
          f'| mean | {threshold_stats["mean"]} |',
          f'| median | {threshold_stats["median"]} |',
          f'| sd | {threshold_stats["sd"]} |',
          '',
          f'**All threshold values:** {", ".join(f"{t:.0%}" for t in thresholds)}',
          '',
          '## n_classes distribution',
          '',
          '| stat | value |',
          '|---|---:|',
          f'| min | {n_classes_stats["min"]} |',
          f'| max | {n_classes_stats["max"]} |',
          f'| mean | {n_classes_stats["mean"]} |',
          f'| median | {n_classes_stats["median"]} |',
          f'| sd | {n_classes_stats["sd"]} |',
          '',
          f'**All n_classes values:** {", ".join(str(n) for n in n_classes)}',
          '',
          '## Per-rep recommendations',
          '',
          '| rep | threshold | n_classes | rationale excerpt |',
          '|---:|---:|---:|---|']
    for r in all_reps:
        j = r['judgement']
        rat = (j.get('rationale','') or '').replace('\n',' ')[:150]
        md.append(f"| {r['rep']} | {j.get('recommended_threshold','?')} | {j.get('n_classes_included','?')} | {rat}... |")

    md += ['',
           '## Cross-rep agreement on inclusion',
           '',
           f'**Classes ABOVE threshold in ALL {n_reps} reps:** {len(consistent_above)} (the consensus parent set)',
           '',
           f'**Contested classes** (above-threshold in some reps but not all): {len(contested)}',
           '',
           '| class | n above | freq | name |',
           '|---|---:|---:|---|']
    for c in aggregate['contested_classes'][:30]:
        md.append(f"| {c['class_id']} | {c['n_above']}/{n_reps} | {c['frequency']:.0%} | {c['name']} |")
    md.append('')

    # Borderline class agreement
    md += ['## Borderline-class verdicts across reps',
           '',
           'Classes raised by at least one rep in its borderline set, with cross-rep verdict tally:',
           '',
           '| class | freq | mentions | include / exclude | name |',
           '|---|---:|---:|---:|---|']
    border_sorted = sorted(bc_verdicts.items(), key=lambda kv: -kv[1]['mentions'])
    for cid, v in border_sorted[:25]:
        if cid not in canonical_by_id: continue
        c = canonical_by_id[cid]
        md.append(f"| {cid} | {c['frequency']:.0%} | {v['mentions']}/{n_reps} | {v['include']} / {v['exclude']} | {c['name']} |")
    md.append('')

    md += ['## Headline read',
           '',
           f'Threshold variance across {n_reps} reps: range [{threshold_stats["min"]}, {threshold_stats["max"]}], mean {threshold_stats["mean"]}, sd {threshold_stats["sd"]}.',
           '',
           f'n_classes variance: range [{n_classes_stats["min"]}, {n_classes_stats["max"]}], mean {n_classes_stats["mean"]:.1f}, sd {n_classes_stats["sd"]}.',
           '',
           f'**Consensus parent set** (above-threshold in every rep): {len(consistent_above)} classes.',
           f'**Contested boundary** (above in some reps but not all): {len(contested)} classes.',
           '',
           'The consensus set is the methodologically-defensible v2 candidate. The contested set is where the override-list discussion happens — these are the classes that need explicit per-class judgement rather than mechanical threshold application.',
           '']

    OUT_MD.write_text('\n'.join(md))
    proc = subprocess.run(
        [sys.executable, MD2HTML, 'Threshold-judgement ensemble — 10 reps',
         'Broad Learnings · cross-rep variance characterisation'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    OUT_HTML.write_text(proc.stdout)

    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print(f"wrote {OUT_HTML}")
    print(f"\nthreshold range: {threshold_stats['min']}–{threshold_stats['max']}")
    print(f"n_classes range: {n_classes_stats['min']}–{n_classes_stats['max']}")
    print(f"consensus above-threshold across all reps: {len(consistent_above)}")
    print(f"contested: {len(contested)}")


if __name__ == '__main__':
    main()
