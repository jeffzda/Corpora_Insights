#!/usr/bin/env python3
"""Extract the Summary and Recommendations section from ANAO marker JSON.

Uses marker's SectionHeader blocks and their embedded <hN> tags rather than
regex over the rendered markdown. Robust to fragmented bold styling that
defeats markdown-level matching.

Boundary detection:
- Start: first top-level heading whose text matches a summary-chapter label
- End:   first top-level heading that marks a later chapter (audit findings,
         a numbered chapter, appendices, glossary, index, abbreviations)

Output per doc:
- <stem>.summary.md  — extracted markdown of the summary section
- <stem>.summary.json — {"title", "start_heading", "end_heading",
                        "chars", "paragraphs", "start_page", "end_page"}
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Clean text from HTML heading tag.
H_TAG = re.compile(r"<h[1-6]>(.*?)</h[1-6]>", re.DOTALL)
TAG_STRIP = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")


def heading_info(html: str) -> tuple[int | None, str]:
    """Return (level, normalised_text) from a SectionHeader block's html."""
    if not html:
        return None, ""
    m = re.search(r"<h([1-6])>", html)
    level = int(m.group(1)) if m else None
    inner = H_TAG.sub(lambda m: m.group(1), html)
    text = TAG_STRIP.sub("", inner)
    text = WS.sub(" ", text).strip().lower()
    # drop trailing chapter-number artefacts like " (chapter 1)"
    text = re.sub(r"\s*\(chapter\s+\d+\)\s*$", "", text)
    return level, text


START_PATTERNS = [
    re.compile(r"^summary and recommendations?$"),
    re.compile(r"^executive summary$"),
    re.compile(r"^summary$"),
    re.compile(r"^key findings$"),
    re.compile(r"^key findings by chapter$"),
]

# Unambiguous chapter/back-matter starts — safe to end on at any same-or-higher level
END_PATTERNS_STRICT = [
    re.compile(r"^audit findings?(\s+and\s+conclusions?)?$"),
    re.compile(r"^\d+\.\s"),                          # "1. Background" etc.
    re.compile(r"^appendix\b"),
    re.compile(r"^appendices$"),
    re.compile(r"^glossary$"),
    re.compile(r"^index$"),
    re.compile(r"^abbreviations$"),
    re.compile(r"^series titles$"),
    re.compile(r"^(current )?better practice guides$"),
]

# Ambiguous — also often appear as summary sub-sections. Only end if STRICTLY
# higher level than the summary heading (i.e. a real chapter boundary).
END_PATTERNS_LOOSE = [
    re.compile(r"^(introduction|background)$"),
]


def matches_any(text: str, patterns: list[re.Pattern]) -> bool:
    return any(p.search(text) for p in patterns)


def walk(node, out, page=None):
    """Flatten to (block_type, html, page, block_id) stream."""
    bt = node.get("block_type")
    if bt == "Page":
        # marker block ids embed /page/N/...
        pid = node.get("id", "")
        m = re.search(r"/page/(\d+)", pid)
        if m:
            page = int(m.group(1)) + 1
        for c in node.get("children") or []:
            walk(c, out, page)
        return
    if bt == "Document":
        for c in node.get("children") or []:
            walk(c, out, page)
        return
    out.append((bt, node.get("html", ""), page, node.get("id", "")))
    if bt in ("ListGroup", "TableGroup", "FigureGroup", "PictureGroup"):
        for c in node.get("children") or []:
            walk(c, out, page)


def find_summary_section(blocks):
    """Return (start_idx, end_idx, start_level, start_text, end_text) or None."""
    # First pass: locate candidate starts
    for i, (bt, html, _, _) in enumerate(blocks):
        if bt != "SectionHeader":
            continue
        level, text = heading_info(html)
        if matches_any(text, START_PATTERNS):
            start_idx = i
            start_level = level
            start_text = text
            # Find end: next SectionHeader at same-or-higher level matching END patterns,
            # OR next SectionHeader at a strictly higher level (H1 if we started at H2), etc.
            for j in range(i + 1, len(blocks)):
                bt2, html2, _, _ = blocks[j]
                if bt2 != "SectionHeader":
                    continue
                lvl2, txt2 = heading_info(html2)
                if lvl2 is None:
                    continue
                if not start_level:
                    continue
                # Strict end markers: fire at same-or-higher level
                if lvl2 <= start_level and matches_any(txt2, END_PATTERNS_STRICT):
                    return start_idx, j, start_level, start_text, txt2
                # Loose end markers (introduction/background): only at strictly higher level
                if lvl2 < start_level and matches_any(txt2, END_PATTERNS_LOOSE):
                    return start_idx, j, start_level, start_text, txt2
            return start_idx, len(blocks), start_level, start_text, None
    return None


