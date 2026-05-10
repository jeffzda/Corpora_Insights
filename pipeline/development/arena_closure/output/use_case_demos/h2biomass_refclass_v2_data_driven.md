# Reference-class memo (v2): hydrogen-from-biomass FOAK — data-driven

**Hypothetical project (unchanged).** First-of-a-kind 5 MW hydrogen-from-biomass demonstration in regional Australia.

**Reframing.** The first memo scoped 15 parents by hand and pulled clusters under each. That was reasonable but interpretive. This version reverses the direction: filter the corpus to records tagged with hydrogen or bioenergy ARENA categories, find the clusters where those records *concentrate*, then look at what other tech is in those same clusters. The data does the parent selection; the corpus tells you which mechanisms bite this kind of project, and the clusters' non-H2/biomass members tell you which other-tech projects to learn from.

---

## Method

- **Filter.** Records whose `kb_category` contains `Hydrogen` or `Bioenergy`. (90,192 raw records → 23,674 clustered into 1,141 mechanism clusters → **2,291** match the filter, **9.7% base rate**.)
- **Coverage.** H₂/bio records touch **482 of 1,166 clusters** — about 41% of the corpus's mechanism vocabulary already has at least one analogous record in this tech filter.
- **Ranking lenses.** Two independent rankings, because each carries different signal:
  - **Volume** = absolute count of filter-matching records in a cluster. Tells you which mechanisms bite this tech *most*.
  - **Concentration** = filter share within a cluster (with ≥10 records and ≥2× base rate). Tells you which mechanisms are *specific* to this tech.

---

## Volume — top mechanisms biting H₂/bio projects

The 25 clusters with the most H₂/bio records (parent in column 2). Volume can come from generic mechanisms that everyone hits, *plus* this tech being a heavy contributor — both are useful to know.

| cid | parent | h2/bio | total | share | mechanism |
|---|---|---:|---:|---:|---|
| c002 | p41 standards/cert gap | **72** | 193 | 37% | Overseas Equipment Non-Compliance With Australian Standards |
| c003 | p23 regulatory novelty | 71 | 226 | 31% | Regulatory Gap Slowing Novel Technology Approval |
| c005 | p39 external shock | 59 | 286 | 21% | COVID-19 Pandemic Disrupting Project Delivery |
| c009 | p20 cost-benefit | 56 | 381 | 15% | High Upfront Capital Preventing Positive Investment Return |
| c021 | p44 chicken-and-egg | **52** | 63 | **83%** | Feedstock Aggregation Chicken-and-Egg Market Failure |
| c588 | p29 misaligned incentives | **50** | 57 | **88%** | Intermediate Product Higher Value Diverts Feedstock from Final Product |
| c785 | p20 cost-benefit | **50** | 60 | **83%** | Green Fuel Cost Premium Blocks Offtaker Adoption |
| c004 | p39 external shock | 38 | 182 | 21% | Supply Chain Disruption Delaying Hardware Delivery |
| c008 | p20 cost-benefit | **36** | 45 | **80%** | Immature Electrolyser Market Limiting Commercial Viability |
| c634 | p20 cost-benefit | 35 | 110 | 32% | Low-Utilisation Asset Uncompetitive Due to Fixed Cost Spread |
| c042 | p06 chemical limit | 34 | 150 | 23% | Electrode Material Degradation From Chemical Incompatibility |
| c035 | p31 social licence | 31 | 88 | 35% | Community Opposition Threatening Large Infrastructure Project Viability |
| c038 | p31 social licence | **31** | 39 | **79%** | Hydrogen Safety Perception Barrier to Public Acceptance |
| c025 | p24 approval friction | 26 | 158 | 16% | Lengthy Multi-Party Permitting Delaying Construction Start |
| c742 | p47 demand-supply mismatch | **25** | 32 | **78%** | Transport Distance Erodes Export Cost Competitiveness |
| c766 | p16 lab-to-field | 23 | 66 | 35% | Demonstration-Stage Technology Requires Further R&D Before Upscaling |
| c505 | p16 lab-to-field | 22 | 63 | 35% | Lab-to-Pilot Equipment Mismatch Causes Process Translation Failure |
| c592 | p25 policy uncertainty | 21 | 134 | 16% | Unstable Policy Environment Deters Long-Lived Capital Investment |
| c949 | p50 feedstock variability | **21** | 27 | **78%** | Biomass and Biological Feedstock Variability Limits Scale-Up |
| c026 | p50 feedstock variability | **20** | 21 | **95%** | Biomass Handling Causing Bridging and Flow Blockages |
| c877 | p07 spatial constraint | 18 | 37 | 49% | Physical Transport Constraint Limits System Capacity or Efficiency |
| c691 | p05 knowledge gap | 17 | 41 | 41% | Immature Domestic Industry Elevating Project Risk |
| c500 | p36 planning inadequacy | 16 | 213 | 7% | Insufficient Technical Scoping Causes Installation Delays and Cost Overruns |

