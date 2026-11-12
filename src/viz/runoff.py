"""
Three-panel chart of a standalone runoff run (moved from simulation_2turno).

Left: semicircle of outcomes by margin category; top right: vote-share
distributions; bottom right: absolute margin in millions of valid votes.
Colors follow the candidate-identity palette shared with the other charts.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch, Wedge
import matplotlib.pyplot as plt
import numpy as np

from src.core.runoff import ABSTENCAO_2T_MU, ABSTENCAO_2T_SIGMA
from src.core.simulation import ELEITORADO
from src.viz.charts import generate_palette, hex_lighten
from src.viz.colors import candidate_palette


def plot_runoff(df, cand_a, cand_b, prob_a, prob_b, output_path,
                data_2t: date = date(2026, 10, 25), data_referencia: date | None = None):
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

    cores = candidate_palette([cand_a, cand_b], generate_palette(2))
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
        hex_lighten(cor_lider, 0.00),
        hex_lighten(cor_lider, 0.38),
        hex_lighten(cor_lider, 0.65),
        hex_lighten(cor_vice,  0.65),
        hex_lighten(cor_vice,  0.38),
        hex_lighten(cor_vice,  0.00),
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
        (1, f"Apertado\n{seg['lider_close']:.1f}%",   hex_lighten(cor_lider, 0.2), 6.0),
        (2, f"<1pp\n{seg['lider_photo']:.1f}%",        hex_lighten(cor_lider, 0.5), 2.0),
        (3, f"<1pp\n{seg['vice_photo']:.1f}%",         hex_lighten(cor_vice,  0.5), 2.0),
        (4, f"Apertado\n{seg['vice_close']:.1f}%",    hex_lighten(cor_vice,  0.2), 6.0),
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
                     edgecolor="none", label=f"{cand} (simulado)")
        mean_v = df[col].mean()
        ax_dist.axvline(mean_v, color=cor, lw=2.0, ls="--", alpha=0.85)
        ax_dist.text(0.02, 0.96 if col == "voto_a" else 0.88,
                     f"Média simulada {cand}: {mean_v:.1f}%", color=cor, fontsize=9,
                     transform=ax_dist.transAxes, fontweight="bold", va="top")

    meta = df.attrs.get("calibracao")
    if meta:
        ax_dist.axvline(meta["fatia_agregada_a"], color=cor_a, ls=":",
                        label=f"{cand_a}: agregada {meta['fatia_agregada_a']:.1f}%")
        ax_dist.axvline(meta["fatia_central_a"], color=cor_a, ls="-.",
                        label=f"{cand_a}: centro {meta['fatia_central_a']:.1f}% (viés {meta['vies_pp_a']:+.1f} pp)")
    ax_dist.axvline(50, color="#888888", lw=1.2, ls=":", alpha=0.6)
    ax_dist.set_xlabel("Votos válidos (%)", fontsize=9, color="#666666", labelpad=6)
    ax_dist.set_ylabel("Frequência", fontsize=9, color="#666666")
    ax_dist.set_title(
        f"Distribuição simulada de votos válidos\n{len(df):,} sorteios",
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
    referencia = data_referencia or date.today()
    dias_restantes = (data_2t - referencia).days
    quando = (f"Eleição em {dias_restantes} dias" if dias_restantes > 0
              else f"Pesquisas até {referencia.strftime('%d/%m/%Y')}")
    fig.text(0.03, 0.950, "BRASIL 2026 — 2º TURNO",
             fontsize=24, fontweight="bold", color="#1a1a2e", va="bottom")
    fig.text(0.03, 0.932,
             f"Simulação Standalone  ·  {quando}"
             f"  ({data_2t.strftime('%d/%m/%Y')})",
             fontsize=10, color="#555555", va="bottom")
    fig.text(0.03, 0.916,
             f"{len(df):,} simulações Monte Carlo  ·  Eleitorado: {ELEITORADO:,}  ·  "
             f"Abstenção: Normal({ABSTENCAO_2T_MU:.0%}, σ={ABSTENCAO_2T_SIGMA:.0%})",
             fontsize=8.5, color="#999999", va="bottom")
    fig.add_artist(plt.Line2D(
        [0.03, 0.97], [0.910, 0.910],
        transform=fig.transFigure, color="#dddddd", lw=1.2,
    ))

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=300, bbox_inches="tight", facecolor=BG)
    print(f"   Graph saved: {out}")
    plt.close()
    return out
