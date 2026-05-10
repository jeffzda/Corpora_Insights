#!/usr/bin/env python3
"""Full-corpus event grouping via Anthropic Batches API.

Wave-batched architecture: within a project, doc N's grouping call depends
on doc N-1's events.json output, so calls within a project cannot all go in
one batch. But across projects at the same project-depth, calls are
independent and can be batched together.

  Wave 1: every project's seed-doc call (no prior events) — N projects
  Wave 2: every project's 2nd-doc call — projects with ≥2 docs
  Wave 3: every project's 3rd-doc call — projects with ≥3 docs
  ...
  Wave M: longest project's last doc

Each wave is one Anthropic Batches API submission. Halves cost vs sync,
async-completes within 24h SLA per wave (typically 15-90 min for ~500
calls). Total wall ≈ M × per-wave latency.

Resumable: each wave's output is checkpointed; orchestrator can be
re-invoked and will skip waves whose outputs are already on disk.

Usage:
  python -m pipeline.group_events_corpus_batch \\
      --domain arena \\
      --out-dir runs/arena/fullcorpus_1rep_batch \\
      --exclude-fields lesson
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import anthropic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "corpora" / "arena" / "canonical" / "narrative"))
from seed_doc_heuristic import select_seed

from pipeline.group_events import (
    load_prompt, build_prompt, parse_response, merge_event_registries,
)

DEFAULT_MODEL = "claude-sonnet-4-6"
PRICE_INPUT = 3.0     # batch is 50% off — accounted for below
PRICE_OUTPUT = 15.0
MAX_TOKENS = 128_000  # standing rule: never cap below model ceiling


def parse_date(s):
    if not s: return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try: return datetime.strptime(s.strip(), fmt)
        except: pass
    return None


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")[:60]


def load_corpus_per_doc(domain):
    per_doc_dir = ROOT / "corpora" / domain / "output" / "per_doc"
    docs = []
    for p in sorted(per_doc_dir.glob("doc_*.json")):
        d = json.load(open(p))
        if not d.get("records"): continue
        r0 = d["records"][0]
        docs.append({
            "doc_id": p.stem,
            "json_path": p,
            "title": r0.get("source_title", ""),
            "doc_type": r0.get("kb_document_type", ""),
            "publish_date": parse_date(r0.get("kb_publish_date", "")),
            "pub_str": r0.get("kb_publish_date", ""),
            "project": r0.get("kb_associated_project", ""),
            "project_status": r0.get("kb_project_status", ""),
            "n_records": len(d["records"]),
            "input_tokens": (d.get("_meta") or {}).get("input_tokens", 0),
        })
    return docs


def order_project_docs(docs):
    if len(docs) == 1: return list(docs)
    seed, _ = select_seed(docs)
    seed_date = seed["publish_date"]
    if seed_date is None:
        return [seed] + [d for d in docs if d["doc_id"] != seed["doc_id"]]
    pre = sorted(
        [d for d in docs if d["doc_id"] != seed["doc_id"]
            and d["publish_date"] and d["publish_date"] < seed_date],
        key=lambda d: -d["publish_date"].timestamp())
    post = sorted(
        [d for d in docs if d["doc_id"] != seed["doc_id"]
            and d["publish_date"] and d["publish_date"] >= seed_date],
        key=lambda d: d["publish_date"].timestamp())
    no_date = [d for d in docs if d["doc_id"] != seed["doc_id"] and not d["publish_date"]]
    return [seed] + pre + post + no_date


def project_dir_for(out_dir, project_name):
    return out_dir / (slugify(project_name) or "unassigned")


def events_path_for(out_dir, project_name, doc_id):
    return project_dir_for(out_dir, project_name) / f"{doc_id}.events.json"


def assignments_path_for(out_dir, project_name, doc_id):
    return project_dir_for(out_dir, project_name) / f"{doc_id}.assignments.json"


def load_prior_events_for_doc(out_dir, project_name, prior_doc_id):
    """Load events.json from the prior doc in the same project's chain."""
    if prior_doc_id is None: return []
    p = events_path_for(out_dir, project_name, prior_doc_id)
    if not p.exists(): return []
    d = json.load(open(p))
    return d.get("events", [])


