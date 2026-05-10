# Causal-chain test on multi-mechanism events

For 6 ARENA events that span ≥5 distinct mechanism clusters across ≥4 distinct parent archetypes, asked Sonnet 4.6 to assess whether the parents form a causal chain or an orthogonal cluster of failures.

**Cost:** $0.07, 34s.

## Verdict distribution

| verdict | n |
|---|---:|
| causal_chain | 2 |
| partial_chain | 2 |
| cluster_of_orthogonal_failures | 1 |
| single_root_with_multiple_consequences | 1 |

## Per-event diagnoses

### EVT-0037 — Lake Bonney Battery Energy Storage System

**Verdict:** `causal_chain` · confidence: `high`

**Reconstructed chain:**

- p36 -> p37
- p37 -> p05
- p05 -> p38
- p38 -> p23
- p23 -> p24
- p24 -> p30
- p24 -> p49
- p24 -> p28
- p24 -> p15

**Evidence:** ARENA-DLV-0651-0008 shows p36 (poor scoping) failed to identify system strength shortfall. ARENA-DLV-0651-0106 confirms p37 (hidden brownfield condition) then emerged. ARENA-DLV-0651-0071/0072 show p05 (OEM model opacity) blocked resolution. ARENA-DLV-0651-0070 shows p38 (integration testing) exposed model failures. ARENA-DLV-0651-0069 shows p23 (regulatory gap) removed applicant visibility, enabling p24 (approval friction) to cause 8-month delay per ARENA-DLV-0651-0061. p30, p49, p28 and p15 follow as downstream consequences.

### EVT-0004 — Musselroe Wind Farm FCAS Trial

**Verdict:** `causal_chain` · confidence: `medium`

**Reconstructed chain:**

- p14 -> p09
- p09 -> p13
- p13 -> p11
- p11 -> p36
- p36 -> p38
- p38 -> p16
- p27 -> p36

**Evidence:** ARENA-DLV-1292-0021 shows p14 (legacy incompatibility) meant existing plant did not facilitate FCAS dispatch. ARENA-DLV-0720-0040 shows p09 (design-envelope mismatch) from retrofit context. ARENA-DLV-0721-0020 shows p13 (interface failure) with setpoint conflicts. ARENA-DLV-1292-0010 shows p11 (control-loop failure) during on-site tests. ARENA-DLV-0721-0028 shows p36 (scoping inadequacy) as sign-off burden. ARENA-DLV-1292-0028 shows p38 (incremental integration testing). ARENA-DLV-1292-0015 confirms p16 (scale-up gap) requiring further refinement.

### EVT-0005 — Impact and Management of Harmonic Distortion for Large Renewable Generators

**Verdict:** `cluster_of_orthogonal_failures` · confidence: `high`

**Evidence:** Records span independent methodological critiques: ARENA-DLV-0567-0026 (p17, uniform treatment misfit), ARENA-DLV-0567-0027 (p28, governance fragmentation), ARENA-DLV-0567-0029/0097 (p19, aggregate-individual mismatch), ARENA-DLV-0567-0032 (p03, model assumption error), ARENA-DLV-0567-0095 (p41, standards obsolescence), ARENA-DLV-0567-0096 (p23, regulatory misfit). Each identifies a distinct flaw in harmonic allocation methods without one causing the next; they co-exist as parallel deficiencies in the regulatory-technical landscape.

### EVT-0030 — Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)

**Verdict:** `single_root_with_multiple_consequences` · confidence: `high`

**Reconstructed chain:**

- p14 -> p23
- p14 -> p22
- p14 -> p25
- p14 -> p36
- p14 -> p27
- p14 -> p42
- p14 -> p69

**Evidence:** Across nearly all records, p14 (legacy regulatory framework designed for unidirectional flows) is the dominant root cause, explicitly stated in ARENA-DLV-0813-0012/0047/0072/0073, ARENA-DLV-1039-0093/0094/0135, ARENA-DLV-1337-0056/0057/0058. Downstream consequences include p23 (regulatory gap), p22 (value capture blocked), p25 (policy uncertainty), p36 (scoping rework), p27 (coordination overhead), p42 (compliance gap), and p69 (conservatism bias), all radiating from the single structural misfit.

### EVT-0124 — Port Kembla Steelworks Renewables & Emissions Reduction Study

**Verdict:** `partial_chain` · confidence: `medium`

**Reconstructed chain:**

- p50 -> p02
- p50 -> p16
- p50 -> p17
- p50 -> p57
- p02 -> p11
- p16 -> p58

**Evidence:** p50 (feedstock variability) is the dominant root: ARENA-DLV-0789-0075/0079/0081/0082/0086/0087/0108 show biochar's differing density and moisture causing cascading process disruptions. p02 (instrumentation inadequacy) follows per ARENA-DLV-0789-0073/0077/0100/0106 as sensors calibrated for coal misread blends. p11 (control failure) in ARENA-DLV-0789-0122/ARENA-DLV-1325-0014 results from p02 miscalibration. p16 (scale-up gap) per ARENA-DLV-0789-0080 and p57 (trial representativeness) per ARENA-DLV-0789-0092 are partially orthogonal design limitations.

### EVT-0074 — AEMO - Project EDGE (Energy Demand and Generation Exchange)

**Verdict:** `partial_chain` · confidence: `medium`

**Reconstructed chain:**

- p22 -> p29
- p22 -> p20
- p05 -> p31
- p31 -> p33
- p33 -> p32
- p29 -> p32
- p39 -> p22

**Evidence:** ARENA-DLV-0804-0109 shows p22 (absent settlement mechanism) forces aggregators to invent incentives, linking to p29 (misaligned incentives, ARENA-DLV-0804-0111) and p20 (cost threshold, ARENA-DLV-0804-0112). ARENA-DLV-0804-0106/0113/ARENA-DLV-1330-0012 show p05 (low energy literacy) drives p31 (trust deficit, ARENA-DLV-1330-0011) which drives p33 (behavioural friction, ARENA-DLV-1330-0008) and p32 (recruitment shortfall, ARENA-DLV-1330-0033). ARENA-DLV-1330-0003 shows p39 (external shock) exacerbated p22. p55 and p61 are somewhat orthogonal.
