#!/usr/bin/env python3
"""Causal-chain test scaled to all 225 multi-parent events.

Same prompt as 25_causal_chain_test.py but chunked into batches because
single-shot output would exceed Sonnet's 64k token cap.

Output: causal_chain_full.{json,md,html}
"""
from __future__ import annotations
import json, time, subprocess, sys, os, re
from collections import defaultdict, Counter
from pathlib import Path
import anthropic

ROOT = Path(__file__).resolve().parents[2]
PER_DOC = Path('/home/jeffzda/broadlearnings/corpora/arena/output/per_doc')
CATALOGUE = ROOT / 'output/sweep/convergence/catalogue_after_convergence.json'
PARENTS = ROOT / 'closure/output/parents_v1.json'
ASSIGN_PARENTS = ROOT / 'closure/output/cluster_to_parent_assignments.jsonl'
FILTER_INPUT = ROOT / 'output/filter_input.jsonl'
ASSIGN_LAYERS = [
    ROOT / 'output/sweep/corpus_assignments.jsonl',
    ROOT / 'output/sweep/reclassify/reclassified_assignments.jsonl',
    ROOT / 'output/sweep/third_pass/third_pass_assignments.jsonl',
    ROOT / 'output/sweep/residual/residual_assignments.jsonl',
    ROOT / 'output/sweep/convergence/convergence_assignments.jsonl',
]
OUT_DIR = ROOT / 'closure/output/use_case_demos'
OUT_JSON = OUT_DIR / 'causal_chain_full.json'
OUT_MD = OUT_DIR / 'causal_chain_full.md'
OUT_HTML = OUT_DIR / 'causal_chain_full.html'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'
MODEL = 'claude-sonnet-4-6'

BATCH_SIZE = 30
MIN_DISTINCT_PARENTS = 4


PROMPT_TEMPLATE = """# Causal-chain test on multi-mechanism events

In the ARENA project corpus, individual *events* (logical incidents within a project) sometimes produce records that land in many different mechanism clusters across multiple failure-archetype parents. The question is whether these are **causal chains** (parent A's failure causes parent B's failure) or **orthogonal failure modes** (independent things in the same project).

The diagnostic value of the v2 parent layer rests on the first answer being common.

## Input

Below are {n_events} candidate events, each with records sorted by project year showing cluster + parent + narrative excerpt.

## Task

For each event return one JSON entry:

- `event_id`, `project` — copy from input.
- `verdict` — one of:
  - `causal_chain` — parents form a sequence; earlier ones create conditions for later ones.
  - `partial_chain` — some chain, some orthogonal additions.
  - `single_root_with_multiple_consequences` — one root cause, many flat consequences.
  - `cluster_of_orthogonal_failures` — independent failure modes co-occurring.
- `reconstructed_chain` — list of `parent_id -> parent_id` arrows. Use only parent_ids given. null if orthogonal.
- `evidence` — ≤60 words citing record_ids; quote ≤8 words from each.
- `confidence` — `high`, `medium`, or `low`.

## Output

Strict JSON, no extra text:

```json
{{"events": [{{"event_id":"EVT-XXXX","project":"...","verdict":"causal_chain","reconstructed_chain":["p36 -> p37","p37 -> p23"],"evidence":"...","confidence":"high"}}]}}
```

## Input data

{events_block}

Return only the JSON. No commentary."""


def fmt_event(e):
    out = [f"\n### EVENT: {e['event_id']} — project: {e['project']}"]
    for r in e['records']:
        yr = r.get('year') or '?'
        out.append(f"  [{r['record_id']}] year={yr} cluster=[{r['cluster_id']}] {r['cluster_name']}; parent: {r['parent_id']} {r['parent_name']}")
        narr = (r.get('narrative') or '').replace('\n',' ')[:280]
        out.append(f"    narrative: {narr}")
    return '\n'.join(out)


def parse_json(raw):
    r = raw.strip()
    if r.startswith('```'):
        r = r.split('\n',1)[1]
        if r.endswith('```'): r = r.rsplit('```',1)[0]
    s, e = r.find('{'), r.rfind('}')
    if s < 0 or e <= s: return None
    try: return json.loads(r[s:e+1])
    except Exception: pass
    # Recover partial entries
    entries = []
    pattern = re.compile(r'\{\s*"event_id"\s*:.*?(?:"confidence"\s*:\s*"[^"]*")\s*\}', re.DOTALL)
    for m in pattern.finditer(r):
        try: entries.append(json.loads(m.group(0)))
        except Exception: pass
    return {'events': entries} if entries else None


