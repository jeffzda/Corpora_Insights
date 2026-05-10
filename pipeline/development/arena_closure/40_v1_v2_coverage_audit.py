#!/usr/bin/env python3
"""Compare v1 (71) and v2 (70) parent sets via single Opus 4.7 call.

Produces: for every v1 parent, where it lands in v2 (mapped | partial | missing).
For every v2 parent, where it came from in v1 (descended_from | new).
And a short list of genuinely missing mechanisms (in v1 but not in v2) +
genuinely new mechanisms (in v2 but not in v1).
"""
from __future__ import annotations
import json, time, subprocess, sys
from pathlib import Path
import anthropic

ROOT = Path(__file__).resolve().parents[2]
V1 = ROOT/'closure/output/parents_v1.json'
V2 = ROOT/'closure/output/parent_derivation_clean_ensemble/v2_parents.json'
OUT_DIR = ROOT/'closure/output/parent_derivation_clean_ensemble'
OUT_RAW = OUT_DIR/'v1_v2_coverage_audit.raw.txt'
OUT_JSON = OUT_DIR/'v1_v2_coverage_audit.json'
OUT_MD = OUT_DIR/'v1_v2_coverage_audit.md'
OUT_HTML = OUT_DIR/'v1_v2_coverage_audit.html'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'
MODEL = 'claude-opus-4-7'
MAX_TOKENS = 32000


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


def render_v1(parents):
    out = []
    for p in parents:
        out.append(f"  [{p['parent_id']}] {p['name']} — {p.get('mechanism_criterion', p.get('description',''))}")
    return '\n'.join(out)


def render_v2(core, high_promoted):
    out = ['## Core (43, ≥90% rep agreement)']
    for c in core:
        out.append(f"  [{c['parent_id']}] {c['name']} — {c.get('mechanism_criterion', c.get('description',''))}")
    out.append('')
    out.append('## High-tier promoted (27, 70-89% rep agreement)')
    for h in high_promoted:
        out.append(f"  [{h['class_id']}] (promoted) — {h.get('reason','')}")
    return '\n'.join(out)


PROMPT = """# v1 vs v2 parent-taxonomy coverage audit

We have two ARENA failure-mechanism parent taxonomies derived from the same 1,141-cluster catalogue:

- **v1**: 71 parents, derived in a single Opus pass without ensemble validation.
- **v2**: 70 parents (43 core ≥90% rep agreement + 27 promoted high-tier), derived from a 59-rep deliberation-rich ensemble.

Both are intended for an ARENA portfolio manager scanning failure-mode space for project-risk assessment.

## Your task

For every v1 parent, decide whether the v2 set covers the same mechanism. Assign one of:
- `mapped`: a single v2 parent cleanly covers the same mechanism class
- `split`: the v1 mechanism is now split across multiple v2 parents (more granular)
- `merged`: the v1 mechanism is now subsumed into a broader v2 parent (less granular, but still covered)
- `missing`: no v2 parent reasonably covers this mechanism — a genuine coverage gap

For every v2 parent (core + promoted), decide whether v1 had it:
- `descended_from_v1`: a v1 parent named the same mechanism class
- `refined_from_v1`: derived by splitting/clarifying a v1 parent
- `new_in_v2`: no v1 parent named this mechanism — a genuine new addition

Then synthesise:
- A short list of **mechanisms genuinely missing from v2** (≥1 v1 parent rated `missing`).
- A short list of **mechanisms genuinely new in v2** (≥1 v2 parent rated `new_in_v2`).
- An overall verdict on whether v2's coverage is complete relative to v1, and which (if any) v1 parents the v2 set should consider re-adding.

Be discriminating: a v1 parent that's *partially* covered by a v2 parent (e.g. mechanism class is named at higher abstraction) should be `merged`, not `missing`. Reserve `missing` for cases where a PM scanning v2 would have no parent to land a v1-named mechanism on.

## Output (strict JSON, no extra text)

```json
{
  "v1_to_v2": [
    {"v1_id": "p01", "v1_name": "...", "verdict": "mapped|split|merged|missing", "v2_target_ids": ["p01"] or [], "reason": "<≤25 words>"}
  ],
  "v2_to_v1": [
    {"v2_id": "p01", "v2_name": "...", "verdict": "descended_from_v1|refined_from_v1|new_in_v2", "v1_source_ids": ["p01"] or [], "reason": "<≤25 words>"}
  ],
  "missing_from_v2": [
    {"v1_ids": ["pNN"], "mechanism_class": "...", "evidence": "<why this is a real gap, ≤40 words>", "recommendation": "add_as_new_parent | merge_into_<v2_id> | accept_as_subsumed"}
  ],
  "new_in_v2": [
    {"v2_ids": ["pNN" or "high_NN"], "mechanism_class": "...", "evidence": "<why this is a real new addition, ≤40 words>"}
  ],
  "verdict": "<≤200 words: is v2 coverage complete relative to v1? which (if any) v1 parents should be re-added? what does v2 add that v1 lacks?>"
}
```

## v1 (71)

{v1_block}

## v2 (70 = 43 core + 27 promoted)

{v2_block}
"""


