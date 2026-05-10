"""Canonical pipeline stages.

Each stage lives under pipeline/stages/sNN_<stage_name>/ with stage.py
plus prompt template(s). Shared helpers (streaming, parsing) live in
pipeline/stages/shared/.

Dispatch via pipeline/run.py STEPS table.
"""
