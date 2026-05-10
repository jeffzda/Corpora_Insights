#!/usr/bin/env python3
"""Bundled axis-tagging pass over extracted records.

Reads YAML record files (output of pipeline.extract or pipeline.extract_v2),
sends batches of records to Sonnet with the prompt at
`pipeline/prompts/label_axes.md`, and writes parallel `.labels.yaml` files
containing per-record axis tags. The original record files are NOT modified.

This replaces the v1 separate stages of causal-recovery (Stage 2),
valence/mechanism tagging (Stage A), and realisation classification (Stage 6)
with one bundled call per batch. Adds three new axes (stakeholder,
interface_locus, outcome_class) implicit in the cluster taxonomy but not
previously surfaced as per-record fields. See methodology_gaps.md §14.

The architectural rationale (after the §14 revision): extraction stays pure /
taxonomy-free. All categorical labelling is here. Recalibrating any single
axis is a re-run of this pass without touching extraction.

Usage:
    # Label a single doc
    python -m pipeline.label_axes --domain arena --in runs/arena/per_doc_v2/doc_0029.yaml

    # Label a directory of doc YAMLs (writes <stem>.labels.yaml alongside)
    python -m pipeline.label_axes --domain arena --in-dir runs/arena/per_doc_v2

    # Pilot batch run
    python -m pipeline.label_axes --domain arena --in-dir runs/arena/per_doc_v2 \\
        --batch-size 20

    # Anthropic Batches API submission for full corpus
    python -m pipeline.label_axes --domain arena --in-dir runs/arena/per_doc_v2 --batch
"""

import argparse
import json
import re
import time
from pathlib import Path

try:
    import anthropic
except ImportError:
    raise SystemExit("anthropic not installed")

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed")

from pipeline.config import DomainConfig
from pipeline.extract import ROOT, MAX_RETRIES, RETRY_BASE_DELAY

# Default to Sonnet for nuance on stakeholder/interface_locus/outcome_class.
# Override via --model haiku for cheaper runs.
DEFAULT_MODEL_KEY = "extraction_model"  # use the domain's extraction-tier model
DEFAULT_BATCH_SIZE = 20  # records per LLM call

PRICE_INPUT_SONNET = 3.0
PRICE_OUTPUT_SONNET = 15.0
PRICE_INPUT_HAIKU = 0.80
PRICE_OUTPUT_HAIKU = 4.0


def load_prompt_template(cfg):
    """Load label_axes prompt with domain context substituted."""
    path = ROOT / "pipeline" / "prompts" / "label_axes.md"
    template = path.read_text()
    template = template.replace("{domain_context}", cfg.domain_context)
    return template


def record_for_labelling(rec):
    """Trim a full record down to the fields the labelling LLM needs.

    The labelling pass only needs the text the model will reason over —
    record_id, what_happened, lesson_learnt, intervention_note,
    evidence_excerpt. Stripping the rest keeps prompts compact.
    """
    keep = ["record_id", "what_happened", "lesson_learnt",
            "intervention_note", "evidence_excerpt"]
    return {k: rec.get(k) for k in keep if rec.get(k) is not None}


def build_batch_prompt(template, batch_records):
    """Render one batch's prompt by appending the trimmed records as YAML."""
    trimmed = [record_for_labelling(r) for r in batch_records]
    records_yaml = yaml.dump(trimmed, allow_unicode=True, sort_keys=False,
                              default_flow_style=False)
    prompt = template.replace(
        "[Records appended by the orchestrating script]",
        f"```yaml\n{records_yaml}```"
    )
    return prompt


