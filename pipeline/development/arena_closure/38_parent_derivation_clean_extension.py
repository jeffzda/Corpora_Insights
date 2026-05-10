#!/usr/bin/env python3
"""Extension batch — submit 49 more reps of the deliberation-rich PM-purpose
parent derivation. Combined with rep_01 (script 36) + reps 02-10 (script 37)
gives a 59-rep ensemble — slightly more than the original 50-rep ensemble's
N for apples-to-apples-or-better cross-prompt comparison.

Same prompt, same input, same model. Output lands in the script-37 ensemble
directory under a separate raw_responses file so the final analysis can pick
up all 59 reps in one go.
"""
from __future__ import annotations
import argparse, json, time, subprocess, sys, re
from pathlib import Path
from collections import Counter, defaultdict
import statistics
import anthropic

ROOT = Path(__file__).resolve().parents[2]
PARSED_RUNS = ROOT/'closure/output/parent_ensemble/parsed_runs.jsonl'
PROMPT_FILE = ROOT/'closure/prompts/parent_derivation_clean.md'
OUT_DIR = ROOT/'closure/output/parent_derivation_clean_ensemble'

REP1_FROM_36 = ROOT/'closure/output/parent_ensemble/parent_derivation_clean.json'
REPS_2_10_RAW = OUT_DIR/'raw_responses.jsonl'
EXT_BATCH_ID_FILE = OUT_DIR/'batch_id_extension.txt'
EXT_BATCH_META_FILE = OUT_DIR/'batch_meta_extension.json'
EXT_RAW_RESPONSES = OUT_DIR/'raw_responses_extension.jsonl'
PARSED_PATH = OUT_DIR/'parsed_runs.jsonl'
AGGREGATE_JSON = OUT_DIR/'ensemble_aggregate.json'
AGGREGATE_MD = OUT_DIR/'ensemble_aggregate.md'
AGGREGATE_HTML = OUT_DIR/'ensemble_aggregate.html'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 64000
N_RUNS = 49   # rep_11 through rep_59
START_REP = 11


def build_prompt():
    runs = [json.loads(l) for l in PARSED_RUNS.open()]
    label_records = []
    for r in runs:
        run_id = r['custom_id']
        for p in r.get('parents', []):
            pid = p.get('parent_id', '')
            name = (p.get('name') or '').replace('|', '/').strip()
            crit = (p.get('mechanism_criterion') or '').replace('|', '/').replace('\n', ' ').strip()
            label_records.append(f"  [{run_id}:{pid}] {name} | {crit}")
    labels_block = '\n'.join(label_records)
    template = PROMPT_FILE.read_text()
    return template.replace('{labels_block}', labels_block), len(label_records)


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


def cmd_submit(args):
    if EXT_BATCH_ID_FILE.exists():
        print(f"! batch_id_extension exists: {EXT_BATCH_ID_FILE.read_text().strip()}")
        return 1
    prompt, n_labels = build_prompt()
    requests = [
        {'custom_id': f'rep_{START_REP+i:02d}',
         'params': {'model': MODEL, 'max_tokens': MAX_TOKENS,
                    'messages': [{'role':'user','content':prompt}]}}
        for i in range(N_RUNS)
    ]
    print(f"submitting {len(requests)} requests, prompt {len(prompt):,} chars each", flush=True)
    in_tok = len(prompt)//4
    out_tok = 8000
    sync_per = in_tok/1e6*5 + out_tok/1e6*25
    batch_per = sync_per * 0.5
    print(f"per-rep estimate: ~${sync_per:.2f} sync, ~${batch_per:.2f} batch", flush=True)
    print(f"total estimate: ~${batch_per*N_RUNS:.2f} batch", flush=True)
    client = anthropic.Anthropic()
    batch = client.messages.batches.create(requests=requests)
    EXT_BATCH_ID_FILE.write_text(batch.id)
    EXT_BATCH_META_FILE.write_text(json.dumps({
        'batch_id': batch.id,
        'submitted_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'n_requests': N_RUNS,
        'rep_range': f'{START_REP}-{START_REP+N_RUNS-1}',
        'model': MODEL, 'max_tokens': MAX_TOKENS,
        'prompt_chars': len(prompt),
    }, indent=2))
    print(f"  batch: {batch.id}, status: {batch.processing_status}", flush=True)
    return 0


def cmd_status(args):
    if not EXT_BATCH_ID_FILE.exists():
        print("no batch_id_extension"); return 1
    bid = EXT_BATCH_ID_FILE.read_text().strip()
    client = anthropic.Anthropic()
    b = client.messages.batches.retrieve(bid)
    print(f"batch {bid}: {b.processing_status}, counts: {b.request_counts}")
    return 0


