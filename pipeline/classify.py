#!/usr/bin/env python3
"""Failure archetype classification — per category.

Config-driven version of scripts/archetype_v2_classify.py.
Uses domain config for model selection and prompt rendering.

Usage:
    python -m pipeline.classify --domain arena --category "Battery storage" --test
    python -m pipeline.classify --domain arena --all --batch submit
    python -m pipeline.classify --domain arena --all --batch status
    python -m pipeline.classify --domain arena --all --batch collect
    python -m pipeline.classify --domain arena --reconcile
    python -m pipeline.classify --domain arena --validate
    python -m pipeline.classify --domain arena --refine --all --batch submit
"""

import argparse
import glob
import json
import sys
import yaml
from collections import Counter, defaultdict
from pathlib import Path

import anthropic

from pipeline.config import DomainConfig

ROOT = Path(__file__).resolve().parents[1]
MAX_TOKENS = 600
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
    taxonomy_dir = ROOT / "runs" / domain_lower / "failure_archetypes"
    if not taxonomy_dir.exists() and (ROOT / "insights" / "failure_archetypes" / "v2").exists():
        taxonomy_dir = ROOT / "insights" / "failure_archetypes" / "v2"
    output_dir = taxonomy_dir / "classifications"
    return events_dir, per_doc_dir, taxonomy_dir, output_dir


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


def load_taxonomy(taxonomy_dir, category):
    """Load discovered taxonomy for a category."""
    fname = f"{category.replace('/', '_').replace(' ', '_')}.json"
    path = taxonomy_dir / fname
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def build_taxonomy_text(taxonomy):
    lines = []
    for a in taxonomy["archetypes"]:
        lines.append(f"[{a['parent_category']}] {a['name']}: {a['description']}")
    return "\n".join(lines)


def build_valid_names(taxonomy):
    return "\n".join(a["name"] for a in taxonomy["archetypes"])


def build_user_msg(e):
    return (
        f"Title: {e['event_title']}\n"
        f"What happened: {e['what_happened']}\n"
        f"Consequence: {e.get('consequence', 'N/A')}"
    )


def classify_test(category, events, taxonomy, model, prompt_template):
    """Test classification using Sonnet (sequential)."""
    tax_text = build_taxonomy_text(taxonomy)
    valid_names = build_valid_names(taxonomy)
    system = prompt_template.format(category=category, taxonomy_text=tax_text, valid_names=valid_names)
    client = anthropic.Anthropic()

    results = []
    for i, e in enumerate(events):
        resp = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": build_user_msg(e)}],
        )

        text = resp.content[0].text
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            parsed = json.loads(text[start:end])
        except (json.JSONDecodeError, ValueError):
            parsed = {"primary": "parse_error", "primary_category": "none",
                       "confidence": 0, "secondary": None, "secondary_category": None}

        results.append({
            "event_title": e["event_title"],
            "old_archetype": e.get("failure_mode", ""),
            "old_category": e.get("failure_category", ""),
            "primary": parsed.get("primary", ""),
            "primary_category": parsed.get("primary_category", ""),
            "confidence": parsed.get("confidence", 0),
            "secondary": parsed.get("secondary"),
            "secondary_category": parsed.get("secondary_category"),
        })

        if (i + 1) % 25 == 0:
            print(f"  Classified {i+1}/{len(events)}...")

    return results


