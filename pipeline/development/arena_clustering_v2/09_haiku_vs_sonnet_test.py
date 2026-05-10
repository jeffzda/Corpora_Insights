#!/usr/bin/env python3
"""Phase 4d-test — Haiku 4.5 vs Sonnet 4.6 A/B on the final-singleton classification task.

Three random 100-record samples drawn from the pending-singleton pool. Each sample
is classified by BOTH models against the same frozen 797-cluster catalogue.

Compare:
  - Classification rate (% non-orphan)
  - Agreement rate (where both models classify, do they pick the same cluster?)
  - Disagreement patterns (sample 20 disagreements for hand-inspection)
  - Cost per call

Why three samples: a single 100-record comparison is noisy. Three lets us
estimate within-sample variance and check stability of the classification rate.

Outputs (in clustering_v2/output/sweep/ab_test/):
  - haiku_sample_<N>.jsonl, sonnet_sample_<N>.jsonl  (per-record raw)
  - comparison.json  (aggregate stats per sample + overall)
  - disagreements_sample.md  (hand-inspection sheet for 20 records)
"""
import argparse
import asyncio
import json
import random
import re
import time
from pathlib import Path

import anthropic

# Reuse builders from 08
import importlib.util
_08_path = Path(__file__).resolve().parent / '08_final_singleton_sweep.py'
_spec = importlib.util.spec_from_file_location('p08', _08_path)
p08 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p08)

OUT_DIR = Path(__file__).resolve().parent.parent / 'output'
SWEEP_DIR = OUT_DIR / 'sweep'
INPUT = OUT_DIR / 'filter_input.jsonl'
PENDING = SWEEP_DIR / 'pending_singletons.json'
WORKING_CATALOGUE = SWEEP_DIR / 'cluster_catalogue.json'

AB_DIR = SWEEP_DIR / 'ab_test'
AB_DIR.mkdir(exist_ok=True)


async def classify_with_model(model, records, catalogue_block, valid_ids, concurrency, label):
    """Wrap classify_one with per-model usage tracking. Reuses parse helpers from 08."""
    client = anthropic.AsyncAnthropic()
    sem = asyncio.Semaphore(concurrency)
    started = time.time()
    out = []

    async def one(r):
        async with sem:
            t0 = time.time()
            try:
                resp = await client.messages.create(
                    model=model,
                    max_tokens=64,
                    temperature=0.0,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": catalogue_block,
                             "cache_control": {"type": "ephemeral"}},
                            {"type": "text", "text": p08.build_record_text(r)},
                        ]
                    }],
                )
                text = resp.content[0].text if resp.content else ''
                parsed = p08.parse_response(text)
                cid = (parsed or {}).get('cluster_id', None)
                if cid != 'orphan' and cid not in valid_ids:
                    cid = 'orphan'
                return {
                    'record_id': r['record_id'], 'cluster_id': cid or 'orphan',
                    'input_tokens': resp.usage.input_tokens,
                    'output_tokens': resp.usage.output_tokens,
                    'cache_creation_tokens': getattr(resp.usage, 'cache_creation_input_tokens', 0),
                    'cache_read_tokens': getattr(resp.usage, 'cache_read_input_tokens', 0),
                    'wall_seconds': round(time.time()-t0, 2),
                    'raw': text,
                }
            except Exception as e:
                return {'record_id': r['record_id'], 'cluster_id': None, 'error': str(e)}

    tasks = [asyncio.create_task(one(r)) for r in records]
    n = 0
    for fut in asyncio.as_completed(tasks):
        result = await fut; out.append(result); n += 1
        if n % 25 == 0:
            print(f"    [{label}] {n}/{len(records)}  ({n/(time.time()-started):.1f}/s)", flush=True)
    return out


def cost_estimate(rows, prices):
    """prices: dict with input, output, cache_write, cache_read in $/M-tokens"""
    total_in = sum(r.get('input_tokens',0) for r in rows if 'input_tokens' in r)
    total_out = sum(r.get('output_tokens',0) for r in rows if 'output_tokens' in r)
    total_cw = sum(r.get('cache_creation_tokens',0) for r in rows if 'cache_creation_tokens' in r)
    total_cr = sum(r.get('cache_read_tokens',0) for r in rows if 'cache_read_tokens' in r)
    cost = (total_in/1e6)*prices['input'] + (total_out/1e6)*prices['output'] + \
           (total_cw/1e6)*prices['cache_write'] + (total_cr/1e6)*prices['cache_read']
    return {'input_tok': total_in, 'output_tok': total_out,
            'cache_write_tok': total_cw, 'cache_read_tok': total_cr, 'cost_usd': cost}


