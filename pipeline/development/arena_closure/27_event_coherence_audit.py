#!/usr/bin/env python3
"""Event-coherence audit — production handoff #2.

For a stratified sample of events, ask Haiku: do the records assigned to this
event_id genuinely describe one singular occurrence (incident / decision /
programme), or were multiple distinct occurrences bundled into one event?

This tests grouping QUALITY directly, separate from grouping coverage. Open
gap from `corpora/arena/canonical/narrative/runs/README.md` production-
handoff checklist item #2.

Strata:
  A) Multi-parent events (≥4 distinct parents) — the population the causal-
     chain analysis depends on (367 events; sample 50)
  B) Medium events (3-5 records, 2-3 parents) — control (20)
  C) "Orthogonal-failure" verdicts from causal-chain test — testing whether
     orthogonal classifications correlate with bad grouping (15 of the 45)

Output: event_coherence_audit.{json,md,html}
"""
from __future__ import annotations
import json, time, random, subprocess, sys, os
from collections import defaultdict, Counter
from pathlib import Path
import anthropic

ROOT = Path(__file__).resolve().parents[2]
PER_DOC = Path('/home/jeffzda/broadlearnings/corpora/arena/output/per_doc')
FILTER_INPUT = ROOT / 'output/filter_input.jsonl'
ASSIGN_LAYERS = [
    ROOT / 'output/sweep/corpus_assignments.jsonl',
    ROOT / 'output/sweep/reclassify/reclassified_assignments.jsonl',
    ROOT / 'output/sweep/third_pass/third_pass_assignments.jsonl',
    ROOT / 'output/sweep/residual/residual_assignments.jsonl',
    ROOT / 'output/sweep/convergence/convergence_assignments.jsonl',
]
ASSIGN_PARENTS = ROOT / 'closure/output/cluster_to_parent_assignments.jsonl'
CAUSAL_CHAIN = ROOT / 'closure/output/use_case_demos/causal_chain_full.json'
OUT_DIR = ROOT / 'closure/output/use_case_demos'
OUT_JSON = OUT_DIR / 'event_coherence_audit.json'
OUT_MD = OUT_DIR / 'event_coherence_audit.md'
OUT_HTML = OUT_DIR / 'event_coherence_audit.html'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'
MODEL = 'claude-haiku-4-5-20251001'
SEED = 42

PROMPT = """# Event-coherence audit

You are auditing the quality of event-grouping in an ARENA project corpus. The grouping pass assigned each record to an event_id — a logical unit representing one singular occurrence (incident, decision, programme, milestone) within a project.

For each input event, judge whether the records grouped under that event_id genuinely describe **one singular occurrence**, or whether **multiple distinct occurrences were bundled** into the same event_id.

## What counts as one occurrence

- One technical incident (e.g. a specific commissioning failure on a specific date).
- One decision (e.g. selecting a contractor or technology).
- One sub-programme of work (e.g. a battery-deployment phase, a particular trial cohort).
- One regulatory engagement (e.g. a specific approval process for a specific asset).

**Multiple records describing different aspects of the same occurrence (cause, mechanism, intervention, outcome, lesson) all belong to one event.**

## What's bundled

- Records describing distinct technical incidents (separate failures with different timing/causes).
- Records describing different sub-projects within the same project that share no causal connection.
- Generic project-level commentary mixed with a specific incident's narrative.

## Schema

For each event return:

- `event_id`, `project` — copy from input.
- `verdict` — ONE OF: `coherent`, `partially_coherent`, `multiple_occurrences`.
- `n_distinct_occurrences_inferred` — your estimate of how many distinct occurrences the grouped records actually describe (1 = coherent; 2+ = bundled).
- `evidence` — short paragraph (≤50 words) citing record_ids; quote ≤8 words from each.
- `confidence` — `high`, `medium`, `low`.

## Output

Strict JSON. Single object:

```json
{{"events": [{{"event_id":"EVT-XXXX","project":"...","verdict":"coherent","n_distinct_occurrences_inferred":1,"evidence":"...","confidence":"high"}}]}}
```

## Input — {n_events} events

{events_block}

Return only the JSON. No commentary."""


def fmt_event(e):
    out = [f"\n### EVENT: {e['event_id']} — project: {e['project']}",
           f"  records: {len(e['records'])}, n_clusters: {e['n_clusters']}, n_parents: {e['n_parents']}, stratum: {e['stratum']}"]
    for r in e['records']:
        narr = (r.get('narrative') or '').replace('\n',' ')[:280]
        out.append(f"  [{r['record_id']}] year={r.get('year') or '?'}: {narr}")
    return '\n'.join(out)