def validate_results(results):
    """Validate secondary archetype discipline."""
    primary_set = set(r["primary"] for r in results if r["primary"] != "parse_error")
    secondary_set = set(r["secondary"] for r in results
                        if r.get("secondary") and r["secondary"] != "null")

    orphan_secondaries = secondary_set - primary_set

    n_total = len(results)
    n_primary_only = sum(1 for r in results if not r.get("secondary") or r["secondary"] == "null")
    n_with_secondary = n_total - n_primary_only
    n_parse_error = sum(1 for r in results if r["primary"] == "parse_error")

    pri_counts = Counter(r["primary"] for r in results)
    sec_counts = Counter(r["secondary"] for r in results
                         if r.get("secondary") and r["secondary"] != "null")

    print(f"\n{'='*60}")
    print(f"VALIDATION RESULTS")
    print(f"{'='*60}")
    print(f"Total events:          {n_total}")
    print(f"Primary only:          {n_primary_only} ({n_primary_only/n_total*100:.1f}%)")
    print(f"With secondary:        {n_with_secondary} ({n_with_secondary/n_total*100:.1f}%)")
    print(f"Parse errors:          {n_parse_error}")
    print(f"Unique primaries:      {len(primary_set)}")
    print(f"Unique secondaries:    {len(secondary_set)}")

    if orphan_secondaries:
        print(f"\nORPHAN SECONDARIES (never appear as primary):")
        for s in sorted(orphan_secondaries):
            print(f"  - {s} (assigned as secondary {sec_counts[s]}x)")

    print(f"\nTop 15 primary archetypes:")
    for name, count in pri_counts.most_common(15):
        print(f"  [{count:3d}] {name}")

    if sec_counts:
        print(f"\nTop 10 secondary archetypes:")
        for name, count in sec_counts.most_common(10):
            marker = " *** ORPHAN" if name in orphan_secondaries else ""
            print(f"  [{count:3d}] {name}{marker}")

    return {
        "total": n_total, "primary_only": n_primary_only,
        "with_secondary": n_with_secondary, "parse_errors": n_parse_error,
        "orphan_secondaries": sorted(orphan_secondaries),
    }


def submit_batch(categories, by_cat, taxonomy_dir, output_dir, batch_model, prompt_template, limit=0):
    """Submit classification requests to batch API."""
    client = anthropic.Anthropic()
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_state = output_dir / "batch_state.json"

    requests = []
    for cat in categories:
        taxonomy = load_taxonomy(taxonomy_dir, cat)
        tax_text = build_taxonomy_text(taxonomy)
        valid_names = build_valid_names(taxonomy)
        system = prompt_template.format(category=cat, taxonomy_text=tax_text, valid_names=valid_names)
        events = by_cat[cat]
        if limit:
            events = events[:limit]

        for i, e in enumerate(events):
            safe_cat = cat.replace("/", "_").replace(" ", "_")
            custom_id = f"{safe_cat}___{i}"
            requests.append({
                "custom_id": custom_id,
                "params": {
                    "model": batch_model,
                    "max_tokens": MAX_TOKENS,
                    "system": system,
                    "messages": [{"role": "user", "content": build_user_msg(e)}],
                },
            })

    print(f"Submitting {len(requests)} requests across {len(categories)} categories...")

    batch = client.messages.batches.create(requests=requests)
    print(f"Batch submitted: {batch.id}")

    state = {"batch_id": batch.id, "n_requests": len(requests), "categories": categories}
    with open(batch_state, "w") as f:
        json.dump(state, f, indent=2)
    print(f"State saved to {batch_state}")


def check_status(output_dir):
    batch_state = output_dir / "batch_state.json"
    if not batch_state.exists():
        print("No batch state found.")
        return
    with open(batch_state) as f:
        state = json.load(f)
    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(state["batch_id"])
    counts = batch.request_counts
    print(f"Batch: {state['batch_id']}")
    print(f"Status: {batch.processing_status}")
    print(f"  Succeeded: {counts.succeeded}, Processing: {counts.processing}, Errored: {counts.errored}")