def build_events():
    print("Loading data...", flush=True)
    records_data = {}
    event_records = defaultdict(list)
    for line in open(FILTER_INPUT):
        rec = json.loads(line)
        rid = rec['record_id']
        records_data[rid] = rec
        eid = rec.get('event_id'); proj = rec.get('project') or ''
        if eid and proj:
            event_records[(proj, eid)].append(rid)

    rid2cid = {}
    for f in ASSIGN_LAYERS:
        if not f.exists(): continue
        for line in open(f):
            d = json.loads(line)
            rid2cid[d['record_id']] = d.get('cluster_id')

    clu2par = {}
    for line in open(ASSIGN_PARENTS):
        a = json.loads(line)
        clu2par[a['cluster_id']] = a['parent_id']

    parents = {p['parent_id']: p for p in json.load(open(PARENTS))['parents']}
    cat = {c['cluster_id']: c for c in json.load(open(CATALOGUE))['clusters']}

    doc_year = {}
    for fn in os.listdir(PER_DOC):
        if not fn.startswith('doc_'): continue
        try: d = json.load(open(PER_DOC/fn))
        except: continue
        for rec in d.get('records',[]):
            doc_year[rec.get('id')] = rec.get('kb_year')

    # Filter: events with ≥MIN_DISTINCT_PARENTS distinct parents
    out = []
    for evt_key, rids in event_records.items():
        proj, eid = evt_key
        clusters_set = set()
        parents_set = set()
        for rid in rids:
            cid = rid2cid.get(rid)
            if not cid: continue
            clusters_set.add(cid)
            pid = clu2par.get(cid)
            if pid: parents_set.add(pid)
        if len(parents_set) < MIN_DISTINCT_PARENTS: continue

        def yr(rid):
            try: return int(doc_year.get(rid) or 0)
            except: return 0
        rids_sorted = sorted(rids, key=yr)

        records = []
        for rid in rids_sorted:
            cid = rid2cid.get(rid)
            if not cid: continue
            pid = clu2par.get(cid, '?')
            records.append({
                'record_id': rid,
                'year': doc_year.get(rid),
                'cluster_id': cid,
                'cluster_name': cat.get(cid,{}).get('canonical_name','?'),
                'parent_id': pid,
                'parent_name': parents.get(pid,{}).get('name','?'),
                'narrative': (records_data[rid].get('narrative') or '')[:300],
            })
        out.append({
            'event_id': eid, 'project': proj,
            'n_records': len(records), 'n_clusters': len(clusters_set),
            'n_parents': len(parents_set),
            'records': records,
        })
    out.sort(key=lambda e: -e['n_parents'])  # most diverse first
    return out


def call_sonnet(events_chunk, batch_idx, n_batches):
    prompt = PROMPT_TEMPLATE.format(
        n_events=len(events_chunk),
        events_block='\n'.join(fmt_event(e) for e in events_chunk),
    )
    print(f"  batch {batch_idx+1}/{n_batches}: {len(events_chunk)} events, {len(prompt):,} chars", flush=True)

    client = anthropic.Anthropic()
    started = time.time()
    parts = []
    last_print = 0; last_chars = 0; text_chars = 0
    with client.messages.stream(
        model=MODEL, max_tokens=64000,
        messages=[{"role":"user","content":prompt}],
    ) as stream:
        for ev in stream.text_stream:
            parts.append(ev); text_chars += len(ev)
            now = time.time()
            if now - last_print >= 10:
                rate = (text_chars - last_chars) / max(now - last_print, 1)
                print(f"    [{int(now-started)}s] {text_chars:,} chars +{rate:.0f} c/s", flush=True)
                last_print = now; last_chars = text_chars
        msg = stream.get_final_message()
    raw = ''.join(parts)
    wall = time.time() - started
    cost = msg.usage.input_tokens/1e6*3 + msg.usage.output_tokens/1e6*15
    print(f"    done: {wall:.0f}s, ${cost:.3f}, stop={msg.stop_reason}", flush=True)
    parsed = parse_json(raw)
    return parsed.get('events', []) if parsed else [], {
        'cost': cost, 'wall': wall,
        'in_tok': msg.usage.input_tokens, 'out_tok': msg.usage.output_tokens,
        'stop': msg.stop_reason, 'raw_chars': len(raw),
    }


