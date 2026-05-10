#!/usr/bin/env python3
"""Failure archetype discovery — per category.

Config-driven version of scripts/archetype_v2_discover.py.
Uses domain config for model selection and prompt rendering.

Usage:
    python -m pipeline.discover --domain arena --category "Battery storage"
    python -m pipeline.discover --domain arena --all
    python -m pipeline.discover --domain arena --all --dry-run
    python -m pipeline.discover --domain arena --refine --all
"""

import argparse
import glob
import json
import random
import sys
import yaml
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic

from pipeline.config import DomainConfig

ROOT = Path(__file__).resolve().parents[1]
MAX_TOKENS = 128000
FM_NO = "no major failure stated"


def get_dirs(cfg):
    """Get input/output directories for this domain."""
    domain_lower = cfg.domain.name.lower()
    events_dir = ROOT / "runs" / domain_lower / "per_project_events"
    if not events_dir.exists() and (ROOT / "insights" / "per_project_events_v2").exists():
        events_dir = ROOT / "insights" / "per_project_events_v2"
    per_doc_dir = ROOT / "runs" / domain_lower / "per_doc"
    if not per_doc_dir.exists():
        per_doc_dir = ROOT / "insights" / "per_doc"
    output_dir = ROOT / "runs" / domain_lower / "failure_archetypes"
    if not output_dir.exists() and (ROOT / "insights" / "failure_archetypes" / "v2").exists():
        output_dir = ROOT / "insights" / "failure_archetypes" / "v2"
    return events_dir, per_doc_dir, output_dir


def load_record_categories(per_doc_dir, category_field):
    """Load category for each record_id from per_doc YAMLs."""
    record_cats = {}
    for fp in sorted(glob.glob(str(per_doc_dir / "doc_*.yaml"))):
        with open(fp) as f:
            doc = yaml.safe_load(f)
        if not doc:
            continue
        recs = doc if isinstance(doc, list) else doc.get("records", [])
        for r in recs:
            rid = r.get("record_id", "")
            cats = r.get(category_field, [])
            if rid and cats:
                record_cats[rid] = cats
    return record_cats


def load_events_by_category(events_dir, record_cats):
    """Load all RDEs grouped by category."""
    by_cat = defaultdict(list)
    for fp in sorted(glob.glob(str(events_dir / "*.json"))):
        fname = Path(fp).name
        if fname in ("batch_state.json", "event_index.json", "project_index.json",
                      "discovery_summary.json", "canonical_taxonomy.json",
                      "reconciled_classifications.json"):
            continue
        with open(fp) as f:
            data = json.load(f)
        evts = data if isinstance(data, list) else data.get("events", [])
        for e in evts:
            if e.get("event_type") != "realised_delivery_event":
                continue
            fm = e.get("failure_mode", "")
            if not fm or fm == FM_NO:
                continue
            cats = set()
            for sr in (e.get("source_records") or []):
                rid = sr.get("record_id", "")
                if rid in record_cats:
                    cats.update(record_cats[rid])
            for cat in cats:
                by_cat[cat].append(e)
    return dict(by_cat)


def discover_category(category, events, model, system_prompt, output_dir, dry_run=False):
    """Run discovery for a single category."""
    if dry_run:
        return {"category": category, "count": len(events), "status": "dry_run"}

    random.seed(42)
    shuffled = list(events)
    random.shuffle(shuffled)

    lines = []
    for i, e in enumerate(shuffled):
        lines.append(
            f"{i+1}. Title: {e['event_title']} | "
            f"What happened: {e['what_happened']} | "
            f"Consequence: {e.get('consequence', 'N/A')}"
        )

    user_msg = (
        f"{len(shuffled)} realised delivery events from {category} projects.\n\n"
        + "\n\n".join(lines)
    )

    system = system_prompt.format(category=category)

    client = anthropic.Anthropic()
    result_text = ""
    with client.messages.stream(
        model=model,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    ) as stream:
        for text in stream.text_stream:
            result_text += text

    start = result_text.find("{")
    end = result_text.rfind("}") + 1
    if start == -1 or end == 0:
        return {"category": category, "error": "No JSON found", "raw": result_text[:500]}

    try:
        result = json.loads(result_text[start:end])
    except json.JSONDecodeError as ex:
        return {"category": category, "error": str(ex), "raw": result_text[:500]}

    outpath = output_dir / f"{category.replace('/', '_').replace(' ', '_')}.json"
    with open(outpath, "w") as f:
        json.dump(result, f, indent=2)

    archetypes = result.get("archetypes", [])
    total_covered = sum(a["count"] for a in archetypes)

    return {
        "category": category,
        "events": len(events),
        "archetypes": len(archetypes),
        "parents": len(set(a["parent_category"] for a in archetypes)),
        "covered": total_covered,
        "uncovered": len(events) - total_covered,
        "coverage_pct": round(total_covered / len(events) * 100, 1) if events else 0,
        "output": str(outpath),
    }


