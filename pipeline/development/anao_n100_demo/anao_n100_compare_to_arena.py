#!/usr/bin/env python3
"""ANAO N=100 — compare 50 ANAO parents against ARENA v2 86 parents.

For each ANAO parent, find the ARENA parent that names the same mechanism
(or 'none' if no equivalent exists). Same in reverse for ARENA. Output:
overlap analysis showing which mechanisms are common, ANAO-only, ARENA-only.
"""
import json, time
from pathlib import Path
import anthropic

ROOT = Path('/home/jeffzda/broadlearnings')
ANAO_PARENTS = ROOT / 'corpora/anao/n100_demo/output/anao_n100_parents.json'
ARENA_PARENTS = ROOT / 'corpora/arena/clustering_v2/closure/output/parent_derivation_clean_ensemble/v2_parents_extended.json'
OUT = ROOT / 'corpora/anao/n100_demo/output/anao_n100_arena_overlap.json'
OUT_MD = ROOT / 'corpora/anao/n100_demo/output/anao_n100_arena_overlap.md'
OUT_RAW = ROOT / 'corpora/anao/n100_demo/output/anao_n100_arena_overlap.raw.txt'


PROMPT = """# ANAO ↔ ARENA parent-taxonomy overlap audit

Two failure-mechanism parent taxonomies derived by the same pipeline on different government corpora:

- **ARENA v2 extended** (86 parents): from the ARENA Knowledge Bank corpus of clean-energy project documents (1,141 mechanism clusters)
- **ANAO N=100** (50 parents): from a stratified sample of 100 ANAO performance audit reports (207 mechanism clusters)

Both taxonomies serve the same purpose: a navigable diagnostic vocabulary for an analyst evaluating program/project risk. The audiences differ — ARENA's is a clean-energy portfolio manager; ANAO's is a Commonwealth program manager.

## Your task

For every ANAO parent, identify whether ARENA has a parent that names the same mechanism class. Assign:
- `mapped_to_<arena_id>`: ANAO parent maps cleanly to one ARENA parent (same mechanism class, possibly differently named)
- `partial_<arena_id>`: ANAO parent overlaps with one ARENA parent but is broader/narrower or different in scope
- `arena_split_into_<a>_<b>_...`: ANAO parent corresponds to multiple ARENA parents that ARENA splits more finely
- `no_arena_equivalent`: no ARENA parent reasonably names the same mechanism — this is an ANAO-only mechanism

For every ARENA parent, do the same in reverse against ANAO.

Then synthesise:
- **common mechanisms**: parents that map cleanly between the two corpora (mechanisms shared)
- **ANAO-only mechanisms**: ANAO parents with no ARENA equivalent — government-program failure modes ARENA doesn't surface
- **ARENA-only mechanisms**: ARENA parents with no ANAO equivalent — clean-energy-specific failure modes ANAO doesn't surface

Be discriminating. A mechanism that's named in similar abstract terms but applies to genuinely different causal pathways shouldn't be called mapped.

## Output (strict JSON, no extra text)

```json
{{
  "anao_to_arena": [
    {{"anao_id": "p01", "anao_name": "...", "verdict": "mapped|partial|split|no_equivalent",
      "arena_target_ids": ["pNN"] or [], "reason": "<≤25 words>"}}
  ],
  "arena_to_anao": [
    {{"arena_id": "p01", "arena_name": "...", "verdict": "mapped|partial|split|no_equivalent",
      "anao_target_ids": ["pNN"] or [], "reason": "<≤25 words>"}}
  ],
  "common_mechanisms": [
    {{"shared_class": "...", "anao_ids": ["pNN"], "arena_ids": ["pNN"], "evidence": "<short>"}}
  ],
  "anao_only": [
    {{"anao_ids": ["pNN"], "mechanism_class": "...", "evidence": "<≤30 words>"}}
  ],
  "arena_only": [
    {{"arena_ids": ["pNN"], "mechanism_class": "...", "evidence": "<≤30 words>"}}
  ],
  "verdict": "<≤200 words: how much of the mechanism space is shared? what kinds of failures are corpus-specific? does the ANAO set look like a general program-failure taxonomy with ARENA's clean-energy specifics carved off, or are the two taxonomies more independent than that?>"
}}
```

## ANAO parents (50)

{anao_block}

## ARENA v2 extended parents (86)

{arena_block}
"""


