#!/usr/bin/env python3
"""
Deterministic structural parser for ANAO-style audit reports.

Extracts atomic records from the Summary section of each markdown document:
  - Summary supporting findings (numbered paragraphs = atomic records)
  - Recommendations with entity responses
  - Report metadata, audit objective, overall conclusion

This is a pre-LLM step: everything extracted here is deterministic and auditable.
No API calls are made. The output feeds into downstream LLM passes for taxonomy
derivation and classification.

Usage:
    python -m pipeline.parse --domain anao
    python -m pipeline.parse --domain anao --limit 50
    python -m pipeline.parse --domain anao --file some-report.md
    python -m pipeline.parse --domain anao --stats
    python -m pipeline.parse --domain anao --force
"""

import argparse
import json
import re
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

from pipeline.config import DomainConfig

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]


def corpus_dirs(domain: str):
    md_dir = REPO_ROOT / "corpora" / domain / "markdown"
    parsed_dir = REPO_ROOT / "corpora" / domain / "parsed"
    return md_dir, parsed_dir


# ---------------------------------------------------------------------------
# Regex patterns (adapted from ~/ANAO/scripts/03_parse_structure.py)
# ---------------------------------------------------------------------------

RE_PAGE = re.compile(r"<!-- page (\d+) -->")

RE_REPORT_NUM = re.compile(
    r"(?:Audit(?:or-General)?|ANAO)\s+Report\s+No\.?\s*(\d+)\s+(\d{4})[–\-](\d{2,4})",
    re.IGNORECASE,
)

RE_H1 = re.compile(r"^# (.+)$", re.MULTILINE)

RE_ENTITY_HEADING = re.compile(r"^(##|###) (.+)$", re.MULTILINE)

RE_DATE_CANBERRA = re.compile(
    r"Canberra\s+ACT\s*[\n\s]+(\d{1,2}\s+\w+\s+\d{4})", re.IGNORECASE
)
RE_DATE_TABLED = re.compile(
    r"Tabled\s+(\d{1,2}\s+\w+\s+\d{4})", re.IGNORECASE
)

RE_SUMMARY = re.compile(
    r"^# Summary(?:\s+and\s+[Rr]ecommendations)?\s*$", re.MULTILINE
)

RE_CONCLUSION = re.compile(
    r"^(#{1,4})\s+(?:Overall\s+)?(?:Audit\s+)?(?:Findings?\s+and\s+)?[Cc]onclusion[s]?\s*$",
    re.MULTILINE,
)

RE_SUPPORTING_FINDINGS = re.compile(
    r"^(#{2,4})\s+[Ss]upporting\s+[Ff]indings?\s*$", re.MULTILINE
)

RE_RECOMMENDATIONS_HEADING = re.compile(
    r"^(#{2,4})\s+[Rr]ecommendations?\s*$", re.MULTILINE
)

RE_AUDIT_OBJECTIVE = re.compile(
    r"^(#{2,4})\s+(?:Audit\s+(?:scope\s+and\s+)?)?[Oo]bjective"
    r"(?:\s+and\s+(?:criteria|scope|approach|methodology))?\s*$",
    re.MULTILINE,
)

RE_BACKGROUND = re.compile(
    r"^(#{2,4})\s+[Bb]ackground\s*$", re.MULTILINE
)

# Paragraph numbering patterns
RE_PARA_HEADING = re.compile(r"^####\s+(\d{1,3})\.\s*$", re.MULTILINE)
RE_PARA_INLINE = re.compile(r"^(\d{1,3})\.\s+(\S.+)", re.MULTILINE)
# Summary-level paragraphs: "N. Text..." where N is a simple integer (not chapter.para)
RE_SUMMARY_PARA = re.compile(r"^(\d{1,3})\.\s+(\S.+)", re.MULTILINE)

# Subsection headings within summary (e.g. "#### Oversight arrangements")
RE_SUMMARY_SUBSECTION = re.compile(r"^(#{2,4})\s+(.+)$", re.MULTILINE)

