#!/usr/bin/env python3
"""Closure phase 4: Generate a synthesis report on a single failure-mode cluster.

Prototype for cluster-level documentation. Given a target cluster_id, this:

1. Pulls every record assigned to the cluster (from corpus_assignments.jsonl)
2. Joins each record's project to project-level metadata from arena-projects-export
3. For each record's event_id, finds OTHER records that belong to the same event
   (across the whole filter_input pool, not restricted to this cluster) and
   labels them as "event siblings" — they describe a different aspect of the
   same incident/decision/programme
4. Sends the full assembled context to Opus 4.7 with a synthesis prompt
5. Saves the report as Markdown

Output target: a portfolio-review-grade report that synthesises across records
and events, with citations, without leaning on direct quotation. Report-style
but readable.

Cost per cluster: ~$0.50-1.50 sync depending on cluster size and event-sibling
expansion. Not viable to run on all 1,141 clusters, but useful for high-
interest clusters in the methodology paper or any spotlight write-up.
"""
import argparse
import csv
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import anthropic

MD2HTML = Path('/home/jeffzda/broadlearnings/tools/md2html')

V2_OUT = Path(__file__).resolve().parents[2] / 'output'
CLOSURE_OUT = Path(__file__).resolve().parent.parent / 'output'
CATALOGUE = V2_OUT / 'sweep' / 'convergence' / 'catalogue_after_convergence.json'
# Assignment layers in chronological order — later passes override earlier ones
# for a given record_id. Mirrors tools/q's ASSIGN_LAYERS so cluster
# membership is consistent across the codebase. Earlier code only loaded the
# first layer, which left ~35% of records out of cluster reports. Fix 2026-05-04.
ASSIGN_LAYERS = [
    V2_OUT / 'sweep' / 'corpus_assignments.jsonl',
    V2_OUT / 'sweep' / 'reclassify' / 'reclassified_assignments.jsonl',
    V2_OUT / 'sweep' / 'third_pass' / 'third_pass_assignments.jsonl',
    V2_OUT / 'sweep' / 'residual' / 'residual_assignments.jsonl',
    V2_OUT / 'sweep' / 'convergence' / 'convergence_assignments.jsonl',
]
INPUT = V2_OUT / 'filter_input.jsonl'
PROJECTS_CSV = Path('/home/jeffzda/broadlearnings/corpora/arena/portfolio.csv')  # canonical projects file (refreshed by domains/arena/scrape_incremental.py)
PER_DOC_DIR = Path('/home/jeffzda/broadlearnings/corpora/arena/output/per_doc')  # rich per-record metadata source (kb_publish_date, kb_year, kb_document_type, source_title, pages, pdf_url)

REPORT_DIR = CLOSURE_OUT / 'cluster_reports'
REPORT_DIR.mkdir(exist_ok=True)


