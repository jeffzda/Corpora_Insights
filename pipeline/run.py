#!/usr/bin/env python3
"""CLI entry point for the pipeline.

Usage:
    python -m pipeline.run --domain arena --step event_type --dry-run
    python -m pipeline.run --domain arena --step verify --batch submit
    python -m pipeline.run --domain arena --step discover --all
    python -m pipeline.run --domain arena --step classify --all --batch submit
    python -m pipeline.run --domain arena --step matrix

    # Or run individual modules directly:
    python -m pipeline.event_type --domain arena --dry-run
    python -m pipeline.verify --domain arena --batch submit
    python -m pipeline.discover --domain arena --all
"""

import argparse
import sys
from pathlib import Path

from pipeline.config import DomainConfig


STEPS = {
    # Ingestion / preprocessing
    "ingest":         "pipeline.ingest",
    "parse":          "pipeline.parse",
    "marker_convert": "pipeline.ingest.marker_convert",

    # Canonical 11-stage pipeline (corpus-agnostic engine + prompt_tokens config)
    "extract":            "pipeline.stages.s01_extract.stage",
    "group_events":       "pipeline.stages.s02_group_events.stage",
    "label_record_types": "pipeline.stages.s03_label_record_types.stage",
    "cluster_filter":     "pipeline.stages.s04_cluster_filter.stage",
    "cluster_seed":       "pipeline.stages.s05_cluster_seed.stage",
    "cluster_sweep":      "pipeline.stages.s06_cluster_sweep.stage",
    "cluster_singleton":  "pipeline.stages.s07_cluster_singleton.stage",
    "cluster_residual":   "pipeline.stages.s08_cluster_residual.stage",
    "parent_derive":      "pipeline.stages.s09_parent_derive.stage",
    "parent_assign":      "pipeline.stages.s10_parent_assign.stage",
    "theme_audit":        "pipeline.stages.s11_theme_audit.stage",

    # Glossary sub-pipeline (parallel branch from markdown — see pipeline/glossary/)
    "glossary_candidates":      "pipeline.glossary.g01_regex_candidates.stage",
    "glossary_ner":             "pipeline.glossary.g02_ner_candidates.stage",
    "glossary_normalise":       "pipeline.glossary.g03_normalise.stage",
    "glossary_define":          "pipeline.glossary.g04_define.stage",
    "glossary_define_followup": "pipeline.glossary.g05_define_followups.stage",
    "glossary_merge":           "pipeline.glossary.g06_merge.stage",
    "glossary_subcat_propose":  "pipeline.glossary.g07_subcategory_propose.stage",
    "glossary_subcat_apply":    "pipeline.glossary.g08_subcategory_apply.stage",
    "glossary_fingerprint":     "pipeline.glossary.g09_metadata_fingerprint.stage",
    "glossary_finalise":        "pipeline.glossary.g10_finalise.stage",
    "glossary_inverses":        "pipeline.glossary.g11_inverse_signatures.stage",

    # Legacy v1 / taxonomy-first stages (kept for backward compat)
    "event_type":  "pipeline.event_type",
    "verify":      "pipeline.verify",
    "clean":       "pipeline.clean",
    "reconcile":   "pipeline.reconcile",
    "synthesise":  "pipeline.synthesise",
    "discover":    "pipeline.discover",
    "classify":    "pipeline.classify",
    "matrix":      "pipeline.matrix",
}

# Steps that work before full domain config exists
EARLY_STEPS = {"ingest", "parse"}


def main():
    parser = argparse.ArgumentParser(
        description="Run pipeline steps",
        usage="python -m pipeline.run --domain <name> --step <step> [step args...]",
    )
    parser.add_argument("--domain", required=True, help="Domain name (e.g. arena)")
    parser.add_argument("--step", required=True, choices=STEPS.keys(),
                        help="Pipeline step to run")
    parser.add_argument("--list-steps", action="store_true", help="List available steps")

    # Parse only known args — the rest are forwarded to the step module
    args, remaining = parser.parse_known_args()

    if args.list_steps:
        print("Available pipeline steps:")
        for name, module in STEPS.items():
            print(f"  {name:<15s}  ({module})")
        return

    # Validate domain exists
    # Early steps (ingest, bootstrap) don't require full config
    if args.step not in EARLY_STEPS:
        try:
            cfg = DomainConfig.load(args.domain)
            print(f"Domain: {cfg.domain.name} ({cfg.domain.full_name})")
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        domain_dir = Path(__file__).resolve().parents[1] / "domains" / args.domain
        if not domain_dir.exists():
            domain_dir.mkdir(parents=True)
            print(f"Created domain directory: {domain_dir}")
        print(f"Domain: {args.domain} (early step — partial config OK)")

    # Forward to step module's main()
    module_name = STEPS[args.step]

    # Rebuild sys.argv for the step module
    sys.argv = [module_name, "--domain", args.domain] + remaining

    # Import and run the step
    import importlib
    module = importlib.import_module(module_name)
    module.main()


if __name__ == "__main__":
    main()
