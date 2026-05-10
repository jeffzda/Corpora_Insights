#!/usr/bin/env python3
"""Pass-1 ensemble (SOFT-BALANCE variant): 20 identical parent-derivation
requests with an added soft constraint asking the model to prefer parent
definitions that subsume similar volumes of records.

Tests whether the soft constraint compresses the records-per-parent
variance vs the baseline 50-run ensemble (which used the unconstrained
prompt). Same model (Opus 4.7), same seed, same input — only the prompt
differs (uses 12_derive_parents_softbalance.md with constraint #7 added).

Subcommands (run in order):
  --dry      validate prompt building, request shape, file paths; no API
  --test     single sync call (~$1) to verify parse before batch
  --submit   submit the 20-run batch (~$10 at 50% batch discount)
  --status   poll batch status
  --retrieve download completed batch results to disk
  --analyse  parse all 20 runs; compare records-per-parent distribution
             to the baseline 50-run unconstrained ensemble

Pre-registered analysis plan:
  HYPOTHESIS: the soft-balance constraint will compress the records-per-
  parent distribution within each run — specifically:
   - max/median ratio reduces from baseline ~3.4x toward ~2x
   - n_parents distribution shifts (likely toward fewer parents, since
     model can't "shed mass" by leaving extreme tails)
   - the broad-and-pervasive parents (knowledge gap, planning) split
     more often; the narrow-but-reliable parents (chicken-and-egg,
     equity) merge into adjacent categories more often
  ALTERNATIVE: the constraint is too soft to bite, and distributions
  match baseline within sampling noise.

Outputs live under closure/output/parent_ensemble_softbalance/
"""
from __future__ import annotations
import argparse
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / 'output/sweep/convergence/catalogue_after_convergence.json'
PROMPT_FILE = ROOT / 'closure/prompts/12_derive_parents_softbalance.md'
OUT_DIR = ROOT / 'closure/output/parent_ensemble_softbalance'
BASELINE_PARSED = ROOT / 'closure/output/parent_ensemble/parsed_runs.jsonl'

BATCH_ID_FILE = OUT_DIR / 'batch_id.txt'
BATCH_META_FILE = OUT_DIR / 'batch_meta.json'
RAW_RESPONSES = OUT_DIR / 'raw_responses.jsonl'
PARSED_RUNS = OUT_DIR / 'parsed_runs.jsonl'
SUMMARY_JSON = OUT_DIR / 'ensemble_summary.json'
SUMMARY_MD = OUT_DIR / 'ensemble_summary.md'
TEST_RESPONSE = OUT_DIR / 'test_response.json'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 128000
N_RUNS = 20
SEED = 42  # fixed across all runs — input prompt is byte-identical
PRICE_IN_PER_M = 5
PRICE_OUT_PER_M = 25


def build_prompt() -> str:
    """Build the same prompt as 12_opus_derive_parents.py with seed=42."""
    cat = json.load(CATALOGUE.open())
    clusters = cat['clusters']
    random.seed(SEED)
    shuffled = list(clusters)
    random.shuffle(shuffled)
    template = PROMPT_FILE.read_text()
    lines = []
    for c in shuffled:
        cid = c['cluster_id']
        name = (c.get('canonical_name') or '').replace('|', '/').strip()
        sig = (c.get('mechanism_signature') or '').replace('|', '/').replace('\n', ' ').strip()
        n = len(c.get('supporting_record_ids', []))
        lines.append(f"  {cid} | {name} | {sig} | {n}")
    cluster_block = '\n'.join(lines)
    return template.replace('{cluster_block}', cluster_block)


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