def render_anao(parents):
    return '\n'.join(f"  [{p['parent_id']}] {p['name']} — {p.get('mechanism_criterion','')}"
                     for p in parents)


def render_arena(parents):
    return '\n'.join(f"  [{p['parent_id']}] {p['name']} — {p.get('mechanism_criterion','')}"
                     for p in parents)


def parse_json(raw):
    t = raw.strip()
    if t.startswith('```'):
        t = t.split('\n', 1)[1]
        if t.endswith('```'): t = t.rsplit('```', 1)[0]
    s, e = t.find('{'), t.rfind('}')
    if s >= 0 and e > s:
        try: return json.loads(t[s:e+1])
        except json.JSONDecodeError as ex: print(f'parse error: {ex}')
    return None


def main():
    anao = json.load(ANAO_PARENTS.open())['derivation']['parents']
    arena = json.load(ARENA_PARENTS.open())['extended']['parents']
    print(f'ANAO: {len(anao)}  ARENA: {len(arena)}', flush=True)

    prompt = PROMPT.format(anao_block=render_anao(anao), arena_block=render_arena(arena))
    print(f'prompt: {len(prompt):,} chars (~{len(prompt)//4:,} input tokens)', flush=True)

    client = anthropic.Anthropic()
    print(f'calling claude-opus-4-7...', flush=True)
    started = time.time()
    parts = []
    last_print = 0; last_chars = 0; text_chars = 0
    with client.messages.stream(model='claude-opus-4-7', max_tokens=32000,
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
    wall = time.time()-started
    cost = msg.usage.input_tokens/1e6*5 + msg.usage.output_tokens/1e6*25
    print(f'done: {wall:.0f}s ${cost:.3f}', flush=True)

    parsed = parse_json(raw)
    if not parsed:
        raise SystemExit('parse failed')

    json.dump({
        'cost_usd': round(cost, 4),
        'wall_seconds': round(wall, 1),
        'input_tokens': msg.usage.input_tokens,
        'output_tokens': msg.usage.output_tokens,
        'audit': parsed,
    }, OUT.open('w'), indent=2)

    common = parsed.get('common_mechanisms', [])
    anao_only = parsed.get('anao_only', [])
    arena_only = parsed.get('arena_only', [])
    print(f'\ncommon: {len(common)}  anao-only: {len(anao_only)}  arena-only: {len(arena_only)}', flush=True)

    md = ['# ANAO ↔ ARENA parent overlap audit', '',
          f'**Cost:** ${cost:.2f}, {wall:.0f}s', '',
          '## Verdict', '', parsed.get('verdict', '(none)'), '', ]
    md += [f'## Common mechanisms ({len(common)})', '',
           '| shared mechanism class | ANAO | ARENA |',
           '|---|---|---|']
    for c in common:
        md.append(f"| {c.get('shared_class','')} | {', '.join(c.get('anao_ids', []))} | {', '.join(c.get('arena_ids', []))} |")
    md += ['', f'## ANAO-only mechanisms ({len(anao_only)})', '',
           '| ANAO ids | mechanism class | evidence |', '|---|---|---|']
    for a in anao_only:
        md.append(f"| {', '.join(a.get('anao_ids', []))} | {a.get('mechanism_class','')} | {a.get('evidence','')} |")
    md += ['', f'## ARENA-only mechanisms ({len(arena_only)})', '',
           '| ARENA ids | mechanism class | evidence |', '|---|---|---|']
    for a in arena_only:
        md.append(f"| {', '.join(a.get('arena_ids', []))} | {a.get('mechanism_class','')} | {a.get('evidence','')} |")

    OUT_MD.write_text('\n'.join(md))
    print(f'wrote {OUT_MD}')


if __name__ == '__main__':
    main()
