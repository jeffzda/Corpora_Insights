#!/usr/bin/env python3
"""Ask Sonnet to propose a more granular sub-clustering of the three
biggest glossary categories (technology, organisation, concept).

Goal: a categorisation a portfolio manager would actually navigate by.
Produces a proposal — not an application. Jeff reviews before apply.
"""
from __future__ import annotations
import json, time
from pathlib import Path
import anthropic

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'output/glossary_subclustering_input.json'
OUT = ROOT / 'output/glossary_subclustering_proposal.json'
RAW = ROOT / 'output/glossary_subclustering_proposal.raw.txt'
MODEL = 'claude-sonnet-4-6'

PROMPT = """# Sub-clustering proposal — ARENA glossary

You are designing a more navigable taxonomy for an ARENA (Australian Renewable Energy Agency) portfolio-manager study guide. The current glossary has three top-level categories that are too big to navigate:

- **technology** ({n_tech} entries)
- **organisation** ({n_org} entries)
- **concept** ({n_concept} entries)

Total: {n_total} entries across these three buckets.

## Audience and use

The reader is an ARENA portfolio manager — incoming or mid-tenure. Their workflow includes reading project synthesis reports that cite many acronyms and named entities, looking up "what is X" or "what kind of X is this" for entries they don't recognise. They benefit from sub-categories that map to their mental model: kinds of technology that ARENA funds, kinds of organisation that show up in renewables work, kinds of concept that recur in project documentation.

Don't propose categories that exist for taxonomic completeness without serving the PM workflow. Don't make the categories too fine — 4-8 subcategories per top category is the right granularity. Each subcategory name should be self-explanatory.

## Task

For each of the three top categories below, propose:

1. A set of subcategories — 4-8 each, more if genuinely needed.
2. A short rationale (one sentence per subcategory) explaining what fits there and why a PM would find it useful.
3. A sample assignment — for each subcategory, list 3-6 example terms from the input that belong there (use the term as given).
4. An "edge cases" note where some entries don't fit cleanly or are genuinely cross-category.

Output strict JSON, no commentary or markdown fences:

```json
{{
  "technology": {{
    "subcategories": [
      {{"name": "...", "description": "...", "examples": ["DER", "BESS", ...]}}
    ],
    "edge_cases": "..."
  }},
  "organisation": {{...}},
  "concept": {{...}}
}}
```

## Input data

Each entry below is `[term] expansion | n_docs corpus coverage | definition`.

### technology — {n_tech} entries

{tech_block}

### organisation — {n_org} entries

{org_block}

### concept — {n_concept} entries

{concept_block}

Return only the JSON proposal. No commentary."""


def fmt(entries, max_def=140):
    lines = []
    entries = sorted(entries, key=lambda e: -(e.get('n_unique_docs') or 0))
    for e in entries:
        defn = (e.get('definition') or '').replace('\n', ' ')[:max_def]
        exp = e.get('expansion') or '(no expansion)'
        n_d = e.get('n_unique_docs', 0)
        lines.append(f"[{e['term']}] {exp} | {n_d}d | {defn}")
    return '\n'.join(lines)


def main():
    data = json.load(open(INPUT))
    tech = data['technology']; org = data['organisation']; concept = data['concept']

    prompt = PROMPT.format(
        n_tech=len(tech), n_org=len(org), n_concept=len(concept),
        n_total=len(tech)+len(org)+len(concept),
        tech_block=fmt(tech),
        org_block=fmt(org),
        concept_block=fmt(concept),
    )
    print(f"prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"calling {MODEL}...", flush=True)
    started = time.time()
    parts = []
    last_print = 0; last_chars = 0; text_chars = 0
    with client.messages.stream(
        model=MODEL, max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
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
    raw = ''.join(parts)
    RAW.write_text(raw)
    wall = time.time() - started
    cost = msg.usage.input_tokens/1e6*3 + msg.usage.output_tokens/1e6*15
    print(f"\ndone: {len(raw):,} chars in {wall:.0f}s; {msg.usage.input_tokens:,}in/{msg.usage.output_tokens:,}out ${cost:.3f}; stop={msg.stop_reason}", flush=True)

    # Parse
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
        raise SystemExit(f"parse failed; raw at {RAW}")

    OUT.write_text(json.dumps(parsed, indent=2))
    print(f"wrote {OUT}")

    # Print summary
    for cat in ['technology', 'organisation', 'concept']:
        if cat not in parsed: continue
        subs = parsed[cat].get('subcategories', [])
        print(f"\n=== {cat} → {len(subs)} subcategories ===")
        for s in subs:
            print(f"  - {s.get('name','?')}: {s.get('description','')[:90]}")
            ex = s.get('examples', [])
            print(f"      e.g. {', '.join(ex[:5])}")
        if parsed[cat].get('edge_cases'):
            print(f"  edge cases: {parsed[cat]['edge_cases'][:200]}")


if __name__ == '__main__':
    main()