The single largest signal isn't lab-to-field translation or chemistry — it's **c002 *Overseas Equipment Non-Compliance With Australian Standards*** (72 records). My hand-picked memo missed this entirely. So did the FOAK use-case demo. The corpus is telling you: of all the things that bite hydrogen and bioenergy projects in Australia, the most-recorded structural mechanism is that the imported equipment doesn't meet AS/NZS standards out of the box.

Other things the data flagged that the hand-picked memo missed: **c005 COVID disruption**, **c004 supply-chain disruption**, **c035 community opposition**, **c038 hydrogen safety perception** as a social-licence problem (distinct from generic NIMBY), **c742 export transport distance**, **c025 multi-party permitting friction**.

---

## Concentration — mechanisms genuinely specific to H₂/bio

Clusters with ≥10 records and share ≥2× the 9.7% base rate. These are mechanisms that essentially only happen in this tech.

| cid | h2/bio | total | share | mechanism |
|---|---:|---:|---:|---|
| c1304 | 11 | 11 | **100%** | Hydrogen Combustion NOx Increase From Burner Type Change |
| c043 | 15 | 15 | **100%** | Renewable Product Specification Shortfall Without Fractionation |
| c616 | 11 | 11 | **100%** | High-Pressure Hydrogen Service Requires Pipeline Derating |
| c725 | 11 | 11 | **100%** | Dedicated Cropping Biofuel Pathways Cause Elevated Eutrophication Impacts |
| c026 | 20 | 21 | 95% | Biomass Handling Causing Bridging and Flow Blockages |
| c588 | 50 | 57 | 88% | Intermediate Product Higher Value Diverts Feedstock from Final Product |
| c785 | 50 | 60 | 83% | Green Fuel Cost Premium Blocks Offtaker Adoption |
| c1072 | 10 | 12 | 83% | Regulatory Classification Excludes Renewable Pathway From Incentive |
| c982 | 10 | 12 | 83% | Contaminant Concentration Elevates Waste Stream Regulatory Grade |
| c021 | 52 | 63 | 83% | Feedstock Aggregation Chicken-and-Egg Market Failure |
| c008 | 36 | 45 | 80% | Immature Electrolyser Market Limiting Commercial Viability |
| c608 | 12 | 15 | 80% | Feedstock Calorific Value Insufficient for Thermal Self-Sufficiency |
| c038 | 30 | 38 | 79% | Hydrogen Safety Perception Barrier to Public Acceptance |
| c742 | 25 | 32 | 78% | Transport Distance Erodes Export Cost Competitiveness |
| c949 | 21 | 27 | 78% | Biomass and Biological Feedstock Variability Limits Scale-Up |
| c794 | 15 | 20 | 75% | Contaminant Accumulation Restricts Flow And Reduces Capacity |
| c045 | 11 | 15 | 73% | Hydrogen Compliance Hazardous Area Reclassification Requiring Equipment Replacement |
| c831 | 13 | 21 | 62% | Physical Property Mismatch Prevents Infrastructure Repurposing |
| c030 | 11 | 19 | 58% | EPC Contractor Unfamiliarity With Novel Vendor Coordination |

These are where the H₂/bio reference class is *the* reference class — there's no useful cross-tech analog because the mechanism is chemistry- or feedstock-specific.

---

## Cross-tech transfer — what other tech is in these clusters

For the volume-ranked top clusters (where H₂/bio share is moderate, not dominant), the *other* records are the cross-tech reference class. Below: top non-H₂/bio categories and one illustrative analog per cluster.

### c002 — Overseas Equipment Non-Compliance With Australian Standards
**121 non-H₂/bio records**, distributed: 30 EV / 22 battery / 19 DER / 13 solar / 12 large-scale solar.
> [ARENA-DLV-1208-0029, *UNSW Addressing Barriers to Efficient Renewable Integration*, solar PV / system security]
> Many existing inverters comply with the older AS4777.2:2015, allowing reactive power injection up to ±100% of nameplate, which contradicts the newer AS4777.2:2020 requirement that limits reactive power injection above 95% nameplate active power…

