#!/usr/bin/env python3
"""Pass 2 (v2-extended): assign every one of 1,141 v2 mechanism clusters
to exactly one of the 86 parents in the v2 extended set.

Single one-shot Opus 4.7 call. Reuses the prompt template from
prompts/13_assign_clusters.md. Differs from script 13 in that the parent
rubric is the 86-parent extended set produced by script 42, not the 71-
parent v1 set.

Inputs:
  - v2_parents_extended.json (script 42 output)
  - catalogue_after_convergence.json
  - prompts/13_assign_clusters.md

Outputs:
  - cluster_to_parent_assignments_v2_extended.jsonl
  - cluster_to_parent_assignments_v2_extended_meta.json
"""
from __future__ import annotations
import json, time
from collections import Counter
from pathlib import Path
import anthropic

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / 'output/sweep/convergence/catalogue_after_convergence.json'
PARENTS = ROOT / 'closure/output/parent_derivation_clean_ensemble/v2_parents_extended.json'
PROMPT_FILE = ROOT / 'closure/prompts/13_assign_clusters.md'
OUT_DIR = ROOT / 'closure/output/parent_derivation_clean_ensemble'
OUT = OUT_DIR / 'cluster_to_parent_assignments_v2_extended.jsonl'
META = OUT_DIR / 'cluster_to_parent_assignments_v2_extended_meta.json'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 128000
PRICE_IN_PER_M = 5
PRICE_OUT_PER_M = 25


def build_parent_block(parents):
    out = []
    for p in parents:
        out.append(f"### {p.get('parent_id', '?')}: {p.get('name', '?')}")
        out.append(f"Description: {p.get('description', '')}")
        out.append(f"Mechanism criterion: {p.get('mechanism_criterion', '')}")
        out.append("")
    return '\n'.join(out)


def build_cluster_block(clusters):
    lines = []
    for c in clusters:
        cid = c['cluster_id']
        name = (c.get('canonical_name') or '').replace('|', '/').strip()
        sig = (c.get('mechanism_signature') or '').replace('|', '/').replace('\n', ' ').strip()
        n = len(c.get('supporting_record_ids', []))
        lines.append(f"  {cid} | {name} | {sig} | {n}")
    return '\n'.join(lines)


def parse_json(raw):
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
    parents = parents_data['extended']['parents']
    valid_pids = {p.get('parent_id') for p in parents}
    print(f"  {len(clusters)} clusters, {len(parents)} parents", flush=True)

    prompt_template = PROMPT_FILE.read_text()
    parent_block = build_parent_block(parents)
    cluster_block = build_cluster_block(clusters)
    prompt = (prompt_template
              .replace('{parent_block}', parent_block)
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

    parsed = parse_json(raw)
    if not parsed or 'assignments' not in parsed:
        OUT.with_suffix('.raw.json').write_text(json.dumps({'raw_response': raw}, indent=2))
        raise SystemExit(f"! Parse failed; raw at {OUT.with_suffix('.raw.json')}")

    assigns = parsed['assignments']
    print(f"\n  Returned {len(assigns)} assignments (input had {len(clusters)} clusters)",
          flush=True)

    seen = {a.get('cluster_id') for a in assigns}
    input_ids = {c['cluster_id'] for c in clusters}
    missing = input_ids - seen
    extra = seen - input_ids
    bad_pids = [a for a in assigns
                if a.get('parent_id') not in valid_pids and a.get('parent_id') != 'none']
    if missing:
        print(f"  ! {len(missing)} clusters missing: {sorted(missing)[:10]}...", flush=True)
    if extra:
        print(f"  ! {len(extra)} extra: {sorted(extra)[:10]}...", flush=True)
    if bad_pids:
        print(f"  ! {len(bad_pids)} bad parent_ids: {[a.get('parent_id') for a in bad_pids[:10]]}", flush=True)

    with OUT.open('w') as f:
        for a in assigns:
            f.write(json.dumps(a) + '\n')
    print(f"\nWrote {OUT}", flush=True)

    parent_counter = Counter(a.get('parent_id') for a in assigns)
    confidence_counter = Counter(a.get('confidence') for a in assigns)
    print(f"\n  Confidence distribution: {dict(confidence_counter)}", flush=True)
    print(f"  Top 10 parents:", flush=True)
    for pid, n in parent_counter.most_common(10):
        pname = next((p['name'] for p in parents if p.get('parent_id') == pid), pid)
        print(f"    {n:4d}  [{pid}] {pname[:60]}", flush=True)
    print(f"  Bottom (smallest assignment counts):", flush=True)
    all_pids_with_zero = sorted([(parent_counter.get(p['parent_id'], 0), p['parent_id'], p.get('name','')) for p in parents])
    for n, pid, pname in all_pids_with_zero[:10]:
        print(f"    {n:4d}  [{pid}] {pname[:60]}", flush=True)

    META.write_text(json.dumps({
        'model': MODEL, 'max_tokens': MAX_TOKENS,
        'input_tokens': in_tok, 'output_tokens': out_tok,
        'cost_usd': round(cost, 4), 'wall_seconds': round(wall, 1),
        'stop_reason': msg.stop_reason,
        'prompt_chars': len(prompt), 'output_chars': len(raw),
        'n_clusters_input': len(clusters),
        'n_assignments_output': len(assigns),
        'n_missing_clusters': len(missing),
        'n_extra_cluster_ids': len(extra),
        'n_invalid_parent_ids': len(bad_pids),
        'confidence_distribution': dict(confidence_counter),
        'parent_assignment_distribution': dict(parent_counter),
    }, indent=2))
    print(f"Wrote {META}", flush=True)


if __name__ == '__main__':
    main()
