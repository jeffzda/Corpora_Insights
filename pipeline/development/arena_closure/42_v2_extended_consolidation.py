#!/usr/bin/env python3
"""v2 extended consolidation — single Opus call producing canonical
definitions for all 83 promoted v2 parents in one unified pass.

Inputs (all from the 59-rep deliberation-rich ensemble):
  - 43 core classes (≥90% rep agreement)
  - 27 high-tier classes promoted by script 39
  - 13 boundary classes promoted by script 41 (after dedup of internal duplicates)

For each class, sends Opus the rep-evidence: candidate_names, candidate_criteria,
top_exemplar_cluster_ids, and (for promoted high-tier) the script-39 promotion reason.

Output: unified v2_parents_extended.{json,md,html} with parent_id, name,
description, mechanism_criterion, exemplar_cluster_ids, source_tier
(core | high | boundary), and n_reps for every parent.
"""
from __future__ import annotations
import json, time, subprocess, sys, re
from collections import Counter
from pathlib import Path
import anthropic

ROOT = Path(__file__).resolve().parents[2]
PARSED = ROOT/'closure/output/parent_derivation_clean_ensemble/parsed_runs.jsonl'
V2 = ROOT/'closure/output/parent_derivation_clean_ensemble/v2_parents.json'
BDRY = ROOT/'closure/output/parent_derivation_clean_ensemble/v2_boundary_extension.json'
OUT_DIR = ROOT/'closure/output/parent_derivation_clean_ensemble'
OUT_RAW = OUT_DIR/'v2_parents_extended.raw.txt'
OUT_JSON = OUT_DIR/'v2_parents_extended.json'
OUT_MD = OUT_DIR/'v2_parents_extended.md'
OUT_HTML = OUT_DIR/'v2_parents_extended.html'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 64000


PROMPT = """# v2 extended parent-set consolidation

You are producing the final canonical definitions for the v2 ARENA failure-mechanism parent taxonomy. The 59-rep deliberation-rich ensemble produced three tiers of promoted mechanism classes:

- **Core ({n_core}, ≥90% rep agreement):** universally surfaced across reps.
- **High-tier promoted ({n_high}, 70-89% rep agreement):** judged worth promoting in an earlier pass.
- **Boundary promoted ({n_bdry}, 40-69% rep agreement):** judged worth promoting against the existing v2 set.

All {n_total} are accepted. Your task is to produce a **single unified parent definition** for each, in the same v2 style: canonical name, 2-4 sentence description, one-sentence mechanism criterion, 3-5 exemplar_cluster_ids drawn from the rep evidence.

## Audience

The v2 parent set serves an ARENA portfolio manager as a navigable diagnostic vocabulary. The PM scans parent names + criteria to surface every important failure mechanism that could plausibly arise within their project. Optimise canonical names + criteria for that scan-by-glance use.

## Constraints

- Each parent's name and criterion must be derived from the rep evidence — pick from candidate phrasings or synthesise from observed criteria. Do not invent new mechanisms.
- Where two input classes name closely-overlapping mechanisms (e.g. duplicates flagged in the boundary tier), produce a single parent definition and note the consolidation in `notes`. The expected output count is **at most {n_total}**, possibly fewer if you find redundancy.
- Order parents thematically (e.g. data/measurement family first, regulatory family adjacent, market/economic family, etc.) — choose grouping that makes the set scannable.
- Assign parent_id p01, p02, ... in your output order.
- For each parent, set `source_tier` to "core", "high", or "boundary" matching the input class's origin tier. If you consolidated multiple input classes into one parent, list the highest tier in `source_tier` and list the input class_ids in `source_class_ids`.

## Output

Strict JSON, no preamble:

```json
{{
  "parents": [
    {{
      "parent_id": "p01",
      "name": "<3-7 words>",
      "description": "<2-4 sentences>",
      "mechanism_criterion": "<one sentence>",
      "exemplar_cluster_ids": ["cNNN", ...],
      "source_tier": "core | high | boundary",
      "source_class_ids": ["core_NN" or "high_NN" or "bdry_NN", possibly multiple],
      "n_reps_min": <integer, smallest n_reps across source classes>
    }}
  ],
  "notes": "<≤200 words: structural observations, consolidations made, any tensions between adjacent parents>"
}}
```

## Input — promoted mechanism classes ({n_total} total)

Each entry:
- `class_id`: synthetic ID for this consolidation
- `tier`: core | high | boundary
- `n_reps`: how many of 59 reps proposed a parent matching this class
- `candidate_names`: distinct name phrasings (most common first, top 6)
- `candidate_criteria`: distinct criterion phrasings (top 3)
- `top_exemplar_cluster_ids`: most-frequently-cited cluster_ids (top 8)
- `prior_promotion_reason` (high-tier and boundary only): the one-line reason given when the class was promoted

{classes_block}
"""


