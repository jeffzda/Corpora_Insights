#!/usr/bin/env python3
"""Causal-chain test on multi-cluster events.

Question: when an event in the ARENA corpus produces records that land in
≥5 distinct mechanism clusters across ≥4 distinct parent archetypes, do
those parents form a coherent causal chain (parent A → parent B → parent C)
or are they orthogonal failure modes that happened to occur within the
same project?

For each candidate event: load record narratives ordered by project year
plus their cluster + parent assignments. Send to Sonnet with the question
"is this a causal chain or a bundle of orthogonal failures?" with
structured output.

Output: causal_chain_test.json (per-event verdict + reconstructed chain
if applicable), causal_chain_test.md (human-readable report).
"""
from __future__ import annotations
import json, time, subprocess, sys
from pathlib import Path
import anthropic

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / 'closure/output/use_case_demos/causal_chain_test_input.json'
OUT_JSON = ROOT / 'closure/output/use_case_demos/causal_chain_test.json'
OUT_RAW = ROOT / 'closure/output/use_case_demos/causal_chain_test.raw.txt'
OUT_MD = ROOT / 'closure/output/use_case_demos/causal_chain_test.md'
OUT_HTML = ROOT / 'closure/output/use_case_demos/causal_chain_test.html'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'
MODEL = 'claude-sonnet-4-6'


PROMPT_TEMPLATE = """# Causal-chain test on multi-mechanism events

In the ARENA project corpus, individual *events* (logical incidents / decisions / programmes within a project) sometimes produce records that land in many different mechanism clusters across multiple failure-archetype parents. The question is whether these are **causal chains** (parent A's failure causes parent B's failure causes parent C's...) or **orthogonal failure modes** (independent things that happened in the same project, no causal link).

The diagnostic value of the v2 parent layer rests on the first answer being common. If real failure events display causal-chain structure when traced through the parents, then applying the parent layer reconstructs the *causal mechanism*, not just a list of tags.

## Input

Below are {n_events} candidate events. Each shows:
- The project and event ID.
- The records belonging to the event, sorted by project year (oldest first).
- For each record: the cluster it was assigned to, the parent archetype that cluster sits under, and a narrative excerpt.

## Task

For each event, return one JSON entry:

- `event_id`, `project` — copy from input.
- `verdict` — ONE OF:
  - `causal_chain` — parents form a clear sequence where earlier parents create the conditions for later parents to fire.
  - `partial_chain` — some parents form a chain, others are orthogonal additions.
  - `cluster_of_orthogonal_failures` — parents are independent failure modes co-occurring in the same project, no causal link.
  - `single_root_with_multiple_consequences` — one root cause manifests in many forms (technically a chain, but flat — N consequences from 1 cause rather than a sequence).
- `reconstructed_chain` — if `causal_chain` or `partial_chain`: a list of `parent_id → parent_id` arrows representing the inferred causal sequence. Use only the parent_ids given. If `cluster_of_orthogonal_failures`, return null. Use ASCII arrow `->`.
- `evidence` — a short paragraph (≤80 words) citing specific records (by record_id) that support your verdict. Quote no more than 8 words from each.
- `confidence` — `high`, `medium`, or `low`.

## Output

Strict JSON, no extra text. Single object:

```json
{{
  "events": [
    {{
      "event_id": "EVT-0037",
      "project": "Lake Bonney Battery Energy Storage System",
      "verdict": "causal_chain",
      "reconstructed_chain": ["p36 -> p37", "p37 -> p38", "p38 -> p23 -> p24"],
      "evidence": "...",
      "confidence": "high"
    }}
  ]
}}
```

## Input data

{events_block}

Return only the JSON. No commentary."""


def fmt_event(e):
    out = [f"\n### EVENT: {e['event_id']} — project: {e['project']}"]
    for r in e['records']:
        yr = r.get('year') or '?'
        out.append(f"\n  [{r['record_id']}] year={yr}  cluster=[{r['cluster_id']}] {r['cluster_name']}")
        out.append(f"    parent: {r['parent_id']} {r['parent_name']}")
        narr = (r.get('narrative') or '').replace('\n',' ')[:380]
        out.append(f"    narrative: {narr}")
    return '\n'.join(out)


