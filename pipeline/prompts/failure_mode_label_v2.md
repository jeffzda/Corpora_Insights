You will read several extracted insight records that have been clustered together because their failure-mechanism descriptions are semantically similar. Your job is to name the failure-mode pattern they share.

For each member record you have:
- The verbatim causal connective the author used
- The mechanism phrase the author named (the *how* of the failure)
- A snippet of the record's narrative

## Critical labelling discipline

**Find the broadest common thread that genuinely fits ALL the members, not just the dominant theme.** Clusters often contain members at different granularities — some specific (e.g. "inverter firmware compliance not updated") and some broader (e.g. "third-party device protocol limitations discovered late"). The right label captures what's *common to every member*, not the most vivid or specific instance.

Anti-pattern to avoid: picking the label that fits the **majority** of members and ignoring 2-3 outliers. The outliers are part of the cluster's actual semantic shape; if your label doesn't fit them, the label is too narrow. Instead, **abstract upward** to a broader label that covers them.

If 4 of 9 members are about specific inverter firmware compliance and 5 of 9 are about other device-protocol limitations and network-signal staleness, the right label is **"device protocol and data-interface gaps surfacing during integration"** — broader, but fits all 9. NOT "inverter firmware and protocol compliance discovered too late" — narrower, fits only 4.

When the cluster genuinely is uniform (all members concretely about the same thing), use the specific label. When members span related but distinct sub-types, abstract upward. Read each member and ask: "would the label still fit this one?" If not, broaden.

## What to produce

A short failure-mode entry consisting of:

1. `name` — a short noun phrase (5-10 words) naming the failure-mode pattern at a level that fits all members. PM-recognisable; not so abstract as to be unhelpful ("technology problems"); not so narrow that 2-3 members don't fit. Examples of the right granularity:
   - "device protocol and data-interface gaps surfacing during integration"
   - "regulatory approval delays despite engagement"
   - "rooftop PV oversupply destabilises distribution voltage"
   - "novel-process discovery during execution causes integration delays"

2. `description` — 2-3 sentences describing what kind of mechanism produces what kind of bad outcome. Reference the recurring causal pattern across the members. Mention briefly that members vary in specificity if they do.

3. `mechanism_signature` — one short phrase (3-7 words) capturing the *how*. The shared mechanism, not the most specific instance.

4. `confidence`:
   - `high` if all members share genuinely the same underlying failure mode (uniform cluster)
   - `medium` if most do but 1-3 are loose fits or the label had to abstract upward to fit everyone
   - `low` if the cluster is mixed and the label is a best-effort common abstraction

Use `medium` honestly when you've abstracted upward to fit outliers — it's a real signal about the cluster's coherence.

## Output

Strict JSON, no extra text:

```json
{"name": "...", "description": "...", "mechanism_signature": "...", "confidence": "high|medium|low"}
```

## Member records

{members}
