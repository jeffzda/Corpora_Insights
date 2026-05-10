#!/usr/bin/env python3
"""v2 parent-set consolidation — single Opus call covering two tasks:

  1. Consolidate the 43 core mechanism classes (≥90% rep agreement in
     the 59-rep deliberation-rich ensemble) into final v2 parent
     definitions: canonical name, description, mechanism criterion,
     exemplar_cluster_ids.

  2. Judge the 28 high-tier classes (70-89% rep agreement) for
     promote-to-v2 / hold-for-tier2 / merge-into-existing-parent
     verdicts with reasoning.

Same model end-to-end (Opus 4.7) for consistency. Single call so the
model can see core parents already accepted while judging high-tier.

Output:
  closure/output/parent_derivation_clean_ensemble/v2_parents.{json,md,html}
"""
from __future__ import annotations
import json, time, subprocess, sys, re
from collections import Counter, defaultdict
from pathlib import Path
import anthropic

ROOT = Path(__file__).resolve().parents[2]
PARSED = ROOT/'closure/output/parent_derivation_clean_ensemble/parsed_runs.jsonl'
AGGREGATE = ROOT/'closure/output/parent_derivation_clean_ensemble/ensemble_aggregate.json'
OUT_DIR = ROOT/'closure/output/parent_derivation_clean_ensemble'
OUT_RAW = OUT_DIR/'v2_consolidation.raw.txt'
OUT_JSON = OUT_DIR/'v2_parents.json'
OUT_MD = OUT_DIR/'v2_parents.md'
OUT_HTML = OUT_DIR/'v2_parents.html'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 32000


PROMPT_TEMPLATE = """# v2 parent-set consolidation

You are finalising the v2 parent-archetype taxonomy for an ARENA failure-mode mechanism corpus. The 59-rep deliberation-rich derivation ensemble produced two cohorts of mechanism classes that need decisions:

- **Core cohort ({n_core} classes, ≥90% rep agreement):** these are accepted as v2 parents. Your task is to produce the final canonical name, 2-4 sentence description, one-sentence mechanism criterion, and 3-5 exemplar_cluster_ids for each. Use the evidence below — the candidate names, criteria, and most-frequently-cited cluster_ids that reps proposed.

- **High-tier cohort ({n_high} classes, 70-89% rep agreement):** these are candidates that didn't reach core consensus but are well-supported. For each, return a verdict: `promote` (treat as v2 parent equivalent to core), `hold_for_tier2` (defer to a future v2.1 expansion), or `merge_into_<parent_id>` (subsume into an existing core parent — specify which).

## Audience

The v2 parent set serves an ARENA portfolio manager as a navigable diagnostic vocabulary. The PM scans parent names + criteria to surface every important failure mechanism that could plausibly arise within their project. Optimise canonical names + criteria for that scan-by-glance use.

## Output

Strict JSON, no preamble:

```json
{{
  "core_consolidations": [
    {{
      "class_id": "<from input>",
      "parent_id": "p01",
      "name": "<canonical name, 3-7 words>",
      "description": "<2-4 sentences naming the mechanism class and the membership criterion>",
      "mechanism_criterion": "<one sentence: what must be true of a member's mechanism for it to belong here>",
      "exemplar_cluster_ids": ["<3-5 cluster_ids, picking the most-frequently-cited ones from the evidence>"]
    }}
  ],
  "high_tier_judgements": [
    {{
      "class_id": "<from input>",
      "verdict": "promote | hold_for_tier2 | merge_into_pNN",
      "reason": "<one sentence>"
    }}
  ],
  "notes": "<optional: structural observations about the v2 set, redundancy patterns within the core, or limitations>"
}}
```

Constraints on output:
- `core_consolidations` must have exactly {n_core} entries, one per input core class, in input order.
- `parent_id` should be assigned p01, p02, ... in your output order — choose an order that groups thematically-related parents (e.g. data/measurement family, regulatory family, market/economic family).
- `high_tier_judgements` must have exactly {n_high} entries, one per input high-tier class.
- Where `verdict` is `merge_into_<parent_id>`, the parent_id must be one you've assigned in `core_consolidations`.
- `name` and `mechanism_criterion` must be derived from the evidence — pick from candidate phrasings or synthesise from the criteria observed across the reps. Do not invent new mechanisms not represented in the evidence.

## Input

Each entry is a Jaccard-grouped mechanism class with:
- `class_id`: synthetic ID for this consolidation pass
- `n_reps`: how many of 59 reps proposed a parent matching this class
- `candidate_names`: the distinct name phrasings across reps (most common first)
- `candidate_criteria`: distinct criterion phrasings (most common first, top 5)
- `top_exemplar_cluster_ids`: most-frequently-cited cluster_ids across member labels (top 8)

### Core cohort ({n_core} classes, ≥{core_min_reps}/59 reps each)

{core_block}

### High-tier cohort ({n_high} classes, {high_min_reps}-{high_max_reps}/59 reps each)

{high_block}
"""