def collect_results(categories, by_cat, output_dir):
    batch_state = output_dir / "batch_state.json"
    if not batch_state.exists():
        print("No batch state found.")
        return
    with open(batch_state) as f:
        state = json.load(f)

    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(state["batch_id"])
    if batch.processing_status != "ended":
        print(f"Batch not done yet: {batch.processing_status}")
        return

    raw_results = {}
    errors = 0
    for result in client.messages.batches.results(state["batch_id"]):
        cid = result.custom_id
        if result.result.type == "succeeded":
            text = result.result.message.content[0].text
            try:
                start = text.find("{")
                end = text.rfind("}") + 1
                parsed = json.loads(text[start:end])
            except (json.JSONDecodeError, ValueError):
                parsed = {"primary": "parse_error", "primary_category": "none",
                           "confidence": 0, "secondary": None, "secondary_category": None}
                errors += 1
        else:
            parsed = {"primary": "api_error", "primary_category": "none",
                       "confidence": 0, "secondary": None, "secondary_category": None}
            errors += 1
        raw_results[cid] = parsed

    print(f"Collected {len(raw_results)} results ({errors} errors)")

    for cat in categories:
        safe_cat = cat.replace("/", "_").replace(" ", "_")
        events = by_cat[cat]
        cat_results = []
        for i, e in enumerate(events):
            cid = f"{safe_cat}___{i}"
            parsed = raw_results.get(cid, {
                "primary": "missing", "primary_category": "none",
                "confidence": 0, "secondary": None, "secondary_category": None,
            })
            cat_results.append({
                "event_title": e["event_title"],
                "old_archetype": e.get("failure_mode", ""),
                "old_category": e.get("failure_category", ""),
                "primary": parsed.get("primary", ""),
                "primary_category": parsed.get("primary_category", ""),
                "confidence": parsed.get("confidence", 0),
                "secondary": parsed.get("secondary"),
                "secondary_category": parsed.get("secondary_category"),
            })

        outpath = output_dir / f"{safe_cat}.json"
        with open(outpath, "w") as f:
            json.dump(cat_results, f, indent=2)
        print(f"  {cat}: {len(cat_results)} results → {outpath.name}")
        validate_results(cat_results)


def submit_refine_batch(categories, by_cat, taxonomy_dir, output_dir, batch_model, prompt_template):
    """Submit only 'Other' events for reclassification against expanded taxonomy."""
    client = anthropic.Anthropic()
    output_dir.mkdir(parents=True, exist_ok=True)
    refine_batch_state = output_dir / "refine_batch_state.json"

    requests = []
    for cat in categories:
        safe_cat = cat.replace("/", "_").replace(" ", "_")
        classify_path = output_dir / f"{safe_cat}.json"
        if not classify_path.exists():
            continue

        with open(classify_path) as f:
            existing_results = json.load(f)

        taxonomy = load_taxonomy(taxonomy_dir, cat)
        tax_text = build_taxonomy_text(taxonomy)
        valid_names = build_valid_names(taxonomy)
        system = prompt_template.format(category=cat, taxonomy_text=tax_text, valid_names=valid_names)

        events = by_cat[cat]
        count = 0
        for i, r in enumerate(existing_results):
            if (r.get("primary") or "").startswith("Other "):
                if i < len(events):
                    e = events[i]
                    custom_id = f"refine_{safe_cat}___{i}"
                    requests.append({
                        "custom_id": custom_id,
                        "params": {
                            "model": batch_model,
                            "max_tokens": MAX_TOKENS,
                            "system": system,
                            "messages": [{"role": "user", "content": build_user_msg(e)}],
                        },
                    })
                    count += 1
        print(f"  {cat}: {count} 'Other' events to reclassify")

    if not requests:
        print("No 'Other' events to reclassify.")
        return

    print(f"\nSubmitting {len(requests)} refine requests...")
    batch = client.messages.batches.create(requests=requests)
    print(f"Batch submitted: {batch.id}")

    state = {"batch_id": batch.id, "n_requests": len(requests), "categories": categories}
    with open(refine_batch_state, "w") as f:
        json.dump(state, f, indent=2)


def check_refine_status(output_dir):
    refine_batch_state = output_dir / "refine_batch_state.json"
    if not refine_batch_state.exists():
        print("No refine batch state found.")
        return
    with open(refine_batch_state) as f:
        state = json.load(f)
    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(state["batch_id"])
    counts = batch.request_counts
    print(f"Refine batch: {state['batch_id']}")
    print(f"Status: {batch.processing_status}")
    print(f"  Succeeded: {counts.succeeded}, Processing: {counts.processing}, Errored: {counts.errored}")


