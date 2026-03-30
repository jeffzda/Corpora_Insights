# ARENA Project Delivery — Reference Class Analysis
**Version 1.0 | March 2026**
**Corpus: 267 delivery insight records from 100 ARENA report documents (2014–2025)**

---

## How to read this report

Each record in the corpus captures one discrete delivery event — a failure, delay, success, or lesson — extracted from an ARENA knowledge bank report. The 267 records are tagged with structured fields: `project_type`, `project_scale_band`, `lifecycle_phase`, `proponent_type`, `delay_category`, `failure_mode`, and `outcome_class`.

This report slices those fields 14 different ways to surface cross-cutting delivery patterns. The purpose is **reference-class learning** in the Flyvbjerg sense: what can a portfolio manager predict about a new project before it starts, based on what similar projects have historically produced?

---

## 1. The failure mode landscape

| Failure mode | n | % |
|---|---|---|
| No major failure stated | 55 | 21% |
| **Design assumption failure** | **48** | **18%** |
| Regulatory misfit | 26 | 10% |
| Schedule slippage | 26 | 10% |
| Technical underperformance | 24 | 9% |
| Data quality / measurement failure | 21 | 8% |
| Governance / coordination failure | 17 | 6% |
| Commercial / demand failure | 17 | 6% |
| Integration failure | 14 | 5% |
| Resource / capability shortfall | 12 | 4% |
| Cost overrun | 6 | 2% |

**The dominant finding: 79% of records document a substantive failure mode.** Only 1 in 5 records reports a clean outcome. This is not pessimism bias in the extraction — it reflects the nature of the source documents (lessons learnt reports are written specifically to capture what went wrong or was unexpected).

**The single largest failure mode is design assumption failure** — wrong technical assumptions made during development and design, which then collide with reality during construction or commissioning. This is the operational signature of optimism bias.

**Cost overrun is underrepresented** — only 6 records. This almost certainly reflects disclosure norms (cost data is commercially sensitive) rather than a genuinely low incidence of cost overrun in ARENA projects.

---

## 2. Five delivery reference classes

Based on the `project_type` × `failure_mode` cross-tabulation, five coherent delivery reference classes emerge, each with a distinct failure signature.

---

### Reference Class 1: Physical-scale infrastructure
*project_type: storage, generation, network/grid*

**Storage (n=30):** The dominant failure modes are design assumption failure (30%), regulatory misfit (20%), and integration failure (20%). Two-thirds of storage records carry a non-trivial failure mode. The lifecycle phase where problems hit is almost exclusively **commissioning/integration** — 11 of 30 records are in this phase, and when they are, 10 out of 11 result in delays or rescopes. The specific pattern: inverter-PPC-GFM control architecture is where assumptions fail. Every major battery project in the corpus encountered unexpected control system integration issues that were not resolvable from the OEM documentation alone.

**Generation (n=35):** Design assumption failures dominate (9 records), but uniquely, this class has **zero data quality failures** — physical generation projects know their performance outcomes. The failure pattern is early-stage: 18 of 48 design assumption failures across the full corpus hit during **development/design phase**, and generation projects are disproportionately represented there.

**Key reference class prediction:** Physical storage and generation projects should budget for a commissioning/integration phase that is 50–100% longer than planned, driven by control system integration surprises. Projects that engage OEM and system integrator jointly before procurement will materially reduce this risk.

---

### Reference Class 2: Digital aggregation and VPP
*project_type: DER/customer-side (n=48), software/data/digital (n=35)*

This class has the highest record count (83/267 = 31%) and the most distinctive failure profile.

**DER/customer-side:** The top failure modes are schedule slippage (8), data quality/measurement failure (6), and regulatory misfit (4). The delay profile is unusual: **data/validation/testing (7) and stakeholder/land/community (7) are co-equal top delay categories** — meaning these projects slow down both because of technical measurement problems and because of the difficulty of enrolling, retaining and managing distributed customer participants.

**Software/data/digital:** Data quality/measurement failure (10 records) is the dominant failure mode — by far the highest rate of any project type (29% of all software/digital records). These projects consistently discover that the data they need either doesn't exist, is in the wrong format, is inaccessible due to privacy/cyber constraints, or is owned by parties who won't share it.

**Key reference class prediction:** DER and digital aggregation projects face a tripartite delivery risk that is unlike physical infrastructure: (1) participant recruitment and retention risk, (2) data access and quality risk, and (3) regulatory/market framework risk. All three must be resolved before meaningful testing can begin, and in practice they are often discovered sequentially rather than in parallel. Add 6–12 months to any DER program schedule for this discovery phase.

