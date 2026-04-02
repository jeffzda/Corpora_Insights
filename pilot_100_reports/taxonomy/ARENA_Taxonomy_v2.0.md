# ARENA Delivery Insight Taxonomy v2.0
**Lean reference class framework for project-delivery insights from ARENA knowledge documents**

**Version history**
- v1.0 March 2026 — pilot (100 documents, 267 records)
- v1.1 March 2026 — full corpus (1,440 documents, 1,752 records)
- v1.2 March 2026 — post-analysis update; added extraction guidance and known distortions
- v2.0 April 2026 — taxonomy redesign for reference class forecasting; consolidated category fields, replaced LLM-inferred scale bands with deterministic activity type, converted consortium to governance flag

---

## Purpose

This taxonomy extracts **project-delivery-relevant knowledge** from ARENA Knowledge Bank documents and structures it for **reference class forecasting** — predicting the likely outcome of new projects based on historical base rates for similar projects.

It is deliberately biased toward:
- delivery characteristics and failure patterns
- reference-class retrieval (finding the right historical comparator set)
- deterministic classification where possible (avoiding LLM inference for dimensions that can be derived from metadata)
- alignment with ARENA's own vocabulary and portfolio structure

---

## Design rationale

### Why 3 category fields were consolidated into 1

v1 had three overlapping category fields: `project_type` (10 LLM-inferred values like "generation", "storage"), `technology_domain` (14 LLM-inferred values like "solar PV", "hydrogen"), and `kb_category` (raw KB metadata, ~20 values, display-only). These largely duplicated each other — a battery storage project would be `project_type: storage`, `technology_domain: battery storage`, `kb_category: Battery storage`. The overlap added complexity without analytical value.

v2 replaces all three with a single `arena_category` field mapped deterministically from KB metadata. This:
- Eliminates LLM inference for the technology dimension entirely
- Uses ARENA's own vocabulary (how staff think about their portfolio)
- Makes 100% of KB documents discoverable (41% were previously invisible to website filters)
- Reduces 34 total category values to 14

### Why ARENA's vocabulary was chosen over LLM-inferred categories

ARENA staff think in terms of their KB filter categories. A portfolio manager looking at a new hydrogen project will search for "Hydrogen", not "generation" or "industrial decarbonisation". Aligning with the institutional vocabulary means the tool speaks the same language as its users.

The mapping is deterministic — every raw KB category maps to exactly one arena_category value, with no LLM judgement required. This makes the classification auditable and reproducible.

### Why ocean and geothermal are excluded from matrices

Ocean energy and geothermal energy have too few records in the corpus to produce statistically meaningful base rates. Including them in reference class matrices would create misleadingly precise cells from tiny samples. Records are preserved in the dataset and searchable in the dashboard — they're just excluded from the forecasting matrices.

### Why `project_scale_band` was replaced by `activity_type`

The LLM-inferred `project_scale_band` had two fatal problems:
1. **"Demonstration" absorbed 56% of all records** — a category that captures more than half the data provides almost no discriminating power
2. **The inference is unreliable and unvalidatable** — there is no external ground truth to check whether a project was correctly classified as "demonstration" vs "first commercial/FOAK"

`activity_type` is derived deterministically from the projects CSV (title + summary + program name keywords) with an investment-size fallback. It produces three meaningful bins (Study/feasibility, Pilot/demonstration, Deployment) plus an R&D exclusion. Coverage is ~95% from keywords, ~5% from investment fallback.

### Why ARENA funding ratio was investigated and ruled out as a maturity proxy

ARENA's co-investment ratio (ARENA funding / total project value) was tested as a potential proxy for project maturity — the hypothesis being that ARENA invests a higher fraction of riskier, earlier-stage projects. Analysis showed the median ratio is ~40% regardless of project stage, proponent type, or outcome. The ratio reflects deal structure (ARENA's standard co-investment model), not project risk. It was conclusively ruled out as a useful dimension.

### Why investment-based scale bands were investigated and ruled out

Absolute investment size (total project value) was tested as a scale dimension. The distribution is log-normal with no natural breakpoints — 111 projects cluster right at any proposed $10m boundary. Any cutoff would be arbitrary and would misclassify projects near the boundary. Combined with the fact that users wouldn't know the investment amount for a project they're assessing, this approach was abandoned.

### Why `consortium` was converted from a proponent type to a boolean flag

"Consortium/multi-party venture" describes governance structure, not actor type. Its failure signal is confounded — consortia contain utilities, researchers, developers, and industrial operators, each with their own failure profile. The 77% adversity rate for consortia is a mix of the underlying proponent types' base rates plus the governance coordination overhead.

