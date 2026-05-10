# Attention-degradation hypothesis: test design

## Hypothesis

The growth of the cluster catalogue causes Pass 1 batched classification (200 records vs N clusters in one call) to miss true matches as N grows. The post-P1 orphan rate trajectory (78% → 44% plateau → 26% by iter ~110) is a combination of catalogue-coverage growth (drives rate down) and attention dilution (drives rate up); the small uptick in new-cluster-creation rate around iter 90-110 is a possible signature of attention degradation crossing a threshold around catalogue size 700.

## Test design

**Controlled A/B comparison at fixed catalogue snapshots.**

For one or more target iterations (suggested: iters 30, 70, 110):

1. **Reconstruct catalogue snapshot at iter K start** = current catalogue minus all clusters with creation_iter ≥ K. Cluster creation_iter is derivable from `corpus_assignments.jsonl` as the minimum iter where each cluster_id ≥ c500 appears as `status="new_cluster"`. Seed clusters (cluster_id < c500) are always present.

2. **Pull the 200 records** from `corpus_assignments.jsonl` with `iteration == K`. Look up full record metadata in `filter_input.jsonl`.

3. **Arm A — batched (replication):** run the same 200 records through Pass 1 with the reconstructed catalogue, batch=200, exactly as the original sweep ran.

4. **Arm B — per-record cached:** issue 200 separate Sonnet calls, each containing the cached catalogue prefix + one record. Use prompt caching (`cache_control` on the catalogue portion) so the catalogue is read once and reused across all 200 calls.

5. **Comparison metrics:**
   - **Replication fidelity** (Arm A vs original sweep): how often does the same prompt produce the same answer at temperature=0? Establishes nondeterminism baseline.
   - **Recovery rate** (Arm A "orphan" → Arm B "classified"): records that batched Pass 1 missed but per-record correctly placed. This is the attention-dilution effect.
   - **Disagreement rate** (Arm A "classified to X" vs Arm B "classified to Y" or "orphan"): records where the two regimes give different answers. Measures the precision difference.
   - **Sample manual inspection** of recovered records (10-20 per arm): are Arm B's classifications correct? Cross-check against the cluster's mechanism_signature.

## Expected outcome under the attention hypothesis

- Recovery rate at iter 30 (catalogue ~340): low, maybe 5-10% of orphans recovered
- Recovery rate at iter 70 (catalogue ~580): moderate, 15-25%
- Recovery rate at iter 110 (catalogue ~750): higher, 25-35%
- Disagreement rate scales similarly

Monotonic growth in recovery rate with catalogue size = strong support for attention dilution.
Flat recovery rate = attention is fine, the orphan rate is genuinely about catalogue coverage.

## Implementation cost

Per A/B run at one iter:
- Arm A: 1 batched call ≈ $0.20 sync
- Arm B: 200 cached calls ≈ $0.79 sync ($0.40 batch API)
- Total per iter: ~$1.00 sync

Three iters tested: ~$3 sync. Trivial.

## Probity / methodology notes

- The signatures of clusters in the iter-K snapshot are identical to their final-state signatures, by the immutability rule. So Arm A and Arm B both classify against the *same exact text* the original sweep saw.
- This is a clean experiment because the procurement-probity rule already gave us this property "for free."
- Running the test does NOT modify the production catalogue or assignments. Output goes to a separate file.

## Run after main sweep completes

This is queued for after the corpus sweep finishes. Implementation slot: `code/test_attention_hypothesis.py`.
