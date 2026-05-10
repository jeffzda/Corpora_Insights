#!/usr/bin/env python3
"""Closure phase 2 v3: Opus merge-finder restricted to battery-dominated clusters.

Same prompt as script 04 but the catalogue presented is just the top-50
battery-storage-dominated clusters (size ≥10, sorted by battery_share desc
then size desc). Hypothesis: with a constrained focus set, Opus's attention
is narrower and it should find more merges within the subset.

Useful as a sanity-check on whether script 04's catalogue-wide miss rate is
attention-driven (Opus should catch more in a smaller, more tightly-related
pool) or genuinely-low-redundancy (small pool also finds few merges).

Inputs: same as script 04, plus computed battery-dominated subset.
Output: merge_groups_battery_subset.json
"""
import argparse
import json
import re
import time
import csv
from collections import Counter
from pathlib import Path

import anthropic

V2_OUT = Path(__file__).resolve().parents[2] / 'output'
CLOSURE_OUT = Path(__file__).resolve().parent.parent / 'output'
CATALOGUE = V2_OUT / 'sweep' / 'convergence' / 'catalogue_after_convergence.json'
ASSIGNMENTS = V2_OUT / 'sweep' / 'corpus_assignments.jsonl'
INPUT = V2_OUT / 'filter_input.jsonl'
PROJECTS_CSV = Path('/home/jeffzda/broadlearnings/corpora/arena/arena-projects-export_1772932404.csv')

GROUPS_OUT = CLOSURE_OUT / 'merge_groups_battery_subset.json'
RAW_OUT = CLOSURE_OUT / 'opus_battery_subset_raw.txt'


PROMPT_HEADER = """You are auditing a catalogue of failure-mode clusters extracted from a renewable-energy project corpus. Each cluster has a canonical name and a mechanism signature (a one-sentence statement of the causal pathway).

The clusters below are a subset selected for being dominated by battery-storage records (each cluster has at least 40% battery-storage share among its members). They are presented in descending order of battery dominance.

Your task: identify any GROUPS of clusters that describe the SAME causal failure mechanism — clusters that should be merged. Two clusters belong in a merge group if their mechanism signatures describe the same causal pathway, even if:
- they use different surface vocabulary
- they look at the mechanism from different perspectives (e.g., one party's loss is another party's gain — same mechanism, opposite framings)
- they apply to different technologies / projects / domains as long as the causal structure is identical

Two clusters do NOT belong in a merge group if:
- they share topic vocabulary but describe different causal pathways
- they are mechanistically adjacent but distinct (siblings within a parent category, with different proximate causes — sibling ≠ duplicate)
- one is a more general statement than the other (categorical containment is not equivalence)
- the same outcome is reached through different proximate causes (different mechanisms, same outcome)

Be precise. Sibling mechanisms within the same category should remain SEPARATE — only merge when the underlying causal pathway is the same.

# CATALOGUE (battery-dominated subset)
"""

PROMPT_FOOTER = """\

# OUTPUT FORMAT — STRICT

Return JSON only. First character `{`, last character `}`. No preamble, no markdown fences.

Schema:
{
  "merge_groups": [
    {"members": ["c001", "c042"], "rationale": "<one sentence stating the shared mechanism>"},
    ...
  ]
}

If no merge groups exist, return {"merge_groups": []}."""


