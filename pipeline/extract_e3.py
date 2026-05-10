#!/usr/bin/env python3
"""E3 extraction driver — canonical taxonomy-free extraction at temp=0.

Reads a domain's manifest CSV, derives marker-rendered markdown paths,
applies the domain's E3 prompt at `domains/<domain>/prompts/extract.md`,
calls Sonnet 4.6 at temperature=0 with streaming, parses the JSON output,
stamps catalogue metadata, and writes one JSON per document.

Resumable. Concurrent. Independent of the legacy `pipeline/extract.py`.

Usage:
    python -m pipeline.extract_e3 --domain arena --smoke 5
    python -m pipeline.extract_e3 --domain arena
    python -m pipeline.extract_e3 --domain arena --resume
    python -m pipeline.extract_e3 --domain arena --concurrency 6
"""
import argparse
import csv
import json
import re
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 64000
DEFAULT_CONCURRENCY = 4

# Sonnet 4.6 sync pricing
PRICE_INPUT_PER_M = 3.0
PRICE_OUTPUT_PER_M = 15.0
# Batches API discount (50% off both input and output)
BATCH_PRICE_INPUT_PER_M = 1.5
BATCH_PRICE_OUTPUT_PER_M = 7.5


# ---------- stem normalisation ----------

def normalise_stem(name: str) -> str:
    """Lowercase, replace -/space with _, collapse multiple _, strip edges.
    Hash suffix is preserved — different docs with similar titles disambiguate
    by their content hash (e.g. _6fb7c0 vs _04d35d)."""
    n = name.lower().replace("-", "_").replace(" ", "_")
    n = re.sub(r"_+", "_", n).strip("_")
    return n


def build_marker_index(marker_root: Path) -> dict[str, Path]:
    """Index marker_output/<stem>/<stem>.rendered.md by hash-preserving
    normalised stem. Two docs with similar titles but different content
    hashes get distinct keys."""
    idx = {}
    for d in marker_root.iterdir():
        if not d.is_dir():
            continue
        norm = normalise_stem(d.name)
        rendered = d / f"{d.name}.rendered.md"
        if rendered.exists():
            idx[norm] = rendered
    return idx


# ---------- catalogue + metadata stamping ----------

def load_domain_yaml(domain: str) -> dict:
    path = ROOT / "domains" / domain / "domain.yaml"
    if not path.exists():
        raise SystemExit(f"domain.yaml not found: {path}")
    return yaml.safe_load(path.read_text())


def load_manifest(domain: str, dyaml: dict, status_filter: str = "downloaded"):
    cat_cfg = dyaml.get("catalogue", {})
    cat_file = cat_cfg.get("file", "manifest.csv")
    cat_path = ROOT / "corpora" / domain / cat_file
    if not cat_path.exists():
        raise SystemExit(f"manifest not found: {cat_path}")
    rows = list(csv.DictReader(cat_path.open()))
    if status_filter:
        rows = [r for r in rows if (r.get("status") or "").strip().lower() == status_filter]
    return rows, cat_cfg


def derive_md_path(row: dict, marker_idx: dict[str, Path], cat_cfg: dict) -> Path | None:
    """Map a manifest row to its marker rendered.md via hash-preserving stem
    normalisation on local_path."""
    join_key = cat_cfg.get("join_key", "local_path")
    local = (row.get(join_key) or "").strip()
    if not local:
        return None
    # local_path is e.g. "pdfs/Reports/Title_HASH.pdf"
    norm = normalise_stem(Path(local).stem)
    return marker_idx.get(norm)


def build_metadata_for_record(row: dict, cat_cfg: dict, dyaml: dict) -> dict:
    """Map catalogue columns onto record metadata fields per domain.yaml field_map."""
    meta = {}
    field_map = (cat_cfg or {}).get("field_map", {})
    for src_col, dst_field in field_map.items():
        v = row.get(src_col)
        if v is not None and str(v).strip():
            meta[dst_field] = str(v).strip()
    # Title (always include explicitly)
    title_field = (cat_cfg or {}).get("title_field", "Title")
    if row.get(title_field):
        meta["source_title"] = row[title_field].strip()
    # Markdown filename hint for traceability
    return meta


