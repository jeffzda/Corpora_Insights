"""Stage g03 — Embedding-based normalisation + catalogue cross-reference.

Generalises:
    pipeline/development/arena_glossary/03_normalise_and_match.py

Inputs (from glossary.candidate.output_dir):
    candidate_frequencies.csv         (regex, required)
    ner_candidate_frequencies.csv     (optional)
    ner_trf_candidate_frequencies.csv (optional)

Steps:
  1. Combine all candidate sources; filter to surfaces with ≥ min_mentions.
  2. Embed surfaces + catalogue strings (project_title + lead_org).
  3. Cluster surfaces at cosine ≥ cluster_threshold to collapse variants.
  4. Match each cluster centroid against catalogue strings.

Outputs:
    output_path                       entity_index.csv
    output_dir/entity_clusters_detail.csv
    output_dir/unmatched_top.csv

Domain config (domain.yaml glossary.normalise):
    catalogue_path             path to corpus catalogue CSV
    project_title_column       catalogue column for project/document titles
    lead_org_column            catalogue column for lead organisation (optional)
    embedding_model            default 'all-mpnet-base-v2'
    min_mentions               default 3
    cluster_threshold          default 0.85
    catalogue_match_threshold  default 0.80
    output_path                where to write entity_index.csv
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path

from pipeline.config import DomainConfig
from pipeline.glossary.shared.io import resolve


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', required=True)
    args, _ = ap.parse_known_args()

    cfg = DomainConfig.load(args.domain)
    c = (cfg.glossary.get('candidate') or {})
    nrm = (cfg.glossary.get('normalise') or {})

    cand_dir = resolve(c.get('output_dir') or '')
    output_path = resolve(nrm.get('output_path') or (cand_dir / 'entity_index.csv'))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    clusters_detail = output_path.parent / 'entity_clusters_detail.csv'
    unmatched_top = output_path.parent / 'unmatched_top.csv'

    catalogue_path = resolve(nrm.get('catalogue_path') or '')
    title_col = nrm.get('project_title_column')
    org_col = nrm.get('lead_org_column')
    if not catalogue_path.exists():
        raise SystemExit(f'catalogue_path missing: {catalogue_path}')
    if not title_col:
        raise SystemExit('glossary.normalise.project_title_column is required')

    embedding_model = nrm.get('embedding_model', 'all-mpnet-base-v2')
    min_mentions = int(nrm.get('min_mentions', 3))
    cluster_threshold = float(nrm.get('cluster_threshold', 0.85))
    match_threshold = float(nrm.get('catalogue_match_threshold', 0.80))

    import numpy as np
    import pandas as pd

    print(f"Loading candidate frequencies from {cand_dir} ...", flush=True)
    sources = []
    regex_path = cand_dir / 'candidate_frequencies.csv'
    if regex_path.exists():
        df = pd.read_csv(regex_path)
        df['source'] = 'regex'
        sources.append(df)
    ner_path = cand_dir / 'ner_candidate_frequencies.csv'
    if ner_path.exists():
        df_ner = pd.read_csv(ner_path)
        df_ner['pattern'] = 'ner_sm'
        df_ner['source'] = 'ner_sm'
        sources.append(df_ner)
        print(f"  loaded NER-sm freq table: {len(df_ner)} surfaces", flush=True)
    ner_trf_path = cand_dir / 'ner_trf_candidate_frequencies.csv'
    if ner_trf_path.exists():
        df_trf = pd.read_csv(ner_trf_path)
        df_trf['pattern'] = 'ner_trf'
        df_trf['source'] = 'ner_trf'
        sources.append(df_trf)
        print(f"  loaded NER-trf freq table: {len(df_trf)} surfaces", flush=True)
    if not sources:
        raise SystemExit(f'no candidate frequency CSVs found in {cand_dir}')

    df = pd.concat(sources, ignore_index=True)
    grouped = df.groupby('surface').agg(
        n_total_mentions=('n_total_mentions', 'sum'),
        n_unique_docs=('n_unique_docs', 'max'),
        sources=('source', lambda s: ','.join(sorted(set(s)))),
        primary_pattern=('pattern', 'first'),
    ).reset_index()
    print(f"  combined unique surfaces: {len(grouped):,}", flush=True)

    surf_df = grouped[grouped['n_total_mentions'] >= min_mentions].copy().reset_index(drop=True)
    print(f"  with ≥{min_mentions} mentions: {len(surf_df):,}", flush=True)

    print(f"Loading catalogue from {catalogue_path} ...", flush=True)
    cat = pd.read_csv(catalogue_path)
    if title_col not in cat.columns:
        raise SystemExit(
            f'project_title_column {title_col!r} not in catalogue columns: '
            f'{list(cat.columns)[:8]}...'
        )
    if org_col and org_col not in cat.columns:
        org_col = next((col for col in cat.columns
                        if 'lead organisation' in col.lower() or 'lead organization' in col.lower()),
                       None)
    print(f"  Project col: {title_col!r}  Org col: {org_col!r}", flush=True)

    cat_records = []
    for _, r in cat.iterrows():
        title = str(r[title_col]).strip()
        if title and title.lower() != 'nan':
            cat_records.append({'name': title, 'kind': 'project_title', 'project_id': title})
        if org_col:
            org = str(r[org_col]).strip()
            if org and org.lower() != 'nan':
                cat_records.append({'name': org, 'kind': 'lead_org', 'project_id': title})
    cat_df = (pd.DataFrame(cat_records)
              .drop_duplicates(subset=['name', 'kind'])
              .reset_index(drop=True))
    print(f"  catalogue strings to match against: {len(cat_df):,}", flush=True)

    print(f"Loading sentence-transformers model ({embedding_model}) ...", flush=True)
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(embedding_model)

    print(f"Embedding {len(surf_df):,} candidate surfaces...", flush=True)
    surf_emb = model.encode(surf_df['surface'].tolist(),
                            normalize_embeddings=True, show_progress_bar=True, batch_size=128)
    print(f"Embedding {len(cat_df):,} catalogue strings...", flush=True)
    cat_emb = model.encode(cat_df['name'].tolist(),
                           normalize_embeddings=True, show_progress_bar=True, batch_size=128)
    surf_emb = np.asarray(surf_emb, dtype=np.float32)
    cat_emb = np.asarray(cat_emb, dtype=np.float32)

    print(f"\nClustering surfaces (cosine ≥{cluster_threshold}) ...", flush=True)
    from sklearn.cluster import AgglomerativeClustering
    if len(surf_df) > 1:
        clusterer = AgglomerativeClustering(
            n_clusters=None, distance_threshold=1 - cluster_threshold,
            metric='cosine', linkage='average')
        cluster_ids = clusterer.fit_predict(surf_emb)
    else:
        cluster_ids = np.array([0] * len(surf_df))
    surf_df['cluster_id'] = cluster_ids
    print(f"  produced {len(set(cluster_ids)):,} clusters from {len(surf_df):,} surfaces", flush=True)

    cluster_to_member_idx = defaultdict(list)
    for i, cid in enumerate(cluster_ids):
        cluster_to_member_idx[cid].append(i)

    cluster_records = []
    for cid, member_idx in cluster_to_member_idx.items():
        members = surf_df.iloc[member_idx]
        canonical = members.sort_values('n_total_mentions', ascending=False).iloc[0]
        all_variants = members.sort_values('n_total_mentions',
                                           ascending=False)['surface'].tolist()
        canonical_idx = members['n_total_mentions'].idxmax()
        centroid = surf_emb[canonical_idx]

        sims = cat_emb @ centroid
        best_i = int(sims.argmax())
        best_sim = float(sims[best_i])
        if best_sim >= match_threshold:
            match_name = cat_df.iloc[best_i]['name']
            match_kind = cat_df.iloc[best_i]['kind']
            match_proj = cat_df.iloc[best_i]['project_id']
            match_status = 'matched'
        else:
            match_name = match_kind = match_proj = ''
            match_status = 'unmatched'

        cluster_records.append({
            'cluster_id': int(cid),
            'canonical_surface': canonical['surface'],
            'cluster_size': len(members),
            'n_total_mentions': int(members['n_total_mentions'].sum()),
            'n_unique_docs': int(members['n_unique_docs'].max()),
            'top_3_variants': ' || '.join(all_variants[:3]),
            'all_variants': ' || '.join(all_variants[:20]),
            'pattern': canonical['primary_pattern'],
            'sources': canonical['sources'],
            'catalogue_match_name': match_name,
            'catalogue_match_kind': match_kind,
            'catalogue_project_id': match_proj,
            'catalogue_match_confidence': round(best_sim, 3),
            'match_status': match_status,
        })

    out_df = pd.DataFrame(cluster_records).sort_values('n_total_mentions', ascending=False)
    out_df.to_csv(output_path, index=False)

    surf_df['catalogue_match_name'] = surf_df['cluster_id'].map(
        out_df.set_index('cluster_id')['catalogue_match_name'].to_dict())
    surf_df.to_csv(clusters_detail, index=False)

    unmatched_df = out_df[out_df['match_status'] == 'unmatched'].sort_values(
        'n_total_mentions', ascending=False)
    unmatched_df.head(500).to_csv(unmatched_top, index=False)

    print(f"\nResults:")
    print(f"  total clusters:          {len(out_df):,}")
    print(f"  matched to catalogue:    {(out_df['match_status'] == 'matched').sum():,}")
    print(f"  unmatched:               {(out_df['match_status'] == 'unmatched').sum():,}")
    print(f"\nWrote:\n  {output_path}\n  {clusters_detail}\n  {unmatched_top}", flush=True)


if __name__ == "__main__":
    main()