# === --dry ===
def cmd_dry(args):
    print("=== DRY RUN ===")
    print(f"Output dir: {OUT_DIR}")
    print(f"  exists: {OUT_DIR.exists()}")
    print(f"Catalogue: {CATALOGUE}")
    print(f"  exists: {CATALOGUE.exists()}")
    print(f"Prompt template: {PROMPT_FILE}")
    print(f"  exists: {PROMPT_FILE.exists()}")
    print()
    print("Building prompt...")
    prompt = build_prompt()
    print(f"  Prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tokens)")
    print(f"  First 200 chars: {prompt[:200]!r}...")
    print(f"  Last 200 chars:  ...{prompt[-200:]!r}")
    print()
    print("Constructing batch request bodies...")
    requests = [
        {
            'custom_id': f'run_{i+1:02d}',
            'params': {
                'model': MODEL,
                'max_tokens': MAX_TOKENS,
                'messages': [{'role': 'user', 'content': prompt}],
            }
        }
        for i in range(N_RUNS)
    ]
    print(f"  Built {len(requests)} request bodies")
    print(f"  Sample custom_ids: {[r['custom_id'] for r in requests[:3]]}...{requests[-1]['custom_id']}")
    print(f"  Each request: model={requests[0]['params']['model']}, max_tokens={requests[0]['params']['max_tokens']:,}")
    print(f"  Each request prompt (chars): {len(requests[0]['params']['messages'][0]['content']):,}")
    print(f"  All requests have identical prompts: {all(r['params']['messages'][0]['content'] == prompt for r in requests)}")
    print()

    # Total cost estimate
    in_tok_per_run = len(prompt) // 4
    expected_out_tok = 17_000  # observed range across the 3 prior runs: 15-19k
    sync_cost_per_run = in_tok_per_run/1e6 * PRICE_IN_PER_M + expected_out_tok/1e6 * PRICE_OUT_PER_M
    batch_cost_per_run = sync_cost_per_run * 0.5
    print(f"Cost projection:")
    print(f"  per-run sync:   ${sync_cost_per_run:.2f}")
    print(f"  per-run batch:  ${batch_cost_per_run:.2f}")
    print(f"  TOTAL ({N_RUNS} runs sync):  ${sync_cost_per_run * N_RUNS:.2f}")
    print(f"  TOTAL ({N_RUNS} runs batch): ${batch_cost_per_run * N_RUNS:.2f}")
    print()
    print("Anthropic SDK check:")
    try:
        client = anthropic.Anthropic()
        # Just verify the batches namespace exists
        assert hasattr(client.messages, 'batches'), "client.messages.batches not present"
        print(f"  client.messages.batches.create: callable")
        print(f"  client.messages.batches.retrieve: callable")
        print(f"  client.messages.batches.results: callable")
    except Exception as e:
        print(f"  ! SDK check failed: {e}")
        return 1
    print()
    print("Output paths that will be written on submission/retrieval:")
    for p in [BATCH_ID_FILE, BATCH_META_FILE, RAW_RESPONSES, PARSED_RUNS, SUMMARY_JSON, SUMMARY_MD]:
        marker = '(exists)' if p.exists() else '(new)'
        print(f"  {p}  {marker}")
    print()
    print("=== DRY RUN OK — no API calls made, no files written ===")
    print(f"Next: run --test (1 sync call, ~$1) or skip directly to --submit.")
    return 0


