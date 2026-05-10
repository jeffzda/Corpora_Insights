"""PDF → marker JSON → rendered markdown conversion.

Generalises:
    pipeline/ingest/marker_convert.sh (existing bash driver, used for ARENA + ANAO)

Walks every PDF under the corpus's pdf_dir, skips PDFs whose
<stem>/<stem>.rendered.md already exists, and for each remaining PDF:
    1. Runs `marker_single <pdf> --output_format json --output_dir <out>`
       which writes <out>/<stem>/<stem>.json
    2. Runs render_json.py to turn that JSON into <stem>.rendered.md
       (footnote rewriting, page markers, char-encoding fixups)

Resume-safe (re-running picks up where it left off). Heartbeat every N
items with rate + ETA per CLAUDE.md long-running-script standing instructions.

Domain config (domain.yaml ingest.marker_convert — all optional, sensible
defaults derive from the corpus directory layout):

    pdf_dir              default 'corpora/<domain>/pdfs'
    pdf_glob             default '**/*.pdf' (recursive)
    output_dir           default 'corpora/<domain>/marker_output'
    log_path             default '<output_dir>/run.log'
    extra_marker_args    list[str], extra flags forwarded to marker_single
    skip_existing        default true (resume)
    heartbeat_every      default 10 PDFs

Usage:
    python -m pipeline.run --domain anao --step marker_convert
    python -m pipeline.run --domain arena --step marker_convert --limit 5
"""
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from pipeline.config import DomainConfig

ROOT = Path(__file__).resolve().parents[2]
RENDER = ROOT / "pipeline" / "ingest" / "render_json.py"


def _resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def _convert_one(pdf_str: str, stem: str, output_dir_str: str,
                 marker: str, extra_args: list[str]):
    """Module-level so ProcessPoolExecutor can pickle it.

    Returns (stem, status, log_text). status ∈
    {'ok','marker_fail','no_json','render_fail'}.
    """
    output_dir = Path(output_dir_str)
    json_out = output_dir / stem / f"{stem}.json"
    cmd = [marker, pdf_str, "--output_format", "json",
           "--output_dir", output_dir_str, *extra_args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=True)
        marker_log = (r.stdout or "") + (r.stderr or "")
    except subprocess.CalledProcessError as e:
        return stem, "marker_fail", (e.stdout or "") + (e.stderr or "")
    if not json_out.exists():
        return stem, "no_json", marker_log
    try:
        r2 = subprocess.run([sys.executable, str(RENDER), str(json_out)],
                            capture_output=True, text=True, check=True)
        render_log = (r2.stdout or "") + (r2.stderr or "")
        return stem, "ok", marker_log + render_log
    except subprocess.CalledProcessError as e:
        return stem, "render_fail", marker_log + (e.stdout or "") + (e.stderr or "")


