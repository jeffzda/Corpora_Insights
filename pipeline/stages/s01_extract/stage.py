"""Stage 01 — Extraction.

Thin shim around the existing canonical pipeline/extract.py module.
That module is already config-driven (DomainConfig) and consumes
domains/<corpus>/prompts/extract.md.
"""
from pipeline.extract import main


if __name__ == '__main__':
    main()