def stream_call(client, prompt, model, max_tokens=16000, raw_path=None):
    raw_f = open(raw_path, 'w') if raw_path else None
    started = time.time()
    last_print = 0; last_chars = 0; text_chars = 0
    parts = []; msg = None
    try:
        with client.messages.stream(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for ev in stream.text_stream:
                if raw_f: raw_f.write(ev); raw_f.flush()
                parts.append(ev); text_chars += len(ev)
                now = time.time()
                if now - last_print >= 5:
                    rate = (text_chars - last_chars) / max(now - last_print, 1)
                    print(f"  [{int(now - started)}s] {text_chars:,} chars  +{rate:.0f} c/s",
                          flush=True)
                    last_print = now; last_chars = text_chars
            msg = stream.get_final_message()
    finally:
        if raw_f: raw_f.close()
    return ''.join(parts), msg


def parse_response(text):
    text = text.strip()
    m = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
    body = m.group(1).strip() if m else text
    first = body.find('{'); last = body.rfind('}')
    if first >= 0 and last > first:
        try: return json.loads(body[first:last+1])
        except: pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--top-n', type=int, default=50)
    ap.add_argument('--min-size', type=int, default=10)
    ap.add_argument('--model', default='claude-opus-4-7')
    args = ap.parse_args()

    print("Loading inputs...", flush=True)
    catalogue = json.load(open(CATALOGUE))['clusters']
    cid_to_meta = {c['cluster_id']: c for c in catalogue}
    rows = [json.loads(l) for l in open(INPUT)]
    rid_to = {r['record_id']: r for r in rows}
    csv_rows = list(csv.DictReader(open(PROJECTS_CSV)))
    proj_to_cat = {r['Project']: r.get('Category','') for r in csv_rows}
    assigns = [json.loads(l) for l in open(ASSIGNMENTS)]

    cluster_members = {}
    for a in assigns:
        cid = a.get('cluster_id')
        if cid in cid_to_meta:
            cluster_members.setdefault(cid, []).append(a['record_id'])

    # Compute battery dominance per cluster
    results = []
    for cid, mem_ids in cluster_members.items():
        if len(mem_ids) < args.min_size: continue
        members = [rid_to[r] for r in mem_ids if r in rid_to]
        cats = [proj_to_cat.get(m.get('project',''),'') for m in members]
        cats_clean = [c for c in cats if c]
        if not cats_clean: continue
        cnt = Counter(cats_clean)
        bs_count = cnt.get('Battery storage', 0)
        bs_share = bs_count / sum(cnt.values())
        if bs_count == 0: continue
        results.append({
            'cluster_id': cid, 'size': len(mem_ids),
            'battery_share': bs_share, 'battery_count': bs_count,
        })
    results.sort(key=lambda r: (-r['battery_share'], -r['size']))
    subset = results[:args.top_n]
    subset_ids = [r['cluster_id'] for r in subset]
    print(f"  selected top-{args.top_n} battery-dominated clusters (size ≥{args.min_size})", flush=True)
    print(f"  battery-share range in subset: {subset[-1]['battery_share']:.0%} - {subset[0]['battery_share']:.0%}", flush=True)

    # Build prompt
    block_lines = []
    for cid in subset_ids:
        c = cid_to_meta[cid]
        block_lines.append(f"\n[{cid}] {c['canonical_name']}")
        block_lines.append(f"  mechanism: {c.get('mechanism_signature','')}")
    prompt = PROMPT_HEADER + ''.join(block_lines) + PROMPT_FOOTER
    print(f"  prompt size: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"\nCalling {args.model}...", flush=True)
    t0 = time.time()
    text, msg = stream_call(client, prompt, args.model, raw_path=RAW_OUT)
    wall = time.time() - t0
    print(f"\n  generation done: {len(text):,} chars in {wall:.0f}s", flush=True)
    in_p = 15 if 'opus' in args.model else 3
    out_p = 75 if 'opus' in args.model else 15
    cost = msg.usage.input_tokens/1e6*in_p + msg.usage.output_tokens/1e6*out_p
    print(f"  tokens: {msg.usage.input_tokens:,}in / {msg.usage.output_tokens:,}out  cost ${cost:.3f}", flush=True)

    parsed = parse_response(text)
    groups = (parsed or {}).get('merge_groups') or []
    valid_in_subset = set(subset_ids)
    cleaned = []
    for g in groups:
        members = sorted({m for m in (g.get('members') or []) if m in valid_in_subset})
        if len(members) >= 2:
            cleaned.append({'members': members, 'rationale': g.get('rationale', '')})
    cleaned.sort(key=lambda g: -len(g['members']))
    GROUPS_OUT.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False))

    print(f"\n=== DONE ===")
    print(f"  merge groups: {len(cleaned)}")
    n_aff = len({m for g in cleaned for m in g['members']})
    print(f"  clusters in proposed merges: {n_aff} of {args.top_n} ({100*n_aff/args.top_n:.1f}%)")
    print(f"\nProposed merges:")
    for g in cleaned:
        print(f"\n  {g['members']}")
        for cid in g['members']:
            c = cid_to_meta[cid]
            print(f"    [{cid}] {c['canonical_name']}")
        print(f"    rationale: {g['rationale']}")


if __name__ == "__main__":
    main()
