"""Stage g08 — Apply subcategorisation to glossary entries (LLM, single call).

Generalises:
    pipeline/development/arena_glossary/08_apply_subclustering.py

Reads merged glossary + g07 proposal, asks the LLM to assign each entry in
a refined category to one of the proposed subcategories.

Outputs:
    subcategory.output_dir/glossary_subcategories.json
    subcategory.output_dir/glossary_subcategories.raw.txt

Domain config (domain.yaml glossary.subcategory):
    apply_model               default 'claude-sonnet-4-6'
    max_tokens                default 32000
    refine_categories         which categories were refined (must match g07)
    output_dir
"""
from __future__ import annotations
import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path

import anthropic

from pipeline.config import DomainConfig
from pipeline.glossary.shared.io import resolve
from pipeline.stages.shared.parse import parse_json_tolerant


def _fmt_taxonomy(prop, refine):
    out = []
    for cat in refine:
        if cat not in prop:
            continue
        out.append(f"\n### {cat}")
        for s in prop[cat].get('subcategories', []):
            out.append(f"- **{s.get('name', '?')}**: {s.get('description', '')}")
    return '\n'.join(out)


def _fmt_entries(entries_by_cat, refine):
    out = []
    for cat in refine:
        e = entries_by_cat.get(cat, [])
        if not e:
            continue
        out.append(f"\n### {cat} ({len(e)} entries)")
        for ent in e:
            term = ent['term']
            exp = ent.get('expansion') or ''
            defn = (ent.get('definition') or '').replace('\n', ' ')[:120]
            out.append(f"[{term}] {exp} — {defn}")
    return '\n'.join(out)


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

    proposal_path = out_dir / 'glossary_subclustering_proposal.json'
    if not proposal_path.exists():
        raise SystemExit(f'proposal missing (run g07 first): {proposal_path}')

    out_path = out_dir / 'glossary_subcategories.json'
    raw_path = out_dir / 'glossary_subcategories.raw.txt'

    refine = list(s.get('refine_categories') or [])
    if not refine:
        raise SystemExit('glossary.subcategory.refine_categories must be set')
    model = s.get('apply_model', 'claude-sonnet-4-6')
    max_tokens = int(s.get('max_tokens', 32000))

    glossary = json.load(open(glossary_path))
    proposal = json.load(open(proposal_path))
    entries_by_cat: dict[str, list] = {}
    for e in glossary['entries']:
        c = e.get('category')
        if c in refine:
            entries_by_cat.setdefault(c, []).append(e)
    n_total = sum(len(v) for v in entries_by_cat.values())

    prompt = cfg.prompt(
        'prompt', stage='g08_subcategory_apply',
        taxonomy_block=_fmt_taxonomy(proposal, refine),
        entries_block=_fmt_entries(entries_by_cat, refine),
        n_total=n_total,
        corpus_full_name=cfg.prompt_tokens.get('corpus_full_name', cfg.domain.full_name),
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
        ents = []
        for mm in re.finditer(r'\{\s*"t"\s*:\s*"([^"]+)"\s*,\s*"s"\s*:\s*"([^"]+)"\s*\}', raw):
            ents.append({'t': mm.group(1), 's': mm.group(2)})
        parsed = {'assignments': ents}
        print(f"  recovered {len(ents)} via regex", flush=True)

    assignments = parsed.get('assignments', [])
    json.dump({
        'model': model, 'n_input': n_total, 'n_returned': len(assignments),
        'cost_sync': round(cost, 3), 'wall_seconds': round(wall, 1),
        'assignments': assignments,
    }, open(out_path, 'w'), indent=2)
    print(f"  wrote {out_path}", flush=True)

    by_sub = Counter(a['s'] for a in assignments)
    print(f"\nsubcategory distribution:")
    for sub, n in by_sub.most_common():
        print(f"  {n:>4}  {sub}")


if __name__ == '__main__':
    main()
