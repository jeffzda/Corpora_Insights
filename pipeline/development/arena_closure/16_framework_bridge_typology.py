#!/usr/bin/env python3
"""For each of the 71 v2 parent archetypes, identify the formal academic
framework that names the mechanism class, then measure invocation density
in (a) raw markdown source and (b) extracted records.

Classification:
  ABSENT          — frame is missing from both source and records (Pareto-grade)
  LLM_AMPLIFIED   — records use the frame ≥2× more than markdown source
                    (extraction model interpolating vocabulary authors didn't use)
  PARITY_LOW      — ≈parity ratio, low absolute density (siloed/specialist usage)
  PARITY_HIGH     — ≈parity ratio, high absolute density (frame in active circulation)
  LLM_STRIPPED    — markdown uses frame ≥2× more than records
                    (extraction model dropping vocabulary the source used)
  NO_FRAMEWORK    — no canonical academic framework exists for this mechanism class
                    (the gap is in the literature, not the field's uptake)

This produces a methodology-paper-grade artefact: the distribution of bridge
types across the parent set, where the v2 substrate is the lens that makes
the question askable in the first place.

Run: python3 corpora/arena/clustering_v2/closure/code/16_framework_bridge_typology.py
Cost: free (no API).
"""
from __future__ import annotations
import json, re, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARENTS = ROOT / 'closure/output/parents_v1.json'
FILTER_INPUT = ROOT / 'output/filter_input.jsonl'
MARKDOWN_DIR = Path('/home/jeffzda/broadlearnings/corpora/arena/markdown')
OUT_JSON = ROOT / 'closure/output/framework_bridge_typology.json'


