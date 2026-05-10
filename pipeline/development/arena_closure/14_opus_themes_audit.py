#!/usr/bin/env python3
"""Pass 3 of the v2 parent-archetype roll-up.

Single one-shot Opus 4.7 call that:
  (a) audits the candidate parent set from Pass 1 (per-parent verdict:
      keep / split / merge / drop, plus mechanism-coherence and
      population-fit calls); and
  (b) groups the parents into a smaller set of higher-level themes
      ("themes derived from mechanism similarity, not from parent names").

Mirrors legacy/code/stage_5_parent_taxonomy/71_audit_and_group_opus.py
exactly, with v2 cluster schema (canonical_name + mechanism_signature,
no description field).

Inputs:
  - parents_v1.json
  - cluster_to_parent_assignments.jsonl
  - catalogue_after_convergence.json
  - prompts/14_themes_audit.md

Outputs:
  - themes_and_parent_audit_v1.json
  - themes_and_parent_audit_v1_meta.json

Cost target: ~$2.70 (120k in / 12k out @ Opus 4.7).
Wall: ~3 min streaming.
"""
from __future__ import annotations
import json
import time
from collections import Counter
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / 'output/sweep/convergence/catalogue_after_convergence.json'
PARENTS = ROOT / 'closure/output/parents_v1.json'
ASSIGNMENTS = ROOT / 'closure/output/cluster_to_parent_assignments.jsonl'
PROMPT_FILE = ROOT / 'closure/prompts/14_themes_audit.md'
OUT = ROOT / 'closure/output/themes_and_parent_audit_v1.json'
META = ROOT / 'closure/output/themes_and_parent_audit_v1_meta.json'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 128000
# Opus 4.7 (1M context, claude-opus-4-7) pricing
PRICE_IN_PER_M = 5
PRICE_OUT_PER_M = 25


def build_parent_block(parents: list[dict]) -> str:
    out = []
    for p in parents:
        out.append(f"### {p.get('parent_id', '?')}: {p.get('name', '?')}")
        out.append(f"Description: {p.get('description', '')}")
        out.append(f"Mechanism criterion: {p.get('mechanism_criterion', '')}")
        out.append("")
    return '\n'.join(out)


def build_assignment_block(assigns: list[dict]) -> str:
    """Compact one-line-per-cluster: cluster_id -> parent_id (confidence)."""
    lines = []
    for a in assigns:
        cid = a.get('cluster_id', '?')
        pid = a.get('parent_id', '?')
        conf = a.get('confidence', '?')
        lines.append(f"  {cid} -> {pid} ({conf})")
    return '\n'.join(lines)


def build_cluster_block(clusters: list[dict]) -> str:
    lines = []
    for c in clusters:
        cid = c['cluster_id']
        name = (c.get('canonical_name') or '').replace('|', '/').strip()
        sig = (c.get('mechanism_signature') or '').replace('|', '/').replace('\n', ' ').strip()
        n = len(c.get('supporting_record_ids', []))
        lines.append(f"  {cid} | {name} | {sig} | {n}")
    return '\n'.join(lines)


