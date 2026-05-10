"""Stage g04 — First-pass glossary define (LLM).

Generalises:
    pipeline/development/arena_glossary/04_glossary_pass.py

Reads entity_index from g03, filters to high-signal candidates by pattern +
unique-doc threshold, asks the configured LLM to produce structured glossary
entries.

Outputs:
    define.output_path                glossary.json
    sibling glossary.raw.txt          raw LLM response
    sibling glossary_meta.json        cost / tokens / wall

Domain config (domain.yaml glossary.define + glossary.prompt_tokens):
    define.model                       default 'claude-sonnet-4-6'
    define.max_tokens                  default 64000
    define.top_n                       top-N candidates by mentions, default 600
    define.min_unique_docs             default 5
    define.patterns                    default ['acronym']
    define.match_status                default 'unmatched'
    define.input_path                  default <normalise.output_path>
    define.output_path                 where to write glossary.json
"""
from __future__ import annotations
import argparse
import csv
import json
import time
from pathlib import Path

import anthropic

from pipeline.config import DomainConfig
from pipeline.glossary.shared.io import resolve
from pipeline.stages.shared.parse import parse_json_tolerant


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', required=True)
    args, _ = ap.parse_known_args()

    cfg = DomainConfig.load(args.domain)
    d = (cfg.glossary.get('define') or {})
    nrm = (cfg.glossary.get('normalise') or {})

    input_path = resolve(d.get('input_path') or nrm.get('output_path') or '')
    if not input_path.exists():
        raise SystemExit(f'entity_index missing: {input_path}')

    output_path = resolve(d.get('output_path') or '')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path = output_path.with_suffix('.raw.txt')
    meta_path = output_path.parent / 'glossary_meta.json'

    model = d.get('model', 'claude-sonnet-4-6')
    max_tokens = int(d.get('max_tokens', 64000))
    top_n = int(d.get('top_n', 600))
    min_docs = int(d.get('min_unique_docs', 5))
    patterns = list(d.get('patterns', ['acronym']))
    match_status_filter = d.get('match_status', 'unmatched')

    print(f"Loading {input_path} ...", flush=True)
    rows = list(csv.DictReader(open(input_path)))
    print(f"  total entities: {len(rows):,}", flush=True)

    candidates = [
        r for r in rows
        if (not match_status_filter or r['match_status'] == match_status_filter)
        and r['pattern'] in patterns
        and int(r['n_unique_docs']) >= min_docs
    ]
    candidates.sort(key=lambda r: -int(r['n_total_mentions']))
    candidates = candidates[:top_n]
    print(f"  filtered to top-{top_n} {patterns} ≥{min_docs} docs: "
          f"{len(candidates)} entries", flush=True)

    lines = []
    for r in candidates:
        variants = (r.get('all_variants') or '').replace('\n', ' ')[:200]
        lines.append(
            f"[{r['canonical_surface']}] ({r['n_total_mentions']}m, "
            f"{r['n_unique_docs']}d)  variants: {variants}"
        )
    terms_block = '\n'.join(lines)

    prompt = cfg.prompt(
        'prompt', stage='g04_define',
        n_terms=len(candidates),
        terms_block=terms_block,
        glossary_purpose=cfg.prompt_tokens.get('glossary_purpose', ''),
        corpus_full_name=cfg.prompt_tokens.get('corpus_full_name', cfg.domain.full_name),
        corpus_short_description=cfg.prompt_tokens.get('corpus_short_description', cfg.domain.full_name),
        audience_persona=cfg.prompt_tokens.get('audience_persona', 'analyst'),
        style_guidance=cfg.prompt_tokens.get('style_guidance', 'Use domain-appropriate terminology.'),
    )
    print(f"  prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"\nCalling {model} (max_tokens={max_tokens:,}) ...", flush=True)
    started = time.time()
    parts = []
    last_print = 0; last_chars = 0; text_chars = 0
    with client.messages.stream(
        model=model, max_tokens=max_tokens,
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

    in_p = 5 if 'opus' in model else 3
    out_p = 25 if 'opus' in model else 15
    cost = msg.usage.input_tokens / 1e6 * in_p + msg.usage.output_tokens / 1e6 * out_p
    print(f"\n  done: {len(raw):,} chars in {wall:.0f}s; "
          f"{msg.usage.input_tokens:,}in/{msg.usage.output_tokens:,}out ${cost:.3f}; "
          f"stop={msg.stop_reason}", flush=True)

    parsed = parse_json_tolerant(raw)
    if not parsed:
        raise SystemExit(f"parse failed; raw at {raw_path}")
    entries = parsed.get('entries', [])
    print(f"  entries returned: {len(entries)} (input had {len(candidates)})", flush=True)

    by_surf = {r['canonical_surface']: r for r in candidates}
    for e in entries:
        m = by_surf.get(e.get('term'))
        if m:
            e['n_total_mentions'] = int(m['n_total_mentions'])
            e['n_unique_docs'] = int(m['n_unique_docs'])
            e['sources'] = m['sources']
            e['variants_sample'] = (m.get('all_variants') or '').split(' || ')[:5]

    output_path.write_text(json.dumps({
        'model': model, 'n_input': len(candidates), 'n_output': len(entries),
        'filters': {'top_n': top_n, 'min_docs': min_docs, 'patterns': patterns},
        'entries': entries,
    }, indent=2))

    meta_path.write_text(json.dumps({
        'model': model,
        'input_tokens': msg.usage.input_tokens,
        'output_tokens': msg.usage.output_tokens,
        'cost_sync': round(cost, 3),
        'wall_seconds': round(wall, 1),
        'stop_reason': msg.stop_reason,
        'n_entries': len(entries),
        'filters': {'top_n': top_n, 'min_docs': min_docs, 'patterns': patterns},
    }, indent=2))

    print(f"\nWrote:\n  {output_path}\n  {raw_path}\n  {meta_path}", flush=True)


if __name__ == '__main__':
    main()
