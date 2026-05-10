#!/usr/bin/env python3
"""Stage 3: embedding-based normalisation + ARENA catalogue cross-reference.

Inputs:
- output/candidate_frequencies.csv   (from stage 1)
- output/ner_candidate_frequencies.csv (from stage 2 — optional, used if present)
- corpora/arena/arena-projects-export_*.csv (catalogue)

Steps:
1. Load all unique candidate surface forms; filter to surfaces with ≥3
   total mentions (cuts long-tail noise).
2. Embed every surface + every catalogue project_title + lead_org with
   sentence-transformers/all-mpnet-base-v2 (CPU-fine for ~30k strings).
3. Cluster surfaces at cosine ≥0.85 to collapse variants.
4. For each cluster, find max cosine vs catalogue (project_title or
   lead_org). Threshold 0.80+ for a confident match.
5. Output:
   - entity_index.csv: one row per canonical entity with cluster_size,
     n_mentions, n_unique_docs, catalogue_match (or null), match_kind,
     match_confidence, top_surface_variants
"""
import csv
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = Path(__file__).resolve().parent.parent / 'output'

REGEX_FREQ = OUT_DIR / 'candidate_frequencies.csv'
NER_FREQ = OUT_DIR / 'ner_candidate_frequencies.csv'
NER_TRF_FREQ = OUT_DIR / 'ner_trf_candidate_frequencies.csv'
CATALOGUE = ROOT / 'corpora/arena/arena-projects-export_1772932404.csv'

ENTITY_INDEX = OUT_DIR / 'entity_index.csv'
CLUSTERS_DETAIL = OUT_DIR / 'entity_clusters_detail.csv'
UNMATCHED = OUT_DIR / 'unmatched_top.csv'

MIN_MENTIONS = 3            # filter low-frequency long-tail
CLUSTER_THRESHOLD = 0.85    # cosine for variant collapsing
CATALOGUE_MATCH_THRESHOLD = 0.80


def normalise_for_embed(s):
    """Light normalisation — preserve case + acronyms (they're informative for embedding)."""
    return re.sub(r'\s+', ' ', s).strip()