**Read:** This is solar/inverter equipment hitting a standards mismatch at the same structural level a hydrogen plant's compressors will. The lessons-learned from EV/battery import projects on AS/NZS conformity are directly transferable.

### c003 — Regulatory Gap Slowing Novel Technology Approval
**155 non-H₂/bio records**, distributed: 37 battery / 32 DER / 28 EV / 13 solar / 8 renewables-for-industry.
> [ARENA-DLV-0648-0049, *Reactive Technologies — System Inertia Measurement*, system security]
> Australia's regulatory frameworks treat inertia services as a single product, which obscures distinctions between different forms of system strength services and limits the ability of providers to commercialise novel measurement and reporting capabilities…

**Read:** Different tech, identical mechanism — regulators classify a single product where the technical reality is a family. Battery-installation regulator unfamiliarity in 2017–2019 is the closest analog to where hydrogen sits in 2026.

### c021 — Feedstock Aggregation Chicken-and-Egg Market Failure
**11 non-H₂/bio records**, mostly renewables-for-industry / hybrid / CST.
> [ARENA-DLV-0633-0029, *Realising Electric Vehicle-to-Grid Services*, EV]
> Despite some success, dynamic incentive contracts didn't appear to attract many new participants and we suspect that this customer-focussed product alone wouldn't be enough to drive market growth without manufacturer-led offerings…

**Read:** V2G has the *same* chicken-and-egg structure (no aggregation without participation, no participation without aggregation). EV-to-grid trials' findings on market-make incentives transfer.

### c588 — Intermediate Product Diverts Feedstock From Final Product
**7 non-H₂/bio records**, mostly renewables-for-industry.
> [ARENA-DLV-0560-0069, *HILT CRC — upgrading iron ore for DRI*, renewables for industry]
> The BALIO process scenario with maximum by-products and maximum brine recycling (Scenario B) achieved an OPEX of USD 107/t, while the scenario with no by-products and no recycling (Scenario C) achieved OPEX of USD 175/t…

**Read:** Same economics — intermediate-product value capture changes process design. Iron-ore-DRI work is the cleanest analog.

### c785 — Green Fuel Cost Premium Blocks Offtaker Adoption
**10 non-H₂/bio records.**
> [ARENA-DLV-1009-0064, *APVI Silicon to Solar Study*, solar PV]
> Green premium products in advanced materials (such as low-carbon silicon, 4N silicon, and solar-grade silicon) are limited by the absence of standards and certification frameworks that would allow buyers to verify and pay premiums for low-carbon attributes…

**Read:** The premium-buyer problem is identical in low-carbon silicon and green hydrogen — no certification rail means no premium pricing. Solar-PV cost-premium work is directly applicable to H₂ offtake design.

### c008 — Immature Electrolyser Market Limiting Commercial Viability
**9 non-H₂/bio records.**
> [ARENA-DLV-0939-0067, *UniWave200 King Island Project — Wave Swell*, ocean energy]
> Without large global market adoption of wave energy generation a system or means of comparing wave energy converters against each other, in similar manner to how solar panels are compared, will not exist…

**Read:** Wave energy faces the same "no comparable market → no benchmarking → no procurement confidence" structural problem as electrolysers. Different tech, same loop.

### c038 — Hydrogen Safety Perception Barrier to Public Acceptance
**8 non-H₂/bio records**, mostly EV / CST / solar.
> [ARENA-DLV-0613-0064, *Solar Hybrid Fuels*, CST]
> Limited concept-development work also led to potential safety risks not being fully recognised and embedded into the project from the outset, requiring iterative redesign and approval cycles late in project execution.

**Read:** Adjacent rather than identical — public-perception specifics differ — but the *recognise-safety-risk-late* pattern shows up cross-tech.

### c742 — Transport Distance Erodes Export Cost Competitiveness
> [ARENA-DLV-0826-0019, *Tidal Energy in Australia*, ocean energy]
> Tidal energy resources at lower flow speeds (between 1–2 m/s) are abundant and located closer to demand centres, while higher-flow-speed sites (>2 m/s) tend to be in the Kimberley and Bass Strait regions far from demand centres, complicating value capture.

**Read:** Same shape — the best resource is far from the load. Ocean energy faces the export-distance problem in the same structural form as Pilbara H₂.

### c042 — Electrode Material Degradation From Chemical Incompatibility
**116 non-H₂/bio records**, mostly battery / solar / CST.
> [ARENA-DLV-0353-0008, *Fortescue — low temperature direct electrochemical*, renewables for industry]
> Direct ammonia synthesis using lithium-ion batteries faces irreversible degradation due to side reactions involving the same lithium ions critical for nitrogen reduction…

