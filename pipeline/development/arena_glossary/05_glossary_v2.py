#!/usr/bin/env python3
"""Glossary v2 builder — compact-schema follow-up passes.

Three modes:
  --mode tail        — recover the 95 acronyms truncated from v1
  --mode titlecase   — top-300 titlecase entries (orgs, programmes, standards)
  --mode reground    — re-ground v1's 100 uncertain entries with corpus context

Each mode writes a separate output JSON; the merge script (06) combines
them with v1's confident entries to produce the final glossary.

Compact JSON schema (saves ~40% output tokens vs v1):
  t = term, e = expansion (null ok), c = category,
  d = definition (HARD CAP 30 words),
  x = arena_context (only for n_unique_docs ≥ 50; else null),
  n = notes (null ok), u = uncertainty (bool).
"""
from __future__ import annotations
import argparse
import json
import os
import random
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / 'output'
PER_DOC = Path('/home/jeffzda/broadlearnings/corpora/arena/output/per_doc')

CATEGORIES = ('technology', 'market', 'regulation', 'organisation',
              'programme', 'standard', 'concept', 'location', 'unit',
              'event', 'person', 'noise')


PROMPT_BASE = """# ARENA corpus glossary — {mode_label}

Producing a study-guide glossary for the ARENA (Australian Renewable Energy Agency) project corpus. Each input term was extracted from ARENA-funded project documentation and ranked by frequency.

## Schema (compact — single-letter keys)

For each input term, return one JSON entry with these fields:

- `t`: the canonical surface, exactly as given.
- `e`: full expansion of the abbreviation/term. null if no plausible expansion (it's a name not an acronym, or it's noise).
- `c`: ONE of: technology, market, regulation, organisation, programme, standard, concept, location, unit, event, person, noise.
- `d`: plain-English definition in the Australian renewables / electricity-market context. **HARD CAP: 30 words. No exceptions.** null if `c` is `noise`.
- `x`: ONE short sentence on how the term shows up in ARENA project documentation. **Only populate if the term has high coverage (≥50 unique docs in input metadata); else null.**
- `n`: notes — ambiguity flags or important sub-terms. null if none.
- `u`: true if you're not confident in the expansion or definition; false otherwise.

## Style

- Australian English spelling.
- Australian-specific definitions where the global term differs.
- Be honest about noise — sentence fragments, generic English mis-caught, ambiguous abbreviations → `c: noise`, `d: null`.
- Don't pad. null over "N/A".
- Don't invent ARENA programmes; if unsure, set `u: true`.

## Output

Strict JSON, no extra text:

```json
{{"entries": [{{"t":"DER","e":"Distributed Energy Resources","c":"technology","d":"Small-scale generation, storage, or controllable load assets at the distribution network level — solar, batteries, EVs, smart appliances.","x":"Core ARENA portfolio theme; appears in DER orchestration trials and grid integration studies.","n":null,"u":false}}]}}
```

One entry per input term, in input order.

{mode_specific_block}

## Input — {n_terms} terms

{terms_block}
"""


MODE_BLOCKS = {
    'tail': "These are the lowest-frequency acronyms from the top-600 cohort that the v1 pass truncated before reaching. Same task as v1: produce a glossary entry for each.",
    'titlecase': "These are titlecase surfaces (organisation names, programme names, standards, conference names, concept phrases) that the entity pipeline caught with title-case proper-noun matching. Many will be ARENA programmes (Advancing Renewables Program), Australian organisations (Western Power, AEMO units), market mechanisms named in caps, or standards bodies. Some will be project-specific names that the portfolio catalogue should already cover — for those, set `c: noise` since they don't belong in a generic glossary. Person names → `c: person`. Locations → `c: location`. Single-occurrence project codenames → `c: noise`.",
    'reground': "These are entries the v1 pass flagged as uncertain. For each, you have the v1 model's first attempt (in the input metadata) PLUS up to 3 sample narrative snippets from the corpus where the term actually appears. Use the corpus context to confirm or correct the v1 expansion/definition. If the corpus context resolves the ambiguity → set `u: false`. If still ambiguous after seeing the context → keep `u: true` and explain in `n`.",
}


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
    except Exception:
        return None


def recover_partial(raw: str):
    """Recover any complete entries even if the JSON tail truncated."""
    r = raw.strip()
    if r.startswith('```'):
        r = r.split('\n', 1)[1] if '\n' in r else r
        if r.endswith('```'): r = r.rsplit('```', 1)[0]
    m = re.search(r'"entries"\s*:\s*\[', r)
    if not m: return []
    i = m.end()
    entries = []; depth = 0; buf = []; in_str = False; esc = False
    while i < len(r):
        ch = r[i]
        if esc: buf.append(ch); esc = False; i += 1; continue
        if in_str:
            if ch == '\\': buf.append(ch); esc = True; i += 1; continue
            if ch == '"': in_str = False
            buf.append(ch); i += 1; continue
        if ch == '"':
            in_str = True; buf.append(ch); i += 1; continue
        if ch == '{':
            if depth == 0: buf = []
            depth += 1; buf.append(ch); i += 1; continue
        if ch == '}':
            depth -= 1; buf.append(ch); i += 1
            if depth == 0:
                try: entries.append(json.loads(''.join(buf)))
                except Exception: pass
            continue
        if depth > 0: buf.append(ch)
        i += 1
    return entries