# Recommendation pattern
RE_REC_ANY = re.compile(
    r"(?:^#{2,4}\s+)?Recommendation\s+(?:No\.?\s*|no\.?\s*)(\d+)"
    r"(?:\s+Para\.?\s*(\d+\.\d+))?",
    re.IGNORECASE | re.MULTILINE,
)

# Entity response heading
RE_ENTITY_RESPONSE = re.compile(
    r"^#{2,4}\s+(.+?)(?:[''']s)?\s+response:?\s*(.*)$",
    re.IGNORECASE | re.MULTILINE,
)

# Response values
RE_RESPONSE_VALUE = re.compile(
    r"^(Agreed|Partially\s+agreed|Not\s+agreed|Agreed\s+with\s+(?:qualification|comment)"
    r"|Noted|Disagree[ds]?|Agrees|Not\s+Agreed)\b",
    re.IGNORECASE | re.MULTILINE,
)

# Page footer noise
RE_FOOTER = re.compile(
    r"^(?:Auditor-General|ANAO Audit)\s+Report\s+No\.?\s*\d+\s+\d{4}[–\-]\d{2,4}\s+.+?\s*\d+\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# Conclusion rating extraction
RE_CONCLUSION_RATING = re.compile(
    r"has\s+been\s+((?:partly|largely|not)\s+)?effective",
    re.IGNORECASE,
)
RE_CONCLUSION_INEFFECTIVE = re.compile(
    r"has\s+(?:been\s+)?ineffective",
    re.IGNORECASE,
)

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_date(date_str: str) -> str | None:
    if not date_str:
        return None
    date_str = date_str.strip()
    m = re.match(r"(?:\d{1,2}\s+)?(\w+)\s+(\d{4})", date_str)
    if m:
        month_name = m.group(1).lower()
        year = m.group(2)
        if month_name in MONTHS:
            return f"{year}-{MONTHS[month_name]:02d}"
    return None


def build_page_map(text: str) -> list[tuple[int, int]]:
    return [(int(m.group(1)), m.start()) for m in RE_PAGE.finditer(text)]


def page_at_offset(page_map: list[tuple[int, int]], offset: int) -> int | None:
    current_page = None
    for page_num, page_offset in page_map:
        if page_offset > offset:
            break
        current_page = page_num
    return current_page


def clean_text(text: str) -> str:
    """Remove page markers, footers, and excessive whitespace."""
    text = RE_PAGE.sub("", text)
    text = RE_FOOTER.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

def extract_metadata(text: str, page_map: list) -> dict:
    result = {
        "report_title": None,
        "report_number": None,
        "report_year": None,
        "report_date": None,
        "audited_entities": [],
    }

    first_pages = text[:page_map[5][1]] if len(page_map) >= 6 else text[:10000]

    # Report number
    m = RE_REPORT_NUM.search(first_pages)
    if not m:
        m = RE_REPORT_NUM.search(text[:30000])
    if m:
        result["report_number"] = m.group(1)
        result["report_year"] = f"{m.group(2)}-{m.group(3)}"

    # Report title
    titles = RE_H1.findall(text[:5000])
    for title in titles:
        title = title.strip()
        if title and title not in ("", "Contents", "Abbreviations", "Glossary"):
            result["report_title"] = title
            break

    # Audited entities from page 1
    page1_end = page_map[1][1] if len(page_map) > 1 else min(len(text), 3000)
    page1_text = text[:page1_end]
    if result["report_title"]:
        title_pos = page1_text.find(result["report_title"])
        if title_pos >= 0:
            after_title = page1_text[title_pos + len(result["report_title"]):]
            skip = {"performance audit", "abbreviations", "summary", "contents",
                    "glossary", "audit report", "key findings"}
            for m in RE_ENTITY_HEADING.finditer(after_title):
                entity = m.group(2).strip()
                if entity.lower() not in skip and len(entity) > 2:
                    if any(kw in entity.lower() for kw in [
                        "audit report", "contents", "abbreviations",
                        "summary", "background", "introduction",
                    ]):
                        break
                    result["audited_entities"].append(entity)

    # Date
    m = RE_DATE_CANBERRA.search(first_pages)
    if m:
        result["report_date"] = parse_date(m.group(1))
    if not result["report_date"]:
        m = RE_DATE_TABLED.search(first_pages)
        if m:
            result["report_date"] = parse_date(m.group(1))

    return result


# ---------------------------------------------------------------------------
# Summary section extraction
# ---------------------------------------------------------------------------

def extract_summary_section(text: str) -> str | None:
    """Return the full text of the Summary section, or None if not found."""
    m = RE_SUMMARY.search(text)
    if not m:
        return None
    start = m.start()
    # Find next top-level heading after summary
    next_h1 = re.search(r"^# (?!Summary)", text[start + 1:], re.MULTILINE)
    end = start + 1 + next_h1.start() if next_h1 else len(text)
    return text[start:end]


def extract_conclusion_text(summary: str) -> str | None:
    """Extract the conclusion subsection from the summary."""
    m = RE_CONCLUSION.search(summary)
    if not m:
        return None
    start = m.end()
    level = m.group(1).count("#")
    # Find next heading of same or higher level
    pattern = re.compile(r"^#{1," + str(level) + r"}\s", re.MULTILINE)
    next_h = pattern.search(summary, start)
    end = next_h.start() if next_h else len(summary)
    return clean_text(summary[start:end])


def extract_conclusion_rating(conclusion_text: str | None) -> str | None:
    """Extract the overall rating from the conclusion text."""
    if not conclusion_text:
        return None
    m = RE_CONCLUSION_INEFFECTIVE.search(conclusion_text)
    if m:
        return "ineffective"
    m = RE_CONCLUSION_RATING.search(conclusion_text)
    if m:
        qualifier = (m.group(1) or "").strip().lower()
        if qualifier == "partly":
            return "partly effective"
        elif qualifier == "largely":
            return "largely effective"
        elif qualifier == "not":
            return "not effective"
        else:
            return "effective"
    return None


def extract_audit_objective(text: str) -> str | None:
    """Extract the audit objective section."""
    m = RE_AUDIT_OBJECTIVE.search(text)
    if not m:
        return None
    start = m.end()
    level = m.group(1).count("#")
    pattern = re.compile(r"^#{1," + str(level) + r"}\s", re.MULTILINE)
    next_h = pattern.search(text, start)
    end = next_h.start() if next_h else len(text)
    return clean_text(text[start:end])


def extract_summary_findings(summary: str, page_map: list, summary_offset: int) -> list[dict]:
    """Extract numbered finding paragraphs from the summary section.

    These are the atomic records: discrete observations between
    Conclusion and Recommendations subsections.

    Returns list of {paragraph_number, subsection, text, page}.
    """
    if not summary:
        return []

    # Identify the findings zone within the summary.
    # Strategy: find the zone after Background/Conclusion/Objective and before Recommendations.
    # The findings zone contains the numbered paragraphs that are our atomic records.

    # Find key boundary markers
    conclusion_end = None
    # Find ALL conclusion-like headings (there may be multiple) and use the last one
    for m in re.finditer(
        r"^(#{1,4})\s+(?:Overall\s+)?(?:Audit\s+)?(?:Findings?\s+and\s+)?[Cc]onclusion[s]?\s*$",
        summary, re.MULTILINE,
    ):
        level = m.group(1).count("#")
        pattern = re.compile(r"^#{1," + str(level) + r"}\s", re.MULTILINE)
        next_h = pattern.search(summary, m.end())
        if next_h:
            conclusion_end = next_h.start()

    # Also check for "Key findings" heading as a findings zone start marker
    key_findings_start = None
    m = re.search(r"^(#{2,4})\s+[Kk]ey\s+[Ff]indings?\s*$", summary, re.MULTILINE)
    if m:
        key_findings_start = m.start()

    supporting_start = None
    m = RE_SUPPORTING_FINDINGS.search(summary)
    if m:
        supporting_start = m.end()

    recs_start = None
    m = RE_RECOMMENDATIONS_HEADING.search(summary)
    if m:
        recs_start = m.start()

    # Also check for "Summary of entity response" as an end marker
    entity_response_start = None
    m = re.search(
        r"^(#{2,4})\s+[Ss]ummary\s+of\s+(?:entity|agency)\s+responses?\s*$",
        summary, re.MULTILINE,
    )
    if m:
        entity_response_start = m.start()

    # Determine the findings zone
    if supporting_start is not None:
        zone_start = supporting_start
    elif key_findings_start is not None:
        zone_start = key_findings_start
    elif conclusion_end is not None:
        zone_start = conclusion_end
    else:
        # Fallback: start from the beginning of the summary (after the heading)
        first_newline = summary.find("\n")
        zone_start = first_newline + 1 if first_newline >= 0 else 0

    # End zone at the earliest of: recommendations, entity response summary, end of summary
    zone_end = len(summary)
    if recs_start is not None:
        zone_end = min(zone_end, recs_start)
    if entity_response_start is not None:
        zone_end = min(zone_end, entity_response_start)

    # Don't let the zone start past the end
    if zone_start >= zone_end:
        zone_start = 0

    findings_zone = summary[zone_start:zone_end]

    # Extract numbered paragraphs from the zone
    findings = []
    current_subsection = None

    # Track subsection headings within the findings zone
    # Build a list of (offset, type, content) events
    events = []

    # Subsection headings
    for m in RE_SUMMARY_SUBSECTION.finditer(findings_zone):
        heading = m.group(2).strip()
        # Skip known non-finding headings
        skip = {"background", "background and context", "background to the audit",
                "introduction",
                "conclusion", "conclusions", "overall conclusion", "overall conclusions",
                "overall audit conclusion", "overall audit conclusions",
                "audit conclusion", "audit conclusions",
                "audit objective", "audit objectives",
                "audit objective and criteria", "audit objective and scope",
                "audit objectives and scope", "audit objectives and criteria",
                "audit scope and objective", "audit scope and objectives",
                "audit objective, scope and criteria",
                "audit objective and methodology", "audit scope and focus",
                "audit approach", "audit criteria", "audit scope", "audit methodology",
                "audit objective and approach", "the audit approach", "the audit",
                "rationale for undertaking the audit", "rationale for the audit",
                "legislative framework",
                "recommendations", "recommendation",
                "summary of entity response", "summary of entity responses",
                "summary of agency response", "summary of agency responses",
                "key messages from this audit for all australian government entities",
                "key messages for all australian government entities"}
        if heading.lower().strip() in skip:
            continue
        # Skip entity response headings
        if RE_ENTITY_RESPONSE.match(m.group(0)):
            continue
        # Skip paragraph-number headings (e.g. "#### 19." or "#### 3.14")
        if re.match(r"^\d{1,3}\.?\s*$", heading):
            continue
        if re.match(r"^\d{1,2}\.\d{1,3}\s*$", heading):
            continue
        events.append((m.start(), "subsection", heading, m.end()))

    # Numbered paragraphs — heading format: "#### N."
    for m in RE_PARA_HEADING.finditer(findings_zone):
        para_num = int(m.group(1))
        # Get text until next heading or next paragraph marker
        text_start = m.end()
        # Find next paragraph heading or section heading
        next_marker = re.search(
            r"^(?:####\s+\d{1,3}\.\s*$|#{2,4}\s+)",
            findings_zone[text_start:],
            re.MULTILINE,
        )
        text_end = text_start + next_marker.start() if next_marker else len(findings_zone)
        para_text = clean_text(findings_zone[text_start:text_end])
        if para_text:
            abs_offset = summary_offset + zone_start + m.start()
            events.append((m.start(), "para", {
                "paragraph_number": para_num,
                "text": para_text,
                "page": page_at_offset(page_map, abs_offset),
            }, m.end()))

    # Numbered paragraphs — inline format: "N. Text..."
    # Only use if no heading-format paragraphs were found
    heading_paras = [e for e in events if e[1] == "para"]
    if not heading_paras:
        for m in RE_SUMMARY_PARA.finditer(findings_zone):
            para_num = int(m.group(1))
            # Skip very high numbers (likely not paragraph numbers)
            if para_num > 200:
                continue
            # Get text: from the match to the next numbered paragraph or heading
            text_start = m.start()
            next_marker = re.search(
                r"^(?:\d{1,3}\.\s+\S|#{2,4}\s+)",
                findings_zone[m.end():],
                re.MULTILINE,
            )
            text_end = m.end() + next_marker.start() if next_marker else len(findings_zone)
            para_text = clean_text(findings_zone[text_start:text_end])
            if para_text:
                abs_offset = summary_offset + zone_start + m.start()
                events.append((m.start(), "para", {
                    "paragraph_number": para_num,
                    "text": para_text,
                    "page": page_at_offset(page_map, abs_offset),
                }, m.end()))

    # Sort events by offset and assign subsections to paragraphs
    events.sort(key=lambda e: e[0])

    current_subsection = None
    for offset, etype, content, end_offset in events:
        if etype == "subsection":
            current_subsection = content
        elif etype == "para":
            content["subsection"] = current_subsection
            findings.append(content)

    return findings


# ---------------------------------------------------------------------------
# Recommendation extraction
# ---------------------------------------------------------------------------

def extract_recommendations(text: str, page_map: list) -> list[dict]:
    """Extract all recommendations with entity responses."""
    raw_recs = []

    for m in RE_REC_ANY.finditer(text):
        rec_num = int(m.group(1))
        para_ref = m.group(2)

        if not para_ref:
            next_lines = text[m.end():m.end() + 200]
            para_m = re.search(r"^\s*Para(?:graph)?\.?\s*(\d+\.\d+)",
                               next_lines, re.IGNORECASE)
            if para_m:
                para_ref = para_m.group(1)

        rec_text = _extract_rec_text(text, m)
        responses = _extract_entity_responses(text, m.end())
        page = page_at_offset(page_map, m.start())

        raw_recs.append({
            "number": rec_num,
            "paragraph_ref": para_ref,
            "text": rec_text,
            "entity_responses": responses,
            "page": page,
        })

    # Deduplicate by recommendation number
    best = {}
    for r in raw_recs:
        num = r["number"]
        if num not in best:
            best[num] = r
        else:
            existing = best[num]
            score_new = (
                (1 if r["paragraph_ref"] else 0)
                + len(r["entity_responses"])
                + (1 if len(r["text"]) > len(existing["text"]) else 0)
            )
            score_old = (
                (1 if existing["paragraph_ref"] else 0)
                + len(existing["entity_responses"])
                + 1
            )
            if score_new > score_old:
                if not r["paragraph_ref"] and existing["paragraph_ref"]:
                    r["paragraph_ref"] = existing["paragraph_ref"]
                best[num] = r

    return sorted(best.values(), key=lambda r: r["number"])


def _extract_rec_text(text: str, match: re.Match) -> str:
    """Extract the recommendation text (appears before or after the marker)."""
    # Try text AFTER the marker (older format)
    after_start = match.end()
    remaining = text[after_start:after_start + 3000]
    remaining = re.sub(
        r"^\s*(?:Para(?:graph)?\.?\s*\d+\.\d+\s*\n)?"
        r"(?:####\s+\d+\.\d+\s*\n)?",
        "", remaining,
    )

    end_patterns = [
        re.compile(r"^#{2,4}\s+.+?response:?\s*$", re.MULTILINE | re.IGNORECASE),
        re.compile(r"Recommendation\s+(?:no\.?\s*)?\d+", re.IGNORECASE),
        re.compile(r"^#{1,2}\s+\S", re.MULTILINE),
    ]

    end_pos = len(remaining)
    for pat in end_patterns:
        m = pat.search(remaining)
        if m and m.start() < end_pos:
            end_pos = m.start()

    after_text = clean_text(remaining[:end_pos])

    if len(after_text) > 10:
        return after_text

    # Try text BEFORE the marker (modern format)
    before_end = match.start()
    before_start = max(0, before_end - 2000)
    before_text = text[before_start:before_end]

    start_patterns = [
        re.compile(r"^#{2,4}\s+.+?response:?\s*$", re.MULTILINE | re.IGNORECASE),
        re.compile(r"Recommendation\s+(?:no\.?\s*)?\d+", re.IGNORECASE),
        re.compile(r"^#{1,3}\s+\S", re.MULTILINE),
        re.compile(r"(Agreed|Partially\s+agreed|Not\s+agreed|Noted)\s*\.", re.IGNORECASE),
    ]

    latest_boundary = 0
    for pat in start_patterns:
        for m in pat.finditer(before_text):
            boundary = m.end()
            newline = before_text.find("\n", boundary)
            if newline >= 0:
                boundary = newline + 1
            if boundary > latest_boundary:
                latest_boundary = boundary

    before_block = clean_text(before_text[latest_boundary:])
    return before_block


def _extract_entity_responses(text: str, rec_start: int) -> list[dict]:
    """Extract entity responses following a recommendation."""
    responses = []

    search_text = text[rec_start:rec_start + 5000]
    next_rec = re.search(
        r"Recommendation\s+(?:no\.?\s*)?\d+", search_text[100:], re.IGNORECASE
    )
    boundary = (next_rec.start() + 100) if next_rec else len(search_text)
    section = search_text[:boundary]

    for m in RE_ENTITY_RESPONSE.finditer(section):
        entity_name = m.group(1).strip()
        inline_value = (m.group(2) or "").strip()

        entity_name = re.sub(r"[''']s$", "", entity_name)
        entity_name = re.sub(r"^####?\s*", "", entity_name)

        after_heading = section[m.end():m.end() + 500]
        combined = (inline_value + "\n" + after_heading) if inline_value else after_heading

        resp_m = RE_RESPONSE_VALUE.search(combined)
        if resp_m:
            response_val = resp_m.group(1).strip().rstrip(".")
            response_val = response_val.replace("Agrees", "Agreed")
            response_val = response_val.replace("Disagreed", "Not agreed")
            response_val = response_val.replace("Disagree", "Not agreed")

            detail_text = combined[resp_m.end():].strip()
            detail_end_m = RE_ENTITY_RESPONSE.search(detail_text)
            if detail_end_m:
                detail_text = detail_text[:detail_end_m.start()]
            detail_text = clean_text(detail_text)
            if len(detail_text) < 5:
                detail_text = None

            responses.append({
                "entity": entity_name,
                "response": response_val,
                "detail": detail_text,
            })

    return responses


# ---------------------------------------------------------------------------
# Cross-referencing: link findings to recommendations
# ---------------------------------------------------------------------------

def _parse_para_ref(ref: str) -> tuple[int, int] | None:
    """Parse '2.10' into (2, 10) for range comparison."""
    parts = ref.split(".")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return (int(parts[0]), int(parts[1]))
    return None


def link_findings_to_recommendations(findings: list[dict],
                                      recommendations: list[dict]) -> list[dict]:
    """Link summary findings to recommendations via paragraph_ref cross-references.

    Finding text ends with "(See paragraphs X.Y to X.Z)". A recommendation with
    paragraph_ref "2.10" links to a finding whose range includes 2.10.
    """
    for finding in findings:
        finding["linked_recommendations"] = []
        text = finding.get("text") or ""

        # Extract paragraph ranges: "See paragraphs X.Y to X.Z" or "See paragraph X.Y"
        ranges = re.findall(
            r"[Ss]ee\s+paragraphs?\s+(\d+\.\d+)(?:\s+to\s+(\d+\.\d+))?",
            text,
        )

        if not ranges:
            continue

        for rec in recommendations:
            ref = rec.get("paragraph_ref")
            if not ref:
                continue
            ref_parsed = _parse_para_ref(ref)
            if not ref_parsed:
                continue

            for range_start, range_end in ranges:
                start = _parse_para_ref(range_start)
                if not start:
                    continue
                if range_end:
                    end = _parse_para_ref(range_end)
                    if not end:
                        continue
                    # Check if ref falls within [start, end]
                    if (start[0] == ref_parsed[0] == end[0]
                            and start[1] <= ref_parsed[1] <= end[1]):
                        finding["linked_recommendations"].append(rec["number"])
                        break
                else:
                    # Exact match
                    if ref_parsed == start:
                        finding["linked_recommendations"].append(rec["number"])
                        break

    return findings


# ---------------------------------------------------------------------------
# Main parse function
# ---------------------------------------------------------------------------

def parse_document(md_path: Path) -> dict:
    """Parse a single markdown file and return the structured result."""
    text = md_path.read_text(encoding="utf-8")
    page_map = build_page_map(text)

    metadata = extract_metadata(text, page_map)
    summary = extract_summary_section(text)
    conclusion_text = extract_conclusion_text(summary) if summary else None
    conclusion_rating = extract_conclusion_rating(conclusion_text)
    audit_objective = extract_audit_objective(text)

    # Extract summary findings
    summary_offset = 0
    if summary:
        m = RE_SUMMARY.search(text)
        if m:
            summary_offset = m.start()
    findings = extract_summary_findings(summary, page_map, summary_offset)

    # Extract recommendations (from full text, not just summary)
    recommendations = extract_recommendations(text, page_map)

    # Cross-reference findings to recommendations
    findings = link_findings_to_recommendations(findings, recommendations)

    return {
        "source_file": md_path.name,
        "report_title": metadata["report_title"],
        "report_number": metadata["report_number"],
        "report_year": metadata["report_year"],
        "report_date": metadata["report_date"],
        "audited_entities": metadata["audited_entities"],
        "audit_objective": audit_objective,
        "audit_conclusion": conclusion_text,
        "overall_conclusion_rating": conclusion_rating,
        "summary_findings": findings,
        "recommendations": recommendations,
        "has_summary": summary is not None,
        "total_pages": page_map[-1][0] if page_map else 0,
    }


def parse_and_save(entry: dict) -> dict:
    """Parse a markdown file and save JSON output. For ProcessPoolExecutor."""
    md_path = Path(entry["md_path"])
    out_path = Path(entry["out_path"])

    try:
        result = parse_document(md_path)

        if not entry.get("dry_run", False):
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

        return {
            "slug": md_path.stem,
            "ok": True,
            "findings": len(result["summary_findings"]),
            "recommendations": len(result["recommendations"]),
            "has_summary": result["has_summary"],
            "has_conclusion": result["audit_conclusion"] is not None,
            "has_objective": result["audit_objective"] is not None,
            "conclusion_rating": result["overall_conclusion_rating"],
        }
    except Exception as e:
        return {
            "slug": md_path.stem,
            "ok": False,
            "error": str(e),
            "findings": 0,
            "recommendations": 0,
            "has_summary": False,
            "has_conclusion": False,
            "has_objective": False,
            "conclusion_rating": None,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Parse ANAO markdown into structured JSON",
        usage="python -m pipeline.parse --domain anao [options]",
    )
    parser.add_argument("--domain", required=True)
    parser.add_argument("--limit", type=int, help="Process only N files")
    parser.add_argument("--file", help="Process a single file (relative to markdown/)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing parsed files")
    parser.add_argument("--dry-run", action="store_true", help="Parse but don't write files")
    parser.add_argument("--stats", action="store_true", help="Show statistics from existing parsed output")
    parser.add_argument("--workers", type=int, default=None, help="Number of parallel workers")
    args = parser.parse_args()

    md_dir, parsed_dir = corpus_dirs(args.domain)

    if args.stats:
        _print_stats(parsed_dir)
        return

    if not md_dir.exists():
        print(f"Error: markdown directory not found: {md_dir}")
        sys.exit(1)

    parsed_dir.mkdir(parents=True, exist_ok=True)

    # Collect files to process
    if args.file:
        files = [md_dir / args.file]
        if not files[0].exists():
            print(f"Error: file not found: {files[0]}")
            sys.exit(1)
    else:
        files = sorted(md_dir.glob("*.md"))

    if args.limit:
        files = files[:args.limit]

    # Filter already-processed (unless --force)
    entries = []
    for md_path in files:
        out_path = parsed_dir / (md_path.stem + ".json")
        if out_path.exists() and not args.force:
            continue
        entries.append({
            "md_path": str(md_path),
            "out_path": str(out_path),
            "dry_run": args.dry_run,
        })

    if not entries:
        print(f"Nothing to process ({len(files)} files already parsed). Use --force to re-parse.")
        if not args.dry_run:
            _print_stats(parsed_dir)
        return

    print(f"Parsing {len(entries)} files ({len(files) - len(entries)} already done)...")

    workers = args.workers or min(cpu_count(), 8)
    results = []

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(parse_and_save, e): e for e in entries}
        done = 0
        for future in as_completed(futures):
            done += 1
            result = future.result()
            results.append(result)
            if not result["ok"]:
                print(f"  ERROR: {result['slug']}: {result.get('error', '?')}")
            if done % 100 == 0 or done == len(entries):
                print(f"  {done}/{len(entries)} done")

    # Summary
    ok = [r for r in results if r["ok"]]
    errors = [r for r in results if not r["ok"]]
    total_findings = sum(r["findings"] for r in ok)
    total_recs = sum(r["recommendations"] for r in ok)
    with_summary = sum(1 for r in ok if r["has_summary"])

    print(f"\nParsed {len(ok)} files ({len(errors)} errors)")
    print(f"  With summary section: {with_summary}")
    print(f"  Total summary findings: {total_findings}")
    print(f"  Total recommendations: {total_recs}")
    print(f"  Findings per report: mean={total_findings / len(ok):.1f}" if ok else "")

    if not args.dry_run:
        _print_stats(parsed_dir)


