"""
brazil-election-montecarlo — Standalone Second Round Simulation (v2.7)
=======================================================================
Dedicated simulation for the presidential runoff after the two finalists
are known from the first round result.

Rationale:
    Once the finalists are determined, running 40,000 first-round simulations
    to reach the second round is unnecessary. This script simulates the runoff
    directly with its own poll data, capturing second-round dynamics that differ
    from first-round surveys (smaller undecided pool, completed vote transfer,
    potential rejection shifts).

Usage:
    python src/simulation_2turno.py

CSV format (data/pesquisas_2turno.csv):
    candidato,intencao_voto_pct,rejeicao_pct,desvio_padrao_pct,instituto,data
    Lula,54.0,42.0,2.0,Datafolha,2026-10-08
    Lula,53.0,43.0,2.0,Quaest,2026-10-09
    Flávio Bolsonaro,46.0,48.0,2.0,Datafolha,2026-10-08
    Flávio Bolsonaro,47.0,47.0,2.0,Quaest,2026-10-09

    - Exactly two candidates expected (no "Outros" or "Brancos/Nulos" rows).
    - intencao_voto_pct values need not sum to 100; the gap is treated as
      residual (undecided + blank/null) and redistributed before simulation.
    - Aggregation, temporal weighting, and outlier detection are inherited
      from simulation_v2 via direct import.

Outputs:
    outputs/resultados_2turno_standalone.csv
    outputs/simulacao_2turno.png

License: MIT
"""

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, FancyBboxPatch
import matplotlib.gridspec as gridspec
from pathlib import Path
from datetime import date

# Allow running from project root or from src/
sys.path.insert(0, str(Path(__file__).parent))

from simulation_v2 import (
    agregar_pesquisas_candidato,
    calcular_peso_temporal,
    detectar_outliers,
    gerar_cores,
    _hex_lighten,
    ELEITORADO,
    ABSTENCAO_2T_MU,
    ABSTENCAO_2T_SIGMA,
)

# ─── CONFIG ───────────────────────────────────────────────────────────────────

OUTPUT_DIR    = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

DATA_ELEICAO  = date(2026, 10, 4)
DATA_2T       = date(2026, 10, 25)   # Historical pattern: runoff ~3 weeks after 1st round
N_SIM         = 40_000
DESVIO_BASE   = 2.0                  # Overridden by aggregated value from CSV

np.random.seed(42)


# ─── DATA LOADING ─────────────────────────────────────────────────────────────