def main():
    data = json.load(open(INPUT))
    events = data['events']
    print(f"loaded {len(events)} events", flush=True)

    events_block = '\n'.join(fmt_event(e) for e in events)
    prompt = PROMPT_TEMPLATE.format(n_events=len(events), events_block=events_block)
    print(f"prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"calling {MODEL}...", flush=True)
    started = time.time()
    parts = []
    last_print = 0; last_chars = 0; text_chars = 0
    with client.messages.stream(
        model=MODEL, max_tokens=16000,
        messages=[{"role":"user","content":prompt}],
    ) as stream:
        for ev in stream.text_stream:
            parts.append(ev); text_chars += len(ev)
            now = time.time()
            if now - last_print >= 5:
                rate = (text_chars - last_chars) / max(now - last_print, 1)
                print(f"  [{int(now-started)}s] {text_chars:,} chars  +{rate:.0f} c/s", flush=True)
                last_print = now; last_chars = text_chars
        msg = stream.get_final_message()
    raw = ''.join(parts); OUT_RAW.write_text(raw)
    wall = time.time() - started
    cost = msg.usage.input_tokens/1e6*3 + msg.usage.output_tokens/1e6*15
    print(f"\ndone: {len(raw):,} chars in {wall:.0f}s; {msg.usage.input_tokens:,}in/{msg.usage.output_tokens:,}out ${cost:.3f}; stop={msg.stop_reason}", flush=True)

    r = raw.strip()
    if r.startswith('```'):
        r = r.split('\n',1)[1]
        if r.endswith('```'): r = r.rsplit('```',1)[0]
    s, e = r.find('{'), r.rfind('}')
    parsed = None
    if s>=0 and e>s:
        try: parsed = json.loads(r[s:e+1])
        except Exception as ex: print(f"parse error: {ex}")

    out_events = parsed.get('events', []) if parsed else []
    json.dump({'events': out_events,
               'cost': round(cost,3), 'wall': round(wall,1)},
              open(OUT_JSON,'w'), indent=2)

    # MD
    md = ['# Causal-chain test on multi-mechanism events',
          '',
          f'For {len(events)} ARENA events that span ≥5 distinct mechanism clusters across ≥4 distinct parent archetypes, asked Sonnet 4.6 to assess whether the parents form a causal chain or an orthogonal cluster of failures.',
          '',
          f'**Cost:** ${cost:.2f}, {wall:.0f}s.',
          '']
    from collections import Counter
    verdicts = Counter(e.get('verdict','?') for e in out_events)
    md += ['## Verdict distribution', '', '| verdict | n |', '|---|---:|']
    for v, n in verdicts.most_common():
        md.append(f'| {v} | {n} |')
    md += ['', '## Per-event diagnoses', '']
    for e in out_events:
        md.append(f"### {e.get('event_id','?')} — {e.get('project','?')}")
        md.append('')
        md.append(f"**Verdict:** `{e.get('verdict','?')}` · confidence: `{e.get('confidence','?')}`")
        md.append('')
        chain = e.get('reconstructed_chain')
        if chain:
            md.append('**Reconstructed chain:**')
            md.append('')
            for c in chain:
                md.append(f'- {c}')
            md.append('')
        ev = e.get('evidence')
        if ev:
            md.append(f"**Evidence:** {ev}")
            md.append('')

    OUT_MD.write_text('\n'.join(md))
    proc = subprocess.run(
        [sys.executable, MD2HTML, 'Causal-chain test on multi-mechanism events',
         'Broad Learnings · v2 parent-layer validation'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    OUT_HTML.write_text(proc.stdout)

    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print(f"wrote {OUT_HTML}")
    print(f"\nverdicts: {dict(verdicts)}")


if __name__ == '__main__':
    main()
