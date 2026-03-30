#!/usr/bin/env python3
"""
Match unassigned per_doc records to ARENA portfolio projects.

Records without kb_associated_project have a model-inferred project_name but
no confirmed link to the ARENA portfolio. This script attempts to resolve them:

Pass 1 — Fuzzy match (rapidfuzz) against the projects CSV.
          Accept matches ≥ FUZZY_THRESHOLD. Fast, free, handles minor variations.

Pass 2 — Haiku batch for the remainder.
          Groups unmatched names, sends them to Claude with the full project list,
          asks for confident matches only. Submitted via Anthropic Batch API.

Pass 3 — Collect batch results and apply matches.

Excludes obvious portfolio/study/review documents from matching — these
legitimately have no single project association.

Reads:
  insights/per_doc/doc_*.yaml
  arena-projects-export_1772932404.csv

Writes:
  insights/project_name_matches.yaml        — full match log
  insights/per_doc_qa/match_batch_state.json
  updates insights/per_doc/doc_*.yaml in-place

Usage:
    python scripts/match_unassigned_projects.py --pass1        # fuzzy only
    python scripts/match_unassigned_projects.py --pass2-submit # submit Haiku batch
    python scripts/match_unassigned_projects.py --pass2-collect # collect + apply
    python scripts/match_unassigned_projects.py --dry-run      # show matches, no writes
"""

import argparse
import csv
import json
import re
import glob
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed.")

try:
    from rapidfuzz import process, fuzz
except ImportError:
    raise SystemExit("rapidfuzz not installed. Run: pip install rapidfuzz")

try:
    import anthropic
except ImportError:
    raise SystemExit("anthropic not installed.")

ROOT          = Path(__file__).resolve().parents[1]
PER_DOC_DIR   = ROOT / "insights" / "per_doc"
PROJECTS_CSV  = ROOT / "arena-projects-export_1772932404.csv"
MATCH_LOG     = ROOT / "insights" / "project_name_matches.yaml"
BATCH_STATE   = ROOT / "insights" / "per_doc_qa" / "match_batch_state.json"

MODEL          = "claude-haiku-4-5-20251001"
MAX_TOKENS     = 2048
FUZZY_THRESHOLD = 88   # % similarity to auto-accept
BATCH_SIZE     = 10_000

# Project names containing these keywords are likely portfolio/study docs —
# don't try to match them to a single ARENA project
EXCLUDE_PATTERNS = [
    r'\bportfolio\b', r'\breview\b', r'\bstocktake\b', r'\bsector study\b',
    r'\boptions for\b', r'\bopportunities\b', r'\bpathways? to\b',
    r'\bguidance\b', r'\binitiative\b', r'\bprogram\b', r'\bround \d',
    r'\bbaseline\b', r'\blandscape\b', r'\bframework\b', r'\bsynthesis\b',
    r'\binternational engagement\b',
]

MATCH_PROMPT = """\
You are matching project names to an official ARENA project portfolio list.

For each name in "To match", identify the single best match from the "Portfolio" list.
Only return a match if you are confident — the name clearly refers to the same project,
even if abbreviated, rephrased, or slightly different.

Return ONLY a JSON object mapping each input name to its best portfolio match,
or null if you are not confident. Example:
{{
  "Chargefox EV Charging": "Chargefox Electric Vehicle Charging Network",
  "Some Ambiguous Name": null
}}

## To match
{names_json}

## Portfolio (authoritative ARENA project names)
{portfolio_json}
"""


