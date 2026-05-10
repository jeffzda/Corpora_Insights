#!/usr/bin/env python3
"""For 50 sampled records, compare narrative vs evidence vs source markdown
to test the architectural claim that one-shot whole-document extraction
binds doc-level context into atomic records.

For each record:
  1. Load `narrative` (atomic mechanism statement, model-rendered)
     and `evidence` (source paragraph excerpt).
  2. Tokenise both into content-bearing 2-grams and 3-grams (skip
     stopword-only n-grams).
  3. Find narrative n-grams NOT in evidence — i.e. content that did not
     come from the immediate source paragraph.
  4. For each such n-gram, check whether it appears elsewhere in the
     source markdown document.
       - in source_md  → "DOC_CONTEXT" (whole-document context bound in)
       - not in source_md → "VOICE_OR_IMPUTED" (model voice or fabrication)
  5. Aggregate per-record counts; classify the record.

Stratified sample across parents to ensure diversity.

Cost: free (no API).
"""
from __future__ import annotations
import json, random, re, time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PER_DOC_DIR = Path('/home/jeffzda/broadlearnings/corpora/arena/output/per_doc')
PARENT_ASSIGN = ROOT / 'closure/output/cluster_to_parent_assignments.jsonl'
ASSIGN_LAYERS = [
    ROOT / 'output/sweep/corpus_assignments.jsonl',
    ROOT / 'output/sweep/reclassify/reclassified_assignments.jsonl',
    ROOT / 'output/sweep/third_pass/third_pass_assignments.jsonl',
    ROOT / 'output/sweep/residual/residual_assignments.jsonl',
    ROOT / 'output/sweep/convergence/convergence_assignments.jsonl',
]
OUT = ROOT / 'closure/output/narrative_vs_evidence_audit.json'
N_SAMPLE = 50
SEED = 42

WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z\-]+|\d+")
STOP = set("""a about above after again against all am an and any are as at be because been before being below between both but by can could did do does doing don down during each few for from further had has have having he her here hers him himself his how i if in into is it its itself just me more most must my myself no nor not now of off on once only or other our ours out over own same she should so some such than that the their theirs them then there these they this those through to too under until up very was we were what when where which while who whom why will with would you your yours""".split())

def tokenise(t: str) -> list[str]:
    return [m.group(0).lower() for m in WORD_RE.finditer(t or '')]

def is_content(g: tuple[str, ...]) -> bool:
    if all(t in STOP for t in g): return False
    if all(len(t) < 3 and not t.isdigit() for t in g): return False
    return True