def main():
    print(f"Loading candidate frequencies...")
    df_regex = pd.read_csv(REGEX_FREQ)
    df_regex['source'] = 'regex'
    sources = [df_regex]
    if NER_FREQ.exists():
        df_ner = pd.read_csv(NER_FREQ)
        df_ner['pattern'] = 'ner_sm'
        df_ner['source'] = 'ner_sm'
        sources.append(df_ner)
        print(f"  loaded NER-sm freq table: {len(df_ner)} surfaces")
    if NER_TRF_FREQ.exists():
        df_trf = pd.read_csv(NER_TRF_FREQ)
        df_trf['pattern'] = 'ner_trf'
        df_trf['source'] = 'ner_trf'
        sources.append(df_trf)
        print(f"  loaded NER-trf freq table: {len(df_trf)} surfaces")
    df = pd.concat(sources, ignore_index=True)
    # Merge regex and ner counts on surface
    grouped = df.groupby('surface').agg(
        n_total_mentions=('n_total_mentions', 'sum'),
        n_unique_docs=('n_unique_docs', 'max'),
        sources=('source', lambda s: ','.join(sorted(set(s)))),
        primary_pattern=('pattern', 'first'),
    ).reset_index()
    print(f"  combined unique surfaces: {len(grouped):,}")

    # Filter
    surf_df = grouped[grouped['n_total_mentions'] >= MIN_MENTIONS].copy().reset_index(drop=True)
    print(f"  with ≥{MIN_MENTIONS} mentions: {len(surf_df):,}")

    # Load catalogue
    print(f"Loading catalogue...")
    cat = pd.read_csv(CATALOGUE)
    proj_title_col = cat.columns[0]
    org_col = next((c for c in cat.columns if 'lead organisation' in c.lower()
                     or 'lead organization' in c.lower()), None)
    print(f"  Project col: '{proj_title_col}'  Org col: '{org_col}'")

    cat_records = []
    for _, r in cat.iterrows():
        title = str(r[proj_title_col]).strip()
        if title and title != 'nan':
            cat_records.append({'name': title, 'kind': 'project_title', 'project_id': title})
        if org_col:
            org = str(r[org_col]).strip()
            if org and org != 'nan':
                cat_records.append({'name': org, 'kind': 'lead_org', 'project_id': title})
    cat_df = pd.DataFrame(cat_records).drop_duplicates(subset=['name','kind']).reset_index(drop=True)
    print(f"  catalogue strings to match against: {len(cat_df):,} (titles + orgs)")

    # Load embedding model
    print(f"Loading sentence-transformers model...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-mpnet-base-v2')

    # Embed
    print(f"Embedding {len(surf_df):,} candidate surfaces...")
    surf_emb = model.encode(surf_df['surface'].tolist(),
                              normalize_embeddings=True,
                              show_progress_bar=True,
                              batch_size=128)
    print(f"Embedding {len(cat_df):,} catalogue strings...")
    cat_emb = model.encode(cat_df['name'].tolist(),
                             normalize_embeddings=True,
                             show_progress_bar=True,
                             batch_size=128)
    surf_emb = np.asarray(surf_emb, dtype=np.float32)
    cat_emb = np.asarray(cat_emb, dtype=np.float32)

    # Cluster surfaces by cosine ≥ CLUSTER_THRESHOLD
    print(f"\nClustering surfaces (cosine ≥{CLUSTER_THRESHOLD})...")
    from sklearn.cluster import AgglomerativeClustering
    if len(surf_df) > 1:
        clusterer = AgglomerativeClustering(
            n_clusters=None, distance_threshold=1 - CLUSTER_THRESHOLD,
            metric='cosine', linkage='average')
        cluster_ids = clusterer.fit_predict(surf_emb)
    else:
        cluster_ids = np.array([0] * len(surf_df))
    surf_df['cluster_id'] = cluster_ids
    print(f"  produced {len(set(cluster_ids)):,} clusters from {len(surf_df):,} surfaces")

    # Build canonical entity per cluster (most-mentioned surface as canonical)
    cluster_records = []
    cluster_to_member_idx = defaultdict(list)
    for i, c in enumerate(cluster_ids):
        cluster_to_member_idx[c].append(i)

    for cid, member_idx in cluster_to_member_idx.items():
        members = surf_df.iloc[member_idx]
        canonical = members.sort_values('n_total_mentions', ascending=False).iloc[0]
        all_variants = members.sort_values('n_total_mentions', ascending=False)['surface'].tolist()
        # Use the most-mentioned member's embedding as the cluster centroid
        canonical_idx = members['n_total_mentions'].idxmax()
        centroid = surf_emb[canonical_idx]

        # Match to catalogue
        sims = cat_emb @ centroid
        best_i = int(np.argmax(sims))
        best_sim = float(sims[best_i])
        if best_sim >= CATALOGUE_MATCH_THRESHOLD:
            match_name = cat_df.iloc[best_i]['name']
            match_kind = cat_df.iloc[best_i]['kind']
            match_proj = cat_df.iloc[best_i]['project_id']
            match_status = 'matched'
        else:
            match_name = ''
            match_kind = ''
            match_proj = ''
            match_status = 'unmatched'

        cluster_records.append({
            'cluster_id': int(cid),
            'canonical_surface': canonical['surface'],
            'cluster_size': len(members),
            'n_total_mentions': int(members['n_total_mentions'].sum()),
            'n_unique_docs': int(members['n_unique_docs'].max()),
            'top_3_variants': ' || '.join(all_variants[:3]),
            'all_variants': ' || '.join(all_variants[:20]),  # cap to 20 for CSV
            'pattern': canonical['primary_pattern'],
            'sources': canonical['sources'],
            'catalogue_match_name': match_name,
            'catalogue_match_kind': match_kind,
            'catalogue_project_id': match_proj,
            'catalogue_match_confidence': round(best_sim, 3),
            'match_status': match_status,
        })

    out_df = pd.DataFrame(cluster_records).sort_values('n_total_mentions', ascending=False)
    out_df.to_csv(ENTITY_INDEX, index=False)

    # Cluster detail (per surface, with cluster id) for drill-down
    surf_df['catalogue_match_name'] = surf_df['cluster_id'].map(
        out_df.set_index('cluster_id')['catalogue_match_name'].to_dict())
    surf_df.to_csv(CLUSTERS_DETAIL, index=False)

    # Unmatched top — for human review
    unmatched_df = out_df[out_df['match_status'] == 'unmatched'].sort_values('n_total_mentions', ascending=False)
    unmatched_df.head(500).to_csv(UNMATCHED, index=False)

    print(f"\nResults:")
    print(f"  total clusters:          {len(out_df):,}")
    print(f"  matched to catalogue:    {(out_df['match_status']=='matched').sum():,}")
    print(f"  unmatched:               {(out_df['match_status']=='unmatched').sum():,}")
    print(f"\nWrote:")
    print(f"  {ENTITY_INDEX}  ({ENTITY_INDEX.stat().st_size:,} bytes)")
    print(f"  {CLUSTERS_DETAIL}  ({CLUSTERS_DETAIL.stat().st_size:,} bytes)")
    print(f"  {UNMATCHED}  ({UNMATCHED.stat().st_size:,} bytes)")

    # Top output samples
    print(f"\nTop 20 entities by mention count:")
    print(f"{'canonical':<40}  {'#mentions':>9}  {'#docs':>5}  {'match':<30}  {'conf':>5}")
    for _, r in out_df.head(20).iterrows():
        m = (r['catalogue_match_name'] or '')[:30]
        print(f"  {r['canonical_surface'][:38]:<38}  {r['n_total_mentions']:>9,}  "
              f"{r['n_unique_docs']:>5}  {m:<30}  {r['catalogue_match_confidence']:>5}")

    print(f"\nTop 10 unmatched entities (likely external comparators or unlisted partners):")
    for _, r in unmatched_df.head(10).iterrows():
        print(f"  {r['canonical_surface'][:50]:<50}  {r['n_total_mentions']:>5,}× across "
              f"{r['n_unique_docs']:>3} docs")


if __name__ == "__main__":
    main()
