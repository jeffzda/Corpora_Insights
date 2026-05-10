#!/usr/bin/env python3
"""Closure phase 3: extract clusters whose mechanism is NOT renewable-energy specific.

Reads the entire 1,141-cluster catalogue and asks Opus 4.7 to classify each
cluster's mechanism as either:
  - "general": the causal pathway applies broadly beyond renewable energy
    (e.g., to any infrastructure project, any policy domain, any organisation)
  - "tech_specific": the causal pathway depends on physics/equipment/markets
    specific to renewable energy or its regulatory environment

For "general" clusters, also tag the broader domain(s) the mechanism applies
to (e.g., "infrastructure project management", "novel-technology adoption",
"public-private coordination", "regulatory framework design").

This is the substrate-extraction step: identifying the mechanism vocabulary
that transfers to ANAO, PC, APH, and other infrastructure corpora — the
universal grammar of failure modes that the ARENA corpus served as evidence
for but isn't bound to.

Output: general_mechanisms.json — list of cluster classifications with tags.
Cost: ~$1.50-2 sync.
"""
import argparse
import json
import re
import time
from pathlib import Path

import anthropic

V2_OUT = Path(__file__).resolve().parents[2] / 'output'
CLOSURE_OUT = Path(__file__).resolve().parent.parent / 'output'
CATALOGUE = V2_OUT / 'sweep' / 'convergence' / 'catalogue_after_convergence.json'
OUT_FILE = CLOSURE_OUT / 'general_mechanisms.json'
RAW_OUT = CLOSURE_OUT / 'general_mechanisms_raw.txt'
META_OUT = CLOSURE_OUT / 'general_mechanisms_meta.json'


PROMPT_HEADER = """You are reviewing a catalogue of failure-mode clusters extracted from a corpus of renewable-energy project deliverables (ARENA Knowledge Bank). Each cluster has a canonical name and a mechanism signature describing a causal pathway.

Your task: for each cluster, decide whether the underlying causal mechanism is GENERAL (applies broadly beyond renewable energy — to any infrastructure project, any policy program, any organisational coordination problem, any novel-technology adoption context, etc.) or TECH-SPECIFIC (depends on physics, equipment, market structure, or regulation that is specific to renewable energy and its grid/market context).

Examples of the distinction:
- "Multi-party coordination overhead delays project delivery" → GENERAL (applies to any multi-stakeholder project)
- "Inverter fault current incompatibility with protection schemes" → TECH-SPECIFIC (specific to grid-connected power electronics)
- "Pre-specified outcomes limit innovation learning" → GENERAL (applies to any innovation-funded program)
- "Perovskite ion migration causes measurement artefacts" → TECH-SPECIFIC (specific to a PV cell technology)
- "Community opposition risk from inadequate engagement" → GENERAL (applies to any large infrastructure project)
- "FCAS revenue compression reducing battery business case" → TECH-SPECIFIC (specific to a particular electricity-market product)
- "Modeller familiarity bias constrains scenario range" → GENERAL (applies to any modelling exercise)
- "Grid-forming inverter additional tuning complexity" → TECH-SPECIFIC

For each GENERAL cluster, also list the broader domain(s) the mechanism applies to. Use 1-3 short tags from a vocabulary like:
  infrastructure_project_delivery, novel_technology_adoption, public_private_coordination,
  regulatory_framework_design, financial_incentive_design, community_engagement,
  organisational_coordination, modelling_methodology, supply_chain, contracts_legal,
  data_systems_integration, capacity_building, program_design, market_structure,
  innovation_funding, lab_to_field_translation, equipment_lifecycle, safety_governance

You may use other tags if these don't fit, but prefer the ones above when they apply.

# CATALOGUE
"""

PROMPT_FOOTER = """\

# OUTPUT FORMAT — STRICT

Return JSON only. First character `{`, last character `}`. No preamble, no markdown fences.

Schema:
{
  "classifications": [
    {"cluster_id": "c001", "scope": "tech_specific"},
    {"cluster_id": "c002", "scope": "general", "domains": ["infrastructure_project_delivery", "regulatory_framework_design"]},
    ...
  ]
}

Every cluster_id from the catalogue must appear exactly once. For tech_specific clusters, omit the "domains" field. For general clusters, include 1-3 domain tags."""