def ngrams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    return [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


def main():
    random.seed(SEED)

    print("Building record-id → parent_id map...", flush=True)
    cluster_to_parent = {a['cluster_id']: a.get('parent_id')
                         for a in (json.loads(l) for l in open(PARENT_ASSIGN))}
    rid_to_cluster = {}
    for f in ASSIGN_LAYERS:
        if not f.exists(): continue
        for line in open(f):
            a = json.loads(line)
            rid_to_cluster[a['record_id']] = a.get('cluster_id')
    rid_to_parent = {rid: cluster_to_parent.get(cid)
                     for rid, cid in rid_to_cluster.items()
                     if cluster_to_parent.get(cid)}
    parent_to_rids = defaultdict(list)
    for rid, pid in rid_to_parent.items():
        parent_to_rids[pid].append(rid)
    print(f"  {len(rid_to_parent):,} records mapped across {len(parent_to_rids)} parents",
          flush=True)

    # Stratified sample: at least one record from each of the largest 25 parents,
    # then fill remainder randomly across the rest. Ensures coverage diversity.
    parents_by_size = sorted(parent_to_rids.items(), key=lambda kv: -len(kv[1]))
    sampled_rids = []
    for pid, rids in parents_by_size[:25]:
        sampled_rids.append(random.choice(rids))
    remaining = N_SAMPLE - len(sampled_rids)
    pool = [rid for pid, rids in parents_by_size[25:] for rid in rids]
    sampled_rids.extend(random.sample(pool, k=min(remaining, len(pool))))
    sampled_rids = sampled_rids[:N_SAMPLE]
    print(f"  sampled {len(sampled_rids)} records (stratified across parents)\n", flush=True)

    # Build doc_id index across per_doc/*.json (one file per doc, holds many records)
    print("Indexing per_doc records...", flush=True)
    rid_to_record = {}
    rid_to_md_path = {}
    needed = set(sampled_rids)
    # Map record_id → doc_id from id format ARENA-DLV-NNNN-XX
    needed_docs = {f"doc_{rid.split('-')[2]}" for rid in needed}
    for doc_id in needed_docs:
        f = PER_DOC_DIR / f'{doc_id}.json'
        if not f.exists(): continue
        d = json.load(open(f))
        for r in d.get('records', []):
            if r.get('id') in needed:
                rid_to_record[r['id']] = r
                rid_to_md_path[r['id']] = r.get('markdown_path')
    print(f"  loaded {len(rid_to_record)} records  ({len(needed - set(rid_to_record))} missing)\n",
          flush=True)

    # Cache markdown text per doc
    md_cache = {}
    def get_md(path: str) -> str:
        if path in md_cache: return md_cache[path]
        try:
            md_cache[path] = Path(path).read_text(errors='ignore') if path else ''
        except Exception:
            md_cache[path] = ''
        return md_cache[path]

    # === Per-record analysis ===
    results = []
    print("=" * 88)
    print("PER-RECORD AUDIT — narrative vs evidence vs source markdown")
    print("=" * 88)
    for i, rid in enumerate(sampled_rids):
        rec = rid_to_record.get(rid)
        if not rec:
            print(f"\n[{i+1}/{N_SAMPLE}] {rid}: record not found, skipping")
            continue

        narrative = rec.get('narrative', '') or ''
        evidence = rec.get('evidence', '') or ''
        md_path = rid_to_md_path.get(rid, '')
        md_text = get_md(md_path)
        pid = rid_to_parent.get(rid)

        # Build n-gram sets
        narr_tok = tokenise(narrative)
        evid_tok = tokenise(evidence)
        md_tok = tokenise(md_text)

        narr_2grams = {g for g in ngrams(narr_tok, 2) if is_content(g)}
        narr_3grams = {g for g in ngrams(narr_tok, 3) if is_content(g)}
        evid_2grams = set(ngrams(evid_tok, 2))
        evid_3grams = set(ngrams(evid_tok, 3))
        md_2grams = set(ngrams(md_tok, 2))
        md_3grams = set(ngrams(md_tok, 3))

        # Narrative content NOT in evidence
        narr_only_2 = narr_2grams - evid_2grams
        narr_only_3 = narr_3grams - evid_3grams

        # Of those, how many ARE in source markdown (= drawn from doc context)
        in_md_2 = narr_only_2 & md_2grams
        not_md_2 = narr_only_2 - md_2grams
        in_md_3 = narr_only_3 & md_3grams
        not_md_3 = narr_only_3 - md_3grams

        # Classification
        # use 3-grams as the diagnostic since they're more content-bearing
        if not narr_only_3:
            verdict = 'NARRATIVE⊆EVIDENCE'
            doc_context_pct = 0.0
        else:
            doc_context_pct = len(in_md_3) / len(narr_only_3) * 100
            if doc_context_pct >= 50:
                verdict = 'DOC_CONTEXT_DRAWN'
            elif doc_context_pct >= 20:
                verdict = 'MIXED'
            else:
                verdict = 'VOICE_OR_IMPUTED'

        # Print
        print(f"\n[{i+1}/{N_SAMPLE}] {rid}  parent={pid}")
        print(f"  doc: {Path(md_path).name if md_path else '(none)'}")
        print(f"  narrative ({len(narr_tok)} tok): {narrative[:160].replace(chr(10),' ')}{'...' if len(narrative)>160 else ''}")
        print(f"  evidence  ({len(evid_tok)} tok): {(evidence[:160].replace(chr(10),' ') + '...') if len(evidence)>160 else evidence.replace(chr(10),' ')}")
        print(f"  narrative-only 3-grams: {len(narr_only_3)}  "
              f"(in source md: {len(in_md_3)} = {doc_context_pct:.0f}%, "
              f"not in source: {len(not_md_3)})")
        # Show 3 examples of each
        if in_md_3:
            samples = list(in_md_3)[:3]
            print(f"    ↳ DOC_CONTEXT examples: " + " | ".join(' '.join(s) for s in samples))
        if not_md_3:
            samples = list(not_md_3)[:3]
            print(f"    ↳ NOT-IN-SOURCE   examples: " + " | ".join(' '.join(s) for s in samples))
        print(f"  → VERDICT: {verdict}  ({doc_context_pct:.0f}% of novel content traces back to other parts of the doc)")

        results.append({
            'record_id': rid,
            'parent_id': pid,
            'doc_path': str(md_path) if md_path else None,
            'narrative_chars': len(narrative),
            'evidence_chars': len(evidence),
            'md_chars': len(md_text),
            'narr_only_3grams': len(narr_only_3),
            'narr_only_3grams_in_md': len(in_md_3),
            'narr_only_3grams_not_in_md': len(not_md_3),
            'doc_context_pct_3': doc_context_pct,
            'verdict': verdict,
            'sample_doc_context_3grams': [' '.join(g) for g in list(in_md_3)[:5]],
            'sample_not_in_source_3grams': [' '.join(g) for g in list(not_md_3)[:5]],
        })

    # === Aggregate ===
    verdicts = Counter(r['verdict'] for r in results)
    avg_pct = sum(r['doc_context_pct_3'] for r in results) / max(len(results), 1)
    avg_novel = sum(r['narr_only_3grams'] for r in results) / max(len(results), 1)
    avg_in_md = sum(r['narr_only_3grams_in_md'] for r in results) / max(len(results), 1)
    avg_not_md = sum(r['narr_only_3grams_not_in_md'] for r in results) / max(len(results), 1)

    print(f"\n{'='*70}")
    print("AGGREGATE")
    print('='*70)
    print(f"  Verdicts across {len(results)} records:")
    for v, n in verdicts.most_common():
        print(f"    {v:25} {n:>3}  ({n/len(results)*100:.0f}%)")
    print()
    print(f"  Avg novel 3-grams per record (narrative \\ evidence): {avg_novel:.1f}")
    print(f"  Avg 3-grams that DO appear elsewhere in source doc:  {avg_in_md:.1f}")
    print(f"  Avg 3-grams that DON'T appear in source doc:         {avg_not_md:.1f}")
    print(f"  Average doc-context-drawn rate: {avg_pct:.0f}%")

    OUT.write_text(json.dumps({
        'n_sampled': len(results),
        'seed': SEED,
        'verdicts': dict(verdicts),
        'aggregate_stats': {
            'avg_narr_only_3grams': round(avg_novel, 2),
            'avg_in_source_md': round(avg_in_md, 2),
            'avg_not_in_source_md': round(avg_not_md, 2),
            'avg_doc_context_pct': round(avg_pct, 1),
        },
        'records': results,
    }, indent=2))
    print(f"\nWrote {OUT}", flush=True)


if __name__ == '__main__':
    main()
