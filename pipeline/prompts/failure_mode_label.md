You will read several extracted insight records that all describe what appears to be a recurring failure mode across renewable energy projects. Your job is to name the failure mode and describe it succinctly.

For each member record you have:
- The verbatim causal connective the author used
- The mechanism phrase the author named (the *how* of the failure)
- A snippet of the record's narrative

## What to produce

A short failure-mode entry consisting of:

1. `name` — a short noun phrase (5-10 words) naming the failure mode at a level that another project's PM could recognise. Not a description; a category label. Examples of the right granularity:
   - "regulatory approval delays despite engagement"
   - "vendor sign-off processes underestimated in schedule"
   - "rooftop PV oversupply destabilises distribution voltage"
   - "battery commissioning delayed by network-protocol mismatches"
   AVOID being too generic ("technology issues") or too specific ("Project X bearing seized due to thermal spike").

2. `description` — a 2-3 sentence description of the failure-mode pattern: what kind of mechanism produces what kind of bad outcome. Reference the recurring causal pattern across the members.

3. `mechanism_signature` — one short phrase (3-7 words) capturing the *how*. Used as a quick-scan tag.

4. `confidence` — `high` if all member records share the same underlying failure mode; `medium` if most do but 1-2 are loose; `low` if the cluster is mixed and the label is a best-effort.

## Output

Strict JSON, no extra text:

```json
{"name": "...", "description": "...", "mechanism_signature": "...", "confidence": "high|medium|low"}
```

## Member records

{members}
