# Sample of input rows sent to Opus for threshold-selection

The full input has 126 rows. Each row is one canonical class formatted as:

```
[class_id] freq=X% — name :: definition :: mechanism_criterion
```

Sample rows from different positions in the frequency distribution:

## Top of list (highest frequency, ≈100%)

```
[c03] freq=100% — Measurement and sensing limitations :: A sensor, instrument, or measurement method fails to detect, resolve, or accurately capture the target physical quantity due to its physical, placement, calibration, or environmental limits. :: Failure traces to an instrument's intrinsic capability or deployment limits, not to data handling.
```

```
[c04] freq=100% — Model, simulation, and forecast inaccuracy :: A model, simulation, or forecast produces outputs that systematically diverge from reality because of its assumptions, parameters, scope, or training data. :: Failure stems from a representational/parameterisation gap in a model or forecast, not from missing inputs.
```

```
[c06] freq=100% — Material, chemical, and physical-property limits :: A failure is driven by an intrinsic physical, chemical, thermodynamic, or material property limit of the system. :: An inherent material/chemical/thermodynamic property is the binding constraint.
```

## Middle of list (around 60-70%, rank 50-53)

```
[c49] freq=68% — Vendor lock-in and proprietary closure :: Proprietary technology, IP, certification, or contracts restrict third-party access, integration, or substitution. :: Vendor proprietary control prevents independent action by other parties.
```

```
[c67] freq=68% — Manufacturing variability and fabrication defects :: Defects, variability, or yield loss introduced during manufacturing or fabrication degrade product quality or performance. :: Fabrication/manufacturing process introduces defects or variation in produced items.
```

```
[c16] freq=66% — Temporal mismatch between supply and demand :: Supply and demand are misaligned in time (seasonal, diurnal, transient) such that the resource cannot be used when needed. :: Two flows are individually adequate but their temporal profiles do not coincide when alignment is required.
```

## Lower tier (around 30-40%, near the recommended threshold)

```
[c107] freq=40% — Long-horizon commitment and stranded asset risk :: Asset lifetime or commitment horizon exceeds the stability window of policy, market, or technology, creating stranding or lock-in risk. :: Mismatch between asset horizon and decision-maker/policy horizon creates stranding exposure.
```

```
[c101] freq=38% — System inertia and synchronous-service shortfall :: Bulk-system inertia, system strength, or services historically provided by synchronous plant become inadequate as the generation mix shifts. :: Loss of system-wide synchronous services (distinct from individual IBR-grid interactions) is the binding factor.
```

```
[c69] freq=36% — Latent defects revealed in operation :: A pre-existing latent defect or rare failure mode is undetectable at testing and only manifests during field operation or stress. :: Pre-existing fault revealed only by integration/operation/triggering event.
```

## Long tail (lowest frequencies)

```
[c123] freq=8% — Coordinated-control granularity and addressing limits :: Distributed assets cannot be effectively coordinated because architecture, addressing, or telemetry granularity is insufficient for operational requirement. :: DER coordination/aggregation architecture cannot scale or differentiate at required granularity.
```

```
[c124] freq=6% — Pre-existing/concurrent activity interference :: A pre-existing or concurrent activity, installation, or condition interferes with the intended deployment or operation. :: Concurrent or co-existing activity creates unintended operational impact.
```

```
[none] freq=0% — No fit :: Label does not cleanly fit any defined canonical class. :: No assignment to a defined class is appropriate.
```


Total prompt size with all 126 rows + scaffolding: ~40,300 chars (~10,100 tokens).