def main():
    all_reps = [json.loads(l) for l in PARSED.open()]
    print(f"loaded {len(all_reps)} reps", flush=True)

    STOP = {'and','or','of','the','to','for','a','in','on','at','by','from','as','an','vs','with','due','no','not','its'}
    def toks(s):
        return {w.lower() for w in re.findall(r"[a-zA-Z]{4,}", s) if w.lower() not in STOP}

    classes = []
    for r in all_reps:
        rep_id = r['rep']
        for p in r['derivation'].get('parents', []):
            t = toks(p.get('name',''))
            best, best_jac = None, 0
            for i, c in enumerate(classes):
                jac = len(t & c['tokens'])/max(len(t|c['tokens']),1)
                if jac > best_jac: best, best_jac = i, jac
            label = {
                'rep': rep_id,
                'name': p.get('name',''),
                'criterion': p.get('mechanism_criterion',''),
                'exemplar_cluster_ids': p.get('exemplar_cluster_ids', []),
            }
            if best is not None and best_jac >= 0.30:
                classes[best]['runs'].add(rep_id)
                classes[best]['labels'].append(label)
            else:
                classes.append({'tokens': t, 'runs': {rep_id}, 'labels': [label]})

    n_reps = len(all_reps)
    core = [c for c in classes if len(c['runs'])/n_reps >= 0.90]
    high = [c for c in classes if 0.70 <= len(c['runs'])/n_reps < 0.90]
    boundary = [c for c in classes if 0.40 <= len(c['runs'])/n_reps < 0.70]

    # Promoted high (load script 39 verdicts)
    v2j = json.load(V2.open())
    high_judgements = v2j['consolidation']['high_tier_judgements']
    high_promoted_ids = {h['class_id']: h.get('reason','') for h in high_judgements if h['verdict']=='promote'}

    # Promoted boundary (load script 41 verdicts)
    bdj = json.load(BDRY.open())
    bdry_judgements = bdj['judgements']['boundary_judgements']
    bdry_promoted_ids = {b['class_id']: b.get('reason','') for b in bdry_judgements if b['verdict']=='promote'}

    def class_summary(c, idx, prefix):
        names = Counter(l['name'] for l in c['labels'])
        crits = Counter(l['criterion'] for l in c['labels'])
        exemplars = Counter()
        for l in c['labels']:
            for cid in l['exemplar_cluster_ids']:
                exemplars[cid] += 1
        return {
            'class_id': f'{prefix}_{idx:02d}',
            'n_reps': len(c['runs']),
            'candidate_names': [n for n, _ in names.most_common(6)],
            'candidate_criteria': [cr for cr, _ in crits.most_common(3)],
            'top_exemplar_cluster_ids': [cid for cid, _ in exemplars.most_common(8)],
        }

    # Build promoted-class list
    items = []
    for i, c in enumerate(core):
        s = class_summary(c, i+1, 'core')
        s['tier'] = 'core'
        items.append(s)
    for i, c in enumerate(high):
        s = class_summary(c, i+1, 'high')
        if s['class_id'] in high_promoted_ids:
            s['tier'] = 'high'
            s['prior_promotion_reason'] = high_promoted_ids[s['class_id']]
            items.append(s)
    for i, c in enumerate(boundary):
        s = class_summary(c, i+1, 'bdry')
        if s['class_id'] in bdry_promoted_ids:
            s['tier'] = 'boundary'
            s['prior_promotion_reason'] = bdry_promoted_ids[s['class_id']]
            items.append(s)

    print(f"core: {len(core)}, high promoted: {sum(1 for x in items if x['tier']=='high')}, boundary promoted: {sum(1 for x in items if x['tier']=='boundary')}", flush=True)
    print(f"total to consolidate: {len(items)}", flush=True)

    def fmt(s):
        lines = [f"\n[{s['class_id']}] tier={s['tier']} n_reps={s['n_reps']}/59"]
        lines.append(f"  candidate_names: " + ' || '.join(s['candidate_names'][:6]))
        lines.append(f"  candidate_criteria (top 3): " + ' || '.join(s['candidate_criteria'][:3]))
        lines.append(f"  top_exemplar_cluster_ids: " + ', '.join(s['top_exemplar_cluster_ids']))
        if s.get('prior_promotion_reason'):
            lines.append(f"  prior_promotion_reason: {s['prior_promotion_reason']}")
        return '\n'.join(lines)

    classes_block = '\n'.join(fmt(s) for s in items)

    n_core_in = sum(1 for x in items if x['tier']=='core')
    n_high_in = sum(1 for x in items if x['tier']=='high')
    n_bdry_in = sum(1 for x in items if x['tier']=='boundary')

    prompt = PROMPT.format(
        n_core=n_core_in, n_high=n_high_in, n_bdry=n_bdry_in, n_total=len(items),
        classes_block=classes_block,
    )
    print(f"prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"calling {MODEL}...", flush=True)
    started = time.time()
    parts = []
    last_print, last_chars, text_chars = 0, 0, 0
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
                last_print, last_chars = now, text_chars
        msg = stream.get_final_message()
    raw = ''.join(parts); OUT_RAW.write_text(raw)
    wall = time.time() - started
    cost = msg.usage.input_tokens/1e6*5 + msg.usage.output_tokens/1e6*25
    print(f"done: {wall:.0f}s, {msg.usage.input_tokens:,}in/{msg.usage.output_tokens:,}out ${cost:.3f}, stop={msg.stop_reason}", flush=True)

    r = raw.strip()
    if r.startswith('```'):
        r = r.split('\n',1)[1]
        if r.endswith('```'): r = r.rsplit('```',1)[0]
    s, e = r.find('{'), r.rfind('}')
    parsed = None
    if s>=0 and e>s:
        try: parsed = json.loads(r[s:e+1])
        except Exception as ex: print(f"parse error: {ex}")
    if not parsed:
        raise SystemExit(f"parse failed; raw at {OUT_RAW}")

    parents = parsed.get('parents', [])
    tier_counts = Counter(p.get('source_tier','?') for p in parents)
    print(f"parents: {len(parents)}, tiers: {dict(tier_counts)}", flush=True)

    json.dump({
        'model': MODEL, 'cost': round(cost,3), 'wall_seconds': round(wall,1),
        'input_tokens': msg.usage.input_tokens, 'output_tokens': msg.usage.output_tokens,
        'n_input_classes': len(items), 'n_parents': len(parents),
        'tier_counts': dict(tier_counts),
        'extended': parsed,
    }, open(OUT_JSON,'w'), indent=2)

    md = ['# v2 extended parent set — 59-rep ensemble + boundary-tier extension', '',
          f'Single Opus 4.7 call. {len(items)} promoted mechanism classes consolidated into {len(parents)} unified v2 parent definitions.',
          f'**Cost:** ${cost:.2f}, {wall:.0f}s wall.', '',
          f'**Tier breakdown:** {dict(tier_counts)}', '',
          '## Parent set', '',
          '| parent | name | tier | n_reps_min | mechanism criterion |',
          '|---|---|---|---|---|']
    for p in parents:
        crit = (p.get('mechanism_criterion','—') or '—')[:120]
        md.append(f"| {p.get('parent_id','?')} | {p.get('name','?')} | {p.get('source_tier','?')} | {p.get('n_reps_min','?')} | {crit} |")

    md += ['', '## Full definitions', '']
    for p in parents:
        md += [f"### {p.get('parent_id','?')} — {p.get('name','?')}",
               '',
               f"*tier: {p.get('source_tier','?')}, n_reps_min: {p.get('n_reps_min','?')}, sources: {', '.join(p.get('source_class_ids',[]))}*",
               '',
               p.get('description',''),
               '',
               f"**Mechanism criterion:** {p.get('mechanism_criterion','—')}",
               '']
        ex = p.get('exemplar_cluster_ids', [])
        if ex:
            md.append(f"**Exemplar clusters:** {', '.join(ex)}")
        md.append('')

    notes = parsed.get('notes')
    if notes:
        md += ['## Notes', '', notes, '']

    OUT_MD.write_text('\n'.join(md))
    proc = subprocess.run(
        [sys.executable, MD2HTML, 'v2 extended parent set',
         f'Broad Learnings · {len(parents)} parents from 59-rep ensemble + boundary extension'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    OUT_HTML.write_text(proc.stdout)
    print(f"wrote {OUT_JSON}, {OUT_MD}, {OUT_HTML}")


if __name__ == '__main__':
    main()
