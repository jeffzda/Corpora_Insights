#!/usr/bin/env python3
"""
Step 4c: Within-project deduplication of extracted delivery insight records.

Multiple documents from the same ARENA project often describe the same delivery
event. This script groups records by project, uses Haiku to identify which records
describe the same underlying event, then merges each group into a single canonical
record — keeping the richest information from all contributors.

Inputs:
  insights/per_doc/doc_*.yaml       — extracted per-document records

Outputs:
  insights/per_project/<slug>.yaml  — canonical deduped records per project
  insights/registry_deduped.yaml    — flat registry of all canonical records
  insights/dedup_report.yaml        — merge statistics

Usage:
    python scripts/04c_dedup_within_project.py
    python scripts/04c_dedup_within_project.py --project "AGL Solar Project"
    python scripts/04c_dedup_within_project.py --resume
    python scripts/04c_dedup_within_project.py --dry-run

Model: claude-haiku-4-5-20251001
Cost:  ~$0.50 for full 500-project corpus
"""

import argparse
import glob
import json
import re
import time
from collections import Counter
from pathlib import Path

try:
    import anthropic
except ImportError:
    raise SystemExit("anthropic not installed. Run: pip install anthropic")

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed. Run: pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
PER_DOC_DIR = ROOT / "insights" / "per_doc"
PER_PROJECT_DIR = ROOT / "insights" / "per_project"
DEDUPED_REGISTRY = ROOT / "insights" / "registry_deduped.yaml"
DEDUP_REPORT = ROOT / "insights" / "dedup_report.yaml"

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 2048
MAX_RETRIES = 5
RETRY_BASE_DELAY = 10

SEVERITY_ORDER = ["none", "minor", "moderate", "major", "critical"]
TRANSFERABILITY_ORDER = ["narrow", "moderate", "broad"]

GROUP_PROMPT = """\
You are deduplicating delivery insight records for a single ARENA project.
The records below were extracted from multiple documents about the same project.
Some may describe the same delivery event documented in different reports.

Group records that describe the same underlying delivery event.
Records about completely different events must be in separate groups.

Return ONLY a JSON list of groups (each group is a list of record_ids).
Every record_id must appear in exactly one group.
Single-record groups are fine — not everything will be a duplicate.

Example output:
[
  ["ARENA-DLV-0001", "ARENA-DLV-0045"],
  ["ARENA-DLV-0002"],
  ["ARENA-DLV-0003", "ARENA-DLV-0089", "ARENA-DLV-0120"]
]

Records:
{records_yaml}
"""


def load_all_records(input_dir: Path) -> list[dict]:
    records = []
    for path in sorted(glob.glob(str(input_dir / "doc_*.yaml"))):
        with open(path, encoding="utf-8") as f:
            recs = yaml.safe_load(f)
            if recs:
                records.extend(recs)
    return records


