"""Stage g05 — Compact-schema follow-up glossary passes.

Generalises:
    pipeline/development/arena_glossary/05_glossary_v2.py

Three modes:
    --mode tail        recover acronyms truncated from the initial pass
    --mode titlecase   define titlecase surfaces (orgs, programmes, etc.)
    --mode reground    re-ground uncertain entries with corpus snippets

Inputs (in glossary.define_followups.output_dir):
    glossary_v2_tail_input.json
    glossary_v2_titlecase_input.json
    glossary_v2_reground_input.json     (with v1_* metadata + per-doc available)

Outputs (per mode):
    glossary_v2_<mode>.json
    glossary_v2_<mode>.raw.txt

Domain config (domain.yaml glossary.define_followups):
    model               default 'claude-sonnet-4-6'
    max_tokens          default 64000
    output_dir          required
    per_doc_dir         optional, for reground corpus-snippet lookup
    record_text_fields  default ['narrative', 'evidence']
"""
from __future__ import annotations
import argparse
import json
import os
import re
import time
from pathlib import Path

import anthropic

from pipeline.config import DomainConfig
from pipeline.glossary.shared.io import resolve
from pipeline.stages.shared.parse import parse_json_tolerant


def _recover_partial(raw: str):
    r = raw.strip()
    if r.startswith('```'):
        r = r.split('\n', 1)[1] if '\n' in r else r
        if r.endswith('```'):
            r = r.rsplit('```', 1)[0]
    m = re.search(r'"entries"\s*:\s*\[', r)
    if not m:
        return []
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


def _build_basic(items):
    lines = []
    for it in items:
        v = (it.get('all_variants') or '').replace('\n', ' ')[:200]
        lines.append(
            f"[{it['surface']}] ({it['n_total_mentions']}m, {it['n_unique_docs']}d) "
            f"variants: {v}"
        )
    return '\n'.join(lines)


def _load_corpus_snippets(surface: str, per_doc_dir: Path,
                          text_fields: list[str], max_snippets: int = 3,
                          max_chars: int = 300):
    if not per_doc_dir.exists():
        return []
    pattern = re.compile(r'(?<![A-Za-z0-9])' + re.escape(surface) + r'(?![A-Za-z0-9])')
    snippets = []
    seen_docs = set()
    for fn in sorted(os.listdir(per_doc_dir)):
        if len(snippets) >= max_snippets:
            break
        if not fn.endswith('.json'):
            continue
        try:
            d = json.load(open(per_doc_dir / fn))
        except Exception:
            continue
        for rec in d.get('records', []):
            if len(snippets) >= max_snippets:
                break
            doc_id = (rec.get('doc_id') or rec.get('_doc_slug')
                      or fn.replace('.json', ''))
            if doc_id in seen_docs:
                continue
            for field in text_fields:
                text = (rec.get(field) or '').strip()
                if not text:
                    continue
                m = pattern.search(text)
                if m:
                    s = max(0, m.start() - 80)
                    e = min(len(text), m.end() + 200)
                    snip = text[s:e].strip()
                    if len(snip) > max_chars:
                        snip = snip[:max_chars] + '…'
                    snippets.append((rec.get('id', '?'), snip))
                    seen_docs.add(doc_id)
                    break
    return snippets


def _build_reground(items, per_doc_dir: Path, text_fields: list[str]):
    lines = []
    for it in items:
        surf = it['surface']
        snips = _load_corpus_snippets(surf, per_doc_dir, text_fields)
        lines.append(
            f"\n[{surf}] (n_mentions={it.get('n_total_mentions')}, "
            f"n_docs={it.get('n_unique_docs')})"
        )
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
    ap.add_argument('--domain', required=True)
    ap.add_argument('--mode', required=True, choices=['tail', 'titlecase', 'reground'])
    args, _ = ap.parse_known_args()

    cfg = DomainConfig.load(args.domain)
    f = (cfg.glossary.get('define_followups') or {})
    out_dir = resolve(f.get('output_dir') or '')
    out_dir.mkdir(parents=True, exist_ok=True)

    in_path = out_dir / f'glossary_v2_{args.mode}_input.json'
    out_path = out_dir / f'glossary_v2_{args.mode}.json'
    raw_path = out_dir / f'glossary_v2_{args.mode}.raw.txt'
    if not in_path.exists():
        raise SystemExit(f'input missing: {in_path}')

    items = json.load(open(in_path))
    print(f"loaded {len(items)} items from {in_path.name}", flush=True)

    if args.mode == 'reground':
        per_doc_dir = resolve(f.get('per_doc_dir') or '')
        text_fields = list(f.get('record_text_fields', ['narrative', 'evidence']))
        terms_block = _build_reground(items, per_doc_dir, text_fields)
    else:
        terms_block = _build_basic(items)

    prompt = cfg.prompt(
        f'prompt_{args.mode}', stage='g05_define_followups',
        n_terms=len(items),
        terms_block=terms_block,
        corpus_full_name=cfg.prompt_tokens.get('corpus_full_name', cfg.domain.full_name),
        corpus_short_description=cfg.prompt_tokens.get('corpus_short_description', cfg.domain.full_name),
        style_guidance=cfg.prompt_tokens.get('style_guidance', 'Use domain-appropriate terminology.'),
    )
    print(f"prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    model = f.get('model', 'claude-sonnet-4-6')
    max_tokens = int(f.get('max_tokens', 64000))

    client = anthropic.Anthropic()
    print(f"calling {model} ({args.mode}) ...", flush=True)
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
    if parsed and 'entries' in parsed:
        entries = parsed['entries']
    else:
        entries = _recover_partial(raw)
        print(f"  partial parse: {len(entries)} entries recovered", flush=True)

    json.dump({
        'mode': args.mode, 'model': model,
        'n_input': len(items), 'n_returned': len(entries),
        'stop_reason': msg.stop_reason,
        'cost_sync': round(cost, 3), 'wall_seconds': round(wall, 1),
        'input_tokens': msg.usage.input_tokens,
        'output_tokens': msg.usage.output_tokens,
        'entries': entries,
    }, open(out_path, 'w'), indent=2)
    print(f"  wrote {out_path}", flush=True)


if __name__ == '__main__':
    main()