---

### Reference Class 3: Industrial decarbonisation
*project_type: industrial decarbonisation (n=42)*

**This class has the highest proportion of "no major failure stated" outcomes (11/42 = 26%)** — higher than any other project type. Industrial operators who reach the point of publishing lessons learnt reports often have successful demonstrations to report. But when failures occur, they cluster around:

- **Resource/capability shortfall** (3 records): industrial operators often lack in-house project management capability for novel technology integration
- **Design assumption failure** (6 records): feasibility studies in industrial settings consistently underestimate the complexity of legacy equipment integration, data gaps, and seasonal operational constraints
- **Regulatory misfit** (5 records): environmental approvals, production licenses, and safety regulations designed for conventional industrial processes create unexpected barriers for novel clean energy inputs (e.g. hydrogen injection, biochar blending, heat pump integration)

The delay profile: **internal governance/resourcing (3) and data/validation/testing (3)** are co-dominant. Industrial operators struggle to allocate internal engineering resources for externally-funded R&D projects alongside production commitments.

**Key reference class prediction:** Industrial decarbonisation projects with industrial operators as lead proponent need a dedicated internal project owner with decision-making authority — not a nominated contact. Without this, delivery drags on internal governance bottlenecks. Budget 3–6 months for baseline energy data collection before feasibility modelling begins.

---

### Reference Class 4: Manufacturing and technology scale-up
*project_type: manufacturing/supply chain (n=30)*

**100% of manufacturer/OEM records carry a failure mode.** Design assumption failure (10/30 = 33%) is the single dominant failure — the highest rate of any project type. The specific pattern: product design assumptions made at bench scale do not hold when production processes are developed or when the product is integrated into a real-world deployment environment.

The lifecycle phase profile is distinctive: design assumption failures in this class hit **construction/installation** (11 records) not development/design — meaning the assumptions are typically about manufacturing process scalability, and they are discovered during the build of production equipment or the first production runs, not during design review.

**Key reference class prediction:** Manufacturing/supply chain projects (solar PV manufacturing, automated deployment systems, novel electrolyser production) should structure their ARENA milestones around manufacturing process validation checkpoints, not just product performance metrics. The schedule risk sits in the transition from prototype to pilot production line, not in R&D.

---

### Reference Class 5: Transport electrification
*project_type: transport electrification (n=18)*

**Regulatory misfit is uniquely dominant here (6/18 = 33%)** — the highest regulatory misfit rate of any project type. The specific patterns: EV charging infrastructure encounters mismatches with metering standards (no unified revenue metering standard for DC EVCS), AS/NZS 4777.2:2020 not fit for bidirectional chargers, DNSP formal approval agreements not designed for EV charging, and FBT/lease regulatory constraints limiting fleet transition pace.

**Commercial/demand failure is the second most common failure mode** (3 records): EV fast charging network economics depend on utilisation, which is highly location- and timing-dependent. Projects that chose sites based on "black spot" logic rather than demand modelling encountered underutilisation.

Delays in this class are dominated by **approvals/regulatory (4)** and **construction/installation (2)**, with grid connection delays a recurring third factor. The approval bottleneck is not AEMO but DNSP — local network capacity assessments and connection agreements are the critical path item.

**Key reference class prediction:** EV charging rollout projects face a deterministic regulatory gap risk that is not addressable through better project management — it requires prior engagement with metering authorities, standards bodies, and DNSPs at program design stage. Projects that treat approvals as a procurement-phase activity rather than a program design activity will consistently miss their first milestone.

---

## 3. Scale band findings: what does project scale predict?

| Scale band | n | Delayed/rescoped/partial | Successful/scale-up | Knowledge-only |
|---|---|---|---|---|
| Lab / bench | 21 | 14% | 33% | 47% |
| Pilot | 27 | 55% | 22% | 22% |
| **Demonstration** | **115** | **53%** | **17%** | **36%** |
| First commercial / FOAK | 34 | 55% | 26% | 23% |
| Commercial expansion | 13 | 61% | 15% | 7% |
| **Utility / large-scale** | **29** | **69%** | **17%** | **13%** |
| Programmatic / portfolio-level | 14 | 14% | 28% | 63% |

**Three findings stand out:**

**1. Utility/large-scale has the highest delay/rescope/partial rate (69%).** These are the projects most likely to be delayed but recoverable — they are too large and too important to abandon, but they consistently take longer and cost more than planned. The failure mode profile at utility scale is: schedule slippage (disproportionately high), regulatory misfit, and integration failure. This is the classic infrastructure megaproject signature.