def collect_refine_results(categories, by_cat, output_dir):
    refine_batch_state = output_dir / "refine_batch_state.json"
    if not refine_batch_state.exists():
        print("No refine batch state found.")
        return
    with open(refine_batch_state) as f:
        state = json.load(f)

    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(state["batch_id"])
    if batch.processing_status != "ended":
        print(f"Batch not done yet: {batch.processing_status}")
        return

    raw_results = {}
    errors = 0
    for result in client.messages.batches.results(state["batch_id"]):
        cid = result.custom_id
        if result.result.type == "succeeded":
            text = result.result.message.content[0].text
            try:
                start = text.find("{")
                end = text.rfind("}") + 1
                parsed = json.loads(text[start:end])
            except (json.JSONDecodeError, ValueError):
                parsed = None
                errors += 1
        else:
            parsed = None
            errors += 1
        raw_results[cid] = parsed

    print(f"Collected {len(raw_results)} results ({errors} errors)")

    for cat in categories:
        safe_cat = cat.replace("/", "_").replace(" ", "_")
        classify_path = output_dir / f"{safe_cat}.json"
        if not classify_path.exists():
            continue

        with open(classify_path) as f:
            existing_results = json.load(f)

        updated = 0
        still_other = 0
        for i, r in enumerate(existing_results):
            cid = f"refine_{safe_cat}___{i}"
            if cid in raw_results and raw_results[cid] is not None:
                parsed = raw_results[cid]
                existing_results[i]["primary"] = parsed.get("primary", r["primary"])
                existing_results[i]["primary_category"] = parsed.get("primary_category", r["primary_category"])
                existing_results[i]["confidence"] = parsed.get("confidence", r["confidence"])
                existing_results[i]["secondary"] = parsed.get("secondary")
                existing_results[i]["secondary_category"] = parsed.get("secondary_category")
                new_pri = existing_results[i]["primary"] or ""
                if new_pri.startswith("Other "):
                    still_other += 1
                else:
                    updated += 1

        with open(classify_path, "w") as f:
            json.dump(existing_results, f, indent=2)

        total_other = sum(1 for r in existing_results if (r.get("primary") or "").startswith("Other "))
        print(f"  {cat}: {updated} reclassified, {still_other} still Other, "
              f"{total_other}/{len(existing_results)} total Other "
              f"({total_other/len(existing_results)*100:.0f}%)")
        validate_results(existing_results)


def reconcile_best_of(events_dir, per_doc_dir, taxonomy_dir, output_dir, category_field):
    """For multi-category events, pick the best classification across all categories."""
    cat_results = {}
    for fp in sorted(glob.glob(str(output_dir / "*.json"))):
        if "batch_state" in fp or "refine" in fp:
            continue
        cat = Path(fp).stem
        with open(fp) as f:
            cat_results[cat] = json.load(f)

    record_cats = load_record_categories(per_doc_dir, category_field)
    by_cat = load_events_by_category(events_dir, record_cats)

    event_classifications = defaultdict(list)
    for cat_safe, results in cat_results.items():
        matched_cat = None
        for real_cat in by_cat:
            if real_cat.replace("/", "_").replace(" ", "_") == cat_safe:
                matched_cat = real_cat
                break
        if not matched_cat:
            continue

        events = by_cat[matched_cat]
        for i, r in enumerate(results):
            if i < len(events):
                title = events[i].get("event_title", "")
                if title:
                    event_classifications[title].append({
                        "category": matched_cat,
                        "primary": r.get("primary") or "",
                        "primary_category": r.get("primary_category") or "",
                        "confidence": r.get("confidence", 0) or 0,
                        "secondary": r.get("secondary"),
                        "secondary_category": r.get("secondary_category"),
                    })

    reconciled = {}
    multi_cat_events = 0
    upgraded = 0

    for title, classifications in event_classifications.items():
        if len(classifications) == 1:
            best = classifications[0]
        else:
            multi_cat_events += 1
            sorted_c = sorted(classifications, key=lambda c: (
                0 if c["primary"].startswith("Other ") else 1,
                c["confidence"],
            ), reverse=True)
            best = sorted_c[0]
            worst = sorted_c[-1]
            if worst["primary"].startswith("Other ") and not best["primary"].startswith("Other "):
                upgraded += 1

        reconciled[title] = {
            "primary": best["primary"],
            "primary_category": best["primary_category"],
            "confidence": best["confidence"],
            "secondary": best["secondary"],
            "secondary_category": best["secondary_category"],
            "source_category": best["category"],
            "n_categories": len(classifications),
        }

    n_total = len(reconciled)
    n_other = sum(1 for r in reconciled.values() if r["primary"].startswith("Other "))
    n_multi = sum(1 for r in reconciled.values() if r["n_categories"] > 1)

    print(f"Reconciliation complete:")
    print(f"  Unique events:        {n_total}")
    print(f"  Multi-category:       {n_multi} ({n_multi/n_total*100:.0f}%)")
    print(f"  Upgraded from Other:  {upgraded}")
    print(f"  Final Other rate:     {n_other}/{n_total} ({n_other/n_total*100:.0f}%)")

    reconciled_path = taxonomy_dir / "reconciled_classifications.json"
    with open(reconciled_path, "w") as f:
        json.dump(reconciled, f, indent=2)
    print(f"\n  Written to {reconciled_path}")


