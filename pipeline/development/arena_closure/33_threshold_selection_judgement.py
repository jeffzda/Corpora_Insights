#!/usr/bin/env python3
"""Clean LLM threshold-selection judgement for v2 parent-archetype taxonomy.

Operates purely on the 126 canonical classes from the 50-rep ensemble
consolidation. No reference to v1 or any prior parent layer. PM-facing
purpose framing in the prompt.

Output:
  closure/output/parent_ensemble/threshold_judgement.{json,md,html,raw.txt}

Model: Opus 4.7 (consistent with the prior 50-rep + consolidation chain).
"""
from __future__ import annotations
import json, time, subprocess, sys, re
from pathlib import Path
import anthropic

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT/'closure/output/parent_ensemble/canonical_vocabulary.json'
PROMPT_FILE = ROOT/'closure/prompts/threshold_selection.md'
OUT_DIR = ROOT/'closure/output/parent_ensemble'
OUT_RAW = OUT_DIR/'threshold_judgement.raw.txt'
OUT_JSON = OUT_DIR/'threshold_judgement.json'
OUT_MD = OUT_DIR/'threshold_judgement.md'
OUT_HTML = OUT_DIR/'threshold_judgement.html'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 32000


def parse_json(raw):
    r = raw.strip()
    if r.startswith('```'):
        r = r.split('\n',1)[1]
        if r.endswith('```'): r = r.rsplit('```',1)[0]
    s, e = r.find('{'), r.rfind('}')
    if s>=0 and e>s:
        try: return json.loads(r[s:e+1])
        except Exception as ex: print(f"parse error: {ex}")
    return None


def main():
    canonical = json.load(CANONICAL.open())['canonical_classes']
    sorted_classes = sorted(canonical, key=lambda c: -c['frequency'])

    # Build canonical_block — each class on a clean line
    lines = []
    for c in sorted_classes:
        cid = c['class_id']
        freq = c['frequency']
        name = (c.get('name') or '').strip()
        defn = (c.get('definition') or '').strip().replace('\n',' ')
        crit = (c.get('mechanism_criterion') or '').strip().replace('\n',' ')
        lines.append(f"[{cid}] freq={freq:.0%} — {name} :: {defn} :: {crit}")
    canonical_block = '\n'.join(lines)

    template = PROMPT_FILE.read_text()
    prompt = template.replace('{canonical_block}', canonical_block)
    print(f"prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"calling {MODEL}...", flush=True)
    started = time.time()
    parts = []
    last_print = 0; last_chars = 0; text_chars = 0
    with client.messages.stream(
        model=MODEL, max_tokens=MAX_TOKENS,
        messages=[{"role":"user","content":prompt}],
    ) as stream:
        for ev in stream.text_stream:
            parts.append(ev); text_chars += len(ev)
            now = time.time()
            if now - last_print >= 5:
                rate = (text_chars - last_chars) / max(now - last_print, 1)
                print(f"  [{int(now-started)}s] {text_chars:,} chars +{rate:.0f} c/s", flush=True)
                last_print = now; last_chars = text_chars
        msg = stream.get_final_message()
    raw = ''.join(parts); OUT_RAW.write_text(raw)
    wall = time.time() - started
    cost = msg.usage.input_tokens/1e6*5 + msg.usage.output_tokens/1e6*25
    print(f"\ndone: {wall:.0f}s, {msg.usage.input_tokens:,}in/{msg.usage.output_tokens:,}out ${cost:.3f}, stop={msg.stop_reason}", flush=True)

    parsed = parse_json(raw)
    if not parsed:
        raise SystemExit(f"parse failed; raw at {OUT_RAW}")

    result = {
        'model': MODEL,
        'cost_sync': round(cost, 3),
        'wall_seconds': round(wall, 1),
        'input_tokens': msg.usage.input_tokens,
        'output_tokens': msg.usage.output_tokens,
        'stop_reason': msg.stop_reason,
        'judgement': parsed,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2))

    # Verify / count classes that pass
    threshold = parsed.get('recommended_threshold')
    if isinstance(threshold, (int, float)):
        n_above = sum(1 for c in canonical if c['frequency'] >= threshold)
        result['verified_n_above_threshold'] = n_above

    # Build MD
    md = ['# Threshold-selection judgement — clean LLM assessment',
          '',
          f'Single-shot Opus 4.7 judgement on the 126 canonical classes from the 50-rep ensemble. Operates purely on the canonical content; no reference to v1 or any prior parent layer. PM-facing purpose framing in the prompt.',
          '',
          f'**Cost:** ${cost:.2f}, {wall:.0f}s.',
          '',
          '## Recommendation',
          '',
          f'**Threshold: {parsed.get("recommended_threshold","?")} (={parsed.get("recommended_threshold",0)*100:.0f}% if numeric)**',
          '',
          f'**Classes included: {parsed.get("n_classes_included","?")}**',
          '',
          ]
    if 'verified_n_above_threshold' in result:
        md.append(f'**Verification:** {result["verified_n_above_threshold"]} canonical classes have frequency ≥ threshold.')
        md.append('')

    md += ['## Rationale', '', parsed.get('rationale','(none)'), '']

    bc = parsed.get('borderline_classes', []) or []
    if bc:
        md += ['## Borderline classes',
               '',
               '| class | freq | verdict | reason |',
               '|---|---:|---|---|']
        for b in bc:
            md.append(f"| {b.get('class_id','?')} | {b.get('frequency',0):.0%} | {b.get('verdict','?')} | {b.get('reason','')} |")
        md.append('')

    notes = parsed.get('notes')
    if notes:
        md += ['## Notes', '', notes, '']

    OUT_MD.write_text('\n'.join(md))
    proc = subprocess.run(
        [sys.executable, MD2HTML, 'Threshold-selection judgement (Opus 4.7)',
         'Broad Learnings · clean canonical-only assessment'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    OUT_HTML.write_text(proc.stdout)

    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print(f"wrote {OUT_HTML}")
    print(f"\nthreshold: {parsed.get('recommended_threshold')}")
    print(f"n_classes: {parsed.get('n_classes_included')}")
    print(f"borderline: {len(bc)}")


if __name__ == '__main__':
    main()