def _check_marker_installed() -> str:
    p = shutil.which("marker_single")
    if not p:
        raise SystemExit(
            "marker_single not found on PATH. Install via "
            "`pip install marker-pdf` (CUDA build recommended)."
        )
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True)
    ap.add_argument("--limit", type=int, default=None,
                    help="Convert at most N un-converted PDFs (smoke test)")
    ap.add_argument("--force", action="store_true",
                    help="Re-convert PDFs whose .rendered.md already exists")
    ap.add_argument("--workers", type=int, default=None,
                    help="Number of parallel worker processes (default: config or 1)")
    args, _ = ap.parse_known_args()

    cfg = DomainConfig.load(args.domain)
    ig = (cfg.raw.get("ingest") or {})
    mc = (ig.get("marker_convert") or {})

    pdf_dir = _resolve(mc.get("pdf_dir") or f"corpora/{args.domain}/pdfs")
    pdf_glob = mc.get("pdf_glob", "**/*.pdf")
    output_dir = _resolve(mc.get("output_dir") or f"corpora/{args.domain}/marker_output")
    log_path = _resolve(mc.get("log_path") or (output_dir / "run.log"))
    extra_args = list(mc.get("extra_marker_args") or [])
    skip_existing = bool(mc.get("skip_existing", True)) and not args.force
    heartbeat_every = int(mc.get("heartbeat_every", 10))
    workers = (args.workers if args.workers is not None
               else int(mc.get("workers", 1)))

    if not pdf_dir.exists():
        raise SystemExit(f"pdf_dir does not exist: {pdf_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    marker = _check_marker_installed()
    print(f"marker_single: {marker}", flush=True)

    pdfs = sorted(pdf_dir.glob(pdf_glob))
    if not pdfs:
        raise SystemExit(f"no PDFs found at {pdf_dir} (glob {pdf_glob!r})")

    pending = []
    for pdf in pdfs:
        if args.limit is not None and len(pending) >= args.limit:
            break
        stem = pdf.stem
        rendered = output_dir / stem / f"{stem}.rendered.md"
        if skip_existing and rendered.exists():
            continue
        pending.append((pdf, stem, rendered))

    n_total = len(pdfs)
    n_skip = n_total - len(pending)
    print(f"PDFs total: {n_total:,}  already converted: {n_skip:,}  "
          f"pending: {len(pending):,}", flush=True)
    if not pending:
        print("nothing to do.", flush=True)
        return

    n_ok = n_fail = 0
    started = time.time()
    log_f = open(log_path, "a")
    log_f.write(f"\n=== run started {time.strftime('%Y-%m-%d %H:%M:%S')} "
                f"workers={workers} ===\n")
    log_f.flush()
    print(f"workers: {workers}", flush=True)

    def _record(i, stem, status, log_text):
        nonlocal n_ok, n_fail
        log_f.write(f"=== [{i}/{len(pending)}] {stem} status={status} ===\n")
        if log_text:
            log_f.write(log_text)
            if not log_text.endswith("\n"):
                log_f.write("\n")
        log_f.flush()
        if status == "ok":
            n_ok += 1
        else:
            n_fail += 1
            print(f"  [{i:>4}/{len(pending)}] FAIL ({status}) {stem}", flush=True)
        if i % heartbeat_every == 0 or i == len(pending):
            el = time.time() - started
            rate = i / el if el > 0 else 0
            eta = (len(pending) - i) / rate if rate > 0 else 0
            print(f"  [{i:>4}/{len(pending)}] ok={n_ok} fail={n_fail}  "
                  f"{rate:.2f} pdf/s  ETA={eta/60:.1f} min",
                  flush=True)

    try:
        if workers <= 1:
            for i, (pdf, stem, _r) in enumerate(pending, 1):
                stem_, status, log_text = _convert_one(
                    str(pdf), stem, str(output_dir), marker, extra_args)
                _record(i, stem_, status, log_text)
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(_convert_one, str(pdf), stem,
                                str(output_dir), marker, extra_args):
                        (i, stem)
                    for i, (pdf, stem, _r) in enumerate(pending, 1)
                }
                done = 0
                for fut in as_completed(futures):
                    done += 1
                    i_orig, stem_orig = futures[fut]
                    try:
                        stem_, status, log_text = fut.result()
                    except Exception as e:
                        stem_, status, log_text = stem_orig, "exception", repr(e)
                    _record(done, stem_, status, log_text)
    finally:
        elapsed = time.time() - started
        log_f.write(f"=== run finished {time.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"ok={n_ok} fail={n_fail} elapsed={elapsed:.0f}s ===\n")
        log_f.close()

    rate_str = (f" ({n_ok / (elapsed / 60):.1f} pdf/min)"
                if elapsed > 0 and n_ok > 0 else "")
    print(f"\nfinished: {n_ok} ok, {n_fail} fail, {elapsed / 60:.1f} min{rate_str}",
          flush=True)
    print(f"output: {output_dir}\nlog: {log_path}", flush=True)


if __name__ == "__main__":
    main()