As a boolean flag (`is_consortium`), it becomes an additive risk adjustment: "what happens when a utility leads a consortium project?" rather than conflating governance structure with actor identity.

The 1,687 consortium records were reclassified to their lead actor's proponent type using: sibling-document majority vote (69%), lead organisation keyword matching (12%), project name inference (23%), and default to government for ARENA portfolio-level records (remainder).

### Why proponent_type was kept at 10 values

Data analysis showed some proponent pairs have similar failure profiles (e.g. developer vs vendor). However, the distinctions matter operationally — a portfolio manager assessing a new proposal needs to know "what happens when a fleet operator runs an EV project?", not "what happens when an industrial/commercial entity does something." The complexity budget saved elsewhere (34 category values → 14, 7 scale values → 3 activity types) allows keeping this dimension at full resolution.

### Why category grouping was rejected

An intermediate grouping layer (8 groups like "Solar", "Grid & system", "Other generation") was considered and rejected. Grouping confounds distinct categories — solar PV and solar thermal have different failure profiles, as do distributed energy resources and demand response. Sparse matrix cells for individual categories are informative (they tell you the evidence base is thin), while grouped cells hide uncertainty behind aggregated numbers.

### Why technology maturity is implicit rather than explicit

Technology maturity (how commercially proven a technology is) was initially considered as a separate dimension. Analysis showed it is completely determined by the combination of `arena_category` (what technology) and `activity_type` (what the project is doing). Solar PV is mature; green hydrogen is early. A solar PV deployment is a very different reference class from a hydrogen pilot — and those two dimensions already capture that distinction. Adding a separate maturity dimension would be redundant.

### The reference class forecasting philosophy

**Sparse cells = honest uncertainty.** A matrix cell with 3 projects tells you "we don't have enough data to forecast this combination reliably." That's valuable information for a portfolio manager.

**Confounded categories = hidden error.** A matrix cell that mixes solar PV with solar thermal, or utilities with consortia, produces a number that looks precise but answers the wrong question. The base rate for "Solar" tells you less than separate rates for "Solar PV" and "Solar thermal."

The taxonomy optimises for clean, unconfounded dimensions at the cost of some sparsity. This is the correct trade-off for reference class forecasting.

---

## Field schema

### Input dimensions (define the reference class)

#### 1. `arena_category`
**type:** deterministic (from KB metadata)
**purpose:** what technology or domain the project operates in

**14 values:** Battery storage · Bioenergy · Demand response · Distributed energy resources · Electric vehicles · Grid stability · Hybrid technologies · Hydrogen · Industrial renewables · Off grid · Pumped hydro · Solar PV · Solar thermal · Wind

**Mapping from raw KB metadata:**
```python
ARENA_CATEGORY_MAP = {
    "Battery storage":                          "Battery storage",
    "Bioenergy / Energy from waste":            "Bioenergy",
    "Concentrated solar thermal":               "Solar thermal",
    "Demand response":                          "Demand response",
    "Distributed energy resources":             "Distributed energy resources",
    "Electric vehicles":                        "Electric vehicles",
    "Geothermal energy":                        None,   # excluded
    "Hybrid technologies":                      "Hybrid technologies",
    "Hydrogen energy":                          "Hydrogen",
    "Solar energy":                             "Solar PV",
    "Solar PV R&D":                             "Solar PV",
    "Large-scale solar":                        "Solar PV",
    "Renewables for industry":                  "Industrial renewables",
    "System security and reliability":          "Grid stability",
    "Wind energy":                              "Wind",
    "Hydropower / Pumped Hydro Energy Storage": "Pumped hydro",
    "Renewables in buildings":                  "Distributed energy resources",
    "Off grid":                                 "Off grid",
    "Ocean energy":                             None,   # excluded
    "General":                                  None,
}
```

