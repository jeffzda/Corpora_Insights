#!/usr/bin/env python3
"""
Merge PDF page-split table fragments into single CSVs and update markdown references.

Background
----------
PyMuPDF's find_tables() detects each page's portion of a multi-page table as a
separate CSV. This script identifies confirmed split pairs (and chains of 3+
fragments), merges them, and updates the markdown cross-references.

Merge logic
-----------
Two consecutive cross-page table fragments are confirmed merges if:
  - Same column count
  - No body text between them in the markdown (only page markers / page numbers)
  - Either: T2's first row == T1's first row (repeated header → strip before merge)
         Or: T2's first row looks like data, not a new header (direct concatenation)

Chains (3+ fragments) are handled by following the merge graph — if T1→T2 and
T2→T3 are both confirmed merges, all three are merged into one CSV.

Output
------
  tables/merged/{merged_filename}.csv   — merged CSV (fragments preserved in place)
  markdown/structured/{slug}.md         — updated in place: multiple [TABLE: ...]
                                          refs replaced with single merged ref

The original fragment CSVs are left untouched so the merge is reversible.
tables_index.json is updated: fragment entries gain a 'merged_into' field;
a new entry is added for each merged file.

Usage
-----
    python scripts/02d_merge_split_tables.py
    python scripts/02d_merge_split_tables.py --dry-run
"""

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT      = Path(__file__).resolve().parents[1]
MD_DIR    = ROOT / 'markdown' / 'structured'
TABLE_DIR = ROOT / 'tables'
MERGED_DIR = TABLE_DIR / 'merged'
INDEX_PATH = ROOT / 'insights' / 'tables_index.json'

