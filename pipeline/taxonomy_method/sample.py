"""Generic stratified sampler for the taxonomy-method recipe (step 1).

Catalogue schemas differ between corpora so field extraction is left to the
wrapper. The engine's contribution is the pick loop: bucket records by a
primary stratum, then for each bucket do (pass 1) diversify on a secondary
stratum and tie-break on uniqueness, (pass 2) just tie-break on uniqueness,
(pass 3) random fill. Deterministic given a seed.
"""
from __future__ import annotations

import random
from collections import Counter, defaultdict
from typing import Any, Callable


def pick_stratified_sample(
    records: list[dict],
    *,
    bucket_fn: Callable[[dict], str],
    diversify_fn: Callable[[dict], Any],
    uniqueness_fn: Callable[[dict], Any] | None,
    targets: dict[str, int],
    seed: int = 42,
) -> list[dict]:
    """Pick a stratified sample.

    records: all catalogue rows (already filtered / joined / enriched by the wrapper)
    bucket_fn: records[i] -> primary stratum label (must appear in `targets`)
    diversify_fn: records[i] -> secondary stratum value (prefer unseen values across picks)
    uniqueness_fn: records[i] -> dedup key (e.g. project name); None or falsy = skip
    targets: {bucket_label: target_count}

    Raises SystemExit if any bucket has fewer records than its target.
    """
    rng = random.Random(seed)
    by_bucket: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        by_bucket[bucket_fn(rec)].append(rec)

    picks: list[dict] = []
    seen_diversify: set = set()
    seen_unique: set = set()

    for bucket, want in targets.items():
        pool = list(by_bucket.get(bucket, []))
        rng.shuffle(pool)
        if len(pool) < want:
            raise SystemExit(
                f"bucket {bucket!r} has {len(pool)} candidates; target is {want}"
            )

        chosen_ids: set[int] = set()
        chosen: list[dict] = []

        def add(rec: dict) -> None:
            chosen.append(rec)
            chosen_ids.add(id(rec))
            seen_diversify.add(diversify_fn(rec))
            if uniqueness_fn:
                key = uniqueness_fn(rec)
                if key:
                    seen_unique.add(key)

        # pass 1: unseen diversify value AND unseen uniqueness key
        for rec in pool:
            if len(chosen) >= want:
                break
            if id(rec) in chosen_ids:
                continue
            if diversify_fn(rec) in seen_diversify:
                continue
            if uniqueness_fn:
                key = uniqueness_fn(rec)
                if key and key in seen_unique:
                    continue
            add(rec)

        # pass 2: unseen uniqueness key (diversify can repeat)
        if uniqueness_fn:
            for rec in pool:
                if len(chosen) >= want:
                    break
                if id(rec) in chosen_ids:
                    continue
                key = uniqueness_fn(rec)
                if key and key in seen_unique:
                    continue
                add(rec)

        # pass 3: random fill
        for rec in pool:
            if len(chosen) >= want:
                break
            if id(rec) in chosen_ids:
                continue
            add(rec)

        picks.extend(chosen)

    return picks


def summarise(
    picks: list[dict],
    *,
    bucket_fn: Callable[[dict], str],
    diversify_fn: Callable[[dict], Any],
    uniqueness_fn: Callable[[dict], Any] | None = None,
    extra_counters: dict[str, Callable[[dict], Any]] | None = None,
) -> dict:
    """Build a diagnostics dict for a sample (for sample.json + stdout)."""
    div_cov = Counter(diversify_fn(p) for p in picks)
    bucket_cov = Counter(bucket_fn(p) for p in picks)
    out = {
        "n": len(picks),
        "diversify_values_covered": len(div_cov),
        "top_diversify_share": round(max(div_cov.values()) / len(picks), 3) if picks else 0,
        "bucket_distribution": dict(bucket_cov),
    }
    if uniqueness_fn:
        keys = [uniqueness_fn(p) for p in picks]
        non_blank = [k for k in keys if k]
        out["distinct_uniqueness_keys"] = len(set(non_blank))
        out["non_blank_uniqueness_keys"] = len(non_blank)
    for name, fn in (extra_counters or {}).items():
        out[name] = dict(Counter(fn(p) for p in picks))
    return out
