#!/usr/bin/env python3
"""Sync mop-up for the wave-batched dedup orchestrator.

Picks up where group_events_corpus_batch.py left off:
- Reads the same per-project doc plan
- Skips docs whose assignments.json already exists
- Calls the Anthropic API synchronously for the rest
- Parallelises across projects WITHIN a wave (different projects' wave-N
  docs are independent), but serialises across waves (depth dependency)

Use when the remaining waves are small (≤10 calls each) and batch API
latency (~10 min per wave) dominates wall time.

Usage:
  python -m pipeline.group_events_corpus_sync_mopup --domain arena --out-dir runs/arena/fullcorpus_dedup
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "corpora" / "arena" / "canonical" / "narrative"))
from seed_doc_heuristic import select_seed

from pipeline.group_events import (
    load_prompt, build_prompt, parse_response, merge_event_registries,
)

DEFAULT_MODEL = "claude-sonnet-4-6"
PRICE_INPUT_SYNC = 3.0
PRICE_OUTPUT_SYNC = 15.0
MAX_TOKENS = 128_000


def parse_date(s):
    if not s: return None
    for fmt in ("%d/%m/%Y","%Y-%m-%d","%d/%m/%y"):
        try: return datetime.strptime(s.strip(), fmt)
        except: pass
    return None


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")[:60]


def order_project_docs(docs):
    """seed-first then chronological; same as batch orchestrator."""
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


def assignments_path(out_dir, project_name, doc_id):
    return project_dir_for(out_dir, project_name) / f"{doc_id}.assignments.json"


def events_path(out_dir, project_name, doc_id):
    return project_dir_for(out_dir, project_name) / f"{doc_id}.events.json"


def load_corpus_per_doc(domain):
    per_doc_dir = ROOT / "corpora" / domain / "output" / "per_doc"
    docs = []
    for p in sorted(per_doc_dir.glob("doc_*.json")):
        d = json.load(open(p))
        if not d.get("records"): continue
        r0 = d["records"][0]
        docs.append({
            "doc_id": p.stem, "json_path": p,
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


def call_sync(client, prompt, model):
    """Sync API call. Uses streaming because high max_tokens (128k) requires it."""
    with client.messages.stream(
        model=model,
        max_tokens=MAX_TOKENS,
        temperature=0.0,
        messages=[{"role":"user","content":prompt}],
    ) as stream:
        msg = stream.get_final_message()
    return msg.content[0].text, msg.usage.input_tokens, msg.usage.output_tokens


def process_doc(client, project_name, doc, prior_events, prompt_template, exclude_fields, model, out_dir):
    """Process one doc synchronously. Persist assignments + events.
    SAFETY: refuses to overwrite an existing assignments.json — caller
    must skip docs with existing output before calling."""
    pdir = project_dir_for(out_dir, project_name)
    asn_path = pdir / f"{doc['doc_id']}.assignments.json"
    if asn_path.exists():
        raise RuntimeError(f"Refusing to overwrite existing {asn_path}")
    records = json.load(open(doc["json_path"]))["records"]
    prompt = build_prompt(prompt_template, prior_events, records, exclude_fields=exclude_fields)
    text, in_tok, out_tok = call_sync(client, prompt, model)
    custom_id = f"sync__{slugify(project_name)[:48]}__{doc['doc_id']}"
    assignments, new_events = parse_response(text, custom_id)
    running = merge_event_registries(prior_events, new_events)
    pdir.mkdir(parents=True, exist_ok=True)
    asn_path.write_text(
        json.dumps({"doc": doc["doc_id"], "n_records": len(records),
                     "n_assignments": len(assignments),
                     "assignments": assignments,
                     "input_tokens": in_tok, "output_tokens": out_tok},
                    indent=2, ensure_ascii=False))
    (pdir / f"{doc['doc_id']}.events.json").write_text(
        json.dumps({"doc": doc["doc_id"], "n_events": len(running),
                     "events": running}, indent=2, ensure_ascii=False))
    return in_tok, out_tok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", default="arena")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--exclude-fields", default="lesson")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-concurrency", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true",
                         help="Print plan + remaining work; do NOT call API")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute(): out_dir = ROOT / out_dir
    exclude_fields = {f.strip() for f in args.exclude_fields.split(",") if f.strip()}

    print(f"Loading per-doc records for {args.domain}...", flush=True)
    docs = load_corpus_per_doc(args.domain)
    by_project = defaultdict(list)
    for d in docs:
        if d["project"]: by_project[d["project"]].append(d)

    plan = {p: order_project_docs(dl) for p, dl in by_project.items()}
    max_depth = max(len(dl) for dl in plan.values())
    total_calls = sum(len(dl) for dl in plan.values())
    print(f"  {len(plan)} projects, {total_calls} total doc-calls, max depth {max_depth}", flush=True)

    # Identify what's already done
    done_count = 0
    todo_per_wave = defaultdict(list)
    for project, ordered in plan.items():
        for wave_idx, doc in enumerate(ordered):
            if assignments_path(out_dir, project, doc["doc_id"]).exists():
                done_count += 1
            else:
                todo_per_wave[wave_idx].append((project, doc))
    n_todo = sum(len(v) for v in todo_per_wave.values())
    print(f"  Already done: {done_count} doc-calls", flush=True)
    print(f"  Remaining:    {n_todo} doc-calls across {len(todo_per_wave)} waves", flush=True)
    if n_todo == 0:
        print("Nothing to do.", flush=True)
        return

    print(f"\nWaves to process:", flush=True)
    for w in sorted(todo_per_wave.keys()):
        sample_projs = sorted({p for p, _ in todo_per_wave[w]})[:3]
        print(f"  wave {w+1}: {len(todo_per_wave[w])} calls   sample projects: {sample_projs}", flush=True)
    print(flush=True)

    if args.dry_run:
        print(f"=== DRY RUN — would process {n_todo} docs across {len(todo_per_wave)} waves ===", flush=True)
        # Sample a few specific docs to be processed
        sample_to_process = []
        for w in sorted(todo_per_wave.keys()):
            for p, d in todo_per_wave[w][:2]:
                sample_to_process.append((w+1, p[:40], d['doc_id']))
        print(f"\nSample docs that would be processed:")
        for w, p, did in sample_to_process[:15]:
            print(f"  wave {w:>2}  project='{p}'  doc={did}")
        print(f"\nNo API calls made. Re-run without --dry-run to execute.", flush=True)
        return

    prompt_template = load_prompt()
    client = anthropic.Anthropic()

    started = time.time()
    grand_in = grand_out = 0
    grand_done = 0

    for wave_idx in sorted(todo_per_wave.keys()):
        wave_docs = todo_per_wave[wave_idx]
        ts = datetime.now().strftime("%H:%M:%S")
        bar = "=" * 70
        print(f"\n{bar}", flush=True)
        print(f"  [{ts}] WAVE {wave_idx+1} (sync): {len(wave_docs)} calls", flush=True)
        print(bar, flush=True)

        wave_started = time.time()
        wave_in = wave_out = 0

        # For each doc, find its prior doc in the same project chain to load prior events
        def task_for(project_name, doc):
            ordered = plan[project_name]
            doc_pos = next(i for i, d in enumerate(ordered) if d["doc_id"] == doc["doc_id"])
            prior_events = []
            if doc_pos > 0:
                prior_doc = ordered[doc_pos - 1]
                p = events_path(out_dir, project_name, prior_doc["doc_id"])
                if p.exists():
                    prior_events = json.load(open(p)).get("events", [])
            return process_doc(client, project_name, doc, prior_events,
                                 prompt_template, exclude_fields, args.model, out_dir)

        # Run wave docs concurrently up to max_concurrency
        with ThreadPoolExecutor(max_workers=args.max_concurrency) as ex:
            futures = {ex.submit(task_for, p, d): (p, d) for p, d in wave_docs}
            for fut in as_completed(futures):
                p, d = futures[fut]
                try:
                    in_tok, out_tok = fut.result()
                    wave_in += in_tok; wave_out += out_tok
                    grand_in += in_tok; grand_out += out_tok
                    grand_done += 1
                except Exception as e:
                    print(f"    ERR {p[:30]} {d['doc_id']}: {e}", flush=True)

        wave_elapsed = time.time() - wave_started
        cost = wave_in/1e6*PRICE_INPUT_SYNC + wave_out/1e6*PRICE_OUTPUT_SYNC
        running_cost = grand_in/1e6*PRICE_INPUT_SYNC + grand_out/1e6*PRICE_OUTPUT_SYNC
        ts2 = datetime.now().strftime("%H:%M:%S")
        print(f"  [{ts2}] WAVE {wave_idx+1} DONE in {wave_elapsed:.0f}s  "
              f"${cost:.2f} (sync) / ${running_cost:.2f} cumulative  "
              f"{grand_done}/{n_todo} done", flush=True)

    elapsed = time.time() - started
    final_cost = grand_in/1e6*PRICE_INPUT_SYNC + grand_out/1e6*PRICE_OUTPUT_SYNC
    print(f"\n=== SYNC MOP-UP COMPLETE ===", flush=True)
    print(f"  {grand_done} doc-calls in {elapsed:.0f}s ({elapsed/60:.1f}m)", flush=True)
    print(f"  ${final_cost:.2f} sync (~${final_cost/2:.2f} batch-equivalent)", flush=True)


if __name__ == "__main__":
    main()