PROMPT_TEMPLATE = """You are writing a portfolio-review report for ARENA (Australian Renewable Energy Agency) on a specific failure-mode cluster identified in their project corpus. Your audience is a senior portfolio manager who already understands ARENA's mandate but wants a clear, synthesis-grade write-up of how this particular failure pattern has manifested across the portfolio.

# CLUSTER UNDER REVIEW

Cluster ID: {cluster_id}
Canonical name: {cluster_name}
Mechanism signature: {cluster_signature}
Records in cluster: {n_records}
Unique projects: {n_projects}
Distinct ARENA categories represented: {n_categories}

# EVIDENCE BASE

Below is the full evidence base assembled for this report. Four layers:

1. **Temporal range**: the project-year and publish-year span of the records, summarised at the top of the evidence block.
2. **Cluster records**: every record assigned to this cluster, with the originating project, the source document title, the project year (when the work happened), the publish date (when the document was released), and the document type. Records within each project are sorted oldest project-year first.
3. **Project metadata**: for each project that contributed records, the project's title, ARENA category, lead organisation, ARENA funding, total project value, location, status, and ARENA programme.
4. **Event siblings**: where a cluster record belongs to an event with other records (in this or other clusters), those sibling records are listed with a note on their cluster placement, source title, and timing. These describe different aspects of the same incident/decision/programme, providing fuller context.

{evidence_block}

# TIME-VARIANT FACTORS — IMPORTANT

Most failure-mode mechanisms in this corpus are **time-variant**: their salience, scale, and even their *existence* depend on the state of the market, the regulatory environment, technology cost curves, deployment penetration, or counterparty maturity at the time the project was operating. A claim about *current* applicability of a mechanism is different from a claim about its *historical* manifestation.

Two date fields per record matter:
- **`project year`** = when the project was actually operating. This dates the *underlying conditions* — market structure, regulatory rules, available technology, counterparty landscape. Use this to date the mechanism's *cause*.
- **`publish date`** = when ARENA released the document. This dates the *interpretation* — what was understood at write-up time. Often 1–5 years later than the project year.

When the two diverge significantly, both dates are relevant and you should note that distinction in your synthesis.

A worked example of why this matters: a 2018-vintage finding about FCAS revenue compression (Hornsdale Power Reserve effect) reflects a market that was structurally *thin* — few qualified providers, marginal cost near zero, prices that compressed sharply with each new entrant. By 2024, the market structure has changed (more participants, different rule set, different price formation dynamics). A synthesis that treats the 2018 mechanism as a present-tense claim without naming its temporal scope misleads the portfolio manager. The mechanism *as historical pattern* is robustly evidenced; whether it *currently still operates with the same intensity* is a separate question that depends on the current market state.

For each claim you make in the synthesis, ask: is this a claim about a *time-bound condition* (e.g. "the FCAS market was thin in 2017–2019") or a *time-invariant mechanism* (e.g. "shallow ancillary-service markets compress prices as new entrants arrive"). Time-bound claims should explicitly cite the period they refer to. Time-invariant mechanisms can stand without temporal qualification, but their *manifestation* in the corpus is bounded by the dates of the evidence.

Where evidence spans many years, look for whether the mechanism has *evolved* over time — is it more or less salient in recent records than older ones? That trajectory is itself a finding.

# TASK

Write a synthesis report on this failure archetype. Required elements:

1. **Opening framing**: one or two paragraphs naming the mechanism in plain language, why it matters for an ARENA-style infrastructure-investment portfolio, and the scale and *temporal range* of its presence in the corpus.

2. **The mechanism itself**: a careful articulation of the causal pathway — what conditions create the vulnerability, what the proximate failure looks like, and what makes it distinct from adjacent mechanisms. Where the mechanism depends on market/regulatory/technology state, name those dependencies and the period they applied to.

3. **How it manifests across the portfolio**: synthesis (not a list) of the patterns of manifestation. Where does it show up? In which technologies? At what stages of project lifecycle? **Across what time period?** Are there sub-patterns, including temporal sub-patterns (e.g. older records show one variant, newer records show another)? Cite specific records using **superscript reference numbers** (see Citation format below). Project names appear inline as `[Project Title]` without a number — they're contextual labels rather than bibliographic citations. Do NOT quote source text. Describe and synthesise rather than excerpt.

4. **Project-level context** where instructive. The records sit inside projects with their own structure, funding, scale, stakeholders — and operating period. Note where this context illuminates *why* this mechanism arose for that project specifically and at that time.

5. **Event-level context** where event siblings add to the story.

6. **Temporal-trajectory observations** — explicitly: how does the evidence date-range shape the claim? Is the mechanism likely still operating with the same intensity now, or has the underlying market/regulatory state shifted? If the corpus only contains older records, name that limitation. If newer records modify or moderate older findings, surface that.

7. **Mitigation patterns observed**: from the records themselves, what mitigations or workarounds have been proposed or attempted? Note whether mitigation effectiveness itself is time-variant (some mitigations only work under particular regulatory configurations).

8. **Implications for portfolio decisions**: what would a portfolio manager do differently knowing this archetype is real and pervasive — and given its temporal scope? Be specific. Where the mechanism's current applicability is uncertain (because evidence is older), say so and recommend what would update the picture.

9. **Open questions or evidence gaps**: what does this corpus *not* tell us about this archetype? What further evidence would sharpen the picture? Are there gaps in the temporal coverage that matter?

Style:
- Report-style, prose-heavy, not bulleted unless a bullet helps
- Do NOT quote source text directly — synthesise
- When citing time-bound claims, include the period (e.g. "in 2017–2019, when the FCAS market was structurally thin..." rather than just "FCAS markets are thin")
- Keep it interesting — connect the mechanism to broader patterns where relevant (other industries, classical economics/management/engineering analogies, etc.) where it sharpens the insight
- Length: aim for 1500-2500 words for the body, plus the references section. Substance over length.

# CITATION FORMAT

Cite specific records using **HTML superscript tags** with the reference number, like this:

> The FCAS regulation market is structurally thin at roughly 210–220 MW<sup>1</sup>, and a single 100 MW battery can saturate it<sup>1,3</sup>.

Numbering rules:
- Number references in **order of first appearance** in the body.
- **Reuse the same number** for repeat citations of the same record.
- Multiple citations on one claim go inside one `<sup>` separated by commas, e.g. `<sup>1,3,7</sup>`.
- Do NOT use `[c016/ARENA-DLV-NNNN-NN]` form anywhere in the body — that goes in the references section only.
- Project titles remain inline as `[Project Name]` *without* a superscript number — projects are contextual labels.
- Event siblings, when cited, get their own reference number on the same numbering line.

At the end of the report, immediately after the body, include a `## References` section listing every cited record in numeric order, one per line, in this exact format:

```
1. **ARENA-DLV-1086-0057** — *Large-Scale Battery Storage Knowledge Sharing Report* (Reports/Insights, project year 2018, published 25/09/2019, p. 28). [Source page](https://arena.gov.au/knowledge-bank/...) · [PDF](https://arena.gov.au/assets/...)
2. **ARENA-DLV-0254-0016** — *ARENA Insights Forum Presentation Summaries & Key Points — Large-Scale Projects Stream* (Reports, project year 2018, published 25/06/2019, p. 3). [Source page](https://...) · [PDF](https://...)
```

Field-by-field requirements for each reference line:
1. Number followed by `.` and a space.
2. **Bold record_id** (the `ARENA-DLV-NNNN-NN` form).
3. ` — ` (em-dash with spaces).
4. *Italic source title* — the document's title as it appears in `source_title:` in the evidence block.
5. Parenthetical context, comma-separated: document type, project year (if known), publish date, page numbers (if known). Skip any field that's missing in the metadata; don't invent values.
6. ` ` then `[Source page](URL)` linking to `source_url` from the evidence block.
7. ` · ` separator.
8. `[PDF](URL)` linking to `pdf_url` from the evidence block.
9. If a record has no `source_url` or `pdf_url` in the evidence block, omit that link rather than substituting a placeholder.

Every cited record (anything you've assigned a `<sup>N</sup>` in the body) MUST appear in the references list. Don't list records you didn't cite.

Return only the report Markdown — no preamble, no commentary, no closing notes."""