# Per-parent framework + diagnostic vocabulary patterns.
# `framework=None` means no canonical academic framework worth probing for.
# Patterns must be tight: proper-noun namesakes (Markowitz, Pareto, Dixit),
# technical bigrams (covariance matrix, Lyapunov time, MTBF), or canonical
# acronyms. Single common words ("trade-off", "incentive") are forbidden —
# they would catch operational vocabulary, not framework invocation.
FRAMEWORKS = {
    'p01': (None, None),  # Missing/inaccessible data — no canonical framework
    'p02': ('Metrology / measurement uncertainty (GUM)',
            r'\b(allan\s+variance|measurement\s+uncertainty\s+budget|guide\s+to.{0,5}expression\s+of\s+uncertainty|GUM\s+(uncertainty|standard))\b'),
    'p03': ('Model verification & validation (ASME V&V)',
            r'\b(verification\s+(and|&)\s+validation|V&V\s+(framework|methodology)|model\s+risk\s+(framework|management)|ASME\s+V&V)\b'),
    'p04': ('Predictability theory / Lyapunov / Kalman / signal-to-noise',
            r'\b(lyapunov|predictability\s+(horizon|limit|ceiling)|skill\s+(ceiling|score)|irreducible\s+(uncertainty|variance)|signal[\s\-]to[\s\-]noise|kalman\s+filter|cram[ée]r[\s\-]rao|brier\s+score)\b'),
    'p05': (None, None),  # overlap with p29; skip to avoid double-counting
    'p06': ('Thermodynamic limits (Carnot, Shockley-Queisser, exergy)',
            r'\b(carnot\s+(limit|efficiency|cycle)|shockley[\s\-]queisser|second\s+law\s+of\s+thermodynamics|exergy\s+(analysis|efficiency)|gibbs\s+free\s+energy)\b'),
    'p07': (None, None),  # site/footprint — no canonical academic framework
    'p08': ('Extreme-value statistics / return periods',
            r'\b(weibull\s+(distribution|fit)|return\s+period|extreme\s+value\s+(theory|analysis)|gumbel|generali[sz]ed\s+pareto)\b'),
    'p09': ('Robust control / H-infinity',
            r'\b(robust\s+control|H[\s\-]infinity|H_?∞|μ[\s\-]synthesis|loop[\s\-]shaping)\b'),
    'p10': ('Queueing theory / Erlang',
            r'\b(queueing\s+theory|erlang\s+(B|C|formula)|kendall\s+notation|M/M/[0-9])\b'),
    'p11': ('Control theory (MPC, Lyapunov, Nyquist/Bode)',
            r'\b(model\s+predictive\s+control|MPC\s+(controller|formulation)|nyquist\s+(criterion|stability)|bode\s+(plot|criterion)|lyapunov\s+stability)\b'),
    'p12': ('Real-time scheduling / rate-monotonic',
            r'\b(rate[\s\-]monotonic|earliest\s+deadline\s+first|EDF\s+scheduling|jitter\s+analysis|hard\s+real[\s\-]time)\b'),
    'p13': (None, None),  # interoperability is engineering practice, no clean framework
    'p14': (None, None),  # legacy design — technical debt is informal
    'p15': ('Grid-forming / grid-following inverter theory',
            r'\b(grid[\s\-]forming|grid[\s\-]following|virtual\s+synchronous\s+(machine|generator)|VSM|VSG\s+control|droop\s+control)\b'),
    'p16': ('Technology Readiness Levels / Stokes quadrant',
            r'\b(TRL\s*[1-9]|technology\s+readiness\s+level|valley\s+of\s+death|stokes\s+quadrant|hype\s+cycle)\b'),
    'p17': ('Mixed-effects / hierarchical Bayes / Simpson paradox',
            r'\b(mixed[\s\-]effects?\s+model|hierarchical\s+bayes|simpson.{0,5}paradox|jensen.{0,8}inequality|ecological\s+fallacy)\b'),
    'p18': ('Multi-objective optimisation / Pareto front',
            r'\b(pareto|non[\s\-]dominat|efficient\s+frontier|trade-?off\s+space|NSGA[\s\-]II|multi[\s\-]objective\s+optimi[sz])\b'),
    'p19': ('Portfolio / correlation theory / Markowitz',
            r'\b(markowitz|portfolio\s+(theory|optimi[sz]ation)|jensen.{0,8}inequality|correlation\s+matrix|covariance\s+matrix|systemic\s+risk|variance\s+of\s+(the\s+)?sum|correlated\s+(risks?|failures?)|diversification\s+benefit)\b'),
    'p20': (None, None),  # NPV/IRR is universal — too common to be diagnostic
    'p21': ('Pigou / externalities / missing markets',
            r'\b(pigou|pigouvian|externalit(y|ies)|missing\s+market|incomplete\s+market|coase\s+theorem)\b'),
    'p22': (None, None),  # overlap with p21
    'p23': ('Regulatory sandbox / adaptive regulation',
            r'\b(regulatory\s+sandbox|adaptive\s+regulat|experimentalist\s+governance|safe\s+harbour\s+regulat)\b'),
    'p24': (None, None),  # purely operational
    'p25': ('Real options / Dixit-Pindyck',
            r'\b(real\s+option|dixit|pindyck|option\s+value\s+(of\s+)?(wait|delay|deferral)|irreversible\s+investment|investment\s+under\s+uncertainty)\b'),
    'p26': ('Goodhart / Campbell — metric gaming',
            r"\b(goodhart|campbell.{0,5}law|gaming\s+(the|a)\s+metric|metric\s+gaming|specification\s+gaming|reward\s+hacking)\b"),
    'p27': ('Mechanism design / public goods / Coase',
            r'\b(mechanism\s+design|coase\s+theorem|public\s+goods\s+(provision|problem)|free[\s\-]rider\s+problem|VCG\s+mechanism|nash\s+bargaining)\b'),
    'p28': ('Tragedy of the commons / Ostrom',
            r'\b(tragedy\s+of\s+(the\s+)?commons|ostrom|common[\s\-]pool\s+resource|free[\s\-]rider)\b'),
    'p29': ('Principal-agent / moral hazard / adverse selection',
            r'\b(principal[\s\-]agent|moral\s+hazard|adverse\s+selection|information\s+asymmetry|signall?ing\s+equilibrium|screening\s+contract|residual\s+claimant)\b'),
    'p30': ('Incomplete contracts (Hart-Moore)',
            r'\b(incomplete\s+contracts?|hart[\s\-]moore|residual\s+(rights|control\s+rights)|relational\s+contract)\b'),
    'p31': ('Social licence to operate (SLO)',
            r'\b(social\s+licen[cs]e\s+to\s+operate|SLO\s+(framework|theory)|procedural\s+justice\s+(framework|theory))\b'),
    'p32': ('Diffusion of innovations (Rogers)',
            r'\b(diffusion\s+of\s+innovat|rogers.{0,5}adoption|adoption\s+S[\s\-]curve|bass\s+diffusion\s+model|early\s+adopter\s+chasm|crossing\s+the\s+chasm)\b'),
    'p33': ('Behavioural economics (prospect theory, status-quo bias, hyperbolic discounting)',
            r'\b(prospect\s+theory|status[\s\-]quo\s+bias|hyperbolic\s+discount|loss\s+aversion|kahneman|tversky|nudge\s+(theory|economics)|endowment\s+effect)\b'),
    'p34': (None, None),  # workforce — HR practice, no canonical academic framework
    'p35': ('Change management (Kotter, Lewin, ADKAR)',
            r'\b(kotter|lewin.{0,5}change|ADKAR|organi[sz]ational\s+maturity\s+(model|framework)|CMMI)\b'),
    'p36': (None, None),  # PM practice
    'p37': (None, None),  # operational
    'p38': (None, None),  # operational
    'p39': ('Black swan / antifragility (Taleb)',
            r'\b(black\s+swan|taleb|antifragil|fat[\s\-]tailed\s+risk|grey\s+rhino)\b'),
    'p40': ('Path dependence / lock-in (Arthur)',
            r'\b(path\s+dependen|increasing\s+returns\s+to\s+adoption|arthur.{0,5}lock[\s\-]in|switching\s+cost\s+(model|framework))\b'),
    'p41': (None, None),  # standards/cert — engineering practice
    'p42': (None, None),  # compliance — operational
    'p43': ('Capital structure (Modigliani-Miller) / risk transfer',
            r'\b(modigliani[\s\-]miller|capital\s+structure\s+irrelevance|insurance\s+theory|risk\s+transfer\s+(framework|instrument))\b'),
    'p44': ('Two-sided markets / coordination games / critical mass',
            r'\b(two[\s\-]sided\s+market|rochet|tirole|coordination\s+(game|failure)|equilibrium\s+selection|critical\s+mass|network\s+externalit|indirect\s+network\s+effect|positive\s+feedback\s+loop)\b'),
    'p45': ('Industrial organisation / market concentration (HHI)',
            r'\b(herfindahl|HHI\s+(index|measure)|market\s+concentration\s+(ratio|index)|antitrust\s+(framework|analysis))\b'),
    'p46': ('Path dependence / Arthurian lock-in / increasing returns',
            r'\b(path\s+dependen|increasing\s+returns\s+to\s+adoption|arthur.{0,5}(lock|increasing)|installed\s+base\s+effect)\b'),
    'p47': (None, None),  # supply-demand mismatch — operational
    'p48': ('Stochastic optimal control / capacity firming',
            r'\b(stochastic\s+optimal\s+control|capacity\s+firming\s+(framework|methodology)|unit\s+commitment\s+(formulation|model)|economic\s+dispatch\s+formulation)\b'),
    'p49': ('Optimal power flow / N-1 security',
            r'\b(optimal\s+power\s+flow|OPF\s+(formulation|solution)|N[\s\-]1\s+(criterion|contingency)|hosting\s+capacity\s+analysis)\b'),
    'p50': ('Statistical process control / Taguchi loss function',
            r'\b(statistical\s+process\s+control|SPC\s+(chart|framework)|taguchi\s+(loss|method)|six\s+sigma\s+(methodology|DMAIC)|process\s+capability)\b'),
    'p51': (None, None),  # process design — engineering practice
    'p52': ('Process capability / Six Sigma',
            r'\b(C[\s]?p\s*[k]?\s+(index|≥|>=)|process\s+capability\s+(index|study)|six\s+sigma|DMAIC|defects\s+per\s+million|DPMO)\b'),
    'p53': ('Reliability engineering — Weibull life / accelerated life testing',
            r'\b(weibull.{0,15}distribut|accelerated\s+life\s+test|bathtub\s+curve|wear[\s\-]out\s+(failure|phase)|reliability\s+function|hazard\s+rate)\b'),
    'p54': ('HAZOP / LOPA / fault tree',
            r'\b(HAZOP|LOPA|layer\s+of\s+protection\s+analysis|fault\s+tree\s+analysis|FTA\s+(framework|study))\b'),
    'p55': ('STRIDE / OWASP / threat modelling',
            r'\b(STRIDE|OWASP|threat\s+modell?ing|attack\s+surface\s+(analysis|reduction)|MITRE\s+ATT&CK)\b'),
    'p56': (None, None),  # software practice
    'p57': ('Quasi-experimental design / Campbell-Stanley validity',
            r'\b(external\s+validity|internal\s+validity|generali[sz]ability\s+(of|theory)|quasi[\s\-]experiment|campbell[\s\-]stanley|construct\s+validity)\b'),
    'p58': (None, None),  # ground-truth absence is meta-methodology, no clean framework
    'p59': (None, None),  # data engineering practice
    'p60': (None, None),  # KM — informal
    'p61': (None, None),  # comm — too broad
    'p62': ('Specification gaming / Goodhart / reward hacking',
            r'\b(specification\s+gaming|goodhart|reward\s+hacking|metric\s+gaming|proxy\s+gaming|optimi[sz]ation\s+pressure)\b'),
    'p63': (None, None),  # overlaps p31
    'p64': ('Round-trip efficiency / exergy analysis',
            r'\b(round[\s\-]trip\s+efficien|exergy\s+(analysis|efficiency)|second[\s\-]law\s+efficiency|parasitic\s+(load|consumption)\s+analysis)\b'),
    'p65': ('Reliability theory / Perrow normal-accident',
            r'\b(perrow|normal\s+accident|interactive\s+complexity|tight\s+coupling|MTBF|MTTR|MTTF|mean[\s\-]time[\s\-]between[\s\-]failure|fault\s+tree|reliability\s+block\s+diagram|FMEA|failure\s+mode\s+and\s+effects)\b'),
    'p66': ('Modular design / design structure matrix',
            r'\b(design\s+structure\s+matrix|DSM\s+(analysis|framework)|modular\s+(design|architecture)\s+(theory|framework)|modularity\s+index)\b'),
    'p67': ('Experience curve / Wright law / production function',
            r'\b(experience\s+curve|wright.{0,5}law|learning\s+(curve|rate)\s+coefficient|production\s+function|diminishing\s+marginal\s+(return|productivity))\b'),
    'p68': ('Life-cycle assessment / LCOE methodology',
            r'\b(life[\s\-]cycle\s+assessment\s+(methodology|framework)|LCA\s+(methodology|framework)|LCOE\s+(formula|methodology|definition)|levelised\s+cost\s+of\s+energy\s+formula)\b'),
    'p69': ('Robust optimisation / minimax / Wald criterion',
            r'\b(minimax|robust\s+optimi[sz]ation|maximin|wald.{0,5}criterion|worst[\s\-]case\s+design\s+(framework|approach))\b'),
    'p70': (None, None),  # data accuracy — operational
    'p71': ('Energy justice / just transition',
            r'\b(energy\s+justice|distributional\s+impact\s+(analysis|assessment)|just\s+transition\s+(framework|principle)|procedural\s+justice)\b'),
}


