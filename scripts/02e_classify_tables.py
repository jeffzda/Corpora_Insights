#!/usr/bin/env python3
"""
Classify all clean tables in the ARENA corpus into semantic categories using Claude Haiku.

Each clean entry in tables_index.json gains a `table_category` field, enabling
fast downstream retrieval by data type (e.g. "give me all cost_breakdown tables
for solar projects") without needing to grep table contents.

Categories
----------
  cost_breakdown      — capex/opex line items, cost components, budget breakdowns
  performance_metrics — efficiency %, output MWh, capacity factors, generation data,
                        test/measurement results
  financial_summary   — total project cost, ARENA funding, funding ratios, project budgets
  technology_comparison — side-by-side comparison of technologies, options, or scenarios
  schedule_milestone  — dates, project phases, timelines, milestones, Gantt-style
  specifications      — equipment specs, technical parameters, ratings, material properties
  project_summary     — project overview, status updates, KPI tables, objectives/outcomes
  survey_results      — survey responses, stakeholder data, questionnaire results
  glossary            — definitions, acronyms, abbreviations
  other               — doesn't fit above categories clearly

Process
-------
  1. Load tables_index.json, filter to clean entries not yet classified
  2. Batch 20 tables per API call; send table metadata + first 3 content rows to Haiku
  3. Parse JSON response, store category per filename
  4. Checkpoint to insights/table_categories.json every 50 batches (resumable)
  5. On completion (or --merge): write table_category into tables_index.json

Usage
-----
    python scripts/02e_classify_tables.py                  # classify all clean tables
    python scripts/02e_classify_tables.py --dry-run        # show sample prompt, no API
    python scripts/02e_classify_tables.py --limit 200      # classify first N clean tables
    python scripts/02e_classify_tables.py --merge-only     # just merge checkpoint → index
    python scripts/02e_classify_tables.py --stats          # show category breakdown

Cost (estimate)
---------------
    11,940 clean tables / 20 per batch = ~600 API calls
    ~2,000 input + 200 output tokens per call ≈ $1.50 total with Haiku

Requires
--------
    pip install anthropic
"""

import argparse
import csv
import json
import time
from pathlib import Path

try:
    import anthropic
except ImportError:
    raise SystemExit("anthropic not installed. Run: pip install anthropic")

ROOT         = Path(__file__).resolve().parents[1]
TABLE_DIR    = ROOT / 'tables'
INDEX_PATH   = ROOT / 'insights' / 'tables_index.json'
CHECKPOINT   = ROOT / 'insights' / 'table_categories.json'

MODEL        = 'claude-haiku-4-5-20251001'
BATCH_SIZE   = 20      # tables per API call
CHECKPOINT_EVERY = 50  # batches between checkpoint writes
MAX_RETRIES  = 4
RETRY_BASE   = 5       # seconds

CATEGORIES = [
    'cost_breakdown',
    'performance_metrics',
    'financial_summary',
    'technology_comparison',
    'schedule_milestone',
    'specifications',
    'project_summary',
    'survey_results',
    'glossary',
    'other',
]

CATEGORY_DESCRIPTIONS = {
    'cost_breakdown':       'capex/opex line items, cost components, budget breakdowns, $/unit cost tables',
    'performance_metrics':  'efficiency %, output MWh, capacity factors, generation data, test/measurement results, performance KPIs',
    'financial_summary':    'total project cost, ARENA funding, funding ratios, project budgets, financial model outputs',
    'technology_comparison':'side-by-side comparison of technologies, options, scenarios, or alternatives',
    'schedule_milestone':   'dates, project phases, timelines, milestones, Gantt-style tables, planned vs actual',
    'specifications':       'equipment specs, technical parameters, ratings, material properties, design parameters',
    'project_summary':      'project overview, status updates, KPI tables, objectives/outcomes, key facts',
    'survey_results':       'survey responses, stakeholder data, questionnaire results, rankings/ratings from participants',
    'glossary':             'definitions, acronyms, abbreviations, terminology tables',
    'other':                "doesn't fit above categories",
}


# ---------------------------------------------------------------------------
# Table loading
# ---------------------------------------------------------------------------

def get_csv_path(filename: str) -> Path | None:
    for folder in ['', 'merged/', 'noise/', 'broken/']:
        p = TABLE_DIR / folder / filename
        if p.exists():
            return p
    return None