def load_portfolio() -> list[str]:
    with open(PROJECTS_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [row["Project"].strip() for row in rows if row.get("Project")]


def is_excluded(name: str) -> bool:
    nl = name.lower()
    return any(re.search(pat, nl) for pat in EXCLUDE_PATTERNS)


def load_unmatched() -> dict[str, int]:
    """Return {project_name: record_count} for records missing kb_associated_project."""
    counts: Counter = Counter()
    for path in sorted(PER_DOC_DIR.glob("doc_*.yaml")):
        records = yaml.safe_load(open(path, encoding="utf-8")) or []
        for r in records:
            if not r.get("kb_associated_project"):
                name = (r.get("project_name") or "").strip()
                if name:
                    counts[name] += 1
    return dict(counts)


def apply_matches(matches: dict[str, str], dry_run: bool) -> int:
    """Write kb_associated_project onto matching records. Returns change count."""
    changes = 0
    for path in sorted(PER_DOC_DIR.glob("doc_*.yaml")):
        records = yaml.safe_load(open(path, encoding="utf-8")) or []
        changed = False
        for r in records:
            if r.get("kb_associated_project"):
                continue
            name = (r.get("project_name") or "").strip()
            if name in matches and matches[name]:
                if not dry_run:
                    r["kb_associated_project"] = matches[name]
                    r["in_arena_portfolio"] = True
                changes += 1
                changed = True
        if changed and not dry_run:
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(records, f, allow_unicode=True, sort_keys=False,
                          default_flow_style=False)
    return changes


# ── Pass 1: Fuzzy ─────────────────────────────────────────────────────────────

def run_pass1(unmatched: dict[str, int], portfolio: list[str],
              dry_run: bool) -> tuple[dict[str, str], list[str]]:
    """
    Fuzzy-match unmatched names against portfolio.
    Returns (accepted_matches, still_unmatched_names).
    """
    candidates = [n for n in unmatched if not is_excluded(n)]
    excluded   = [n for n in unmatched if is_excluded(n)]

    print(f"\nPass 1 — Fuzzy matching")
    print(f"  {len(candidates)} names to attempt  ({len(excluded)} excluded as portfolio/study docs)")

    accepted: dict[str, str] = {}
    remainder: list[str] = []

    for name in sorted(candidates):
        result = process.extractOne(name, portfolio, scorer=fuzz.token_sort_ratio)
        if result and result[1] >= FUZZY_THRESHOLD:
            match, score, _ = result
            accepted[name] = match
            print(f"  ✓ [{score:3.0f}%] {name!r:60s} → {match!r}")
        else:
            best = result[1] if result else 0
            remainder.append(name)
            if result:
                print(f"  ✗ [{best:3.0f}%] {name!r}")

    print(f"\n  Accepted: {len(accepted)}  Remainder for Haiku: {len(remainder)}")

    if not dry_run and accepted:
        changes = apply_matches(accepted, dry_run=False)
        print(f"  Applied {changes} record updates from fuzzy matches")

    return accepted, remainder


# ── Pass 2: Haiku batch submit ────────────────────────────────────────────────

def run_pass2_submit(remainder: list[str], portfolio: list[str]):
    """Submit unmatched names to Haiku via Batch API in groups of 20."""
    client = anthropic.Anthropic()
    portfolio_json = json.dumps(portfolio, ensure_ascii=False)

    # Group names into batches of 20 per API request (keeps prompt small)
    GROUP_SIZE = 20
    requests = []
    groups = [remainder[i:i+GROUP_SIZE] for i in range(0, len(remainder), GROUP_SIZE)]

    for i, group in enumerate(groups):
        names_json = json.dumps(group, ensure_ascii=False)
        prompt = MATCH_PROMPT.format(names_json=names_json, portfolio_json=portfolio_json)
        requests.append({
            "custom_id": f"match-group-{i:04d}",
            "params": {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
            },
        })

    print(f"\nPass 2 — Haiku batch submit")
    print(f"  {len(remainder)} names in {len(groups)} groups of {GROUP_SIZE}")

    batch_ids = []
    for i in range(0, len(requests), BATCH_SIZE):
        chunk = requests[i:i+BATCH_SIZE]
        batch = client.messages.batches.create(requests=chunk)
        batch_ids.append(batch.id)
        print(f"  Submitted batch {len(batch_ids)}: {batch.id}  ({len(chunk)} requests)")

    # Save remainder names alongside batch IDs so collect can route results
    state = {
        "batch_ids": batch_ids,
        "groups": groups,
    }
    with open(BATCH_STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"  State saved to {BATCH_STATE}")
    print(f"  Run --pass2-collect when complete.")


# ── Pass 2: Haiku batch collect ───────────────────────────────────────────────

def run_pass2_collect(portfolio: list[str], dry_run: bool):
    if not BATCH_STATE.exists():
        raise SystemExit(f"No batch state at {BATCH_STATE}. Run --pass2-submit first.")

    client = anthropic.Anthropic()
    with open(BATCH_STATE, encoding="utf-8") as f:
        state = json.load(f)

    groups: list[list[str]] = state["groups"]
    portfolio_set = set(portfolio)

    all_matches: dict[str, str] = {}
    confident = 0
    null_returns = 0

    for batch_id in state["batch_ids"]:
        batch = client.messages.batches.retrieve(batch_id)
        print(f"Batch {batch_id}: {batch.processing_status}")
        if batch.processing_status != "ended":
            print("  Not ready — try again later.")
            return

        for result in client.messages.batches.results(batch_id):
            group_idx = int(result.custom_id.split("-")[-1])
            group_names = groups[group_idx]

            if result.result.type != "succeeded":
                continue

            text = result.result.message.content[0].text.strip()
            # Strip markdown fences
            text = re.sub(r"^```(?:json)?\s*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
            try:
                mapping = json.loads(text)
            except json.JSONDecodeError:
                print(f"  WARNING: could not parse response for group {group_idx}")
                continue

            for name in group_names:
                matched = mapping.get(name)
                if matched and matched in portfolio_set:
                    all_matches[name] = matched
                    confident += 1
                    print(f"  ✓ {name!r:60s} → {matched!r}")
                else:
                    null_returns += 1

    print(f"\nPass 2 results: {confident} confident matches, {null_returns} unmatched/null")

    if not dry_run and all_matches:
        changes = apply_matches(all_matches, dry_run=False)
        print(f"Applied {changes} record updates from Haiku matches")

    # Save combined match log
    log = {"pass2_matches": all_matches}
    if MATCH_LOG.exists():
        existing = yaml.safe_load(open(MATCH_LOG)) or {}
        existing.update(log)
        log = existing
    with open(MATCH_LOG, "w", encoding="utf-8") as f:
        yaml.dump(log, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"Match log saved to {MATCH_LOG}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pass1",          action="store_true", help="Run fuzzy matching only")
    parser.add_argument("--pass2-submit",   action="store_true", help="Submit Haiku batch for remainder")
    parser.add_argument("--pass2-collect",  action="store_true", help="Collect Haiku batch results")
    parser.add_argument("--dry-run",        action="store_true", help="Show matches without writing")
    args = parser.parse_args()

    portfolio = load_portfolio()
    print(f"Portfolio: {len(portfolio)} projects")

    if args.pass2_collect:
        run_pass2_collect(portfolio, args.dry_run)
        return

    unmatched = load_unmatched()
    print(f"Unmatched project_names: {len(unmatched)} distinct  "
          f"({sum(unmatched.values()):,} records)")

    if args.pass1 or args.pass2_submit:
        accepted, remainder = run_pass1(unmatched, portfolio, args.dry_run)

        if args.pass2_submit:
            run_pass2_submit(remainder, portfolio)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
