"""Shared helpers for the glossary sub-pipeline."""
from __future__ import annotations
import re
from pathlib import Path
from typing import Iterable, Iterator

ROOT = Path(__file__).resolve().parents[3]


def resolve(path: str | Path) -> Path:
    """Resolve a config path: absolute as-is, otherwise relative to repo root."""
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def derive_doc_id(md_path: Path, strategy: str = "parent_name") -> str:
    """Derive a doc identifier from the markdown path.

    parent_name : md.parent.name (marker layout: <slug>/<slug>.rendered.md)
    stem        : md.stem with .rendered suffix stripped
    """
    if strategy == "parent_name":
        return md_path.parent.name
    if strategy == "stem":
        s = md_path.stem
        if s.endswith(".rendered"):
            s = s[:-len(".rendered")]
        return s
    raise ValueError(f"Unknown doc_id strategy: {strategy}")


def iter_markdown(md_dir: Path, glob: str = "*/*.rendered.md") -> Iterator[Path]:
    """Yield markdown files in deterministic order."""
    yield from sorted(md_dir.glob(glob))


def load_stoplist(path: Path | None) -> set[str]:
    """Load a per-corpus stoplist (one entry per line; # comments allowed)."""
    out: set[str] = set()
    if path is None or not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line)
    return out


def derive_slug(value: str, pattern: str | None) -> str:
    """Apply a regex (with one capture group) to extract a slug from a
    catalogue cell. If no pattern is given, returns the value verbatim.

    The pattern is a per-corpus config knob — the engine has no built-in
    knowledge of URL shapes, file extensions, or path conventions.

    Examples (defined in domain.yaml, not in engine code):
      ANAO  page_url   '/([^/]+)/?$'           — last URL segment
      ARENA local_path '([^/]+)\\.[^.]+$'      — filename stem
    """
    if not value:
        return ""
    if not pattern:
        return value.strip()
    import re as _re
    m = _re.search(pattern, value)
    return m.group(1) if m else ""


def load_doc_metadata_from_catalogue(
    catalogue_path: Path,
    slug_column: str,
    slug_pattern: str | None,
    field_columns: dict[str, str],
    valid_slugs: set[str] | None = None,
):
    """Build slug → metadata map directly from a catalogue CSV.

    The catalogue is the canonical source of corpus metadata; no extraction
    artefacts (per_doc records) required.

    Args:
        catalogue_path: CSV file
        slug_column:    catalogue column whose value identifies a document
        slug_pattern:   regex with one capture group applied to the slug
                        column to extract the slug; null/empty = use value
                        as-is
        field_columns:  {logical_field_name: csv_column_name} mapping for
                        the metadata fields the engine wants
                        (e.g. {'project': 'entity', 'category': 'portfolio'})
        valid_slugs:    optional set; rows whose derived slug isn't in this
                        set are skipped

    Returns:
        dict[slug, dict[logical_field, value]] — one entry per matched row.
    """
    import csv
    out: dict[str, dict] = {}
    if not catalogue_path.exists():
        raise FileNotFoundError(f"catalogue_path does not exist: {catalogue_path}")
    for r in csv.DictReader(open(catalogue_path)):
        slug = derive_slug(r.get(slug_column, ""), slug_pattern)
        if not slug:
            continue
        if valid_slugs is not None and slug not in valid_slugs:
            continue
        out[slug] = {logical: (r.get(col) or "").strip()
                     for logical, col in field_columns.items()}
    return out