def classify(rec_density: float, md_density: float) -> tuple[str, float]:
    """Return (typology, ratio) where ratio = rec_density/md_density.

    Thresholds:
      ABSENT          : both densities < 0.02 / Mchar
      LLM_AMPLIFIED   : ratio >= 2.0  (records over-invoke)
      LLM_STRIPPED    : ratio <= 0.5  (records under-invoke)
      PARITY_LOW      : ratio in [0.5, 2.0], md_density < 0.5
      PARITY_HIGH     : ratio in [0.5, 2.0], md_density >= 0.5
    """
    if rec_density < 0.02 and md_density < 0.02:
        return 'ABSENT', float('nan')
    if md_density < 0.001:  # records hit, source has none
        return 'LLM_AMPLIFIED', float('inf')
    ratio = rec_density / md_density
    if ratio >= 2.0:
        return 'LLM_AMPLIFIED', ratio
    if ratio <= 0.5:
        return 'LLM_STRIPPED', ratio
    if md_density < 0.5:
        return 'PARITY_LOW', ratio
    return 'PARITY_HIGH', ratio


def main():
    print("Loading parents catalogue...", flush=True)
    parents = json.load(PARENTS.open())['parents']
    p_meta = {p['parent_id']: p for p in parents}
    print(f"  {len(parents)} parents", flush=True)

    print("Loading filter_input records...", flush=True)
    rec_text_total = 0
    rec_blob = []
    for line in open(FILTER_INPUT):
        r = json.loads(line)
        t = ' '.join([r.get('narrative','') or '', r.get('lesson','') or '', r.get('evidence','') or ''])
        rec_text_total += len(t)
        rec_blob.append(t)
    rec_blob = '\n'.join(rec_blob)
    print(f"  {len(rec_blob):,} chars ({rec_text_total/1e6:.1f}M chars of record narrative)", flush=True)

    print("Loading markdown corpus...", flush=True)
    md_files = sorted(MARKDOWN_DIR.glob('*.md'))
    md_blob_parts = []
    for f in md_files:
        try:
            md_blob_parts.append(f.read_text(errors='ignore'))
        except Exception:
            pass
    md_blob = '\n'.join(md_blob_parts)
    md_total = len(md_blob)
    print(f"  {len(md_files):,} markdown files, {md_total/1e6:.1f}M chars", flush=True)

    rec_Mc = len(rec_blob) / 1e6
    md_Mc = md_total / 1e6

    print(f"\nRunning {sum(1 for v in FRAMEWORKS.values() if v[0])} pattern probes "
          f"and skipping {sum(1 for v in FRAMEWORKS.values() if not v[0])} no-framework parents...",
          flush=True)

    results = []
    t0 = time.time()
    for i, (pid, (frame, pat_str)) in enumerate(FRAMEWORKS.items()):
        meta = p_meta.get(pid, {})
        name = meta.get('name', '?')
        n_clusters = len(meta.get('exemplar_cluster_ids', []))  # rough scale
        if not frame:
            results.append({
                'parent_id': pid,
                'parent_name': name,
                'framework': None,
                'pattern': None,
                'rec_matches': None,
                'md_matches': None,
                'rec_density_per_Mchar': None,
                'md_density_per_Mchar': None,
                'ratio_rec_over_md': None,
                'typology': 'NO_FRAMEWORK',
            })
            continue
        pat = re.compile(pat_str, re.IGNORECASE)
        rec_n = len(pat.findall(rec_blob))
        md_n = len(pat.findall(md_blob))
        rec_d = rec_n / rec_Mc
        md_d = md_n / md_Mc
        typ, ratio = classify(rec_d, md_d)
        results.append({
            'parent_id': pid,
            'parent_name': name,
            'framework': frame,
            'pattern': pat_str,
            'rec_matches': rec_n,
            'md_matches': md_n,
            'rec_density_per_Mchar': round(rec_d, 3),
            'md_density_per_Mchar': round(md_d, 3),
            'ratio_rec_over_md': (None if ratio != ratio else  # NaN check
                                   ('inf' if ratio == float('inf') else round(ratio, 2))),
            'typology': typ,
        })
        if (i+1) % 10 == 0:
            print(f"  scanned {i+1}/71 parents... ({time.time()-t0:.0f}s)", flush=True)

    # === Summary ===
    print(f"\n{'='*100}")
    print("PER-PARENT TYPOLOGY (sorted by typology then by markdown density desc)")
    print('='*100)
    type_order = ['ABSENT', 'LLM_AMPLIFIED', 'LLM_STRIPPED', 'PARITY_LOW', 'PARITY_HIGH', 'NO_FRAMEWORK']
    results_sorted = sorted(results, key=lambda r: (
        type_order.index(r['typology']),
        -(r['md_density_per_Mchar'] or 0),
    ))
    print(f"\n{'pid':4} {'type':14} {'rec/Mc':>8} {'md/Mc':>8} {'ratio':>7} | parent / framework")
    print('-' * 100)
    for r in results_sorted:
        ratio = r['ratio_rec_over_md']
        ratio_s = '—' if ratio is None else (str(ratio))
        rd = r['rec_density_per_Mchar']
        md = r['md_density_per_Mchar']
        rd_s = '—' if rd is None else f"{rd:.2f}"
        md_s = '—' if md is None else f"{md:.2f}"
        print(f"{r['parent_id']:4} {r['typology']:14} {rd_s:>8} {md_s:>8} {ratio_s:>7} | {r['parent_name'][:55]}")
        if r['framework']:
            print(f"{'':4} {'':14} {'':8} {'':8} {'':7} | ↳ {r['framework'][:80]}")

    # === Distribution ===
    from collections import Counter
    dist = Counter(r['typology'] for r in results)
    print(f"\n{'='*60}")
    print("TYPOLOGY DISTRIBUTION (across 71 parents)")
    print('='*60)
    for t in type_order:
        n = dist.get(t, 0)
        pct = n/71*100
        print(f"  {t:14} {n:>3}  ({pct:.0f}%)")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({
        'corpus_chars': {'records': len(rec_blob), 'markdown': md_total},
        'distribution': dict(dist),
        'results': results,
    }, indent=2))
    print(f"\nWrote {OUT_JSON}", flush=True)


if __name__ == '__main__':
    main()
