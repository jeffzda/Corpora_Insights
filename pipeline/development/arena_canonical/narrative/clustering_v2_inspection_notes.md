# Clustering v2 — first inspection


## Threshold 0.60

- 10,321 clusters; 4,694 singletons (45%)
- 4,854 small (2-5); 740 medium (6-20); 33 large (>20)
- Largest cluster: 98 records


### Top 8 largest clusters

- **Cluster 9295** (98 records, 57 events, 8 projects, axes: o88% m54% -100%)
  - Sample: "Project EDGE consumer research found that current VPP customers want a greater share of VPP benefits, indicating that cu..."
- **Cluster 8313** (44 records, 26 events, 1 projects, axes: o90% m61% s63% -100%)
  - Sample: "For long rural feeders with long SWER connections, adjusting off-load tap changers provides only limited benefit because..."
- **Cluster 8611** (40 records, 15 events, 4 projects, axes: o95% -100%)
  - Sample: "Voltage sags are defined as reductions in RMS grid voltage for short durations (milliseconds to several seconds) to 10–9..."
- **Cluster 8302** (37 records, 22 events, 20 projects, axes: o67% m86% -100%)
  - Sample: "High levels of reverse power flow caused by solar PV can lead to network interruptions. Energy Queensland identifies loc..."
- **Cluster 8195** (37 records, 24 events, 9 projects, axes: m78% s56% -100%)
  - Sample: "Static operating envelopes set fixed import and export limits for electricity customers based on worst-case scenarios, a..."
- **Cluster 8805** (33 records, 17 events, 5 projects, axes: o78% m78% -100%)
  - Sample: "Establishing accurate baselines was identified as a significant challenge for certain load types within the demand respo..."
- **Cluster 6575** (31 records, 12 events, 6 projects, axes: o90% m71% -100%)
  - Sample: "The AEMO MP5F API was found to be functional but AEMO was still working through operational issues ('kinks') at the time..."
- **Cluster 9132** (31 records, 19 events, 4 projects, axes: o90% m71% -100%)
  - Sample: "The SA Power Networks and AusNet Flexible Exports Trial found a lack of compatible technology capable of flexible export..."

### Random sample of medium clusters


- **Cluster 7487** (6 records, axes: o100% m83% -100%):
  - `ARENA-DLV-1344-0026`: Tesla (the VBB supplier) was required to conduct thorough lab testing of the modulation functionality before VBB could be confirme
  - `ARENA-DLV-1344-0034`: VBB lenders required approval from the Australian Energy Regulator (AER) before VBB could be used as a modulator. This regulatory 
  - `ARENA-DLV-1345-0038`: A requirement from VBB lenders for AER approval before VBB could be used as a modulator was not anticipated in the early project s
  - `ARENA-DLV-1346-0035`: VBB lenders required a 'No Action' letter from AER before consenting to VBB being used as a modulator. Obtaining this letter was a
  - `ARENA-DLV-1346-0043`: The AER approval requirement for VBB to be used as a modulator was not anticipated in early project planning. This unanticipated r

- **Cluster 8923** (6 records, axes: o100% m83% s100% -100%):
  - `ARENA-DLV-0656-0003`: Under Scenario 1 (no network or market charges on LEM volumes), consumers could save 31–41% and prosumers could gain 54–107% over 
  - `ARENA-DLV-0656-0004`: Under Scenario 2 (symmetric network and market charges on both imports and exports), consumers saved 11.4–22.9% but prosumers lost
  - `ARENA-DLV-0656-0085`: The LEM modelling found that under Scenario 2, the retailer's loss was only 1.8% of counterfactual revenues (reflecting lost margi
  - `ARENA-DLV-0656-0086`: The LEM modelling found that under Scenario 1, buyers collectively could save 31–41% on LEM-traded volumes and prosumers could gai
  - `ARENA-DLV-0656-0091`: The LEM modelling found that under Scenario 3, the retailer suffered a net loss of only 2.7% ($4,897) on counterfactual revenues o

- **Cluster 8522** (4 records, axes: o75% m75% s75% -100%):
  - `ARENA-DLV-0275-0015`: Fronius had not yet released its control API at the time of reporting, meaning battery control functionality via Fronius inverters
  - `ARENA-DLV-0338-0020`: The Tesla Powerwall 1 was only compatible with a SolarEdge inverter at the start of the trial, while all other Phase 1 packs (exce
  - `ARENA-DLV-0593-0057`: The Tesla Powerwall 1 was only compatible with a Solar Edge inverter at the beginning of the trial, while all other packs (excludi
  - `ARENA-DLV-0594-0025`: Tesla and Samsung batteries operate at higher voltages than the SMA Sunny Island inverter and are therefore incompatible with it. 

- **Cluster 9007** (7 records, axes: m100% -100%):
  - `ARENA-DLV-0248-0070`: Under scenario 1, high retail import prices during the day provide an incentive to discharge even when electricity supply from the
  - `ARENA-DLV-0618-0051`: Retailers exposed to the energy spot market incur a cost when their customers' rooftop PV systems export to the grid during negati
  - `ARENA-DLV-0656-0049`: Current network cost recovery is weighted heavily towards volumetric (c/kWh) charges applied only to consumption. Prosumers avoid 
  - `ARENA-DLV-0656-0050`: A peak demand charge (ideally based on coincident peak demand) operating symmetrically as a negative demand charge or rebate for p
  - `ARENA-DLV-0656-0084`: The LEM modelling found that under Scenario 2, applying a volumetric export charge to prosumers could create strong incentives for

- **Cluster 8525** (6 records, axes: o83% m100% -100%):
  - `ARENA-DLV-0452-0055`: Compatibility issues between battery storage systems and inverters caused some inverters to go offline during VPP events, with the
  - `ARENA-DLV-0689-0010`: Inverter instability is not necessarily caused by a single rogue inverter but by a mutually incompatible combination of inverters 
  - `ARENA-DLV-0814-0113`: The Pilot demonstrated that PV inverters were not available at some times when they were on 'night mode', contributing to the dyna
  - `ARENA-DLV-0896-0046`: PV inverters (SMA Sunny Tripower) configured to comply with AS4777.2 became unstable at mid-range power levels (400–500 kW) when o
  - `ARENA-DLV-1078-0057`: EnergyAustralia's VPP program encountered compatibility issues between battery storage systems and battery inverters, causing inve

- **Cluster 6365** (6 records, axes: m100% -100%):
  - `ARENA-DLV-0234-0059`: The relatively small geographical size of the SWIS compared with the eastern states grid substantially limits the ability to widel
  - `ARENA-DLV-0339-0069`: Victorian wind has a strong anti-correlation with solar, which gains more relevance in later years and starts to impact the value 
  - `ARENA-DLV-0578-0051`: Solar generation is highly correlated across the NEM, and wind in South Australia is highly correlated with wind in Victoria (62% 
  - `ARENA-DLV-1043-0026`: Australian wind farms are clustered in southern regions with strong wind resource and electrical infrastructure, but these regions
  - `ARENA-DLV-1043-0087`: The study identified that Tasmania was excluded from the generation profile analysis due to the relatively poor solar resource in 