# Parent-layer gap audit

Comparing the production 71-parent v2 layer against 126 canonical classes consolidated from the 50-run parent-derivation ensemble (4,150 raw parent labels). Question: are there valuable mechanism-class categories the ensemble proposed reliably that the production layer is missing?

**Method:** Sonnet 4.6 single call. For each canonical class, decide whether the 71-parent layer covers it cleanly, partially, or not at all. For non-clean matches, assign gap priority based on ensemble frequency and structural distinctness.

**Cost:** $0.20, 123s.

## Summary

| match_status | count | % |
|---|---:|---:|
| clean_match | 60 | 48% |
| partial_match | 42 | 34% |
| missing | 23 | 18% |

## Gap priorities (for partial_match + missing)

| priority | count |
|---|---:|
| low | 27 |
| medium | 25 |
| high | 13 |

## High-priority gaps (genuine missing categories ≥40% ensemble frequency)

| class | freq | name | rationale |
|---|---:|---|---|
| c62 | 88% | Schedule cascade and dependency delays | No parent covers sequential task dependency cascades where upstream delay propagates through coupled schedule into broader project loss. |
| c36 | 82% | Regulatory ambiguity, fragmentation, and jurisdictional conflict | No parent covers conflicting, overlapping, or ambiguous rules across multiple jurisdictions as a distinct mechanism from framework gaps. |
| c81 | 76% | Technology readiness and maturity gap | No parent covers insufficient technology or ecosystem maturity for the deployment context as a distinct failure mechanism. |
| c77 | 72% | Communications and connectivity failures | No parent specifically covers communication channel, network, or telemetry infrastructure unreliability or congestion as a distinct failure mechanism. |


## Medium-priority gaps (20-39% ensemble frequency or meaningful partial-match distinction)

| class | freq | match_status | best_match | name | rationale |
|---|---:|---|---|---|---|
| c22 | 68% | partial_match | p19 | Aggregation and granularity mismatch | p19 covers aggregate-individual divergence; c22 specifically targets masking of individual-unit conditions by aggregated metrics or controls. |
| c35 | 62% | partial_match | p23 | Regulatory framework misfit or obsolescence | p23 covers gap for novel contexts; c35 specifically names existing rules producing wrong outcomes because assumptions became obsolete. |
| c60 | 62% | partial_match | p33 | Behavioural rebound and unintended response | p33 covers behavioural friction; c60 specifically names rebound effects where intervention benefits are offset by induced compensatory behaviour. |
| c90 | 62% | partial_match | p57 | Sample, selection, and representativeness bias | p57 covers pilot design limits; c90 more broadly covers systematic unrepresentativeness in datasets or samples biasing inferences beyond trials. |
| c104 | 62% | missing | — | Funding instrument and milestone design misfit | No parent covers grant or funding instrument structure misaligned with actual delivery profile producing milestone-driven distortions. |
| c48 | 58% | missing | — | Procurement and tendering process distortions | No parent specifically covers procurement design or tender criteria producing suboptimal supplier or contract selection outcomes. |
| c78 | 58% | missing | — | Single point of failure and common-mode dependency | No parent covers single shared resource or centralised dependency creating correlated common-mode failure across multiple dependents. |
| c87 | 56% | missing | — | Lifecycle and end-of-life pathway gaps | No parent covers absent or inadequate end-of-life, recycling, or disposal pathways as a distinct failure mechanism. |
| c106 | 54% | missing | — | Manual processes and automation gaps | No parent covers reliance on manual processes creating throughput bottlenecks, errors, or scaling limits as a distinct mechanism. |
| c19 | 52% | partial_match | p47 | Geographic and locational mismatch | p47 covers spatial mismatch broadly; c19 specifically names geographic separation imposing transmission cost or feasibility penalty. |
| c56 | 50% | partial_match | p63 | Trust, perception, and social licence barriers | p63 covers inter-party trust erosion; c56 specifically addresses public/societal trust and perception blocking adoption independently of merit. |
| c68 | 50% | partial_match | p53 | Equipment degradation, wear, and ageing | p53 covers cumulative operational burden broadly; c68 specifically isolates progressive equipment degradation, wear, and ageing as the mechanism. |
| c18 | 48% | partial_match | p48 | Resource intermittency and variability | p48 covers system-level balancing stress; c18 focuses on resource-level intermittency affecting process continuity, a narrower distinct mechanism. |
| c92 | 48% | partial_match | p58 | Counterfactual and baseline measurement difficulty | p58 covers absent ground truth; c92 specifically names inability to construct defensible counterfactual or baseline for attribution. |
| c113 | 48% | partial_match | p27 | Stakeholder alignment and expectation divergence | p27 covers coordination overhead; c113 specifically names structurally divergent stakeholder interests preventing aligned action despite communication. |
| c23 | 46% | partial_match | p20 | Capital cost and upfront investment barriers | p20 covers cost-benefit threshold broadly; c23 specifically names upfront capital and payback horizon as the barrier mechanism. |
| c52 | 46% | partial_match | p34 | Personnel turnover and key-person dependency | p34 covers skill availability; c52 specifically names personnel turnover and key-person dependency disrupting knowledge continuity. |
| c97 | 46% | partial_match | p48 | Curtailment and headroom-driven output loss | p48 covers system-level balancing stress; c97 specifically names operational, contractual, or system constraints forcing curtailment of available output. |
| c28 | 44% | missing | — | Volatile or correlated input price exposure | No parent covers exogenous input/output price volatility or correlation destabilising project economics as a distinct mechanism. |
| c83 | 42% | partial_match | p05 | Mechanism understanding and scientific knowledge gap | p05 covers knowledge gaps broadly; c83 specifically names incomplete scientific or mechanistic understanding preventing reliable design or prediction. |
| c88 | 42% | missing | — | Hard-to-abate residual emissions | No parent covers structural ceiling from residual emissions lacking viable low-emission alternatives as a distinct mechanism. |
| c98 | 42% | missing | — | Visibility, observability, and monitoring gaps | No parent specifically covers inability to observe asset state or behaviour degrading operational decisions as a distinct mechanism. |
| c109 | 42% | missing | — | Unintended secondary consequences | No parent covers interventions triggering adverse second-order effects elsewhere through unanticipated system coupling. |
| c107 | 40% | partial_match | p68 | Long-horizon commitment and stranded asset risk | p68 covers accounting time-horizon mismatch; c107 specifically names commitment horizon exceeding policy or market stability creating stranding risk. |
| c82 | 34% | missing | — | First-of-kind execution and precedent absence | No parent covers elevated cost, risk, or effort specifically because no prior precedent or reference design exists. |