def build_terms_block_basic(items):
    """For tail / titlecase: surface + freq + variants."""
    lines = []
    for it in items:
        v = (it.get('all_variants') or '').replace('\n', ' ')[:200]
        lines.append(f"[{it['surface']}] ({it['n_total_mentions']}m, {it['n_unique_docs']}d) variants: {v}")
    return '\n'.join(lines)


def _load_corpus_snippets(surface, max_snippets=3, max_chars=300):
    """Find up to N narrative snippets where the surface appears (case-sensitive,
    word boundary). Looks in per_doc/*.json across all records' narrative+evidence."""
    pattern = re.compile(r'(?<![A-Za-z0-9])' + re.escape(surface) + r'(?![A-Za-z0-9])')
    snippets = []
    seen_docs = set()
    for fn in sorted(os.listdir(PER_DOC)):
        if len(snippets) >= max_snippets: break
        if not fn.startswith('doc_'): continue
        try:
            d = json.load(open(PER_DOC / fn))
        except Exception:
            continue
        for rec in d.get('records', []):
            if len(snippets) >= max_snippets: break
            doc_id = rec.get('doc_id') or fn.replace('.json','')
            if doc_id in seen_docs: continue
            for field in ('narrative', 'evidence'):
                text = (rec.get(field) or '').strip()
                if not text: continue
                m = pattern.search(text)
                if m:
                    s = max(0, m.start()-80)
                    e = min(len(text), m.end()+200)
                    snip = text[s:e].strip()
                    if len(snip) > max_chars: snip = snip[:max_chars] + '…'
                    snippets.append((rec.get('id', '?'), snip))
                    seen_docs.add(doc_id)
                    break
    return snippets


def build_terms_block_reground(items):
    """For reground: v1 attempt + corpus snippets."""
    lines = []
    for it in items:
        surf = it['surface']
        snips = _load_corpus_snippets(surf)
        lines.append(f"\n[{surf}] (n_mentions={it.get('n_total_mentions')}, "
                     f"n_docs={it.get('n_unique_docs')})")
        v1e = it.get('v1_expansion') or 'null'
        v1c = it.get('v1_category', '?')
        v1d = (it.get('v1_definition') or '')[:200]
        lines.append(f"  v1: e={v1e!r} c={v1c} d={v1d!r}")
        if it.get('v1_notes'):
            lines.append(f"  v1_notes: {it['v1_notes']}")
        if snips:
            lines.append(f"  corpus context:")
            for rid, s in snips:
                lines.append(f"    [{rid}] {s}")
        else:
            lines.append(f"  corpus context: (no snippets found)")
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', required=True, choices=['tail','titlecase','reground'])
    ap.add_argument('--model', default='claude-sonnet-4-6')
    ap.add_argument('--max-tokens', type=int, default=64000)
    args = ap.parse_args()

    in_path = INPUT_DIR / f'glossary_v2_{args.mode}_input.json'
    out_path = INPUT_DIR / f'glossary_v2_{args.mode}.json'
    raw_path = INPUT_DIR / f'glossary_v2_{args.mode}.raw.txt'
    items = json.load(open(in_path))
    print(f"loaded {len(items)} items from {in_path.name}", flush=True)

    if args.mode == 'reground':
        terms_block = build_terms_block_reground(items)
    else:
        terms_block = build_terms_block_basic(items)

    prompt = PROMPT_BASE.format(
        mode_label=args.mode,
        n_terms=len(items),
        mode_specific_block=MODE_BLOCKS[args.mode],
        terms_block=terms_block,
    )
    print(f"prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"calling {args.model} ...", flush=True)
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
    raw_path.write_text(raw)
    wall = time.time() - started
    in_p = 5 if 'opus' in args.model else 3
    out_p = 25 if 'opus' in args.model else 15
    cost = msg.usage.input_tokens/1e6*in_p + msg.usage.output_tokens/1e6*out_p
    print(f"\ndone: {len(raw):,} chars in {wall:.0f}s; "
          f"{msg.usage.input_tokens:,}in/{msg.usage.output_tokens:,}out ${cost:.3f}; "
          f"stop={msg.stop_reason}", flush=True)

    parsed = parse_json(raw)
    if parsed and 'entries' in parsed:
        entries = parsed['entries']
    else:
        entries = recover_partial(raw)
        print(f"  partial parse: {len(entries)} entries recovered", flush=True)

    json.dump({
        'mode': args.mode, 'model': args.model,
        'n_input': len(items), 'n_returned': len(entries),
        'stop_reason': msg.stop_reason,
        'cost_sync': round(cost,3), 'wall_seconds': round(wall,1),
        'input_tokens': msg.usage.input_tokens,
        'output_tokens': msg.usage.output_tokens,
        'entries': entries,
    }, open(out_path,'w'), indent=2)
    print(f"  wrote {out_path}", flush=True)


if __name__ == '__main__':
    main()