def call_api(client, prompt, model, max_tokens, label):
    """Call Claude API with retry."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            message = client.messages.create(
                model=model, max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            usage = message.usage
            return (message.content[0].text,
                    usage.input_tokens, usage.output_tokens)
        except anthropic.RateLimitError as e:
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            print(f"  Rate limit ({label}, attempt {attempt}/{MAX_RETRIES}), waiting {delay}s",
                  flush=True)
            time.sleep(delay)
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                delay = RETRY_BASE_DELAY * attempt
                print(f"  Server error {e.status_code} ({label}, attempt {attempt}/{MAX_RETRIES})",
                      flush=True)
                time.sleep(delay)
            else:
                raise
    raise RuntimeError(f"{label}: API failed after {MAX_RETRIES} attempts")


def parse_labels_response(response, label):
    """Parse the YAML labels list from the model response."""
    m = re.search(r"```(?:yaml)?\s*(.*?)```", response, re.DOTALL)
    if not m:
        print(f"  WARNING ({label}): no YAML block in response", flush=True)
        return []
    try:
        parsed = yaml.safe_load(m.group(1).strip())
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "records" in parsed:
            return parsed["records"]
    except yaml.YAMLError as e:
        print(f"  WARNING ({label}): YAML parse failed: {e}", flush=True)
    return []


def merge_labels_into_records(records, labels):
    """Attach axis-tag fields to each record by record_id match.

    Returns (annotated_records, n_unmatched).
    """
    by_id = {l.get("record_id"): l for l in labels if l.get("record_id")}
    n_unmatched = 0
    annotated = []
    axis_fields = ["causal_claim_made", "causal_connective", "valence",
                   "mechanism_named", "mechanism_phrase", "realisation",
                   "stakeholder", "interface_locus", "outcome_class"]
    for rec in records:
        rid = rec.get("record_id")
        out = dict(rec)
        if rid in by_id:
            for f in axis_fields:
                if f in by_id[rid]:
                    out[f] = by_id[rid][f]
        else:
            n_unmatched += 1
        annotated.append(out)
    return annotated, n_unmatched


def write_labels_file(labels, out_path):
    """Write the labels-only YAML alongside the records file."""
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(labels, f, allow_unicode=True, sort_keys=False,
                  default_flow_style=False)


def label_one_file(in_path, out_path, prompt_template, client, model,
                    max_tokens, batch_size, dry_run):
    """Label all records in one YAML file, batching them."""
    with open(in_path) as f:
        records = yaml.safe_load(f) or []
    if not records:
        print(f"  {in_path.name}: empty, skipping", flush=True)
        return 0, 0

    all_labels = []
    total_in = total_out = 0
    n_batches = (len(records) + batch_size - 1) // batch_size

    for bi in range(n_batches):
        batch = records[bi * batch_size:(bi + 1) * batch_size]
        prompt = build_batch_prompt(prompt_template, batch)
        label = f"{in_path.stem} batch {bi+1}/{n_batches}"

        if dry_run:
            print(f"\n--- DRY RUN {label} (first 2500 chars) ---")
            print(prompt[:2500])
            print("\n[... remainder elided ...]\n")
            continue

        response, in_tok, out_tok = call_api(client, prompt, model,
                                              max_tokens, label)
        total_in += in_tok
        total_out += out_tok
        labels = parse_labels_response(response, label)
        all_labels.extend(labels)
        print(f"    {label}: {len(batch)} records → {len(labels)} labels  "
              f"({in_tok:,} in / {out_tok:,} out)", flush=True)

    if dry_run:
        return 0, 0

    if all_labels:
        write_labels_file(all_labels, out_path)
        n_records = len(records)
        n_labelled = len(all_labels)
        print(f"  {in_path.name}: labelled {n_labelled}/{n_records} records → {out_path.name}",
              flush=True)

    return total_in, total_out


def main():
    parser = argparse.ArgumentParser(
        description="Bundled axis-tagging pass over extracted records")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--in", dest="in_path", default=None,
                         help="Single record YAML file to label")
    parser.add_argument("--in-dir", default=None,
                         help="Directory of doc_*.yaml files to label")
    parser.add_argument("--out-suffix", default=".labels.yaml",
                         help="Suffix for output files (default .labels.yaml)")
    parser.add_argument("--model", default=None,
                         help="Override the labelling model (e.g. claude-sonnet-4-6)")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true",
                         help="Skip files whose .labels.yaml already exists")
    parser.add_argument("--batch", action="store_true",
                         help="Submit all calls as Anthropic Batches API job")
    args = parser.parse_args()

    cfg = DomainConfig.load(args.domain)
    model = args.model or cfg.domain.extraction_model

    # Collect input files
    if args.in_path:
        files = [Path(args.in_path)]
    elif args.in_dir:
        d = Path(args.in_dir)
        if not d.is_absolute():
            d = ROOT / d
        files = sorted(d.glob("doc_*.yaml"))
    else:
        raise SystemExit("Need --in or --in-dir")

    if args.resume:
        files = [f for f in files if not (f.parent / (f.stem + args.out_suffix)).exists()]
        print(f"Resume: {len(files)} files remaining")

    if not files:
        print("Nothing to label.")
        return

    prompt_template = load_prompt_template(cfg)
    client = anthropic.Anthropic()
    max_tokens = 16_000  # enough for ~30 records of axis labels

    if args.batch:
        # Build all batch requests across all files
        print(f"\nPreparing batch requests for {len(files)} files...")
        all_requests = []
        custom_id_to_meta = {}
        for fpath in files:
            with open(fpath) as f:
                records = yaml.safe_load(f) or []
            n = len(records)
            for bi in range((n + args.batch_size - 1) // args.batch_size):
                batch = records[bi * args.batch_size:(bi + 1) * args.batch_size]
                prompt = build_batch_prompt(prompt_template, batch)
                cid = f"{fpath.stem}_b{bi:03d}"
                all_requests.append({
                    "custom_id": cid,
                    "params": {
                        "model": model,
                        "max_tokens": max_tokens,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                })
                custom_id_to_meta[cid] = {"file": str(fpath), "batch_idx": bi}

        if not all_requests:
            print("No batches to submit.")
            return

        batch = client.messages.batches.create(requests=all_requests)
        print(f"Batch submitted: {batch.id}  ({len(all_requests)} requests)")
        # Persist meta for retrieval
        meta_path = ROOT / "runs" / args.domain / f"label_axes_batch_{batch.id}.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps({
            "batch_id": batch.id,
            "model": model,
            "out_suffix": args.out_suffix,
            "batch_size": args.batch_size,
            "custom_id_to_meta": custom_id_to_meta,
        }, indent=2))
        print(f"Metadata saved to {meta_path}")
        print(f"Retrieve with: --retrieve {batch.id}  (not yet implemented for label_axes)")
        return

    # Sync mode
    total_in = total_out = 0
    for fpath in files:
        out_path = fpath.parent / (fpath.stem + args.out_suffix)
        if args.resume and out_path.exists():
            continue
        print(f"\n[{fpath.name}]")
        in_tok, out_tok = label_one_file(fpath, out_path, prompt_template,
                                           client, model, max_tokens,
                                           args.batch_size, args.dry_run)
        total_in += in_tok
        total_out += out_tok
        if args.dry_run:
            return

    # Cost estimate
    is_haiku = "haiku" in model.lower()
    p_in = PRICE_INPUT_HAIKU if is_haiku else PRICE_INPUT_SONNET
    p_out = PRICE_OUTPUT_HAIKU if is_haiku else PRICE_OUTPUT_SONNET
    cost = (total_in / 1_000_000 * p_in) + (total_out / 1_000_000 * p_out)
    print(f"\nDone. Tokens: {total_in:,} input / {total_out:,} output")
    print(f"Estimated cost ({model}): ${cost:.2f}")


if __name__ == "__main__":
    main()