# ---------- prompt rendering ----------

def load_prompt_template(domain: str) -> str:
    """Prefer domains/<name>/prompts/extract.md; fall back to pipeline/prompts/extract.md."""
    domain_path = ROOT / "domains" / domain / "prompts" / "extract.md"
    if domain_path.exists():
        return domain_path.read_text()
    fallback = ROOT / "pipeline" / "prompts" / "extract.md"
    if fallback.exists():
        return fallback.read_text()
    raise SystemExit(f"No extract prompt found at {domain_path} or {fallback}")


def render_prompt(template: str, prefix: str, title: str, text: str) -> str:
    return (template
            .replace("{{prefix}}", prefix)
            .replace("{{title}}", title)
            .replace("{{text}}", text))


# ---------- output parsing ----------

def strip_fence(t: str) -> str:
    s = t.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n", "", s)
        if s.endswith("```"):
            s = s[:-3]
    return s.strip()


def parse_json_output(raw: str) -> tuple[list[dict], str]:
    """Returns (records, parse_method). Method ∈ {strict, lenient, failed}."""
    text = strip_fence(raw)
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and isinstance(obj.get("records"), list):
            return obj["records"], "strict"
        if isinstance(obj, list):
            return obj, "strict"
    except json.JSONDecodeError:
        pass
    # Lenient: find first {...} block
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict) and isinstance(obj.get("records"), list):
                return obj["records"], "lenient"
        except json.JSONDecodeError:
            pass
    return [], "failed"


# ---------- API call ----------

