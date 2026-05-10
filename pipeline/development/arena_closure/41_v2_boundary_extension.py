#!/usr/bin/env python3
"""v2 boundary-tier extension — judge the 25 boundary-tier (40-69%)
mechanism classes against the existing 70-parent v2 set, with
promote/hold/merge verdicts.

Closes the methodological gap that the original v2 consolidation only
saw core (≥90%) + high-tier (70-89%) cohorts; the boundary tier was
never shown to the model.

Output:
  closure/output/parent_derivation_clean_ensemble/v2_boundary_extension.{json,md,html}
"""
from __future__ import annotations
import json, time, subprocess, sys, re
from collections import Counter
from pathlib import Path
import anthropic

ROOT = Path(__file__).resolve().parents[2]
PARSED = ROOT/'closure/output/parent_derivation_clean_ensemble/parsed_runs.jsonl'
V2 = ROOT/'closure/output/parent_derivation_clean_ensemble/v2_parents.json'
OUT_DIR = ROOT/'closure/output/parent_derivation_clean_ensemble'
OUT_RAW = OUT_DIR/'v2_boundary_extension.raw.txt'
OUT_JSON = OUT_DIR/'v2_boundary_extension.json'
OUT_MD = OUT_DIR/'v2_boundary_extension.md'
OUT_HTML = OUT_DIR/'v2_boundary_extension.html'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 32000