PRICES = {
    'sonnet':  {'input': 3.0,  'output': 15.0, 'cache_write': 3.75, 'cache_read': 0.30},
    'haiku':   {'input': 0.80, 'output': 4.0,  'cache_write': 1.0,  'cache_read': 0.08},
}
MODELS = {
    'sonnet': 'claude-sonnet-4-6',
    'haiku':  'claude-haiku-4-5-20251001',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n-samples', type=int, default=3)
    ap.add_argument('--sample-size', type=int, default=100)
    ap.add_argument('--concurrency', type=int, default=20)
    ap.add_argument('--seed', type=int, default=2026)
    args = ap.parse_args()

    print("Loading catalogue + pending pool...", flush=True)
    catalogue = json.load(open(WORKING_CATALOGUE))['clusters']
    valid_ids = {c['cluster_id'] for c in catalogue}
    pending = list(json.load(open(PENDING)))
    rows = [json.loads(l) for l in open(INPUT)]
    rid_to_record = {r['record_id']: r for r in rows}
    print(f"  catalogue: {len(catalogue)}  pending: {len(pending):,}", flush=True)

    rng = random.Random(args.seed)
    rng.shuffle(pending)

    catalogue_block = p08.build_catalogue_block(catalogue)
    print(f"  cached prefix: {len(catalogue_block):,} chars (~{len(catalogue_block)//4:,} tok)", flush=True)

    samples = []
    for i in range(args.n_samples):
        ids = pending[i*args.sample_size:(i+1)*args.sample_size]
        recs = [rid_to_record[rid] for rid in ids if rid in rid_to_record]
        samples.append(recs)
        print(f"  sample {i+1}: {len(recs)} records (ids {ids[0]} ... {ids[-1]})", flush=True)

    aggregate = {
        'samples': [], 'overall': {},
        'catalogue_size': len(catalogue),
        'sample_size': args.sample_size, 'concurrency': args.concurrency,
    }

    sonnet_all = []
    haiku_all = []
    for i, sample in enumerate(samples, 1):
        print(f"\n=== Sample {i}/{len(samples)} ===", flush=True)
        # Run sonnet
        print(f"  → Sonnet 4.6 ({len(sample)} records, concurrency {args.concurrency})", flush=True)
        t0 = time.time()
        sonnet_rows = asyncio.run(classify_with_model(
            MODELS['sonnet'], sample, catalogue_block, valid_ids,
            args.concurrency, f's{i}-sonnet'))
        sonnet_wall = time.time() - t0
        (AB_DIR / f'sonnet_sample_{i}.jsonl').write_text(
            '\n'.join(json.dumps(r, ensure_ascii=False) for r in sonnet_rows))

        # Run haiku
        print(f"  → Haiku 4.5  ({len(sample)} records, concurrency {args.concurrency})", flush=True)
        t0 = time.time()
        haiku_rows = asyncio.run(classify_with_model(
            MODELS['haiku'], sample, catalogue_block, valid_ids,
            args.concurrency, f's{i}-haiku'))
        haiku_wall = time.time() - t0
        (AB_DIR / f'haiku_sample_{i}.jsonl').write_text(
            '\n'.join(json.dumps(r, ensure_ascii=False) for r in haiku_rows))

        # Compare
        s_by_rid = {r['record_id']: r for r in sonnet_rows}
        h_by_rid = {r['record_id']: r for r in haiku_rows}
        rids = sorted(set(s_by_rid) & set(h_by_rid))
        s_clf = sum(1 for r in rids if s_by_rid[r]['cluster_id'] not in (None,'orphan'))
        h_clf = sum(1 for r in rids if h_by_rid[r]['cluster_id'] not in (None,'orphan'))
        both_clf = [r for r in rids if s_by_rid[r]['cluster_id'] not in (None,'orphan')
                                  and h_by_rid[r]['cluster_id'] not in (None,'orphan')]
        agree = sum(1 for r in both_clf
                    if s_by_rid[r]['cluster_id'] == h_by_rid[r]['cluster_id'])
        only_sonnet = [r for r in rids if s_by_rid[r]['cluster_id'] not in (None,'orphan')
                                       and h_by_rid[r]['cluster_id'] in (None,'orphan')]
        only_haiku = [r for r in rids if h_by_rid[r]['cluster_id'] not in (None,'orphan')
                                      and s_by_rid[r]['cluster_id'] in (None,'orphan')]
        cross = [r for r in both_clf if s_by_rid[r]['cluster_id'] != h_by_rid[r]['cluster_id']]

        s_cost = cost_estimate(sonnet_rows, PRICES['sonnet'])
        h_cost = cost_estimate(haiku_rows, PRICES['haiku'])
        sample_summary = {
            'sample': i, 'n': len(rids),
            'sonnet': {'classified': s_clf, 'orphan': len(rids)-s_clf,
                       'wall_seconds': round(sonnet_wall,1), **s_cost},
            'haiku':  {'classified': h_clf, 'orphan': len(rids)-h_clf,
                       'wall_seconds': round(haiku_wall,1), **h_cost},
            'agreement_when_both_classify': {
                'both_classified': len(both_clf), 'agree': agree,
                'agree_rate': round(agree/len(both_clf), 3) if both_clf else None,
            },
            'asymmetric_classification': {
                'only_sonnet': len(only_sonnet), 'only_haiku': len(only_haiku),
                'cross_disagreement': len(cross),
            },
        }
        aggregate['samples'].append(sample_summary)
        sonnet_all += sonnet_rows; haiku_all += haiku_rows
        print(f"  Sonnet: {s_clf}/{len(rids)} classified  (${s_cost['cost_usd']:.2f}, {sonnet_wall:.0f}s)", flush=True)
        print(f"  Haiku:  {h_clf}/{len(rids)} classified  (${h_cost['cost_usd']:.2f}, {haiku_wall:.0f}s)", flush=True)
        print(f"  Agreement when both classify: {agree}/{len(both_clf)} "
              f"({100*agree/max(len(both_clf),1):.1f}%)", flush=True)
        print(f"  Asymmetric: only-sonnet {len(only_sonnet)}, only-haiku {len(only_haiku)}, "
              f"cross-class {len(cross)}", flush=True)

    # Overall
    s_cost_all = cost_estimate(sonnet_all, PRICES['sonnet'])
    h_cost_all = cost_estimate(haiku_all, PRICES['haiku'])
    aggregate['overall'] = {
        'sonnet_total_cost': round(s_cost_all['cost_usd'], 3),
        'haiku_total_cost':  round(h_cost_all['cost_usd'], 3),
        'sonnet_classified': sum(s['sonnet']['classified'] for s in aggregate['samples']),
        'haiku_classified':  sum(s['haiku']['classified']  for s in aggregate['samples']),
        'total_records':     sum(s['n'] for s in aggregate['samples']),
    }
    (AB_DIR / 'comparison.json').write_text(json.dumps(aggregate, indent=2))

    # Disagreement sheet
    print(f"\n=== Building disagreement inspection sheet ===", flush=True)
    s_by_rid = {r['record_id']: r for r in sonnet_all}
    h_by_rid = {r['record_id']: r for r in haiku_all}
    rid_to_record_all = {r['record_id']: r for r in rows}
    cid_to_meta = {c['cluster_id']: c for c in catalogue}
    disagreements = []
    for rid in sorted(set(s_by_rid) & set(h_by_rid)):
        sc = s_by_rid[rid]['cluster_id']; hc = h_by_rid[rid]['cluster_id']
        if sc != hc:
            disagreements.append((rid, sc, hc))
    rng = random.Random(99)
    rng.shuffle(disagreements)
    sample_disag = disagreements[:20]
    md = ["# Disagreement inspection — 20 random records", ""]
    for rid, sc, hc in sample_disag:
        r = rid_to_record_all.get(rid, {})
        md.append(f"\n## {rid}\n")
        md.append(f"narrative: {(r.get('narrative') or '').strip()}")
        evi = (r.get('evidence') or '').strip()
        if evi and evi != r.get('narrative'):
            md.append(f"evidence: {evi[:400]}")
        for label, cid in (('Sonnet', sc), ('Haiku', hc)):
            if cid in cid_to_meta:
                cm = cid_to_meta[cid]
                md.append(f"\n**{label} → [{cid}] {cm['canonical_name']}**")
                md.append(f"  mech: {cm['mechanism_signature'][:300]}")
            else:
                md.append(f"\n**{label} → {cid}**")
        md.append("")
    (AB_DIR / 'disagreements_sample.md').write_text('\n'.join(md))
    print(f"  wrote {AB_DIR/'disagreements_sample.md'} ({len(sample_disag)} disagreements)", flush=True)

    print(f"\n=== A/B summary ===", flush=True)
    print(f"  Sonnet: {aggregate['overall']['sonnet_classified']}/{aggregate['overall']['total_records']} classified, ${aggregate['overall']['sonnet_total_cost']:.2f}")
    print(f"  Haiku:  {aggregate['overall']['haiku_classified']}/{aggregate['overall']['total_records']} classified, ${aggregate['overall']['haiku_total_cost']:.2f}")


if __name__ == "__main__":
    main()