DOC_META_FIELDS = (
    'kb_publish_date',     # DD/MM/YYYY string — when ARENA released the document
    'kb_year',             # project year (often the project's *operational* year, not publish year — frequently differs by 1-5 years)
    'kb_document_type',    # Reports / Lessons / Milestones / Insights / etc.
    'source_title',        # human-readable document title
    'source_url',          # ARENA KB page for the document (human-friendly entry point)
    'pages',               # list of page numbers the record cites
    'pdf_url',             # direct link to the underlying PDF
    'doc_id',              # doc_NNNN
)


def _load_doc_metadata():
    """Build {record_id: {kb_publish_date, kb_year, kb_document_type, source_title, pages, pdf_url, doc_id}}.

    Reads all per_doc/*.json files. Only the fields in DOC_META_FIELDS are
    retained; per-record narrative/lesson/evidence already come from
    filter_input.jsonl in load_data() so we don't duplicate them.
    """
    doc_meta = {}
    for f in sorted(PER_DOC_DIR.glob('doc_*.json')):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        for rec in d.get('records', []):
            rid = rec.get('id')
            if not rid:
                continue
            doc_meta[rid] = {k: rec.get(k) for k in DOC_META_FIELDS}
    return doc_meta


def load_data():
    catalogue = json.load(open(CATALOGUE))['clusters']
    cid_to_meta = {c['cluster_id']: c for c in catalogue}
    rows = [json.loads(l) for l in open(INPUT)]
    rid_to = {r['record_id']: r for r in rows}
    csv_rows = list(csv.DictReader(open(PROJECTS_CSV)))
    proj_meta = {r['Project']: r for r in csv_rows}
    # Load all assignment layers; later layers override earlier ones for a given record_id.
    rid_to_cluster = {}
    for f in ASSIGN_LAYERS:
        if not f.exists():
            continue
        for line in open(f):
            a = json.loads(line)
            rid_to_cluster[a['record_id']] = a.get('cluster_id')
    cluster_members = defaultdict(list)
    for rid, cid in rid_to_cluster.items():
        if cid:
            cluster_members[cid].append(rid)
    # CRITICAL: event_ids in filter_input.jsonl are per-project local labels
    # that collide globally (e.g. EVT-0001 appears in 179 projects). Scope event
    # membership by (project, event_id) composite key to recover real events.
    event_records = defaultdict(list)
    for r in rows:
        eid = r.get('event_id')
        proj = r.get('project') or ''
        if eid:
            event_records[(proj, eid)].append(r['record_id'])
    # Document-level metadata (publish_date, year, document_type, title, pages, pdf_url)
    # — needed for time-variant analysis in the synthesis prompt.
    doc_meta = _load_doc_metadata()
    return {
        'catalogue': cid_to_meta,
        'records': rid_to,
        'projects': proj_meta,
        'rid_to_cluster': rid_to_cluster,
        'cluster_members': dict(cluster_members),
        'event_records': dict(event_records),  # keyed by (project, event_id)
        'doc_meta': doc_meta,                   # rid → {kb_publish_date, kb_year, ...}
    }


