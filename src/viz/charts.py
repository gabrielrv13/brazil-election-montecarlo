"""
src/viz/charts.py
=================
Parametrized visualization layer for brazil-election-montecarlo v3.0.

Design contracts
----------------
- Every public function accepts data as parameters and returns a ``Figure``.
- No global variable reads. No matplotlib state mutations outside the returned Figure.
- No calls to ``plt.show()``, ``plt.savefig()``, or ``plt.close()``.
  The caller is responsible for I/O decisions.
- No imports from ``simulation_v2``, ``simulation_combined``, or any legacy module.
- ``output_dir`` is accepted as an explicit ``Path`` argument where persistence is needed;
  chart-returning functions do not write files themselves.
"""

from __future__ import annotations

import colorsys
from datetime import date
from pathlib import Path
from typing import Optional

import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from src.viz.colors import candidate_palette
from src.core.events import eventos_primeiro_turno, probabilidades_vitoria_2t


# ─── PALETTE UTILITIES ────────────────────────────────────────────────────────

_PALETTE_BASE: list[str] = [
    "#e74c3c",  # vermelho
    "#3498db",  # azul
    "#2ecc71",  # verde
    "#f39c12",  # laranja
    "#9b59b6",  # roxo
    "#34495e",  # chumbo
    "#95a5a6",  # cinza
    "#1abc9c",  # turquesa
]

MARGIN_THRESHOLDS: list[int] = [5, 10, 15, 20, 25]


def generate_palette(n: int) -> list[str]:
    """Return ``n`` distinct hex color strings.

    Uses the curated base palette for n ≤ 8; falls back to matplotlib's
    ``tab10`` colormap for larger candidate sets.

    Args:
        n: Number of colors required.

    Returns:
        List of ``n`` hex color strings.
    """
    if n <= len(_PALETTE_BASE):
        return _PALETTE_BASE[:n]
    # matplotlib.cm.get_cmap was removed in matplotlib 3.9; the colormap
    # registry exists since 3.5.
    import matplotlib  # noqa: PLC0415
    cmap = matplotlib.colormaps["tab10"]
    return [
        "#{:02x}{:02x}{:02x}".format(
            int(r * 255), int(g * 255), int(b * 255)
        )
        for r, g, b, _ in (cmap(i / n) for i in range(n))
    ]


def hex_lighten(hex_color: str, factor: float) -> str:
    """Blend ``hex_color`` toward white by ``factor`` (0.0 = original, 1.0 = white).

    Args:
        hex_color: Source color in ``#rrggbb`` format.
        factor: Blend weight toward white in [0.0, 1.0].

    Returns:
        Blended color in ``#rrggbb`` format.
    """
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return "#{:02x}{:02x}{:02x}".format(
        int(r + (255 - r) * factor),
        int(g + (255 - g) * factor),
        int(b + (255 - b) * factor),
    )


# ─── FORECAST TRACKER ─────────────────────────────────────────────────────────

def plot_forecast_tracker(
    history_df: pd.DataFrame,
    *,
    candidates: Optional[list[str]] = None,
    palette: Optional[list[str]] = None,
    election_date: Optional[date] = None,
    title: str = "Evolução da Previsão — Brasil 2026",
    figsize: tuple[float, float] = (12, 6),
) -> Figure:
    """Plot win-probability trajectories with confidence bands for each candidate.

    Reads a long-format DataFrame produced by ``src/io/history.carregar_historico()``.

    Expected columns
    ----------------
    - ``date``       : datetime-like, the snapshot date.
    - ``candidate``  : str, candidate name.
    - ``win_prob``   : float, model win probability in [0, 100].
    - ``ci_lo``      : float, lower bound of the 90 % CI (same scale as ``win_prob``).
    - ``ci_hi``      : float, upper bound of the 90 % CI.

    Args:
        history_df:
            Long-format DataFrame with columns ``date``, ``candidate``,
            ``win_prob``, ``ci_lo``, ``ci_hi``.
        candidates:
            Ordered list of candidate names to plot. If ``None``, all unique
            values in ``history_df["candidate"]`` are used.
        palette:
            List of hex color strings, one per entry in ``candidates``.
            If ``None``, ``generate_palette`` is called automatically.
        election_date:
            If provided, a vertical dashed reference line is drawn on this date.
        title:
            Figure title string.
        figsize:
            Matplotlib figure size ``(width, height)`` in inches.

    Returns:
        A ``matplotlib.figure.Figure`` instance. The caller decides whether to
        call ``fig.savefig()``, ``plt.show()``, or embed in Streamlit.
    """
    df = history_df.copy()
    df["date"] = pd.to_datetime(df["date"])

    if candidates is None:
        candidates = sorted(df["candidate"].unique().tolist())

    if palette is None:
        palette = candidate_palette(candidates, generate_palette(len(candidates)))

    color_map: dict[str, str] = dict(zip(candidates, palette))

    BG = "#F7F7F7"
    fig, ax = plt.subplots(figsize=figsize, facecolor=BG)
    ax.set_facecolor(BG)

    for cand in candidates:
        subset = df[df["candidate"] == cand].sort_values("date")
        if subset.empty:
            continue

        col = color_map[cand]
        dates = subset["date"].values
        probs = subset["win_prob"].values
        ci_lo = subset["ci_lo"].values
        ci_hi = subset["ci_hi"].values

        # Confidence band
        ax.fill_between(dates, ci_lo, ci_hi, color=col, alpha=0.15, linewidth=0)

        # Trajectory line
        ax.plot(dates, probs, color=col, linewidth=2.2, label=cand, zorder=3)

        # Terminal annotation — last known value
        if len(probs):
            ax.annotate(
                f"{probs[-1]:.1f}%",
                xy=(dates[-1], probs[-1]),
                xytext=(6, 0),
                textcoords="offset points",
                fontsize=8.5,
                color=col,
                va="center",
                fontweight="bold",
            )

    # Election date reference
    if election_date is not None:
        ax.axvline(
            pd.Timestamp(election_date),
            color="#aaaaaa",
            linestyle="--",
            linewidth=1.2,
            alpha=0.7,
            zorder=2,
        )
        ax.text(
            pd.Timestamp(election_date),
            ax.get_ylim()[1] * 0.98,
            "  Eleição",
            fontsize=8,
            color="#888888",
            va="top",
        )

    # Axis formatting
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=10))
    ax.set_ylabel("Prob. vitória (%)", fontsize=10, color="#555555", labelpad=8)
    ax.set_ylim(bottom=0, top=100)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100, decimals=0))

    # Grid — horizontal only, light
    ax.grid(axis="y", alpha=0.22, color="#aaaaaa", linewidth=0.8)
    ax.grid(axis="x", visible=False)

    # Spines
    for spine in ("top", "right", "bottom"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#cccccc")
    ax.tick_params(colors="#666666", labelsize=9)

    # Legend
    ax.legend(
        loc="upper left",
        fontsize=9,
        framealpha=0.85,
        edgecolor="#dddddd",
        labelcolor="#333333",
    )

    fig.suptitle(title, fontsize=13, fontweight="bold", color="#1a1a2e", x=0.03, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.96])

    return fig

