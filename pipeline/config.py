"""Domain configuration loader.

Loads all config files from a domains/<domain>/ directory and provides
typed access to enums, prompts, rules, and settings.

Usage:
    from pipeline.config import DomainConfig
    cfg = DomainConfig.load("arena")
    print(cfg.domain.name)           # "ARENA"
    print(cfg.enums.failure_mode)    # ["no major failure stated", ...]
    print(cfg.prompt("event_type"))  # rendered prompt template
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


DOMAINS_DIR = Path(__file__).resolve().parents[1] / "domains"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
STAGES_DIR = Path(__file__).resolve().parent / "stages"
GLOSSARY_DIR = Path(__file__).resolve().parent / "glossary"


@dataclass
class DomainSettings:
    """Master domain settings from domain.yaml."""
    name: str
    full_name: str
    description: str = ""
    record_id_prefix: str = ""
    ids_per_document: int = 50
    max_document_chars: int = 600000
    project_grouping_field: str = ""
    category_field: str = ""
    has_portfolio_matching: bool = False
    temporal_relevance_years: int = 5
    archetype_independence_threshold: dict = field(default_factory=lambda: {"min_events": 3, "min_projects": 3})
    archetype_refine_threshold: dict = field(default_factory=lambda: {"min_events": 2})
    extraction_model: str = "claude-sonnet-4-6"
    classification_model: str = "claude-haiku-4-5-20251001"
    discovery_model: str = "claude-sonnet-4-6"
    reconciliation_model: str = "claude-haiku-4-5-20251001"
    verification_model: str = "claude-haiku-4-5-20251001"
    synthesis_model: str = "claude-sonnet-4-6"
    # Catalogue config for metadata stamping
    catalogue: dict = field(default_factory=dict)
    # raw dict for any extra fields
    _raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> DomainSettings:
        known = {f.name for f in cls.__dataclass_fields__.values() if f.name != "_raw"}
        kwargs = {k: v for k, v in d.items() if k in known}
        kwargs["_raw"] = d
        return cls(**kwargs)


@dataclass
class Enums:
    """All enum values for the domain."""
    _data: dict = field(default_factory=dict, repr=False)

    def __getattr__(self, name: str) -> list:
        if name.startswith("_"):
            raise AttributeError(name)
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"No enum '{name}' in domain config")

    def get(self, name: str, default=None):
        return self._data.get(name, default)

    def keys(self):
        return self._data.keys()


class DomainConfig:
    """Complete domain configuration."""

    def __init__(self, domain_dir: Path):
        self.domain_dir = domain_dir

        # Load domain.yaml
        with open(domain_dir / "domain.yaml") as f:
            raw = yaml.safe_load(f)
        self.domain = DomainSettings.from_dict(raw)

        # Load enums.yaml (optional — not needed for taxonomy-agnostic extraction)
        enums_path = domain_dir / "enums.yaml"
        if enums_path.exists():
            with open(enums_path) as f:
                self.enums = Enums(_data=yaml.safe_load(f) or {})
        else:
            self.enums = Enums(_data={})

        # Load optional config files
        self.category_map = self._load_yaml("category_map.yaml")
        self.parent_categories = self._load_yaml("parent_categories.yaml")
        self.keyword_rules = self._load_yaml("keyword_rules.yaml")
        self.remap_rules = self._load_yaml("remap_rules.yaml")
        self.do_not_merge = self._load_yaml("do_not_merge.yaml")
        self.excluded_doc_types = self._load_yaml("excluded_doc_types.yaml")
        self.kb_overrides = self._load_yaml("kb_overrides.yaml")

        # Load domain context
        ctx_path = domain_dir / "prompts" / "domain_context.md"
        self.domain_context = ctx_path.read_text().strip() if ctx_path.exists() else ""

        # NEW: prompt_tokens — substituted into engine prompt templates
        # via {token_name}. Optional; defaults to {} if absent.
        self.prompt_tokens: dict = (raw.get("prompt_tokens") or {})

        # NEW: per-stage execution config (model, batch sizes, paths).
        # Optional; defaults to {} if absent. Stage modules read
        # cfg.stages[stage_name] for their config.
        self.stages: dict = (raw.get("stages") or {})

        # NEW: per-stage prompt overrides (existing 'prompts:' block extended)
        self.prompt_overrides: dict = (raw.get("prompts") or {})

        # NEW: glossary sub-pipeline config (parallel branch to stages/).
        # Optional; defaults to {} if absent. Stage modules read
        # cfg.glossary.candidate / cfg.glossary.fingerprint etc.
        self.glossary: dict = (raw.get("glossary") or {})

        # Expose raw yaml for sub-pipelines that introduce their own blocks
        # (avoids needing a config.py edit per new sub-pipeline).
        self.raw: dict = raw

    def _load_yaml(self, filename: str) -> Optional[dict]:
        path = self.domain_dir / filename
        if not path.exists():
            return None
        with open(path) as f:
            return yaml.safe_load(f)

    def prompt(self, name: str, stage: Optional[str] = None, **kwargs) -> str:
        """Load and render a prompt template.

        Resolution priority:
          1. Explicit override in domain.yaml prompts: block (per-corpus override)
          2. domains/<corpus>/prompts/<name>.md (per-corpus prompt file)
          3. pipeline/stages/<stage>/<name>.md (canonical engine template, if stage given)
          4. pipeline/prompts/<name>.md (legacy engine prompt location)

        Substitutes:
          - Default tokens: domain_name, domain_full_name, domain_context, record_id_prefix
          - prompt_tokens block from domain.yaml (if present)
          - **kwargs passed by caller (highest priority)
        """
        path = self._resolve_prompt_path(name, stage)
        if path is None:
            raise FileNotFoundError(
                f"No prompt template found for name={name!r} stage={stage!r}. "
                f"Searched: domain overrides, domains/{self.domain.name.lower()}/prompts/, "
                f"pipeline/stages/{stage}/, pipeline/prompts/"
            )

        template = path.read_text()

        # Default template variables from domain config
        defaults = {
            "domain_name": self.domain.name,
            "domain_full_name": self.domain.full_name,
            "domain_context": self.domain_context,
            "record_id_prefix": self.domain.record_id_prefix,
            "min_events": self.domain.archetype_independence_threshold.get("min_events", 3),
            "min_events_refine": self.domain.archetype_refine_threshold.get("min_events", 2),
        }
        # Auto-inject prompt_tokens from domain.yaml
        defaults.update(self.prompt_tokens or {})
        # Sub-pipelines can carry their own prompt_tokens block (e.g.
        # glossary.prompt_tokens). Merge those in with higher precedence
        # than top-level prompt_tokens, so a glossary stage gets glossary-
        # specific tokens even when a sibling cluster-stage token has the
        # same name.
        for sub in ("glossary",):
            block = self.raw.get(sub) or {}
            sub_tokens = block.get("prompt_tokens") if isinstance(block, dict) else None
            if sub_tokens:
                defaults.update(sub_tokens)
        # Caller kwargs take precedence
        defaults.update(kwargs)

        return template.format(**defaults)

    def _resolve_prompt_path(self, name: str, stage: Optional[str] = None) -> Optional[Path]:
        """Resolve prompt template path using priority order."""
        # 1. Explicit override
        if name in self.prompt_overrides:
            override = self.prompt_overrides[name]
            p = Path(override)
            if not p.is_absolute():
                # treat as relative to repo root
                p = Path(__file__).resolve().parents[1] / override
            if p.exists():
                return p

        # 2. domains/<corpus>/prompts/<name>.md
        per_corpus = self.domain_dir / "prompts" / f"{name}.md"
        if per_corpus.exists():
            return per_corpus

        # 3. pipeline/stages/<stage>/<name>.md or pipeline/glossary/<stage>/<name>.md
        if stage:
            for base in (STAGES_DIR, GLOSSARY_DIR):
                stage_dir = base / stage
                if stage_dir.exists():
                    # Try <name>.md first, then prompt.md as default
                    candidates = [stage_dir / f"{name}.md", stage_dir / "prompt.md"]
                    for c in candidates:
                        if c.exists():
                            return c

        # 4. pipeline/prompts/<name>.md (legacy)
        legacy = PROMPTS_DIR / f"{name}.md"
        if legacy.exists():
            return legacy

        return None

    def stage(self, stage_name: str) -> dict:
        """Get config dict for a specific pipeline stage.

        Returns empty dict if stage block is absent. Stage modules can
        also fall back to top-level domain settings (e.g. cfg.domain.extraction_model).
        """
        return self.stages.get(stage_name, {}) if self.stages else {}

    @classmethod
    def load(cls, domain_name: str) -> DomainConfig:
        """Load config for a named domain."""
        domain_dir = DOMAINS_DIR / domain_name
        if not domain_dir.exists():
            raise FileNotFoundError(f"Domain directory not found: {domain_dir}")
        return cls(domain_dir)
