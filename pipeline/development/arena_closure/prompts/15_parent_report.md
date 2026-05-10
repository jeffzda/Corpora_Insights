# Parent-archetype synthesis report

You are writing a portfolio-review report for ARENA (Australian Renewable Energy Agency) on a specific **parent failure-archetype** identified in their project corpus. A parent archetype is one rung up from a mechanism cluster — it groups together every cluster (each itself a recurring failure pattern) that shares the same underlying mechanism class. Your audience is a senior portfolio manager who already understands ARENA's mandate but wants a clear, synthesis-grade write-up of how this *family* of failure patterns manifests across the portfolio.

The synthesis grain is therefore **cluster-as-instance**: each constituent cluster is one specific way the parent mechanism shows up; the patterns of interest live in the relationships between clusters and across the projects that exemplify them.

# PARENT UNDER REVIEW

Parent ID: {parent_id}
Name: {parent_name}
Mechanism criterion: {parent_criterion}
Description: {parent_description}
Theme: {theme_name}
Constituent clusters: {n_clusters}
Total records across constituent clusters: {n_records}
Unique projects represented: {n_projects}
Distinct ARENA categories represented: {n_categories}

# EVIDENCE BASE

Below is the full evidence base for this report, organised in the order that supports cross-cluster synthesis:

1. **Temporal range**: the project-year and publish-year span across all records in this parent.
2. **Constituent clusters**, each with its canonical name, mechanism signature, and supporting records. Records within each cluster are grouped by project and sorted oldest-first. Each record carries source title, project year, publish date, document type, page references, and source/PDF URLs.
3. **Project metadata** for each project that contributes records: title, ARENA category, lead organisation, ARENA funding, total project value, location, status, programme.
4. **Event siblings** — where a record in this parent shares an event with records *outside* this parent, those siblings are listed with their cluster placement so you can see how the parent mechanism interacts with adjacent failure modes.

{evidence_block}

# TIME-VARIANT FACTORS — IMPORTANT

Most failure-mode mechanisms in this corpus are **time-variant**: their salience, scale, and even their *existence* depend on the state of the market, regulatory environment, technology cost curves, deployment penetration, or counterparty maturity at the time the project was operating. A claim about *current* applicability of a mechanism is different from a claim about its *historical* manifestation.

Two date fields per record matter:
- **`project year`** = when the project was actually operating. Dates the *underlying conditions*.
- **`publish date`** = when ARENA released the document. Dates the *interpretation*.

For each claim you make, ask: is this a claim about a *time-bound condition* or a *time-invariant mechanism*. Time-bound claims should explicitly cite the period they refer to. Time-invariant mechanisms can stand without temporal qualification, but their *manifestation* in the corpus is bounded by the dates of the evidence.

# TASK

Write a synthesis report on this parent archetype. Required elements:

1. **Opening framing**: one or two paragraphs naming the parent mechanism in plain language, why it matters for an ARENA-style infrastructure-investment portfolio, the scale and *temporal range* of its presence in the corpus, and the diversity of constituent clusters.

2. **The mechanism itself**: a careful articulation of the causal pathway *at the parent level* — the structural feature that unifies the constituent clusters. Where the mechanism depends on market/regulatory/technology state, name those dependencies and the period they applied to.

3. **Cluster-level taxonomy of manifestation**: this is the heart of the report. Group the constituent clusters into a small number of coherent sub-patterns (typically 3-7). For each sub-pattern, name what unifies the clusters in it, then walk through the specific clusters that instantiate it, citing records using superscript references (see Citation format below). Project names appear inline as `[Project Title]` without a number — they're contextual labels rather than bibliographic citations. Do NOT quote source text. Describe and synthesise.

4. **Cross-cutting observations**: what patterns emerge when you look across the sub-patterns? Are some clusters at the boundary between two sub-patterns? Are there dimensions (time, technology, project lifecycle stage, scale) along which the parent mechanism's expression varies systematically? Where the evidence dates span many years, name how the mechanism has *evolved* — is it more or less salient in recent records than older ones?

