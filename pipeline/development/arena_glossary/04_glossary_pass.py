#!/usr/bin/env python3
"""Stage 4: Generate a corpus-grounded glossary from the entity index.

Filters entity_index.csv to high-signal acronyms (pattern=acronym, ≥5 docs)
and asks Sonnet 4.6 to produce structured glossary entries — expansion,
category, plain-language definition, ARENA-context note, uncertainty flag.

This is the first cut of a "general ARENA study guide": the empirical
scope is set by the corpus (what acronyms actually show up, ranked by
document coverage), the definitions are written by Sonnet from priors,
and uncertainty flags surface entries that need corpus-grounded follow-up.

Output:
  entity_extraction/output/glossary.json (structured)
  entity_extraction/output/glossary.md (alphabetic, with stats)
  entity_extraction/output/glossary.html (rendered)
  entity_extraction/output/glossary_meta.json (cost, tokens, wall)
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[1]
ENTITY_INDEX = ROOT / 'output/entity_index.csv'
OUT_JSON = ROOT / 'output/glossary.json'
OUT_MD = ROOT / 'output/glossary.md'
OUT_HTML = ROOT / 'output/glossary.html'
OUT_META = ROOT / 'output/glossary_meta.json'

MD2HTML = Path('/home/jeffzda/broadlearnings/tools/md2html')

PROMPT_TEMPLATE = """# ARENA corpus glossary pass

You are producing a study-guide glossary for the ARENA (Australian Renewable Energy Agency) project corpus. Each input entry is an acronym or term that the entity-extraction pipeline found in ARENA-funded project documentation, ranked by frequency.

## Input

Each line below is `[surface] (n_total_mentions, n_unique_docs)  variants: [variant1, variant2, ...]`.

The surfaces are extracted programmatically. Most are technical or market-specific acronyms used in Australian renewables / electricity-market documentation. Some entries will be ambiguous (multiple expansions) or noise (sentence fragments, generic English words). Handle each honestly.

## Task

For every input term, return one JSON entry with these fields:

- `term`: the canonical surface, exactly as given.
- `expansion`: the full phrase this acronym/term abbreviates. If genuinely ambiguous given the ARENA / Australian electricity context, include the most likely expansion and note alternatives in `notes`. If no plausible expansion exists (it's not really an acronym, e.g. a phrase fragment), set `expansion` to null.
- `category`: one of: `technology`, `market`, `regulation`, `organisation`, `programme`, `standard`, `concept`, `location`, `unit`, `noise`. Use `noise` for sentence fragments, generic English words mis-caught as terms, or anything that should not appear in a glossary.
- `definition`: one to three plain-English sentences explaining what the term means in the Australian renewables / electricity-market context. Aim for ~30-60 words; longer only if needed for a hard concept. Do NOT define `noise` entries — return null.
- `arena_context`: one short sentence on how the term typically shows up in ARENA project documentation (which kinds of projects, common phrases, what an analyst should know about it). One short sentence; null for `noise`.
- `notes`: optional. Use for ambiguity flags ("also stands for X in some industries"), date-bound caveats ("specific to NER pre-2024"), or important sub-terms. null if none.
- `uncertainty`: true if you're not confident the expansion or definition is correct in the Australian renewables context (e.g. multiple plausible expansions and you can't pick from priors alone). The downstream pipeline will run a corpus-grounded follow-up pass on uncertain entries.

## Style guide

- Australian English spelling (organisation, optimise, programme).
- Australian-specific definitions where the global term differs (FCAS = Frequency Control Ancillary Services in the NEM specifically).
- Don't invent ARENA programmes or grants. If unsure whether a term is ARENA-specific or general industry, mark `uncertainty: true`.
- Don't pad. Empty fields with null, not "N/A".
- Be honest about noise. If a "term" is "Project" or "the Australian Government" or a sentence fragment, mark `category: noise` and don't fabricate a definition.

## Output

Strict JSON, no extra text. Single object with one key:

```json
{{
  "entries": [
    {{"term": "DER", "expansion": "Distributed Energy Resources", "category": "technology",
      "definition": "Small-scale generation, storage, or controllable load assets sited at the distribution network level — rooftop solar, household batteries, electric vehicles, controllable hot water, smart appliances. The term covers both the assets themselves and the practice of orchestrating them as a system.",
      "arena_context": "Heavily used in distribution-network trials and orchestration pilots like Project Symphony; a core ARENA portfolio theme since 2018.",
      "notes": null, "uncertainty": false}}
  ]
}}
```