def build_wave_requests(wave_idx, plan, out_dir, prompt_template, exclude_fields):
    """Build batch request list for this wave.

    plan: dict project_name -> [doc, doc, ...] in processing order
    Returns: list of {custom_id, params}, plus parallel meta list for result
    routing.
    """
    requests = []
    meta = []
    for project_name, ordered_docs in plan.items():
        if wave_idx >= len(ordered_docs):
            continue
        doc = ordered_docs[wave_idx]
        # Skip if we've already processed this doc (resume)
        if assignments_path_for(out_dir, project_name, doc["doc_id"]).exists():
            continue
        prior_doc_id = ordered_docs[wave_idx - 1]["doc_id"] if wave_idx > 0 else None
        prior_events = load_prior_events_for_doc(out_dir, project_name, prior_doc_id)
        records = json.load(open(doc["json_path"]))["records"]
        prompt = build_prompt(prompt_template, prior_events, records,
                                exclude_fields=exclude_fields)
        custom_id = f"w{wave_idx:02d}__{slugify(project_name)[:48]}__{doc['doc_id']}"
        requests.append({
            "custom_id": custom_id,
            "params": {
                "model": DEFAULT_MODEL,
                "max_tokens": MAX_TOKENS,
                "temperature": 0.0,
                "messages": [{"role": "user", "content": prompt}],
            },
        })
        meta.append({
            "custom_id": custom_id,
            "project": project_name,
            "doc_id": doc["doc_id"],
            "wave": wave_idx,
            "n_records_input": len(records),
        })
    return requests, meta


def submit_wave(client, requests, label):
    print(f"  Submitting batch with {len(requests)} requests... ({label})", flush=True)
    batch = client.messages.batches.create(requests=requests)
    print(f"  Batch ID: {batch.id}  status: {batch.processing_status}", flush=True)
    return batch.id


def wait_for_batch(client, batch_id, label, total_requests=None):
    """Wait for an Anthropic batch to end. Anthropic flips request_counts
    from 0/N to N/N at the moment of completion — there's no useful
    intermediate progress, so we just emit a 60-second 'still waiting' tick
    rather than a fake progress meter."""
    started = time.time()
    last_print = 0
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        status = batch.processing_status
        elapsed = time.time() - started
        if status == "ended": break
        if elapsed - last_print >= 60:
            print(f"  [{int(elapsed)}s] {label}  status={status} (still waiting)",
                  flush=True)
            last_print = elapsed
        time.sleep(20)
    elapsed = time.time() - started
    print(f"  [{int(elapsed)}s] {label} ENDED  {batch.request_counts}",
          flush=True)
    return batch


def collect_wave_results(client, batch_id, meta_by_id, out_dir):
    """Retrieve and persist each request's output. Update events registry per project."""
    n_ok = 0
    n_err = 0
    total_in = total_out = 0
    for result in client.messages.batches.results(batch_id):
        meta = meta_by_id.get(result.custom_id)
        if not meta:
            continue
        if result.result.type != "succeeded":
            print(f"    ERR  {result.custom_id}: {result.result.type}", flush=True)
            n_err += 1
            continue
        msg = result.result.message
        text = msg.content[0].text
        in_tok = msg.usage.input_tokens
        out_tok = msg.usage.output_tokens
        total_in += in_tok
        total_out += out_tok
        assignments, new_events = parse_response(text, meta["custom_id"])
        # Load prior events to merge into running registry
        ordered_docs_in_project = wave_plan_lookup.get(meta["project"], [])
        prior_doc_id = None
        for i, dd in enumerate(ordered_docs_in_project):
            if dd["doc_id"] == meta["doc_id"]:
                if i > 0: prior_doc_id = ordered_docs_in_project[i - 1]["doc_id"]
                break
        prior_events = load_prior_events_for_doc(out_dir, meta["project"], prior_doc_id)
        running_events = merge_event_registries(prior_events, new_events)
        # Persist
        pdir = project_dir_for(out_dir, meta["project"])
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / f"{meta['doc_id']}.assignments.json").write_text(
            json.dumps({"doc": meta["doc_id"], "n_records": meta["n_records_input"],
                         "n_assignments": len(assignments),
                         "assignments": assignments,
                         "input_tokens": in_tok, "output_tokens": out_tok},
                        indent=2, ensure_ascii=False))
        (pdir / f"{meta['doc_id']}.events.json").write_text(
            json.dumps({"doc": meta["doc_id"], "n_events": len(running_events),
                         "events": running_events}, indent=2, ensure_ascii=False))
        n_ok += 1
    return n_ok, n_err, total_in, total_out