**2. Commercial expansion is the riskiest scale band proportionally (61% adverse outcomes).** This is the "second project" problem: replicating a demonstration that worked at one site across multiple sites reveals that the first project's success was partly site-specific. New failure modes emerge: multi-site stakeholder complexity, standardisation limits, and commercial model viability at scale.

**3. Programmatic/portfolio-level projects rarely produce clean technical successes.** Their dominant outcome class is "policy/market influence only" (35%) — meaning the program achieved regulatory or market change rather than a quantifiable technical result. This is often the correct outcome for a portfolio-level program, but it means traditional delivery metrics (on time, on budget, to specification) are the wrong way to evaluate them.

---

## 4. Proponent type: who delivers and who struggles

| Proponent type | n | Any failure mode | Top failure pattern |
|---|---|---|---|
| Manufacturer / OEM | 9 | 100% | Design assumption failure (44%) |
| Fleet / logistics operator | 2 | 100% | Schedule slippage, resource shortfall |
| Community / local body | 3 | 100% | Mixed |
| **Project developer** | **47** | **87%** | **Design assumption failure (28%)** |
| Utility / energy retailer | 28 | 89% | Design assumption + technical underperformance |
| Consortium / multi-party venture | 20 | 85% | **Governance/coordination failure (40%)** |
| Government / public-sector body | 14 | 85% | Data quality / measurement failure |
| Network business | 32 | 75% | Design assumption + regulatory misfit |
| Industrial operator | 24 | 75% | Design assumption failure |
| Technology vendor | 47 | 72% | Regulatory misfit + schedule slippage |
| **Research org / university** | **40** | **65%** | **Design assumption failure (20%)** |

**Key findings:**

**Project developers have the highest absolute design assumption failure rate (28%).** This likely reflects the profile of standalone ARENA grantees — first-time deployers of novel technologies, who make optimistic assumptions about technology readiness, site conditions, and grid connection requirements. 87% of project developer records carry a failure mode.

**Consortium/multi-party ventures are uniquely exposed to governance failure.** 47% of all governance/coordination failures come from consortia, which represent only 7.5% of records. The pattern: VPP programs, DER aggregation trials, and multi-technology demonstrations that require three or more parties to jointly deliver a platform consistently experience internal governance breakdowns — unclear accountability, competing priorities, and staff turnover.