5. **Project- and event-level context** where instructive. The records sit inside projects with their own structure, funding, scale, stakeholders, operating period; sometimes a single project's structure illuminates *why* multiple sub-patterns of the parent show up there. Event siblings tell you how this parent mechanism interacts with adjacent failure modes — when this archetype shows up, what else tends to be happening?

6. **Temporal-trajectory observations**: how does the evidence date-range shape the claim? Is the parent mechanism likely still operating with the same intensity now, or has the underlying state shifted? If the corpus only contains older records, name that limitation. If newer records modify or moderate older findings, surface that.

7. **Mitigation patterns observed**: from the records themselves, what mitigations or workarounds have been proposed or attempted? Note whether mitigation effectiveness is itself time-variant, sub-pattern-specific, or general.

8. **Implications for portfolio decisions**: what would a portfolio manager do differently knowing this archetype is real and pervasive — and given its temporal scope? Be specific about the decision points (funding, milestone review, knowledge sharing) and what changes at each. Where the mechanism's current applicability is uncertain (because evidence is older), say so.

9. **Open questions or evidence gaps**: what does this corpus *not* tell us about this archetype? What further evidence would sharpen the picture? Are there sub-patterns that are thinly evidenced and would benefit from more data?

Style:
- Report-style, prose-heavy, not bulleted unless a bullet helps
- Do NOT quote source text directly — synthesise
- When citing time-bound claims, include the period (e.g. "in 2017–2019, when …")
- Connect the parent mechanism to broader patterns in classical economics/management/engineering/system science where it sharpens the insight — these structural mechanism classes are not unique to renewable energy
- Length: aim for 2,500-4,000 words for the body, plus the references section. Substance over length.

# CITATION FORMAT

Cite specific records using **HTML superscript tags** with the reference number, like this:

> The trade-off between thermal and electrical optimisation in PV-T systems<sup>1</sup> mirrors the demand-vs-supply optimisation tension in residential VPPs<sup>3,7</sup>.

Numbering rules:
- Number references in **order of first appearance** in the body.
- **Reuse the same number** for repeat citations of the same record.
- Multiple citations on one claim go inside one `<sup>` separated by commas, e.g. `<sup>1,3,7</sup>`.
- Cluster ids appear inline as `[c042]` style only when you specifically discuss a cluster as a unit (e.g. "the c042 cluster on electrode-degradation-from-chemical-incompatibility..."). Do NOT use `[cNNN/ARENA-DLV-NNNN-NN]` form anywhere in the body.
- Project titles remain inline as `[Project Name]` *without* a superscript number — projects are contextual labels.
- Event siblings, when cited, get their own reference number on the same numbering line.

At the end of the report, immediately after the body, include a `## References` section listing every cited record in numeric order, one per line, in this exact format:

```
1. **ARENA-DLV-1086-0057** — *Large-Scale Battery Storage Knowledge Sharing Report* (Reports/Insights, project year 2018, published 25/09/2019, p. 28). [Source page](https://arena.gov.au/knowledge-bank/...) · [PDF](https://arena.gov.au/assets/...)
2. **ARENA-DLV-0254-0016** — *ARENA Insights Forum Presentation Summaries & Key Points — Large-Scale Projects Stream* (Reports, project year 2018, published 25/06/2019, p. 3). [Source page](https://...) · [PDF](https://...)
```

Field-by-field requirements:
1. Number followed by `.` and a space.
2. **Bold record_id** (the `ARENA-DLV-NNNN-NN` form).
3. ` — ` (em-dash with spaces).
4. *Italic source title* — the document's title as it appears in `source_title:` in the evidence block.
5. Parenthetical context, comma-separated: document type, project year, publish date, page numbers. Skip any field that's missing in the metadata; don't invent values.
6. ` ` then `[Source page](URL)` linking to `source_url` from the evidence block.
7. ` · ` separator.
8. `[PDF](URL)` linking to `pdf_url` from the evidence block.
9. If a record has no `source_url` or `pdf_url`, omit that link rather than substituting a placeholder.

Every cited record (anything you've assigned a `<sup>N</sup>` in the body) MUST appear in the references list. Don't list records you didn't cite.

Return only the report Markdown — no preamble, no commentary, no closing notes.
