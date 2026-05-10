#!/usr/bin/env python3
"""Classify ANAO N=100 records into v2 extended parent taxonomy.

Stratified sample of 500 records (100 per era band) classified against
the 86-parent v2 extended set in a single Opus 4.7 call.

Demonstrates: does the v2 parent taxonomy (derived purely from ARENA)
generalise to ANAO performance audit findings? Output is the parent-fit
distribution + `none` rate + per-era stability.
"""
from __future__ import annotations
import json, time, random
from collections import Counter, defaultdict
from pathlib import Path
import anthropic

ROOT = Path('/home/jeffzda/broadlearnings')
RECORDS = ROOT/'corpora/anao/n100_demo/output/anao_n100_records_recovered.jsonl'
PARENTS = ROOT/'corpora/arena/clustering_v2/closure/output/parent_derivation_clean_ensemble/v2_parents_extended.json'
OUT_DIR = ROOT/'corpora/anao/n100_demo/output'
OUT_RAW = OUT_DIR/'anao_n100_classify_to_v2.raw.txt'
OUT = OUT_DIR/'anao_n100_classify_to_v2.json'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 32000
SAMPLE_PER_ERA = 100
SEED = 7


PROMPT = """# ANAO record → v2 parent classification

You are classifying ANAO performance-audit-derived records into the v2 extended parent taxonomy.

## Background

The v2 taxonomy is an 86-parent failure-mechanism hierarchy derived from the ARENA Knowledge Bank corpus (clean-energy government project documents). The taxonomy was developed purely on ARENA. Your task: classify a stratified sample of ANAO records (cross-government performance audit findings) against this rubric to test whether the v2 parents generalise.

## Task

For each ANAO record, pick the v2 parent whose `mechanism_criterion` the record best instantiates, OR return `parent_id: "none"` if no parent fits.

- **Mechanism, not topic.** A finding about a different domain that fails through the same mechanism still belongs in the parent.
- **Be willing to call `none` and `low` confidence.** Forcing a fit corrupts the test of generalisability. We want to know honestly which v2 parents transfer to ANAO and which don't.
- Use the exact parent_id from the rubric below (e.g. `p07`).

For each record, output {{record_id, parent_id, confidence (high|medium|low), rationale}}. Rationale ≤ 20 words.

## Output

Strict JSON, one line top-level field `assignments`:

```json
{{
  "assignments": [
    {{"record_id": "<from input>", "parent_id": "<pNN or none>", "confidence": "high|medium|low", "rationale": "<≤20 words>"}}
  ]
}}
```

Output every input record. {n_records} input → {n_records} output.

## v2 parent rubric

{parent_block}

## ANAO records to classify ({n_records} records)

Each entry: `record_id | era | narrative | lesson`

{records_block}
"""


