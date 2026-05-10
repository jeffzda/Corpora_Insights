"""Taxonomy-method engine.

Generic implementation of the 6-step recipe in domains/TAXONOMY_METHOD.md.
Per-corpus wrappers live in `corpora/<name>/tests/taxonomy_method/iter_N/`
and pass in catalogue-specific stratum functions and domain-noun
substitutions for prompts.
"""
from .sample import pick_stratified_sample
from .extract_submit import submit_extract_batch, build_extract_requests
from .extract_collect import collect_extract_batch
from .propose_axes import propose_axes
from .tag_sync import tag_findings_sync, write_fill_rate_report
from .tag_batch import submit_tag_batch, collect_tag_batch

__all__ = [
    "pick_stratified_sample",
    "submit_extract_batch",
    "build_extract_requests",
    "collect_extract_batch",
    "propose_axes",
    "tag_findings_sync",
    "write_fill_rate_report",
    "submit_tag_batch",
    "collect_tag_batch",
]