Multi-valued per record (inherited from document's comma-separated `kb_category`).

---

#### 2. `activity_type`
**type:** deterministic (from projects CSV keywords)
**purpose:** what the project is doing — its position on the commercialisation pathway

**3 values + R&D exclusion:**

| Value | What it means | Keyword signals |
|---|---|---|
| Study / feasibility | Scoping, FEED, assessments, roadmaps | feasibility, FEED, assessment, roadmap, investigation |
| Pilot / demonstration | Trials, testing, proof of concept | pilot, trial, demonstration, proof of concept, testing |
| Deployment | Construction, installation, commissioning of real assets | construct, deploy, install, commission, MW capacity, solar/wind farm |

R&D projects (Post Fellowship Doctorates, ASI, etc.) are excluded from reference class matrices but remain searchable.

Classification priority: R&D programs → Study keywords → R&D keywords → Pilot keywords → Deployment keywords/capacity → Investment-size fallback ($0-3m → Study, $3-15m → Pilot, >$15m → Deployment).

---

#### 3. `proponent_type`
**type:** LLM-inferred
**purpose:** who is delivering the project (the lead delivery actor)

**10 values:**
- project developer
- utility / energy retailer
- network business
- industrial operator
- fleet / logistics operator
- manufacturer / OEM
- technology vendor
- research organisation / university
- government / public-sector body
- community / local body

---

#### 4. `is_consortium`
**type:** deterministic (from original LLM proponent_type classification)
**purpose:** whether the project involves formal multi-party delivery governance

**Boolean.** `true` when the original proponent_type was "consortium/multi-party venture". Enables consortium governance risk adjustment in reference class matrices.

---

### Observation dimensions (describe what happened)

#### 5. `lifecycle_phase`
**type:** LLM-inferred
**purpose:** where in the project lifecycle the insight arose

**8 values:** concept/feasibility · development/design · approvals/contracting · procurement · construction/installation · commissioning/integration · operations · close-out/post-project review

Note: `variation/re-scope` merged into `close-out/post-project review` in v2.0.

---

#### 6. `failure_mode` (unchanged from v1)
**11 values:** no major failure stated · technical underperformance · integration failure · schedule slippage · cost overrun · resource/capability shortfall · commercial/demand failure · regulatory misfit · data quality/measurement failure · design assumption failure · governance/coordination failure

#### 7. `outcome_class` (unchanged from v1)
**8 values:** successful demonstration · partial success · delayed but recoverable · re-scoped/adapted · knowledge generated despite setback · discontinued/not progressed · follow-on scale-up enabled · policy/market influence only

#### 8. `issue_severity` (unchanged from v1)
**5 values:** none · minor · moderate · major · critical

#### 9. `delay_category` (unchanged from v1)
**10 values:** no material delay stated · approvals/regulatory · grid connection/system studies · procurement/supply chain · financing/commercial close · construction/installation · commissioning/integration · data/validation/testing · stakeholder/land/community · internal governance/resourcing

---

### Preserved fields (traceability)

Original v1 fields are preserved on each record for traceability but are not used in matrices or primary filters:
- `project_type` → original LLM-inferred delivery archetype
- `project_scale_band` → original LLM-inferred scale band
- `technology_domain` → original LLM-inferred technology
- `proponent_type_original` → pre-reclassification value (consortium records only)
- `lifecycle_phase_original` → pre-remap value (variation/re-scope records only)

---

## Reference class matrices

### Matrix 1: Technology × Activity
`arena_category × activity_type` — 14 × 3 = 42 cells.
Primary forecasting matrix. Per cell: adversity rate, discontinuation rate, top failure modes, sample size.
*"What happens to Hydrogen pilot/demonstration projects?"*

### Matrix 2: Phase Risk Watch-list
`arena_category × lifecycle_phase` — 14 × 8 = 112 cells (sparse-filtered).
Phase risk watchlist. Only cells with ≥5 projects shown.
*"Where do Battery storage deployments hit trouble?"*

### Matrix 3: Proponent Adjustment
`proponent_type` — 10 values + consortium governance adjustment.
Adversity rate relative to corpus baseline. Consortium row shows the adversity uplift for multi-party vs single-party governance.

### Matrix 4: Discontinuation Risk
`arena_category × activity_type` — subset of Matrix 1 for cells with discontinuation rate ≥ 3%.

---

## Implementation

All changes are deterministic post-processing. No re-extraction required. No API calls.

| Script | Purpose |
|---|---|
| `scripts/arena_category_map.py` | Category mapping, consortium reclassification helpers |
| `scripts/classify_activity_type.py` | Keyword classifier for activity_type from projects CSV |
| `scripts/stamp_taxonomy_v2.py` | Stamps new fields onto all per_doc YAMLs |
| `scripts/build_dashboard.py` | Generates dashboard with new matrices and filters |

---

## Corpus statistics (v2.0)

- **Records:** 16,931 across 1,448 documents
- **arena_category coverage:** 97.5% (16,515 records)
- **activity_type coverage:** 87.4% (14,801 records; 2,130 from non-portfolio-matched projects)
- **Consortium records reclassified:** 1,687 (92 projects)
- **Lifecycle phase remapped:** 76 records (variation/re-scope → close-out)
- **Categories excluded from matrices:** Geothermal, Ocean (too few records)
- **R&D projects excluded from matrices:** ~248 projects (preserved in dashboard, not in reference class analysis)
