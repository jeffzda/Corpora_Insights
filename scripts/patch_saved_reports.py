#!/usr/bin/env python3
"""
Patch existing saved report HTML files to fix broken partial citation linkification.

Problems fixed:
1. CITED list was built from full IDs only — partial continuations (", -48302",
   "through -51260", ", and -65840") were missing from CITED so those IDs had no
   INDEX_MAP entry and were left as unlinked text.
2. JS expansion regex in old reports used broken escaping (\\b instead of \b)
   and was missing entirely from the oldest saved reports.

This script:
- Downloads each saved report from the server
- Parses its body HTML to find ALL referenced IDs (expanding partial patterns)
- Looks up missing records from local per_doc YAML files
- Rebuilds the CITED JSON with the full set
- Replaces the JS linkification block with the fixed version
- Uploads the patched HTML back to the server
"""
import re
import json
import os
import glob
import yaml
import subprocess

SERVER = "root@85.155.188.202"
REMOTE_DIR = "/var/www/arena/reports"
LOCAL_YAML_DIR = "/home/jeffzda/ARENA/insights/per_doc"
REPORT_IDS = [
    "rep_1774839484518",
    "rep_1774840413811",
    "rep_1774844564483",
    "rep_1774850590814",
]

# ── Load record lookup from local YAMLs ──────────────────────────────────────

def load_records():
    records = {}
    for path in sorted(glob.glob(os.path.join(LOCAL_YAML_DIR, "*.yaml"))):
        try:
            with open(path, encoding="utf-8") as f:
                recs = yaml.safe_load(f)
            if isinstance(recs, list):
                for r in recs:
                    rid = r.get("record_id")
                    if rid:
                        records[rid] = r
        except Exception:
            pass
    print(f"Loaded {len(records)} records from YAML files")
    return records


# ── Expand partial citations in text ─────────────────────────────────────────

def expand_ids_from_text(text):
    """
    Return a set of all ARENA-DLV-NNNNN IDs referenced in text,
    including those in partial citation continuations like:
      ARENA-DLV-48301, -48302, -51251 through -51260, -36701, -36702
      ARENA-DLV-3964, -15813, -40356, and -65840
      ARENA-DLV-8701 through -8725
    """
    ids = set()

    # Strip HTML tags first so we operate on plain text
    plain = re.sub(r'<[^>]+>', ' ', text)

    # Main pattern: ARENA-DLV-N followed by optional continuations
    expand_re = re.compile(
        r'ARENA-DLV-(\d+)'
        r'((?:'
        r'(?:\s+through\s+-\d+)'              # " through -N"
        r'|(?:\s*,\s*(?:and\s+)?-\d+(?:\s+through\s+-\d+)?)'  # ", -N" or ", and -N" or ", -N through -M"
        r')*)',
        re.IGNORECASE,
    )

    for m in expand_re.finditer(plain):
        first = int(m.group(1))
        ids.add(f"ARENA-DLV-{first}")
        tail = m.group(2) or ""

        # Check for immediate range: " through -M" at start of tail
        imm = re.match(r'^\s+through\s+-(\d+)', tail)
        rest = tail[imm.end():] if imm else tail
        if imm:
            end = int(imm.group(1))
            for i in range(first + 1, min(end + 1, first + 51)):
                ids.add(f"ARENA-DLV-{i}")

        # Remaining comma-separated items
        for item in re.finditer(r',\s*(?:and\s+)?-(\d+)(?:\s+through\s+-(\d+))?', rest, re.IGNORECASE):
            start = int(item.group(1))
            ids.add(f"ARENA-DLV-{start}")
            if item.group(2):
                end = int(item.group(2))
                for j in range(start + 1, min(end + 1, start + 51)):
                    ids.add(f"ARENA-DLV-{j}")

    return ids


# ── Fixed JS linkification block ─────────────────────────────────────────────

FIXED_JS = r"""// Linkify record IDs with sequential citation numbers
const body = document.getElementById('rp-body');
let rpHtml = body.innerHTML;
// Expand partial citations: "ARENA-DLV-N, -M", "through -M", ", and -M"
rpHtml = rpHtml.replace(
  /\bARENA-DLV-(\d+)((?:(?:\s+through\s+-\d+)|(?:\s*,\s*(?:and\s+)?-\d+(?:\s+through\s+-\d+)?))+)/g,
  function(match, firstNum, tail) {
    var ids = ['ARENA-DLV-' + firstNum];
    var immRange = /^\s+through\s+-(\d+)/.exec(tail);
    var rest = immRange ? tail.slice(immRange[0].length) : tail;
    if (immRange) {
      var s = parseInt(firstNum), e = parseInt(immRange[1]);
      for (var i = s + 1; i <= Math.min(e, s + 50); i++) ids.push('ARENA-DLV-' + i);
    }
    var itemRe = /,\s*(?:and\s+)?-(\d+)(?:\s+through\s+-(\d+))?/g;
    var mx;
    while ((mx = itemRe.exec(rest)) !== null) {
      if (mx[2]) {
        var sa = parseInt(mx[1]), ea = parseInt(mx[2]);
        for (var j = sa; j <= Math.min(ea, sa + 50); j++) ids.push('ARENA-DLV-' + j);
      } else {
        ids.push('ARENA-DLV-' + mx[1]);
      }
    }
    return ids.join(', ');
  }
);
rpHtml = rpHtml.replace(
  /\b(ARENA-DLV-\d{4,})\b/g,
  (match, id) => {
    const n = INDEX_MAP.get(id);
    return n ? `<span class="record-link" data-id="${id}">[${n}]</span>` : match;
  }
);
body.innerHTML = rpHtml;"""


