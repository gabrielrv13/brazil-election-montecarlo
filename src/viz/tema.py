"""
Shared look of the published figures (first-round and runoff panels).

Colors follow the candidate, never the rank: the two 2026 finalists keep a
validated blue/red pair (CVD-safe, >= 3:1 on the surface) and every other
candidate is drawn in a neutral gray, so attention goes to the contenders.
Text is always in ink tokens, never in a series color; a small colored
swatch next to a name carries the identity.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from functools import lru_cache
from typing import Iterator

from matplotlib import font_manager
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch, Rectangle
import matplotlib.pyplot as plt

# ── Tokens ────────────────────────────────────────────────────────────────────
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_MUDA = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"
CARTAO = "#f3f2ee"
NEUTRO = "#b4b2aa"          # candidates outside the contest

AZUL = "#2a78d6"
VERMELHO = "#e34948"
# Ordinal ramps (dark -> light), validated with the dataviz ordinal checks.
RAMPA = {
    AZUL: ("#1c5cab", "#3987e5", "#86b6ef"),
    VERMELHO: ("#b3302f", "#e34948", "#f09c9b"),
}


@lru_cache(maxsize=1)
def _familia() -> str:
    """System UI sans when available (Windows), else matplotlib's default."""
    disponiveis = {f.name for f in font_manager.fontManager.ttflist}
    for nome in ("Segoe UI", "Inter", "Helvetica Neue", "Arial"):
        if nome in disponiveis:
            return nome
    return "DejaVu Sans"


@contextmanager
def estilo() -> Iterator[None]:
    """Local rcParams for one figure (never mutates the global state)."""
    with plt.rc_context({
        "font.family": _familia(),
        "figure.facecolor": SUPERFICIE,
        "axes.facecolor": SUPERFICIE,
        "axes.edgecolor": EIXO,
        "axes.labelcolor": TINTA_2,
        "xtick.color": TINTA_MUDA,
        "ytick.color": TINTA_2,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "savefig.facecolor": SUPERFICIE,
    }):
        yield


# ── Formatting (pt-BR) ────────────────────────────────────────────────────────

def num(x: float, casas: int = 1) -> str:
    """Decimal comma: 44.6 -> '44,6'."""
    return f"{x:.{casas}f}".replace(".", ",")


def pct(x: float, casas: int = 1) -> str:
    return f"{num(x, casas)}%"


def inteiro(n: int) -> str:
    """Thousands with a dot: 40000 -> '40.000'."""
    return f"{n:,}".replace(",", ".")


def data_br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def prob_curta(p: float) -> str:
    """Probability in % for headlines: no false precision at the tails."""
    if p >= 99.5:
        return ">99%"
    if p < 0.5:
        return "<1%"
    return f"{p:.0f}%"


# ── Building blocks ───────────────────────────────────────────────────────────

def cabecalho(fig: Figure, titulo: str, subtitulo: str, x: float = 0.04) -> None:
    fig.text(x, 0.955, titulo, fontsize=24, fontweight="bold", color=TINTA, va="bottom")
    fig.text(x, 0.925, subtitulo, fontsize=12, color=TINTA_2, va="bottom")


def rodape(fig: Figure, texto: str, x: float = 0.04) -> None:
    fig.text(x, 0.018, texto, fontsize=9, color=TINTA_MUDA, va="bottom")


def cartao(
    fig: Figure, x: float, y: float, w: float, h: float,
    rotulo: str, valor: str, detalhe: str = "", cor: str | None = None,
) -> None:
    """Stat tile: label (with an optional identity swatch), hero value, detail."""
    fig.add_artist(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0,rounding_size=0.008",
        transform=fig.transFigure, facecolor=CARTAO, edgecolor="none", zorder=0))
    tx = x + 0.014
    if cor is not None:
        fig.add_artist(Rectangle(
            (tx, y + h - 0.040), 0.009, 0.016, transform=fig.transFigure,
            facecolor=cor, edgecolor="none"))
        tx_rot = tx + 0.015
    else:
        tx_rot = tx
    fig.text(tx_rot, y + h - 0.032, rotulo, fontsize=11.5, color=TINTA_2, va="center")
    fig.text(tx, y + h * 0.38, valor, fontsize=30, fontweight="bold", color=TINTA,
             va="center")
    if detalhe:
        fig.text(tx, y + 0.022, detalhe, fontsize=10, color=TINTA_MUDA, va="center")


def titulo_painel(ax: plt.Axes, texto: str, sub: str = "") -> None:
    ax.set_title(texto, loc="left", fontsize=14, fontweight="bold", color=TINTA,
                 pad=28 if sub else 12)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=10.5, color=TINTA_2,
                va="bottom", ha="left")


def eixo_limpo(ax: plt.Axes, grade_x: bool = True) -> None:
    ax.tick_params(length=0, labelsize=10.5)
    ax.spines["bottom"].set_color(EIXO)
    if grade_x:
        ax.grid(axis="x", color=GRADE, lw=0.8)
    ax.set_axisbelow(True)