def main():
    # Load all 59 reps
    all_reps = [json.loads(l) for l in PARSED.open()]
    print(f"loaded {len(all_reps)} reps", flush=True)

    # Recluster mechanism classes (same Jaccard ≥0.30 method as script 38)
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

    # Filter by tier
    n_reps = len(all_reps)
    core = [c for c in classes if len(c['runs'])/n_reps >= 0.90]
    high = [c for c in classes if 0.70 <= len(c['runs'])/n_reps < 0.90]
    print(f"core (≥90%): {len(core)}, high (70-89%): {len(high)}", flush=True)

    # Build evidence per class
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
            'candidate_names': [n for n, _ in names.most_common(8)],
            'candidate_criteria': [cr for cr, _ in crits.most_common(5)],
            'top_exemplar_cluster_ids': [cid for cid, _ in exemplars.most_common(8)],
        }

    core_summaries = [class_summary(c, i+1, 'core') for i, c in enumerate(core)]
    high_summaries = [class_summary(c, i+1, 'high') for i, c in enumerate(high)]

    def fmt(s):
        lines = [f"\n[{s['class_id']}] n_reps={s['n_reps']}/59"]
        lines.append(f"  candidate_names ({len(s['candidate_names'])}): " + ' || '.join(s['candidate_names'][:6]))
        lines.append(f"  candidate_criteria (top 3): " + ' || '.join(s['candidate_criteria'][:3]))
        lines.append(f"  top_exemplar_cluster_ids: " + ', '.join(s['top_exemplar_cluster_ids']))
        return '\n'.join(lines)

    core_block = '\n'.join(fmt(s) for s in core_summaries)
    high_block = '\n'.join(fmt(s) for s in high_summaries)

    prompt = PROMPT_TEMPLATE.format(
        n_core=len(core_summaries),
        n_high=len(high_summaries),
        core_min_reps=int(0.90 * 59),
        high_min_reps=int(0.70 * 59),
        high_max_reps=int(0.89 * 59),
        core_block=core_block,
        high_block=high_block,
    )
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

    cores = parsed.get('core_consolidations', [])
    judgements = parsed.get('high_tier_judgements', [])
    print(f"\ncore consolidations: {len(cores)}, high-tier judgements: {len(judgements)}", flush=True)

    # Verdict tally
    verdict_counts = Counter()
    for j in judgements:
        v = j.get('verdict','?')
        if v.startswith('merge_into'): v = 'merge_into_*'
        verdict_counts[v] += 1

    json.dump({
        'model': MODEL, 'cost': round(cost,3), 'wall_seconds': round(wall,1),
        'input_tokens': msg.usage.input_tokens, 'output_tokens': msg.usage.output_tokens,
        'n_core': len(cores), 'n_high': len(judgements),
        'verdict_counts': dict(verdict_counts),
        'consolidation': parsed,
    }, open(OUT_JSON,'w'), indent=2)

    # MD report
    md = ['# v2 parent set — consolidated from 59-rep ensemble',
          '',
          f'Single Opus 4.7 call. 43 core mechanism classes (≥90% rep agreement) consolidated into final v2 parent definitions; 28 high-tier classes (70-89%) judged for promote/hold/merge.',
          '',
          f'**Cost:** ${cost:.2f}, {wall:.0f}s wall.',
          '',
          f'**v2 core parents:** {len(cores)}',
          f'**High-tier verdicts:** {dict(verdict_counts)}',
          '',
          '## v2 Parent definitions (core)',
          '',
          '| parent | name | mechanism criterion |',
          '|---|---|---|']
    for c in cores:
        md.append(f"| {c.get('parent_id','?')} | {c.get('name','?')} | {c.get('mechanism_criterion','—')[:100]} |")
    md.append('')
    md.append('### Full descriptions')
    md.append('')
    for c in cores:
        md.append(f"#### {c.get('parent_id','?')} — {c.get('name','?')}")
        md.append('')
        md.append(c.get('description',''))
        md.append('')
        md.append(f"**Mechanism criterion:** {c.get('mechanism_criterion','—')}")
        md.append('')
        ex = c.get('exemplar_cluster_ids', [])
        if ex:
            md.append(f"**Exemplar clusters:** {', '.join(ex)}")
        md.append('')

    md += ['', '## High-tier verdicts (28 candidates)', '',
           '| class | verdict | reason |',
           '|---|---|---|']
    for j in judgements:
        md.append(f"| {j.get('class_id','?')} | {j.get('verdict','?')} | {j.get('reason','')} |")

    notes = parsed.get('notes')
    if notes:
        md += ['', '## Notes', '', notes]

    OUT_MD.write_text('\n'.join(md))
    proc = subprocess.run(
        [sys.executable, MD2HTML, 'v2 parent set — consolidated from 59-rep ensemble',
         f'Broad Learnings · {len(cores)} core parents + {len(judgements)} high-tier judgements'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    OUT_HTML.write_text(proc.stdout)

    print(f"\nwrote {OUT_JSON}, {OUT_MD}, {OUT_HTML}")
    print(f"cost: ${cost:.3f}")


if __name__ == '__main__':
    main()