def load_table_preview(filename: str, max_rows: int = 3, max_cells: int = 6,
                       cell_width: int = 45) -> list[list[str]]:
    """Return first max_rows non-empty rows, truncated for prompt efficiency."""
    p = get_csv_path(filename)
    if not p:
        return []
    try:
        rows = list(csv.reader(open(p, encoding='utf-8')))
    except Exception:
        return []
    preview = []
    for row in rows:
        cells = [c.strip()[:cell_width] for c in row if c.strip()]
        if cells:
            preview.append(cells[:max_cells])
        if len(preview) >= max_rows:
            break
    return preview


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

def build_prompt(batch: list[dict]) -> str:
    cat_lines = '\n'.join(
        f'  {cat}: {desc}' for cat, desc in CATEGORY_DESCRIPTIONS.items()
    )
    tables_text = ''
    for i, entry in enumerate(batch):
        preview = load_table_preview(entry['filename'])
        preview_str = '\n'.join('    ' + str(row) for row in preview) if preview else '    (no preview available)'
        tables_text += (
            f"\n[{i}] {entry['filename']}\n"
            f"    Title: {entry.get('title', '')[:80]}\n"
            f"    Size: {entry['rows']} rows × {entry['cols']} cols\n"
            f"    Preview:\n{preview_str}\n"
        )

    return f"""Classify each table into exactly one category. Return ONLY a JSON array of {len(batch)} category strings, in the same order as the tables. No explanation.

Categories:
{cat_lines}

Tables:{tables_text}

Return format: ["category0", "category1", ...]"""


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def call_api(client: anthropic.Anthropic, prompt: str) -> str:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            msg = client.messages.create(
                model=MODEL,
                max_tokens=256,
                messages=[{'role': 'user', 'content': prompt}],
            )
            return msg.content[0].text.strip()
        except anthropic.RateLimitError as e:
            delay = RETRY_BASE * (2 ** (attempt - 1))
            print(f"  Rate limit (attempt {attempt}/{MAX_RETRIES}), waiting {delay}s")
            time.sleep(delay)
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                delay = RETRY_BASE * attempt
                print(f"  Server error {e.status_code} (attempt {attempt}), waiting {delay}s")
                time.sleep(delay)
            else:
                raise
    raise RuntimeError(f"API failed after {MAX_RETRIES} attempts")


def parse_response(response: str, batch_size: int) -> list[str]:
    """Extract list of categories from model response."""
    # Strip markdown code fences if present
    text = response.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        text = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
    try:
        result = json.loads(text)
        if isinstance(result, list):
            # Validate and normalise each category
            normalised = []
            for cat in result[:batch_size]:
                cat_str = str(cat).strip().lower()
                if cat_str in CATEGORIES:
                    normalised.append(cat_str)
                else:
                    # Fuzzy match: find closest category by prefix
                    match = next((c for c in CATEGORIES if c.startswith(cat_str[:6])), 'other')
                    normalised.append(match)
            # Pad if model returned fewer items than batch
            while len(normalised) < batch_size:
                normalised.append('other')
            return normalised
    except (json.JSONDecodeError, TypeError):
        pass
    # Fallback: try to extract quoted strings
    import re
    found = re.findall(r'"([a-z_]+)"', text)
    valid = [c for c in found if c in CATEGORIES]
    while len(valid) < batch_size:
        valid.append('other')
    return valid[:batch_size]


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def load_checkpoint() -> dict[str, str]:
    if CHECKPOINT.exists():
        return json.loads(CHECKPOINT.read_text(encoding='utf-8'))
    return {}


def save_checkpoint(categories: dict[str, str]):
    CHECKPOINT.write_text(json.dumps(categories, indent=2, ensure_ascii=False), encoding='utf-8')


