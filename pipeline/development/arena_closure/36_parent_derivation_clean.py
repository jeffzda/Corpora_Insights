#!/usr/bin/env python3
"""Re-derive a canonical parent set directly from the 4,150 raw parent labels
of the 50-rep ensemble, using the deliberation-rich PM-purpose prompt.

Skips the original consolidation step (20_consolidate_ensemble.py → 126
canonical classes) and replaces it with a single-call derivation that
applies stricter prompt-design discipline: PM-purpose framing, no priming
examples, deliberation-rich requirement on every borderline parent
boundary, and direct synthesis from raw labels rather than from a
pre-consolidated intermediate.

Input: closure/output/parent_ensemble/parsed_runs.jsonl
Prompt: closure/prompts/parent_derivation_clean.md
Output: closure/output/parent_ensemble/parent_derivation_clean.{json,md,html}
"""
from __future__ import annotations
import json, time, subprocess, sys, re
from pathlib import Path
import anthropic

ROOT = Path(__file__).resolve().parents[2]
PARSED_RUNS = ROOT/'closure/output/parent_ensemble/parsed_runs.jsonl'
PROMPT_FILE = ROOT/'closure/prompts/parent_derivation_clean.md'
OUT_DIR = ROOT/'closure/output/parent_ensemble'
OUT_RAW = OUT_DIR/'parent_derivation_clean.raw.txt'
OUT_JSON = OUT_DIR/'parent_derivation_clean.json'
OUT_MD = OUT_DIR/'parent_derivation_clean.md'
OUT_HTML = OUT_DIR/'parent_derivation_clean.html'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 64000


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
    runs = [json.loads(l) for l in PARSED_RUNS.open()]
    print(f"Loaded {len(runs)} runs", flush=True)

    # Build label list
    label_records = []
    for r in runs:
        run_id = r['custom_id']
        for p in r.get('parents', []):
            pid = p.get('parent_id', '')
            name = (p.get('name') or '').replace('|', '/').strip()
            crit = (p.get('mechanism_criterion') or '').replace('|', '/').replace('\n', ' ').strip()
            label_records.append({
                'label_id': f'{run_id}:{pid}',
                'name': name,
                'criterion': crit,
            })
    print(f"  {len(label_records)} labels total", flush=True)

    # Build labels_block — same format as 20_consolidate_ensemble.py
    lines = [f"  [{lr['label_id']}] {lr['name']} | {lr['criterion']}" for lr in label_records]
    labels_block = '\n'.join(lines)

    template = PROMPT_FILE.read_text()
    prompt = template.replace('{labels_block}', labels_block)
    print(f"prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"calling {MODEL} (max_tokens={MAX_TOKENS:,})...", flush=True)
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
            if now - last_print >= 10:
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

    parents = parsed.get('parents', [])
    delib = parsed.get('deliberated_mechanisms', []) or []
    n_parents = len(parents)
    n_delib = len(delib)

    json.dump({
        'model': MODEL, 'cost_sync': round(cost,3), 'wall_seconds': round(wall,1),
        'input_tokens': msg.usage.input_tokens, 'output_tokens': msg.usage.output_tokens,
        'stop_reason': msg.stop_reason,
        'n_parents': n_parents, 'n_deliberated': n_delib,
        'derivation': parsed,
    }, open(OUT_JSON,'w'), indent=2)

    # Build MD
    md = ['# Re-derived parent set from 4,150 raw labels (deliberation-rich, PM-purpose)',
          '',
          f'Single Opus 4.7 call. Input: 4,150 raw parent labels from the 50-rep ensemble. Output: a canonical parent set + per-parent rationale + per-borderline-decision deliberation entries. Skips the original consolidation step that produced the 126 canonical classes.',
          '',
          f'**Cost:** ${cost:.2f}, {wall:.0f}s wall.',
          f'**Tokens:** {msg.usage.input_tokens:,} in / {msg.usage.output_tokens:,} out (stop={msg.stop_reason}).',
          '',
          f'**Parents derived: {n_parents}**',
          f'**Deliberation entries: {n_delib}**',
          '',
          '## Rationale',
          '',
          parsed.get('rationale','(none)'),
          '',
          '## Parents',
          '',
          '| parent | name | mechanism_criterion | est. recurrence |',
          '|---|---|---|---|']
    for p in parents:
        rec = p.get('estimated_recurrence','—')
        md.append(f"| {p.get('parent_id','?')} | {p.get('name','?')} | {p.get('mechanism_criterion','—')} | {rec} |")

    if delib:
        md += ['', f'## Deliberation entries ({n_delib})', '',
               '| candidate | verdict | reason |',
               '|---|---|---|']
        for d in delib:
            md.append(f"| {d.get('candidate_name','?')} | {d.get('verdict','?')} | {d.get('reason','')} |")

    notes = parsed.get('notes')
    if notes:
        md += ['', '## Notes', '', notes]

    OUT_MD.write_text('\n'.join(md))
    proc = subprocess.run(
        [sys.executable, MD2HTML, 'Re-derived parent set (deliberation-rich, single-call)',
         f'Broad Learnings · {n_parents} parents from 4,150 labels'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    OUT_HTML.write_text(proc.stdout)

    print(f"\nwrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print(f"\nparents: {n_parents}, deliberation entries: {n_delib}")


if __name__ == '__main__':
    main()