# ─── FORECAST HISTORY (SQLite) ────────────────────────────────────────────────

def plot_forecast_history(
    df_history: pd.DataFrame,
    *,
    use_p2v: bool = True,
    event: str | None = None,
    palette: Optional[list[str]] = None,
    election_date: Optional[date] = None,
    poll_dates: Optional[list] = None,
    figsize: tuple[float, float] = (12, 6),
) -> Figure:
    """Plot one explicit probability event from forecast history (SQLite).

    Consumes the DataFrame returned by ``src.io.history.carregar_historico()``. Each row represents one completed simulation run. The event selector never substitutes leadership for victory. Legacy rows are omitted from version-2 events.

    CI derivation
    -------------
    Win probability is a binomial proportion estimated from ``n_sim`` Monte Carlo draws.  The 80 % CI uses the normal approximation::

        p ± 1.28 × sqrt(p × (1 − p) / n_sim)

    This is adequate for the operational range 10 %–90 %.  Near 0 or 1 the interval is conservative (wider than the exact Clopper–Pearson bound).

    Args:
        df_history:
            Output of ``carregar_historico()``.  Required columns:
            ``run_at`` (datetime), ``pv`` (dict, values in [0, 1]),
            ``p2v`` (dict, values in [0, 1]), ``n_sim`` (int).
        use_p2v:
            When ``True`` (default), plots second-round win probability from ``p2v``.  Never falls back to another event; missing observations are omitted.
        event:
            Explicit field: p_lideranca, p_vitoria_1t, p_classificacao_2t or p2v.
            Overrides use_p2v. Without event, use_p2v=False selects leadership,
            preserving the original numerical meaning while correcting its label.
        palette:
            Hex color strings, one per candidate. Generated via ``generate_palette`` when ``None``.
        election_date:
            If provided, draws a vertical reference line at this date.
        poll_dates:
            Explicit dates when new polls were added to ``pesquisas.csv``. Each is marked with a labeled dashed vertical line. When ``None``, every simulation run date is marked with a rug
            of thin vertical ticks at the bottom of the chart.
        figsize:
            Figure size in inches.

    Returns:
        ``matplotlib.figure.Figure``.
    """
    if df_history.empty:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(
            0.5, 0.5, "Nenhum histórico disponível.",
            ha="center", va="center", fontsize=12, color="#888888",
            transform=ax.transAxes,
        )
        ax.axis("off")
        return fig

    event = event or ("p2v" if use_p2v else "p_lideranca")
    labels = {"p2v": "P(vitória 2º turno | segundo turno)",
              "p_lideranca": "P(liderança 1º turno)",
              "p_vitoria_1t": "P(vitória direta 1º turno)",
              "p_classificacao_2t": "P(classificação 2º turno)"}
    if event not in labels:
        raise ValueError(f"Unknown probability event: {event}")
    df = df_history.copy()
    if event == "p2v" and "event_contract_version" not in df:
        labels[event] = "P(vitória 2º turno; contrato legado)"
    if event == "p_lideranca" and event not in df:
        # Explicit legacy argmax leadership view, never direct victory.
        df[event] = df["pv"]
    elif event not in df:
        df[event] = [{} for _ in range(len(df))]
    if event == "p2v" and "event_contract_version" in df:
        df.loc[df["event_contract_version"] < 2, event] = pd.Series(
            [{} for _ in range((df["event_contract_version"] < 2).sum())],
            index=df.index[df["event_contract_version"] < 2], dtype=object)

    df["run_at"] = pd.to_datetime(df["run_at"])
    df = df.sort_values("run_at").reset_index(drop=True)

    all_candidates: set[str] = set()
    for values in df[event]:
        if isinstance(values, dict):
            all_candidates.update(values)

    candidates = sorted(all_candidates)
    if not candidates:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(
            0.5, 0.5, "Histórico sem candidatos reconhecidos.",
            ha="center", va="center", fontsize=12, color="#888888",
            transform=ax.transAxes,
        )
        ax.axis("off")
        return fig

    if palette is None:
        palette = candidate_palette(candidates, generate_palette(len(candidates)))
    color_map: dict[str, str] = dict(zip(candidates, palette))

    BG = "#F7F7F7"
    fig, ax = plt.subplots(figsize=figsize, facecolor=BG)
    ax.set_facecolor(BG)

    for cand in candidates:
        times: list = []
        probs: list[float] = []
        ci_los: list[float] = []
        ci_his: list[float] = []

        for _, row in df.iterrows():
            prob_dict = row[event] if isinstance(row[event], dict) else {}
            if cand not in prob_dict:
                continue

            p: float = float(prob_dict[cand])              # [0, 1]
            n: int = max(1, int(row["n_sim"]))
            if event == "p2v" and row.get("event_contract_version", 1) == 2:
                n = max(1, round(n * float(row["p2t"])))
            half = 1.28 * (p * (1.0 - p) / n) ** 0.5      # 80 % CI half-width

            times.append(row["run_at"])
            probs.append(p * 100.0)
            ci_los.append(max(0.0, (p - half) * 100.0))
            ci_his.append(min(100.0, (p + half) * 100.0))

        if not times:
            continue

        col     = color_map[cand]
        t_arr   = np.array([pd.Timestamp(t) for t in times], dtype="datetime64[ms]")
        p_arr   = np.array(probs)
        lo_arr  = np.array(ci_los)
        hi_arr  = np.array(ci_his)

        ax.fill_between(t_arr, lo_arr, hi_arr, color=col, alpha=0.15, linewidth=0)
        ax.plot(t_arr, p_arr, color=col, linewidth=2.2, label=cand, zorder=3)
        ax.annotate(
            f"{p_arr[-1]:.1f}%",
            xy=(t_arr[-1], p_arr[-1]),
            xytext=(6, 0),
            textcoords="offset points",
            fontsize=8.5,
            color=col,
            va="center",
            fontweight="bold",
        )

    # ── Vertical markers ──────────────────────────────────────────────────────
    if poll_dates is not None:
        for pd_ts in poll_dates:
            ax.axvline(
                pd.Timestamp(pd_ts),
                color="#bbbbbb",
                linestyle="--",
                linewidth=1.0,
                alpha=0.85,
                zorder=2,
            )
            ax.text(
                pd.Timestamp(pd_ts),
                2.5,
                "  nova\n  pesquisa",
                fontsize=6.5,
                color="#aaaaaa",
                va="bottom",
                rotation=90,
            )
    else:
        # Rug: one thin tick per simulation run at the bottom of the plot.
        for ts in df["run_at"].values:
            ax.axvline(
                pd.Timestamp(ts),
                color="#dddddd",
                linewidth=0.7,
                alpha=0.7,
                ymin=0,
                ymax=0.03,
                zorder=2,
            )

    # ── Election date reference ────────────────────────────────────────────────
    if election_date is not None:
        ax.axvline(
            pd.Timestamp(election_date),
            color="#aaaaaa",
            linestyle="--",
            linewidth=1.2,
            alpha=0.7,
            zorder=2,
        )
        ax.text(
            pd.Timestamp(election_date),
            97,
            "  Eleição",
            fontsize=8,
            color="#888888",
            va="top",
        )

    # ── Axes ──────────────────────────────────────────────────────────────────
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=10))
    ax.set_ylabel(labels[event] + " (%)", fontsize=10, color="#555555", labelpad=8)
    ax.set_ylim(bottom=0, top=100)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100, decimals=0))

    ax.grid(axis="y", alpha=0.22, color="#aaaaaa", linewidth=0.8)
    ax.grid(axis="x", visible=False)

    for spine in ("top", "right", "bottom"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#cccccc")
    ax.tick_params(colors="#666666", labelsize=9)

    legend_title = labels[event]
    ax.legend(
        loc="upper left",
        fontsize=9,
        framealpha=0.85,
        edgecolor="#dddddd",
        title=legend_title,
        title_fontsize=8,
    )

    n_runs = len(df)
    fig.suptitle(
        "Evolução da Previsão — Brasil 2026",
        fontsize=13,
        fontweight="bold",
        color="#1a1a2e",
        x=0.03,
        ha="left",
    )
    fig.text(
        0.03, 0.01,
        f"{n_runs} simulações  ·  CI 80% via aprox. binomial  ·  "
        + labels[event],
        fontsize=7.5,
        color="#aaaaaa",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 0.96])
    return fig


