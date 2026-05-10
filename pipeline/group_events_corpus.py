#!/usr/bin/env python3
"""Full-corpus orchestrator for post-extract event grouping.

For each project in the catalogue:
  1. Apply seed-doc heuristic to pick the seed doc.
  2. Order remaining docs: backward-chrono (pre-seed) then forward-chrono (post-seed).
  3. Run pipeline.group_events sequentially per doc, with running event
     registry passed between docs.

Across projects: ThreadPoolExecutor with bounded concurrency.

Skips docs that v1 did not extract (the >600k-char outliers) and unassigned
docs (no project anchor for chronological walk). Produces one
<project_slug>/doc_NNNN.assignments.json per doc.

Usage:
  # Default output dir is corpora/<domain>/canonical/output/grouping/
  python -m pipeline.group_events_corpus --domain arena
  # Override:
  python -m pipeline.group_events_corpus \\
      --domain arena \\
      --out-dir runs/arena/fullcorpus_1rep \\
      --concurrency 6 \\
      --exclude-fields lesson
"""
import argparse
import json
import re
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import anthropic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "corpora" / "arena" / "canonical" / "narrative"))
from seed_doc_heuristic import select_seed

# Reuse logic from group_events
from pipeline.group_events import (
    load_prompt, build_prompt, parse_response, merge_event_registries,
    call_api,
)

DEFAULT_MODEL = "claude-sonnet-4-6"
PRICE_INPUT = 3.0
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
    """Load all per-doc record files, returning [{doc_id, project, n_records, ...}]."""
    per_doc_dir = ROOT / "corpora" / domain / "output" / "per_doc"
    docs = []
    for p in sorted(per_doc_dir.glob("doc_*.json")):
        d = json.load(open(p))
        if not d.get("records"):
            continue
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
    """Apply seed-doc heuristic + chronological backward/forward walk.

    Returns a list of doc dicts in processing order.
    """
    if len(docs) == 1:
        return list(docs)
    seed, _ = select_seed(docs)
    seed_date = seed["publish_date"]
    if seed_date is None:
        return [seed] + [d for d in docs if d["doc_id"] != seed["doc_id"]]
    pre = sorted(
        [d for d in docs if d["doc_id"] != seed["doc_id"]
            and d["publish_date"] and d["publish_date"] < seed_date],
        key=lambda d: -d["publish_date"].timestamp(),
    )
    post = sorted(
        [d for d in docs if d["doc_id"] != seed["doc_id"]
            and d["publish_date"] and d["publish_date"] >= seed_date],
        key=lambda d: d["publish_date"].timestamp(),
    )
    no_date = [d for d in docs if d["doc_id"] != seed["doc_id"] and not d["publish_date"]]
    return [seed] + pre + post + no_date


def group_one_project_chronological(
    project_name, docs_in_order, out_dir, prompt_template,
    client, model, exclude_fields, max_tokens=MAX_TOKENS, batch_size=200,
):
    """Walk one project's docs in given order, threading events between calls.

    Returns: (n_records, n_events, total_in, total_out, error)
    """
    project_slug = slugify(project_name) or "unassigned"
    project_dir = out_dir / project_slug
    project_dir.mkdir(parents=True, exist_ok=True)

    running_events = []
    total_in = total_out = 0
    total_assignments = 0
    started = time.time()

    for doc in docs_in_order:
        records = json.load(open(doc["json_path"]))["records"]
        prompt = build_prompt(prompt_template, running_events, records,
                                exclude_fields=exclude_fields)
        label = f"{project_slug[:30]}/{doc['doc_id']}"
        try:
            response, in_tok, out_tok = call_api(
                client, prompt, model, max_tokens, label)
        except Exception as e:
            return (total_assignments, len(running_events), total_in, total_out,
                     f"{label}: {type(e).__name__}: {e}")
        total_in += in_tok
        total_out += out_tok
        assignments, new_events = parse_response(response, label)
        running_events = merge_event_registries(running_events, new_events)
        total_assignments += len(assignments)
        # Write per-doc output
        (project_dir / f"{doc['doc_id']}.assignments.json").write_text(
            json.dumps({"doc": doc["doc_id"], "n_records": len(records),
                         "n_assignments": len(assignments),
                         "assignments": assignments}, indent=2))
        (project_dir / f"{doc['doc_id']}.events.json").write_text(
            json.dumps({"doc": doc["doc_id"], "n_events": len(running_events),
                         "events": running_events}, indent=2))
    # Project summary
    (project_dir / "_project.json").write_text(json.dumps({
        "project": project_name,
        "doc_order": [d["doc_id"] for d in docs_in_order],
        "n_docs": len(docs_in_order),
        "n_records_input": sum(d["n_records"] for d in docs_in_order),
        "n_assignments": total_assignments,
        "n_events": len(running_events),
        "input_tokens": total_in,
        "output_tokens": total_out,
        "wall_seconds": int(time.time() - started),
        "cost_usd": round((total_in / 1_000_000 * PRICE_INPUT) +
                            (total_out / 1_000_000 * PRICE_OUTPUT), 4),
    }, indent=2, ensure_ascii=False))
    return (total_assignments, len(running_events), total_in, total_out, None)


