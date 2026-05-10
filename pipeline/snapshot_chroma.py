"""Snapshot the live ChromaDB directory for read-only querying during indexing.

Pauses the indexing process (SIGSTOP), copies the whole .chromadb/ dir, then
resumes it (SIGCONT). The pause is brief — typically a few seconds — and the
resulting snapshot can be queried via:

    python3 -m pipeline.rag search "..." --chroma-dir <snapshot_dir>
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_SRC = Path("corpora/.chromadb")
DEFAULT_DST = Path("corpora/.chromadb_snap")
WRITER_PATTERN = "pipeline.rag index"


def find_writer_pids(pattern: str) -> list[int]:
    try:
        out = subprocess.check_output(["pgrep", "-f", pattern], text=True)
    except subprocess.CalledProcessError:
        return []
    return [int(p) for p in out.split() if p.strip().isdigit()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--dst", type=Path, default=DEFAULT_DST)
    ap.add_argument("--no-pause", action="store_true",
                    help="Skip SIGSTOP/SIGCONT — only safe if the writer is idle")
    args = ap.parse_args()

    if not args.src.exists():
        print(f"source {args.src} does not exist", file=sys.stderr)
        return 1

    if args.dst.exists():
        print(f"removing existing {args.dst}")
        shutil.rmtree(args.dst)

    pids = [] if args.no_pause else find_writer_pids(WRITER_PATTERN)
    if pids:
        print(f"pausing writer pids: {pids}")
        for pid in pids:
            os.kill(pid, signal.SIGSTOP)
        time.sleep(0.3)
    else:
        print("no running writer detected" + (" (forced)" if args.no_pause else ""))

    try:
        t0 = time.time()
        shutil.copytree(args.src, args.dst)
        dt = time.time() - t0
        size_mb = sum(f.stat().st_size for f in args.dst.rglob("*") if f.is_file()) / 1024 / 1024
        print(f"copied {size_mb:,.0f} MB to {args.dst} in {dt:.1f}s")
    finally:
        if pids:
            print(f"resuming writer pids: {pids}")
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGCONT)
                except ProcessLookupError:
                    pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
