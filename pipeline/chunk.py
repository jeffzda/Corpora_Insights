#!/usr/bin/env python3
"""Universal paragraph-level markdown chunker.

Produces one chunk per paragraph with full hierarchical metadata and
synthetic paragraph IDs. Works across all document types:

  - Documents with existing numbered paragraphs (APH committee reports:
    1.1, 2.15, 9.258) — preserves original IDs.
  - Documents with numbered sections (ARENA: 1.0, 3.1) — assigns
    sequential paragraph IDs under each section (3.1.1, 3.1.2, ...).
  - Documents with markdown headings (PC, ANAO) — assigns section
    numbers from heading order and paragraph IDs within each section.
  - Documents with minimal structure — uses page breaks as section
    boundaries and assigns sequential IDs.

Every chunk carries the same metadata shape regardless of source:

    text            — chunk content, prefixed with hierarchical context
    raw_text        — paragraph text without context prefix
    paragraph_id    — e.g. "3.1.2" (always populated)
    chapter_number  — top-level section number (int or None)
    chapter_title   — top-level section title
    section_title   — nearest heading above
    is_recommendation — whether this is a recommendation paragraph
    recommendation_number — recommendation number if applicable
    page_number     — from nearest <!-- page N --> marker
    source          — source filename

Usage:
    from pipeline.chunk import chunk_markdown
    chunks = chunk_markdown(text, "report.md")
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass


# ── Configuration ──────────────────────────────────────────────────────

# Minimum numbered paragraphs to use the APH-specific structured path
STRUCTURED_THRESHOLD = 10

# Paragraphs longer than this (chars) get split at sentence boundaries
MAX_PARAGRAPH_CHARS = 4000

# Minimum paragraph size — skip tiny fragments
MIN_PARAGRAPH_CHARS = 50

# ── Patterns ───────────────────────────────────────────────────────────

# Existing chapter.paragraph IDs (APH style: 1.1, 2.15, 9.258).
# Requires chapter number 1-9xx (no leading zero) and a real word after —
# avoids false positives like "0.4 M" (molarity) or "1.25 million tonnes".
PARA_ID_RE = re.compile(r"^([1-9]\d{0,2})\.(\d{1,4})\s+[A-Za-z]{2,}")

# Chapter headings: "# Chapter 1 Introduction" or "# 1. Introduction"
CHAPTER_HEADING_RE = re.compile(
    r"^#\s+(?:Chapter\s+)?(\d{1,3})[.:\s—–-]+(.+)", re.IGNORECASE
)

# Markdown section headings (##, ###, ####)
SECTION_HEADING_RE = re.compile(r"^(#{2,4})\s+(.+)")

# Recommendation headings
RECOMMENDATION_RE = re.compile(
    r"^#{1,4}\s+Recommendation\s+(\d+)", re.IGNORECASE
)

# Page markers: "<!-- page N -->" (legacy) or "<!-- page: N -->" (marker renderer)
PAGE_MARKER_RE = re.compile(r"<!--\s*page\s*:?\s*(\d+)\s*-->")

# Numbered sections: "1.0 Title", "3.1 Technical challenges", "4.2.1 Sub-topic"
# Requires at least one dot (e.g. 1.0) to avoid matching "6 February 2025"
NUMBERED_SECTION_RE = re.compile(
    r"^(\d{1,3}\.\d{1,3}(?:\.\d{1,3})*)\s+([A-Z][A-Za-z].*)"
)

# ALLCAPS headings (at least 3 words, all uppercase)
ALLCAPS_HEADING_RE = re.compile(
    r"^([A-Z][A-Z ]{8,})$"
)

# Standalone page numbers (PDF artefact)
STANDALONE_PAGE_RE = re.compile(
    r"^[ivxlcdm]+$|^\d{1,4}$", re.IGNORECASE
)

# Boilerplate patterns to skip
BOILERPLATE_RE = re.compile(
    r"^(©|isbn\s|source\s+pdf|---+$|\|.*page\s+\d+)",
    re.IGNORECASE,
)

# Role detection: headings that indicate document-level overview content
ROLE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("overview", re.compile(
        r"^(Executive\s+Summary|Summary(\s+and\s+Recommendations)?|Overview"
        r"|Key\s+Points)$", re.IGNORECASE)),
    ("recommendation", re.compile(
        r"^Recommendations?$", re.IGNORECASE)),
    ("key_finding", re.compile(
        r"^(Key\s+Findings?|Findings?)$", re.IGNORECASE)),
    ("terms_of_reference", re.compile(
        r"^Terms?\s+of\s+Reference$", re.IGNORECASE)),
    ("conclusion", re.compile(
        r"^(Conclusions?|Summary\s+of\s+[Ff]indings?)$", re.IGNORECASE)),
    ("introduction", re.compile(
        r"^(Introduction|Background)$", re.IGNORECASE)),
]



_MD_EMPHASIS_RE = re.compile(r"\*\*|__|(?<!\w)\*(?!\s)|(?<!\s)\*(?!\w)")


def _clean_heading(text: str) -> str:
    """Strip markdown bold/italic markers from heading text and collapse
    whitespace. Marker's JSON renderer emits headings like "**Purpose**" or
    "4 **Key insights and** **implications**"; in heading context the
    emphasis markers carry no meaning.
    """
    s = _MD_EMPHASIS_RE.sub("", text)
    return re.sub(r"\s+", " ", s).strip()


def _detect_role(heading: str) -> str:
    """Match a heading against known overview/structural role patterns.

    Returns the role string or empty string if no match.
    """
    heading_clean = heading.strip().rstrip(".")
    for role, pattern in ROLE_PATTERNS:
        if pattern.match(heading_clean):
            return role
    return ""


@dataclass
class Chunk:
    text: str
    raw_text: str
    paragraph_id: str | None
    chapter_number: int | None
    chapter_title: str
    section_title: str
    is_recommendation: bool
    recommendation_number: int | None
    page_number: str
    source: str
    role: str = ""  # overview, recommendation, key_finding, etc.

    def to_dict(self) -> dict:
        return asdict(self)


# ── Heading detection ──────────────────────────────────────────────────

def _detect_heading_style(text: str) -> str:
    """Detect the predominant heading style in a document.

    Returns: 'numbered_para', 'markdown', 'numbered_section', 'allcaps',
             or 'minimal'.
    """
    lines = text.split("\n")

    # Count each pattern
    md_headings = 0
    numbered_ids = 0       # lines starting with X.Y
    numbered_sections = 0  # X.Y followed by title-case text (heading)
    allcaps_headings = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if PARA_ID_RE.match(stripped):
            numbered_ids += 1
        if re.match(r"^#{1,4}\s+\S", stripped):
            md_headings += 1
        if NUMBERED_SECTION_RE.match(stripped):
            numbered_sections += 1
        if ALLCAPS_HEADING_RE.match(stripped) and len(stripped.split()) >= 2:
            allcaps_headings += 1

    # Distinguish numbered paragraphs from numbered sections:
    # If most X.Y lines are short heading-like lines (matched by
    # NUMBERED_SECTION_RE), they're section headings, not paragraphs.
    # True numbered paragraphs are body text (long, many more than sections).
    numbered_paras = numbered_ids - numbered_sections

    # APH-style numbered paragraphs take priority if abundant
    if numbered_paras >= STRUCTURED_THRESHOLD:
        return "numbered_para"

    # Markdown headings
    if md_headings >= 3:
        return "markdown"

    # Numbered sections (ARENA style: 1.0, 3.1)
    if numbered_sections >= 3:
        return "numbered_section"

    # ALLCAPS headings
    if allcaps_headings >= 3:
        return "allcaps"

    return "minimal"


# ── Shared utilities ───────────────────────────────────────────────────

def _build_context_prefix(
    chapter_number: int | None,
    chapter_title: str,
    section_title: str,
    paragraph_id: str | None,
) -> str:
    """Build hierarchical context prefix for embedding.

    e.g. "Chapter 1: Introduction > Other reviews | 1.24"
    """
    parts = []
    if chapter_number is not None and chapter_title:
        parts.append(f"Chapter {chapter_number}: {chapter_title}")
    elif chapter_title:
        parts.append(chapter_title)
    if section_title:
        parts.append(section_title)

    prefix = " > ".join(parts)
    if paragraph_id:
        if prefix:
            prefix += f" | {paragraph_id}"
        else:
            prefix = paragraph_id
    if prefix:
        return prefix + " "
    return ""


def _split_long_paragraph(text: str, max_chars: int = MAX_PARAGRAPH_CHARS
                          ) -> list[str]:
    """Split a very long paragraph at sentence boundaries."""
    if len(text) <= max_chars:
        return [text]

    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    if len(sentences) <= 1:
        return [text]

    fragments = []
    current = []
    current_len = 0

    for sentence in sentences:
        if current_len + len(sentence) > max_chars and current:
            fragments.append(" ".join(current))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len += len(sentence) + 1

    if current:
        fragments.append(" ".join(current))

    return fragments


def _is_skip_line(stripped: str) -> bool:
    """Check whether a line should be skipped entirely."""
    if not stripped:
        return True
    if STANDALONE_PAGE_RE.fullmatch(stripped):
        return True
    if BOILERPLATE_RE.match(stripped):
        return True
    return False


def _split_into_paragraphs(lines: list[str]) -> list[str]:
    """Split a list of content lines into paragraphs at blank-line boundaries.

    Returns list of paragraph texts (joined lines), skipping empty ones.
    """
    paragraphs = []
    current = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                text = "\n".join(current).strip()
                if len(text) >= MIN_PARAGRAPH_CHARS:
                    paragraphs.append(text)
                current = []
        elif _is_skip_line(stripped):
            continue
        else:
            current.append(stripped)

    if current:
        text = "\n".join(current).strip()
        if len(text) >= MIN_PARAGRAPH_CHARS:
            paragraphs.append(text)

    return paragraphs


# ── APH structured chunker (existing numbered paragraphs) ─────────────

def _chunk_structured(lines: list[str], source: str) -> list[Chunk]:
    """Chunk a structured report using numbered paragraphs as atomic units.

    For APH committee reports where paragraphs are numbered 1.1, 2.15, etc.
    """
    chunks: list[Chunk] = []

    chapter_number: int | None = None
    chapter_title: str = ""
    section_title: str = ""
    page_number: str = ""
    in_recommendation: bool = False
    recommendation_number: int | None = None
    in_front_matter: bool = True

    current_role: str = ""  # role for current section

    current_para_id: str | None = None
    current_para_lines: list[str] = []
    current_para_page: str = ""
    current_para_chapter: int | None = None
    current_para_chapter_title: str = ""
    current_para_section: str = ""
    current_para_is_rec: bool = False
    current_para_rec_num: int | None = None
    current_para_role: str = ""

    def _flush_paragraph():
        if not current_para_lines:
            return
        raw = "\n".join(current_para_lines).strip()
        if not raw or len(raw) < MIN_PARAGRAPH_CHARS:
            return
        fragments = _split_long_paragraph(raw)
        for frag in fragments:
            prefix = _build_context_prefix(
                current_para_chapter, current_para_chapter_title,
                current_para_section, current_para_id,
            )
            chunks.append(Chunk(
                text=prefix + frag,
                raw_text=frag,
                paragraph_id=current_para_id,
                chapter_number=current_para_chapter,
                chapter_title=current_para_chapter_title,
                section_title=current_para_section,
                is_recommendation=current_para_is_rec,
                recommendation_number=current_para_rec_num,
                page_number=current_para_page,
                source=source,
                role=current_para_role,
            ))

    for line in lines:
        stripped = line.strip()

        pm = PAGE_MARKER_RE.match(stripped)
        if pm:
            page_number = pm.group(1)
            continue

        if not stripped:
            continue

        if STANDALONE_PAGE_RE.fullmatch(stripped):
            continue

        ch = CHAPTER_HEADING_RE.match(stripped)
        if ch:
            _flush_paragraph()
            current_para_lines = []
            current_para_id = None
            chapter_number = int(ch.group(1))
            chapter_title = _clean_heading(ch.group(2).rstrip("—–-"))
            section_title = ""
            current_role = _detect_role(chapter_title)
            in_front_matter = False
            in_recommendation = False
            recommendation_number = None
            continue

        rec = RECOMMENDATION_RE.match(stripped)
        if rec:
            _flush_paragraph()
            current_para_lines = []
            current_para_id = None
            in_recommendation = True
            recommendation_number = int(rec.group(1))
            current_role = "recommendation"
            continue

        sh = SECTION_HEADING_RE.match(stripped)
        if sh:
            heading_text = _clean_heading(sh.group(2))
            if in_recommendation and not in_front_matter:
                inner_para = PARA_ID_RE.match(heading_text)
                if inner_para:
                    _flush_paragraph()
                    current_para_id = f"{inner_para.group(1)}.{inner_para.group(2)}"
                    current_para_lines = [heading_text]
                    current_para_page = page_number
                    current_para_chapter = chapter_number
                    current_para_chapter_title = chapter_title
                    current_para_section = section_title
                    current_para_is_rec = True
                    current_para_rec_num = recommendation_number
                    current_para_role = "recommendation"
                    in_recommendation = False
                    continue
            _flush_paragraph()
            current_para_lines = []
            current_para_id = None
            if not RECOMMENDATION_RE.match(stripped):
                section_title = heading_text
                current_role = _detect_role(heading_text) or current_role
                in_recommendation = False
                recommendation_number = None
            continue

        if stripped.startswith("# "):
            _flush_paragraph()
            current_para_lines = []
            current_para_id = None
            if in_front_matter:
                section_title = _clean_heading(stripped[2:])
            continue

        para_match = PARA_ID_RE.match(stripped)
        if para_match:
            # A numbered paragraph is body content; exit front matter even
            # when the doc lacks a "# 1. Chapter" anchor (e.g. ARENA reports).
            in_front_matter = False
            _flush_paragraph()
            current_para_id = f"{para_match.group(1)}.{para_match.group(2)}"
            current_para_lines = [stripped]
            current_para_page = page_number
            current_para_chapter = chapter_number
            current_para_chapter_title = chapter_title
            current_para_section = section_title
            current_para_is_rec = in_recommendation
            current_para_rec_num = recommendation_number if in_recommendation else None
            current_para_role = "recommendation" if in_recommendation else current_role
            if in_recommendation:
                in_recommendation = False
            continue

        if in_front_matter:
            continue

        if current_para_id is not None:
            current_para_lines.append(stripped)

    _flush_paragraph()
    return chunks


# ── Universal paragraph-level chunker ──────────────────────────────────

def _chunk_universal(lines: list[str], source: str, style: str) -> list[Chunk]:
    """Universal chunker that assigns synthetic paragraph IDs.

    Handles markdown headings, numbered sections, ALLCAPS headings,
    and structureless documents.
    """
    chunks: list[Chunk] = []

    # State
    page_number: str = ""
    chapter_number: int | None = None
    chapter_title: str = ""
    section_title: str = ""
    section_id: str = ""         # current section's number string
    para_seq: int = 0            # paragraph counter within current section
    top_level_seq: int = 0       # top-level section counter
    sub_level_seq: int = 0       # sub-section counter

    # Accumulate content lines between headings
    content_lines: list[str] = []
    section_page: str = ""       # page at start of current section
    current_role: str = ""       # role for current section

    # Front matter detection: skip content before first heading
    seen_heading = False

    def _flush_section():
        """Emit paragraphs from accumulated content lines."""
        nonlocal para_seq
        if not content_lines:
            return

        paragraphs = _split_into_paragraphs(content_lines)
        for para_text in paragraphs:
            para_seq += 1
            pid = f"{section_id}.{para_seq}" if section_id else str(para_seq)

            for frag in _split_long_paragraph(para_text):
                prefix = _build_context_prefix(
                    chapter_number, chapter_title, section_title, pid,
                )
                chunks.append(Chunk(
                    text=prefix + frag,
                    raw_text=frag,
                    paragraph_id=pid,
                    chapter_number=chapter_number,
                    chapter_title=chapter_title,
                    section_title=section_title,
                    is_recommendation=False,
                    recommendation_number=None,
                    page_number=section_page or page_number,
                    source=source,
                    role=current_role,
                ))

    def _set_section(depth: int, number: str, title: str):
        """Update section state for a new heading."""
        nonlocal chapter_number, chapter_title, section_title
        nonlocal section_id, para_seq, top_level_seq, sub_level_seq
        nonlocal seen_heading, section_page, current_role

        title = _clean_heading(title)

        _flush_section()
        content_lines.clear()
        para_seq = 0
        seen_heading = True
        section_page = page_number
        current_role = _detect_role(title)

        if number:
            # Heading has its own number (e.g. "3.1 Technical challenges")
            section_id = number
            parts = number.split(".")
            if depth == 1 or len(parts) == 1:
                try:
                    chapter_number = int(parts[0])
                except ValueError:
                    chapter_number = None
                chapter_title = title
                section_title = ""
                sub_level_seq = 0
            else:
                section_title = title
        else:
            # Assign sequential numbers
            if depth == 1:
                top_level_seq += 1
                sub_level_seq = 0
                section_id = str(top_level_seq)
                chapter_number = top_level_seq
                chapter_title = title
                section_title = ""
            else:
                # If a sub-heading appears before any top-level one, open
                # an implicit chapter 1 so ids don't start with "0.".
                if top_level_seq == 0:
                    top_level_seq = 1
                    chapter_number = 1
                    chapter_title = ""
                sub_level_seq += 1
                section_id = f"{top_level_seq}.{sub_level_seq}"
                section_title = title

    for line in lines:
        stripped = line.strip()

        # Page markers
        pm = PAGE_MARKER_RE.match(stripped)
        if pm:
            page_number = pm.group(1)
            # For minimal-structure docs, pages act as section boundaries
            if style == "minimal" and seen_heading:
                _set_section(1, "", f"Page {page_number}")
            continue

        if not stripped:
            # Preserve blank lines for paragraph splitting
            if seen_heading:
                content_lines.append("")
            continue

        if _is_skip_line(stripped):
            continue

        # --- Detect headings based on document style ---

        heading_found = False

        if style == "markdown":
            # Markdown headings: #, ##, ###, ####
            md = re.match(r"^(#{1,4})\s+(.+)", stripped)
            if md:
                depth = len(md.group(1))
                # Clean emphasis first — marker emits "4.4**Key insights**"
                # where the ** is both the delimiter and decoration.
                title = _clean_heading(md.group(2))
                num_match = re.match(
                    r"(?:Chapter\s+)?(\d{1,3}(?:\.\d{1,3})*)[.:\s—–-]+(.+)",
                    title, re.IGNORECASE,
                )
                if num_match:
                    _set_section(depth, num_match.group(1), num_match.group(2).strip())
                else:
                    _set_section(depth, "", title)
                heading_found = True

        elif style == "numbered_section":
            # Numbered sections: "1.0 Title", "3.1 Technical challenges"
            ns = NUMBERED_SECTION_RE.match(stripped)
            if ns:
                number = ns.group(1)
                title = ns.group(2).strip()
                depth = len(number.split("."))
                _set_section(depth, number, title)
                heading_found = True
            # Also check for markdown headings (some docs mix styles)
            if not heading_found:
                md = re.match(r"^(#{1,4})\s+(.+)", stripped)
                if md:
                    depth = len(md.group(1))
                    _set_section(depth, "", md.group(2).strip())
                    heading_found = True

        elif style == "allcaps":
            # ALLCAPS headings
            ac = ALLCAPS_HEADING_RE.match(stripped)
            if ac and len(stripped.split()) >= 2:
                title = stripped.title()  # Convert to title case for readability
                _set_section(1, "", title)
                heading_found = True
            # Also check markdown/numbered
            if not heading_found:
                md = re.match(r"^(#{1,4})\s+(.+)", stripped)
                if md:
                    _set_section(len(md.group(1)), "", md.group(2).strip())
                    heading_found = True
            if not heading_found:
                ns = NUMBERED_SECTION_RE.match(stripped)
                if ns:
                    number = ns.group(1)
                    _set_section(len(number.split(".")), number, ns.group(2).strip())
                    heading_found = True

        elif style == "minimal":
            # Minimal structure — check for any heading pattern
            md = re.match(r"^(#{1,4})\s+(.+)", stripped)
            if md:
                _set_section(len(md.group(1)), "", md.group(2).strip())
                heading_found = True
            if not heading_found:
                ns = NUMBERED_SECTION_RE.match(stripped)
                if ns:
                    number = ns.group(1)
                    _set_section(len(number.split(".")), number, ns.group(2).strip())
                    heading_found = True
            if not heading_found:
                ac = ALLCAPS_HEADING_RE.match(stripped)
                if ac and len(stripped.split()) >= 2:
                    _set_section(1, "", stripped.title())
                    heading_found = True

            # If no heading found yet for minimal docs, create an initial section
            if not heading_found and not seen_heading:
                _set_section(1, "", f"Page {page_number}" if page_number else "Content")

        # If we haven't seen a heading yet and this isn't one, skip (front matter)
        if not seen_heading and not heading_found:
            continue

        # Accumulate content lines
        if not heading_found:
            content_lines.append(stripped)

    # Flush final section
    _flush_section()

    return chunks


# ── Public API ─────────────────────────────────────────────────────────

def is_structured(text: str) -> bool:
    """Check whether a document has enough numbered paragraphs for APH-style chunking."""
    count = 0
    for line in text.split("\n"):
        if PARA_ID_RE.match(line.strip()):
            count += 1
            if count >= STRUCTURED_THRESHOLD:
                return True
    return False


def chunk_markdown(text: str, source: str) -> list[dict]:
    """Chunk a markdown document into paragraph-level pieces with metadata.

    Auto-detects document structure and selects the appropriate strategy:
      - 'numbered_para': APH-style with embedded paragraph IDs (1.1, 2.15)
      - 'markdown': markdown headings (#, ##) with synthetic paragraph IDs
      - 'numbered_section': numbered sections (1.0, 3.1) with synthetic IDs
      - 'allcaps': ALL CAPS headings with synthetic IDs
      - 'minimal': page-break boundaries with sequential IDs

    Returns list of dicts with consistent keys across all strategies.
    """
    lines = text.split("\n")
    style = _detect_heading_style(text)

    if style == "numbered_para":
        chunks = _chunk_structured(lines, source)
    else:
        chunks = _chunk_universal(lines, source, style)

    return [c.to_dict() for c in chunks]


def chunk_file(filepath: str) -> list[dict]:
    """Convenience: read a file and chunk it."""
    from pathlib import Path
    p = Path(filepath)
    text = p.read_text(encoding="utf-8", errors="replace")
    return chunk_markdown(text, p.name)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Chunk markdown documents")
    parser.add_argument("files", nargs="+", help="Markdown files to chunk")
    parser.add_argument("--stats", action="store_true",
                        help="Print stats only, not full chunks")
    parser.add_argument("--json", action="store_true",
                        help="Output chunks as JSON")
    parser.add_argument("--sample", type=int, default=0,
                        help="Show N sample chunks")
    args = parser.parse_args()

    for filepath in args.files:
        chunks = chunk_file(filepath)
        text = open(filepath).read()
        style = _detect_heading_style(text)

        if args.stats:
            print(f"\n{filepath}:")
            print(f"  Style: {style}")
            print(f"  Chunks: {len(chunks)}")
            if chunks:
                lengths = [len(c["raw_text"]) for c in chunks]
                print(f"  Char range: {min(lengths)}–{max(lengths)}")
                print(f"  Median: {sorted(lengths)[len(lengths)//2]}")
                paras = [c for c in chunks if c["paragraph_id"]]
                if paras:
                    print(f"  With paragraph_id: {len(paras)}/{len(chunks)}")
                # Unique section titles
                sections = sorted(set(
                    c["section_title"] for c in chunks if c["section_title"]))
                print(f"  Sections: {len(sections)}")
                if sections:
                    for s in sections[:10]:
                        print(f"    - {s[:70]}")
                    if len(sections) > 10:
                        print(f"    ... and {len(sections)-10} more")
                recs = [c for c in chunks if c["is_recommendation"]]
                if recs:
                    print(f"  Recommendations: {len(recs)}")

        elif args.json:
            print(json.dumps(chunks, indent=2))

        else:
            show = chunks[:args.sample] if args.sample else chunks
            for i, c in enumerate(show):
                print(f"\n{'='*70}")
                pid = c["paragraph_id"] or "—"
                ch = c["chapter_number"] or "—"
                rec = (f" [REC {c['recommendation_number']}]"
                       if c["is_recommendation"] else "")
                print(f"[{i+1}] §{pid}  Ch{ch}  p.{c['page_number']}{rec}")
                print(f"  Section: {c['section_title']}")
                print(f"  {c['raw_text'][:200]}...")