def merge_into_index(categories: dict[str, str]) -> tuple[int, int]:
    """Write table_category field into tables_index.json. Returns (updated, skipped)."""
    index = json.loads(INDEX_PATH.read_text(encoding='utf-8'))
    updated = skipped = 0
    for entry in index:
        fname = entry.get('filename', '')
        if fname in categories:
            entry['table_category'] = categories[fname]
            updated += 1
        elif entry.get('clean') and 'table_category' not in entry:
            skipped += 1
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding='utf-8')
    return updated, skipped


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def print_stats():
    checkpoint = load_checkpoint()
    if not checkpoint:
        print("No checkpoint found. Run classification first.")
        return
    from collections import Counter
    counts = Counter(checkpoint.values())
    total = sum(counts.values())
    print(f"\nTable categories ({total:,} classified):")
    for cat in CATEGORIES:
        n = counts.get(cat, 0)
        bar = '█' * (n * 40 // max(counts.values()))
        print(f"  {cat:<22} {n:>5,}  {n/total*100:4.1f}%  {bar}")

    # Also check index
    index = json.loads(INDEX_PATH.read_text(encoding='utf-8'))
    in_index = sum(1 for e in index if 'table_category' in e)
    print(f"\n{in_index:,} entries have table_category in tables_index.json")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Classify clean tables by semantic category')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show sample prompt and stats, no API calls')
    parser.add_argument('--limit', type=int, default=None,
                        help='Classify only the first N unclassified clean tables')
    parser.add_argument('--merge-only', action='store_true',
                        help='Skip classification; just merge checkpoint into tables_index.json')
    parser.add_argument('--stats', action='store_true',
                        help='Show category breakdown from checkpoint and exit')
    args = parser.parse_args()

    if args.stats:
        print_stats()
        return

    # Load index and checkpoint
    index = json.loads(INDEX_PATH.read_text(encoding='utf-8'))
    categories = load_checkpoint()

    if args.merge_only:
        if not categories:
            print("No checkpoint found. Nothing to merge.")
            return
        updated, skipped = merge_into_index(categories)
        print(f"Merged {updated:,} categories into {INDEX_PATH.name}")
        print(f"  {skipped:,} clean tables still unclassified")
        return

    # Find clean tables not yet classified
    to_classify = [
        e for e in index
        if e.get('clean') and e.get('filename') not in categories
    ]
    if args.limit:
        to_classify = to_classify[:args.limit]

    total = len(to_classify)
    print(f"Clean tables to classify: {total:,}")
    print(f"Already classified: {len(categories):,}")
    if args.dry_run:
        sample = to_classify[:BATCH_SIZE]
        print(f"\nSample prompt (first {len(sample)} tables):\n")
        print(build_prompt(sample))
        print(f"\n[dry-run] Would make ~{(total + BATCH_SIZE - 1) // BATCH_SIZE:,} API calls")
        return

    if total == 0:
        print("All clean tables already classified. Use --stats or --merge-only.")
        return

    client = anthropic.Anthropic()

    # Process in batches
    batches = [to_classify[i:i+BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
    n_batches = len(batches)
    classified = 0
    errors = 0

    print(f"Processing {n_batches:,} batches of up to {BATCH_SIZE}...")
    start_time = time.time()

    for batch_idx, batch in enumerate(batches):
        prompt = build_prompt(batch)
        try:
            response = call_api(client, prompt)
            cats = parse_response(response, len(batch))
            for entry, cat in zip(batch, cats):
                categories[entry['filename']] = cat
            classified += len(batch)
        except Exception as e:
            print(f"  Batch {batch_idx+1} failed: {e}")
            for entry in batch:
                categories[entry['filename']] = 'other'
            errors += len(batch)

        # Progress
        if (batch_idx + 1) % 10 == 0 or batch_idx == n_batches - 1:
            elapsed = time.time() - start_time
            rate = classified / elapsed if elapsed > 0 else 0
            remaining = (total - classified) / rate if rate > 0 else 0
            print(f"  [{batch_idx+1:4d}/{n_batches}] {classified:,}/{total:,} classified"
                  f" | {rate:.0f} tables/s | ~{remaining/60:.1f} min remaining")

        # Checkpoint
        if (batch_idx + 1) % CHECKPOINT_EVERY == 0:
            save_checkpoint(categories)

    # Final checkpoint and merge
    save_checkpoint(categories)
    print(f"\nCheckpoint saved: {CHECKPOINT}")

    updated, skipped = merge_into_index(categories)
    print(f"Merged into index: {updated:,} entries updated, {skipped:,} still unclassified")
    print(f"Errors/fallbacks: {errors:,}")

    # Summary breakdown
    from collections import Counter
    counts = Counter(categories.values())
    print(f"\nCategory breakdown ({sum(counts.values()):,} total):")
    for cat in CATEGORIES:
        n = counts.get(cat, 0)
        print(f"  {cat:<22} {n:>5,}  ({n/sum(counts.values())*100:.1f}%)")


if __name__ == '__main__':
    main()