def refine_category(category, other_events, model, refine_prompt, output_dir, dry_run=False):
    """Run refinement discovery on 'Other' events for a category."""
    tax_path = output_dir / f"{category.replace('/', '_').replace(' ', '_')}.json"
    if not tax_path.exists():
        return {"category": category, "error": "No existing taxonomy"}

    with open(tax_path) as f:
        existing = json.load(f)

    existing_archetypes = existing.get("archetypes", [])
    existing_text = "\n".join(
        f"[{a['parent_category']}] {a['name']}: {a['description']}"
        for a in existing_archetypes
    )

    if dry_run:
        return {"category": category, "other_count": len(other_events),
                "existing_archetypes": len(existing_archetypes), "status": "dry_run"}

    random.seed(42)
    shuffled = list(other_events)
    random.shuffle(shuffled)

    lines = []
    for i, e in enumerate(shuffled):
        lines.append(
            f"{i+1}. Title: {e['event_title']} | "
            f"What happened: {e['what_happened']} | "
            f"Consequence: {e.get('consequence', 'N/A')}"
        )

    user_msg = (
        f"{len(shuffled)} unclustered delivery events from {category} projects "
        f"(these were assigned to 'Other' catch-alls in initial classification).\n\n"
        + "\n\n".join(lines)
    )

    system = refine_prompt.format(
        category=category, existing_taxonomy_text=existing_text
    )

    client = anthropic.Anthropic()
    result_text = ""
    with client.messages.stream(
        model=model,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    ) as stream:
        for text in stream.text_stream:
            result_text += text

    start = result_text.find("{")
    end = result_text.rfind("}") + 1
    if start == -1 or end == 0:
        return {"category": category, "error": "No JSON found", "raw": result_text[:500]}

    try:
        new_result = json.loads(result_text[start:end])
    except json.JSONDecodeError as ex:
        return {"category": category, "error": str(ex), "raw": result_text[:500]}

    new_archetypes = new_result.get("archetypes", [])
    existing_names = set(a["name"] for a in existing_archetypes)
    added = []
    for a in new_archetypes:
        if a["name"] not in existing_names:
            existing_archetypes.append(a)
            added.append(a["name"])

    existing["archetypes"] = existing_archetypes
    with open(tax_path, "w") as f:
        json.dump(existing, f, indent=2)

    return {
        "category": category,
        "other_events": len(other_events),
        "new_archetypes": len(added),
        "total_archetypes": len(existing_archetypes),
        "added": added,
    }


def load_other_events(category, by_cat, classify_dir):
    """Load events that were classified as 'Other ...' for refinement."""
    safe_cat = category.replace("/", "_").replace(" ", "_")
    classify_path = classify_dir / f"{safe_cat}.json"
    if not classify_path.exists():
        return []

    with open(classify_path) as f:
        results = json.load(f)

    events = by_cat[category]
    other_events = []
    for i, r in enumerate(results):
        if (r.get("primary") or "").startswith("Other "):
            if i < len(events):
                other_events.append(events[i])
    return other_events


