#!/usr/bin/env python3
"""Parent-gap audit: assess whether the production 71-parent layer is
missing any valuable categories that the 50-run ensemble proposed.

Inputs:
  - 71 production parents (parents_v1.json)
  - 126 canonical classes from the 50-run consolidation
    (parent_ensemble/canonical_vocabulary.json)
  - frequency: each canonical class has n_runs_present / 50 reps

Method: single Sonnet 4.6 call. For each canonical class, find the closest
production parent or flag as missing, with rationale and gap priority.

Output: parent_gap_audit.{json,md,html} under closure/output/.
"""
from __future__ import annotations
import json, time, subprocess, sys, re
from pathlib import Path
import anthropic

ROOT = Path(__file__).resolve().parents[2]
PROD_PARENTS = ROOT/'closure/output/parents_v1.json'
CANONICAL = ROOT/'closure/output/parent_ensemble/canonical_vocabulary.json'
OUT_DIR = ROOT/'closure/output'
OUT_JSON = OUT_DIR/'parent_gap_audit.json'
OUT_RAW = OUT_DIR/'parent_gap_audit.raw.txt'
OUT_MD = OUT_DIR/'parent_gap_audit.md'
OUT_HTML = OUT_DIR/'parent_gap_audit.html'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'
MODEL = 'claude-sonnet-4-6'


PROMPT_TEMPLATE = """# Parent-layer gap audit

You are auditing the ARENA v2 production parent-archetype layer (71 parents) against the canonical-class vocabulary (126 classes) produced by Opus consolidation of a 50-run parent-derivation ensemble. The question is whether the 71-parent production layer is missing any valuable mechanism-class categories that the ensemble proposed reliably.

## Production parent layer (71)

Each parent has a name, description, and mechanism criterion (the structural condition for membership).

{prod_block}

## Canonical classes from 50-run ensemble (126)

Each class was proposed by the ensemble at a given frequency (n_runs_present / 50). Higher frequency = more reliably proposed.

{canonical_block}

## Task

For each canonical class, decide whether the production parent layer covers it:

- `clean_match`: exactly one production parent covers this canonical class.
- `partial_match`: a production parent covers part of it but the canonical class names a finer or different distinction.
- `missing`: no production parent covers this canonical class — the production layer has a genuine gap here.

For `missing` and `partial_match` entries, also assign a **gap priority**:

- `high`: canonical class appeared in ≥40% of ensemble runs AND names a structurally distinct mechanism not covered by existing parents.
- `medium`: 20-39% of runs, OR partial match with a meaningful distinction.
- `low`: <20% of runs, or partial match where the existing parent is reasonable.

## Output

Strict JSON. Single object:

```json
{{"audit": [
  {{"class_id": "c01", "name": "...", "frequency": 0.96,
    "match_status": "clean_match", "best_match_parent": "p44",
    "rationale": "≤25 words"}},
  {{"class_id": "c87", "name": "...", "frequency": 0.30,
    "match_status": "missing", "best_match_parent": null,
    "gap_priority": "medium", "rationale": "≤30 words on what's missing"}}
]}}
```

Return ONE entry per canonical class (126 entries). No commentary.
"""


def parse_json(raw):
    r = raw.strip()
    if r.startswith('```'):
        r = r.split('\n',1)[1]
        if r.endswith('```'): r = r.rsplit('```',1)[0]
    s, e = r.find('{'), r.rfind('}')
    if s>=0 and e>s:
        try: return json.loads(r[s:e+1])
        except Exception: pass
    pat = re.compile(r'\{\s*"class_id".*?(?:"rationale"\s*:\s*"[^"]*")\s*\}', re.DOTALL)
    entries = []
    for m in pat.finditer(r):
        try: entries.append(json.loads(m.group(0)))
        except Exception: pass
    return {'audit': entries} if entries else None