# Module-level lookup so collect_wave_results can find a doc's project ordering
wave_plan_lookup = {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", default="arena")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--exclude-fields", default="lesson")
    parser.add_argument("--limit", type=int, default=None,
                         help="Limit to first N projects (for testing)")
    parser.add_argument("--skip-unassigned", action="store_true", default=True)
    parser.add_argument("--max-waves", type=int, default=None,
                         help="Stop after N waves (for testing)")
    parser.add_argument("--batch-meta-dir", default=None,
                         help="Where to persist batch IDs for resume (default <out>/_batches)")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    exclude_fields = {f.strip() for f in args.exclude_fields.split(",") if f.strip()}
    batch_meta_dir = Path(args.batch_meta_dir) if args.batch_meta_dir else (out_dir / "_batches")
    batch_meta_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading per-doc records for {args.domain}...", flush=True)
    docs = load_corpus_per_doc(args.domain)
    print(f"Loaded {len(docs)} docs (those with records)", flush=True)

    by_project = defaultdict(list)
    skipped_unassigned = 0
    for d in docs:
        if not d["project"]:
            if args.skip_unassigned:
                skipped_unassigned += 1
                continue
            d["project"] = "__UNASSIGNED__"
        by_project[d["project"]].append(d)

    plan = {p: order_project_docs(dl) for p, dl in by_project.items()}
    if args.limit:
        plan = dict(list(plan.items())[:args.limit])
    global wave_plan_lookup
    wave_plan_lookup = plan

    max_depth = max(len(dl) for dl in plan.values())
    total_calls = sum(len(dl) for dl in plan.values())
    print(f"  {len(plan)} projects, {total_calls} doc-calls", flush=True)
    print(f"  Max project depth: {max_depth} (need {max_depth} waves)", flush=True)
    est_cost_batch = total_calls * 0.20 * 0.5
    print(f"  Estimated cost: ~${est_cost_batch:.0f} (Anthropic Batches API, 50% off)",
          flush=True)
    print(f"  Excluding fields: {exclude_fields}", flush=True)
    if args.max_waves:
        max_depth = min(max_depth, args.max_waves)
        print(f"  Stopping after wave {max_depth}", flush=True)

    prompt_template = load_prompt()
    client = anthropic.Anthropic()

    # Print the full wave plan upfront so Jeff can track progress
    print(f"\nWave plan ({max_depth} total waves):", flush=True)
    for w in range(max_depth):
        n = sum(1 for dl in plan.values() if len(dl) > w)
        if w < 5 or w >= max_depth - 3 or n >= 50:
            print(f"  wave {w+1:>2}: {n:>4} calls", flush=True)
        elif w == 5:
            print(f"  ... (smaller waves) ...", flush=True)
    print()

    started = time.time()
    grand_in = grand_out = 0
    grand_calls_done = 0
    for wave_idx in range(max_depth):
        wave_label = f"wave-{wave_idx+1}-of-{max_depth}"
        wave_meta_path = batch_meta_dir / f"{wave_label}.json"

        # Big banner with timestamp so log scrolls have clear wave markers
        bar = "=" * 70
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"\n{bar}", flush=True)
        print(f"  [{ts}] WAVE {wave_idx+1} of {max_depth}", flush=True)
        print(bar, flush=True)

        # Resume: if we already have a batch_id and it ended, skip resubmission
        existing_batch_id = None
        existing_meta = None
        if wave_meta_path.exists():
            wm = json.load(open(wave_meta_path))
            existing_batch_id = wm.get("batch_id")
            existing_meta = wm.get("meta")
            print(f"  Resuming with existing batch {existing_batch_id}", flush=True)

        if not existing_batch_id:
            requests, meta = build_wave_requests(
                wave_idx, plan, out_dir, prompt_template, exclude_fields)
            if not requests:
                print(f"  No requests (all docs at this depth already done or none exist)",
                      flush=True)
                continue
            print(f"  {len(requests)} new requests across {len(set(m['project'] for m in meta))} projects",
                  flush=True)
            existing_batch_id = submit_wave(client, requests, wave_label)
            existing_meta = meta
            wm = {"wave": wave_idx, "label": wave_label,
                   "batch_id": existing_batch_id, "n_requests": len(requests),
                   "meta": meta}
            wave_meta_path.write_text(json.dumps(wm, indent=2))

        # Wait
        n_in_wave = len(existing_meta)
        batch = wait_for_batch(client, existing_batch_id, wave_label, total_requests=n_in_wave)
        if batch.processing_status != "ended":
            print(f"  Batch did not end cleanly: {batch.processing_status}", flush=True)
            break
        # Retrieve and persist results
        meta_by_id = {m["custom_id"]: m for m in existing_meta}
        print(f"  Collecting results for {len(meta_by_id)} requests...", flush=True)
        n_ok, n_err, in_t, out_t = collect_wave_results(
            client, existing_batch_id, meta_by_id, out_dir)
        grand_in += in_t
        grand_out += out_t
        grand_calls_done += n_ok
        # Batches API is 50% off — show effective cost
        cost = (in_t / 1_000_000 * PRICE_INPUT + out_t / 1_000_000 * PRICE_OUTPUT) * 0.5
        running_cost = (grand_in / 1_000_000 * PRICE_INPUT +
                          grand_out / 1_000_000 * PRICE_OUTPUT) * 0.5
        elapsed = time.time() - started
        pct_calls = 100 * grand_calls_done / total_calls if total_calls else 0
        # ETA based on cumulative rate
        rate = grand_calls_done / max(elapsed, 1)
        remain = max(total_calls - grand_calls_done, 0)
        eta_s = int(remain / rate) if rate > 0 else 0
        ts_done = datetime.now().strftime("%H:%M:%S")
        print(f"  [{ts_done}] WAVE {wave_idx+1}/{max_depth} DONE: {n_ok} ok, {n_err} err  "
              f"${cost:.2f} this wave / ${running_cost:.2f} cumulative", flush=True)
        print(f"  Corpus progress: {grand_calls_done:,}/{total_calls:,} doc-calls ({pct_calls:.1f}%)  "
              f"elapsed={int(elapsed)}s  ETA={eta_s}s ({eta_s/60:.0f}m)",
              flush=True)

    elapsed = time.time() - started
    final_cost = (grand_in / 1_000_000 * PRICE_INPUT +
                    grand_out / 1_000_000 * PRICE_OUTPUT) * 0.5
    print(f"\n=== ALL WAVES COMPLETE ===", flush=True)
    print(f"  Tokens: {grand_in:,} in / {grand_out:,} out  "
          f"(50%-off: ${final_cost:.2f})", flush=True)
    print(f"  Wall: {elapsed:.0f}s ({elapsed/60:.1f}m)", flush=True)


if __name__ == "__main__":
    main()