def main():
    parser = argparse.ArgumentParser(description="Classify events into failure archetypes")
    parser.add_argument("--domain", required=True, help="Domain name (e.g. arena)")
    parser.add_argument("--category", help="Category name")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--test", action="store_true", help="Test mode: Sonnet, sequential")
    parser.add_argument("--batch", choices=["submit", "status", "collect"])
    parser.add_argument("--refine", action="store_true", help="Reclassify 'Other' events")
    parser.add_argument("--reconcile", action="store_true", help="Best-of reconciliation")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    cfg = DomainConfig.load(args.domain)
    events_dir, per_doc_dir, taxonomy_dir, output_dir = get_dirs(cfg)
    output_dir.mkdir(parents=True, exist_ok=True)

    category_field = cfg.domain.category_field
    model_test = cfg.domain.discovery_model
    model_batch = cfg.domain.classification_model
    prompt_template = cfg.prompt("archetype_classify")

    if args.reconcile:
        print("Loading data...")
        reconcile_best_of(events_dir, per_doc_dir, taxonomy_dir, output_dir, category_field)
        return

    if args.validate:
        for fp in sorted(glob.glob(str(output_dir / "*.json"))):
            if "batch_state" in fp or "refine" in fp:
                continue
            with open(fp) as f:
                results = json.load(f)
            cat = Path(fp).stem
            print(f"\n--- {cat} ---")
            validate_results(results)
        return

    if args.test and args.category:
        print("Loading data...")
        record_cats = load_record_categories(per_doc_dir, category_field)
        by_cat = load_events_by_category(events_dir, record_cats)

        if args.category not in by_cat:
            print(f"Category '{args.category}' not found.")
            sys.exit(1)

        taxonomy = load_taxonomy(taxonomy_dir, args.category)
        if not taxonomy:
            print(f"No taxonomy found for '{args.category}'.")
            sys.exit(1)

        events = by_cat[args.category]
        if args.limit:
            events = events[:args.limit]

        print(f"Classifying {len(events)} {args.category} events "
              f"against {len(taxonomy['archetypes'])} archetypes...")

        results = classify_test(args.category, events, taxonomy, model_test, prompt_template)

        outpath = output_dir / f"{args.category.replace('/', '_').replace(' ', '_')}.json"
        with open(outpath, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results written to {outpath}")
        validate_results(results)

    elif args.batch:
        if args.batch == "status":
            if args.refine:
                check_refine_status(output_dir)
            else:
                check_status(output_dir)
            return

        print("Loading data...")
        record_cats = load_record_categories(per_doc_dir, category_field)
        by_cat = load_events_by_category(events_dir, record_cats)

        if args.category:
            categories = [args.category]
        elif args.all:
            categories = sorted(by_cat.keys())
        else:
            print("Specify --category 'Name' or --all with --batch")
            sys.exit(1)

        valid_cats = []
        for cat in categories:
            if cat not in by_cat:
                print(f"  SKIP {cat}: no events")
                continue
            tax = load_taxonomy(taxonomy_dir, cat)
            if not tax:
                print(f"  SKIP {cat}: no taxonomy")
                continue
            valid_cats.append(cat)

        if args.refine:
            if args.batch == "submit":
                submit_refine_batch(valid_cats, by_cat, taxonomy_dir, output_dir, model_batch, prompt_template)
            elif args.batch == "collect":
                collect_refine_results(valid_cats, by_cat, output_dir)
        else:
            if args.batch == "submit":
                submit_batch(valid_cats, by_cat, taxonomy_dir, output_dir, model_batch, prompt_template, args.limit)
            elif args.batch == "collect":
                collect_results(valid_cats, by_cat, output_dir)

    else:
        print("Specify --test --category 'Name' or --batch submit/status/collect")
        sys.exit(1)


if __name__ == "__main__":
    main()