# ── Patch a single HTML file ──────────────────────────────────────────────────

def build_cited_in_order(body_html, records):
    """
    Build CITED list in order of first appearance in the body text,
    expanding partial citation continuations (ranges, comma-lists, 'and').
    This ensures INDEX_MAP assigns [1], [2], ... in reading order.
    """
    plain = re.sub(r'<[^>]+>', ' ', body_html)
    cited = []
    seen = set()

    def add(rid):
        if rid not in seen:
            rec = records.get(rid)
            if rec:
                cited.append(rec)
            seen.add(rid)  # mark even if not in records, to avoid re-querying

    expand_re = re.compile(
        r'ARENA-DLV-(\d+)'
        r'((?:'
        r'(?:\s+through\s+-\d+)'
        r'|(?:\s*,\s*(?:and\s+)?-\d+(?:\s+through\s+-\d+)?)'
        r')*)',
        re.IGNORECASE,
    )
    for m in expand_re.finditer(plain):
        first = int(m.group(1))
        add(f'ARENA-DLV-{first}')
        tail = m.group(2) or ''
        imm = re.match(r'^\s+through\s+-(\d+)', tail, re.IGNORECASE)
        rest = tail[imm.end():] if imm else tail
        if imm:
            end = int(imm.group(1))
            for i in range(first + 1, min(end + 1, first + 51)):
                add(f'ARENA-DLV-{i}')
        for item in re.finditer(r',\s*(?:and\s+)?-(\d+)(?:\s+through\s+-(\d+))?', rest, re.IGNORECASE):
            start = int(item.group(1))
            add(f'ARENA-DLV-{start}')
            if item.group(2):
                end = int(item.group(2))
                for j in range(start + 1, min(end + 1, start + 51)):
                    add(f'ARENA-DLV-{j}')
    return cited


def patch_html(html, records):
    # Extract body section for ID scanning
    body_match = re.search(r'<div class="rp-body"[^>]*>(.*?)</div>\s*<div class="rp-footer"', html, re.DOTALL)
    if not body_match:
        print("  WARNING: could not find rp-body section")
        body_text = html
    else:
        body_text = body_match.group(1)

    # Rebuild CITED entirely in order of first appearance
    new_cited = build_cited_in_order(body_text, records)
    missing = len(expand_ids_from_text(body_text)) - len(new_cited)
    print(f"  Built CITED: {len(new_cited)} records in text order ({missing} IDs not in local YAMLs)")

    # Replace CITED JSON
    new_cited_json = json.dumps(new_cited, ensure_ascii=False, separators=(',', ':'))
    cited_match = re.search(r'const CITED = (\[.*?\]);', html, re.DOTALL)
    if cited_match:
        html = html[:cited_match.start()] + f"const CITED = {new_cited_json};" + html[cited_match.end():]
    else:
        print("  WARNING: could not find CITED declaration to replace")

    # Replace the JS linkification block
    # Match from "// Linkify record IDs" to just before the next major section.
    # Using "const _tooltip" as the reliable end-anchor (always follows this block).
    js_block_re = re.compile(
        r'// Linkify record IDs.*?(?=\n\nconst _tooltip)',
        re.DOTALL,
    )
    m = js_block_re.search(html)
    if m:
        html = html[:m.start()] + FIXED_JS + html[m.end():]
        print("  Replaced JS linkification block")
    else:
        print("  WARNING: could not find JS linkification block to replace")

    return html


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    records = load_records()

    for rep_id in REPORT_IDS:
        remote_path = f"{REMOTE_DIR}/{rep_id}.html"
        local_path = f"/tmp/{rep_id}.html"
        local_fixed = f"/tmp/{rep_id}_fixed.html"

        print(f"\nPatching {rep_id}...")

        # Download
        result = subprocess.run(
            ["scp", f"{SERVER}:{remote_path}", local_path],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  ERROR downloading: {result.stderr}")
            continue

        with open(local_path, encoding="utf-8") as f:
            html = f.read()

        print(f"  Downloaded ({len(html):,} chars)")

        # Patch
        fixed = patch_html(html, records)

        # Save
        with open(local_fixed, "w", encoding="utf-8") as f:
            f.write(fixed)

        # Upload
        result = subprocess.run(
            ["scp", local_fixed, f"{SERVER}:{remote_path}"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  ERROR uploading: {result.stderr}")
        else:
            print(f"  Uploaded successfully ({len(fixed):,} chars)")


if __name__ == "__main__":
    main()