def carregar_pesquisas_2t(csv_path=None):
    """
    Loads and aggregates second-round poll data.

    Reuses agregar_pesquisas_candidato() from simulation_v2 for temporal
    weighting and outlier detection. Expects exactly two candidates.

    Args:
        csv_path: Path to CSV (str or Path). Defaults to data/pesquisas_2turno.csv.

    Returns:
        tuple: (cand_a, cand_b, voto_a, voto_b, rej_a, rej_b, desvio, residual)
            - cand_a / cand_b: Candidate names (sorted by descending aggregated vote)
            - voto_a / voto_b: Aggregated vote intentions (%)
            - rej_a / rej_b: Aggregated rejection rates (%)
            - desvio: Combined standard deviation (%)
            - residual: 100 - (voto_a + voto_b), represents undecided + blank/null

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If the CSV does not contain exactly two distinct candidates.
    """
    csv_path = Path(csv_path) if csv_path else Path("data/pesquisas_2turno.csv")

    if not csv_path.exists():
        raise FileNotFoundError(
            f"File not found: {csv_path}\n"
            "Create data/pesquisas_2turno.csv with second-round poll data.\n"
            "See ROADMAP.md (Issue #9) for the expected CSV format."
        )

    df = pd.read_csv(csv_path)

    required = {"candidato", "intencao_voto_pct", "desvio_padrao_pct"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date

    candidatos_unicos = df["candidato"].unique()
    if len(candidatos_unicos) != 2:
        raise ValueError(
            f"Expected exactly 2 candidates; found {len(candidatos_unicos)}: "
            f"{list(candidatos_unicos)}\n"
            "Remove 'Outros' and 'Brancos/Nulos' rows — residual is computed automatically."
        )

    data_ref = date.today()
    resultados = {}

    print("\n" + "=" * 70)
    print("  SECOND ROUND POLL AGGREGATION")
    print("=" * 70)

    for cand in candidatos_unicos:
        df_cand = df[df["candidato"] == cand].copy()
        voto, rej, desv, info = agregar_pesquisas_candidato(df_cand, data_ref)

        resultados[cand] = {
            "voto": voto,
            "rej": rej,
            "desv": desv,
            "info": info,
        }

        n = info["n_pesquisas"]
        print(f"\nCandidate: {cand}")
        print(f"   Polls aggregated: {n}")
        print(f"   Valid polls: {info['n_validas']}")
        if "institutos" in info and n > 1:
            print(f"   Sources: {', '.join(info['institutos'])}")
        print(f"   Aggregated vote: {voto:.2f}%")
        if rej > 0:
            print(f"   Aggregated rejection: {rej:.2f}%")
        if n > 1:
            print(f"   Base std dev: {info['desvio_medio']:.2f}%")
            print(f"   Inter-institute std dev: {info['desvio_entre']:.2f}%")
        print(f"   Combined std dev: {desv:.2f}%")
        if info.get("outliers"):
            print(f"   WARNING: {len(info['outliers'])} outlier(s) excluded:")
            for o in info["outliers"]:
                print(f"      - {o['instituto']}: {o['valor']:.2f}%")

    print("=" * 70)

    # Sort candidates by descending vote share (leader first)
    cands_sorted = sorted(resultados.keys(), key=lambda c: resultados[c]["voto"], reverse=True)
    cand_a, cand_b = cands_sorted

    voto_a = resultados[cand_a]["voto"]
    voto_b = resultados[cand_b]["voto"]
    rej_a  = resultados[cand_a]["rej"]
    rej_b  = resultados[cand_b]["rej"]
    desvio = float(np.mean([resultados[c]["desv"] for c in candidatos_unicos]))

    # Residual: undecided + blank/null implicit in the poll gap
    residual = max(0.0, 100.0 - voto_a - voto_b)

    print(f"\nResidual (undecided + blank/null): {residual:.2f}%")
    print(f"Combined std dev: {desvio:.2f}%")
    print(f"Electorate: {ELEITORADO:,}")

    return cand_a, cand_b, voto_a, voto_b, rej_a, rej_b, desvio, residual


# ─── RESIDUAL REDISTRIBUTION ──────────────────────────────────────────────────

def redistribuir_residual(voto_a, voto_b, rej_a, rej_b, residual, blank_fraction=0.20):
    """
    Distributes the residual (undecided + blank/null) between the two finalists
    and a blank/null pool proportionally to each candidate's available electoral space.

    In second-round polls, intencao_voto_pct values frequently sum to less than 100%
    because a fraction of respondents are undecided or will vote blank/null.
    This function redistributes the residual before Dirichlet parameterization.

    Args:
        voto_a: Aggregated vote intention for candidate A (%)
        voto_b: Aggregated vote intention for candidate B (%)
        rej_a: Rejection rate for candidate A (%)
        rej_b: Rejection rate for candidate B (%)
        residual: Undecided + blank/null gap (100 - voto_a - voto_b) (%)
        blank_fraction: Fraction of residual allocated to blank/null (default: 0.20)

    Returns:
        tuple: (voto_a_adj, voto_b_adj, residual_final)
            - voto_a_adj / voto_b_adj: Adjusted vote intentions after redistribution
            - residual_final: Final blank/null proportion for Dirichlet third category

    Formula:
        weight_i = vote_share_i * max(100 - rejection_i, 0) / 100
        gain_i = (weight_i / sum(weights)) * residual * (1 - blank_fraction)
    """
    if residual <= 0:
        return voto_a, voto_b, 0.0

    espaco_a = max(100.0 - rej_a, 0.0) / 100.0
    espaco_b = max(100.0 - rej_b, 0.0) / 100.0

    peso_a = voto_a * espaco_a
    peso_b = voto_b * espaco_b
    total_peso = peso_a + peso_b

    if total_peso == 0:
        # Fallback: equal split if both candidates have 100% rejection
        prop_a = prop_b = 0.5
    else:
        prop_a = peso_a / total_peso
        prop_b = peso_b / total_peso

    redistribuivel = residual * (1.0 - blank_fraction)
    residual_final = residual * blank_fraction

    voto_a_adj = voto_a + prop_a * redistribuivel
    voto_b_adj = voto_b + prop_b * redistribuivel

    print(f"\n   Residual redistribution (blank_fraction={blank_fraction:.0%}):")
    print(f"   Redistributable to candidates: {redistribuivel:.2f}%")
    print(f"   Allocated to blank/null: {residual_final:.2f}%")
    print(f"   Candidate A gain: +{prop_a * redistribuivel:.2f}pp "
          f"({voto_a:.2f}% → {voto_a_adj:.2f}%)")
    print(f"   Candidate B gain: +{prop_b * redistribuivel:.2f}pp "
          f"({voto_b:.2f}% → {voto_b_adj:.2f}%)")

    return voto_a_adj, voto_b_adj, residual_final


# ─── SIMULATION ───────────────────────────────────────────────────────────────

def simular(cand_a, cand_b, voto_a, voto_b, rej_a, rej_b, desvio, residual):
    """
    Runs 40,000 second-round simulations using a 3-category Dirichlet.

    The three Dirichlet categories are:
        [candidate A votes, candidate B votes, blank/null votes]

    Rejection ceilings are applied to each finalist. The winner is determined
    by the vote share among [A, B] only (blank/null votes excluded from the
    valid vote denominator, consistent with Brazilian electoral law).

    Absolute vote projections use stochastic abstention sampled from
    Normal(ABSTENCAO_2T_MU, ABSTENCAO_2T_SIGMA) per simulation.

    Args:
        cand_a: Name of candidate A (leader by aggregated vote)
        cand_b: Name of candidate B (trailer)
        voto_a: Adjusted vote intention for A after residual redistribution (%)
        voto_b: Adjusted vote intention for B after residual redistribution (%)
        rej_a: Rejection rate for A (%)
        rej_b: Rejection rate for B (%)
        desvio: Combined standard deviation for Dirichlet concentration factor
        residual: Final blank/null proportion (Dirichlet third category) (%)

    Returns:
        pd.DataFrame: One row per simulation with columns:
            voto_a, voto_b, vencedor, diferenca,
            abstencao_pct, votos_validos,
            votos_a_abs, votos_b_abs, margem_votos
    """
    print(f"\n[SIM] Running {N_SIM:,} second-round simulations...")
    print(f"   {cand_a}: {voto_a:.2f}%  (rejection: {rej_a:.1f}%,  ceiling: {100-rej_a:.1f}%)")
    print(f"   {cand_b}: {voto_b:.2f}%  (rejection: {rej_b:.1f}%,  ceiling: {100-rej_b:.1f}%)")
    print(f"   Blank/null pool: {residual:.2f}%")

    # Ensure all Dirichlet alphas are positive (required by numpy)
    blank_pool = max(residual, 0.1)
    fator = max(100.0 / desvio, 1.0)
    alphas = np.array([voto_a, voto_b, blank_pool]) * fator

    proporcoes = np.random.dirichlet(alphas, size=N_SIM)  # (N_SIM, 3)

    # Apply electoral ceiling before computing valid vote shares
    teto_a = max(100.0 - rej_a, 1.0)
    teto_b = max(100.0 - rej_b, 1.0)

    p_a_raw = proporcoes[:, 0] * 100
    p_b_raw = proporcoes[:, 1] * 100

    p_a_raw = np.minimum(p_a_raw, teto_a)
    p_b_raw = np.minimum(p_b_raw, teto_b)

    # Valid vote share excludes blank/null (Brazilian runoff rule)
    total_valido = p_a_raw + p_b_raw
    voto_a_sim = p_a_raw / total_valido * 100
    voto_b_sim = p_b_raw / total_valido * 100

    diferenca = np.abs(voto_a_sim - voto_b_sim)
    vencedor  = np.where(voto_a_sim > voto_b_sim, cand_a, cand_b)

    # Absolute vote projections
    abstencao_sim = np.random.normal(ABSTENCAO_2T_MU, ABSTENCAO_2T_SIGMA, N_SIM).clip(0.05, 0.45)
    votos_validos  = (ELEITORADO * (1.0 - abstencao_sim)).astype(np.int64)
    votos_a_abs    = (votos_validos * voto_a_sim / 100).astype(np.int64)
    votos_b_abs    = (votos_validos * voto_b_sim / 100).astype(np.int64)

    df = pd.DataFrame({
        "voto_a":       voto_a_sim,
        "voto_b":       voto_b_sim,
        "vencedor":     vencedor,
        "diferenca":    diferenca,
        "abstencao_pct": abstencao_sim * 100,
        "votos_validos": votos_validos,
        "votos_a_abs":  votos_a_abs,
        "votos_b_abs":  votos_b_abs,
        "margem_votos": np.abs(votos_a_abs - votos_b_abs),
    })

    out = OUTPUT_DIR / "resultados_2turno_standalone.csv"
    df.to_csv(out, index=False)
    print(f"   Results saved: {out}")
    print("   OK")
    return df


# ─── REPORT ───────────────────────────────────────────────────────────────────

def relatorio(df, cand_a, cand_b, rej_a, rej_b):
    """Prints a structured summary of second-round simulation results."""
    sep = "=" * 60
    print(f"\n{sep}")
    print("  SECOND ROUND STANDALONE REPORT [v2.7]")
    print(sep)

    n = len(df)
    prob_a = (df["vencedor"] == cand_a).mean() * 100
    prob_b = (df["vencedor"] == cand_b).mean() * 100

    print(f"\nVictory probability:")
    print(f"  {cand_a:26s} {prob_a:.2f}%")
    print(f"  {cand_b:26s} {prob_b:.2f}%")

    print(f"\nVote share distribution (valid votes, IC 90%):")
    for label, col, rej in [(cand_a, "voto_a", rej_a), (cand_b, "voto_b", rej_b)]:
        mean_v = df[col].mean()
        ci_lo  = df[col].quantile(0.05)
        ci_hi  = df[col].quantile(0.95)
        print(f"  {label:26s} {mean_v:.2f}%  90% CI: [{ci_lo:.2f}% – {ci_hi:.2f}%]"
              f"  (rej: {rej:.1f}%)")

    print(f"\nMargin of victory:")
    print(f"  Close race (<3pp):      {(df['diferenca'] < 3).mean() * 100:.1f}% of scenarios")
    print(f"  Photo-finish (<1pp):    {(df['diferenca'] < 1).mean() * 100:.1f}% of scenarios")
    print(f"  Comfortable (>5pp):     {(df['diferenca'] >= 5).mean() * 100:.1f}% of scenarios")
    print(f"  Median margin:          {df['diferenca'].median():.2f}pp")

    p5m, p50m, p95m = df["margem_votos"].quantile([0.05, 0.50, 0.95])
    med_abs = df["abstencao_pct"].median()
    med_turn = df["votos_validos"].median()

    print(f"\nAbsolute vote projections:")
    print(f"  Electorate:             {ELEITORADO:>15,}")
    print(f"  Median turnout:         {int(med_turn):>15,}  (abstention: {med_abs:.1f}%)")
    for label, col in [(cand_a, "votos_a_abs"), (cand_b, "votos_b_abs")]:
        p5, p50, p95 = df[col].quantile([0.05, 0.50, 0.95])
        print(f"  {label:26s} {int(p50):>10,} votes  90% CI: [{int(p5):,} – {int(p95):,}]")
    print(f"  Median absolute margin: {int(p50m):>10,} votes  90% CI: [{int(p5m):,} – {int(p95m):,}]")

    print(sep)
    return prob_a, prob_b


# ─── VISUALIZATIONS ───────────────────────────────────────────────────────────

def graficos(df, cand_a, cand_b, rej_a, rej_b, prob_a, prob_b):
    """
    Generates a three-panel visualization for the standalone second-round simulation.

    Layout:
        Left:   Semicircle showing outcome distribution by margin category.
        Top right:  Overlapping vote share distributions for each candidate.
        Bottom right: Absolute margin distribution (millions of votes).
    """
    print("\n[VIZ] Generating visualization...")

    BG = "#F7F7F7"
    plt.rcParams.update({"axes.facecolor": BG, "figure.facecolor": BG})

    fig = plt.figure(figsize=(18, 11), facecolor=BG)
    gs  = gridspec.GridSpec(
        2, 2, figure=fig,
        width_ratios=[1.35, 1], height_ratios=[1, 1],
        hspace=0.42, wspace=0.10,
        left=0.03, right=0.97, top=0.87, bottom=0.06,
    )
    ax_semi = fig.add_subplot(gs[:, 0])
    ax_dist = fig.add_subplot(gs[0, 1])
    ax_abs  = fig.add_subplot(gs[1, 1])

    cores = gerar_cores(2)
    cor_a, cor_b = cores[0], cores[1]

    lider = cand_a if prob_a >= prob_b else cand_b
    vice  = cand_b if prob_a >= prob_b else cand_a
    prob_lider = max(prob_a, prob_b)
    prob_vice  = min(prob_a, prob_b)
    cor_lider  = cor_a if prob_a >= prob_b else cor_b
    cor_vice   = cor_b if prob_a >= prob_b else cor_a

    # ── Segment computation ─────────────────────────────────────────────────────
    n = len(df)
    mask_l = df["vencedor"] == lider
    mask_v = df["vencedor"] == vice

    def _pct(mask):
        return mask.sum() / n * 100

    seg = {
        "lider_confort": _pct(mask_l & (df["diferenca"] >= 5)),
        "lider_close":   _pct(mask_l & df["diferenca"].between(1, 5)),
        "lider_photo":   _pct(mask_l & (df["diferenca"] < 1)),
        "vice_photo":    _pct(mask_v & (df["diferenca"] < 1)),
        "vice_close":    _pct(mask_v & df["diferenca"].between(1, 5)),
        "vice_confort":  _pct(mask_v & (df["diferenca"] >= 5)),
    }
    pct_apertada = (df["diferenca"] < 3).mean() * 100

    # ── PANEL 1: Semicircle ─────────────────────────────────────────────────────
    ax_semi.set_aspect("equal")
    ax_semi.set_xlim(-1.50, 1.50)
    ax_semi.set_ylim(-0.54, 1.50)
    ax_semi.axis("off")

    R_OUT, R_IN = 1.0, 0.50
    center = (0.0, 0.0)

    colors_seq = [
        _hex_lighten(cor_lider, 0.00),
        _hex_lighten(cor_lider, 0.38),
        _hex_lighten(cor_lider, 0.65),
        _hex_lighten(cor_vice,  0.65),
        _hex_lighten(cor_vice,  0.38),
        _hex_lighten(cor_vice,  0.00),
    ]
    seg_values = list(seg.values())
    total_seg  = sum(seg_values) or 100.0
    angles     = [v / total_seg * 180.0 for v in seg_values]

    current  = 180.0
    arc_mids = []
    for angle, color in zip(angles, colors_seq):
        theta2, theta1 = current, current - angle
        arc_mids.append((theta1 + theta2) / 2.0)
        if angle >= 0.3:
            ax_semi.add_patch(Wedge(
                center, R_OUT, theta1, theta2,
                width=R_OUT - R_IN,
                facecolor=color, edgecolor=BG, lw=3.0, zorder=3,
            ))
        current -= angle

    boundary_deg = 180.0 - (prob_lider / 100.0 * 180.0)
    bx = np.cos(np.radians(boundary_deg))
    by = np.sin(np.radians(boundary_deg))
    ax_semi.plot(
        [center[0] + R_IN * bx, center[0] + R_OUT * bx],
        [center[1] + R_IN * by, center[1] + R_OUT * by],
        color=BG, lw=4.5, zorder=5,
    )

    ax_semi.text(0,  0.14, f"{prob_lider:.1f}%",
                 ha="center", va="center", fontsize=32, fontweight="bold",
                 color=cor_lider, zorder=6)
    ax_semi.text(0, -0.08, f"{prob_vice:.1f}%",
                 ha="center", va="center", fontsize=20,
                 color=cor_vice, zorder=6)
    ax_semi.text(0, -0.24,
                 f"Corrida apertada (<3pp): {pct_apertada:.1f}%",
                 ha="center", va="center", fontsize=8.5, color="#777777", zorder=6)

    Y_CEIL = 1.08
    outer_labels = [
        (0, f"Folgado\n{seg['lider_confort']:.1f}%",  cor_lider,                    4.0),
        (1, f"Apertado\n{seg['lider_close']:.1f}%",   _hex_lighten(cor_lider, 0.2), 6.0),
        (2, f"<1pp\n{seg['lider_photo']:.1f}%",        _hex_lighten(cor_lider, 0.5), 2.0),
        (3, f"<1pp\n{seg['vice_photo']:.1f}%",         _hex_lighten(cor_vice,  0.5), 2.0),
        (4, f"Apertado\n{seg['vice_close']:.1f}%",    _hex_lighten(cor_vice,  0.2), 6.0),
        (5, f"Folgado\n{seg['vice_confort']:.1f}%",   cor_vice,                     4.0),
    ]
    for idx_seg, text, col, min_angle in outer_labels:
        if angles[idx_seg] < min_angle:
            continue
        deg = arc_mids[idx_seg]
        rad = np.radians(deg)
        r_label = R_OUT + (0.20 if 30 < deg < 150 else 0.14)
        lx = r_label * np.cos(rad)
        ly = r_label * np.sin(rad)
        if ly > Y_CEIL:
            ly = Y_CEIL
            lx_abs = np.sqrt(max(r_label ** 2 - ly ** 2, 0.01))
            lx = -lx_abs if deg > 90 else lx_abs
        ha = "right" if deg > 90 else "left"
        ax_semi.text(lx, ly, text, ha=ha, va="center",
                     fontsize=8.0, color=col, fontweight="bold")

    w_box, h_box = 1.10, 0.26
    for x0, cand_name, cor, prob in [
        (-1.44, lider, cor_lider, prob_lider),
        (0.34,  vice,  cor_vice,  prob_vice),
    ]:
        ax_semi.add_patch(FancyBboxPatch(
            (x0, -0.51), w_box, h_box,
            boxstyle="round,pad=0.03",
            facecolor=cor, edgecolor="none", alpha=0.12, zorder=2,
        ))
        ax_semi.text(x0 + w_box / 2, -0.51 + h_box * 0.72,
                     cand_name, ha="center", va="center",
                     fontsize=10.5, fontweight="bold", color=cor)
        ax_semi.text(x0 + w_box / 2, -0.51 + h_box * 0.22,
                     f"Vitória: {prob:.1f}%",
                     ha="center", va="center", fontsize=9, color=cor)

    ax_semi.text(0, 1.20, "2º TURNO — CONFRONTO DIRETO",
                 ha="center", va="center", fontsize=13,
                 color="#333333", fontweight="bold")

    # ── PANEL 2: Vote share distributions ──────────────────────────────────────
    for spine in ax_dist.spines.values():
        spine.set_visible(False)

    bins = np.linspace(30, 70, 80)
    for col, cand, cor in [("voto_a", cand_a, cor_a), ("voto_b", cand_b, cor_b)]:
        ax_dist.hist(df[col], bins=bins, color=cor, alpha=0.55,
                     edgecolor="none", label=cand)
        mean_v = df[col].mean()
        ax_dist.axvline(mean_v, color=cor, lw=2.0, ls="--", alpha=0.85)
        ax_dist.text(mean_v, ax_dist.get_ylim()[1] * 0.02,
                     f" {mean_v:.1f}%", color=cor, fontsize=9,
                     fontweight="bold", va="bottom")

    ax_dist.axvline(50, color="#888888", lw=1.2, ls=":", alpha=0.6)
    ax_dist.set_xlabel("Votos válidos (%)", fontsize=9, color="#666666", labelpad=6)
    ax_dist.set_ylabel("Frequência", fontsize=9, color="#666666")
    ax_dist.set_title(
        "Distribuição de votos válidos\n40.000 simulações",
        fontsize=11, fontweight="bold", pad=12, loc="left", color="#222222",
    )
    ax_dist.legend(fontsize=9, frameon=False)
    ax_dist.grid(axis="y", alpha=0.18, color="#aaaaaa")
    ax_dist.set_axisbelow(True)
    ax_dist.tick_params(bottom=False)

    # ── PANEL 3: Absolute margin distribution ───────────────────────────────────
    for spine in ax_abs.spines.values():
        spine.set_visible(False)

    margem_m = df["margem_votos"] / 1_000_000
    ax_abs.hist(margem_m, bins=60, color="#2ecc71", alpha=0.70, edgecolor="none")
    p5m, p50m, p95m = margem_m.quantile([0.05, 0.50, 0.95])
    ax_abs.axvline(p50m, color="#1a8a4a", lw=2.0, ls="--")
    ax_abs.axvspan(p5m, p95m, color="#2ecc71", alpha=0.10)
    ax_abs.text(p50m + 0.05, ax_abs.get_ylim()[1] * 0.88,
                f"Mediana\n{p50m:.2f}M votos",
                fontsize=8.5, color="#1a8a4a", va="top")
    ax_abs.text(p95m + 0.05, ax_abs.get_ylim()[1] * 0.60,
                f"IC 90%\n{p5m:.2f}M – {p95m:.2f}M",
                fontsize=7.5, color="#555555", va="top")
    ax_abs.set_xlabel("Margem de vitória (milhões de votos)", fontsize=9,
                      color="#666666", labelpad=6)
    ax_abs.set_ylabel("Frequência", fontsize=9, color="#666666")
    ax_abs.set_title(
        "Margem absoluta de vitória\n2º Turno",
        fontsize=11, fontweight="bold", pad=12, loc="left", color="#222222",
    )
    ax_abs.grid(axis="y", alpha=0.18, color="#aaaaaa")
    ax_abs.set_axisbelow(True)
    ax_abs.tick_params(bottom=False)

    # ── Header ─────────────────────────────────────────────────────────────────
    dias_restantes = (DATA_2T - date.today()).days
    fig.text(0.03, 0.950, "BRASIL 2026 — 2º TURNO",
             fontsize=24, fontweight="bold", color="#1a1a2e", va="bottom")
    fig.text(0.03, 0.932,
             f"Simulação Standalone  ·  Eleição em {dias_restantes} dias"
             f"  ({DATA_2T.strftime('%d/%m/%Y')})",
             fontsize=10, color="#555555", va="bottom")
    fig.text(0.03, 0.916,
             f"{N_SIM:,} simulações Monte Carlo  ·  Eleitorado: {ELEITORADO:,}  ·  "
             f"Abstenção: Normal({ABSTENCAO_2T_MU:.0%}, σ={ABSTENCAO_2T_SIGMA:.0%})",
             fontsize=8.5, color="#999999", va="bottom")
    fig.add_artist(plt.Line2D(
        [0.03, 0.97], [0.910, 0.910],
        transform=fig.transFigure, color="#dddddd", lw=1.2,
    ))

    out = OUTPUT_DIR / "simulacao_2turno.png"
    plt.savefig(out, dpi=300, bbox_inches="tight", facecolor=BG)
    print(f"   Graph saved: {out}")
    plt.close()


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  BRAZIL ELECTION — STANDALONE SECOND ROUND [v2.7]")
    print("  Monte Carlo · Dirichlet (3 categories) · PyMC-free")
    print("  Imports aggregation functions from simulation_v2")
    print("=" * 60)

    cand_a, cand_b, voto_a, voto_b, rej_a, rej_b, desvio, residual = (
        carregar_pesquisas_2t()
    )

    voto_a_adj, voto_b_adj, residual_final = redistribuir_residual(
        voto_a, voto_b, rej_a, rej_b, residual
    )

    df = simular(cand_a, cand_b, voto_a_adj, voto_b_adj, rej_a, rej_b,
                 desvio, residual_final)

    prob_a, prob_b = relatorio(df, cand_a, cand_b, rej_a, rej_b)

    graficos(df, cand_a, cand_b, rej_a, rej_b, prob_a, prob_b)

    print("\nSimulation completed. Results in /outputs:")
    print("  resultados_2turno_standalone.csv")
    print("  simulacao_2turno.png")
