"""Stage 02 — Per-doc event derivation (group_events).

Thin shim around the existing canonical pipeline/group_events.py module.
Prompt: pipeline/prompts/group_events.md (already engine-canonical, fully
domain-agnostic).
"""
from pipeline.group_events import main


if __name__ == '__main__':
    main()
