#!/usr/bin/env python3
import anthropic, json
from pathlib import Path

meta_file = Path(__file__).resolve().parents[1] / "insights" / "batch_meta.json"
with open(meta_file) as f:
    meta = json.load(f)

batch_id = meta["batch_id"]
client = anthropic.Anthropic()
batch = client.messages.batches.retrieve(batch_id)
counts = batch.request_counts

print(f"Batch:  {batch_id}")
print(f"Status: {batch.processing_status}")
print(f"  succeeded:  {counts.succeeded}")
print(f"  processing: {counts.processing}")
print(f"  errored:    {counts.errored}")
print(f"  expired:    {counts.expired}")

if batch.processing_status == "ended":
    print(f"\nReady to retrieve:")
    print(f"  python3 scripts/03b_extract_registry_per_doc.py --retrieve {batch_id}")