Return one entry per input term, in input order. No commentary, no preamble, no markdown fences.

## Input — {n_terms} terms

{terms_block}
"""


def parse_json(raw: str):
    raw = raw.strip()
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[1] if '\n' in raw else raw
        if raw.endswith('```'):
            raw = raw.rsplit('```', 1)[0]
    s, e = raw.find('{'), raw.rfind('}')
    if s < 0 or e <= s:
        return None
    try:
        return json.loads(raw[s:e+1])
    except Exception as ex:
        print(f"  JSON parse error: {ex}", flush=True)
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--top-n', type=int, default=600,
                    help='Top-N acronyms by n_total_mentions (default 600)')
    ap.add_argument('--min-docs', type=int, default=5,
                    help='Filter to entries with ≥ this many unique docs (default 5)')
    ap.add_argument('--patterns', nargs='+', default=['acronym'],
                    help='Pattern types to include (default: acronym)')
    ap.add_argument('--model', default='claude-sonnet-4-6')
    ap.add_argument('--max-tokens', type=int, default=64000)
    args = ap.parse_args()

    print(f"Loading {ENTITY_INDEX}...", flush=True)
    rows = list(csv.DictReader(open(ENTITY_INDEX)))
    print(f"  total entities: {len(rows):,}")

    # Filter
    candidates = [
        r for r in rows
        if r['match_status'] == 'unmatched'
        and r['pattern'] in args.patterns
        and int(r['n_unique_docs']) >= args.min_docs
    ]
    candidates.sort(key=lambda r: -int(r['n_total_mentions']))
    candidates = candidates[:args.top_n]
    print(f"  filtered to top-{args.top_n} {args.patterns} with ≥{args.min_docs} docs: "
          f"{len(candidates)} entries", flush=True)

    # Build terms block
    lines = []
    for r in candidates:
        variants = (r.get('all_variants') or '').strip().replace('\n', ' ')[:200]
        lines.append(f"[{r['canonical_surface']}] ({r['n_total_mentions']}m, {r['n_unique_docs']}d)  variants: {variants}")
    terms_block = '\n'.join(lines)

    prompt = PROMPT_TEMPLATE.format(n_terms=len(candidates), terms_block=terms_block)
    print(f"  prompt size: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"\nCalling {args.model} (max_tokens={args.max_tokens:,})...", flush=True)
    started = time.time()
    parts = []
    last_print = 0; last_chars = 0; text_chars = 0
    with client.messages.stream(
        model=args.model, max_tokens=args.max_tokens,
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
    wall = time.time() - started
    in_p = 5 if 'opus' in args.model else 3
    out_p = 25 if 'opus' in args.model else 15
    cost = msg.usage.input_tokens/1e6*in_p + msg.usage.output_tokens/1e6*out_p
    print(f"\n  generation done: {len(raw):,} chars in {wall:.0f}s", flush=True)
    print(f"  tokens: {msg.usage.input_tokens:,}in / {msg.usage.output_tokens:,}out  cost ${cost:.3f}", flush=True)
    print(f"  stop reason: {msg.stop_reason}", flush=True)

    parsed = parse_json(raw)
    if not parsed:
        OUT_JSON.with_suffix('.raw.txt').write_text(raw)
        raise SystemExit(f"! Parse failed; raw saved to {OUT_JSON.with_suffix('.raw.txt')}")

    entries = parsed.get('entries', [])
    print(f"  entries returned: {len(entries)} (input had {len(candidates)})", flush=True)

    # Augment with corpus-frequency metadata
    by_surface = {r['canonical_surface']: r for r in candidates}
    for e in entries:
        m = by_surface.get(e.get('term'))
        if m:
            e['n_total_mentions'] = int(m['n_total_mentions'])
            e['n_unique_docs'] = int(m['n_unique_docs'])
            e['sources'] = m['sources']
            e['variants_sample'] = (m.get('all_variants') or '').split(' || ')[:5]

    OUT_JSON.write_text(json.dumps({
        'model': args.model, 'n_input': len(candidates), 'n_output': len(entries),
        'filters': {'top_n': args.top_n, 'min_docs': args.min_docs, 'patterns': args.patterns},
        'entries': entries,
    }, indent=2))

    # Categorise
    by_cat = {}
    for e in entries:
        by_cat.setdefault(e.get('category','?'), []).append(e)

    # Markdown rendering: alphabetic
    md = []
    md.append('# ARENA Corpus Glossary')
    md.append('')
    md.append(f'Auto-generated study-guide companion to ARENA project reports. Definitions are model-written; the empirical *scope* (which terms appear, ranked by document coverage) is set by the corpus.')
    md.append('')
    md.append(f'**Source:** {len(entries)} canonical surfaces extracted from 1,440 ARENA Knowledge Bank documents via regex + spaCy NER + transformer NER, filtered to acronyms appearing in ≥{args.min_docs} unique documents.')
    md.append(f'**Coverage:** top {len(entries)} entries by total mention count.')
    md.append(f'**Model:** {args.model} (definitions are priors-grounded; flagged-uncertain entries warrant corpus-grounded follow-up).')
    md.append('')
    # Category distribution
    cat_counts = {c: len(v) for c, v in by_cat.items()}
    md.append('## Category breakdown')
    md.append('')
    md.append('| category | n |')
    md.append('|---|---:|')
    for c in sorted(cat_counts, key=lambda k: -cat_counts[k]):
        md.append(f'| {c} | {cat_counts[c]} |')
    md.append('')
    n_uncertain = sum(1 for e in entries if e.get('uncertainty'))
    md.append(f'**{n_uncertain} entries** flagged uncertain (will warrant a corpus-grounded follow-up pass).')
    md.append('')

    # Glossary body — alphabetic, omitting noise
    md.append('## Entries')
    md.append('')
    glossary_entries = [e for e in entries if e.get('category') != 'noise']
    glossary_entries.sort(key=lambda e: e.get('term','').lower())
    for e in glossary_entries:
        term = e.get('term','?')
        expansion = e.get('expansion') or ''
        cat = e.get('category','?')
        defn = e.get('definition','')
        ctx = e.get('arena_context','')
        notes = e.get('notes')
        u = ' ⚠' if e.get('uncertainty') else ''
        n_m = e.get('n_total_mentions','?')
        n_d = e.get('n_unique_docs','?')
        head = f"### {term}"
        if expansion:
            head += f" — *{expansion}*"
        head += f"{u}"
        md.append(head)
        md.append('')
        md.append(f"**{cat}** · {n_m:,} mentions / {n_d:,} docs")
        md.append('')
        if defn:
            md.append(defn)
            md.append('')
        if ctx:
            md.append(f"*ARENA context:* {ctx}")
            md.append('')
        if notes:
            md.append(f"*Notes:* {notes}")
            md.append('')

    # Noise list at the end (compact)
    noise = [e for e in entries if e.get('category') == 'noise']
    if noise:
        md.append('## Filtered out as noise')
        md.append('')
        md.append('Surfaces caught by the entity pipeline but not glossary-worthy (sentence fragments, generic English, mis-segmented phrases):')
        md.append('')
        md.append(', '.join(f'`{e.get("term","")}`' for e in noise))
        md.append('')

    OUT_MD.write_text('\n'.join(md))
    print(f"  wrote {OUT_MD}", flush=True)
    print(f"  wrote {OUT_JSON}", flush=True)

    # Render HTML
    try:
        proc = subprocess.run(
            [sys.executable, str(MD2HTML), 'ARENA Corpus Glossary',
             'Broad Learnings · Study-guide companion'],
            input='\n'.join(md), capture_output=True, text=True, check=True,
        )
        OUT_HTML.write_text(proc.stdout)
        print(f"  wrote {OUT_HTML}", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"  md2html failed: {e.stderr.strip()}", flush=True)

    OUT_META.write_text(json.dumps({
        'model': args.model,
        'input_tokens': msg.usage.input_tokens,
        'output_tokens': msg.usage.output_tokens,
        'cost_sync': round(cost, 3),
        'wall_seconds': round(wall, 1),
        'stop_reason': msg.stop_reason,
        'prompt_chars': len(prompt),
        'output_chars': len(raw),
        'n_entries': len(entries),
        'n_uncertain': n_uncertain,
        'category_counts': cat_counts,
        'filters': {'top_n': args.top_n, 'min_docs': args.min_docs, 'patterns': args.patterns},
    }, indent=2))
    print(f"  wrote {OUT_META}", flush=True)


if __name__ == '__main__':
    main()