def render_block(bt: str, html: str) -> str:
    """Minimal markdown rendering for a block."""
    if bt == "SectionHeader":
        level, text = heading_info(html)
        level = level or 2
        return "#" * level + " " + text.title()
    if bt in ("PageHeader", "PageFooter", "TableOfContents"):
        return ""
    # strip tags for everything else; keep table html as-is
    if bt == "Table":
        return html.strip()
    text = TAG_STRIP.sub("", html)
    text = WS.sub(" ", text).strip()
    return text


def process(json_path: Path, out_dir: Path | None = None):
    doc = json.loads(json_path.read_text())
    blocks = []
    walk(doc, blocks)

    res = find_summary_section(blocks)
    if not res:
        return {"status": "no_start", "path": str(json_path)}

    s_idx, e_idx, s_level, s_text, e_text = res
    # Collect blocks in range
    chunk = blocks[s_idx:e_idx]
    start_page = next((p for _, _, p, _ in chunk if p), None)
    end_page = next((p for _, _, p, _ in reversed(chunk) if p), None)

    lines = []
    for bt, html, _, _ in chunk:
        rendered = render_block(bt, html)
        if rendered:
            lines.append(rendered)
            lines.append("")
    md = "\n".join(lines).rstrip() + "\n"

    para_count = sum(1 for bt, _, _, _ in chunk
                     if bt in ("Text", "TextInlineMath", "ListItem"))

    meta = {
        "status": "ok",
        "start_heading": s_text,
        "end_heading": e_text,
        "start_level": s_level,
        "start_page": start_page,
        "end_page": end_page,
        "chars": len(md),
        "paragraph_count": para_count,
        "block_count": len(chunk),
    }

    if out_dir is not None:
        stem = json_path.stem
        out_md = out_dir / f"{stem}.summary.md"
        out_meta = out_dir / f"{stem}.summary.json"
        out_md.write_text(md)
        out_meta.write_text(json.dumps(meta, indent=2))

    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path, help="marker_output dir")
    ap.add_argument("--write", action="store_true", help="write summary.md and summary.json per doc")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    jsons = sorted(args.root.rglob("*.json"))
    jsons = [j for j in jsons
             if not j.name.endswith(".summary.json")
             and not j.name.endswith("_meta.json")]
    if args.limit:
        jsons = jsons[: args.limit]

    stats = {"ok": 0, "no_start": 0, "err": 0}
    sizes = []
    starts = {}
    ends = {}
    examples_no_start = []

    for jp in jsons:
        try:
            out_dir = jp.parent if args.write else None
            r = process(jp, out_dir)
        except Exception as e:
            stats["err"] += 1
            print(f"ERR {jp.name}: {e}", file=sys.stderr)
            continue
        stats[r["status"]] = stats.get(r["status"], 0) + 1
        if r["status"] == "ok":
            sizes.append(r["chars"])
            starts[r["start_heading"]] = starts.get(r["start_heading"], 0) + 1
            ends[r["end_heading"]] = ends.get(r["end_heading"], 0) + 1
        elif r["status"] == "no_start" and len(examples_no_start) < 10:
            examples_no_start.append(jp.parent.name)

    total = len(jsons)
    print(f"Docs: {total}")
    for k, v in stats.items():
        print(f"  {k}: {v}  ({v/total*100:.1f}%)")
    if sizes:
        sizes.sort()
        print(f"\nSection chars: min={sizes[0]} p25={sizes[len(sizes)//4]} median={sizes[len(sizes)//2]} p75={sizes[3*len(sizes)//4]} max={sizes[-1]}")
        print(f"  <1k: {sum(1 for x in sizes if x<1000)}")
        print(f"  1-5k: {sum(1 for x in sizes if 1000<=x<5000)}")
        print(f"  5-20k: {sum(1 for x in sizes if 5000<=x<20000)}")
        print(f"  20-50k: {sum(1 for x in sizes if 20000<=x<50000)}")
        print(f"  >50k: {sum(1 for x in sizes if x>=50000)}")
    print("\nTop 10 start headings:")
    for h, c in sorted(starts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {c:4d}  {h}")
    print("\nTop 10 end headings:")
    for h, c in sorted(ends.items(), key=lambda x: -x[1])[:10]:
        print(f"  {c:4d}  {h}")
    if examples_no_start:
        print(f"\nSample no_start docs:")
        for n in examples_no_start:
            print(f"  {n}")


if __name__ == "__main__":
    main()