def main():
    random.seed(SEED)
    parents = json.load(PARENTS.open())['extended']['parents']
    valid_pids = {p['parent_id'] for p in parents}
    print(f'parents: {len(parents)}', flush=True)

    all_recs = [json.loads(l) for l in RECORDS.open()]
    print(f'total records: {len(all_recs)}', flush=True)

    # Stratify by era
    by_era = defaultdict(list)
    for r in all_recs:
        e = r.get('_era')
        if e: by_era[e].append(r)

    sample = []
    for e, lst in by_era.items():
        n = min(SAMPLE_PER_ERA, len(lst))
        sample.extend(random.sample(lst, n))
    print(f'sampled: {len(sample)} ({len(by_era)} eras)', flush=True)

    # Build prompt
    parent_lines = []
    for p in parents:
        parent_lines.append(f"### {p['parent_id']}: {p['name']}")
        parent_lines.append(f"Mechanism criterion: {p.get('mechanism_criterion','')}")
        parent_lines.append('')
    parent_block = '\n'.join(parent_lines)

    record_lines = []
    for r in sample:
        rid = r.get('id','?')
        era = r.get('_era','?')
        narr = (r.get('narrative') or '').replace('|','/').replace('\n',' ')[:300]
        less = (r.get('lesson') or '').replace('|','/').replace('\n',' ')[:200]
        record_lines.append(f"  {rid} | {era} | {narr} | {less}")
    records_block = '\n'.join(record_lines)

    prompt = PROMPT.format(n_records=len(sample), parent_block=parent_block, records_block=records_block)
    print(f'prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tok)', flush=True)

    client = anthropic.Anthropic()
    print(f'calling {MODEL}...', flush=True)
    started = time.time()
    parts = []
    last_print, last_chars, text_chars = 0, 0, 0
    with client.messages.stream(model=MODEL, max_tokens=MAX_TOKENS, messages=[{'role':'user','content':prompt}]) as stream:
        for ev in stream.text_stream:
            parts.append(ev); text_chars += len(ev)
            now = time.time()
            if now - last_print >= 5:
                rate = (text_chars-last_chars)/max(now-last_print,1)
                print(f'  [{int(now-started)}s] {text_chars:,} chars +{rate:.0f} c/s', flush=True)
                last_print, last_chars = now, text_chars
        msg = stream.get_final_message()
    raw = ''.join(parts)
    OUT_RAW.write_text(raw)
    wall = time.time()-started
    cost = msg.usage.input_tokens/1e6*5 + msg.usage.output_tokens/1e6*25
    print(f'done: {wall:.0f}s {msg.usage.input_tokens:,}in/{msg.usage.output_tokens:,}out ${cost:.3f}', flush=True)

    # parse
    t = raw.strip()
    if t.startswith('```'):
        t = t.split('\n',1)[1]
        if t.endswith('```'): t = t.rsplit('```',1)[0]
    s,e = t.find('{'), t.rfind('}')
    parsed = json.loads(t[s:e+1])
    assigns = parsed.get('assignments', [])
    print(f'returned {len(assigns)} assignments (input {len(sample)})', flush=True)

    bad = [a for a in assigns if a.get('parent_id') not in valid_pids and a.get('parent_id')!='none']
    if bad: print(f'! {len(bad)} bad parent_ids: {[a.get("parent_id") for a in bad[:5]]}', flush=True)

    # Build per-record meta map
    rec_by_id = {r['id']: r for r in sample if 'id' in r}
    for a in assigns:
        rid = a.get('record_id')
        if rid in rec_by_id:
            a['_era'] = rec_by_id[rid].get('_era')

    pid_dist = Counter(a.get('parent_id') for a in assigns)
    conf_dist = Counter(a.get('confidence') for a in assigns)
    none_count = pid_dist.get('none', 0)
    none_rate = none_count / len(assigns) if assigns else 0

    # Per-era none rate
    by_era_assign = defaultdict(list)
    for a in assigns:
        if a.get('_era'): by_era_assign[a['_era']].append(a)
    per_era_none = {}
    for era, items in by_era_assign.items():
        n_none = sum(1 for a in items if a.get('parent_id')=='none')
        per_era_none[era] = {'n': len(items), 'none_rate': round(n_none/len(items)*100,1) if items else 0}

    print(f'\n=== distribution ===')
    print(f'none rate overall: {none_rate*100:.1f}% ({none_count}/{len(assigns)})')
    print(f'confidence: {dict(conf_dist)}')
    print(f'\nper-era none rate:')
    for era in sorted(per_era_none):
        d = per_era_none[era]
        print(f"  {era}: {d['n']} records, none {d['none_rate']}%")

    parents_used = sorted(set(pid_dist.keys()) - {'none', None, '?'})
    print(f'\nparents used: {len(parents_used)} of {len(parents)} v2 parents')
    print('\ntop 15 parents by ANAO-record count:')
    for pid, n in pid_dist.most_common(15):
        if pid in (None, 'none', '?'): continue
        pname = next((p['name'] for p in parents if p['parent_id']==pid), pid)
        print(f'  {n:>4}  [{pid}] {pname}')

    json.dump({
        'model': MODEL, 'cost_usd': round(cost,4), 'wall_seconds': round(wall,1),
        'input_tokens': msg.usage.input_tokens, 'output_tokens': msg.usage.output_tokens,
        'n_records_input': len(sample),
        'n_assignments_output': len(assigns),
        'none_rate': round(none_rate, 4),
        'parents_used': len(parents_used),
        'parent_distribution': dict(pid_dist),
        'confidence_distribution': dict(conf_dist),
        'per_era_none_rate': per_era_none,
        'assignments': assigns,
    }, OUT.open('w'), indent=2)
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
