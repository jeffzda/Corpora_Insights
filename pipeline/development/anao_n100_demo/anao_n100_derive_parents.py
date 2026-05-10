#!/usr/bin/env python3
"""ANAO N=100 — Phase 5 Pass 1: derive parent categories.

Mirrors corpora/arena/clustering_v2/closure/code/12_opus_derive_parents.py
applied to the 207-cluster ANAO catalogue.

Single Opus 4.7 call. The prompt is the same shape as ARENA's
12_derive_parents.md with audience and corpus framing adapted
to ANAO performance audits (Commonwealth programs across all portfolios).
"""
import argparse
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import anthropic

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = ROOT / 'corpora/anao/n100_demo/output'
SWEEP_DIR = OUT_DIR / 'sweep'
CATALOGUE = SWEEP_DIR / 'residual' / 'catalogue_after_residual.json'
ASSIGNMENTS_SWEEP = SWEEP_DIR / 'corpus_assignments.jsonl'
ASSIGNMENTS_RECLASS = SWEEP_DIR / 'reclassify' / 'reclassified_assignments.jsonl'
ASSIGNMENTS_RESIDUAL = SWEEP_DIR / 'residual' / 'residual_assignments.jsonl'

OUT_RAW = OUT_DIR / 'anao_n100_parents_raw.txt'
OUT_JSON = OUT_DIR / 'anao_n100_parents.json'
OUT_MD = OUT_DIR / 'anao_n100_parents.md'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 32000


PROMPT = """# Parent-category derivation from ANAO mechanism-level failure clusters

## Context

You are proposing parent categories for a taxonomy of failure-mode clusters extracted from a corpus of ANAO performance audit reports (the Australian National Audit Office, audits of Commonwealth programs and entities across all portfolios — Defence, Treasury, Health, Education, Environment, etc.). Each cluster represents a recurring failure pattern — multiple audit findings across different agencies and programs independently asserting the same underlying causal mechanism.

You will not see the records themselves; you will see only each cluster's **id**, **canonical name**, **mechanism signature** (one sentence describing the causal pathway), and **n_records** (how many records the cluster aggregates).

## Audience

The reader is a Commonwealth program manager / agency executive / policy analyst evaluating a current or prospective program. They use the parent set as a **navigable diagnostic vocabulary**: scanning the parent names and definitions to surface every important failure mechanism that could plausibly arise in their program, and grounding their assessment of forward-looking risk in the audit evidence beneath each mechanism. The taxonomy needs to:

- **Cover the mechanism space comprehensively** so a manager scanning the list does not encounter a real risk with no corresponding parent.
- **Remain navigable at a glance** — too many parents and the manager can't scan them efficiently; too few and the taxonomy collapses genuinely-distinct mechanisms together.
- **Support defensible claims about future program risk** — each parent must name a mechanism the manager can cite as a structurally real failure pattern the audit corpus has shown recurring.

## Task

Read all the clusters listed below. Propose parent categories that group them by **mechanism class** — the kind of thing that goes wrong, not the topic or domain it goes wrong in.

## Constraints

1. **Emergent count.** Return as many parents as the clusters genuinely require, no more and no fewer. There is no preset number.

2. **Mechanism class, not topic.** Two clusters from different portfolios that fail through the same mechanism should land in the same parent. Two clusters from the same agency that fail through different mechanisms should land in different parents. Do not group by portfolio or sector.

3. **Tightness over breadth.** Prefer narrower, well-defined parents that genuinely fit their members over broad parents that absorb anything loosely related. If a parent's description has to use "or" to span structurally different mechanisms, split it.

4. **Honest unfit reporting.** If some clusters do not cleanly fit any proposed parent, return them under an `unassigned` bucket with reasons. Forcing membership reduces taxonomy quality.

5. **Mid-tail attention.** The cluster list contains both larger (50+ record) and smaller (3-5 record) clusters. Do not let larger clusters dominate the parent design — smaller clusters often instantiate tighter, more specific mechanisms that matter for the parent definition.

6. **Independence of axes.** Make parents distinguishable on mechanism class alone. If two parents differ only in which portfolio or programme stage their members come from, they are likely the same mechanism class differently labelled.

## Output

Strict JSON, no extra text:

```json
{{
  "parents": [
    {{
      "parent_id": "p01",
      "name": "<short noun phrase, 3-7 words>",
      "description": "<2-4 sentences naming the mechanism class and the criterion for membership>",
      "mechanism_criterion": "<one sentence: what must be true of a cluster's mechanism for it to belong here>",
      "exemplar_cluster_ids": ["<ids of 3-5 clusters that most cleanly instantiate this parent>"],
      "estimated_population": "<rough fraction of total clusters expected to fit, e.g. '5-8%'>"
    }}
  ],
  "unassigned": [
    {{"cluster_id": "<cNNN>", "reason": "<why no parent fits>"}}
  ],
  "notes": "<optional: anything you noticed about the cluster distribution worth flagging>"
}}
```

Number parents `p01`, `p02`, ... in the order you list them. Order them thematically so adjacent parents are mechanism-related families.

## Input — {n_clusters} clusters

Each entry: `cluster_id | canonical_name | mechanism_signature | n_records`

{cluster_block}
"""