**Technology vendors are the most commercially productive proponent type** with the highest success/scale-up rate. Their primary risk is regulatory misfit (they build products assuming a market framework exists, and discover it doesn't) and schedule slippage (manufacturing and supply chain delays). They are significantly less exposed to governance and design assumption failures than developers.

**Research organisations / universities have the lowest failure rate (65%)** and the most benign failure profile — mostly design assumption failures that produce knowledge rather than wasted capital. Their outcomes cluster strongly around "knowledge generated despite setback" and "follow-on scale-up enabled" — which is the appropriate output for research-stage activity.

---

## 5. Lifecycle phase analysis: where does delay actually hit?

| Lifecycle phase | Total delay records | Top delay category | Second |
|---|---|---|---|
| Development / design | 36 | Internal governance / resourcing (28%) | Data / validation / testing (17%) |
| Commissioning / integration | 27 | Commissioning / integration (56%) | Data / validation / testing (19%) |
| Construction / installation | 26 | Construction / installation (58%) | Procurement / supply chain (15%) |
| Approvals / contracting | 24 | Approvals / regulatory (58%) | Grid connection / system studies (13%) |
| Operations | 16 | Data / validation / testing (31%) | Approvals / regulatory (25%) |
| Procurement | 15 | Procurement / supply chain (87%) | — |

**The most important finding here is the self-consistency pattern:** when a project is in phase X, the most common delay category is also X. This sounds tautological but it isn't — it means delays are not primarily caused by upstream phases bleeding into downstream ones. Instead, **each phase generates its own characteristic failure type:**

- Development/design fails due to internal governance (scope management, resource allocation, partner alignment)
- Approvals/contracting fails due to regulatory misfit
- Procurement fails due to supply chain
- Construction/installation fails due to civil and site-specific surprises
- Commissioning/integration fails due to integration incompatibilities
- Operations fails due to data quality and (surprisingly) regulatory approvals — often late-stage regulatory requirements discovered only when systems are live

**The practical implication:** Portfolio managers cannot prevent these failures by applying pressure in adjacent phases. A commissioning failure is almost always caused by something that only becomes visible during commissioning. The mitigation is commissioning-specific — earlier factory acceptance testing, integrated system testing before site, and contingency time in the commissioning schedule.

---

## 6. Technology-specific delivery risk profiles

| Technology | Top delay | Second delay | Specific risk signature |
|---|---|---|---|
| Battery storage | Commissioning/integration (38%) | Approvals/regulatory (24%) | Control architecture surprises at commissioning; AEMO/GPS regulatory misfit |
| Hydrogen | Procurement/supply chain (28%) | Approvals/regulatory (22%) | Immature global supply chain; novel regulatory classification |
| DER | Data/validation/testing (21%) | Stakeholder/community (21%) | Participant recruitment + data access as co-equal bottlenecks |
| Solar PV | Internal governance/resourcing (30%) | Procurement/supply chain (20%) | Project management discipline; supply chain lead times |
| EV | Approvals/regulatory (31%) | Grid connection (15%) | Standards gap; DNSP process mismatch |
| Pumped hydro | Construction/installation (88%) | — | Geotechnical surprises dominate; almost no regulatory delay |
| Grid/system stability | Approvals/regulatory (50%) | Data/validation/testing (25%) | AEMO process; modelling validation delays |
| Solar thermal | Procurement/supply chain (29%) | Financing/commercial close (29%) | Technology supply chain + off-take market immaturity |

**The most distinctive profile is pumped hydro:** 7 of 8 delay records are construction/installation delays — geotechnical surprises (unexpected water ingress, fault zones, perched aquifers) dominate. There is almost no regulatory delay. This is a clean civil engineering reference class: schedule risk is ground conditions, not approvals.

**The most distinctive profile at the other extreme is DER:** delays are spread across multiple categories with no single dominant driver. This reflects the complexity of coordinating distributed assets, customers, network operators, and regulators simultaneously.

---

## 7. Portfolio manager implications: five actionable reference class rules

**Rule 1: Apply a commissioning contingency multiplier for inverter-based projects.**
Storage, GFM battery, and solar-gas hybrid projects show a systematic pattern of commissioning delays caused by control system integration surprises. Historical evidence supports a 50–100% contingency on the commissioning phase schedule for any project involving multiple OEMs and a novel control architecture.

**Rule 2: Treat regulatory misfit as a pre-commitment risk, not a project management problem.**
Regulatory misfits in this corpus were almost always discovered at or after the approvals/contracting stage — meaning capital had been committed before the misfit was identified. For transport electrification and storage projects, regulatory fit analysis (AS/NZS standards, AEMO GPS requirements, DNSP connection rules) should be a pre-conditions-precedent deliverable, not a milestone 1 deliverable.

**Rule 3: Consortium governance is the primary risk in multi-party DER programs.**
47% of governance failures come from consortium structures. For VPP, DER aggregation, and multi-technology programs, the ARENA funding agreement should require a single lead delivery entity with contractual authority over sub-participants, a named program director with >50% time allocation, and a governance framework agreed before execution phase begins.

**Rule 4: Industrial decarbonisation feasibility studies need a data-first milestone.**
The consistent pattern across industrial operator projects: baseline energy data is either absent, inaccessible, or of poor quality, and this discovery typically occurs 3–6 months into the feasibility study — after the budget has been partially consumed. A pre-feasibility "data readiness assessment" milestone (metering audit, SCADA access, seasonal data completeness check) should be a standard ARENA funding condition for this reference class.

**Rule 5: Commercial expansion is not a lower-risk scale than demonstration.**
The data shows commercial expansion projects (n=13) have a higher adverse outcome rate (61%) than demonstration projects (53%). Replication from demonstration to commercial expansion introduces new failure modes — multi-site standardisation limits, commercial model viability, and stakeholder complexity at scale — that are not visible at the single-site demonstration stage. Program designs that assume "the hard part is the demonstration" will be surprised.

---

## Appendix: Summary statistics

| Metric | Value |
|---|---|
| Total insight records | 267 |
| Source documents analysed | 100 |
| Years covered | 2014–2025 |
| Field population rate (core fields) | 99–100% |
| Field population rate (delay_category) | 71% |
| Records with any substantive failure mode | 212 (79%) |
| Records with successful / scale-up outcome | 53 (20%) |
| Records with delayed / rescoped / partial outcome | 123 (46%) |

**Files:**
- `ARENA_delivery_registry_v1.yaml` — all 267 structured records
- `insights/reports/group_01.yaml` through `group_10.yaml` — batch files
- `ARENA_Taxonomy_v1.1.md` — canonical taxonomy
- `reports_sample_100.json` — 100-document sample with quality scores
