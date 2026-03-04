"""
brazil-election-montecarlo — Combined First + Second Round Simulation (v2.7+)
==============================================================================
Orchestrates both simulation stages using their dedicated data sources:

    Stage 1 (1T):  simulation_v2.py + data/pesquisas.csv
                   PyMC Dirichlet model · N candidates · poll aggregation
    Stage 2 (2T):  simulation_2turno.py + data/pesquisas_2turno.csv
                   Dirichlet (3 categories) · PyMC-free · standalone model

Motivation:
    simulation_v2.py derives the second round from the top-2 finalists of
    each first-round simulation (using vote-transfer heuristics). Once
    dedicated second-round polls are available — which capture transfer
    dynamics, updated rejection, and smaller undecided pools — running the
    full first-round model just to reach the runoff adds noise rather than
    signal. This script runs each stage independently against its own data
    and combines the outputs into a single dashboard.

Usage:
    python src/simulation_combined.py

Requirements:
    data/pesquisas.csv          — first-round poll data
    data/pesquisas_2turno.csv   — second-round poll data

Outputs:
    outputs/resultados_1turno_v2.csv          (from simulation_v2)
    outputs/resultados_2turno_standalone.csv  (from simulation_2turno)
    outputs/simulacao_combinada.png           (combined dashboard)

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

sys.path.insert(0, str(Path(__file__).parent))

# ── Stage 1 imports ───────────────────────────────────────────────────────────
import simulation_v2 as s1

# ── Stage 2 imports ───────────────────────────────────────────────────────────
from simulation_2turno import (
    carregar_pesquisas_2t,
    redistribuir_residual,
    simular as simular_2t,
    relatorio as relatorio_2t,
    DATA_2T,
    N_SIM as N_SIM_2T,
)

# ─── CONFIG ───────────────────────────────────────────────────────────────────

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

BG = "#F7F7F7"


# ─── COMBINED VISUALIZATION ───────────────────────────────────────────────────

def graficos_combinados(
    df1: pd.DataFrame,
    df_2t: pd.DataFrame,
    cand_a: str,
    cand_b: str,
    prob_a: float,
    prob_b: float,
    rej_a: float,
    rej_b: float,
) -> None:
    """
    Renders a combined dashboard with first-round and second-round results.

    Layout (mirrors simulation_v2 graficos() but 2T data from standalone model):
        Left panel:    Second-round semicircle (from simulation_2turno).
        Top-right:     First-round vote intention · 90% CI (from simulation_v2).
        Bottom-right:  Rejection index · electoral ceiling (from simulation_v2).

    Args:
        df1:     First-round simulation DataFrame (simulation_v2 output).
        df_2t:   Second-round simulation DataFrame (simulation_2turno output).
        cand_a:  Leader candidate name (sorted by poll aggregation).
        cand_b:  Trailing candidate name.
        prob_a:  Probability of cand_a winning the runoff (%).
        prob_b:  Probability of cand_b winning the runoff (%).
        rej_a:   Aggregated rejection rate for cand_a (%).
        rej_b:   Aggregated rejection rate for cand_b (%).
    """
    plt.rcParams.update({"axes.facecolor": BG, "figure.facecolor": BG})

    fig = plt.figure(figsize=(18, 11), facecolor=BG)
    gs = gridspec.GridSpec(
        2, 2, figure=fig,
        width_ratios=[1.35, 1], height_ratios=[1, 1],
        hspace=0.40, wspace=0.10,
        left=0.03, right=0.97, top=0.87, bottom=0.06,
    )
    ax_semi = fig.add_subplot(gs[:, 0])
    ax_vote = fig.add_subplot(gs[0, 1])
    ax_rej  = fig.add_subplot(gs[1, 1])

    candidatos_validos = [
        c for c in s1.CANDIDATOS if "Brancos" not in c and "Nulos" not in c
    ]
    dias_1t = (s1.DATA_ELEICAO - date.today()).days
    dias_2t = (DATA_2T - date.today()).days

    # ── Leader / vice colors ──────────────────────────────────────────────────
    lider = cand_a if prob_a >= prob_b else cand_b
    vice  = cand_b if lider == cand_a else cand_a
    prob_lider = prob_a if lider == cand_a else prob_b
    prob_vice  = prob_b if lider == cand_a else prob_a

    idx_lider = s1.CANDIDATOS.index(lider) if lider in s1.CANDIDATOS else 0
    idx_vice  = s1.CANDIDATOS.index(vice)  if vice  in s1.CANDIDATOS else 1
    cor_lider = s1.CORES[idx_lider]
    cor_vice  = s1.CORES[idx_vice]

    # ── Margin segments from df_2t ────────────────────────────────────────────
    n = len(df_2t)
    mask_l = df_2t["vencedor"] == lider
    mask_v = df_2t["vencedor"] == vice

    def _pct(mask: pd.Series) -> float:
        return float(mask.sum() / n * 100)

    seg = {
        "lider_confort": _pct(mask_l & (df_2t["diferenca"] >= 5)),
        "lider_close":   _pct(mask_l & df_2t["diferenca"].between(1, 5)),
        "lider_photo":   _pct(mask_l & (df_2t["diferenca"] < 1)),
        "vice_photo":    _pct(mask_v & (df_2t["diferenca"] < 1)),
        "vice_close":    _pct(mask_v & df_2t["diferenca"].between(1, 5)),
        "vice_confort":  _pct(mask_v & (df_2t["diferenca"] >= 5)),
    }
    pct_apertada = float((df_2t["diferenca"] < 3).mean() * 100)

    # ── PANEL 1: Second-round semicircle ──────────────────────────────────────
    ax_semi.set_aspect("equal")
    ax_semi.set_xlim(-1.50, 1.50)
    ax_semi.set_ylim(-0.54, 1.50)
    ax_semi.axis("off")

    R_OUT, R_IN = 1.0, 0.50
    center = (0.0, 0.0)

    colors_seq = [
        s1._hex_lighten(cor_lider, 0.00),
        s1._hex_lighten(cor_lider, 0.38),
        s1._hex_lighten(cor_lider, 0.65),
        s1._hex_lighten(cor_vice,  0.65),
        s1._hex_lighten(cor_vice,  0.38),
        s1._hex_lighten(cor_vice,  0.00),
    ]
    seg_values = list(seg.values())
    total_seg  = sum(seg_values) or 100.0
    angles = [v / total_seg * 180.0 for v in seg_values]

    current = 180.0
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

    ax_semi.text(0, 0.14, f"{prob_lider:.1f}%",
                 ha="center", va="center", fontsize=32, fontweight="bold",
                 color=cor_lider, zorder=6)
    ax_semi.text(0, -0.08, f"{prob_vice:.1f}%",
                 ha="center", va="center", fontsize=20,
                 color=cor_vice, zorder=6)
    ax_semi.text(0, -0.24,
                 f"Corrida apertada (<3pp): {pct_apertada:.1f}%",
                 ha="center", va="center", fontsize=8.5, color="#777777", zorder=6)

    outer_labels = [
        (0, f"Folgado\n{seg['lider_confort']:.1f}%",  cor_lider,                      4.0),
        (1, f"Apertado\n{seg['lider_close']:.1f}%",   s1._hex_lighten(cor_lider, 0.2), 6.0),
        (2, f"<1pp\n{seg['lider_photo']:.1f}%",        s1._hex_lighten(cor_lider, 0.5), 2.0),
        (3, f"<1pp\n{seg['vice_photo']:.1f}%",         s1._hex_lighten(cor_vice,  0.5), 2.0),
        (4, f"Apertado\n{seg['vice_close']:.1f}%",    s1._hex_lighten(cor_vice,  0.2), 6.0),
        (5, f"Folgado\n{seg['vice_confort']:.1f}%",   cor_vice,                       4.0),
    ]
    Y_CEIL = 1.08
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
    for x0, cand_name, cor in [(-1.44, lider, cor_lider), (0.34, vice, cor_vice)]:
        prob = prob_lider if cand_name == lider else prob_vice
        ax_semi.add_patch(FancyBboxPatch(
            (x0, -0.51), w_box, h_box,
            boxstyle="round,pad=0.03",
            facecolor=cor, edgecolor="none", alpha=0.12, zorder=2,
        ))
        ax_semi.text(x0 + w_box / 2, -0.51 + h_box * 0.72,
                     cand_name, ha="center", va="center",
                     fontsize=10.5, fontweight="bold", color=cor)
        ax_semi.text(x0 + w_box / 2, -0.51 + h_box * 0.22,
                     f"Vitória no 2º turno: {prob:.1f}%",
                     ha="center", va="center", fontsize=9, color=cor)

    ax_semi.text(0, 1.20, "SEGUNDO TURNO",
                 ha="center", va="center", fontsize=13,
                 color="#333333", fontweight="bold")

    # Source annotation: distinguish standalone 2T model from derived 2T
    ax_semi.text(0, -0.46,
                 "Modelo 2T: pesquisas_2turno.csv (standalone)",
                 ha="center", va="center", fontsize=7.5, color="#999999", zorder=6)

    # ── PANEL 2: First-round vote intention · 90% CI ──────────────────────────
    for spine in ax_vote.spines.values():
        spine.set_visible(False)
    ax_vote.tick_params(left=False, bottom=False)

    cands_plot = list(reversed(candidatos_validos))
    for y, cand in enumerate(cands_plot):
        idx   = s1.CANDIDATOS.index(cand)
        col   = s1.CORES[idx]
        col_v = f"{cand}_val"
        serie = df1[col_v] if col_v in df1.columns else df1[cand]

        mean_v = serie.mean()
        ci_lo  = serie.quantile(0.05)
        ci_hi  = serie.quantile(0.95)

        ax_vote.plot([ci_lo, ci_hi], [y, y], color=col, lw=3,
                     alpha=0.35, solid_capstyle="round")
        ax_vote.scatter([mean_v], [y], color=col, s=110, zorder=5)
        ax_vote.text(mean_v, y + 0.34, f"{mean_v:.1f}%",
                     ha="center", va="bottom", fontsize=9.5,
                     fontweight="bold", color=col)
        ax_vote.text(ci_lo - 0.8, y, f"{ci_lo:.1f}",
                     ha="right", va="center", fontsize=7.5, color="#aaaaaa")
        ax_vote.text(ci_hi + 0.8, y, f"{ci_hi:.1f}",
                     ha="left",  va="center", fontsize=7.5, color="#aaaaaa")

    ax_vote.set_yticks(range(len(cands_plot)))
    ax_vote.set_yticklabels(cands_plot, fontsize=10.5)
    ax_vote.axvline(50, color="#aaaaaa", ls="--", lw=1, alpha=0.5)
    ax_vote.set_xlim(0, 62)
    ax_vote.set_ylim(-0.6, len(cands_plot) - 0.4)
    ax_vote.grid(axis="x", alpha=0.18, color="#aaaaaa")
    ax_vote.set_axisbelow(True)
    ax_vote.set_xlabel("Votos válidos (%)", fontsize=9, color="#666666", labelpad=6)
    ax_vote.set_title(
        "Intenção de Voto  ·  1º Turno\nIC 90% — votos válidos",
        fontsize=11, fontweight="bold", pad=12, loc="left", color="#222222",
    )

    # ── PANEL 3: Rejection index ───────────────────────────────────────────────
    for spine in ax_rej.spines.values():
        spine.set_visible(False)
    ax_rej.tick_params(left=False, bottom=False)

    cands_rej = [
        c for c in candidatos_validos if s1.REJEICAO[s1.CANDIDATOS.index(c)] > 0
    ]
    cands_rej_rev = list(reversed(cands_rej))

    for y, cand in enumerate(cands_rej_rev):
        idx  = s1.CANDIDATOS.index(cand)
        rej  = s1.REJEICAO[idx]
        teto = 100 - rej

        if rej > 50:
            bar_color, status = "#c0392b", "Inviável"
        elif rej > 45:
            bar_color, status = "#e67e22", "Dificuldade alta"
        else:
            bar_color, status = "#27ae60", "Viável"

        ax_rej.barh(y, 72, color="#e8e8e8", height=0.50, zorder=1)
        ax_rej.barh(y, rej, color=bar_color, height=0.50, alpha=0.80, zorder=2)
        ax_rej.text(rej + 1.2, y + 0.13,
                    f"{rej:.0f}%  →  teto {teto:.0f}%   {status}",
                    ha="left", va="center", fontsize=8.5,
                    color="#333333", fontweight="bold")

    ax_rej.axvline(50, color="#c0392b", ls="--", lw=1.5, alpha=0.65, zorder=5)
    ax_rej.text(50.8, len(cands_rej_rev) - 0.50,
                "Limite crítico\n(50%)", fontsize=7.5, color="#c0392b", va="top")
    ax_rej.set_yticks(range(len(cands_rej_rev)))
    ax_rej.set_yticklabels(cands_rej_rev, fontsize=10.5)
    ax_rej.set_xlim(0, 95)
    ax_rej.set_ylim(-0.55, len(cands_rej_rev) - 0.45)
    ax_rej.grid(axis="x", alpha=0.18, color="#aaaaaa")
    ax_rej.set_axisbelow(True)
    ax_rej.set_xlabel("Rejeição (%)", fontsize=9, color="#666666", labelpad=6)
    ax_rej.set_title(
        "Índice de Rejeição  ·  Teto Eleitoral",
        fontsize=11, fontweight="bold", pad=12, loc="left", color="#222222",
    )

    # ── Header ────────────────────────────────────────────────────────────────
    fig.text(0.03, 0.950, "BRASIL 2026",
             fontsize=24, fontweight="bold", color="#1a1a2e", va="bottom")
    fig.text(0.03, 0.932,
             f"Previsão Presidencial  ·  1T em {dias_1t} dias ({s1.DATA_ELEICAO.strftime('%d/%m/%Y')})"
             f"  ·  2T em {dias_2t} dias ({DATA_2T.strftime('%d/%m/%Y')})",
             fontsize=10, color="#555555", va="bottom")
    fig.text(0.03, 0.916,
             f"1T: {s1.N_SIM:,} simulações (PyMC)  ·  "
             f"2T: {N_SIM_2T:,} simulações (standalone)  ·  "
             f"σ = {s1.DESVIO:.2f}%",
             fontsize=8.5, color="#999999", va="bottom")
    fig.add_artist(plt.Line2D(
        [0.03, 0.97], [0.910, 0.910],
        transform=fig.transFigure, color="#dddddd", lw=1.2,
    ))

    out = OUTPUT_DIR / "simulacao_combinada.png"
    plt.savefig(out, dpi=300, bbox_inches="tight", facecolor=BG)
    print(f"   Graph saved: {out}")
    plt.close()


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("  BRAZIL ELECTION — COMBINED SIMULATION [v2.7+]")
    print("  Stage 1: simulation_v2  (1T · PyMC · pesquisas.csv)")
    print("  Stage 2: simulation_2turno  (2T · standalone · pesquisas_2turno.csv)")
    print("=" * 65)

    # ── Stage 1: First Round ──────────────────────────────────────────────────
    print("\n[STAGE 1] First Round")
    s1.inicializar()
    s1.validar_viabilidade()
    trace = s1.construir_modelo()
    df1, info_lim_1t, info_indecisos, validos_final, candidatos_validos = (
        s1.simular_primeiro_turno()
    )
    # Report 1T only (pass empty df2 to skip 2T section)
    pv, _, p2t = s1.relatorio(df1, pd.DataFrame(), info_lim_1t, {}, info_indecisos)

    # ── Stage 2: Second Round (standalone) ───────────────────────────────────
    print("\n[STAGE 2] Second Round (standalone model)")
    cand_a, cand_b, voto_a, voto_b, rej_a, rej_b, desvio, residual = (
        carregar_pesquisas_2t()
    )
    voto_a_adj, voto_b_adj, residual_final = redistribuir_residual(
        voto_a, voto_b, rej_a, rej_b, residual
    )
    df_2t = simular_2t(
        cand_a, cand_b, voto_a_adj, voto_b_adj, rej_a, rej_b, desvio, residual_final
    )
    prob_a, prob_b = relatorio_2t(df_2t, cand_a, cand_b, rej_a, rej_b)

    # ── Combined visualization ────────────────────────────────────────────────
    print("\n[COMBINED] Rendering combined dashboard...")
    graficos_combinados(df1, df_2t, cand_a, cand_b, prob_a, prob_b, rej_a, rej_b)

    print("\nSimulation completed. Results in /outputs:")
    print("  resultados_1turno_v2.csv")
    print("  resultados_2turno_standalone.csv")
    print("  simulacao_combinada.png")
    print("\nModel sources:")
    print(f"  1T data:  data/pesquisas.csv  ({s1.N_SIM:,} sims · PyMC)")
    print(f"  2T data:  data/pesquisas_2turno.csv  ({N_SIM_2T:,} sims · Dirichlet)")
