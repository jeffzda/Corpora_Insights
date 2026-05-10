"""Propose → empirically test → revise loop for axis derivation.

Removes human curation from the orthogonality verdict. The loop:
  1. Sonnet proposes 2-4 axes blind (using propose_axes prompt as-is).
  2. Haiku tags a deterministic sub-sample of findings.
  3. Compute pairwise NMI between every axis pair.
  4. If the worst pair exceeds threshold, pack the diagonal-collapse
     evidence into a revise prompt and ask Sonnet to fix it.
  5. Repeat until all pairs pass or max_rounds reached.

Engine-level — no corpus-specific logic. Wrappers supply prompt
substitutions only.
"""
from __future__ import annotations

import json
import math
import random
from collections import Counter
from itertools import combinations
from pathlib import Path

from .propose_axes import propose_axes
from .tag_sync import tag_findings_sync

REVISE_PROMPT = Path(__file__).parent / "prompts" / "revise_axes.md"


def _pairwise_nmi(tags: dict[int, dict], axes: dict) -> dict[tuple[str, str], dict]:
    names = [a["name"] for a in axes["axes"]]
    valid_vals = {a["name"]: {v["name"] for v in a["values"]} for a in axes["axes"]}
    out = {}
    for a, b in combinations(names, 2):
        pairs = [(t.get(a), t.get(b)) for t in tags.values()
                 if t.get(a) in valid_vals[a] and t.get(b) in valid_vals[b]]
        n = len(pairs)
        if n == 0:
            out[(a, b)] = {"nmi": 0.0, "n": 0, "top": []}
            continue
        cx = Counter(x for x, _ in pairs)
        cy = Counter(y for _, y in pairs)
        cp = Counter(pairs)
        mi = sum((c / n) * math.log2((c / n) / ((cx[x] / n) * (cy[y] / n)))
                 for (x, y), c in cp.items())
        hx = -sum((c / n) * math.log2(c / n) for c in cx.values())
        hy = -sum((c / n) * math.log2(c / n) for c in cy.values())
        nmi = mi / max(min(hx, hy), 1e-9)
        top = []
        for (x, y), c in cp.most_common(8):
            e = cx[x] * cy[y] / n
            top.append({"x": x, "y": y, "obs": c, "exp": round(e, 1), "ratio": round(c / e, 2)})
        out[(a, b)] = {"nmi": nmi, "n": n, "top": top}
    return out


def _format_evidence(top: list[dict]) -> str:
    return "\n".join(
        f"  - {c['obs']:3d}  (exp {c['exp']:5.1f}, {c['ratio']:.1f}x)  {c['x']} × {c['y']}"
        for c in top if c["ratio"] >= 1.5
    ) or "  (no single cell stood out; collapse is diffuse)"


def _format_all_pairs(nmi: dict[tuple[str, str], dict], threshold: float) -> str:
    lines = []
    for (a, b), v in sorted(nmi.items(), key=lambda kv: -kv[1]["nmi"]):
        flag = " ❌ FAIL" if v["nmi"] > threshold else " ✓ pass"
        lines.append(f"  - {a} × {b}: NMI {v['nmi']:.1%}{flag}")
    return "\n".join(lines)


def derive_axes_with_validation(
    findings: list[dict],
    out_dir: Path,
    *,
    propose_substitutions: dict[str, str],
    nmi_threshold: float = 0.15,
    max_rounds: int = 4,
    sample_size: int = 200,
    seed: int = 42,
    propose_prompt_path: Path | None = None,
) -> dict:
    """Run the propose→tag→measure→revise loop. Writes per-round artifacts."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    sub = list(findings)
    rng.shuffle(sub)
    sub = sub[:sample_size]
    (out_dir / "validation_subsample.json").write_text(json.dumps(sub, indent=1))

    history = []
    propose_kwargs = {"prompt_path": propose_prompt_path} if propose_prompt_path else {}
    axes = propose_axes(
        findings,
        out_path=out_dir / "axes_round0.json",
        prompt_substitutions=propose_substitutions,
        **propose_kwargs,
    )

    for rnd in range(max_rounds):
        print(f"\n=== round {rnd}: tagging sub-sample of {len(sub)} ===")
        tags = tag_findings_sync(
            sub, axes,
            tags_out=out_dir / f"validation_tags_round{rnd}.json",
            concurrency=20,
        )
        nmi = _pairwise_nmi(tags, axes)
        report = {
            "round": rnd,
            "axes": [a["name"] for a in axes["axes"]],
            "pairs": [
                {"a": a, "b": b, "nmi": round(v["nmi"], 4), "n": v["n"]}
                for (a, b), v in nmi.items()
            ],
        }
        (out_dir / f"validation_report_round{rnd}.json").write_text(
            json.dumps(report, indent=2)
        )
        history.append(report)
        print(_format_all_pairs(nmi, nmi_threshold))

        worst = max(nmi.items(), key=lambda kv: kv[1]["nmi"])
        worst_pair, worst_v = worst
        if worst_v["nmi"] <= nmi_threshold:
            print(f"\n✓ all pairs pass at threshold {nmi_threshold:.0%}")
            (out_dir / "axes_final.json").write_text(json.dumps(axes, indent=2))
            (out_dir / "validation_history.json").write_text(json.dumps(history, indent=2))
            return axes
        if rnd == max_rounds - 1:
            print(f"\n✗ max rounds reached; worst pair {worst_pair} still {worst_v['nmi']:.1%}")
            break

        revise_subs = {
            **propose_substitutions,
            "sample_size": str(len(sub)),
            "threshold": f"{nmi_threshold:.0%}",
            "worst_pair": f"{worst_pair[0]} × {worst_pair[1]}",
            "worst_nmi": f"{worst_v['nmi']:.1%}",
            "worst_evidence": _format_evidence(worst_v["top"]),
            "all_pairs": _format_all_pairs(nmi, nmi_threshold),
            "prior_axes": json.dumps(axes, indent=2),
            "n_findings": str(len(findings)),
        }
        axes = propose_axes(
            findings,
            out_path=out_dir / f"axes_round{rnd + 1}.json",
            prompt_substitutions=revise_subs,
            prompt_path=REVISE_PROMPT,
        )

    (out_dir / "axes_final.json").write_text(json.dumps(axes, indent=2))
    (out_dir / "validation_history.json").write_text(json.dumps(history, indent=2))
    return axes
