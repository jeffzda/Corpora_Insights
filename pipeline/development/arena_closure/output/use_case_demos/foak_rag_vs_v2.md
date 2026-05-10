# Use-case demo: RAG vs v2 layer

**Query.** *"What systematically goes wrong with first-of-a-kind technology demonstration projects?"*

A real ARENA portfolio-manager question. We ran it against two layers built on the same underlying corpus (1,440 ARENA Knowledge Bank documents):

- **RAG**: Qwen3-Embedding-4B over 219,980 paragraph chunks, top-20 by cosine.
- **v2**: 1,141 mechanism clusters → 71 parent-archetypes → 12 themes (Opus 4.7 layered taxonomy over 90,192 extracted records).

---

## What each layer returned

### RAG (top-20 chunks)

20 paragraph snippets, ~140 chars each, drawn from 18 distinct documents. Reading them in score order gives this picture:

- 4 hits (#1, #3, #5, #18) are **TRL-definition pages and section-header pointers** — high cosine because the question mentions "demonstration", but they carry no findings.
- 9 hits (#2, #6, #8, #10, #14, #15, #16, #17, #19) are **genuine FOAK lessons**: tech ahead of internal processes (Monash Smart Energy City), risk is not just technical (Solar Hybrid Fuels), material costs underestimated (Perovskite Tandem), MVR FEL-3 design maturity gap (Low Carbon Alumina), original assumptions broken (V2G), capital intensity / cost-overrun risk for early-adopter low-emissions tech (Alumina roadmap).
- The remainder are adjacent — investor risk (#9), regulatory streamlining (#12), engagement (#13), supply chain stats (#20).

The reader has to read all 20 chunks, weed out the TRL filler, and mentally cluster the remaining lessons into a coherent answer. The synthesis lives in the reader's head.

### v2 layer (5 FOAK-relevant parent-archetypes)

Five parent-archetypes from the 71-parent layer fit the question:

| parent | mechanism family | clusters | records |
|---|---|---:|---:|
| **p16** | Scale-up and lab-to-field translation failure | 9 | 27 |
| **p23** | Regulatory framework gap or misfit for novel context | 33 | 105 |
| **p37** | Late-discovered constraint or hidden site condition | 11 | 33 |
| **p38** | Commissioning and integration testing exposure | 12 | 38 |
| **p58** | Validation infeasibility and absent ground truth | 14 | 42 |
| | **Total (parent-row counts, deduped seeds)** | **79** | **245** |

The parent-row record counts above use catalogue seed memberships. Joining through the full assignment layers, those 79 clusters carry **1,737 records / 775 documents / 375 distinct projects / 47 ARENA category combinations**. The full population is 9× larger than the seed-row total because the catalogue records are seeds; assignment passes pull every matching record in the corpus through the same mechanism class.

Within each parent, the cluster names already do the synthesis work. Examples:

**p16 — Scale-up & lab-to-field:**
- Lab-to-Pilot Equipment Mismatch Causes Process Translation Failure (c505)
- Demonstration-Stage Technology Requires Further R&D Before Upscaling (c766)
- Software Model Scope Mismatch Causes Redevelopment Delays (c891)
- Laboratory Fabrication Process Incompatible With Industrial Scale (c900)

**p37 — Late-discovered constraint / hidden site condition:**
- Undocumented Site History Creating Brownfield Construction Surprises (c015)
- Pre-Existing Grid Condition Misattributed To New Asset (c764)
- Undiscovered Site Contamination Forces Project Abandonment (c928)
- Material Specification Inadequacy Discovered Late Causing Rework (c1110)

**p38 — Commissioning & integration testing exposure:**
- Commissioning Exposing Minor System Failures Causing Schedule Overrun (c028)
- Declared Compatibility Without Comprehensive Interoperability Testing (c950)
- Pre-Production Environment Masking Production Rejection Conditions (c713)
- Connector or Assembly Complexity Causes Latent Connectivity Failures (c897)

**p58 — Validation infeasibility:**
- Manufacturer Performance Claims Unverified by Independent Testing (c795)
- Absent Test Infrastructure Constrains Technology Validation Progression (c687)
- Simulation Validity Cannot Be Confirmed Without Independent Measurement (c904)

---

## What v2 surfaces that RAG@20 missed

These are concrete FOAK pitfalls visible in the v2 layer with multi-record evidence — *and zero overlap with RAG's top-20*. The reader could not have asked for them by name, because the underlying records don't lexically use "first-of-a-kind"; they describe specific structural failures.

| Mechanism | Where it shows up |
|---|---|
| **Pre-production environment masks production-rejection conditions** (c713) | Wind forecasting demo's pre-prod accept-window was too lenient; NT Solar PV output 318% of model in one site (Gapuwiyak) implying baseline-modelling failure during demo phase |
| **Manufacturer claims unverified by independent testing** (c795) | ITP Renewables Battery Testing Centre (whole reason it exists); LSS Round OPEX forecasts were ~half of actual across 11 projects |
| **Declared compatibility without interoperability testing** (c950) | Battery vendors declare inverter compat without testing; Daly River BESS ferroresonance traced to BESS-grid interaction never specified in tender |
| **Pilot-scale renders value proposition imperceptible** (c545) | Origin EV smart charging only relevant at fleet scale; NT Solar single-array maintenance economics |
| **Software model scope mismatch causing redevelopment** (c891) | Strata-residential billing platform; BESS software for microgrids needed redevelopment for transmission |
| **Undiscovered site contamination forces abandonment** (c928) | Cooper Basin geothermal MT-survey failure; reservoir-quality fines mobilisation |

These are answers to the original question. RAG didn't surface them in top-20 because the relevant chunks don't contain the question's lexicon — but the v2 extraction has already classified them under FOAK-relevant mechanism families.

---

## What RAG surfaces that v2 didn't (in this query)

A few RAG hits don't map cleanly into the five FOAK-archetypes:

- **#9 (Battery Storage Workshop)**: "Investor risk associated with emerging technology and lack of reference projects" — financing-risk angle. v2's parent layer routes this to p20 (Cost-benefit threshold not crossed) or p21 (Price signal absent), neither of which I scoped under FOAK above. Whether financing-risk-due-to-novelty *should* be a FOAK family is a design question.
- **#7 (AEMO CER Data Exchange)**: a high-level design-report ToC pointer that's noise in this query; RAG can't tell.
- **#13 (Project SHIELD)**: "consistent engagement and industry" — phrasing ambiguous; the underlying text could be FOAK-relevant or generic stakeholder talk.

So RAG's filter is "lexical / semantic similarity to the question". It picks up ToC pointers and adjacent themes that the v2 parent-routing chose to file elsewhere. A reader can recover both, but only by reading and rejecting hits, which is the whole job.

---

## Comparison

| | RAG (top-20) | v2 (5 FOAK parents) |
|---|---|---|
| Output | 20 paragraph chunks | 79 mechanism clusters, 5 mechanism families |
| Underlying evidence reachable | 18 distinct docs | 775 docs, 375 projects, 1,737 records |
| Synthesis | Reader does it | Already done — cluster + parent names |
| Noise (TRL pointers, ToC entries) | ~20% of top-20 | None — non-finding records are filtered upstream |
| Time to a structured answer | Minutes of reading | Seconds (read parent + cluster names) |
| Verifiability | Direct: chunk → page in source doc | One hop: cluster → record → source doc (via `tools/q cluster c###`) |
| Discoverability of "blind spot" mechanisms | Limited to lexical hits | High — sub-mechanism cluster names surface things you wouldn't have queried for |
| Cost to answer one query | ~$0 (free local embed) | ~$0 (precomputed); ~$11.94 amortised across all queries |

The two layers do **different jobs**.

- RAG is a **retrieval lens**: "show me passages from the corpus that look like the question." Cheap, local, every query is fresh, every hit is directly verifiable. Useful when you already have a specific question in your head and want evidence for it.
- v2 is an **extracted artefact**: someone (Opus, layered) has already read every record and grouped them by failure mechanism, with mechanism names that *answer* questions like "what kinds of things go wrong?" Useful when you want the answer, not the evidence — or when you want to discover failure modes you didn't know to ask about.

---

## Honest caveats

- **Apples-and-oranges scaling.** RAG@20 is the default; RAG@200 would surface more — but reading 200 chunks is also more work. The point isn't "RAG retrieves less"; it's "v2 retrieves *categorised structure*, RAG retrieves *raw chunks*." If you bumped RAG to 200 you'd still have to do the categorisation yourself.
- **v2's FOAK parents are my interpretive choice.** I scoped 5 parents (p16/23/37/38/58) as "FOAK-relevant"; you could argue for including p20 (cost-benefit), p22 (value capture blocked), p47 (workforce skills), or others. The answer to the question is sensitive to that scoping. RAG sidesteps this by not categorising at all.
- **Cluster-name quality is doing a lot of work.** The cluster names ("Pre-Production Environment Masking Production Rejection Conditions") are themselves a synthesis the reader is trusting. If they're wrong, the layer surfaces wrong answers fluently.
- **One query is not a benchmark.** This demonstrates the *kind* of difference, not its average size. Some queries (very lexically specific: "ferroresonance at Daly River") will favour RAG; broad mechanism questions like FOAK favour v2.

---

## Reader takeaway

For "what systematically goes wrong" / "what should I worry about" / "what reference-class evidence applies to my new project" questions, the v2 layer answers with structure that RAG doesn't produce — because the categorisation is the answer. RAG continues to win on lexically-specific lookups where you already know what you're looking for.

The two are complementary, not substitutes. Worth pinning the demo as the methodology paper's empirical anchor for the **v2 vs RAG framing memory** (RAG retrieves; v2 extracts structured artefacts).

---

## Reproduction

```bash
# RAG
python3 -m pipeline.rag search \
  "What systematically goes wrong with first-of-a-kind technology demonstration projects" \
  --corpus arena --top-k 20 \
  --chroma-dir corpora/arena/.chromadb --collection arena

# v2 (parent-routed)
# Listed parents: p16 p23 p37 p38 p58
# tools/q cluster cNNN --projects --with-records  # drill into any cluster
```

Underlying data: `closure/output/use_case_demos/foak_rag_raw.txt`, `foak_v2_breakdown.json`, `foak_v2_diversity.json`.