def group_by_project(records: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for r in records:
        proj = (r.get("kb_associated_project") or r.get("project_name") or "").strip()
        if not proj:
            proj = "__no_project__"
        groups.setdefault(proj, []).append(r)
    return groups


def project_slug(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:80]


def call_api(client: anthropic.Anthropic, prompt: str) -> str:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            msg = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        except anthropic.RateLimitError:
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            print(f"    Rate limit (attempt {attempt}/{MAX_RETRIES}), waiting {delay}s")
            time.sleep(delay)
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                delay = RETRY_BASE_DELAY * attempt
                print(f"    Server error {e.status_code}, waiting {delay}s")
                time.sleep(delay)
            else:
                raise
    raise RuntimeError(f"API failed after {MAX_RETRIES} attempts")


def parse_groups(response: str, record_ids: set[str]) -> list[list[str]] | None:
    """Parse JSON groups from model response, validate all record_ids accounted for."""
    text = re.sub(r"^```(?:json)?\s*\n?", "", response.strip())
    text = re.sub(r"\n?```\s*$", "", text)
    try:
        groups = json.loads(text)
        if not isinstance(groups, list):
            return None
        seen = set()
        for g in groups:
            if not isinstance(g, list):
                return None
            for rid in g:
                if rid in seen:
                    print(f"    WARNING: duplicate record_id in groups: {rid}")
                    return None
                seen.add(rid)
        # Check all record_ids accounted for
        missing = record_ids - seen
        extra = seen - record_ids
        if missing:
            print(f"    WARNING: {len(missing)} record_ids missing from groups: {list(missing)[:3]}")
        if extra:
            print(f"    WARNING: {len(extra)} unknown record_ids in groups: {list(extra)[:3]}")
        # Return groups filtered to known ids, adding any missing as singletons
        valid_groups = [[rid for rid in g if rid in record_ids] for g in groups]
        valid_groups = [g for g in valid_groups if g]
        for rid in missing:
            valid_groups.append([rid])
        return valid_groups
    except (json.JSONDecodeError, TypeError):
        return None


def merge_field_longest(records: list[dict], field: str) -> str | None:
    vals = [r.get(field) for r in records if r.get(field)]
    if not vals:
        return None
    return max(vals, key=len)


def merge_field_max_ordered(records: list[dict], field: str, order: list[str]):
    vals = [r.get(field) for r in records if r.get(field) in order]
    if not vals:
        return records[0].get(field)
    return max(vals, key=lambda v: order.index(v))


def merge_field_majority(records: list[dict], field: str, prefer_nonnull: bool = True):
    vals = [r.get(field) for r in records if r.get(field)]
    if not vals:
        return None
    counts = Counter(vals)
    return counts.most_common(1)[0][0]


def merge_source_pages(records: list[dict]) -> list | None:
    all_pages = []
    for r in records:
        sp = r.get("source_pages")
        if sp:
            if isinstance(sp, list):
                all_pages.extend(sp)
            elif isinstance(sp, int):
                all_pages.append(sp)
    if not all_pages:
        return None
    return sorted(set(all_pages))


def merge_secondary_failure_mode(records: list[dict]) -> str | None:
    vals = {r.get("secondary_failure_mode") for r in records if r.get("secondary_failure_mode")}
    if not vals:
        return None
    return list(vals)[0] if len(vals) == 1 else ", ".join(sorted(vals))


def merge_group(group_records: list[dict]) -> dict:
    """Merge a group of records describing the same event into one canonical record."""
    if len(group_records) == 1:
        r = dict(group_records[0])
        r["corroboration_count"] = 1
        r["source_doc_count"] = 1
        r["contributing_record_ids"] = [r["record_id"]]
        r["contributing_source_titles"] = [r.get("source_title", "")]
        sp = r.get("source_pages")
        r["contributing_sources"] = [{
            "source_title":      r.get("source_title", ""),
            "pdf_url":           r.get("pdf_url") or None,
            "source_pages":      sp if isinstance(sp, list) else ([sp] if sp else None),
            "source_url":        r.get("source_url") or None,
            "markdown_filename": r.get("markdown_filename") or None,
        }]
        return r

    # Use the record with the most evidence as the base
    base = max(group_records, key=lambda r: len(r.get("what_happened") or ""))
    canonical = dict(base)

    # Text fields — longest wins
    for field in ("what_happened", "lesson_learnt", "evidence_excerpt", "intervention_note"):
        canonical[field] = merge_field_longest(group_records, field)

    # Ordered max fields
    canonical["issue_severity"] = merge_field_max_ordered(
        group_records, "issue_severity", SEVERITY_ORDER)
    canonical["transferability"] = merge_field_max_ordered(
        group_records, "transferability", TRANSFERABILITY_ORDER)

    # Majority vote fields
    for field in ("failure_mode", "lifecycle_phase", "outcome_class",
                  "project_type", "project_scale_band", "proponent_type",
                  "technology_domain", "delay_category", "delay_magnitude"):
        canonical[field] = merge_field_majority(group_records, field)

    # Union fields
    canonical["source_pages"] = merge_source_pages(group_records)
    canonical["secondary_failure_mode"] = merge_secondary_failure_mode(group_records)

    # Provenance
    canonical["corroboration_count"] = len(group_records)
    canonical["source_doc_count"] = len({r.get("source_title") for r in group_records
                                         if r.get("source_title")})
    canonical["contributing_record_ids"] = [r["record_id"] for r in group_records]
    canonical["contributing_source_titles"] = list({
        r.get("source_title", "") for r in group_records if r.get("source_title")
    })
    # Store per-source links so the dashboard can link to every contributing document
    seen_titles = set()
    contributing_sources = []
    for r in group_records:
        title = r.get("source_title", "")
        if title in seen_titles:
            continue
        seen_titles.add(title)
        sp = r.get("source_pages")
        contributing_sources.append({
            "source_title":      title,
            "pdf_url":           r.get("pdf_url") or None,
            "source_pages":      sp if isinstance(sp, list) else ([sp] if sp else None),
            "source_url":        r.get("source_url") or None,
            "markdown_filename": r.get("markdown_filename") or None,
        })
    canonical["contributing_sources"] = contributing_sources

    # Confidence note
    note_parts = []
    existing_note = base.get("confidence_note") or ""
    if existing_note:
        note_parts.append(existing_note)
    note_parts.append(
        f"Canonical record merged from {len(group_records)} source records "
        f"across {canonical['source_doc_count']} document(s)."
    )
    canonical["confidence_note"] = " ".join(note_parts)

    return canonical


def dedup_project(project_name: str, records: list[dict],
                  client: anthropic.Anthropic, dry_run: bool) -> list[dict]:
    """Dedup records for one project. Returns list of canonical records."""
    if len(records) == 1:
        r = dict(records[0])
        r["corroboration_count"] = 1
        r["source_doc_count"] = 1
        r["contributing_record_ids"] = [r["record_id"]]
        r["contributing_source_titles"] = [r.get("source_title", "")]
        return [r]

    # Build compact YAML for grouping prompt (only 4 fields)
    compact = []
    for r in records:
        compact.append({
            "record_id": r["record_id"],
            "what_happened": (r.get("what_happened") or "")[:200],
            "failure_mode": r.get("failure_mode"),
            "lifecycle_phase": r.get("lifecycle_phase"),
        })
    records_yaml = yaml.dump(compact, allow_unicode=True, default_flow_style=False)
    prompt = GROUP_PROMPT.format(records_yaml=records_yaml)

    if dry_run:
        print(f"  [dry-run] Would call API for {len(records)} records")
        return [merge_group([r]) for r in records]

    response = call_api(client, prompt)
    record_ids = {r["record_id"] for r in records}
    groups = parse_groups(response, record_ids)

    if groups is None:
        print(f"  WARNING: could not parse groups — treating all as singletons")
        groups = [[r["record_id"]] for r in records]

    # Build lookup by record_id
    by_id = {r["record_id"]: r for r in records}

    canonical_records = []
    for group_ids in groups:
        group_recs = [by_id[rid] for rid in group_ids if rid in by_id]
        if group_recs:
            canonical_records.append(merge_group(group_recs))

    n_merged = len(records) - len(canonical_records)
    print(f"  {len(records)} records → {len(canonical_records)} canonical "
          f"({n_merged} merged)")
    return canonical_records


def main():
    parser = argparse.ArgumentParser(description="Within-project deduplication")
    parser.add_argument("--input", default=str(PER_DOC_DIR))
    parser.add_argument("--project", type=str, default=None,
                        help="Process only this project name (exact match)")
    parser.add_argument("--resume", action="store_true",
                        help="Skip projects that already have per_project output")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print grouping prompts but make no API calls or writes")
    args = parser.parse_args()

    PER_PROJECT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading records...")
    all_records = load_all_records(Path(args.input))
    if not all_records:
        raise SystemExit(f"No records found in {args.input}")
    print(f"Loaded {len(all_records)} records")

    project_groups = group_by_project(all_records)

    if args.project:
        if args.project not in project_groups:
            raise SystemExit(f"Project not found: {args.project!r}")
        project_groups = {args.project: project_groups[args.project]}

    if args.resume:
        before = len(project_groups)
        project_groups = {
            p: recs for p, recs in project_groups.items()
            if not (PER_PROJECT_DIR / f"{project_slug(p)}.yaml").exists()
        }
        print(f"Resuming: {len(project_groups)} of {before} projects to process")

    client = None if args.dry_run else anthropic.Anthropic()
    print(f"Processing {len(project_groups)} project(s) using {MODEL}\n")

    all_canonical: list[dict] = []
    report_rows: list[dict] = []
    total_raw = total_canonical = 0

    for proj_name, records in sorted(project_groups.items()):
        print(f"[{proj_name[:70]}]  {len(records)} record(s)")
        canonical = dedup_project(proj_name, records, client, args.dry_run)

        all_canonical.extend(canonical)
        total_raw += len(records)
        total_canonical += len(canonical)

        corroboration_counts = [r["corroboration_count"] for r in canonical]
        report_rows.append({
            "project": proj_name,
            "raw_records": len(records),
            "canonical_records": len(canonical),
            "merged": len(records) - len(canonical),
            "max_corroboration": max(corroboration_counts),
            "corroborated_events": sum(1 for c in corroboration_counts if c > 1),
        })

        if not args.dry_run:
            slug = project_slug(proj_name)
            out_path = PER_PROJECT_DIR / f"{slug}.yaml"
            with open(out_path, "w", encoding="utf-8") as f:
                yaml.dump(canonical, f, allow_unicode=True, sort_keys=False,
                          default_flow_style=False)

    if not args.dry_run:
        # Write flat deduped registry
        with open(DEDUPED_REGISTRY, "w", encoding="utf-8") as f:
            yaml.dump(all_canonical, f, allow_unicode=True, sort_keys=False,
                      default_flow_style=False)
        print(f"\nWrote {DEDUPED_REGISTRY.name} ({len(all_canonical)} canonical records)")

        # Write dedup report
        with open(DEDUP_REPORT, "w", encoding="utf-8") as f:
            yaml.dump(report_rows, f, allow_unicode=True, sort_keys=False,
                      default_flow_style=False)
        print(f"Wrote {DEDUP_REPORT.name}")

    print(f"\nDone.")
    print(f"  Raw records:       {total_raw}")
    print(f"  Canonical records: {total_canonical}")
    print(f"  Merged away:       {total_raw - total_canonical} "
          f"({100*(total_raw-total_canonical)/total_raw:.0f}%)")
    corroborated = sum(1 for r in all_canonical if r.get("corroboration_count", 1) > 1)
    print(f"  Corroborated events (2+ source records): {corroborated}")


if __name__ == "__main__":
    main()