def main():
    prod = json.load(open(PROD_PARENTS))['parents']
    canonical = json.load(open(CANONICAL))['canonical_classes']

    # Build prod block
    prod_lines = []
    for p in prod:
        prod_lines.append(f"[{p['parent_id']}] {p['name']}")
        prod_lines.append(f"  desc: {(p.get('description') or '')[:200]}")
        prod_lines.append(f"  criterion: {(p.get('mechanism_criterion') or '')[:200]}")
    prod_block = '\n'.join(prod_lines)

    # Build canonical block
    can_lines = []
    for c in canonical:
        can_lines.append(f"[{c['class_id']}] freq={c.get('frequency',0):.2f} ({c.get('n_runs_present','?')}/50)")
        can_lines.append(f"  name: {c.get('name','')}")
        defn = (c.get('definition') or '')[:200]
        if defn: can_lines.append(f"  defn: {defn}")
    canonical_block = '\n'.join(can_lines)

    prompt = PROMPT_TEMPLATE.format(prod_block=prod_block, canonical_block=canonical_block)
    print(f"prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    started = time.time()
    parts = []
    last_print = 0; last_chars = 0; text_chars = 0
    with client.messages.stream(
        model=MODEL, max_tokens=32000,
        messages=[{"role":"user","content":prompt}],
    ) as stream:
        for ev in stream.text_stream:
            parts.append(ev); text_chars += len(ev)
            now = time.time()
            if now - last_print >= 5:
                rate = (text_chars - last_chars) / max(now - last_print, 1)
                print(f"  [{int(now-started)}s] {text_chars:,} chars +{rate:.0f} c/s", flush=True)
                last_print = now; last_chars = text_chars
        msg = stream.get_final_message()
    raw = ''.join(parts); OUT_RAW.write_text(raw)
    wall = time.time() - started
    cost = msg.usage.input_tokens/1e6*3 + msg.usage.output_tokens/1e6*15
    print(f"\ndone: {wall:.0f}s, {msg.usage.input_tokens:,}in/{msg.usage.output_tokens:,}out ${cost:.3f}, stop={msg.stop_reason}", flush=True)

    parsed = parse_json(raw)
    if not parsed or not parsed.get('audit'):
        raise SystemExit(f"parse failed; raw at {OUT_RAW}")
    audit = parsed['audit']

    # Build canonical-class lookup
    can_by_id = {c['class_id']: c for c in canonical}
    prod_by_id = {p['parent_id']: p for p in prod}
    for a in audit:
        cid = a.get('class_id')
        if cid in can_by_id:
            a['canonical_n_runs'] = can_by_id[cid].get('n_runs_present')
            a['canonical_definition'] = can_by_id[cid].get('definition','')

    json.dump({
        'n_canonical_classes': len(canonical),
        'n_audited': len(audit),
        'cost_sync': round(cost,3), 'wall_seconds': round(wall,1),
        'audit': audit,
    }, open(OUT_JSON,'w'), indent=2)

    # Aggregate
    from collections import Counter
    status = Counter(a.get('match_status','?') for a in audit)
    priorities = Counter(a.get('gap_priority','?') for a in audit if a.get('match_status')!='clean_match')

    # MD report
    md = ['# Parent-layer gap audit',
          '',
          f'Comparing the production 71-parent v2 layer against 126 canonical classes consolidated from the 50-run parent-derivation ensemble (4,150 raw parent labels). Question: are there valuable mechanism-class categories the ensemble proposed reliably that the production layer is missing?',
          '',
          f'**Method:** Sonnet 4.6 single call. For each canonical class, decide whether the 71-parent layer covers it cleanly, partially, or not at all. For non-clean matches, assign gap priority based on ensemble frequency and structural distinctness.',
          '',
          f'**Cost:** ${cost:.2f}, {wall:.0f}s.',
          '',
          '## Summary', '',
          '| match_status | count | % |', '|---|---:|---:|']
    n_total = len(audit)
    for s, n in status.most_common():
        md.append(f"| {s} | {n} | {n/n_total*100:.0f}% |")
    md += ['', '## Gap priorities (for partial_match + missing)', '',
           '| priority | count |', '|---|---:|']
    for p, n in priorities.most_common():
        md.append(f"| {p} | {n} |")

    # High-priority missing
    md += ['', '## High-priority gaps (genuine missing categories ≥40% ensemble frequency)', '']
    high = [a for a in audit if a.get('match_status')=='missing' and a.get('gap_priority')=='high']
    high.sort(key=lambda a: -(a.get('frequency',0) or 0))
    if high:
        md.append('| class | freq | name | rationale |')
        md.append('|---|---:|---|---|')
        for a in high:
            md.append(f"| {a.get('class_id','?')} | {a.get('frequency',0):.0%} | {a.get('name','')} | {a.get('rationale','')} |")
    else:
        md.append('*(none — production layer covers all high-frequency canonical classes)*')
    md.append('')

    # Medium-priority missing
    md += ['', '## Medium-priority gaps (20-39% ensemble frequency or meaningful partial-match distinction)', '']
    med = [a for a in audit if a.get('gap_priority')=='medium']
    med.sort(key=lambda a: -(a.get('frequency',0) or 0))
    if med:
        md.append('| class | freq | match_status | best_match | name | rationale |')
        md.append('|---|---:|---|---|---|---|')
        for a in med[:30]:
            md.append(f"| {a.get('class_id','?')} | {a.get('frequency',0):.0%} | {a.get('match_status','')} | {a.get('best_match_parent') or '—'} | {a.get('name','')} | {a.get('rationale','')} |")
        if len(med) > 30:
            md.append(f"| ... | | | | | _(+{len(med)-30} more)_ |")
    else:
        md.append('*(none)*')
    md.append('')

    # Partial matches at high frequency (worth examining for finer distinctions)
    md += ['', '## Partial matches at high frequency (production parent fits but coarsely)', '']
    partial_hi = [a for a in audit if a.get('match_status')=='partial_match' and (a.get('frequency',0) or 0) >= 0.40]
    partial_hi.sort(key=lambda a: -(a.get('frequency',0) or 0))
    if partial_hi:
        md.append('| class | freq | parent | name | rationale |')
        md.append('|---|---:|---|---|---|')
        for a in partial_hi:
            md.append(f"| {a.get('class_id','?')} | {a.get('frequency',0):.0%} | {a.get('best_match_parent','—')} | {a.get('name','')} | {a.get('rationale','')} |")
    else:
        md.append('*(none)*')
    md.append('')

    OUT_MD.write_text('\n'.join(md))
    proc = subprocess.run(
        [sys.executable, MD2HTML, 'Parent-layer gap audit',
         'Broad Learnings · 71 vs 126 canonical-class comparison'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    OUT_HTML.write_text(proc.stdout)

    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print(f"\nverdict distribution: {dict(status)}")
    print(f"gap priorities: {dict(priorities)}")
    print(f"high-priority missing: {len(high)}")
    print(f"medium-priority gaps: {len(med)}")
    print(f"high-freq partial matches: {len(partial_hi)}")


if __name__ == '__main__':
    main()