def stream_call(client, prompt, model, max_tokens=64000, raw_path=None):
    raw_f = open(raw_path, 'w') if raw_path else None
    started = time.time()
    last_print = 0; last_chars = 0; text_chars = 0
    parts = []; msg = None
    try:
        with client.messages.stream(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for ev in stream.text_stream:
                if raw_f: raw_f.write(ev); raw_f.flush()
                parts.append(ev); text_chars += len(ev)
                now = time.time()
                if now - last_print >= 5:
                    rate = (text_chars - last_chars) / max(now - last_print, 1)
                    print(f"  [{int(now - started)}s] {text_chars:,} chars  +{rate:.0f} c/s",
                          flush=True)
                    last_print = now; last_chars = text_chars
            msg = stream.get_final_message()
    finally:
        if raw_f: raw_f.close()
    return ''.join(parts), msg


def parse_response(text):
    text = text.strip()
    m = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
    body = m.group(1).strip() if m else text
    first = body.find('{'); last = body.rfind('}')
    if first >= 0 and last > first:
        try: return json.loads(body[first:last+1])
        except: pass
    # Tolerant: extract complete classification objects
    objs = []
    for m in re.finditer(r'\{\s*"cluster_id"\s*:\s*"([^"]+)"\s*,\s*"scope"\s*:\s*"(general|tech_specific)"(?:\s*,\s*"domains"\s*:\s*(\[[^\]]*\]))?\s*\}', body, re.DOTALL):
        try:
            cid = m.group(1); scope = m.group(2)
            obj = {'cluster_id': cid, 'scope': scope}
            if scope == 'general' and m.group(3):
                obj['domains'] = json.loads(m.group(3))
            objs.append(obj)
        except: pass
    return {'classifications': objs, '_recovered': True} if objs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='claude-opus-4-7')
    args = ap.parse_args()

    print(f"Loading catalogue from {CATALOGUE}", flush=True)
    catalogue = json.load(open(CATALOGUE))['clusters']
    cid_to_meta = {c['cluster_id']: c for c in catalogue}
    print(f"  {len(catalogue)} clusters", flush=True)

    block_lines = []
    for c in catalogue:
        block_lines.append(f"\n[{c['cluster_id']}] {c['canonical_name']}")
        block_lines.append(f"  mechanism: {c.get('mechanism_signature','')}")
    prompt = PROMPT_HEADER + ''.join(block_lines) + PROMPT_FOOTER
    print(f"  prompt size: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"\nCalling {args.model}...", flush=True)
    t0 = time.time()
    text, msg = stream_call(client, prompt, args.model, raw_path=RAW_OUT)
    wall = time.time() - t0
    print(f"\n  generation done: {len(text):,} chars in {wall:.0f}s", flush=True)
    in_p = 15 if 'opus' in args.model else 3
    out_p = 75 if 'opus' in args.model else 15
    cost = msg.usage.input_tokens/1e6*in_p + msg.usage.output_tokens/1e6*out_p
    print(f"  tokens: {msg.usage.input_tokens:,}in / {msg.usage.output_tokens:,}out  cost ${cost:.3f}", flush=True)

    parsed = parse_response(text)
    classes = (parsed or {}).get('classifications') or []
    print(f"  parsed: {len(classes)} classifications", flush=True)

    valid_ids = {c['cluster_id'] for c in catalogue}
    cleaned = []
    seen = set()
    for c in classes:
        cid = c.get('cluster_id')
        if cid in valid_ids and cid not in seen:
            seen.add(cid)
            obj = {'cluster_id': cid, 'scope': c.get('scope')}
            if obj['scope'] == 'general' and c.get('domains'):
                obj['domains'] = c['domains']
            obj['canonical_name'] = cid_to_meta[cid]['canonical_name']
            cleaned.append(obj)
    missing = valid_ids - seen
    print(f"  unique cluster classifications: {len(cleaned)}; missing: {len(missing)}", flush=True)

    OUT_FILE.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False))
    META_OUT.write_text(json.dumps({
        'model': args.model,
        'input_tokens': msg.usage.input_tokens,
        'output_tokens': msg.usage.output_tokens,
        'cost_sync': round(cost, 3),
        'wall_seconds': round(wall, 1),
        'n_classified': len(cleaned),
        'n_missing': len(missing),
        'n_general': sum(1 for c in cleaned if c['scope'] == 'general'),
        'n_tech_specific': sum(1 for c in cleaned if c['scope'] == 'tech_specific'),
    }, indent=2))

    n_gen = sum(1 for c in cleaned if c['scope']=='general')
    n_tech = sum(1 for c in cleaned if c['scope']=='tech_specific')
    print(f"\n=== DONE ===")
    print(f"  General mechanisms: {n_gen} ({100*n_gen/len(cleaned):.1f}%)")
    print(f"  Tech-specific: {n_tech} ({100*n_tech/len(cleaned):.1f}%)")
    if missing:
        print(f"  Missing classifications: {len(missing)}")
        print(f"    sample: {sorted(missing)[:10]}")

    # Domain frequency among general
    from collections import Counter
    domain_freq = Counter()
    for c in cleaned:
        if c['scope'] == 'general':
            for d in (c.get('domains') or []):
                domain_freq[d] += 1
    print(f"\n  Top domain tags among general clusters:")
    for d, n in domain_freq.most_common(20):
        print(f"    {n:>4}  {d}")


if __name__ == "__main__":
    main()