def cmd_retrieve(args):
    if not EXT_BATCH_ID_FILE.exists():
        print("no batch_id_extension"); return 1
    bid = EXT_BATCH_ID_FILE.read_text().strip()
    client = anthropic.Anthropic()
    b = client.messages.batches.retrieve(bid)
    if b.processing_status != 'ended':
        print(f"batch is {b.processing_status}, not ended"); return 1
    n = 0
    with EXT_RAW_RESPONSES.open('w') as f:
        for r in client.messages.batches.results(bid):
            f.write(r.model_dump_json() + '\n'); n += 1
    print(f"wrote {n} responses to {EXT_RAW_RESPONSES}")
    return 0


def cmd_analyse(args):
    """Load all 59 reps: rep_01 + reps 02-10 + reps 11-59."""
    all_reps = []
    if REP1_FROM_36.exists():
        d = json.load(open(REP1_FROM_36))
        if 'derivation' in d:
            all_reps.append({'rep': 1, 'derivation': d['derivation'],
                             'in_tok': d.get('input_tokens'), 'out_tok': d.get('output_tokens')})

    # Load reps 02-10 from script 37's raw_responses.jsonl
    for path in [REPS_2_10_RAW, EXT_RAW_RESPONSES]:
        if not path.exists(): continue
        for line in path.open():
            d = json.loads(line)
            cid = d.get('custom_id')
            res = d.get('result', {})
            if res.get('type') != 'succeeded':
                print(f"  ! {cid} failed: {res.get('type')}")
                continue
            msg = res.get('message', {})
            text = ''.join(c.get('text','') for c in msg.get('content',[]) if c.get('type')=='text')
            usage = msg.get('usage', {})
            parsed = parse_json(text)
            if not parsed:
                (OUT_DIR/f'{cid}.raw.txt').write_text(text)
                print(f"  ! {cid} parse failed; saved raw")
                continue
            rep_id = int(cid.split('_')[1])
            all_reps.append({
                'rep': rep_id,
                'in_tok': usage.get('input_tokens',0), 'out_tok': usage.get('output_tokens',0),
                'stop_reason': msg.get('stop_reason'),
                'derivation': parsed,
            })

    all_reps.sort(key=lambda r: r['rep'])
    print(f"analysing {len(all_reps)} reps")

    with PARSED_PATH.open('w') as f:
        for r in all_reps:
            f.write(json.dumps(r) + '\n')

    n_parents = [len(r['derivation'].get('parents', [])) for r in all_reps]
    n_delib = [len(r['derivation'].get('deliberated_mechanisms', []) or []) for r in all_reps]

    parents_stats = {
        'min': min(n_parents) if n_parents else None,
        'max': max(n_parents) if n_parents else None,
        'mean': round(statistics.mean(n_parents),1) if n_parents else None,
        'median': statistics.median(n_parents) if n_parents else None,
        'sd': round(statistics.stdev(n_parents),2) if len(n_parents)>1 else 0,
        'p10': sorted(n_parents)[max(0, int(len(n_parents)*0.10))],
        'p90': sorted(n_parents)[min(len(n_parents)-1, int(len(n_parents)*0.90))],
        'values': n_parents,
    }
    delib_stats = {
        'min': min(n_delib) if n_delib else None,
        'max': max(n_delib) if n_delib else None,
        'mean': round(statistics.mean(n_delib),1) if n_delib else None,
        'sd': round(statistics.stdev(n_delib),2) if len(n_delib)>1 else 0,
        'values': n_delib,
    }

    # Cross-rep parent-name agreement via Jaccard ≥0.30
    STOP = {'and','or','of','the','to','for','a','in','on','at','by','from','as','an','vs','with','due','no','not','its'}
    def toks(s):
        return {w.lower() for w in re.findall(r"[a-zA-Z]{4,}", s) if w.lower() not in STOP}

    classes = []
    for r in all_reps:
        rep_id = r['rep']
        for p in r['derivation'].get('parents', []):
            t = toks(p.get('name',''))
            best, best_jac = None, 0
            for i, c in enumerate(classes):
                jac = len(t & c['tokens'])/max(len(t|c['tokens']),1)
                if jac > best_jac: best, best_jac = i, jac
            if best is not None and best_jac >= 0.30:
                classes[best]['runs'].add(rep_id)
                classes[best]['names'].add(p.get('name',''))
            else:
                classes.append({'tokens': t, 'runs': {rep_id}, 'names': {p.get('name','')}})
    classes.sort(key=lambda c: -len(c['runs']))
    n_reps = len(all_reps)
    tier_counts = Counter()
    for c in classes:
        f = len(c['runs'])/n_reps
        if f >= 0.9: tier_counts['core_>=90%'] += 1
        elif f >= 0.7: tier_counts['high_70-89%'] += 1
        elif f >= 0.4: tier_counts['boundary_40-69%'] += 1
        elif f >= 0.2: tier_counts['rare_20-39%'] += 1
        else: tier_counts['singleton_<20%'] += 1

    aggregate = {
        'n_reps': n_reps,
        'n_parents_per_rep_stats': parents_stats,
        'n_delib_per_rep_stats': delib_stats,
        'tier_counts': dict(tier_counts),
        'distinct_mechanism_classes': len(classes),
        'classes': [{'name_set': sorted(c['names']),
                      'n_reps_present': len(c['runs']),
                      'frequency': round(len(c['runs'])/n_reps, 2)}
                    for c in classes],
        'reps': [{'rep': r['rep'], 'n_parents': len(r['derivation'].get('parents',[])),
                  'n_delib': len(r['derivation'].get('deliberated_mechanisms',[]) or [])}
                 for r in all_reps],
    }
    AGGREGATE_JSON.write_text(json.dumps(aggregate, indent=2))

    # MD report
    md = [f'# Deliberation-rich parent-derivation ensemble — {n_reps} reps',
          '',
          f'{n_reps} single-shot Opus 4.7 derivations from the 4,150 raw parent labels of the original 50-rep ensemble. Same prompt (parent_derivation_clean.md), same input. Apples-to-apples-or-better N vs the original 50-rep untargeted ensemble.',
          '',
          '## Per-rep counts',
          '',
          '| stat | n_parents | n_deliberated |',
          '|---|---:|---:|',
          f'| min | {parents_stats["min"]} | {delib_stats["min"]} |',
          f'| max | {parents_stats["max"]} | {delib_stats["max"]} |',
          f'| mean | {parents_stats["mean"]} | {delib_stats["mean"]} |',
          f'| median | {parents_stats["median"]} | — |',
          f'| sd | {parents_stats["sd"]} | {delib_stats["sd"]} |',
          f'| p10 | {parents_stats["p10"]} | — |',
          f'| p90 | {parents_stats["p90"]} | — |',
          '',
          '## Cross-rep tier distribution (Jaccard ≥0.30 on parent names)',
          '',
          f'**Distinct mechanism classes detected across {n_reps} reps:** {len(classes)}',
          '',
          '| tier | n classes |',
          '|---|---:|']
    for t in ['core_>=90%','high_70-89%','boundary_40-69%','rare_20-39%','singleton_<20%']:
        md.append(f'| {t} | {tier_counts.get(t,0)} |')
    md.append('')
    md += ['## Comparison vs original 50-rep untargeted ensemble',
           '',
           '| | original (50 reps, untargeted prompt) | refined (this run, deliberation-rich) |',
           '|---|---:|---:|',
           f'| n_parents per rep mean | 83.0 | {parents_stats["mean"]} |',
           f'| n_parents per rep sd | 13.6 | {parents_stats["sd"]} |',
           f'| core ≥90% Jaccard classes | 1 | {tier_counts.get("core_>=90%",0)} |',
           f'| high 70-89% | 3 | {tier_counts.get("high_70-89%",0)} |',
           f'| singleton <20% | 1104 | {tier_counts.get("singleton_<20%",0)} |',
           f'| total distinct classes | 1206 | {len(classes)} |',
           '']

    md += ['## Top 50 most-recurring mechanism classes', '',
           '| n_runs | freq | name(s) |', '|---:|---:|---|']
    for c in classes[:50]:
        names = ' / '.join(sorted(c['names']))[:200]
        md.append(f'| {len(c["runs"])} | {len(c["runs"])/n_reps:.0%} | {names} |')

    AGGREGATE_MD.write_text('\n'.join(md))
    proc = subprocess.run(
        [sys.executable, MD2HTML, f'Deliberation-rich parent-derivation — {n_reps}-rep ensemble',
         f'Broad Learnings · n_parents range {parents_stats["min"]}-{parents_stats["max"]}, sd {parents_stats["sd"]}'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    AGGREGATE_HTML.write_text(proc.stdout)

    print(f"\nwrote {AGGREGATE_JSON}")
    print(f"wrote {AGGREGATE_MD}")
    print(f"\nn_parents: {parents_stats}")
    print(f"distinct classes: {len(classes)}")
    print(f"tier_counts: {dict(tier_counts)}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--submit', action='store_true')
    g.add_argument('--status', action='store_true')
    g.add_argument('--retrieve', action='store_true')
    g.add_argument('--analyse', action='store_true')
    args = ap.parse_args()
    if args.submit: return cmd_submit(args)
    if args.status: return cmd_status(args)
    if args.retrieve: return cmd_retrieve(args)
    if args.analyse: return cmd_analyse(args)


if __name__ == '__main__':
    main()
