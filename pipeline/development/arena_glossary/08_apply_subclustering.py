#!/usr/bin/env python3
"""Apply Sonnet's proposed subcategorisation to the technology / organisation /
concept entries in the merged glossary.

Compact schema: {t: term, s: subcategory_name}. Single call.
"""
from __future__ import annotations
import json, time
from pathlib import Path
import anthropic

ROOT = Path(__file__).resolve().parents[1]
GLOSSARY = ROOT / 'output/glossary.json'
PROPOSAL = ROOT / 'output/glossary_subclustering_proposal.json'
OUT = ROOT / 'output/glossary_subcategories.json'
RAW = ROOT / 'output/glossary_subcategories.raw.txt'
MODEL = 'claude-sonnet-4-6'


PROMPT = """# Sub-category assignment

You proposed a sub-categorisation scheme for the ARENA glossary's three biggest categories. Now apply it: assign each entry to one subcategory.

## The taxonomy

{taxonomy_block}

## Task

For each input entry below, return its subcategory using the EXACT subcategory name from above. If an entry genuinely doesn't fit any subcategory in its top-level (rare), assign it `"other"` and the reader will fall back to the top-level label.

If an entry is genuinely cross-cutting (you flagged some as edge cases in the proposal), pick the subcategory it primarily fits and let the reader infer the rest from context — don't multi-tag.

## Output

Strict JSON, no extra text. Compact schema:

```json
{{"assignments": [
  {{"t": "DER", "s": "Distributed energy resources and smart energy systems"}},
  {{"t": "BESS", "s": "Energy storage technologies"}}
]}}
```

One entry per input term, in input order. No commentary.

## Input — {n_total} entries grouped by top category

{entries_block}
"""


def fmt_taxonomy(prop):
    out = []
    for cat in ['technology','organisation','concept']:
        if cat not in prop: continue
        out.append(f"\n### {cat}")
        for s in prop[cat].get('subcategories', []):
            out.append(f"- **{s.get('name','?')}**: {s.get('description','')}")
    return '\n'.join(out)


def fmt_entries(entries_by_cat):
    out = []
    for cat in ['technology','organisation','concept']:
        e = entries_by_cat.get(cat, [])
        if not e: continue
        out.append(f"\n### {cat} ({len(e)} entries)")
        for ent in e:
            term = ent['term']
            exp = ent.get('expansion') or ''
            defn = (ent.get('definition') or '').replace('\n',' ')[:120]
            out.append(f"[{term}] {exp} — {defn}")
    return '\n'.join(out)


def main():
    glossary = json.load(open(GLOSSARY))
    proposal = json.load(open(PROPOSAL))
    entries_by_cat = {}
    for e in glossary['entries']:
        c = e.get('category')
        if c in ('technology','organisation','concept'):
            entries_by_cat.setdefault(c, []).append(e)
    n_total = sum(len(v) for v in entries_by_cat.values())

    prompt = PROMPT.format(
        taxonomy_block=fmt_taxonomy(proposal),
        n_total=n_total,
        entries_block=fmt_entries(entries_by_cat),
    )
    print(f"prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"calling {MODEL}...", flush=True)
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
                print(f"  [{int(now-started)}s] {text_chars:,} chars  +{rate:.0f} c/s",
                      flush=True)
                last_print = now; last_chars = text_chars
        msg = stream.get_final_message()
    raw = ''.join(parts); RAW.write_text(raw)
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
    if not parsed:
        # Try recovering partial
        import re
        ents = []
        for m in re.finditer(r'\{\s*"t"\s*:\s*"([^"]+)"\s*,\s*"s"\s*:\s*"([^"]+)"\s*\}', r):
            ents.append({'t': m.group(1), 's': m.group(2)})
        parsed = {'assignments': ents}
        print(f"  recovered {len(ents)} via regex")

    assignments = parsed.get('assignments', [])
    json.dump({
        'model': MODEL, 'n_input': n_total, 'n_returned': len(assignments),
        'cost_sync': round(cost,3), 'wall_seconds': round(wall,1),
        'assignments': assignments,
    }, open(OUT,'w'), indent=2)
    print(f"  wrote {OUT}", flush=True)

    # Distribution
    from collections import Counter
    by_sub = Counter(a['s'] for a in assignments)
    print(f"\nsubcategory distribution:")
    for s, n in by_sub.most_common():
        print(f"  {n:>4}  {s}")


if __name__ == '__main__':
    main()
