#!/usr/bin/env python3
"""Render marker JSON output to markdown with proper footnote handling.

Uses marker's native block labels to:
- Convert Footnote blocks to [^N]: definitions
- Rewrite inline <sup>N</sup> references to [^N]
- Drop PageHeader / PageFooter boilerplate
- Emit a page separator marker containing the page number
- Preserve SectionHeader hierarchy
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

SUP_NUM = re.compile(r"<sup>\s*(\d{1,3})\s*</sup>")
TAGS = re.compile(r"<[^>]+>")

# Broken font-encoding characters from legacy ANAO/gov PDFs.
# ȱ sits in whitespace positions — strip entirely.
# ȇ Ȉ Ȭ substitute for real characters — map to ASCII equivalents.
CHAR_FIXUPS = str.maketrans({
    # 2005-2009 ANAO era: Surya OCR / broken cmap substitutions
    "ȇ": "'",    # curly apostrophe
    "Ȉ": '"',    # curly double quote
    "ȉ": '"',    # opening curly double quote (seen variant)
    "Ȭ": "-",    # hyphen / en-dash
    # 2000-2004 ANAO era: CP1252 smart-quote bytes leaked through broken decode
    "\x91": "'", # left single quote
    "\x92": "'", # right single quote / apostrophe
    "\x93": '"', # left double quote
    "\x94": '"', # right double quote
    "\x95": "*", # bullet
    "\x96": "-", # en dash
    "\x97": "-", # em dash
    "\x98": "~", # small tilde
})


def clean_text(s: str) -> str:
    """Apply font-encoding cleanup to a string."""
    s = s.translate(CHAR_FIXUPS)
    s = re.sub(r"ȱ+", " ", s)
    # Fix bold/italic with inner padding: "**text **" / "** text**" → "**text**"
    # Markdown treats ** with adjacent whitespace as literal asterisks.
    # Constrain to single line (no newlines inside) and iterate to fixed point
    # because re.sub's left-to-right scanner can skip overlapping candidates
    # on crowded lines.
    subs = [
        (r"\*\*[ \t]+([^*\n]+?)\*\*", r"**\1**"),
        (r"\*\*([^*\n]+?)[ \t]+\*\*", r"**\1**"),
        (r"(?<!\*)\*[ \t]+([^*\n]+?)\*(?!\*)", r"*\1*"),
        (r"(?<!\*)\*([^*\n]+?)[ \t]+\*(?!\*)", r"*\1*"),
    ]
    for _ in range(5):  # usually converges in 2-3
        prev = s
        for pat, rep in subs:
            s = re.sub(pat, rep, s)
        if s == prev:
            break
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" +\n", "\n", s)
    return s


def html_to_text(s: str) -> str:
    """Strip HTML tags, decode entities. Keep <sup>N</sup> marker first."""
    # Replace sup with sentinel so it survives tag strip
    s = SUP_NUM.sub(r"⟦FN:\1⟧", s)
    # Inline formatting -> markdown
    s = re.sub(r"<i>(.*?)</i>", r"*\1*", s, flags=re.DOTALL)
    s = re.sub(r"<b>(.*?)</b>", r"**\1**", s, flags=re.DOTALL)
    s = re.sub(r"<em>(.*?)</em>", r"*\1*", s, flags=re.DOTALL)
    s = re.sub(r"<strong>(.*?)</strong>", r"**\1**", s, flags=re.DOTALL)
    s = TAGS.sub("", s)
    s = html.unescape(s)
    return s.strip()


def extract_footnote_num(html_str: str) -> tuple[str | None, str]:
    """Pull the leading footnote number from a Footnote block's html.

    Marker formats footnotes as <p><sup>N</sup>  body...</p>. Sometimes
    the sup is empty (continuation or misdetection) — then we try to
    read a leading digit from the plain text.
    """
    m = SUP_NUM.search(html_str)
    if m:
        num = m.group(1)
        cleaned = SUP_NUM.sub("", html_str, count=1)
        return num, html_to_text(cleaned)
    text = html_to_text(html_str)
    m = re.match(r"^(\d{1,3})\s+(.+)$", text, re.DOTALL)
    if m:
        return m.group(1), m.group(2).strip()
    return None, text


def walk_blocks(node, out):
    """Flatten children into an ordered block stream."""
    bt = node.get("block_type")
    if bt == "Page":
        out.append(("Page", node))
        for c in node.get("children") or []:
            walk_blocks(c, out)
        return
    if bt in ("Document",):
        for c in node.get("children") or []:
            walk_blocks(c, out)
        return
    out.append((bt, node))
    # Groups: recurse so inner blocks are reachable (ListGroup -> ListItem etc.)
    if bt in ("ListGroup", "TableGroup", "FigureGroup", "PictureGroup"):
        for c in node.get("children") or []:
            walk_blocks(c, out)


def render(doc: dict, include_images: bool = False, page_markers: bool = True) -> tuple[str, list[dict]]:
    blocks = []
    walk_blocks(doc, blocks)

    out_lines: list[str] = []
    footnotes: list[tuple[str, str, int]] = []  # (num, body, page)
    pages_meta: list[dict] = []
    current_page = None

    def emit(s: str = ""):
        out_lines.append(s)

    for bt, node in blocks:
        if bt == "Page":
            page_no = len(pages_meta) + 1  # 1-indexed sequential
            # Marker uses /page/N/... in block ids — try to parse
            pid = node.get("id", "")
            m = re.search(r"/page/(\d+)", pid)
            if m:
                page_no = int(m.group(1)) + 1  # marker is 0-indexed
            pages_meta.append({"page": page_no, "id": pid})
            current_page = page_no
            if page_markers:
                if out_lines:
                    emit()
                emit(f"<!-- page: {page_no} -->")
                emit()
            continue

        if bt in ("PageHeader", "PageFooter"):
            continue

        if bt == "SectionHeader":
            level = node.get("heading_level") or 2
            level = max(1, min(6, int(level)))
            text = html_to_text(node.get("html", ""))
            if text:
                emit("#" * level + " " + text)
                emit()
            continue

        if bt == "Footnote":
            num, body = extract_footnote_num(node.get("html", ""))
            if num and body:
                # Rewrite remaining sentinels inside body (nested refs)
                body = re.sub(r"⟦FN:(\d+)⟧", r"[^\1]", body)
                footnotes.append((num, body, current_page or 0))
            continue

        if bt == "Caption":
            text = html_to_text(node.get("html", ""))
            text = re.sub(r"⟦FN:(\d+)⟧", r"[^\1]", text)
            if text:
                emit(f"*{text}*")
                emit()
            continue

        if bt == "ListItem":
            text = html_to_text(node.get("html", ""))
            text = re.sub(r"⟦FN:(\d+)⟧", r"[^\1]", text)
            # Legacy ANAO PDFs encode the bullet glyph as a literal "x "
            # at the start of each list item — strip it.
            text = re.sub(r"^x[\sȱ]+", "", text)
            if text:
                # Numbered paragraphs (e.g. "3.43 Text..." or "46. Text...")
                # get misclassified as ListItem — emit as plain paragraph
                # so they don't render as nested dot-list items.
                if re.match(r"^\**\d+(\.\d+)*\.?\**[\sȱ]+\S", text):
                    emit(text)
                    emit()
                else:
                    emit(f"- {text}")
            continue

        if bt == "Table":
            # marker renders tables as HTML in the `html` field; keep as HTML
            # block so the markdown stays renderable. Alternative: parse to pipe.
            html_str = node.get("html", "").strip()
            if html_str:
                emit(html_str)
                emit()
            continue

        if bt in ("Figure", "Picture") and include_images:
            # Images are saved as sidecar files; reference by id
            pid = node.get("id", "")
            emit(f"![figure]({pid})")
            emit()
            continue

        if bt == "TableOfContents":
            # TOC is redundant given section hierarchy + page separators.
            # The flattened HTML loses column alignment anyway.
            continue

        if bt in ("Text", "TextInlineMath", "Code", "Equation",
                  "Form", "Handwriting",
                  "ComplexRegion", "Reference"):
            text = html_to_text(node.get("html", ""))
            text = re.sub(r"⟦FN:(\d+)⟧", r"[^\1]", text)
            if text:
                if bt == "Code":
                    emit("```")
                    emit(text)
                    emit("```")
                elif re.match(r"^x[\sȱ]+\S", text):
                    # Text block that's actually a misclassified bullet item.
                    emit(f"- {re.sub(r'^x[\sȱ]+', '', text)}")
                else:
                    emit(text)
                emit()
            continue

        # Skip groups / table cells (rendered via parent)

    # Inline footnote recovery deferred — marker often fails to tag inline
    # <sup> glyphs, leaving bare digits glued to preceding words. A
    # monotonic-sequence heuristic works but has false-positive overlap
    # with identifiers (CO2, FY23, ED1, AS4777). Revisit later.

    # Footnote definitions at the end
    if footnotes:
        emit()
        emit("---")
        emit()
        seen = set()
        for num, body_text, pg in footnotes:
            key = (num, body_text[:40])
            if key in seen:
                continue
            seen.add(key)
            body_text = re.sub(r"\s+", " ", body_text)
            emit(f"[^{num}]: {body_text}")

    md = "\n".join(out_lines).rstrip() + "\n"
    md = clean_text(md)
    return md, pages_meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--no-pages", action="store_true", help="omit page separator markers")
    args = ap.parse_args()

    doc = json.loads(args.json_path.read_text())
    md, pages = render(doc, page_markers=not args.no_pages)
    out = args.output or args.json_path.with_suffix(".rendered.md")
    out.write_text(md)
    print(f"wrote {out} ({len(md)} chars, {len(pages)} pages)", file=sys.stderr)


if __name__ == "__main__":
    main()
