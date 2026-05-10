Your previous axis proposal failed empirical orthogonality testing.

We tagged a {{sample_size}}-finding sub-sample against your axes with a
fast classifier and measured pairwise normalised mutual information
(NMI). Independent axes have NMI near 0%; perfectly redundant axes
have NMI near 100%. Threshold: {{threshold}}.

## Worst pair
**{{worst_pair}}** — NMI {{worst_nmi}}.

Diagonal collapses (observed cells, with ratio over what independence
would predict):

{{worst_evidence}}

These cells are evidence that the two axes are encoding the same latent
dimension from slightly different angles.

## All pairwise NMI
{{all_pairs}}

## Your task
Revise the axis set to fix the failing pair. Pick exactly one of:

1. **Drop** one of the two muddied axes. Cleanest fix when one axis is
   strictly less informative than the other.
2. **Re-pose** one of the two axes so its values cut ACROSS the other's
   values rather than parallel to them. Test mentally: for any value of
   axis A, are findings at that value spread over multiple values of axis
   B? If not, you haven't re-posed.
3. **Merge** specific overlapping values within the offending axes (e.g.
   if `axis_A.value_x` and `axis_B.value_y` are restating each other,
   drop one).

Do NOT just rename values — that won't change the empirical NMI.

Return the same JSON shape as the original proposal, with the full
revised axis set (including any axes that were already passing). Include
a `revision_notes` field explaining what you changed and why.

Original axes for reference:

{{prior_axes}}

Findings (same {{n_findings}} as before):