def main():
    events = build_events()
    print(f"events with ≥{MIN_DISTINCT_PARENTS} distinct parents: {len(events)}", flush=True)
    print(f"running in batches of {BATCH_SIZE}", flush=True)

    chunks = [events[i:i+BATCH_SIZE] for i in range(0, len(events), BATCH_SIZE)]
    print(f"  {len(chunks)} batches\n", flush=True)

    all_diagnoses = []
    total_cost = 0; total_wall = 0
    for i, chunk in enumerate(chunks):
        diagnoses, meta = call_sonnet(chunk, i, len(chunks))
        all_diagnoses.extend(diagnoses)
        total_cost += meta['cost']; total_wall += meta['wall']
        # Save intermediate after each batch in case of crash
        json.dump({'events': all_diagnoses, 'partial': True,
                   'batches_done': i+1, 'total_batches': len(chunks)},
                  open(OUT_JSON, 'w'), indent=2)

    print(f"\ntotal: {len(all_diagnoses)}/{len(events)} events diagnosed", flush=True)
    print(f"total cost: ${total_cost:.3f}, wall: {total_wall:.0f}s", flush=True)

    # Final save
    json.dump({
        'events': all_diagnoses,
        'n_input': len(events),
        'n_diagnosed': len(all_diagnoses),
        'total_cost': round(total_cost,3),
        'total_wall_s': round(total_wall,1),
        'model': MODEL,
        'batch_size': BATCH_SIZE,
    }, open(OUT_JSON,'w'), indent=2)

    # Aggregate
    verdicts = Counter(e.get('verdict','?') for e in all_diagnoses)
    confidences = Counter(e.get('confidence','?') for e in all_diagnoses)

    # MD report
    md = ['# Causal-chain test — full corpus run',
          '',
          f'Applied the v2 parent-layer causal-chain diagnostic to **{len(all_diagnoses)} ARENA events** spanning ≥{MIN_DISTINCT_PARENTS} distinct parent archetypes each. The empirical question: do real failure events display causal-chain structure when traced through the parent layer, or are multi-parent events bundles of orthogonal failures within the same project?',
          '',
          f'**Cost:** ${total_cost:.2f}, {total_wall:.0f}s wall across {len(chunks)} batches.',
          '',
          '## Verdict distribution',
          '',
          '| verdict | n | % |',
          '|---|---:|---:|']
    total_n = len(all_diagnoses) or 1
    for v, n in verdicts.most_common():
        md.append(f'| {v} | {n} | {n/total_n*100:.0f}% |')

    md += ['', '## Confidence distribution', '',
           '| confidence | n |', '|---|---:|']
    for c, n in confidences.most_common():
        md.append(f'| {c} | {n} |')

    # Top reconstructed chains (longest)
    md += ['', '## 20 longest reconstructed chains', '']
    chain_events = [(e, len(e.get('reconstructed_chain') or [])) for e in all_diagnoses if e.get('reconstructed_chain')]
    chain_events.sort(key=lambda x: -x[1])
    for e, length in chain_events[:20]:
        md.append(f"### {e.get('event_id','?')} — {e.get('project','?')}")
        md.append('')
        md.append(f"**Verdict:** `{e.get('verdict','?')}` · confidence: `{e.get('confidence','?')}` · chain length: {length} links")
        md.append('')
        md.append('**Chain:**')
        md.append('')
        for c in e['reconstructed_chain']:
            md.append(f'- {c}')
        md.append('')
        if e.get('evidence'):
            md.append(f"**Evidence:** {e['evidence']}")
            md.append('')

    md += ['', '## All diagnoses (compact)', '',
           '| event | project | verdict | confidence | chain length |',
           '|---|---|---|---|---:|']
    for e in all_diagnoses:
        chain_len = len(e.get('reconstructed_chain') or []) if e.get('reconstructed_chain') else 0
        md.append(f"| {e.get('event_id','?')} | {(e.get('project','?') or '')[:60]} | {e.get('verdict','?')} | {e.get('confidence','?')} | {chain_len} |")

    OUT_MD.write_text('\n'.join(md))
    proc = subprocess.run(
        [sys.executable, MD2HTML, 'Causal-chain test — full corpus run',
         f'Broad Learnings · {len(all_diagnoses)} ARENA events'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    OUT_HTML.write_text(proc.stdout)

    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print(f"wrote {OUT_HTML}")
    print(f"\nverdicts: {dict(verdicts)}")
    print(f"confidences: {dict(confidences)}")


if __name__ == '__main__':
    main()