# === --test ===
def cmd_test(args):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prompt = build_prompt()
    print(f"Calling {MODEL} with {len(prompt):,}-char prompt (sync, single request)...", flush=True)
    client = anthropic.Anthropic()
    started = time.time()
    parts = []
    last_print = started; last_chars = 0; text_chars = 0
    with client.messages.stream(
        model=MODEL, max_tokens=MAX_TOKENS,
        messages=[{'role': 'user', 'content': prompt}],
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
    in_tok = msg.usage.input_tokens; out_tok = msg.usage.output_tokens
    cost = in_tok/1e6 * PRICE_IN_PER_M + out_tok/1e6 * PRICE_OUT_PER_M
    parsed = parse_json(raw)
    n_parents = len(parsed.get('parents', [])) if parsed else None
    n_unassigned = len(parsed.get('unassigned', [])) if parsed else None
    print(f"\n  Wall: {wall:.0f}s  in/out: {in_tok:,}/{out_tok:,}  cost ${cost:.3f}")
    print(f"  Stop reason: {msg.stop_reason}")
    print(f"  Parsed: n_parents={n_parents}  n_unassigned={n_unassigned}")
    TEST_RESPONSE.write_text(json.dumps({
        'model': MODEL,
        'wall_seconds': round(wall, 1),
        'input_tokens': in_tok,
        'output_tokens': out_tok,
        'cost_usd': round(cost, 4),
        'stop_reason': msg.stop_reason,
        'raw_response': raw,
        'parsed': parsed,
        'n_parents': n_parents,
        'n_unassigned': n_unassigned,
    }, indent=2))
    print(f"  wrote {TEST_RESPONSE}")
    if not parsed or n_parents is None:
        print("  ! Parsing failed — fix before submitting batch")
        return 1
    print(f"\n  ✓ Test passed. Safe to proceed with --submit.")
    return 0


# === --submit ===
def cmd_submit(args):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if BATCH_ID_FILE.exists():
        existing = BATCH_ID_FILE.read_text().strip()
        print(f"! batch_id.txt already exists: {existing}")
        print(f"  Refusing to overwrite. Delete or move it if you want to re-submit.")
        return 1
    prompt = build_prompt()
    print(f"Building {N_RUNS} batch requests with seed={SEED} (identical prompt across all runs)...", flush=True)
    requests = [
        {
            'custom_id': f'run_{i+1:02d}',
            'params': {
                'model': MODEL,
                'max_tokens': MAX_TOKENS,
                'messages': [{'role': 'user', 'content': prompt}],
            }
        }
        for i in range(N_RUNS)
    ]
    print(f"  prompt: {len(prompt):,} chars per request, identical across all {N_RUNS}", flush=True)
    print(f"\nSubmitting batch...", flush=True)
    client = anthropic.Anthropic()
    batch = client.messages.batches.create(requests=requests)
    BATCH_ID_FILE.write_text(batch.id)
    BATCH_META_FILE.write_text(json.dumps({
        'batch_id': batch.id,
        'submitted_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'n_requests': N_RUNS,
        'model': MODEL,
        'max_tokens': MAX_TOKENS,
        'seed': SEED,
        'prompt_chars': len(prompt),
        'processing_status': batch.processing_status,
    }, indent=2))
    print(f"  Batch submitted: {batch.id}")
    print(f"  Processing status: {batch.processing_status}")
    print(f"  Wrote {BATCH_ID_FILE} and {BATCH_META_FILE}")
    print(f"\nNext: run --status to poll, then --retrieve when complete.")
    return 0


# === --status ===
def cmd_status(args):
    if not BATCH_ID_FILE.exists():
        print(f"! No batch_id.txt at {BATCH_ID_FILE}; nothing to check.")
        return 1
    batch_id = BATCH_ID_FILE.read_text().strip()
    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(batch_id)
    print(f"Batch {batch_id}")
    print(f"  processing_status: {batch.processing_status}")
    print(f"  request_counts: {batch.request_counts}")
    if hasattr(batch, 'created_at'): print(f"  created_at: {batch.created_at}")
    if hasattr(batch, 'ended_at'): print(f"  ended_at: {batch.ended_at}")
    if hasattr(batch, 'expires_at'): print(f"  expires_at: {batch.expires_at}")
    if batch.processing_status == 'ended':
        print(f"\n  ✓ Batch complete. Run --retrieve to download results.")
    return 0


# === --retrieve ===
def cmd_retrieve(args):
    if not BATCH_ID_FILE.exists():
        print(f"! No batch_id.txt at {BATCH_ID_FILE}.")
        return 1
    batch_id = BATCH_ID_FILE.read_text().strip()
    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(batch_id)
    if batch.processing_status != 'ended':
        print(f"! Batch is {batch.processing_status}, not ended. Wait for completion.")
        return 1
    print(f"Streaming batch results to {RAW_RESPONSES}...", flush=True)
    n = 0
    with RAW_RESPONSES.open('w') as f:
        for r in client.messages.batches.results(batch_id):
            # r is a MessageBatchIndividualResponse
            f.write(r.model_dump_json() + '\n')
            n += 1
    print(f"  wrote {n:,} responses")
    return 0


def _exemplar_records(parent, n_recs_by_cluster):
    """Sum of n_records across this parent's exemplar_cluster_ids.
    Proxy for records-per-parent without re-running Pass-2 assignment."""
    exs = parent.get('exemplar_cluster_ids', []) or []
    return sum(n_recs_by_cluster.get(c, 0) for c in exs), len(exs)


def _compute_records_per_parent_stats(runs, n_recs_by_cluster):
    """For each run, compute within-run records-per-parent distribution.
    Returns list of dicts (one per run) with stats + one per-run sequence."""
    import statistics
    out = []
    for r in runs:
        per_parent_recs = []
        per_parent_n_exs = []
        for p in r.get('parents', []):
            recs, n_exs = _exemplar_records(p, n_recs_by_cluster)
            if n_exs > 0:
                per_parent_recs.append(recs)
                per_parent_n_exs.append(n_exs)
        if not per_parent_recs:
            continue
        n = len(per_parent_recs)
        med = statistics.median(per_parent_recs)
        max_v = max(per_parent_recs)
        min_v = min(per_parent_recs)
        sd = statistics.stdev(per_parent_recs) if n > 1 else 0
        out.append({
            'custom_id': r.get('custom_id'),
            'n_parents': n,
            'records_per_parent_min': min_v,
            'records_per_parent_max': max_v,
            'records_per_parent_median': med,
            'records_per_parent_mean': round(statistics.mean(per_parent_recs), 1),
            'records_per_parent_sd': round(sd, 1),
            'max_over_median': round(max_v / med, 2) if med > 0 else None,
            'mean_n_exemplars': round(statistics.mean(per_parent_n_exs), 2),
            'per_parent_recs': per_parent_recs,
        })
    return out


# === --analyse ===
def cmd_analyse(args):
    if not RAW_RESPONSES.exists():
        print(f"! No raw responses at {RAW_RESPONSES}; run --retrieve first.")
        return 1
    print(f"Loading raw responses from {RAW_RESPONSES}...", flush=True)
    runs = []
    total_in = total_out = 0
    parse_failures = []
    for line in RAW_RESPONSES.open():
        d = json.loads(line)
        custom_id = d.get('custom_id')
        result = d.get('result', {})
        if result.get('type') != 'succeeded':
            parse_failures.append({'custom_id': custom_id, 'reason': f"result.type={result.get('type')}"})
            continue
        message = result.get('message', {})
        content = message.get('content', [])
        text = ''.join(c.get('text', '') for c in content if c.get('type') == 'text')
        usage = message.get('usage', {})
        in_tok = usage.get('input_tokens', 0); out_tok = usage.get('output_tokens', 0)
        total_in += in_tok; total_out += out_tok
        parsed = parse_json(text)
        if not parsed:
            parse_failures.append({'custom_id': custom_id, 'reason': 'json_parse_failed'})
            continue
        runs.append({
            'custom_id': custom_id,
            'input_tokens': in_tok, 'output_tokens': out_tok,
            'stop_reason': message.get('stop_reason'),
            'parents': parsed.get('parents', []),
            'unassigned': parsed.get('unassigned', []),
            'notes': parsed.get('notes', ''),
        })

    print(f"  parsed {len(runs)} runs, {len(parse_failures)} failures")
    if parse_failures:
        print(f"  failures:")
        for f in parse_failures: print(f"    {f}")

    # Save parsed runs
    with PARSED_RUNS.open('w') as f:
        for r in runs:
            f.write(json.dumps(r) + '\n')
    print(f"  wrote {PARSED_RUNS}")

    # === Aggregate stats ===
    n_parents_per_run = [len(r['parents']) for r in runs]
    n_unassigned_per_run = [len(r['unassigned']) for r in runs]
    cost_total = total_in/1e6 * PRICE_IN_PER_M*0.5 + total_out/1e6 * PRICE_OUT_PER_M*0.5  # batch 50%
    cost_total_sync_equiv = total_in/1e6 * PRICE_IN_PER_M + total_out/1e6 * PRICE_OUT_PER_M

    import statistics
    def stats(xs):
        return {
            'min': min(xs), 'max': max(xs),
            'mean': round(statistics.mean(xs), 2),
            'sd': round(statistics.stdev(xs), 2) if len(xs) > 1 else 0,
            'p10': sorted(xs)[max(0, int(len(xs)*0.10))],
            'p50': sorted(xs)[int(len(xs)*0.50)],
            'p90': sorted(xs)[min(len(xs)-1, int(len(xs)*0.90))],
        }
    parents_stats = stats(n_parents_per_run)
    unassigned_stats = stats(n_unassigned_per_run)

    # === Mechanism-class frequency table ===
    # Cluster all parent labels across all runs by name-Jaccard.
    # Greedy: for each parent label, find existing class with Jaccard >=0.30
    # to its centroid; if found, add to it; else start new class.
    STOP = {'and','or','of','the','to','for','a','in','on','at','by','from','as','an','vs','versus','with','due','no','not','its'}
    def toks(s):
        return {w.lower() for w in re.findall(r"[a-zA-Z]{4,}", s) if w.lower() not in STOP}

    classes = []  # list of {tokens_centroid, runs_set, examples}
    for r in runs:
        run_id = r['custom_id']
        for p in r['parents']:
            name = p.get('name', '?')
            t = toks(name)
            best_idx, best_jac = None, 0
            for idx, cls in enumerate(classes):
                # Jaccard against representative tokens
                if not t and not cls['tokens']: continue
                jac = len(t & cls['tokens']) / max(len(t | cls['tokens']), 1)
                if jac > best_jac:
                    best_jac = jac; best_idx = idx
            if best_idx is not None and best_jac >= 0.30:
                cls = classes[best_idx]
                cls['runs'].add(run_id)
                cls['examples'].append((run_id, name))
                # Update tokens to intersection (representative set)
                # Actually keep original tokens as anchor — don't drift
            else:
                classes.append({
                    'tokens': t,
                    'runs': {run_id},
                    'examples': [(run_id, name)],
                })

    # Sort classes by frequency
    classes.sort(key=lambda c: -len(c['runs']))
    n_runs = len(runs)
    tier_counts = Counter()
    for cls in classes:
        f = len(cls['runs']) / n_runs
        if f >= 0.90: tier_counts['core_>=90%'] += 1
        elif f >= 0.70: tier_counts['high_70-89%'] += 1
        elif f >= 0.40: tier_counts['boundary_40-69%'] += 1
        elif f >= 0.20: tier_counts['rare_20-39%'] += 1
        else: tier_counts['singleton_<20%'] += 1

    union_at = {1: 0, 5: 0, 10: 0, 25: 0, 45: 0}
    for cls in classes:
        n = len(cls['runs'])
        for k in union_at:
            if n >= k: union_at[k] += 1

    summary = {
        'n_runs_parsed': n_runs,
        'parse_failures': parse_failures,
        'n_parents_per_run': parents_stats,
        'n_unassigned_per_run': unassigned_stats,
        'total_input_tokens': total_in,
        'total_output_tokens': total_out,
        'total_cost_batch_usd': round(cost_total, 4),
        'total_cost_sync_equiv_usd': round(cost_total_sync_equiv, 4),
        'distinct_mechanism_classes_found': len(classes),
        'tier_counts': dict(tier_counts),
        'union_size_at_min_runs': union_at,
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2))
    print(f"\n  wrote {SUMMARY_JSON}")

    # === Markdown summary ===
    lines = []
    lines.append(f"# Pass-1 Parent-Derivation Ensemble — {n_runs}-Run Summary\n")
    lines.append(f"**Model:** `{MODEL}`  |  **Prompt seed:** {SEED} (identical across all runs)  |  **Total cost:** ${cost_total:.2f} batch (${cost_total_sync_equiv:.2f} sync-equivalent)\n")
    lines.append(f"\n## Granularity distribution (n_parents per run)\n")
    lines.append(f"- min / mean / max: **{parents_stats['min']} / {parents_stats['mean']} / {parents_stats['max']}**")
    lines.append(f"- sd: {parents_stats['sd']}, p10/p50/p90: {parents_stats['p10']}/{parents_stats['p50']}/{parents_stats['p90']}")
    lines.append(f"\n## Coverage (n_unassigned per run, of 1,141 input clusters)\n")
    lines.append(f"- min / mean / max: **{unassigned_stats['min']} / {unassigned_stats['mean']} / {unassigned_stats['max']}**")
    lines.append(f"- sd: {unassigned_stats['sd']}, p10/p50/p90: {unassigned_stats['p10']}/{unassigned_stats['p50']}/{unassigned_stats['p90']}")
    lines.append(f"\n## Mechanism-class frequency tiers (across {n_runs} runs)\n")
    lines.append(f"Distinct mechanism classes detected (Jaccard ≥ 0.30 grouping): **{len(classes)}**\n")
    lines.append(f"| Tier | n classes |")
    lines.append(f"|---|---:|")
    for t in ['core_>=90%', 'high_70-89%', 'boundary_40-69%', 'rare_20-39%', 'singleton_<20%']:
        lines.append(f"| {t} | {tier_counts.get(t, 0)} |")
    lines.append(f"\n## Union vocabulary size at minimum-runs threshold\n")
    lines.append(f"| Min runs | n classes |")
    lines.append(f"|---:|---:|")
    for k, n in sorted(union_at.items()):
        lines.append(f"| ≥ {k} | {n} |")

    lines.append(f"\n## Top 30 most-frequent mechanism classes\n")
    lines.append(f"| Runs | Frequency | Example labels |")
    lines.append(f"|---:|---:|---|")
    for cls in classes[:30]:
        n = len(cls['runs'])
        examples = list({name for _, name in cls['examples']})[:3]
        ex_str = ' / '.join(examples)
        lines.append(f"| {n}/{n_runs} | {n/n_runs*100:.0f}% | {ex_str} |")

    # === Records-per-parent (exemplar-sum proxy) — within-run distribution ===
    # Load catalogue to get n_records per cluster
    cat = json.load(CATALOGUE.open())
    n_recs_by_cluster = {c['cluster_id']: len(c.get('supporting_record_ids', [])) for c in cat['clusters']}

    rec_stats_softbalance = _compute_records_per_parent_stats(runs, n_recs_by_cluster)
    rec_stats_baseline = []
    if BASELINE_PARSED.exists():
        baseline_runs = [json.loads(l) for l in BASELINE_PARSED.open()]
        rec_stats_baseline = _compute_records_per_parent_stats(baseline_runs, n_recs_by_cluster)
        print(f"  loaded {len(baseline_runs)} baseline runs from {BASELINE_PARSED}")

    def _agg(rec_stats):
        if not rec_stats: return None
        import statistics
        return {
            'n_runs': len(rec_stats),
            'mean_n_parents': round(statistics.mean(s['n_parents'] for s in rec_stats), 1),
            'mean_max_over_median': round(statistics.mean(s['max_over_median'] for s in rec_stats if s['max_over_median']), 2),
            'mean_records_per_parent_sd': round(statistics.mean(s['records_per_parent_sd'] for s in rec_stats), 1),
            'mean_median_records': round(statistics.mean(s['records_per_parent_median'] for s in rec_stats), 1),
            'max_records_observed': max(s['records_per_parent_max'] for s in rec_stats),
            'min_records_observed': min(s['records_per_parent_min'] for s in rec_stats),
        }

    agg_sb = _agg(rec_stats_softbalance)
    agg_bl = _agg(rec_stats_baseline)
    summary['exemplar_records_softbalance'] = agg_sb
    summary['exemplar_records_baseline'] = agg_bl
    summary['exemplar_records_per_run_softbalance'] = rec_stats_softbalance
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2))

    # Append comparison block to MD
    lines.append('\n## Records-per-parent within-run distribution (exemplar-sum proxy)\n')
    lines.append('Each parent has 3-5 exemplar clusters; sum of their `n_records` gives a proxy for the parent\'s population. The within-run *spread* of this measure tells us whether parents are population-balanced.')
    lines.append('')
    if agg_sb and agg_bl:
        lines.append('| metric | baseline 50-run (no constraint) | soft-balance 20-run (this run) | delta |')
        lines.append('|---|---:|---:|---:|')
        for k in ['n_runs','mean_n_parents','mean_max_over_median','mean_records_per_parent_sd','mean_median_records','max_records_observed','min_records_observed']:
            bv = agg_bl.get(k); sv = agg_sb.get(k)
            if isinstance(bv, (int, float)) and isinstance(sv, (int, float)):
                delta = round(sv - bv, 2)
                lines.append(f"| {k} | {bv} | {sv} | {delta:+} |")
            else:
                lines.append(f"| {k} | {bv} | {sv} | — |")
        lines.append('')
        lines.append('**Reading:** if the soft-balance constraint bit, expect *mean_max_over_median* and *mean_records_per_parent_sd* to be notably lower in soft-balance vs baseline; expect *mean_n_parents* to shift modestly (toward fewer parents if the model dropped rare-narrow categories, toward more if it split broad ones). If the constraint was too soft to bite, all metrics within sampling noise of baseline.')
    elif agg_sb:
        lines.append('(No baseline parsed_runs.jsonl found at the expected path; soft-balance stats only.)')
        lines.append('')
        for k, v in agg_sb.items():
            lines.append(f"- {k}: {v}")
    lines.append('')

    SUMMARY_MD.write_text('\n'.join(lines))
    print(f"  wrote {SUMMARY_MD}")
    print(f"\n=== Summary printed below ===\n")
    print('\n'.join(lines))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--dry', action='store_true', help='Validate without API calls')
    g.add_argument('--test', action='store_true', help='Single sync call (~$1)')
    g.add_argument('--submit', action='store_true', help='Submit 50-run batch (~$25)')
    g.add_argument('--status', action='store_true', help='Poll batch status')
    g.add_argument('--retrieve', action='store_true', help='Download completed batch results')
    g.add_argument('--analyse', action='store_true', help='Parse and summarise')
    args = ap.parse_args()

    if args.dry: return cmd_dry(args)
    if args.test: return cmd_test(args)
    if args.submit: return cmd_submit(args)
    if args.status: return cmd_status(args)
    if args.retrieve: return cmd_retrieve(args)
    if args.analyse: return cmd_analyse(args)
    return 1


if __name__ == '__main__':
    sys.exit(main())