def parse_json(raw):
    import re
    r = raw.strip()
    if r.startswith('```'):
        r = r.split('\n',1)[1]
        if r.endswith('```'): r = r.rsplit('```',1)[0]
    s, e = r.find('{'), r.rfind('}')
    if s >= 0 and e > s:
        try: return json.loads(r[s:e+1])
        except Exception: pass
    pat = re.compile(r'\{\s*"event_id"\s*:.*?"confidence"\s*:\s*"[^"]*"\s*\}', re.DOTALL)
    entries = []
    for m in pat.finditer(r):
        try: entries.append(json.loads(m.group(0)))
        except Exception: pass
    return {'events': entries} if entries else None


def main():
    random.seed(SEED)

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

    doc_year = {}
    for fn in os.listdir(PER_DOC):
        if not fn.startswith('doc_'): continue
        try: d = json.load(open(PER_DOC/fn))
        except: continue
        for rec in d.get('records',[]):
            doc_year[rec.get('id')] = rec.get('kb_year')

    # Compute event metadata
    event_meta = {}
    for evt_key, rids in event_records.items():
        clusters_set = set()
        parents_set = set()
        for rid in rids:
            cid = rid2cid.get(rid)
            if not cid: continue
            clusters_set.add(cid)
            pid = clu2par.get(cid)
            if pid: parents_set.add(pid)
        event_meta[evt_key] = {'n_records': len(rids), 'n_clusters': len(clusters_set),
                                'n_parents': len(parents_set)}

    # Stratum A: multi-parent events (≥4 parents) — sample 50
    multi_parent = [k for k, m in event_meta.items() if m['n_parents'] >= 4]
    print(f"  multi-parent events (≥4): {len(multi_parent)}")
    sample_a = random.sample(multi_parent, min(50, len(multi_parent)))

    # Stratum B: medium events (3-5 records, 2-3 parents) — sample 20
    medium = [k for k, m in event_meta.items()
              if 3 <= m['n_records'] <= 5 and 2 <= m['n_parents'] <= 3]
    print(f"  medium events: {len(medium)}")
    sample_b = random.sample(medium, min(20, len(medium)))

    # Stratum C: events flagged orthogonal_failures by causal-chain test — sample 15
    if CAUSAL_CHAIN.exists():
        cc = json.load(open(CAUSAL_CHAIN))
        orth_events = [(e['project'], e['event_id']) for e in cc['events']
                       if e.get('verdict') == 'cluster_of_orthogonal_failures'
                       and (e['project'], e['event_id']) in event_meta]
        print(f"  orthogonal-failure events: {len(orth_events)}")
        sample_c = random.sample(orth_events, min(15, len(orth_events)))
    else:
        sample_c = []

    # Combine
    samples = []
    for k in sample_a:
        samples.append((k, 'A_multi_parent'))
    for k in sample_b:
        samples.append((k, 'B_medium'))
    for k in sample_c:
        samples.append((k, 'C_orthogonal'))

    # Build payload
    events_payload = []
    for evt_key, stratum in samples:
        proj, eid = evt_key
        rids = event_records[evt_key]
        def yr(rid):
            try: return int(doc_year.get(rid) or 0)
            except: return 0
        rids_sorted = sorted(rids, key=yr)
        records = []
        for rid in rids_sorted:
            records.append({
                'record_id': rid,
                'year': doc_year.get(rid),
                'narrative': (records_data[rid].get('narrative') or '')[:280],
            })
        m = event_meta[evt_key]
        events_payload.append({
            'event_id': eid, 'project': proj,
            'stratum': stratum,
            'n_clusters': m['n_clusters'], 'n_parents': m['n_parents'],
            'records': records,
        })

    print(f"\ntotal sample: {len(events_payload)} events")

    # Batch (fewer per batch since Haiku output is shorter)
    BATCH = 25
    chunks = [events_payload[i:i+BATCH] for i in range(0, len(events_payload), BATCH)]
    print(f"  {len(chunks)} batches\n")

    client = anthropic.Anthropic()
    all_diagnoses = []
    total_cost = 0; total_wall = 0
    for i, chunk in enumerate(chunks):
        prompt = PROMPT.format(
            n_events=len(chunk),
            events_block='\n'.join(fmt_event(e) for e in chunk),
        )
        print(f"  batch {i+1}/{len(chunks)}: {len(chunk)} events, {len(prompt):,} chars", flush=True)
        started = time.time()
        parts = []
        with client.messages.stream(
            model=MODEL, max_tokens=16000,
            messages=[{"role":"user","content":prompt}],
        ) as stream:
            for ev in stream.text_stream:
                parts.append(ev)
            msg = stream.get_final_message()
        raw = ''.join(parts)
        wall = time.time() - started
        # Haiku 4.5 pricing: $1/M in, $5/M out
        cost = msg.usage.input_tokens/1e6*1 + msg.usage.output_tokens/1e6*5
        print(f"    done: {wall:.0f}s, {msg.usage.input_tokens:,}in/{msg.usage.output_tokens:,}out ${cost:.3f}, stop={msg.stop_reason}", flush=True)
        parsed = parse_json(raw)
        if parsed and parsed.get('events'):
            all_diagnoses.extend(parsed['events'])
        total_cost += cost; total_wall += wall

    # Augment with stratum
    stratum_by_id = {(e['project'], e['event_id']): e['stratum'] for e in events_payload}
    for d in all_diagnoses:
        d['stratum'] = stratum_by_id.get((d.get('project'), d.get('event_id')), 'unknown')

    print(f"\ntotal: {len(all_diagnoses)}/{len(events_payload)} diagnosed")
    print(f"cost: ${total_cost:.3f}, wall: {total_wall:.0f}s")

    # Aggregate
    by_stratum = defaultdict(Counter)
    for d in all_diagnoses:
        by_stratum[d['stratum']][d.get('verdict','?')] += 1
    overall = Counter(d.get('verdict','?') for d in all_diagnoses)

    print(f"\noverall verdict distribution: {dict(overall)}")
    print(f"\nby stratum:")
    for s, c in by_stratum.items():
        print(f"  {s}: {dict(c)}")

    json.dump({
        'n_sampled': len(events_payload),
        'n_diagnosed': len(all_diagnoses),
        'cost_sync': round(total_cost,3), 'wall_seconds': round(total_wall,1),
        'model': MODEL,
        'overall_verdicts': dict(overall),
        'by_stratum': {s: dict(c) for s, c in by_stratum.items()},
        'diagnoses': all_diagnoses,
    }, open(OUT_JSON,'w'), indent=2)

    # MD report
    md = ['# Event-coherence audit',
          '',
          f'For a stratified sample of {len(all_diagnoses)} events from the production grouping pass, asked Haiku 4.5 to judge whether the records assigned to each event_id genuinely describe **one singular occurrence**, or whether **multiple distinct occurrences were bundled** into the same event.',
          '',
          'This addresses the open production-handoff item #2 from `corpora/arena/canonical/narrative/runs/README.md`: testing grouping quality directly, separate from coverage / record-content fidelity.',
          '',
          f'**Cost:** ${total_cost:.2f}, {total_wall:.0f}s.',
          '',
          '## Strata',
          '',
          '| stratum | description | n |',
          '|---|---|---:|',
          '| A_multi_parent | events with ≥4 distinct parent archetypes (population for the causal-chain analysis) | ' + str(by_stratum['A_multi_parent'].total() if hasattr(by_stratum['A_multi_parent'],'total') else sum(by_stratum['A_multi_parent'].values())) + ' |',
          '| B_medium | 3-5 records, 2-3 parents (control) | ' + str(sum(by_stratum['B_medium'].values())) + ' |',
          '| C_orthogonal | events the causal-chain test flagged `cluster_of_orthogonal_failures` (testing whether orthogonal verdicts correlate with bad grouping) | ' + str(sum(by_stratum['C_orthogonal'].values())) + ' |',
          '',
          '## Verdict distribution overall',
          '',
          '| verdict | n | % |',
          '|---|---:|---:|']
    total = sum(overall.values())
    for v, n in overall.most_common():
        md.append(f'| {v} | {n} | {n/total*100:.0f}% |')

    md += ['', '## Verdict by stratum', '',
           '| stratum | coherent | partially_coherent | multiple_occurrences |',
           '|---|---:|---:|---:|']
    for s in ['A_multi_parent', 'B_medium', 'C_orthogonal']:
        c = by_stratum.get(s, Counter())
        n_total = sum(c.values()) or 1
        pc = lambda k: f"{c.get(k,0)} ({c.get(k,0)/n_total*100:.0f}%)"
        md.append(f"| {s} | {pc('coherent')} | {pc('partially_coherent')} | {pc('multiple_occurrences')} |")

    md += ['', '## Sample of `multiple_occurrences` verdicts (events flagged as bundled)', '']
    bundled = [d for d in all_diagnoses if d.get('verdict') == 'multiple_occurrences']
    for d in bundled[:20]:
        md.append(f"### {d.get('event_id','?')} — {d.get('project','?')} (stratum: {d.get('stratum','?')})")
        md.append('')
        md.append(f"**Inferred occurrences:** {d.get('n_distinct_occurrences_inferred','?')} · confidence: `{d.get('confidence','?')}`")
        md.append('')
        if d.get('evidence'):
            md.append(f"**Evidence:** {d['evidence']}")
            md.append('')

    OUT_MD.write_text('\n'.join(md))
    proc = subprocess.run(
        [sys.executable, MD2HTML, 'Event-coherence audit',
         f'Broad Learnings · grouping-quality validation'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    OUT_HTML.write_text(proc.stdout)

    print(f"\nwrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print(f"wrote {OUT_HTML}")


if __name__ == '__main__':
    main()
