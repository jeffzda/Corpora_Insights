#!/usr/bin/env python3
"""Bootstrap a new domain configuration from sample documents.

Given a directory of markdown documents and a one-line domain description,
generates draft domain config files (domain.yaml, enums.yaml, taxonomy.md)
using an LLM to analyse the document structure and content.

Usage:
    python -m pipeline.bootstrap \\
        --docs /path/to/markdown/*.md \\
        --description "ANAO performance audit reports for Australian government programs" \\
        --output domains/anao/ \\
        --samples 15

    python -m pipeline.bootstrap \\
        --docs /path/to/markdown/*.md \\
        --description "..." \\
        --output domains/anao/ \\
        --dry-run  # print prompt only
"""

import argparse
import glob
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load_sample_docs(docs_pattern: str, n_samples: int, max_chars: int = 30000) -> list[dict]:
    """Load sample documents, truncated to max_chars each."""
    paths = sorted(glob.glob(docs_pattern))
    if not paths:
        print(f"No files matching: {docs_pattern}")
        sys.exit(1)

    # Sample deterministically
    random.seed(42)
    selected = random.sample(paths, min(n_samples, len(paths)))

    samples = []
    for p in selected:
        text = Path(p).read_text(errors="replace")
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[... truncated ...]"
        samples.append({
            "filename": Path(p).name,
            "content": text,
            "chars": len(text),
        })

    return samples


def build_prompt(description: str, samples: list[dict]) -> str:
    """Build the bootstrap prompt from template + samples."""
    template = (PROMPTS_DIR / "bootstrap.md").read_text()

    sample_text = ""
    for i, s in enumerate(samples, 1):
        sample_text += f"\n### Document {i}: {s['filename']} ({s['chars']:,} chars)\n\n"
        sample_text += s["content"]
        sample_text += "\n\n---\n"

    return template.format(
        domain_description=description,
        n_samples=len(samples),
        sample_documents=sample_text,
    )


def run_bootstrap(prompt: str, model: str = "claude-sonnet-4-20250514") -> str:
    """Send bootstrap prompt to LLM and return response."""
    try:
        import anthropic
    except ImportError:
        raise SystemExit("anthropic not installed. Run: pip install anthropic")

    client = anthropic.Anthropic()
    result = ""
    with client.messages.stream(
        model=model,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            result += text

    print()
    return result


def save_draft_config(response: str, output_dir: Path):
    """Parse LLM response and save draft config files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "prompts").mkdir(exist_ok=True)

    # Save raw response for reference
    (output_dir / "_bootstrap_response.md").write_text(response)

    # Try to extract YAML block
    yaml_start = response.find("```yaml")
    yaml_end = response.find("```", yaml_start + 7) if yaml_start >= 0 else -1

    if yaml_start >= 0 and yaml_end >= 0:
        yaml_content = response[yaml_start + 7:yaml_end].strip()
        (output_dir / "_bootstrap_schema.yaml").write_text(yaml_content)
        print(f"\nDraft schema saved to {output_dir / '_bootstrap_schema.yaml'}")
        print("Review and split into domain.yaml, enums.yaml, taxonomy.md")
    else:
        print("\nNo YAML block found in response. Check _bootstrap_response.md")

    print(f"\nNext steps:")
    print(f"  1. Review {output_dir / '_bootstrap_schema.yaml'}")
    print(f"  2. Create domain.yaml with settings")
    print(f"  3. Create enums.yaml with field values")
    print(f"  4. Create taxonomy.md with extraction prompt schema")
    print(f"  5. Write {output_dir / 'prompts' / 'domain_context.md'}")


def main():
    parser = argparse.ArgumentParser(description="Bootstrap domain config from sample documents")
    parser.add_argument("--docs", required=True, help="Glob pattern for markdown docs")
    parser.add_argument("--description", required=True, help="One-line domain description")
    parser.add_argument("--output", required=True, help="Output domain directory")
    parser.add_argument("--samples", type=int, default=15, help="Number of sample docs")
    parser.add_argument("--max-chars", type=int, default=30000, help="Max chars per sample")
    parser.add_argument("--model", default="claude-sonnet-4-20250514", help="Model to use")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt only")
    args = parser.parse_args()

    samples = load_sample_docs(args.docs, args.samples, args.max_chars)
    print(f"Loaded {len(samples)} sample documents")
    for s in samples:
        print(f"  {s['filename']} ({s['chars']:,} chars)")

    prompt = build_prompt(args.description, samples)
    print(f"\nPrompt: {len(prompt):,} chars")

    if args.dry_run:
        print("\n--- DRY RUN: Prompt ---")
        print(prompt[:3000])
        print(f"\n... [{len(prompt):,} chars total] ...")
        return

    response = run_bootstrap(prompt, model=args.model)
    save_draft_config(response, Path(args.output))


if __name__ == "__main__":
    main()
