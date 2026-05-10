"""Lenient JSON parser for LLM outputs.

Extracted from corpora/arena/clustering_v2/code/06_classify_and_cluster_orphans.py
and corpora/arena/clustering_v2/code/13_pending_reclassify.py and standardised
across pipeline stages.

Handles:
- Markdown code-fenced JSON (```json ... ```)
- Bare JSON (most common Opus output with strict-format prompts)
- Truncation: when max_tokens cuts mid-record, recover all complete top-level
  array entries before the cut.
"""
from __future__ import annotations
import json
import re
from typing import Any, Dict, List, Optional


def parse_json_tolerant(text: str) -> Dict[str, Any]:
    """Parse JSON output from an LLM, recovering from common truncation patterns.

    Returns:
      - parsed dict if valid
      - dict with key '_recovered' containing list of complete record-shaped objects
        if the input was truncated mid-array
      - empty dict {} if nothing recoverable
    """
    # Strip markdown fences
    m = re.search(r'```json\s*(.*?)(?:```|$)', text, re.DOTALL)
    body = m.group(1).strip() if m else text.strip()

    # Strict parse first
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        pass

    # Try first-{ to last-} substring extraction
    first = body.find('{')
    last = body.rfind('}')
    if first >= 0 and last > first:
        try:
            return json.loads(body[first:last + 1])
        except json.JSONDecodeError:
            pass

    # Recover complete objects from a truncated array
    objects: List[dict] = []
    arr_start = body.find('[')
    if arr_start >= 0:
        depth = 0
        obj_start = -1
        in_str = False
        esc = False
        i = arr_start + 1
        while i < len(body):
            ch = body[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == '{':
                    if depth == 0:
                        obj_start = i
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0 and obj_start >= 0:
                        try:
                            objects.append(json.loads(body[obj_start:i + 1]))
                        except json.JSONDecodeError:
                            pass
                        obj_start = -1
            i += 1
    if objects:
        return {'_recovered': objects}
    return {}


def parse_records_array(text: str, key: str = 'records') -> List[dict]:
    """Convenience: parse and return the named top-level array, with lenient recovery."""
    parsed = parse_json_tolerant(text)
    if key in parsed and isinstance(parsed[key], list):
        return parsed[key]
    if '_recovered' in parsed:
        return parsed['_recovered']
    return []


def parse_assignments(text: str) -> List[dict]:
    """Convenience: parse a Pass 1 assignments array (used by sweep / singleton stages)."""
    return parse_records_array(text, key='assignments')