def call_sonnet_e3(client: anthropic.Anthropic, prompt: str, model: str,
                   max_tokens: int, temperature: float) -> tuple[str, int, int]:
    """Single streaming Sonnet call. Returns (text, in_tokens, out_tokens)."""
    parts = []
    with client.messages.stream(
        model=model, max_tokens=max_tokens, temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for chunk in stream.text_stream:
            parts.append(chunk)
        final = stream.get_final_message()
    return "".join(parts), final.usage.input_tokens, final.usage.output_tokens


# ---------- Batches API ----------

def build_batch_requests(matched, prompt_template, cat_cfg, dyaml,
                         model, max_tokens, temperature):
    """Build the list of batch request objects to submit.
    Each item maps to one document; custom_id encodes doc_seq."""
    from anthropic.types.messages.batch_create_params import Request

    requests = []
    for i, row, md_path in matched:
        doc_seq = i + 1
        title = row.get(cat_cfg.get("title_field", "Title"), "").strip()
        text = md_path.read_text()
        prefix = f"{dyaml.get('record_id_prefix','REC')}-{doc_seq:04d}"
        prompt = render_prompt(prompt_template, prefix, title, text)
        requests.append(Request(
            custom_id=f"doc_{doc_seq:04d}",
            params={
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            },
        ))
    return requests


def submit_batch(client, requests, batch_id_path: Path):
    """Submit a batch and persist the batch_id."""
    print(f"submitting batch with {len(requests)} requests...", flush=True)
    batch = client.messages.batches.create(requests=requests)
    print(f"batch_id: {batch.id}", flush=True)
    batch_id_path.write_text(batch.id)
    return batch.id


def wait_for_batch(client, batch_id: str, poll_interval: int = 30):
    """Poll until the batch completes."""
    print(f"polling batch {batch_id}...", flush=True)
    while True:
        b = client.messages.batches.retrieve(batch_id)
        counts = b.request_counts
        total = (counts.processing + counts.succeeded + counts.errored
                 + counts.canceled + counts.expired)
        done = counts.succeeded + counts.errored + counts.canceled + counts.expired
        print(f"  status={b.processing_status} {done}/{total} "
              f"(succeeded={counts.succeeded} errored={counts.errored} "
              f"processing={counts.processing})", flush=True)
        if b.processing_status == "ended":
            return b
        time.sleep(poll_interval)


def process_batch_results(client, batch_id: str, matched_by_doc_id: dict,
                          cat_cfg, dyaml, out_dir: Path):
    """Stream batch results, parse JSON, stamp metadata, write per-doc files."""
    n_ok = n_fail = 0
    total_in = total_out = total_recs = 0
    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id
        match = matched_by_doc_id.get(custom_id)
        if match is None:
            print(f"  WARN: result for unknown custom_id {custom_id}", flush=True)
            continue
        i, row, md_path = match
        doc_seq = i + 1

        if result.result.type == "errored":
            err = result.result.error
            print(f"  [{custom_id}] ERROR: {err}", flush=True)
            n_fail += 1
            continue
        if result.result.type != "succeeded":
            print(f"  [{custom_id}] non-success type: {result.result.type}", flush=True)
            n_fail += 1
            continue

        msg = result.result.message
        raw = "".join(b.text for b in msg.content if b.type == "text")
        usage = msg.usage
        in_t = usage.input_tokens
        out_t = usage.output_tokens
        finish_reason = getattr(msg, "stop_reason", None)
        total_in += in_t; total_out += out_t

        # Truncation detection — out_t hitting the max_tokens cap or
        # explicit length stop_reason both indicate the response was cut off.
        truncated = (finish_reason == "max_tokens"
                     or finish_reason == "length"
                     or (out_t >= 63000))  # within 1000 of 64k cap

        records, parse_method = parse_json_output(raw)
        if parse_method == "failed":
            (out_dir / f"{custom_id}.raw.txt").write_text(raw)
            (out_dir / f"{custom_id}.meta.json").write_text(json.dumps({
                "stop_reason": finish_reason, "input_tokens": in_t,
                "output_tokens": out_t, "truncated": truncated,
            }))
            print(f"  [{custom_id}] PARSE FAILED  stop_reason={finish_reason} "
                  f"out={out_t}{'  TRUNCATED' if truncated else ''}", flush=True)
            n_fail += 1
            continue

        prefix = f"{dyaml.get('record_id_prefix','REC')}-{doc_seq:04d}"
        meta = build_metadata_for_record(row, cat_cfg, dyaml)
        for j, r in enumerate(records):
            if "id" not in r or not r["id"]:
                r["id"] = f"{prefix}-{j+1:04d}"
            for k, v in meta.items():
                r.setdefault(k, v)
            r["doc_id"] = custom_id
            r["markdown_path"] = str(md_path.relative_to(ROOT))

        out_path = out_dir / f"{custom_id}.json"
        out_path.write_text(json.dumps({
            "records": records,
            "_meta": {
                "stop_reason": finish_reason,
                "input_tokens": in_t,
                "output_tokens": out_t,
                "truncated": truncated,
            },
        }, indent=2, ensure_ascii=False))
        n_ok += 1
        total_recs += len(records)
        cost = in_t * BATCH_PRICE_INPUT_PER_M / 1e6 + out_t * BATCH_PRICE_OUTPUT_PER_M / 1e6
        trunc_flag = "  TRUNCATED" if truncated else ""
        print(f"  [{custom_id}] ok  {len(records):3d} recs  in={in_t} out={out_t}  ${cost:.3f}{trunc_flag}",
              flush=True)

    cost_total = (total_in * BATCH_PRICE_INPUT_PER_M / 1e6
                  + total_out * BATCH_PRICE_OUTPUT_PER_M / 1e6)
    print(f"\n=== batch summary ===", flush=True)
    print(f"docs: {n_ok} ok, {n_fail} fail", flush=True)
    print(f"records: {total_recs}", flush=True)
    print(f"tokens: in={total_in:,} out={total_out:,}  cost ${cost_total:.2f} (batch pricing)",
          flush=True)


# ---------- per-doc orchestration ----------

def process_doc(client, prompt_template, row, md_path, cat_cfg, dyaml,
                doc_seq, out_dir, model, max_tokens, temperature, force=False):
    """Extract one document. Returns (status, record_count, in_tokens, out_tokens)."""
    doc_id = f"doc_{doc_seq:04d}"
    out_path = out_dir / f"{doc_id}.json"
    if out_path.exists() and not force:
        try:
            data = json.loads(out_path.read_text())
            return "skip", len(data.get("records", [])), 0, 0
        except Exception:
            pass

    title = row.get(cat_cfg.get("title_field", "Title"), "").strip()
    text = md_path.read_text()
    prefix = f"{dyaml.get('record_id_prefix','REC')}-{doc_seq:04d}"
    prompt = render_prompt(prompt_template, prefix, title, text)

    raw, in_t, out_t = call_sonnet_e3(client, prompt, model, max_tokens, temperature)
    records, parse_method = parse_json_output(raw)

    if parse_method == "failed":
        # Save raw + fail status
        (out_dir / f"{doc_id}.raw.txt").write_text(raw)
        return "parse_failed", 0, in_t, out_t

    # Stamp catalogue metadata onto every record
    meta = build_metadata_for_record(row, cat_cfg, dyaml)
    for i, r in enumerate(records):
        if "id" not in r or not r["id"]:
            r["id"] = f"{prefix}-{i+1:04d}"
        for k, v in meta.items():
            r.setdefault(k, v)
        r["doc_id"] = doc_id
        r["markdown_path"] = str(md_path.relative_to(ROOT))

    out_path.write_text(json.dumps({"records": records}, indent=2, ensure_ascii=False))
    return "ok", len(records), in_t, out_t


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="arena")
    ap.add_argument("--smoke", type=int, default=0,
                    help="Run on the first N docs only (for smoke testing)")
    ap.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--output-dir", default=None,
                    help="Default: corpora/<domain>/output/per_doc")
    ap.add_argument("--prompt-path", default=None,
                    help="Override the extraction prompt path "
                         "(default: domains/<domain>/prompts/extract.md)")
    ap.add_argument("--force", action="store_true",
                    help="Re-extract even if output already exists")
    ap.add_argument("--limit", type=int, default=0,
                    help="Cap to first N docs after sorting (useful with --resume + crash recovery)")
    ap.add_argument("--batch", action="store_true",
                    help="Use Anthropic Batches API (50%% cost reduction, async, ~minutes-to-hours)")
    ap.add_argument("--retrieve", default=None,
                    help="Skip submission and process results from an existing batch_id")
    ap.add_argument("--poll-interval", type=int, default=30,
                    help="Seconds between batch status polls")
    args = ap.parse_args()

    # Setup
    dyaml = load_domain_yaml(args.domain)
    rows, cat_cfg = load_manifest(args.domain, dyaml)
    print(f"manifest: {len(rows)} rows with status=downloaded")

    marker_root = ROOT / "corpora" / args.domain / "marker_output"
    if not marker_root.exists():
        raise SystemExit(f"marker_output not found: {marker_root}")
    marker_idx = build_marker_index(marker_root)
    print(f"marker_output: {len(marker_idx)} rendered.md files indexed")

    # Sort rows by local_path for stable doc_seq numbering
    rows.sort(key=lambda r: (r.get("local_path") or "").strip())

    # Match rows to rendered.md
    matched, unmatched = [], []
    for i, r in enumerate(rows):
        md_path = derive_md_path(r, marker_idx, cat_cfg)
        if md_path:
            matched.append((i, r, md_path))
        else:
            unmatched.append(r)
    print(f"matched: {len(matched)}/{len(rows)}; unmatched: {len(unmatched)}")
    if unmatched and len(unmatched) < 20:
        for r in unmatched[:5]:
            print(f"  unmatched: {r.get('local_path','?')[:80]}")

    if args.smoke:
        matched = matched[: args.smoke]
        print(f"smoke mode: limiting to {len(matched)} docs")
    elif args.limit:
        matched = matched[: args.limit]
        print(f"limit mode: first {len(matched)} docs")

    out_dir = Path(args.output_dir) if args.output_dir else (
        ROOT / "corpora" / args.domain / "output" / "per_doc"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"output: {out_dir}")

    if args.prompt_path:
        prompt_template = Path(args.prompt_path).read_text()
        print(f"prompt: {args.prompt_path} (override)")
    else:
        prompt_template = load_prompt_template(args.domain)
    client = anthropic.Anthropic()

    # Filter out already-extracted docs unless --force
    if not args.force:
        before = len(matched)
        matched = [
            (i, r, md) for (i, r, md) in matched
            if not (out_dir / f"doc_{i+1:04d}.json").exists()
        ]
        if before != len(matched):
            print(f"resume: skipping {before - len(matched)} already-extracted docs; "
                  f"{len(matched)} remaining", flush=True)

    # ---- Batches API path ----
    if args.batch or args.retrieve:
        batch_id_path = out_dir.parent / "batch_id.txt"
        matched_by_doc_id = {f"doc_{i+1:04d}": (i, r, md) for (i, r, md) in matched}

        if args.retrieve:
            batch_id = args.retrieve
            # Poll until ended in case the batch is still in flight.
            b = client.messages.batches.retrieve(batch_id)
            if b.processing_status != "ended":
                wait_for_batch(client, batch_id, poll_interval=args.poll_interval)
        else:
            if not matched:
                print("nothing to extract (all done?). exiting.", flush=True)
                return
            requests = build_batch_requests(
                matched, prompt_template, cat_cfg, dyaml,
                args.model, args.max_tokens, args.temperature,
            )
            batch_id = submit_batch(client, requests, batch_id_path)
            wait_for_batch(client, batch_id, poll_interval=args.poll_interval)

        # Process results
        process_batch_results(client, batch_id, matched_by_doc_id,
                              cat_cfg, dyaml, out_dir)
        return

    # ---- Sync streaming path ----
    # Stats
    total_in = total_out = total_records = 0
    n_ok = n_skip = n_fail = 0
    t_start = time.time()

    def _work(triple):
        i, row, md_path = triple
        try:
            status, n_recs, in_t, out_t = process_doc(
                client, prompt_template, row, md_path, cat_cfg, dyaml,
                doc_seq=i + 1, out_dir=out_dir,
                model=args.model, max_tokens=args.max_tokens,
                temperature=args.temperature, force=args.force,
            )
            return i, row, status, n_recs, in_t, out_t, None
        except Exception as e:
            return i, row, "exception", 0, 0, 0, f"{e}\n{traceback.format_exc()}"

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = [ex.submit(_work, m) for m in matched]
        for fut in as_completed(futs):
            i, row, status, n_recs, in_t, out_t, err = fut.result()
            doc_id = f"doc_{i+1:04d}"
            local = (row.get("local_path") or "")[:60]
            if status == "ok":
                n_ok += 1
                total_in += in_t; total_out += out_t; total_records += n_recs
                cost = in_t * PRICE_INPUT_PER_M / 1e6 + out_t * PRICE_OUTPUT_PER_M / 1e6
                print(f"  [{doc_id}] ok  {n_recs:3d} recs  in={in_t} out={out_t}  ${cost:.3f}  {local}",
                      flush=True)
            elif status == "skip":
                n_skip += 1
                print(f"  [{doc_id}] skip ({n_recs} recs cached)  {local}", flush=True)
            elif status == "parse_failed":
                n_fail += 1
                print(f"  [{doc_id}] PARSE FAILED  {local}", flush=True)
            else:
                n_fail += 1
                print(f"  [{doc_id}] {status}  {local}", flush=True)
                if err:
                    print(f"    {err[:300]}", flush=True)

    elapsed = time.time() - t_start
    cost_total = total_in * PRICE_INPUT_PER_M / 1e6 + total_out * PRICE_OUTPUT_PER_M / 1e6
    print(f"\n=== summary ===")
    print(f"docs: {n_ok} ok, {n_skip} skip, {n_fail} fail")
    print(f"records: {total_records}")
    print(f"tokens: in={total_in:,} out={total_out:,}  cost ${cost_total:.2f}")
    print(f"wall: {elapsed:.0f}s")


if __name__ == "__main__":
    main()
