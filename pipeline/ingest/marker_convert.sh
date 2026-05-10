#!/bin/bash
# Batch PDF -> marker JSON -> rendered markdown for a domain.
#
# Resumable: skips any PDF whose .rendered.md already exists.
# Usage: marker_convert.sh <domain>
#   e.g. marker_convert.sh arena
#
# SUPERSEDED by pipeline/ingest/marker_convert.py — invoke via
#   python -m pipeline.run --domain <name> --step marker_convert
# Kept here for shell-only use (no Python config needed).
set -u

DOMAIN="${1:?usage: marker_convert.sh <domain>}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PDF_DIR="$ROOT/corpora/$DOMAIN/pdfs"
OUT_DIR="$ROOT/corpora/$DOMAIN/marker_output"
RENDER="$ROOT/pipeline/ingest/render_json.py"
LOG="$OUT_DIR/run.log"

mkdir -p "$OUT_DIR"
echo "=== run started $(date) ===" | tee -a "$LOG"

start_ts=$(date +%s)
n_total=0; n_skipped=0; n_converted=0; n_failed=0

while IFS= read -r pdf; do
    n_total=$((n_total+1))
    stem=$(basename "${pdf%.pdf}")
    json="$OUT_DIR/$stem/$stem.json"
    md="$OUT_DIR/$stem/$stem.rendered.md"

    if [ -f "$md" ]; then
        n_skipped=$((n_skipped+1))
        continue
    fi

    echo "=== $(date +%H:%M:%S) [$n_total] $stem ===" | tee -a "$LOG"
    if marker_single "$pdf" --output_format json --output_dir "$OUT_DIR" >> "$LOG" 2>&1; then
        if [ -f "$json" ]; then
            python3 "$RENDER" "$json" >> "$LOG" 2>&1 \
                && n_converted=$((n_converted+1)) \
                || { echo "[RENDER FAIL] $stem" | tee -a "$LOG"; n_failed=$((n_failed+1)); }
        else
            echo "[NO JSON] $stem" | tee -a "$LOG"
            n_failed=$((n_failed+1))
        fi
    else
        echo "[MARKER FAIL] $stem" | tee -a "$LOG"
        n_failed=$((n_failed+1))
    fi
done < <(find "$PDF_DIR" -name "*.pdf" | sort)

end_ts=$(date +%s)
echo "=== run finished $(date) ===" | tee -a "$LOG"
echo "total=$n_total skipped=$n_skipped converted=$n_converted failed=$n_failed elapsed=$((end_ts-start_ts))s" | tee -a "$LOG"