def main():
    parser = argparse.ArgumentParser(description="Discover failure archetypes")
    parser.add_argument("--domain", required=True, help="Domain name (e.g. arena)")
    parser.add_argument("--category", help="Single category to process")
    parser.add_argument("--all", action="store_true", help="Process all categories")
    parser.add_argument("--refine", action="store_true", help="Refinement pass on 'Other' events")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=14)
    args = parser.parse_args()

    if not args.category and not args.all:
        print("Specify --category 'Name' or --all")
        sys.exit(1)

    cfg = DomainConfig.load(args.domain)
    events_dir, per_doc_dir, output_dir = get_dirs(cfg)
    output_dir.mkdir(parents=True, exist_ok=True)
    classify_dir = output_dir / "classifications"

    category_field = cfg.domain.category_field
    model = cfg.domain.discovery_model
    discovery_prompt = cfg.prompt("archetype_discovery")
    refine_prompt = cfg.prompt("archetype_discovery_refine")

    print("Loading record categories...")
    record_cats = load_record_categories(per_doc_dir, category_field)
    print(f"  {len(record_cats):,} records indexed")

    print("Loading events by category...")
    by_cat = load_events_by_category(events_dir, record_cats)
    print(f"  {len(by_cat)} categories, {sum(len(v) for v in by_cat.values()):,} total event-category pairs")

    sorted_cats = sorted(by_cat.keys(), key=lambda c: -len(by_cat[c]))

    if args.category:
        if args.category not in by_cat:
            print(f"Category '{args.category}' not found. Available:")
            for c in sorted_cats:
                print(f"  {c}: {len(by_cat[c])} RDEs")
            sys.exit(1)
        categories = [args.category]
    else:
        categories = sorted_cats

    if args.refine:
        for cat in categories:
            other_events = load_other_events(cat, by_cat, classify_dir)
            if not other_events:
                print(f"  {cat}: no 'Other' events to refine")
                continue
            print(f"\n  {cat}: {len(other_events)} 'Other' events for refinement...")
            if args.dry_run:
                print(f"  [DRY RUN] Would send {len(other_events)} events to {model}")
                continue
            result = refine_category(cat, other_events, model, refine_prompt, output_dir)
            if "error" in result:
                print(f"  ERROR: {result['error']}")
            else:
                print(f"  Found {result['new_archetypes']} new archetypes "
                      f"(total now {result['total_archetypes']})")
                for name in result["added"]:
                    print(f"    + {name}")
        return

    # Print summary
    print(f"\n{'Category':<40} {'RDEs':>6}")
    print("-" * 48)
    total = 0
    for c in categories:
        n = len(by_cat[c])
        total += n
        print(f"{c:<40} {n:>6}")
    print("-" * 48)
    print(f"{'Total (with cross-listing)':<40} {total:>6}")

    if args.dry_run:
        print("\n[DRY RUN] No API calls made.")
        return

    print(f"\nSending {len(categories)} discovery calls to {model}...")

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(discover_category, cat, by_cat[cat], model, discovery_prompt, output_dir): cat
            for cat in categories
        }
        for future in as_completed(futures):
            cat = futures[future]
            try:
                result = future.result()
                results.append(result)
                if "error" in result:
                    print(f"  ERROR {cat}: {result['error']}")
                else:
                    print(f"  DONE  {cat}: {result['archetypes']} archetypes, "
                          f"{result['coverage_pct']}% coverage")
            except Exception as ex:
                print(f"  FAIL  {cat}: {ex}")
                results.append({"category": cat, "error": str(ex)})

    print(f"\n{'='*60}")
    print(f"{'Category':<35} {'RDEs':>5} {'Arch':>5} {'Cover':>6} {'Uncov':>6}")
    print("-" * 60)
    for r in sorted(results, key=lambda x: -x.get("events", 0)):
        if "error" in r:
            print(f"{r['category']:<35} ERROR: {r['error'][:30]}")
        else:
            print(f"{r['category']:<35} {r['events']:>5} {r['archetypes']:>5} "
                  f"{r['coverage_pct']:>5.1f}% {r['uncovered']:>6}")

    summary_path = output_dir / "discovery_summary.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSummary written to {summary_path}")


if __name__ == "__main__":
    main()