def parse_json(raw: str) -> dict | None:
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
    print("Loading inputs...", flush=True)
    cat = json.load(CATALOGUE.open())
    clusters = cat['clusters']
    parents_data = json.load(PARENTS.open())
    parents = parents_data.get('parents', [])
    if not parents:
        raise SystemExit(f"No parents found in {PARENTS}; run 12_opus_derive_parents.py first")
    if not ASSIGNMENTS.exists():
        raise SystemExit(f"No assignments at {ASSIGNMENTS}; run 13_opus_assign_clusters.py first")
    assigns = [json.loads(l) for l in ASSIGNMENTS.open()]
    print(f"  {len(clusters)} clusters, {len(parents)} parents, {len(assigns)} assignments",
          flush=True)

    prompt_template = PROMPT_FILE.read_text()
    parent_block = build_parent_block(parents)
    assignment_block = build_assignment_block(assigns)
    cluster_block = build_cluster_block(clusters)
    prompt = (prompt_template
              .replace('{parent_block}', parent_block)
              .replace('{assignment_block}', assignment_block)
              .replace('{cluster_block}', cluster_block))
    print(f"  Prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tokens)", flush=True)

    print(f"\nCalling {MODEL} (max_tokens={MAX_TOKENS:,})...", flush=True)
    client = anthropic.Anthropic()
    parts = []
    started = time.time()
    last_print = started; last_chars = 0; text_chars = 0
    with client.messages.stream(
        model=MODEL, max_tokens=MAX_TOKENS,
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

    in_tok = msg.usage.input_tokens
    out_tok = msg.usage.output_tokens
    cost = in_tok / 1e6 * PRICE_IN_PER_M + out_tok / 1e6 * PRICE_OUT_PER_M
    print(f"\n  Wall: {wall:.0f}s  in/out tokens: {in_tok:,}/{out_tok:,}  cost ${cost:.3f}",
          flush=True)
    print(f"  Stop reason: {msg.stop_reason}", flush=True)
    if msg.stop_reason != 'end_turn':
        print(f"  ! Stop reason was {msg.stop_reason!r} — output may be truncated", flush=True)

    parsed = parse_json(raw)
    if not parsed:
        OUT.with_suffix('.raw.json').write_text(json.dumps({'raw_response': raw}, indent=2))
        raise SystemExit(f"! Parse failed; raw saved to {OUT.with_suffix('.raw.json')}")

    audit = parsed.get('audit', {})
    themes = parsed.get('themes', [])
    unthemed = parsed.get('unthemed_parents', [])
    per = audit.get('per_parent', [])
    missing = audit.get('missing_mechanism_classes', [])

    verdicts = Counter(p.get('verdict', '?') for p in per)
    coherence = Counter(p.get('mechanism_coherence', '?') for p in per)
    pop_fit = Counter(p.get('population_fit', '?') for p in per)

    # Coverage check: every parent must appear exactly once across themes + unthemed
    valid_pids = {p.get('parent_id') for p in parents}
    in_themes = [pid for t in themes for pid in t.get('parent_ids', [])]
    in_themes_set = set(in_themes)
    in_unthemed_set = {u.get('parent_id') for u in unthemed}
    duplicated = [pid for pid, n in Counter(in_themes).items() if n > 1]
    missing_pids = valid_pids - in_themes_set - in_unthemed_set
    extra_pids = (in_themes_set | in_unthemed_set) - valid_pids

    print(f"\n========== AUDIT ==========")
    print(f"Verdicts:    {dict(verdicts)}")
    print(f"Coherence:   {dict(coherence)}")
    print(f"Pop fit:     {dict(pop_fit)}")
    print(f"Missing classes flagged: {len(missing)}")
    for m in missing[:5]:
        print(f"  - {m.get('name', '?')}: {m.get('description', '')[:120]}")

    print(f"\n========== THEMES ({len(themes)}) ==========")
    for t in themes:
        print(f"  [{t.get('theme_id', '?')}] {t.get('name', '?')}  "
              f"({len(t.get('parent_ids', []))} parents)")
        print(f"      {t.get('mechanism_family', '')[:100]}")
    if unthemed:
        print(f"\nUnthemed parents: {len(unthemed)}")
        for u in unthemed:
            print(f"  - [{u.get('parent_id', '?')}]: {u.get('reason', '')[:80]}")

    print(f"\n========== COVERAGE ==========")
    print(f"  Parents in themes: {len(in_themes_set)} / {len(valid_pids)}")
    print(f"  Parents unthemed:  {len(in_unthemed_set)}")
    if missing_pids:
        print(f"  ! Parents with no theme AND not unthemed: {sorted(missing_pids)}")
    if duplicated:
        print(f"  ! Parents in multiple themes: {duplicated}")
    if extra_pids:
        print(f"  ! Theme/unthemed lists reference unknown parent_ids: {sorted(extra_pids)}")

    OUT.write_text(json.dumps(parsed, indent=2))
    print(f"\nWrote {OUT}", flush=True)

    META.write_text(json.dumps({
        'model': MODEL,
        'max_tokens': MAX_TOKENS,
        'input_tokens': in_tok,
        'output_tokens': out_tok,
        'cost_usd': round(cost, 4),
        'wall_seconds': round(wall, 1),
        'stop_reason': msg.stop_reason,
        'prompt_chars': len(prompt),
        'output_chars': len(raw),
        'n_parents_input': len(parents),
        'n_themes_output': len(themes),
        'n_unthemed_output': len(unthemed),
        'n_missing_classes_flagged': len(missing),
        'verdict_distribution': dict(verdicts),
        'coherence_distribution': dict(coherence),
        'population_fit_distribution': dict(pop_fit),
        'parents_uncovered': sorted(missing_pids),
        'parents_duplicated_in_themes': duplicated,
        'parent_ids_unknown_referenced': sorted(extra_pids),
    }, indent=2))
    print(f"Wrote {META}", flush=True)


if __name__ == '__main__':
    main()