def main():
    parser = argparse.ArgumentParser(description="Full-corpus event grouping")
    parser.add_argument("--domain", default="arena")
    parser.add_argument("--out-dir", default=None,
                         help="Output directory. Defaults to corpora/<domain>/canonical/output/grouping/.")
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--exclude-fields", default="lesson",
                         help="Comma-separated fields to drop. Default: lesson")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    parser.add_argument("--limit", type=int, default=None,
                         help="Limit to first N projects (for testing)")
    parser.add_argument("--skip-unassigned", action="store_true",
                         help="Skip docs with no kb_associated_project")
    args = parser.parse_args()

    if args.out_dir is None:
        out_dir = ROOT / "corpora" / args.domain / "canonical" / "output" / "grouping"
    else:
        out_dir = Path(args.out_dir)
        if not out_dir.is_absolute():
            out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {out_dir}", flush=True)
    exclude_fields = {f.strip() for f in args.exclude_fields.split(",") if f.strip()}

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

    print(f"  {len(by_project)} projects (skipped {skipped_unassigned} unassigned docs)",
          flush=True)
    total_records = sum(d["n_records"] for d in docs)
    total_calls = sum(len(dl) for dl in by_project.values())
    print(f"  Total: {total_records} records across {total_calls} doc-calls",
          flush=True)
    est_cost = total_calls * 0.20
    print(f"  Estimated cost: ~${est_cost:.0f} sync", flush=True)
    print(f"  Concurrency: {args.concurrency}", flush=True)
    print(f"  Excluding fields: {exclude_fields}", flush=True)

    # Pre-compute project ordering so skipping is deterministic
    projects = list(by_project.items())
    if args.limit:
        projects = projects[:args.limit]
        print(f"  Limited to first {args.limit} projects for testing", flush=True)

    prompt_template = load_prompt()
    client = anthropic.Anthropic()

    started = time.time()
    completed = 0
    failed = 0
    total_assignments = 0
    total_events = 0
    total_in = total_out = 0
    errors = []

    def task(item):
        proj_name, project_docs = item
        ordered = order_project_docs(project_docs)
        return (proj_name, ordered, group_one_project_chronological(
            proj_name, ordered, out_dir, prompt_template, client, args.model,
            exclude_fields, args.max_tokens))

    print(f"\nStarting {len(projects)} project tasks...", flush=True)
    with ThreadPoolExecutor(max_workers=args.concurrency) as exe:
        futures = {exe.submit(task, p): p[0] for p in projects}
        for fut in as_completed(futures):
            proj_name = futures[fut]
            try:
                pn, ordered, (n_asn, n_ev, in_t, out_t, err) = fut.result()
            except Exception as e:
                failed += 1
                errors.append(f"{proj_name}: {type(e).__name__}: {e}")
                print(f"  FAIL {proj_name}: {e}", flush=True)
                continue
            if err:
                failed += 1
                errors.append(f"{proj_name}: {err}")
                print(f"  ERR  {proj_name[:40]:<40}  {err}", flush=True)
                continue
            completed += 1
            total_assignments += n_asn
            total_events += n_ev
            total_in += in_t
            total_out += out_t
            elapsed = time.time() - started
            cost = (total_in / 1_000_000 * PRICE_INPUT) + (total_out / 1_000_000 * PRICE_OUTPUT)
            print(f"  [{completed}+{failed}/{len(projects)}] "
                  f"{proj_name[:50]:<50}  "
                  f"{len(ordered)}d → {n_asn}r → {n_ev}e   "
                  f"running ${cost:.2f}, {elapsed:.0f}s", flush=True)

    elapsed = time.time() - started
    cost = (total_in / 1_000_000 * PRICE_INPUT) + (total_out / 1_000_000 * PRICE_OUTPUT)
    print(f"\n=== DONE ===", flush=True)
    print(f"  Projects: {completed} succeeded, {failed} failed", flush=True)
    print(f"  Records → assignments: {total_assignments:,}", flush=True)
    print(f"  Events (sum across projects): {total_events:,}", flush=True)
    print(f"  Tokens: {total_in:,} in / {total_out:,} out", flush=True)
    print(f"  Cost: ${cost:.2f}", flush=True)
    print(f"  Wall: {elapsed:.0f}s ({elapsed/60:.1f}m)", flush=True)
    if errors:
        err_path = out_dir / "_errors.txt"
        err_path.write_text("\n".join(errors))
        print(f"  Errors logged to {err_path}", flush=True)


if __name__ == "__main__":
    main()