**Read:** Cross-tech is dense here because electrode-degradation chemistry is universal. The 116 non-H₂/bio records include the entire battery-cycling literature in this corpus.

### c500 — Insufficient Technical Scoping Causes Installation Delays
**197 non-H₂/bio records.**
> [ARENA-DLV-1233-0040, *My Energy Marketplace*, DER]
> A scoping review identified essential business and technical capabilities that were missing or inadequately defined in the original project plan, including data infrastructure, customer engagement strategies, and integration with existing energy management systems…

**Read:** The sample is enormous (197 non-H₂/bio records) and includes DER, battery, solar — every novel-tech project in the corpus has front-end scoping lessons applicable to a hydrogen demo.

### c592 — Unstable Policy Environment Deters Long-Lived Capital
**113 non-H₂/bio records.**
> [ARENA-DLV-1198-0067, *Renewable Energy Hub Marketplace*, renewables-for-industry]
> Policy uncertainty and changes in government priorities create challenges for long-term investment commitments in renewable energy hub developments, requiring proponents to adapt strategies and risk frameworks accordingly.

### c035 — Community Opposition Threatening Project Viability
**57 non-H₂/bio records**, mostly DER / large-scale solar / wind.
> [ARENA-DLV-0879-0123, CSP pilot, CST]
> Community opposition to renewable energy projects has emerged as a significant concern, with some projects facing delays or cancellation due to local resistance regarding land use, visual impact, and concerns about long-term environmental effects.

---

## What this approach found that the hand-picked one missed

Comparing v2 (this memo) to v1 (hand-picked):

| Mechanism | v1 hand-picked | v2 data-driven | Verdict |
|---|---|---|---|
| Overseas equipment non-compliance | missed | **#1 by volume** | data-driven correctly flagged it |
| Pandemic / supply-chain disruption | missed | #3, #8 | structural in this period; should be in any 2020–2025 reference class |
| Community opposition | missed | #12 | major issue regardless of tech |
| Hydrogen safety perception (specific) | missed | #13 | distinct from generic social licence |
| Multi-party permitting friction | missed | #14 | distinct from "regulatory framework gap" |
| Export transport distance | missed | #15 | tech-specific signal |
| Lab-to-field generally | included (top weight) | #16, #17 | v1 over-weighted; corpus says it's mid-rank |
| Front-end scoping | included | #23 | both flagged; v1 over-prioritised |
| Validation infeasibility | included (top weight) | did not appear in top-25 | v1 over-included; corpus doesn't strongly back it for H₂/bio |

The data-driven approach **finds 6 mechanisms the analyst missed** and **down-weights 2 the analyst over-emphasised**. This is the kind of correction the v2 substrate is supposed to enable.

---

## Reader takeaway

For a "what should I worry about for project X?" question, the better workflow is:

1. **Filter records by tech category(ies) matching the project.** No interpretive parent-scoping needed.
2. **Rank standout clusters by volume + concentration.** Volume tells you what bites this tech most; concentration tells you what's specific to this tech.
3. **For each volume-ranked cluster, examine non-filter members.** The non-matching tech in the same cluster is the cross-tech reference class — those are the analogous projects whose lessons transfer.
4. **For each concentration-ranked cluster, accept that the H₂/bio records *are* the reference class** — there's no analog; it's a tech-native mechanism.

The output is a properly-weighted, empirically-grounded reference class with built-in cross-tech transfer, and an analyst's role becomes *interpretation* of the data rather than *invention* of the categories.

---

## Caveats

- **Filter design.** I used `kb_category contains 'Hydrogen' OR 'Bioenergy'`. A project that's specifically biomass-to-hydrogen would be at the intersection — but no records carry both tags simultaneously in this corpus (multi-axis tagging is per-document, not per-axis). The union is the right call for a hypothetical project that draws from both.
- **Cluster size confound.** Big clusters get high volume by being big. Concentration share controls for this; both rankings together give a balanced read.
- **Cross-tech analog quality is variable.** Some clusters' non-filter members are tightly analogous (c042 electrode degradation, c003 regulatory novelty); others are loose (c038 safety perception → CST design risk). Reading the analog matters; the cluster name alone can mislead.
- **One filter per memo.** A real ARENA risk assessment might run several filters (Hydrogen, Bioenergy, Renewables-for-industry, regional, FOAK-stage) and intersect them. That's a follow-up.

Reproduction: `closure/output/use_case_demos/h2bio_cluster_standout.json` (volume + concentration rankings) and `h2bio_cluster_crosstech.json` (per-cluster cross-tech composition with analog records).
