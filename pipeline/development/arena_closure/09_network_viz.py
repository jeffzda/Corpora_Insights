#!/usr/bin/env python3
"""Closure phase 5b: cluster co-occurrence network visualisation.

Builds two visualisations from the cluster_cooccurrence.json data:

1. Static PNG (matplotlib + networkx + spring layout) for the methodology
   paper / static reference.
2. Interactive HTML (self-contained, vis.js from CDN — no install) for
   exploration. Hover/click to see cluster signatures.

Edges are weighted by co-occurrence count; nodes are sized by cluster
membership and coloured by general/tech_specific scope (from script 06's
output where available, else neutral).
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import networkx as nx
import numpy as np

V2_OUT = Path(__file__).resolve().parents[2] / 'output'
CLOSURE_OUT = Path(__file__).resolve().parent.parent / 'output'
CATALOGUE = V2_OUT / 'sweep' / 'convergence' / 'catalogue_after_convergence.json'
ASSIGNMENTS = V2_OUT / 'sweep' / 'corpus_assignments.jsonl'
INPUT_FILTER = V2_OUT / 'filter_input.jsonl'
PROJECTS_CSV = Path('/home/jeffzda/broadlearnings/corpora/arena/arena-projects-export_1772932404.csv')
COOCCUR = CLOSURE_OUT / 'cluster_cooccurrence.json'
GENERAL = CLOSURE_OUT / 'general_mechanisms.json'

# Categorical palette for dominant ARENA category (Tableau-style + extras)
CATEGORY_PALETTE = {
    'Solar energy':              '#e15759',
    'Battery storage':           '#4e79a7',
    'Hydrogen energy':           '#76b7b2',
    'Distributed energy resources': '#f28e2b',
    'Demand response':           '#edc948',
    'Electric vehicles':         '#b07aa1',
    'Renewables for industry':   '#9c755f',
    'Concentrated solar thermal':'#ff9da7',
    'Bioenergy / Energy from waste': '#59a14f',
    'Hydropower / Pumped Hydro Energy Storage': '#bab0ac',
    'System security and reliability': '#37474f',
    'Large-scale solar':         '#c7522b',
    'Wind energy':               '#86c5da',
    'Geothermal energy':         '#a45e3b',
    'Ocean energy':              '#3a7ca5',
    'Hybrid technologies':       '#a0a0a0',
    'Renewables in buildings':   '#d4a017',
    'Off grid':                  '#666666',
}
DEFAULT_COLOR = '#888888'

# Categorical palette for mechanism domain (~18 domains + tech-specific bucket)
DOMAIN_PALETTE = {
    'program_design':                '#4e79a7',
    'infrastructure_project_delivery':'#f28e2b',
    'data_systems_integration':      '#e15759',
    'regulatory_framework_design':   '#76b7b2',
    'modelling_methodology':         '#59a14f',
    'supply_chain':                  '#edc948',
    'equipment_lifecycle':           '#b07aa1',
    'novel_technology_adoption':     '#ff9da7',
    'contracts_legal':               '#9c755f',
    'community_engagement':          '#bab0ac',
    'lab_to_field_translation':      '#86bcb6',
    'organisational_coordination':   '#fabfd2',
    'financial_incentive_design':    '#d4a017',
    'market_structure':              '#5b8c5a',
    'safety_governance':             '#c44e52',
    'capacity_building':             '#937860',
    'innovation_funding':            '#8c564b',
    'public_private_coordination':   '#7f7f7f',
    '_tech_specific':                '#d0d0d0',  # neutral for tech-specific (no domain)
}

PNG_OUT_TEMPLATE = 'cluster_network_{tag}.png'
HTML_OUT_TEMPLATE = 'cluster_network_{tag}.html'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--min-cooccur', type=int, default=4,
                    help='Minimum co-occurrence count to include an edge')
    ap.add_argument('--color-by', choices=['tech','domain'], default='tech',
                    help='tech = ARENA category; domain = mechanism domain (general_mechanisms tags)')
    args = ap.parse_args()

    print(f"Loading data...", flush=True)
    pairs = json.load(open(COOCCUR))
    catalogue = json.load(open(CATALOGUE))['clusters']
    cid_to_meta = {c['cluster_id']: c for c in catalogue}
    assigns = [json.loads(l) for l in open(ASSIGNMENTS)]
    cluster_size = Counter(a.get('cluster_id') for a in assigns
                            if a.get('cluster_id') in cid_to_meta)

    # Dominant ARENA category per cluster (from project metadata join)
    rows = [json.loads(l) for l in open(INPUT_FILTER)]
    rid_to = {r['record_id']: r for r in rows}
    csv_rows = list(csv.DictReader(open(PROJECTS_CSV)))
    proj_to_cat = {r['Project']: r.get('Category','') for r in csv_rows}
    cluster_dom_cat = {}
    cluster_dom_share = {}
    cluster_members = {}
    # Domain classification (general vs tech_specific + domain tags)
    general_classes = {c['cluster_id']: c for c in json.load(open(GENERAL))} \
        if GENERAL.exists() else {}
    cluster_domain = {}  # cluster_id -> primary domain tag, or '_tech_specific'
    for cid, c in general_classes.items():
        if c.get('scope') == 'tech_specific':
            cluster_domain[cid] = '_tech_specific'
        elif c.get('scope') == 'general':
            doms = c.get('domains') or []
            cluster_domain[cid] = doms[0] if doms else '_tech_specific'
    for a in assigns:
        cid = a.get('cluster_id')
        if cid: cluster_members.setdefault(cid, []).append(a['record_id'])
    for cid, mem in cluster_members.items():
        cats = Counter(proj_to_cat.get(rid_to.get(r,{}).get('project',''),'')
                       for r in mem)
        cats.pop('', None)
        if cats:
            top, n = cats.most_common(1)[0]
            cluster_dom_cat[cid] = top
            cluster_dom_share[cid] = n / sum(cats.values())

    edges = [(p['cluster_a'], p['cluster_b'], p['cooccurrences'])
             for p in pairs if p['cooccurrences'] >= args.min_cooccur]
    print(f"  edges with count ≥ {args.min_cooccur}: {len(edges)}", flush=True)

    G = nx.Graph()
    for a, b, w in edges:
        G.add_edge(a, b, weight=w)

    # Largest connected component
    if G.number_of_nodes():
        components = list(nx.connected_components(G))
        components.sort(key=len, reverse=True)
        print(f"  components: {len(components)}; largest has {len(components[0])} nodes", flush=True)
        G = G.subgraph(components[0]).copy()

    print(f"  visualising graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges", flush=True)

    # ====== Static PNG ======
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    pos = nx.spring_layout(G, k=1.4, iterations=200, seed=7,
                            weight='weight')
    fig, ax = plt.subplots(figsize=(20, 16))
    # Edges
    weights = [G[u][v]['weight'] for u, v in G.edges()]
    max_w = max(weights) if weights else 1
    nx.draw_networkx_edges(
        G, pos, width=[1.2 + 5*(w/max_w) for w in weights],
        edge_color=[(0.15, 0.20, 0.32, 0.45 + 0.45*(w/max_w)) for w in weights],
        ax=ax,
    )
    # Nodes coloured per --color-by
    sizes = [80 + 8*cluster_size.get(n, 1) for n in G.nodes()]
    if args.color_by == 'tech':
        node_color_map = {n: CATEGORY_PALETTE.get(cluster_dom_cat.get(n, ''), DEFAULT_COLOR)
                          for n in G.nodes()}
        active_palette = CATEGORY_PALETTE
        used_keys = {cluster_dom_cat.get(n, '') for n in G.nodes()}
        legend_label_fn = lambda k: k[:30]
        title_phrase = 'dominant ARENA category'
    else:  # domain
        node_color_map = {n: DOMAIN_PALETTE.get(cluster_domain.get(n, '_tech_specific'), DEFAULT_COLOR)
                          for n in G.nodes()}
        active_palette = DOMAIN_PALETTE
        used_keys = {cluster_domain.get(n, '_tech_specific') for n in G.nodes()}
        legend_label_fn = lambda k: ('tech-specific (no domain)' if k == '_tech_specific'
                                       else k.replace('_',' '))
        title_phrase = 'mechanism domain'
    colors = [node_color_map[n] for n in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_size=sizes, node_color=colors,
                            edgecolors='white', linewidths=1, ax=ax, alpha=0.92)
    # Labels
    labels = {}
    # Show labels for top-degree nodes only (else clutter)
    degrees = dict(G.degree())
    top_nodes = sorted(degrees, key=degrees.get, reverse=True)[:60]
    for n in top_nodes:
        nm = cid_to_meta[n]['canonical_name']
        if len(nm) > 40: nm = nm[:38] + '…'
        labels[n] = nm
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=7,
                              ax=ax, alpha=0.9)
    ax.set_title(
        f"Cluster co-occurrence network — edges with co-occurrence ≥ {args.min_cooccur}\n"
        f"({G.number_of_nodes()} clusters, {G.number_of_edges()} edges; "
        f"node colour = {title_phrase}; node size ∝ cluster size)",
        fontsize=11)
    # Legend
    legend_handles = []
    import matplotlib.patches as mpatches
    for k, color in active_palette.items():
        if k in used_keys:
            legend_handles.append(mpatches.Patch(color=color,
                                                   label=legend_label_fn(k)))
    ax.legend(handles=legend_handles, loc='lower right', fontsize=7,
              framealpha=0.9, ncol=1)
    ax.set_axis_off()
    plt.tight_layout()
    png_out = CLOSURE_OUT / PNG_OUT_TEMPLATE.format(tag=args.color_by)
    plt.savefig(png_out, dpi=140)
    print(f"  wrote {png_out}", flush=True)

    # ====== Interactive HTML (vis.js, CDN, self-contained) ======
    nodes_data = []
    for n in G.nodes():
        meta = cid_to_meta[n]
        color = node_color_map[n]
        size_val = 5 + 0.4 * cluster_size.get(n, 1) ** 0.6
        title = meta['canonical_name']
        nodes_data.append({
            'id': n, 'label': meta['canonical_name'][:40],
            'title': title, 'color': color, 'size': size_val,
            'value': cluster_size.get(n, 1),
        })
    edges_data = []
    for u, v in G.edges():
        w = G[u][v]['weight']
        edges_data.append({'from': u, 'to': v, 'value': w,
                            'title': f'{w} shared events'})

    nodes_json = json.dumps(nodes_data, ensure_ascii=False)
    edges_json = json.dumps(edges_data, ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>v2 cluster co-occurrence network</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    body {{ margin: 0; font-family: -apple-system, system-ui, sans-serif; }}
    #network {{ width: 100vw; height: 100vh; background: #fafbfc; }}
    .panel {{ position: fixed; top: 12px; left: 12px; max-width: 320px;
              background: rgba(255,255,255,0.92); padding: 12px 16px;
              border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
              font-size: 13px; line-height: 1.4; }}
    .panel h3 {{ margin: 0 0 8px 0; font-size: 14px; }}
    .legend span {{ display: inline-block; width: 11px; height: 11px;
                    border-radius: 50%; margin-right: 4px; vertical-align: middle; }}
  </style>
</head>
<body>
<div class="panel">
  <h3>Cluster co-occurrence network</h3>
  <div>{G.number_of_nodes()} clusters · {G.number_of_edges()} edges</div>
  <div>Edges = ≥ {args.min_cooccur} shared project events</div>
  <div style="margin-top:8px" class="legend">
    Node colour = {title_phrase}
  </div>
  <div style="margin-top:6px; color:#666">
    Hover for cluster name · scroll to zoom · drag to reposition
  </div>
</div>
<div id="network"></div>
<script>
const nodes = new vis.DataSet({nodes_json});
const edges = new vis.DataSet({edges_json});
const container = document.getElementById('network');
const data = {{ nodes: nodes, edges: edges }};
const options = {{
  nodes: {{ shape: 'dot', font: {{ size: 12 }}, scaling: {{ min: 6, max: 26 }} }},
  edges: {{
    smooth: {{ type: 'continuous' }},
    color: {{ color: 'rgba(40,50,80,0.55)', highlight: 'rgba(20,40,90,0.9)' }},
    scaling: {{ min: 0.7, max: 7 }},
  }},
  physics: {{
    barnesHut: {{ gravitationalConstant: -8000, springLength: 200,
                  springConstant: 0.04, damping: 0.4 }},
    stabilization: {{ iterations: 200 }},
  }},
  interaction: {{ hover: true, tooltipDelay: 100 }},
}};
new vis.Network(container, data, options);
</script>
</body>
</html>"""
    html_out = CLOSURE_OUT / HTML_OUT_TEMPLATE.format(tag=args.color_by)
    html_out.write_text(html)
    print(f"  wrote {html_out}", flush=True)


if __name__ == "__main__":
    main()