PROMPT = """# v2 boundary-tier extension

The v2 ARENA failure-mechanism parent taxonomy currently has 70 parents (43 core ≥90% rep agreement + 27 promoted high-tier 70-89%) derived from a 59-rep deliberation-rich ensemble.

A third tier — **boundary classes (40-69% rep agreement)** — was excluded from the original consolidation by threshold. The model was never shown them. Your task is to judge each one explicitly.

For each boundary class, return a verdict:
- `promote`: the mechanism is structurally distinct from existing v2 parents and worth adding as a new parent. Provide a name + mechanism criterion in the v2 style.
- `merge_into_<v2_id>`: the mechanism is already covered by an existing v2 parent; specify which.
- `reject`: the mechanism is too narrow, too overlapping, or insufficiently mechanism-class-like to warrant a parent. Provide a one-sentence reason.

## Audience

The v2 parent set serves an ARENA portfolio manager as a navigable diagnostic vocabulary. The PM scans parent names + criteria to surface every important failure mechanism that could plausibly arise within their project. Optimise for that scan-by-glance use — be discriminating: only `promote` if the mechanism is genuinely distinct from every existing v2 parent and a PM would want it as a separate diagnostic axis.

## Output

Strict JSON, no preamble:

```json
{{
  "boundary_judgements": [
    {{
      "class_id": "<from input>",
      "verdict": "promote | merge_into_pNN | reject",
      "name": "<if promote: 3-7 word canonical name>",
      "mechanism_criterion": "<if promote: one sentence>",
      "reason": "<one sentence on why this verdict>"
    }}
  ],
  "notes": "<optional structural observations>"
}}
```

Constraints:
- Exactly {n_boundary} entries, one per input class.
- `merge_into_<id>` must reference one of the v2 parent IDs in the rubric below.
- A `promote` verdict adds a new parent — be conservative; the boundary tier had only 40-69% rep agreement, so the bar should be: would a PM scanning v2 hit a real blind spot without this?

## Existing v2 parent set ({n_v2_parents} parents)

{v2_block}

## Boundary classes to judge ({n_boundary} classes, {min_reps}-{max_reps}/59 reps each)

Each entry:
- `class_id`: synthetic ID
- `n_reps`: how many of 59 reps proposed a parent matching this class
- `candidate_names`: distinct phrasings (most common first, top 6)
- `candidate_criteria`: distinct criterion phrasings (top 3)
- `top_exemplar_cluster_ids`: most-frequently-cited cluster_ids (top 8)

{boundary_block}
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
    boundary = [c for c in classes if 0.40 <= len(c['runs'])/n_reps < 0.70]
    print(f"boundary (40-69%): {len(boundary)}", flush=True)

    def class_summary(c, idx):
        names = Counter(l['name'] for l in c['labels'])
        crits = Counter(l['criterion'] for l in c['labels'])
        exemplars = Counter()
        for l in c['labels']:
            for cid in l['exemplar_cluster_ids']:
                exemplars[cid] += 1
        return {
            'class_id': f'bdry_{idx:02d}',
            'n_reps': len(c['runs']),
            'candidate_names': [n for n, _ in names.most_common(6)],
            'candidate_criteria': [cr for cr, _ in crits.most_common(3)],
            'top_exemplar_cluster_ids': [cid for cid, _ in exemplars.most_common(8)],
        }

    bdry = [class_summary(c, i+1) for i, c in enumerate(boundary)]

    # Build v2 parent rubric
    v2j = json.load(V2.open())
    cores = v2j['consolidation']['core_consolidations']
    high = [h for h in v2j['consolidation']['high_tier_judgements'] if h['verdict']=='promote']
    v2_lines = []
    for p in cores:
        v2_lines.append(f"  [{p['parent_id']}] {p['name']} — {p.get('mechanism_criterion','')}")
    for h in high:
        v2_lines.append(f"  [{h['class_id']}] (promoted) — {h.get('reason','')}")
    v2_block = '\n'.join(v2_lines)

    def fmt(s):
        lines = [f"\n[{s['class_id']}] n_reps={s['n_reps']}/59"]
        lines.append(f"  candidate_names: " + ' || '.join(s['candidate_names'][:6]))
        lines.append(f"  candidate_criteria (top 3): " + ' || '.join(s['candidate_criteria'][:3]))
        lines.append(f"  top_exemplar_cluster_ids: " + ', '.join(s['top_exemplar_cluster_ids']))
        return '\n'.join(lines)

    boundary_block = '\n'.join(fmt(s) for s in bdry)
    rep_counts = [s['n_reps'] for s in bdry]

    prompt = PROMPT.format(
        n_boundary=len(bdry),
        n_v2_parents=len(cores)+len(high),
        v2_block=v2_block,
        min_reps=min(rep_counts) if rep_counts else 0,
        max_reps=max(rep_counts) if rep_counts else 0,
        boundary_block=boundary_block,
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
    print(f"done: {wall:.0f}s, {msg.usage.input_tokens:,}in/{msg.usage.output_tokens:,}out ${cost:.3f}", flush=True)

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

    js = parsed.get('boundary_judgements', [])
    vc = Counter()
    for j in js:
        v = j.get('verdict','?')
        if v.startswith('merge_into'): v = 'merge_into_*'
        vc[v] += 1
    print(f"verdicts: {dict(vc)}", flush=True)

    json.dump({
        'model': MODEL, 'cost': round(cost,3), 'wall_seconds': round(wall,1),
        'input_tokens': msg.usage.input_tokens, 'output_tokens': msg.usage.output_tokens,
        'n_boundary': len(js),
        'verdict_counts': dict(vc),
        'judgements': parsed,
    }, open(OUT_JSON,'w'), indent=2)

    md = ['# v2 boundary-tier extension', '',
          f'Single Opus 4.7 call. 25 boundary-tier (40-69% rep agreement) mechanism classes judged against the existing 70-parent v2 set.',
          f'**Cost:** ${cost:.2f}, {wall:.0f}s wall.', '',
          f'**Verdicts:** {dict(vc)}', '',
          '| class | n_reps | verdict | name (if promote) | reason |',
          '|---|---|---|---|---|']
    bdry_by_id = {s['class_id']: s for s in bdry}
    for j in js:
        cid = j.get('class_id','?')
        n = bdry_by_id.get(cid,{}).get('n_reps','?')
        md.append(f"| {cid} | {n}/59 | {j.get('verdict','?')} | {j.get('name','')} | {j.get('reason','')} |")
    notes = parsed.get('notes')
    if notes:
        md += ['', '## Notes', '', notes]

    OUT_MD.write_text('\n'.join(md))
    proc = subprocess.run(
        [sys.executable, MD2HTML, 'v2 boundary-tier extension',
         f'Broad Learnings · 25 boundary classes judged'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    OUT_HTML.write_text(proc.stdout)
    print(f"wrote {OUT_JSON}, {OUT_MD}, {OUT_HTML}")


if __name__ == '__main__':
    main()