## Partial matches at high frequency (production parent fits but coarsely)

| class | freq | parent | name | rationale |
|---|---:|---|---|---|
| c02 | 94% | p59 | Data quality, format, and integration defects | p59 covers data infrastructure; c02 specifically targets quality, format, and schema defects in available data, a distinct mechanism. |
| c53 | 92% | p60 | Knowledge transfer and institutional memory loss | p60 covers cross-project dissemination; c53 targets intra-organisational knowledge transfer and institutional memory loss through turnover. |
| c24 | 88% | p20 | Cost structure and unit-economics infeasibility | p20 covers decision-threshold economics; c24 specifically addresses structural unit-cost infeasibility regardless of decision horizon. |
| c41 | 84% | p58 | Test, validation, and verification coverage gaps | p58 covers absent ground truth; c41 specifically targets testing procedures that fail to exercise real-world failure conditions or durations. |
| c27 | 78% | p43 | Investment risk and financing barriers | p43 covers risk-transfer and bankability gaps; c27 more broadly covers investor risk perception and return horizon barriers not requiring new instruments. |
| c55 | 78% | p31 | Stakeholder engagement and consultation failures | p31 covers opposition and social licence; c55 specifically names engagement process failures (timing, channel, depth) independent of substantive opposition. |
| c29 | 76% | p21 | Subsidy and incentive design distortions | p21 covers price signal distortion; c29 specifically names subsidy and rebate scheme design producing perverse eligibility or sizing outcomes. |
| c30 | 76% | p21 | Tariff and price-signal design distortions | p21 broadly covers distorted signals; c30 specifically targets tariff and settlement rule structural design as the distortion mechanism. |
| c86 | 76% | p68 | Externalities and lifecycle accounting omissions | p68 covers lifecycle time-horizon mismatch; c86 specifically names omission of externalities and system-boundary effects from decision metrics. |
| c22 | 68% | p19 | Aggregation and granularity mismatch | p19 covers aggregate-individual divergence; c22 specifically targets masking of individual-unit conditions by aggregated metrics or controls. |
| c35 | 62% | p23 | Regulatory framework misfit or obsolescence | p23 covers gap for novel contexts; c35 specifically names existing rules producing wrong outcomes because assumptions became obsolete. |
| c60 | 62% | p33 | Behavioural rebound and unintended response | p33 covers behavioural friction; c60 specifically names rebound effects where intervention benefits are offset by induced compensatory behaviour. |
| c90 | 62% | p57 | Sample, selection, and representativeness bias | p57 covers pilot design limits; c90 more broadly covers systematic unrepresentativeness in datasets or samples biasing inferences beyond trials. |
| c19 | 52% | p47 | Geographic and locational mismatch | p47 covers spatial mismatch broadly; c19 specifically names geographic separation imposing transmission cost or feasibility penalty. |
| c56 | 50% | p63 | Trust, perception, and social licence barriers | p63 covers inter-party trust erosion; c56 specifically addresses public/societal trust and perception blocking adoption independently of merit. |
| c68 | 50% | p53 | Equipment degradation, wear, and ageing | p53 covers cumulative operational burden broadly; c68 specifically isolates progressive equipment degradation, wear, and ageing as the mechanism. |
| c18 | 48% | p48 | Resource intermittency and variability | p48 covers system-level balancing stress; c18 focuses on resource-level intermittency affecting process continuity, a narrower distinct mechanism. |
| c92 | 48% | p58 | Counterfactual and baseline measurement difficulty | p58 covers absent ground truth; c92 specifically names inability to construct defensible counterfactual or baseline for attribution. |
| c113 | 48% | p27 | Stakeholder alignment and expectation divergence | p27 covers coordination overhead; c113 specifically names structurally divergent stakeholder interests preventing aligned action despite communication. |
| c23 | 46% | p20 | Capital cost and upfront investment barriers | p20 covers cost-benefit threshold broadly; c23 specifically names upfront capital and payback horizon as the barrier mechanism. |
| c52 | 46% | p34 | Personnel turnover and key-person dependency | p34 covers skill availability; c52 specifically names personnel turnover and key-person dependency disrupting knowledge continuity. |
| c97 | 46% | p48 | Curtailment and headroom-driven output loss | p48 covers system-level balancing stress; c97 specifically names operational, contractual, or system constraints forcing curtailment of available output. |
| c83 | 42% | p05 | Mechanism understanding and scientific knowledge gap | p05 covers knowledge gaps broadly; c83 specifically names incomplete scientific or mechanistic understanding preventing reliable design or prediction. |
| c107 | 40% | p68 | Long-horizon commitment and stranded asset risk | p68 covers accounting time-horizon mismatch; c107 specifically names commitment horizon exceeding policy or market stability creating stranding risk. |