def main():
    catalogue = json.load(CATALOGUE.open())['clusters']
    print(f'catalogue: {len(catalogue)} clusters', flush=True)

    # Compute n_records per cluster from all assignments
    counts = Counter()
    for path in [ASSIGNMENTS_SWEEP, ASSIGNMENTS_RECLASS, ASSIGNMENTS_RESIDUAL]:
        if not path.exists(): continue
        for line in path.open():
            a = json.loads(line)
            cid = a.get('cluster_id')
            if cid and cid != 'orphan':
                counts[cid] += 1

    lines = []
    for c in catalogue:
        cid = c['cluster_id']
        n = counts.get(cid, len(c.get('seed_members', [])))
        name = (c.get('canonical_name') or '').replace('|', '/').strip()
        sig = (c.get('mechanism_signature') or '').replace('|', '/').replace('\n', ' ').strip()
        lines.append(f'{cid} | {name} | {sig} | {n}')
    cluster_block = '\n'.join(lines)

    prompt = PROMPT.format(n_clusters=len(catalogue), cluster_block=cluster_block)
    print(f'prompt: {len(prompt):,} chars (~{len(prompt)//4:,} input tokens)', flush=True)

    client = anthropic.Anthropic()
    print(f'calling {MODEL}...', flush=True)
    started = time.time()
    parts = []
    last_print = 0; last_chars = 0; text_chars = 0
    with client.messages.stream(model=MODEL, max_tokens=MAX_TOKENS,
                                 messages=[{'role':'user','content':prompt}]) as stream:
        for ev in stream.text_stream:
            parts.append(ev); text_chars += len(ev)
            now = time.time()
            if now - last_print >= 5:
                rate = (text_chars-last_chars)/max(now-last_print,1)
                print(f'  [{int(now-started)}s] {text_chars:,} chars +{rate:.0f} c/s', flush=True)
                last_print = now; last_chars = text_chars
        msg = stream.get_final_message()
    raw = ''.join(parts)
    OUT_RAW.write_text(raw)
    wall = time.time() - started
    cost = msg.usage.input_tokens/1e6*5 + msg.usage.output_tokens/1e6*25
    print(f'done: {wall:.0f}s {msg.usage.input_tokens:,}in/{msg.usage.output_tokens:,}out ${cost:.3f}', flush=True)

    t = raw.strip()
    if t.startswith('```'):
        t = t.split('\n', 1)[1]
        if t.endswith('```'): t = t.rsplit('```', 1)[0]
    s, e = t.find('{'), t.rfind('}')
    parsed = None
    if s >= 0 and e > s:
        try: parsed = json.loads(t[s:e+1])
        except json.JSONDecodeError as ex: print(f'parse error: {ex}')
    if not parsed:
        raise SystemExit(f'parse failed; raw at {OUT_RAW}')

    parents = parsed.get('parents', [])
    unassigned = parsed.get('unassigned', [])
    print(f'parents: {len(parents)}  unassigned: {len(unassigned)}')

    json.dump({
        'model': MODEL, 'cost': round(cost,4), 'wall_seconds': round(wall,1),
        'input_tokens': msg.usage.input_tokens, 'output_tokens': msg.usage.output_tokens,
        'n_clusters': len(catalogue), 'n_parents': len(parents),
        'n_unassigned': len(unassigned),
        'derivation': parsed,
    }, OUT_JSON.open('w'), indent=2)

    md = ['# ANAO N=100 — parent set derived from 207 mechanism clusters', '',
          f'Single Opus 4.7 call. {len(catalogue)} clusters → {len(parents)} parents.  ${cost:.2f}, {wall:.0f}s.', '',
          f'**Unassigned:** {len(unassigned)}', '',
          '## Parents', '',
          '| parent_id | name | est. population | mechanism criterion |',
          '|---|---|---|---|']
    for p in parents:
        crit = (p.get('mechanism_criterion') or '—')[:120]
        md.append(f"| {p.get('parent_id','?')} | {p.get('name','?')} | {p.get('estimated_population','?')} | {crit} |")
    md.append('')
    md.append('## Full parent definitions')
    md.append('')
    for p in parents:
        md += [f"### {p.get('parent_id','?')} — {p.get('name','?')}",
               '',
               p.get('description',''),
               '',
               f"**Mechanism criterion:** {p.get('mechanism_criterion','?')}",
               '']
        ex = p.get('exemplar_cluster_ids', [])
        if ex:
            md.append(f"**Exemplar clusters:** {', '.join(ex)}")
        md.append(f"**Estimated population:** {p.get('estimated_population','?')}")
        md.append('')

    if unassigned:
        md += ['## Unassigned', '', '| cluster_id | reason |', '|---|---|']
        for u in unassigned:
            md.append(f"| {u.get('cluster_id','?')} | {u.get('reason','')[:200]} |")
        md.append('')

    notes = parsed.get('notes')
    if notes:
        md += ['## Notes', '', notes]

    OUT_MD.write_text('\n'.join(md))
    print(f'\nwrote {OUT_JSON}, {OUT_MD}')

    print(f'\nfirst 10 parents:')
    for p in parents[:10]:
        print(f"  [{p['parent_id']}] {p['name']}")


if __name__ == '__main__':
    main()
