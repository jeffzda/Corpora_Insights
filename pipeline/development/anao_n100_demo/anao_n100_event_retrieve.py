#!/usr/bin/env python3
"""Retrieve and parse ANAO event-derivation batch results.

Joins per-doc events into a corpus-wide registry with doc-prefixed
event_ids to avoid collision (each doc's EVT-NNNN namespace is local).
"""
from __future__ import annotations
import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import anthropic

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = ROOT/'corpora/anao/n100_demo/output'
BATCH_ID_FILE = OUT_DIR/'anao_n100_event_batch_id.txt'
RECORDS_IN = OUT_DIR/'anao_n100_marker_records_filtered.jsonl'
RAW_OUT = OUT_DIR/'anao_n100_event_raw.jsonl'
ASSIGNS_OUT = OUT_DIR/'anao_n100_event_assignments.jsonl'
EVENTS_OUT = OUT_DIR/'anao_n100_events.jsonl'
META_OUT = OUT_DIR/'anao_n100_event_meta.json'


def parse_lenient(text):
    t = text.strip()
    if t.startswith('```'):
        t = t.split('\n', 1)[1] if '\n' in t else t
        if t.endswith('```'): t = t.rsplit('```', 1)[0]
    s, e = t.find('{'), t.rfind('}')
    if s >= 0 and e > s:
        try: return json.loads(t[s:e+1])
        except json.JSONDecodeError: pass
    return None


def main():
    if not BATCH_ID_FILE.exists():
        sys.exit(f'no batch_id at {BATCH_ID_FILE}')
    batch_id = BATCH_ID_FILE.read_text().strip()
    print(f'batch: {batch_id}', flush=True)

    # Load records to join metadata
    rec_meta = {}
    for line in RECORDS_IN.open():
        r = json.loads(line)
        rec_meta[r.get('id')] = {
            '_doc_slug': r.get('_doc_slug'),
            '_year_tabled': r.get('_year_tabled'),
            '_era': r.get('_era'),
            '_portfolio': r.get('_portfolio'),
            '_entity': r.get('_entity'),
        }

    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(batch_id)
    print(f'status: {batch.processing_status}  counts: {batch.request_counts.model_dump()}', flush=True)
    if batch.processing_status != 'ended':
        print('not ready'); return

    raw_lines = []
    all_assignments = []
    all_events = []
    in_tok = out_tok = 0
    parse_full = parse_zero = errored = 0

    for result in client.messages.batches.results(batch_id):
        cid = result.custom_id
        if result.result.type != 'succeeded':
            errored += 1
            print(f'  ! {cid}: {result.result.type}', flush=True)
            continue
        msg = result.result.message
        in_tok += msg.usage.input_tokens
        out_tok += msg.usage.output_tokens
        text = ''.join(b.text for b in msg.content if hasattr(b, 'text'))
        raw_lines.append(json.dumps({'custom_id': cid, 'text': text}))
        d = parse_lenient(text)
        if not d:
            parse_zero += 1
            print(f'  ! {cid}: parse failed (len={len(text)})', flush=True)
            continue
        parse_full += 1
        # Namespace event_ids per doc to avoid collision: doc-slug + EVT-NNNN
        doc_prefix = cid.replace('-', '_')[:30]
        for a in d.get('assignments', []):
            ev = a.get('event_id') or a.get('event_ids')
            if isinstance(ev, list):
                ev_ns = [f'{doc_prefix}::{e}' for e in ev]
                a['event_ids'] = ev_ns
            else:
                a['event_id'] = f'{doc_prefix}::{ev}'
            a['_doc_slug'] = cid
            meta = rec_meta.get(a.get('record_id'), {})
            a.update(meta)
            all_assignments.append(a)
        for e in d.get('events', []):
            e['event_id'] = f'{doc_prefix}::{e.get("event_id")}'
            e['_doc_slug'] = cid
            all_events.append(e)

    RAW_OUT.write_text('\n'.join(raw_lines))
    with ASSIGNS_OUT.open('w') as f:
        for a in all_assignments: f.write(json.dumps(a) + '\n')
    with EVENTS_OUT.open('w') as f:
        for e in all_events: f.write(json.dumps(e) + '\n')

    cost = in_tok/1e6*5*0.5 + out_tok/1e6*25*0.5
    print(f'\ntokens: {in_tok:,} in / {out_tok:,} out  cost ${cost:.2f}', flush=True)
    print(f'parse: {parse_full} ok / {parse_zero} failed / {errored} errored', flush=True)
    print(f'assignments: {len(all_assignments)}', flush=True)
    print(f'events: {len(all_events)}', flush=True)
    if all_assignments:
        ratio = len(all_assignments) / len(all_events)
        print(f'records-per-event ratio: {ratio:.2f} (= dedup factor)', flush=True)

    # Per-doc event count
    events_per_doc = Counter(e.get('_doc_slug') for e in all_events)
    if events_per_doc:
        vals = sorted(events_per_doc.values())
        print(f'events/doc — n_docs={len(events_per_doc)} min={vals[0]} median={vals[len(vals)//2]} max={vals[-1]} mean={sum(vals)/len(vals):.1f}', flush=True)

    # How many events span multiple records?
    event_record_counts = Counter()
    for a in all_assignments:
        eids = a.get('event_ids') or [a.get('event_id')]
        for eid in eids:
            event_record_counts[eid] += 1
    multi_record = sum(1 for v in event_record_counts.values() if v > 1)
    print(f'events with >1 record (real dedup): {multi_record} / {len(event_record_counts)}', flush=True)

    META_OUT.write_text(json.dumps({
        'batch_id': batch_id,
        'n_docs_input': parse_full,
        'n_records_input': len(all_assignments),
        'n_events': len(all_events),
        'records_per_event': round(len(all_assignments)/max(len(all_events),1), 2),
        'multi_record_events': multi_record,
        'events_per_doc_mean': round(sum(events_per_doc.values())/max(len(events_per_doc),1), 1),
        'cost_usd': round(cost, 4),
        'input_tokens': in_tok, 'output_tokens': out_tok,
        'parse_ok': parse_full, 'parse_failed': parse_zero, 'errored': errored,
    }, indent=2))
    print(f'\nwrote {ASSIGNS_OUT}\nwrote {EVENTS_OUT}\nwrote {META_OUT}', flush=True)


if __name__ == '__main__':
    main()