# ─── MARGIN HISTOGRAM (standalone) ────────────────────────────────────────────

def plot_margin_histogram(
    margins: np.ndarray,
    thresholds: list[int],
    *,
    figsize: tuple[float, float] = (8, 5),
) -> Figure:
    """Histogram of first-round margin distribution with threshold reference lines.

    Standalone variant of the margin panel in ``plot_simulation_dashboard``, accepting a raw ``np.ndarray`` instead of the full ``df1``. Intended for direct use in Streamlit tabs and for saving independently of the full dashboard figure.

    Args:
        margins:
            Per-simulation first-round margins in percentage points (winner's share minus runner-up's share).  Shape: ``(n_sim,)``. Equivalent to ``SimulationResult.margins``.
        thresholds:
            List of pp thresholds for the P(margin > X) inset table. The value 15 always receives the "← Polymarket" annotation regardless of whether it is in the list.
        figsize:
            Figure size in inches.

    Returns:
        ``matplotlib.figure.Figure``.
    """
    BG = "#F7F7F7"
    fig, ax = plt.subplots(figsize=figsize, facecolor=BG)
    ax.set_facecolor(BG)

    for spine in ax.spines.values():
        spine.set_visible(False)

    m = np.asarray(margins)
    p5  = float(np.percentile(m, 5))
    p50 = float(np.percentile(m, 50))
    p95 = float(np.percentile(m, 95))

    n_bins = min(60, max(20, len(m) // 200))
    ax.hist(m, bins=n_bins, color="#3498db", alpha=0.72, edgecolor="none", zorder=2)
    y_max = ax.get_ylim()[1]

    _REF_LINES = [
        (5,  "#95a5a6", ":",  "5pp"),
        (10, "#f39c12", "--", "10pp"),
        (15, "#e74c3c", "-",  "15pp ← Polymarket"),
    ]
    for x_val, col, ls, label in _REF_LINES:
        ax.axvline(x_val, color=col, ls=ls, lw=1.5, alpha=0.85, zorder=3)
        ax.text(x_val + 0.3, y_max * 0.97, label,
                va="top", ha="left", fontsize=7.5, color=col, alpha=0.90)

    ax.axvline(p50, color="#27ae60", lw=2.0, alpha=0.90, zorder=4)
    ax.text(
        p50 + 0.3, y_max * 0.78,
        f"Mediana\n{p50:.1f}pp",
        va="top", ha="left", fontsize=7.5, color="#1a8a4a", fontweight="bold",
    )

    thr_lines = [
        f"P(>{t:2d}pp): {(m > t).mean() * 100:5.1f}%"
        + ("  ← Polymarket" if t == 15 else "")
        for t in thresholds
    ]
    # Ensure 15pp row is always present in the inset even if absent from thresholds.
    if 15 not in thresholds:
        thr_lines.append(
            f"P(>15pp): {(m > 15).mean() * 100:5.1f}%  ← Polymarket"
        )
    ax.text(
        0.98, 0.97, "\n".join(thr_lines),
        transform=ax.transAxes, ha="right", va="top",
        fontsize=8, family="monospace",
        bbox=dict(boxstyle="round,pad=0.40", facecolor="white",
                  alpha=0.82, edgecolor="#dddddd"),
    )

    ax.set_title(
        f"Distribuição da Margem  ·  1º Turno\n"
        f"IC 90%: [{p5:.1f} – {p95:.1f}pp]  ·  "
        f"Apertada (<3pp): {(m < 3).mean() * 100:.1f}%  ·  "
        f"Confortável (>10pp): {(m > 10).mean() * 100:.1f}%",
        fontsize=10, fontweight="bold", pad=10, loc="left", color="#222222",
    )
    ax.set_xlabel("Margem 1º vs 2º colocado (pp)", fontsize=9, color="#666666", labelpad=6)
    ax.set_ylabel("Frequência", fontsize=9, color="#666666", labelpad=4)
    ax.tick_params(left=False)
    ax.grid(axis="y", alpha=0.18, color="#aaaaaa")
    ax.set_axisbelow(True)

    fig.tight_layout()
    return fig

# ─── VOTE INTENTION (1ST ROUND) ───────────────────────────────────────────────

def plot_vote_intention(
    df1: pd.DataFrame,
    candidates: list[str],
    palette: list[str],
    *,
    figsize: tuple[float, float] = (7, 5),
) -> Figure:
    """Horizontal dot-and-CI chart for first-round vote intentions.

    Args:
        df1:
            Simulation output DataFrame. For each candidate ``c``, expects a
            column ``{c}_val`` (or ``c`` as fallback) containing per-simulation
            valid-vote percentages.
        candidates:
            Ordered list of candidate names (blanks/nulls excluded).
        palette:
            Hex color strings, one per entry in ``candidates``. Must be the same
            length as ``candidates``.
        figsize:
            Figure size in inches.

    Returns:
        ``matplotlib.figure.Figure``.
    """
    BG = "#F7F7F7"
    fig, ax = plt.subplots(figsize=figsize, facecolor=BG)
    ax.set_facecolor(BG)

    cands_plot = list(reversed(candidates))
    color_map = dict(zip(candidates, palette))

    for y, cand in enumerate(cands_plot):
        col = color_map[cand]
        col_v = f"{cand}_val" if f"{cand}_val" in df1.columns else cand
        serie = df1[col_v]

        mean_v = serie.mean()
        ci_lo = serie.quantile(0.05)
        ci_hi = serie.quantile(0.95)

        # CI bar
        ax.plot([ci_lo, ci_hi], [y, y], color=col, lw=3, alpha=0.35, solid_capstyle="round")
        # Mean dot
        ax.scatter([mean_v], [y], color=col, s=110, zorder=5)
        # Mean label
        ax.text(mean_v, y + 0.34, f"{mean_v:.1f}%",
                ha="center", va="bottom", fontsize=9.5, fontweight="bold", color=col)
        # CI bounds (muted)
        ax.text(ci_lo - 0.8, y, f"{ci_lo:.1f}",
                ha="right", va="center", fontsize=7.5, color="#aaaaaa")
        ax.text(ci_hi + 0.8, y, f"{ci_hi:.1f}",
                ha="left", va="center", fontsize=7.5, color="#aaaaaa")

    ax.set_yticks(range(len(cands_plot)))
    ax.set_yticklabels(cands_plot, fontsize=10.5)
    ax.axvline(50, color="#aaaaaa", ls="--", lw=1, alpha=0.5)
    ax.set_xlim(0, 62)
    ax.set_ylim(-0.6, len(cands_plot) - 0.4)
    ax.grid(axis="x", alpha=0.18, color="#aaaaaa")
    ax.set_axisbelow(True)
    ax.set_xlabel("Votos válidos (%)", fontsize=9, color="#666666", labelpad=6)
    ax.set_title(
        "Intenção de Voto  ·  1º Turno\nIC 90% — votos válidos",
        fontsize=11, fontweight="bold", pad=12, loc="left", color="#222222",
    )

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(left=False, bottom=False)

    fig.tight_layout()
    return fig


# ─── REJECTION INDEX ──────────────────────────────────────────────────────────

def plot_rejection_index(
    candidates: list[str],
    rejection: list[float],
    palette: list[str],
    *,
    figsize: tuple[float, float] = (7, 5),
) -> Figure:
    """Horizontal bar chart showing rejection rates and electoral ceilings.

    Args:
        candidates:
            Ordered list of candidate names (blanks/nulls excluded).
        rejection:
            Rejection percentage for each candidate (same order as ``candidates``).
        palette:
            Hex color strings, one per entry in ``candidates``.
        figsize:
            Figure size in inches.

    Returns:
        ``matplotlib.figure.Figure``.
    """
    BG = "#F7F7F7"
    fig, ax = plt.subplots(figsize=figsize, facecolor=BG)
    ax.set_facecolor(BG)

    cands_rej = [c for c, r in zip(candidates, rejection) if r > 0]
    rej_vals = [r for r in rejection if r > 0]
    cands_rev = list(reversed(cands_rej))
    rej_rev = list(reversed(rej_vals))
    color_map = dict(zip(candidates, palette))

    for y, (cand, rej) in enumerate(zip(cands_rev, rej_rev)):
        teto = 100 - rej
        if rej > 50:
            bar_color, status = "#c0392b", "Inviável"
        elif rej > 45:
            bar_color, status = "#e67e22", "Dificuldade alta"
        else:
            bar_color, status = "#27ae60", "Viável"

        ax.barh(y, 72, color="#e8e8e8", height=0.50, zorder=1)
        ax.barh(y, rej, color=bar_color, height=0.50, alpha=0.80, zorder=2)
        ax.text(rej + 1.2, y + 0.13,
                f"{rej:.0f}%  →  teto {teto:.0f}%   {status}",
                ha="left", va="center", fontsize=8.5, color="#333333", fontweight="bold")

    ax.axvline(50, color="#c0392b", ls="--", lw=1.5, alpha=0.65, zorder=5)
    ax.text(50.8, len(cands_rev) - 0.50,
            "Limite crítico\n(50%)", fontsize=7.5, color="#c0392b", va="top")

    ax.set_yticks(range(len(cands_rev)))
    ax.set_yticklabels(cands_rev, fontsize=10.5)
    ax.set_xlim(0, 95)
    ax.set_ylim(-0.55, len(cands_rev) - 0.45)
    ax.grid(axis="x", alpha=0.18, color="#aaaaaa")
    ax.set_axisbelow(True)
    ax.set_xlabel("Rejeição (%)", fontsize=9, color="#666666", labelpad=6)
    ax.set_title(
        "Índice de Rejeição  ·  Teto Eleitoral",
        fontsize=11, fontweight="bold", pad=12, loc="left", color="#222222",
    )

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(left=False, bottom=False)

    fig.tight_layout()
    return fig


# ─── QUALIFY PROBABILITY ──────────────────────────────────────────────────────

def plot_qualify_probability(
    df1: pd.DataFrame,
    candidates: list[str],
    palette: list[str],
    *,
    figsize: tuple[float, float] = (7, 5),
) -> Figure:
    """Horizontal bar chart showing each candidate's probability of reaching the runoff.

    Args:
        df1:
            Simulation output DataFrame. For each candidate ``c``, expects column
            ``{c}_val`` (or ``c`` as fallback) with per-simulation vote percentages.
        candidates:
            Ordered list of candidate names (blanks/nulls excluded).
        palette:
            Hex color strings, one per entry in ``candidates``.
        figsize:
            Figure size in inches.

    Returns:
        ``matplotlib.figure.Figure``.
    """
    BG = "#F7F7F7"
    fig, ax = plt.subplots(figsize=figsize, facecolor=BG)
    ax.set_facecolor(BG)

    val_cols = [f"{c}_val" if f"{c}_val" in df1.columns else c for c in candidates]
    val_matrix = np.column_stack([df1[col].values for col in val_cols])

    # Raw fallback is explicitly normalized over the valid candidate set.
    if not all(f"{c}_val" in df1 for c in candidates):
        val_matrix = val_matrix / val_matrix.sum(axis=1, keepdims=True) * 100
    prob_qualify = eventos_primeiro_turno(val_matrix)["classificacao_2t"].mean(axis=0) * 100

    color_map = dict(zip(candidates, palette))
    cands_rev = list(reversed(candidates))

    for y, cand in enumerate(cands_rev):
        i = candidates.index(cand)
        col = color_map[cand]
        pq = prob_qualify[i]

        ax.barh(y, 100, color="#e8e8e8", height=0.50, zorder=1)
        ax.barh(y, pq, color=col, height=0.50, alpha=0.82, zorder=2)
        ax.text(pq + 1.5, y + 0.13, f"{pq:.1f}%",
                ha="left", va="center", fontsize=10.5, fontweight="bold", color=col)

    ax.axvline(50, color="#aaaaaa", ls="--", lw=1.2, alpha=0.6, zorder=5)
    ax.set_yticks(range(len(cands_rev)))
    ax.set_yticklabels(cands_rev, fontsize=10.5)
    ax.set_ylim(-0.55, len(cands_rev) - 0.45)
    ax.set_xlabel("Probabilidade de classificação (%)", fontsize=9, color="#666666", labelpad=6)
    ax.set_title(
        "Probabilidade de ir ao 2º Turno\n(sem vitória direta; empates dividem vagas)",
        fontsize=11, fontweight="bold", pad=12, loc="left", color="#222222",
    )
    ax.grid(axis="x", alpha=0.18, color="#aaaaaa")
    ax.set_axisbelow(True)

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(left=False, bottom=False)

    fig.tight_layout()
    return fig


# ─── MARGIN DISTRIBUTION ──────────────────────────────────────────────────────

def plot_margin_distribution(
    df1: pd.DataFrame,
    *,
    margin_col: str = "margem_1t",
    margin_thresholds: list[int] = MARGIN_THRESHOLDS,
    figsize: tuple[float, float] = (7, 5),
) -> Figure:
    """Histogram of the first-round margin with reference lines and probability table.

    Args:
        df1:
            Simulation output DataFrame; must contain column ``margin_col``.
        margin_col:
            Name of the column containing the 1st-vs-2nd margin in pp.
        margin_thresholds:
            List of pp thresholds for which P(margin > X) is reported in the inset.
        figsize:
            Figure size in inches.

    Returns:
        ``matplotlib.figure.Figure``.
    """
    BG = "#F7F7F7"
    fig, ax = plt.subplots(figsize=figsize, facecolor=BG)
    ax.set_facecolor(BG)

    m = df1[margin_col]
    p5_m, p50_m, p95_m = m.quantile([0.05, 0.50, 0.95])

    for spine in ax.spines.values():
        spine.set_visible(False)

    n_bins = min(60, max(20, len(m) // 200))
    ax.hist(m, bins=n_bins, color="#3498db", alpha=0.72, edgecolor="none", zorder=2)
    y_max = ax.get_ylim()[1]

    for x_val, col, ls, label in [
        (5,  "#95a5a6", ":",  "5pp"),
        (10, "#f39c12", "--", "10pp"),
        (15, "#e74c3c", "-",  "15pp ← Polymarket"),
    ]:
        ax.axvline(x_val, color=col, ls=ls, lw=1.5, alpha=0.85, zorder=3)
        ax.text(x_val + 0.3, y_max * 0.97, label,
                va="top", ha="left", fontsize=7.5, color=col, alpha=0.90)

    ax.axvline(p50_m, color="#27ae60", lw=2.0, alpha=0.90, zorder=4)
    ax.text(p50_m + 0.3, y_max * 0.78,
            f"Mediana\n{p50_m:.1f}pp",
            va="top", ha="left", fontsize=7.5, color="#1a8a4a", fontweight="bold")

    thr_lines = [
        f"P(>{t:2d}pp): {(m > t).mean() * 100:5.1f}%"
        + ("  ← Polymarket" if t == 15 else "")
        for t in margin_thresholds
    ]
    ax.text(
        0.98, 0.97, "\n".join(thr_lines),
        transform=ax.transAxes, ha="right", va="top",
        fontsize=8, family="monospace",
        bbox=dict(boxstyle="round,pad=0.40", facecolor="white",
                  alpha=0.82, edgecolor="#dddddd"),
    )

    ax.set_title(
        f"Distribuição da Margem  ·  1º Turno\n"
        f"IC 90%: [{p5_m:.1f} – {p95_m:.1f}pp]  ·  "
        f"Apertada (<3pp): {(m < 3).mean() * 100:.1f}%  ·  "
        f"Confortável (>10pp): {(m > 10).mean() * 100:.1f}%",
        fontsize=10, fontweight="bold", pad=10, loc="left", color="#222222",
    )
    ax.set_xlabel("Margem 1º vs 2º colocado (pp)", fontsize=9, color="#666666", labelpad=6)
    ax.set_ylabel("Frequência", fontsize=9, color="#666666", labelpad=4)
    ax.tick_params(left=False)
    ax.grid(axis="y", alpha=0.18, color="#aaaaaa")
    ax.set_axisbelow(True)

    fig.tight_layout()
    return fig


# ─── COMBINED DASHBOARD FIGURE ────────────────────────────────────────────────

def plot_simulation_dashboard(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    candidates: list[str],
    rejection: list[float],
    palette: list[str],
    *,
    n_sim: int = 40_000,
    desvio: float = 0.0,
    election_date: Optional[date] = None,
    margin_thresholds: list[int] = MARGIN_THRESHOLDS,
    figsize: tuple[float, float] = (16, 10),
    as_of: Optional[date] = None,
    nota: Optional[str] = None,
) -> Figure:
    """First-round forecast figure: headline tiles, vote shares and the lead.

    Layout:
        Header: election, poll cut-off date, election date, simulations.
        Tiles: chance of being elected (or of leading, without runoff data)
            for the two contenders, chance of a runoff, and the conditional
            runoff result.
        Left: valid-vote share per candidate (median, 50% and 90% ranges);
            rejection ceilings as ticks when measured.
        Right: distribution of the gap between the two contenders.

    The two contenders (highest mean share) keep their identity colors from
    ``palette``; every other candidate is drawn in neutral gray.

    Args:
        df1: First-round simulation DataFrame (``<cand>_val`` columns).
        df2: Runoff rows of the dynamic simulation; empty for first round only.
        candidates: Candidate names (blank/null excluded).
        rejection: Rejection % per candidate (0 = not measured).
        palette: One identity color per candidate.
        n_sim: Number of simulations (subtitle).
        desvio: Kept for compatibility; not displayed (the sd of the polling
            average understates the forecast uncertainty).
        election_date: Election day.
        margin_thresholds: Kept for compatibility.
        figsize: Figure size in inches.
        as_of: Poll cut-off date shown in the subtitle.
        nota: Footer text (model parameters); a generic note when omitted.

    Returns:
        ``matplotlib.figure.Figure``.
    """
    from src.viz import tema  # noqa: PLC0415

    val = _matriz_validos(df1, candidates)
    eventos = eventos_primeiro_turno(val)
    p_lider = eventos["lideranca"].mean(axis=0) * 100
    p_vit1 = eventos["vitoria_1t"].mean(axis=0) * 100
    p2t = float(eventos["segundo_turno"].mean()) * 100
    p_cond: dict[str, float] = {}
    if df2 is not None and not df2.empty:
        try:
            p_cond = {c: p * 100 for c, p in probabilidades_vitoria_2t(df2, candidates).items()}
        except ValueError:
            p_cond = {}

    ordem = list(np.argsort(-val.mean(axis=0), kind="stable"))
    i_a, i_b = int(ordem[0]), int(ordem[1])
    cand_a, cand_b = candidates[i_a], candidates[i_b]
    cor = {c: (palette[i] if i in (i_a, i_b) else tema.NEUTRO)
           for i, c in enumerate(candidates)}

    with tema.estilo():
        fig = plt.figure(figsize=figsize)
        ano = election_date.year if election_date else ""
        partes = []
        if as_of is not None:
            partes.append(f"Previsão com pesquisas até {tema.data_br(as_of)}")
        if election_date is not None:
            partes.append(f"votação em {tema.data_br(election_date)}")
        partes.append(f"{tema.inteiro(n_sim)} simulações")
        sub = " · ".join(partes)
        tema.cabecalho(fig, f"Eleição presidencial {ano} · 1º turno".replace("  ", " "),
                       sub[0].upper() + sub[1:])

        # ── Tiles ──────────────────────────────────────────────────────────────
        x0, gap, y, h = 0.04, 0.012, 0.735, 0.145
        w = (0.92 - 3 * gap) / 4
        xs = [x0 + k * (w + gap) for k in range(4)]
        for x, i in zip(xs[:2], (i_a, i_b)):
            c = candidates[i]
            if p_cond:
                eleito = p_vit1[i] + p2t / 100 * p_cond.get(c, 0.0)
                tema.cartao(fig, x, y, w, h, f"{c} · chance de ser eleito",
                            tema.prob_curta(eleito),
                            f"lidera o 1º turno em {tema.prob_curta(p_lider[i])} das simulações",
                            cor=cor[c])
            else:
                tema.cartao(fig, x, y, w, h, f"{c} · lidera o 1º turno",
                            tema.prob_curta(p_lider[i]),
                            f"vence já no 1º turno: {tema.pct(p_vit1[i])}", cor=cor[c])
        tema.cartao(fig, xs[2], y, w, h, "Haverá 2º turno", tema.prob_curta(p2t),
                    f"vitória no 1º turno: {cand_a} {tema.pct(p_vit1[i_a])}"
                    f" · {cand_b} {tema.pct(p_vit1[i_b])}")
        if p_cond:
            fav = max(p_cond, key=p_cond.get)
            outros = ", ".join(f"{c} {tema.prob_curta(p)}" for c, p in
                               sorted(p_cond.items(), key=lambda kv: -kv[1]) if c != fav and p >= 0.5)
            tema.cartao(fig, xs[3], y, w, h, "Se houver 2º turno, vence",
                        f"{fav} {tema.prob_curta(p_cond[fav])}", outros, cor=cor.get(fav))
        else:
            dif = val[:, i_a] - val[:, i_b]
            tema.cartao(fig, xs[3], y, w, h, f"Vantagem de {cand_a}",
                        f"{tema.num(float(np.median(dif)))} pp",
                        f"90% das simulações: {tema.num(np.quantile(dif, .05))} a "
                        f"{tema.num(np.quantile(dif, .95))} pp")

        # ── Left: vote shares ──────────────────────────────────────────────────
        ax = fig.add_axes([0.15, 0.09, 0.40, 0.52])
        _painel_votos(ax, val, candidates, ordem, cor, rejection, (i_a, i_b))

        # ── Right: gap between the contenders ──────────────────────────────────
        ax2 = fig.add_axes([0.62, 0.09, 0.34, 0.52])
        _painel_diferenca(ax2, val[:, i_a] - val[:, i_b], cand_a, cand_b,
                          cor[cand_a], cor[cand_b], n_sim)

        tema.rodape(fig, nota or ("Simulações Monte Carlo a partir da média das pesquisas"
                                  " · não é previsão oficial"))
        fig.canvas.draw()  # create tick labels while the local style is active
    return fig


# ─── PRIVATE RENDER HELPERS ───────────────────────────────────────────────────

def _matriz_validos(df1: pd.DataFrame, candidates: list[str]) -> np.ndarray:
    """Valid-vote shares (rows sum to 100) in ``candidates`` order."""
    cols = [f"{c}_val" if f"{c}_val" in df1.columns else c for c in candidates]
    m = df1[cols].to_numpy(dtype=float)
    if not all(f"{c}_val" in df1.columns for c in candidates):
        m = m / m.sum(axis=1, keepdims=True) * 100
    return m


def _painel_votos(
    ax: plt.Axes, val: np.ndarray, candidates: list[str], ordem: list[int],
    cor: dict[str, str], rejection: list[float], destaque: tuple[int, int],
) -> None:
    from src.viz import tema  # noqa: PLC0415

    q = np.quantile(val, [0.05, 0.25, 0.5, 0.75, 0.95], axis=0)
    tetos = [100 - r if r and r > 0 else None for r in rejection] if rejection else []
    x_max = max(55.0, float(q[4].max()) + 14)
    if any(t is not None for t in tetos):
        x_max = max(x_max, max(t for t in tetos if t is not None) + 6)

    n = len(ordem)
    for linha, i in enumerate(ordem):
        yy = n - 1 - linha
        c = candidates[i]
        forte = i in destaque
        ax.plot([q[0, i], q[4, i]], [yy, yy], color=cor[c], lw=2, zorder=2,
                solid_capstyle="round")
        ax.plot([q[1, i], q[3, i]], [yy, yy], color=cor[c], lw=7, zorder=2,
                solid_capstyle="round")
        ax.scatter([q[2, i]], [yy], s=110 if forte else 70, color=cor[c],
                   edgecolors=tema.SUPERFICIE, linewidths=2, zorder=3)
        ax.annotate(f"{tema.pct(q[2, i])}", (q[4, i], yy), xytext=(8, 1),
                    textcoords="offset points", va="center", fontsize=12, zorder=4,
                    bbox=dict(boxstyle="square,pad=0.1", fc=tema.SUPERFICIE, ec="none"),
                    fontweight="bold" if forte else "normal",
                    color=tema.TINTA if forte else tema.TINTA_2)
        ax.annotate(f"{tema.num(q[0, i])}–{tema.num(q[4, i])}", (q[4, i], yy),
                    xytext=(8, -15), textcoords="offset points", va="center",
                    fontsize=9.5, color=tema.TINTA_MUDA, zorder=4,
                    bbox=dict(boxstyle="square,pad=0.1", fc=tema.SUPERFICIE, ec="none"))
        if tetos and tetos[i] is not None:
            ax.plot([tetos[i]] * 2, [yy - 0.28, yy + 0.28], color=tema.TINTA_2, lw=1.5)
            ax.annotate("teto", (tetos[i], yy + 0.28), xytext=(0, 2),
                        textcoords="offset points", ha="center", va="bottom",
                        fontsize=8.5, color=tema.TINTA_MUDA)

    ax.axvline(50, color=tema.EIXO, ls=(0, (4, 3)), lw=1.2, zorder=1)
    ax.annotate("50%: vence no 1º turno", (50, n - 0.45), xytext=(4, 0),
                textcoords="offset points", fontsize=9.5, color=tema.TINTA_MUDA,
                va="bottom")
    ax.set_yticks(range(n))
    nomes = [candidates[i] for i in reversed(ordem)]
    ax.set_yticklabels(nomes, fontsize=12.5, color=tema.TINTA)
    for rot, i in zip(ax.get_yticklabels(), reversed(ordem)):
        if i in destaque:
            rot.set_fontweight("bold")
    ax.set_ylim(-0.7, n - 0.2)
    ax.set_xlim(0, x_max)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    tema.eixo_limpo(ax)
    tema.titulo_painel(ax, "Votos válidos no 1º turno",
                       "Ponto: mediana · barra grossa: 50% das simulações · linha: 90%")


def _painel_diferenca(
    ax: plt.Axes, dif: np.ndarray, cand_a: str, cand_b: str,
    cor_a: str, cor_b: str, n_sim: int,
) -> None:
    from src.viz import tema  # noqa: PLC0415

    lo, hi = np.quantile(dif, [0.002, 0.998])
    largura = max(0.25, round((hi - lo) / 70 * 4) / 4)
    inicio = np.floor(lo / largura) * largura
    bins = np.arange(inicio, hi + largura, largura)
    if bins.size < 2:  # degenerate draws (identical differences)
        bins = np.array([inicio - largura, inicio + largura])
    a_frente = dif > 0
    ax.hist(dif[a_frente], bins=bins, color=cor_a, edgecolor=tema.SUPERFICIE, lw=0.6)
    ax.hist(dif[~a_frente], bins=bins, color=cor_b, edgecolor=tema.SUPERFICIE, lw=0.6)
    ax.axvline(0, color=tema.TINTA_2, lw=1.2)
    ax.set_yticks([])
    ax.set_xlim(bins[0], bins[-1])
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"{v:+.0f}".replace("+0", "0").replace("-", "−")))
    ax.set_xlabel("pontos percentuais dos votos válidos", fontsize=10.5)
    tema.eixo_limpo(ax, grade_x=False)
    ax.text(0.02, 0.95, f"{cand_b} à frente\n{tema.pct(100 * (~a_frente).mean())}",
            transform=ax.transAxes, ha="left", va="top", fontsize=12, color=tema.TINTA,
            linespacing=1.4)
    ax.text(0.98, 0.95, f"{cand_a} à frente\n{tema.pct(100 * a_frente.mean())}",
            transform=ax.transAxes, ha="right", va="top", fontsize=12, color=tema.TINTA,
            linespacing=1.4)
    tema.titulo_painel(ax, f"Diferença {cand_a} − {cand_b}",
                       f"No 1º turno, em {tema.inteiro(n_sim)} simulações")

# ─── CLI / REPORT ENTRY POINT ─────────────────────────────────────────────────

def generate_charts(
    result: "SimulationResult",
    *,
    output_dir: Path = Path("outputs"),
) -> dict[str, Path]:
    """Generate all standard output figures for a completed simulation run.

    Called by ``src.cli._handle_run()`` at stage 4. Saves the full dashboard PNG and the standalone margin histogram to ``output_dir``.

    This is the only function in ``src/viz/`` that writes to disk; all other functions return ``Figure`` objects and leave I/O to the caller.

    Args:
        result:
            Completed ``SimulationResult`` from ``src.core.simulation``.
        output_dir:
            Directory for output files.  Created if absent.

    Returns:
        Dict mapping ``"dashboard"`` and ``"margin"`` to their ``Path`` objects.
    """
    # Import here to avoid a circular dependency at module load time.
    from src.core.config import SimulationResult as _SR  # noqa: PLC0415

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Reconstruct palette and candidate list from df1 columns.
    val_cols = [c for c in result.df1.columns if c.endswith("_val")]
    candidates = [c.removesuffix("_val") for c in val_cols]
    if not candidates:
        candidates = [c for c in result.df1.columns
                      if c not in ("winner", "vencedor", "tem_2turno",
                                   "margem_1t", "abstencao_1t_pct",
                                   "votos_validos_1t", "comparecimento_1t",
                                   "invalidos_1t_pct", "votos_invalidos_1t",
                                   "lider_1t", "vencedor_1t",
                                   "event_contract_version")
                      and not c.startswith(("evento_", "margem_"))
                      and not c.endswith("_abs")]
    palette = candidate_palette(
        candidates, generate_palette(len(candidates))
    )

    rejection: list[float] = []
    if result.config is not None:
        # PollData is not stored in SimulationResult; reconstruct rejection
        # from df1 column names if the config is available.
        pass  # populated below via poll_data when available
    rejection = [0.0] * len(candidates)  # fallback — no rejection data in result

    election_date = (
        result.config.election_date if result.config else None
    )
    n_sim = result.config.n_sim if result.config else len(result.df1)

    saved: dict[str, Path] = {}

    # ── Full dashboard figure ─────────────────────────────────────────────────
    cfg = result.config
    nota = None
    if cfg is not None:
        from src.viz import tema  # noqa: PLC0415
        nota = (f"Erro comum das pesquisas: {tema.num(cfg.sd_erro_comum_pp)} pp"
                f" (t, ν = {cfg.gl_erro_comum:g}) · deriva {tema.num(cfg.sd_deriva_30d_pp)} pp"
                " por 30 dias · efeitos de instituto"
                f"{'' if cfg.efeitos_instituto else ' desligados'}"
                " · brazil-election-montecarlo · não é previsão oficial")
    fig_dash = plot_simulation_dashboard(
        df1=result.df1,
        df2=result.df2,
        candidates=candidates,
        rejection=rejection,
        palette=palette,
        n_sim=n_sim,
        desvio=result.desvio_base,
        election_date=election_date,
        as_of=cfg.as_of if cfg is not None else None,
        nota=nota,
    )
    dash_path = output_dir / "simulacao_brasil_2026.png"
    fig_dash.savefig(dash_path, dpi=200, bbox_inches="tight", facecolor=fig_dash.get_facecolor())
    plt.close(fig_dash)
    saved["dashboard"] = dash_path

    # ── Standalone margin histogram ───────────────────────────────────────────
    if result.margins is not None and len(result.margins) > 0:
        fig_margin = plot_margin_histogram(result.margins, MARGIN_THRESHOLDS)
        margin_path = output_dir / "margem_1turno.png"
        fig_margin.savefig(margin_path, dpi=200, bbox_inches="tight",
                           facecolor="#F7F7F7")
        plt.close(fig_margin)
        saved["margin"] = margin_path

    return saved