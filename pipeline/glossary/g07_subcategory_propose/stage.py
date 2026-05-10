"""Stage g07 — Propose subcategorisation for large glossary categories (LLM).

Generalises:
    pipeline/development/arena_glossary/07_propose_subclustering.py

Reads merged glossary, filters to refine_categories, asks LLM for 4-8 subs/cat.

Inputs:
    glossary.merge.output_path        merged glossary.json

Outputs:
    subcategory.output_dir/glossary_subclustering_input.json
    subcategory.output_dir/glossary_subclustering_proposal.json
    subcategory.output_dir/glossary_subclustering_proposal.raw.txt

Domain config (domain.yaml glossary.subcategory):
    propose_model              default 'claude-sonnet-4-6'
    max_tokens                 default 16000
    refine_categories          list of category names to subcluster
    min_entries_per_category   skip categories below this size
    output_dir                 where to write proposal artefacts
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path

import anthropic

from pipeline.config import DomainConfig
from pipeline.glossary.shared.io import resolve
from pipeline.stages.shared.parse import parse_json_tolerant


def _fmt_entries(entries, max_def=140):
    lines = []
    entries = sorted(entries, key=lambda e: -(e.get('n_unique_docs') or 0))
    for e in entries:
        defn = (e.get('definition') or '').replace('\n', ' ')[:max_def]
        exp = e.get('expansion') or '(no expansion)'
        n_d = e.get('n_unique_docs', 0)
        lines.append(f"[{e['term']}] {exp} | {n_d}d | {defn}")
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', required=True)
    args, _ = ap.parse_known_args()

    cfg = DomainConfig.load(args.domain)
    s = (cfg.glossary.get('subcategory') or {})
    m = (cfg.glossary.get('merge') or {})

    glossary_path = resolve(m.get('output_path') or '')
    if not glossary_path.exists():
        raise SystemExit(f'merged glossary missing: {glossary_path}')

    out_dir = resolve(s.get('output_dir') or glossary_path.parent)
    out_dir.mkdir(parents=True, exist_ok=True)
    input_snap = out_dir / 'glossary_subclustering_input.json'
    proposal_path = out_dir / 'glossary_subclustering_proposal.json'
    raw_path = out_dir / 'glossary_subclustering_proposal.raw.txt'

    refine = list(s.get('refine_categories') or [])
    if not refine:
        raise SystemExit('glossary.subcategory.refine_categories must be set')
    min_size = int(s.get('min_entries_per_category', 0))
    model = s.get('propose_model', 'claude-sonnet-4-6')
    max_tokens = int(s.get('max_tokens', 16000))

    glossary = json.load(open(glossary_path))
    by_cat: dict[str, list] = {c: [] for c in refine}
    for e in glossary['entries']:
        c = e.get('category')
        if c in by_cat:
            by_cat[c].append(e)

    eligible = {c: lst for c, lst in by_cat.items() if len(lst) >= min_size}
    if not eligible:
        sizes = {c: len(v) for c, v in by_cat.items()}
        raise SystemExit(f'no eligible categories (need >={min_size}): {sizes}')
    print(f"Refining {len(eligible)} categories: "
          f"{ {c: len(v) for c, v in eligible.items()} }", flush=True)

    json.dump(eligible, open(input_snap, 'w'), indent=2)

    blocks = []
    for cat, entries in eligible.items():
        blocks.append(f"\n### {cat} — {len(entries)} entries\n")
        blocks.append(_fmt_entries(entries))
    categories_block = '\n'.join(blocks)

    prompt = cfg.prompt(
        'prompt', stage='g07_subcategory_propose',
        categories_block=categories_block,
        corpus_full_name=cfg.prompt_tokens.get('corpus_full_name', cfg.domain.full_name),
        audience_persona=cfg.prompt_tokens.get('audience_persona', 'analyst'),
    )
    print(f"prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"calling {model} ...", flush=True)
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
    print(f"\ndone: {len(raw):,} chars in {wall:.0f}s; "
          f"{msg.usage.input_tokens:,}in/{msg.usage.output_tokens:,}out ${cost:.3f}; "
          f"stop={msg.stop_reason}", flush=True)

    parsed = parse_json_tolerant(raw)
    if not parsed:
        raise SystemExit(f"parse failed; raw at {raw_path}")
    json.dump(parsed, open(proposal_path, 'w'), indent=2)

    for cat in refine:
        if cat not in parsed:
            continue
        subs = parsed[cat].get('subcategories', [])
        print(f"\n=== {cat} → {len(subs)} subcategories ===")
        for sub in subs:
            print(f"  - {sub.get('name', '?')}: {sub.get('description', '')[:90]}")
            ex = sub.get('examples', [])
            print(f"      e.g. {', '.join(ex[:5])}")

    print(f"\nWrote:\n  {input_snap}\n  {proposal_path}\n  {raw_path}", flush=True)


if __name__ == '__main__':
    main()