def _print_stats(parsed_dir: Path):
    """Print statistics from existing parsed output."""
    files = sorted(parsed_dir.glob("*.json"))
    if not files:
        print("No parsed files found.")
        return

    findings_counts = []
    rec_counts = []
    ratings = {}
    has_summary = 0
    has_conclusion = 0
    has_objective = 0
    subsections = {}
    total = 0
    errors = 0

    for f in files:
        try:
            data = json.loads(f.read_text())
        except Exception:
            errors += 1
            continue

        total += 1
        n_findings = len(data.get("summary_findings", []))
        n_recs = len(data.get("recommendations", []))
        findings_counts.append(n_findings)
        rec_counts.append(n_recs)

        if data.get("has_summary"):
            has_summary += 1
        if data.get("audit_conclusion"):
            has_conclusion += 1
        if data.get("audit_objective"):
            has_objective += 1

        rating = data.get("overall_conclusion_rating")
        if rating:
            ratings[rating] = ratings.get(rating, 0) + 1

        for finding in data.get("summary_findings", []):
            sub = finding.get("subsection") or "(none)"
            subsections[sub] = subsections.get(sub, 0) + 1

    findings_counts.sort()
    rec_counts.sort()

    print(f"\n{'='*60}")
    print(f"ANAO Parse Statistics ({total} files, {errors} read errors)")
    print(f"{'='*60}")
    print(f"  Has summary section:  {has_summary:>5} ({has_summary/total*100:.0f}%)")
    print(f"  Has conclusion:       {has_conclusion:>5} ({has_conclusion/total*100:.0f}%)")
    print(f"  Has audit objective:  {has_objective:>5} ({has_objective/total*100:.0f}%)")

    print(f"\nSummary findings:")
    print(f"  Total:   {sum(findings_counts):>6}")
    print(f"  Mean:    {sum(findings_counts)/total:>6.1f} per report")
    print(f"  Median:  {findings_counts[len(findings_counts)//2]:>6}")
    print(f"  Max:     {max(findings_counts):>6}")
    print(f"  Reports with >0: {sum(1 for c in findings_counts if c > 0)} ({sum(1 for c in findings_counts if c > 0)/total*100:.0f}%)")

    print(f"\nRecommendations:")
    print(f"  Total:   {sum(rec_counts):>6}")
    print(f"  Mean:    {sum(rec_counts)/total:>6.1f} per report")
    print(f"  Median:  {rec_counts[len(rec_counts)//2]:>6}")
    print(f"  Max:     {max(rec_counts):>6}")

    if ratings:
        print(f"\nConclusion ratings:")
        for rating, count in sorted(ratings.items(), key=lambda x: -x[1]):
            print(f"  {rating:<20s} {count:>5} ({count/total*100:.0f}%)")

    if subsections:
        print(f"\nTop 20 finding subsections:")
        for sub, count in sorted(subsections.items(), key=lambda x: -x[1])[:20]:
            print(f"  {sub:<50s} {count:>5}")


if __name__ == "__main__":
    main()