TABLE_RE = re.compile(
    r'\[TABLE: tables/([^\s|]+\.csv)([^\]]*)\| Rows: (\d+) \| Cols: (\d+)\]'
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_csv_path(fname: str) -> Path | None:
    for folder in ['', 'noise/', 'broken/']:
        p = TABLE_DIR / folder / fname
        if p.exists():
            return p
    return None


def load_nonempty(fname: str) -> list[list[str]] | None:
    p = get_csv_path(fname)
    if not p:
        return None
    rows = list(csv.reader(open(p, encoding='utf-8')))
    return [r for r in rows if any(c.strip() for c in r)]


def row_sig(row: list[str]) -> tuple:
    return tuple(c.strip().lower() for c in row if c.strip())


def looks_like_header(row: list[str]) -> bool:
    cells = [c.strip() for c in row if c.strip()]
    if not cells:
        return False
    numeric = sum(1 for c in cells if re.match(r'^[\d\s$%.,\-]+$', c))
    return numeric / len(cells) < 0.3


def write_csv(path: Path, rows: list[list[str]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    max_cols = max(len(r) for r in rows) if rows else 0
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row + [''] * (max_cols - len(row)))


# ---------------------------------------------------------------------------
# Step 1: find all confirmed merge pairs across all markdown files
# ---------------------------------------------------------------------------

def find_merge_pairs() -> list[dict]:
    """Return list of confirmed merge pair dicts."""
    pairs = []

    for md_path in sorted(MD_DIR.glob('*.md')):
        text = md_path.read_text(encoding='utf-8')
        refs = [(m.group(1), int(m.group(3)), int(m.group(4)), m.start(), m.end())
                for m in TABLE_RE.finditer(text)]
        if len(refs) < 2:
            continue

        for i in range(len(refs) - 1):
            fname1, rows1, cols1, start1, end1 = refs[i]
            fname2, rows2, cols2, start2, end2 = refs[i + 1]

            if cols1 != cols2:
                continue

            between = text[end1:start2].strip()
            between_clean = re.sub(r'<!--\s*page \d+\s*-->', '', between).strip()
            between_clean = re.sub(r'^\d+\s*$', '', between_clean, flags=re.M).strip()
            if len(between_clean) >= 80:
                continue

            m1 = re.search(r'_p(\d+)_t\d+', fname1)
            m2 = re.search(r'_p(\d+)_t\d+', fname2)
            if not m1 or not m2:
                continue
            page1, page2 = int(m1.group(1)), int(m2.group(1))
            if page2 <= page1:
                continue

            ne1 = load_nonempty(fname1)
            ne2 = load_nonempty(fname2)
            if not ne1 or not ne2:
                continue

            t1_header = row_sig(ne1[0])
            t2_first  = row_sig(ne2[0])
            t1_last   = row_sig(ne1[-1])

            if t1_header == t2_first:
                merge_type = 'repeated_header'
            elif looks_like_header(ne2[0]) and t2_first != t1_last:
                continue  # different table — skip
            else:
                merge_type = 'data_continues'

            pairs.append({
                'md': md_path,
                'fname1': fname1,
                'fname2': fname2,
                'cols': cols1,
                'merge_type': merge_type,
            })

    return pairs


# ---------------------------------------------------------------------------
# Step 2: build chains from pairs
# ---------------------------------------------------------------------------

def build_chains(pairs: list[dict]) -> list[list[str]]:
    """
    Group pairs into chains. If T1→T2 and T2→T3 are both pairs,
    return the chain [T1, T2, T3].
    Also carries merge_type per link and the md path.
    Returns list of chain dicts: {fnames, md, merge_types}
    """
    # next[fname] = (fname_next, merge_type, md)
    nxt = {}
    prev = set()
    md_for = {}
    merge_type_for = {}

    for p in pairs:
        # If fname1 already has a successor and it's from a different md, skip
        # (same table can appear in only one md)
        if p['fname1'] not in nxt:
            nxt[p['fname1']] = p['fname2']
            prev.add(p['fname2'])
            md_for[p['fname1']] = p['md']
            merge_type_for[p['fname1']] = p['merge_type']

    # Find chain starts: nodes with no predecessor
    starts = [f for f in nxt if f not in prev]

    chains = []
    for start in starts:
        chain_fnames = [start]
        chain_types  = []
        cur = start
        while cur in nxt:
            nxt_f = nxt[cur]
            chain_types.append(merge_type_for[cur])
            chain_fnames.append(nxt_f)
            cur = nxt_f

        chains.append({
            'fnames': chain_fnames,
            'md': md_for[start],
            'merge_types': chain_types,
        })

    return chains


# ---------------------------------------------------------------------------
# Step 3: merge CSVs
# ---------------------------------------------------------------------------

def merge_chain(chain: dict) -> tuple[Path, int]:
    """
    Merge all fragments in the chain into a single CSV.
    Returns (merged_path, total_rows).
    """
    fnames = chain['fnames']
    merge_types = chain['merge_types']

    merged_rows = []
    for idx, fname in enumerate(fnames):
        rows = load_nonempty(fname)
        if not rows:
            continue
        if idx == 0:
            merged_rows.extend(rows)
        else:
            # For repeated_header: skip T_n's first row (it duplicates the header)
            link_type = merge_types[idx - 1]
            if link_type == 'repeated_header':
                merged_rows.extend(rows[1:])
            else:
                merged_rows.extend(rows)

    # Build merged filename from first fragment
    first_stem = Path(fnames[0]).stem
    # Replace _pNNN_tNN suffix with _pNNN_merged (using first page)
    merged_stem = re.sub(r'(_p\d+)_t\d+$', r'\1_merged', first_stem)
    merged_path = MERGED_DIR / f"{merged_stem}.csv"

    return merged_path, merged_rows


# ---------------------------------------------------------------------------
# Step 4: update markdown references
# ---------------------------------------------------------------------------

def build_table_ref(csv_rel_path: str, caption_part: str, nrows: int, ncols: int) -> str:
    cap = caption_part.strip().rstrip('|').strip()
    cap_str = f" {cap} |" if cap else ""
    return f"[TABLE: {csv_rel_path}{cap_str} | Rows: {nrows} | Cols: {ncols}]"


def update_markdown(md_path: Path, chain: dict, merged_path: Path,
                    merged_rows: list, dry_run: bool = False) -> bool:
    """
    Replace the N individual TABLE refs with a single merged ref.
    Returns True if a replacement was made.
    """
    text = md_path.read_text(encoding='utf-8')
    fnames = chain['fnames']

    # Find positions of all refs for this chain in the markdown
    all_matches = list(TABLE_RE.finditer(text))
    chain_set = set(fnames)
    chain_matches = [m for m in all_matches if m.group(1) in chain_set]

    if len(chain_matches) != len(fnames):
        return False  # couldn't find all fragments in this file

    # Verify they are contiguous in the file
    indices = [all_matches.index(m) for m in chain_matches]
    if indices != list(range(indices[0], indices[0] + len(fnames))):
        return False

    # Build replacement ref using first match's caption
    first_match = chain_matches[0]
    caption_part = first_match.group(2)  # everything between filename and Rows:
    ncols = int(first_match.group(4))
    nrows = len(merged_rows)

    merged_rel = f"tables/merged/{merged_path.name}"
    new_ref = build_table_ref(merged_rel, caption_part, nrows, ncols)

    # Replace the span from start of first match to end of last match
    start = chain_matches[0].start()
    end   = chain_matches[-1].end()
    new_text = text[:start] + new_ref + text[end:]

    if not dry_run:
        md_path.write_text(new_text, encoding='utf-8')

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Merge page-split table fragments")
    parser.add_argument('--dry-run', action='store_true',
                        help='Detect and report merges but write no files')
    args = parser.parse_args()

    print("Finding merge pairs...")
    pairs = find_merge_pairs()
    print(f"  Confirmed pairs: {len(pairs)}")

    print("Building chains...")
    chains = build_chains(pairs)
    total_fragments = sum(len(c['fnames']) for c in chains)
    print(f"  Chains: {len(chains)}  ({total_fragments} fragments → {len(chains)} merged tables)")

    chain_lengths = {}
    for c in chains:
        n = len(c['fnames'])
        chain_lengths[n] = chain_lengths.get(n, 0) + 1
    for n, count in sorted(chain_lengths.items()):
        print(f"    {n}-fragment chains: {count}")

    if not args.dry_run:
        MERGED_DIR.mkdir(parents=True, exist_ok=True)

    # Load index for updating
    index = json.loads(INDEX_PATH.read_text(encoding='utf-8'))
    index_by_fname = {e['filename']: e for e in index}

    stats = {'merged': 0, 'md_updated': 0, 'errors': 0}

    for chain in chains:
        merged_path, merged_rows = merge_chain(chain)

        if not merged_rows:
            stats['errors'] += 1
            continue

        # Write merged CSV
        if not args.dry_run:
            write_csv(merged_path, merged_rows)

        # Update markdown
        updated = update_markdown(chain['md'], chain, merged_path,
                                  merged_rows, dry_run=args.dry_run)
        if updated:
            stats['md_updated'] += 1
        else:
            stats['errors'] += 1
            continue

        stats['merged'] += 1

        # Update index: mark fragments, add merged entry
        if not args.dry_run:
            for fname in chain['fnames']:
                if fname in index_by_fname:
                    index_by_fname[fname]['merged_into'] = merged_path.name

            # Use metadata from first fragment
            first_entry = index_by_fname.get(chain['fnames'][0], {})
            new_entry = {
                'filename': merged_path.name,
                'slug': first_entry.get('slug', ''),
                'clean': True,
                'merged': True,
                'fragment_count': len(chain['fnames']),
                'rows': len(merged_rows),
                'cols': first_entry.get('cols', 0),
                'title': first_entry.get('title', ''),
                'doc_type': first_entry.get('doc_type', ''),
                'project': first_entry.get('project', ''),
                'year': first_entry.get('year', ''),
                'category': first_entry.get('category', ''),
            }
            index.append(new_entry)
            index_by_fname[merged_path.name] = new_entry

    if not args.dry_run:
        INDEX_PATH.write_text(
            json.dumps(index, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"\nIndex updated: {INDEX_PATH}")

    print(f"\nDone.")
    print(f"  Chains merged:      {stats['merged']}")
    print(f"  Markdown files updated: {stats['md_updated']}")
    print(f"  Errors/skipped:     {stats['errors']}")
    if not args.dry_run:
        print(f"  Merged CSVs in:     {MERGED_DIR}")


if __name__ == '__main__':
    main()