def main():
    v1_parents = json.load(V1.open())['parents']
    v2j = json.load(V2.open())
    core = v2j['consolidation']['core_consolidations']
    high = v2j['consolidation']['high_tier_judgements']
    high_promoted = [h for h in high if h['verdict']=='promote']
    print(f"v1: {len(v1_parents)}, v2: {len(core)} core + {len(high_promoted)} promoted")

    prompt = PROMPT.replace('{v1_block}', render_v1(v1_parents)).replace('{v2_block}', render_v2(core, high_promoted))
    print(f"prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"calling {MODEL}...", flush=True)
    started = time.time()
    parts = []
    last_print, last_chars, text_chars = 0, 0, 0
    with client.messages.stream(
        model=MODEL, max_tokens=MAX_TOKENS,
        messages=[{"role":"user","content":prompt}],
    ) as stream:
        for ev in stream.text_stream:
            parts.append(ev); text_chars += len(ev)
            now = time.time()
            if now - last_print >= 5:
                rate = (text_chars - last_chars) / max(now - last_print, 1)
                print(f"  [{int(now-started)}s] {text_chars:,} chars +{rate:.0f} c/s", flush=True)
                last_print, last_chars = now, text_chars
        msg = stream.get_final_message()
    raw = ''.join(parts); OUT_RAW.write_text(raw)
    wall = time.time() - started
    cost = msg.usage.input_tokens/1e6*5 + msg.usage.output_tokens/1e6*25
    print(f"done: {wall:.0f}s, {msg.usage.input_tokens:,}in/{msg.usage.output_tokens:,}out ${cost:.3f}", flush=True)

    parsed = parse_json(raw)
    if not parsed:
        raise SystemExit(f"parse failed; raw at {OUT_RAW}")

    json.dump({
        'model': MODEL, 'cost': round(cost,3), 'wall_seconds': round(wall,1),
        'input_tokens': msg.usage.input_tokens, 'output_tokens': msg.usage.output_tokens,
        'audit': parsed,
    }, open(OUT_JSON,'w'), indent=2)

    md = ['# v1 vs v2 parent-taxonomy coverage audit', '',
          f'**v1**: 71 parents (single Opus pass).  **v2**: 70 parents (43 core ≥90% + 27 promoted high-tier from 59-rep ensemble).',
          f'**Cost:** ${cost:.2f}, {wall:.0f}s wall.', '',
          '## Verdict', '', parsed.get('verdict','(none)'), '', ]

    miss = parsed.get('missing_from_v2', [])
    md += [f'## Mechanisms missing from v2 ({len(miss)})', '',
           '| v1_ids | mechanism_class | evidence | recommendation |',
           '|---|---|---|---|']
    for m in miss:
        md.append(f"| {', '.join(m.get('v1_ids',[]))} | {m.get('mechanism_class','')} | {m.get('evidence','')} | {m.get('recommendation','')} |")

    new = parsed.get('new_in_v2', [])
    md += ['', f'## Mechanisms new in v2 ({len(new)})', '',
           '| v2_ids | mechanism_class | evidence |',
           '|---|---|---|']
    for n in new:
        md.append(f"| {', '.join(n.get('v2_ids',[]))} | {n.get('mechanism_class','')} | {n.get('evidence','')} |")

    v1tov2 = parsed.get('v1_to_v2',[])
    from collections import Counter
    vc = Counter(x.get('verdict','?') for x in v1tov2)
    md += ['', f'## v1 → v2 mapping ({len(v1tov2)} entries)', '',
           f'Verdict counts: {dict(vc)}', '',
           '| v1_id | v1_name | verdict | v2_targets | reason |',
           '|---|---|---|---|---|']
    for x in v1tov2:
        md.append(f"| {x.get('v1_id','')} | {x.get('v1_name','')} | {x.get('verdict','')} | {', '.join(x.get('v2_target_ids',[]))} | {x.get('reason','')} |")

    v2tov1 = parsed.get('v2_to_v1',[])
    vc2 = Counter(x.get('verdict','?') for x in v2tov1)
    md += ['', f'## v2 → v1 mapping ({len(v2tov1)} entries)', '',
           f'Verdict counts: {dict(vc2)}', '',
           '| v2_id | v2_name | verdict | v1_sources | reason |',
           '|---|---|---|---|---|']
    for x in v2tov1:
        md.append(f"| {x.get('v2_id','')} | {x.get('v2_name','')} | {x.get('verdict','')} | {', '.join(x.get('v1_source_ids',[]))} | {x.get('reason','')} |")

    OUT_MD.write_text('\n'.join(md))
    proc = subprocess.run(
        [sys.executable, MD2HTML, 'v1 vs v2 parent-taxonomy coverage audit',
         f'Broad Learnings · {len(miss)} missing, {len(new)} new'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    OUT_HTML.write_text(proc.stdout)

    print(f"\nwrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print(f"missing from v2: {len(miss)}, new in v2: {len(new)}")


if __name__ == '__main__':
    main()