def _publish_year(date_str):
    """Parse 'DD/MM/YYYY' or 'D/M/YYYY' to int year; return None if unparseable."""
    if not date_str:
        return None
    parts = str(date_str).strip().split('/')
    if len(parts) == 3:
        try:
            return int(parts[2])
        except ValueError:
            return None
    return None


def _format_doc_metadata(meta):
    """One-line compact rendering of a record's document metadata."""
    if not meta:
        return ""
    parts = []
    py = meta.get('kb_year')
    pd = meta.get('kb_publish_date')
    if py: parts.append(f"project year {py}")
    if pd: parts.append(f"published {pd}")
    dt = meta.get('kb_document_type')
    if dt: parts.append(dt)
    pages = meta.get('pages')
    if pages and isinstance(pages, list) and pages:
        parts.append(f"p. {','.join(str(p) for p in pages[:3])}")
    return " · ".join(parts)


def build_evidence_block(cluster_id, data, max_event_siblings_per_record=4):
    cm = data['cluster_members'].get(cluster_id, [])
    cluster_records = [data['records'][r] for r in cm if r in data['records']]
    if not cluster_records:
        raise ValueError(f"No records in cluster {cluster_id}")

    # Group by project for clean presentation
    by_project = defaultdict(list)
    for r in cluster_records:
        by_project[r.get('project') or '(no project)'].append(r)

    # Compute corpus-wide temporal range of records in this cluster — used for
    # the time-variant context summary at the top of the evidence block.
    project_years = []
    publish_years = []
    for r in cluster_records:
        m = data['doc_meta'].get(r['record_id'], {})
        py = m.get('kb_year')
        pby = _publish_year(m.get('kb_publish_date'))
        try:
            if py: project_years.append(int(py))
        except (ValueError, TypeError):
            pass
        if pby: publish_years.append(pby)

    lines = []

    # === TEMPORAL RANGE SUMMARY ===
    if project_years or publish_years:
        lines.append("\n## Temporal range of evidence in this cluster\n")
        if project_years:
            lines.append(f"Project years span {min(project_years)}–{max(project_years)} "
                         f"(n={len(project_years)} records have a project year tag)")
        if publish_years:
            lines.append(f"Publish years span {min(publish_years)}–{max(publish_years)} "
                         f"(n={len(publish_years)} records have a publish date)")
        lines.append("\nNote: a record's *project year* is when the project was operating "
                     "(market conditions, regulatory state, costs at that time). The *publish year* "
                     "is when ARENA released the document (often 1–5 years later, reflecting more "
                     "current understanding). Both matter; weight evidence accordingly when making "
                     "claims about current vs historical state.")

    # === CLUSTER RECORDS ===
    lines.append("\n## Cluster records grouped by project\n")
    for proj in sorted(by_project, key=lambda p: -len(by_project[p])):
        recs = by_project[proj]
        meta = data['projects'].get(proj, {})
        lines.append(f"\n### Project: {proj}")
        if meta:
            mlines = []
            for k in ['Category','Lead organisation','Arena program','Status',
                      'Start date','Location','Arena funding provided','Total project value']:
                v = (meta.get(k) or '').strip()
                if v: mlines.append(f"{k}: {v}")
            if mlines:
                lines.append("  " + " | ".join(mlines))
            summary = (meta.get('Summary/Information') or '').strip()
            if summary:
                lines.append(f"  Summary: {summary[:1200]}")
        # Sort records by project_year (oldest first) within the project for narrative flow
        recs_sorted = sorted(recs, key=lambda r: (
            int(data['doc_meta'].get(r['record_id'], {}).get('kb_year') or 0)
            if str(data['doc_meta'].get(r['record_id'], {}).get('kb_year') or '').isdigit()
            else 9999
        ))
        lines.append(f"  Records ({len(recs)}):")
        for r in recs_sorted:
            rid = r['record_id']
            narr = (r.get('narrative') or '').strip()
            evi = (r.get('evidence') or '').strip()
            evi_short = evi[:250] if evi and evi != narr else ''
            doc_meta = data['doc_meta'].get(rid, {})
            timing_line = _format_doc_metadata(doc_meta)
            source_title = (doc_meta.get('source_title') or '').strip()
            source_url = (doc_meta.get('source_url') or '').strip()
            pdf_url = (doc_meta.get('pdf_url') or '').strip()
            lines.append(f"\n  - [{rid}]" + (f"  ({timing_line})" if timing_line else ""))
            if source_title:
                lines.append(f"    source_title: {source_title[:160]}")
            if source_url:
                lines.append(f"    source_url:   {source_url}")
            if pdf_url:
                lines.append(f"    pdf_url:      {pdf_url}")
            lines.append(f"    narrative: {narr[:600]}")
            if evi_short:
                lines.append(f"    evidence: {evi_short}")

    # === EVENT SIBLINGS ===
    # Use (project, event_id) composite key — event_ids in filter_input collide
    # globally (per-project local labels). True siblings share both project and
    # event_id.
    sibling_section = ["\n## Event siblings (records in same event as a cluster record — scoped by project)\n"]
    sibling_count = 0
    seen_siblings = set()
    cluster_member_set = set(cm)
    for r in cluster_records:
        eid = r.get('event_id')
        proj = r.get('project') or ''
        if not eid: continue
        key = (proj, eid)
        sibling_rids = [s for s in data['event_records'].get(key, [])
                        if s != r['record_id'] and s not in cluster_member_set
                        and s not in seen_siblings]
        if not sibling_rids: continue
        sibling_section.append(f"\n### Event {eid} in project '{proj}' (seed: {r['record_id']})")
        for srid in sibling_rids[:max_event_siblings_per_record]:
            s = data['records'].get(srid)
            if not s: continue
            seen_siblings.add(srid)
            other_cluster = data['rid_to_cluster'].get(srid, 'unassigned')
            other_cluster_name = ''
            if other_cluster in data['catalogue']:
                other_cluster_name = data['catalogue'][other_cluster]['canonical_name']
            sib_meta = data['doc_meta'].get(srid, {})
            sib_timing = _format_doc_metadata(sib_meta)
            sib_title = (sib_meta.get('source_title') or '').strip()
            sib_url = (sib_meta.get('source_url') or '').strip()
            sib_pdf = (sib_meta.get('pdf_url') or '').strip()
            sibling_section.append(f"\n  - [{srid}] (cluster: {other_cluster}"
                                    + (f" — {other_cluster_name}" if other_cluster_name else "")
                                    + (f"; {sib_timing}" if sib_timing else "")
                                    + ")")
            if sib_title:
                sibling_section.append(f"    source_title: {sib_title[:160]}")
            if sib_url:
                sibling_section.append(f"    source_url:   {sib_url}")
            if sib_pdf:
                sibling_section.append(f"    pdf_url:      {sib_pdf}")
            sibling_section.append(f"    narrative: {(s.get('narrative') or '').strip()[:500]}")
            sibling_count += 1

    if sibling_count > 0:
        lines.extend(sibling_section)
        lines.append(f"\n(Total event siblings included: {sibling_count})")
    else:
        lines.append("\n## Event siblings\n\n(No event siblings found for records in this cluster.)")

    return '\n'.join(lines), {
        'n_records': len(cluster_records),
        'n_projects': len(by_project),
        'n_event_siblings': sibling_count,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cluster', required=True, help='cluster_id (e.g. c016)')
    ap.add_argument('--model', default='claude-sonnet-4-6')
    # Default to model ceiling (Opus 4.7 = 128000). Per project standing
    # instruction, never cap max_tokens below the model's ceiling on a
    # generative task — truncated output (e.g. half-rendered references
    # list) wastes the whole call. c042 (133 records, 51 projects) hit
    # the previous 12000 cap and lost the tail of the references section.
    ap.add_argument('--max-tokens', type=int, default=128000)
    args = ap.parse_args()

    print(f"Loading data...", flush=True)
    data = load_data()
    if args.cluster not in data['catalogue']:
        raise SystemExit(f"Cluster {args.cluster} not in catalogue")
    cluster = data['catalogue'][args.cluster]
    print(f"  cluster: [{args.cluster}] {cluster['canonical_name']}", flush=True)

    # Compute category diversity for the prompt
    members = [data['records'][r] for r in data['cluster_members'].get(args.cluster, [])
               if r in data['records']]
    projs = {m.get('project','') for m in members if m.get('project')}
    cats = set()
    for p in projs:
        c = data['projects'].get(p, {}).get('Category','')
        if c: cats.add(c)

    print(f"  records in cluster: {len(members)}", flush=True)
    print(f"  unique projects: {len(projs)}", flush=True)
    print(f"  distinct categories: {len(cats)}", flush=True)

    print(f"\nBuilding evidence block...", flush=True)
    evidence_block, stats = build_evidence_block(args.cluster, data)
    print(f"  records: {stats['n_records']}, projects: {stats['n_projects']}, "
          f"event siblings: {stats['n_event_siblings']}", flush=True)
    print(f"  evidence block: {len(evidence_block):,} chars", flush=True)

    prompt = PROMPT_TEMPLATE.format(
        cluster_id=args.cluster,
        cluster_name=cluster['canonical_name'],
        cluster_signature=cluster.get('mechanism_signature',''),
        n_records=len(members),
        n_projects=len(projs),
        n_categories=len(cats),
        evidence_block=evidence_block,
    )
    print(f"  prompt size: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"\nCalling {args.model}...", flush=True)
    started = time.time()
    parts = []
    last_print = 0; last_chars = 0; text_chars = 0
    with client.messages.stream(
        model=args.model, max_tokens=args.max_tokens,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for ev in stream.text_stream:
            parts.append(ev); text_chars += len(ev)
            now = time.time()
            if now - last_print >= 5:
                rate = (text_chars - last_chars) / max(now - last_print, 1)
                print(f"  [{int(now-started)}s] {text_chars:,} chars  +{rate:.0f} c/s",
                      flush=True)
                last_print = now; last_chars = text_chars
        msg = stream.get_final_message()
    text = ''.join(parts)
    wall = time.time() - started
    # Opus 4.7 (1M context, claude-opus-4-7): $5/M input, $25/M output.
    # Sonnet 4.6: $3/M input, $15/M output.
    in_p = 5 if 'opus' in args.model else 3
    out_p = 25 if 'opus' in args.model else 15
    cost = msg.usage.input_tokens/1e6*in_p + msg.usage.output_tokens/1e6*out_p
    print(f"\n  generation done: {len(text):,} chars in {wall:.0f}s", flush=True)
    print(f"  tokens: {msg.usage.input_tokens:,}in / {msg.usage.output_tokens:,}out  cost ${cost:.3f}", flush=True)

    out = REPORT_DIR / f'{args.cluster}_report.md'
    out.write_text(text)

    # Render a styled standalone HTML sibling via tools/md2html (no extra
    # API spend; deterministic markdown→HTML with embedded CSS).
    html_out = REPORT_DIR / f'{args.cluster}_report.html'
    title = f"ARENA {args.cluster} — {cluster['canonical_name']}"
    eyebrow = f"Broad Learnings · ARENA cluster synthesis · {args.cluster}"
    try:
        proc = subprocess.run(
            [sys.executable, str(MD2HTML), title, eyebrow],
            input=text, capture_output=True, text=True, check=True,
        )
        html_out.write_text(proc.stdout)
        print(f"  wrote {html_out}", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"  md2html failed (non-fatal): {e.stderr.strip()}", flush=True)

    meta = REPORT_DIR / f'{args.cluster}_meta.json'
    meta.write_text(json.dumps({
        'cluster_id': args.cluster,
        'cluster_name': cluster['canonical_name'],
        'records': len(members),
        'projects': len(projs),
        'categories': len(cats),
        'event_siblings': stats['n_event_siblings'],
        'evidence_chars': len(evidence_block),
        'prompt_chars': len(prompt),
        'output_chars': len(text),
        'input_tokens': msg.usage.input_tokens,
        'output_tokens': msg.usage.output_tokens,
        'cost_sync': round(cost, 3),
        'wall_seconds': round(wall, 1),
        'model': args.model,
    }, indent=2))
    print(f"\n  wrote {out}", flush=True)


if __name__ == "__main__":
    main()
