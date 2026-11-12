"""
Runoff forecast figure (``python -m src runoff`` and the v2.10 script).

Header and headline tiles (chance of winning, close race, median margin),
a segmented bar of how the race ends (by margin band) and the distribution
of the leader's valid-vote share. Colors follow the candidate identity
(``src.viz.colors``); text stays in ink tokens (``src.viz.tema``).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from src.viz import tema
from src.viz.charts import generate_palette
from src.viz.colors import candidate_palette

# Margin bands in pp of the valid votes (same cut points as before).
FAIXAS = (("folgada", 5.0, np.inf), ("apertada", 1.0, 5.0), ("photo finish", 0.0, 1.0))


def plot_runoff(df, cand_a, cand_b, prob_a, prob_b, output_path,
                data_2t: date = date(2026, 10, 25), data_referencia: date | None = None,
                nota: str | None = None):
    """Save the runoff figure for a standalone runoff simulation.

    Args:
        df: Simulation rows with ``voto_a``, ``voto_b``, ``vencedor``,
            ``diferenca`` and ``margem_votos`` (``attrs["calibracao"]`` is used
            for the bias scenario when present).
        cand_a, cand_b: Candidates of ``voto_a`` / ``voto_b``.
        prob_a, prob_b: Win probabilities in %.
        output_path: PNG path.
        data_2t: Runoff day.
        data_referencia: Poll cut-off date (subtitle).
        nota: Footer text (model parameters); a generic note when omitted.

    Returns:
        The saved path.
    """
    print("\n[VIZ] Generating visualization...")

    cor_a, cor_b = candidate_palette([cand_a, cand_b], generate_palette(2))
    if prob_a >= prob_b:
        lider, vice, p_lider, p_vice, cor_l, cor_v, col_l = (
            cand_a, cand_b, prob_a, prob_b, cor_a, cor_b, "voto_a")
    else:
        lider, vice, p_lider, p_vice, cor_l, cor_v, col_l = (
            cand_b, cand_a, prob_b, prob_a, cor_b, cor_a, "voto_b")

    n = len(df)
    dif = df["diferenca"].to_numpy(dtype=float)
    vence_l = (df["vencedor"] == lider).to_numpy()
    margem_m = df["margem_votos"].to_numpy(dtype=float) / 1e6

    with tema.estilo():
        fig = plt.figure(figsize=(16, 10))

        partes = []
        if data_referencia is not None:
            partes.append(f"Previsão com pesquisas até {tema.data_br(data_referencia)}")
        partes.append(f"votação em {tema.data_br(data_2t)}")
        partes.append(f"{tema.inteiro(n)} simulações")
        meta = df.attrs.get("calibracao") or {}
        vies = float(meta.get("vies_pp_a", 0.0) or 0.0)
        if vies:
            favorecido = cand_a if vies > 0 else cand_b
            partes.append(f"cenário: +{tema.num(abs(vies))} pp para {favorecido}")
        sub = " · ".join(partes)
        tema.cabecalho(fig, f"Eleição presidencial {data_2t.year} · 2º turno",
                       sub[0].upper() + sub[1:])

        # ── Tiles ──────────────────────────────────────────────────────────────
        x0, gap, y, h = 0.04, 0.012, 0.735, 0.145
        w = (0.92 - 3 * gap) / 4
        xs = [x0 + k * (w + gap) for k in range(4)]
        tema.cartao(fig, xs[0], y, w, h, f"{lider} · chance de vencer",
                    tema.prob_curta(p_lider), f"{tema.pct(p_lider)} das simulações", cor=cor_l)
        tema.cartao(fig, xs[1], y, w, h, f"{vice} · chance de vencer",
                    tema.prob_curta(p_vice), f"{tema.pct(p_vice)} das simulações", cor=cor_v)
        tema.cartao(fig, xs[2], y, w, h, "Disputa apertada", tema.prob_curta(100 * (dif < 3).mean()),
                    "diferença menor que 3 pontos nos votos válidos")
        p5, p50, p95 = np.quantile(margem_m, [0.05, 0.5, 0.95])
        tema.cartao(fig, xs[3], y, w, h, "Margem do vencedor (mediana)",
                    f"{tema.num(p50)} mi", f"votos; 90% das simulações: "
                    f"{tema.num(p5)} a {tema.num(p95)} milhões")

        # ── How the race ends ──────────────────────────────────────────────────
        ax_bar = fig.add_axes([0.04, 0.465, 0.92, 0.10])
        _barra_desfechos(ax_bar, dif, vence_l, lider, vice, cor_l, cor_v)

        # ── Leader's share ─────────────────────────────────────────────────────
        ax_h = fig.add_axes([0.04, 0.09, 0.92, 0.26])
        # Poll average and scenario centre, in the displayed candidate's terms.
        def _no_lider(v):
            return None if v is None else (float(v) if lider == cand_a else 100.0 - float(v))
        _histograma_fatia(ax_h, df[col_l].to_numpy(dtype=float), lider, vice, cor_l, cor_v,
                          _no_lider(meta.get("fatia_agregada_a")),
                          _no_lider(meta.get("fatia_central_a")) if vies else None,
                          vies if lider == cand_a else -vies)

        tema.rodape(fig, nota or ("Pesquisas de 2º turno agregadas pela fatia de dois"
                                  " candidatos · não é previsão oficial"))
        fig.canvas.draw()

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"   Graph saved: {out}")
    plt.close(fig)
    return out


def _barra_desfechos(ax, dif, vence_l, lider, vice, cor_l, cor_v) -> None:
    """Segmented bar: leader wins by band (dark -> light), then the runner-up."""
    segmentos = []
    for faixa, lo, hi in FAIXAS:
        segmentos.append((lider, faixa, 100 * (vence_l & (dif >= lo) & (dif < hi)).mean()))
    for faixa, lo, hi in reversed(FAIXAS):
        segmentos.append((vice, faixa, 100 * (~vence_l & (dif >= lo) & (dif < hi)).mean()))
    rampa_l, rampa_v = tema.RAMPA.get(cor_l), tema.RAMPA.get(cor_v)
    cores = ([*(rampa_l or (cor_l,) * 3)] + [*(rampa_v or (cor_v,) * 3)][::-1])

    x = 0.0
    for (cand, faixa, p), c, k in zip(segmentos, cores, range(6)):
        if p > 0:
            ax.barh(0, p, left=x, height=0.8, color=c, edgecolor=tema.SUPERFICIE, lw=2)
            claro = k in (2, 3)
            if p >= 6:
                ax.text(x + p / 2, 0.06, tema.pct(p, 0), ha="center", va="center",
                        fontsize=13, fontweight="bold",
                        color=tema.TINTA if claro else "#ffffff")
                ax.text(x + p / 2, -0.22, faixa, ha="center", va="center", fontsize=9.5,
                        color=tema.TINTA if claro else "#ffffff")
            elif p >= 2:
                ax.text(x + p / 2, 0, tema.pct(p, 0), ha="center", va="center",
                        fontsize=10, color=tema.TINTA if claro else "#ffffff")
        x += p
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.45, 0.45)
    ax.axis("off")
    ax.text(0, 0.62, f"{lider} vence", transform=ax.get_yaxis_transform(),
            ha="left", va="bottom", fontsize=12, fontweight="bold", color=tema.TINTA)
    ax.text(1, 0.62, f"{vice} vence", transform=ax.get_yaxis_transform(),
            ha="right", va="bottom", fontsize=12, fontweight="bold", color=tema.TINTA)
    ax.text(0, 1.95, "Como termina a disputa", transform=ax.transAxes, fontsize=14,
            fontweight="bold", color=tema.TINTA, va="bottom")
    ax.text(0, 1.60, "Margem nos votos válidos: folgada ≥ 5 pontos · apertada 1 a 5 ·"
            " photo finish < 1", transform=ax.transAxes, fontsize=10.5,
            color=tema.TINTA_2, va="bottom")


def _histograma_fatia(ax, fatia, lider, vice, cor_l, cor_v,
                      pesquisas=None, centro=None, vies=0.0) -> None:
    """Distribution of the leader's valid-vote share, split at 50%.

    Above the bars: the 90% range with the simulated mean (dot), the poll
    average (triangle) and, in a bias scenario, the shifted centre (diamond),
    so the three quantities of the summary contract stay distinguishable.
    """
    lo, hi = np.quantile(fatia, [0.002, 0.998])
    lo, hi = min(lo, 49.0), max(hi, 51.0)
    bins = np.arange(np.floor(lo * 4) / 4, hi + 0.25, 0.25)
    ganha = fatia > 50
    ax.hist(fatia[ganha], bins=bins, color=cor_l, edgecolor=tema.SUPERFICIE, lw=0.5)
    ax.hist(fatia[~ganha], bins=bins, color=cor_v, edgecolor=tema.SUPERFICIE, lw=0.5)
    ax.axvline(50, color=tema.TINTA_2, lw=1.2)
    p5, p95 = np.quantile(fatia, [0.05, 0.95])
    media = float(np.mean(fatia))
    topo = ax.get_ylim()[1]
    y = topo * 1.04
    ax.plot([p5, p95], [y, y], color=tema.TINTA_2, lw=1.5, solid_capstyle="butt")
    ax.plot([media], [y], "o", color=tema.TINTA, ms=6, zorder=4)
    linhas = [f"média simulada {tema.pct(media)} · 90% entre {tema.num(p5)} e {tema.num(p95)}"]
    if pesquisas is not None:
        ax.plot([pesquisas], [y], "v", color=tema.TINTA_2, ms=7, zorder=3,
                markeredgecolor=tema.SUPERFICIE)
        linhas.append(f"▼ média das pesquisas {tema.pct(pesquisas)}")
    if centro is not None:
        ax.plot([centro], [y], "D", color=tema.SUPERFICIE, ms=6, zorder=5,
                markeredgecolor=tema.TINTA, markeredgewidth=1.5)
        sinal = "+" if vies > 0 else "−"
        linhas.append(rf"$\diamond$ centro do cenário {tema.pct(centro)} (viés {sinal}{tema.num(abs(vies))} pp)")
    ax.annotate("\n".join(linhas), (p95, y), xytext=(8, 0), textcoords="offset points",
                va="top" if len(linhas) > 1 else "center", fontsize=10.5,
                color=tema.TINTA_2, linespacing=1.5)
    ax.set_ylim(0, topo * 1.12)
    ax.set_yticks([])
    ax.set_xlim(bins[0], bins[-1])
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    tema.eixo_limpo(ax, grade_x=False)
    ax.text(0.01, 0.80, f"← {vice} vence", transform=ax.transAxes, fontsize=11.5,
            color=tema.TINTA, ha="left")
    ax.text(0.99, 0.80, f"{lider} vence →", transform=ax.transAxes, fontsize=11.5,
            color=tema.TINTA, ha="right")
    tema.titulo_painel(ax, f"Votos válidos de {lider}",
                       f"Distribuição nas simulações; à direita de 50% {lider} vence")
