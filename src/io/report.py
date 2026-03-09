"""
src/io/report.py
================
CSV and PDF report generation from SimulationResult.

This is the only module that writes output files to disk.
All data is sourced exclusively from SimulationResult — no globals,
no direct imports from simulation_v2.

Public API
----------
    save_csvs(result, output_dir) -> tuple[Path, Path | None]
    generate_pdf(result, output_dir) -> Path
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.core.config import SimulationResult

logger = logging.getLogger(__name__)

_MARGIN_THRESHOLDS: list[int] = [5, 10, 15, 20, 25]

# Columns that are metadata, not per-candidate vote shares, in df1
_DF1_META_COLS: frozenset[str] = frozenset([
    "vencedor", "tem_2turno", "abstencao_1t_pct", "votos_validos_1t",
    "margem_1t", "lider_1t",
])


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _candidate_columns(df1: pd.DataFrame) -> list[str]:
    """
    Extracts the list of candidate names from df1's columns.

    Returns only the base vote-share columns — excludes metadata,
    _val, _abs, and margem_ variants.
    """
    return [
        c for c in df1.columns
        if c not in _DF1_META_COLS
        and not c.endswith("_val")
        and not c.endswith("_abs")
        and not c.startswith("margem_")
    ]


def _iso_timestamp(result: SimulationResult) -> str:
    """Formats result.timestamp as a filesystem-safe ISO 8601 string."""
    return result.timestamp.strftime("%Y-%m-%dT%H-%M-%S")


# ─── CSV OUTPUTS ──────────────────────────────────────────────────────────────

def save_csvs(
    result: SimulationResult,
    output_dir: Path,
) -> tuple[Path, Path | None]:
    """
    Saves first-round and second-round DataFrames to CSV.

    Filenames use an ISO 8601 timestamp from result.timestamp.
    No version number is embedded in the filename.

    Args:
        result:     Completed SimulationResult.
        output_dir: Directory to write files into (created if absent).

    Returns:
        (path_1t, path_2t) where path_2t is None when result.df2 is empty.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = _iso_timestamp(result)

    path_1t = output_dir / f"{ts}_resultados_1turno.csv"
    result.df1.to_csv(path_1t, index=False)
    logger.info("First-round CSV saved: %s", path_1t)

    path_2t: Path | None = None
    if not result.df2.empty:
        path_2t = output_dir / f"{ts}_resultados_2turno.csv"
        result.df2.to_csv(path_2t, index=False)
        logger.info("Second-round CSV saved: %s", path_2t)

    return path_1t, path_2t


# ─── PDF REPORT ───────────────────────────────────────────────────────────────

def _build_table_style() -> "TableStyle":
    """Returns the shared ReportLab TableStyle for all data tables."""
    from reportlab.lib import colors
    from reportlab.platypus import TableStyle

    return TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f4f8")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("ALIGN",         (1, 0), (-1, -1), "RIGHT"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])


def _section_undecided(result: SimulationResult, styles: dict) -> list:
    """Builds the undecided voters section of the PDF story."""
    from reportlab.platypus import Paragraph, Spacer, Table
    from reportlab.lib.units import cm

    if not result.info_indecisos:
        return []

    info = result.info_indecisos
    rows = [
        ["Metric", "Value"],
        ["Total undecided",
         f"{info.get('indecisos_total', 0):.2f}%"],
        ["Redistributed to candidates",
         f"{info.get('indecisos_redistribuiveis', 0):.2f}%"],
        ["Allocated to blank/null",
         f"{info.get('indecisos_para_brancos', 0):.2f}%"],
        ["Blank fraction",
         f"{info.get('blank_fraction', 0) * 100:.0f}%"],
    ]
    t = Table(rows, colWidths=[9 * cm, 4 * cm])
    t.setStyle(_build_table_style())
    return [
        Paragraph("Undecided Voters", styles["h2"]),
        t,
        Spacer(1, 0.3 * cm),
    ]


def _section_first_round(result: SimulationResult, styles: dict) -> list:
    """Builds the first-round vote projections section."""
    from reportlab.platypus import Paragraph, Spacer, Table
    from reportlab.lib.units import cm

    story = [Paragraph("First Round — Vote Projections", styles["h2"])]

    candidatos = list(result.pv.keys()) if result.pv else _candidate_columns(result.df1)

    rows = [["Candidate", "Mean (%)", "P5 (%)", "P95 (%)", "P(1st-round win)"]]
    for cand in candidatos:
        if cand not in result.df1.columns:
            continue
        serie = result.df1[cand]
        p5, p95 = serie.quantile([0.05, 0.95])
        pwin = (
            f"{result.pv[cand] * 100:.1f}%"
            if result.pv and cand in result.pv
            else "—"
        )
        rows.append([cand, f"{serie.mean():.2f}", f"{p5:.2f}", f"{p95:.2f}", pwin])

    t = Table(rows, colWidths=[5 * cm, 3 * cm, 2.5 * cm, 2.5 * cm, 4 * cm])
    t.setStyle(_build_table_style())
    story.append(t)

    # First-round margin sub-section
    if "margem_1t" in result.df1.columns:
        m = result.df1["margem_1t"]
        p5_m, p50_m, p95_m = m.quantile([0.05, 0.50, 0.95])
        margin_rows = [
            ["Metric", "Value"],
            ["Median margin (1st vs 2nd)", f"{p50_m:.1f} pp"],
            ["90% CI", f"[{p5_m:.1f} – {p95_m:.1f}] pp"],
            ["P(close race < 3pp)", f"{(m < 3).mean() * 100:.1f}%"],
            ["P(comfortable > 10pp)", f"{(m > 10).mean() * 100:.1f}%"],
        ]
        for thr in _MARGIN_THRESHOLDS:
            marker = "  ← Polymarket market" if thr == 15 else ""
            margin_rows.append([
                f"P(margin > {thr}pp){marker}",
                f"{(m > thr).mean() * 100:.1f}%",
            ])
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("First-Round Margin Analysis", styles["h2"]))
        tm = Table(margin_rows, colWidths=[9 * cm, 4 * cm])
        tm.setStyle(_build_table_style())
        story.append(tm)

    story.append(Spacer(1, 0.3 * cm))
    return story


def _section_second_round(result: SimulationResult, styles: dict) -> list:
    """Builds the second-round matchup section."""
    from reportlab.platypus import Paragraph, Spacer, Table
    from reportlab.lib.units import cm

    if result.df2.empty or not result.info_matchups:
        return []

    story = [Paragraph("Second Round — Matchup Probabilities", styles["h2"])]

    rows_2t = [["Matchup", "Probability", "Cand A win", "Cand B win"]]
    for matchup, info in sorted(
        result.info_matchups.items(),
        key=lambda x: x[1]["prob_matchup"],
        reverse=True,
    ):
        rows_2t.append([
            matchup,
            f"{info['prob_matchup']:.1f}%",
            f"{info['cand_a']}: {info['prob_a']:.1f}%",
            f"{info['cand_b']}: {info['prob_b']:.1f}%",
        ])

    t2 = Table(rows_2t, colWidths=[6 * cm, 3 * cm, 4 * cm, 4 * cm])
    t2.setStyle(_build_table_style())
    story.append(t2)

    if result.p2v:
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Overall Second-Round Victory Probability", styles["h2"]))
        rows_p2v = [["Candidate", "P(2nd-round win)"]]
        for cand, prob in sorted(result.p2v.items(), key=lambda x: x[1], reverse=True):
            rows_p2v.append([cand, f"{prob * 100:.2f}%"])
        tp2v = Table(rows_p2v, colWidths=[9 * cm, 4 * cm])
        tp2v.setStyle(_build_table_style())
        story.append(tp2v)

    story.append(Spacer(1, 0.3 * cm))
    return story


def generate_pdf(result: SimulationResult, output_dir: Path) -> Path:
    """
    Generates a PDF summary report from a SimulationResult.

    Uses ReportLab Platypus for layout. No globals are read — all
    data comes from result.

    Sections produced:
        - Run metadata (timestamp, n_sim, election_date)
        - Undecided voters (if result.info_indecisos is populated)
        - First-round vote projections with 90% CI
        - First-round margin analysis (if margem_1t column present)
        - Second-round matchup probabilities (if result.df2 is non-empty)
        - Overall second-round victory probabilities

    Args:
        result:     Completed SimulationResult.
        output_dir: Directory to write the PDF into (created if absent).

    Returns:
        Path to the generated PDF file.

    Raises:
        ImportError: If reportlab is not installed.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, Spacer, SimpleDocTemplate
    except ImportError as exc:
        raise ImportError(
            "reportlab is required for PDF generation: pip install reportlab"
        ) from exc

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = _iso_timestamp(result)
    out_path = output_dir / f"{ts}_relatorio.pdf"

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Brazil 2026 Election Forecast",
        author="brazil-election-montecarlo",
    )

    _base = getSampleStyleSheet()
    _styles = {
        "title": ParagraphStyle(
            "ReportTitle", parent=_base["Title"], fontSize=18, spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "H2", parent=_base["Heading2"], fontSize=12,
            spaceAfter=4, spaceBefore=12,
        ),
        "small": ParagraphStyle(
            "Small", parent=_base["Normal"], fontSize=8,
            textColor=colors.HexColor("#888888"),
        ),
    }

    n_sim = result.config.n_sim if result.config else len(result.df1)
    election_date = (
        result.config.election_date.strftime("%Y-%m-%d")
        if result.config else "2026-10-04"
    )

    story: list = []
    story.append(Paragraph("Brazil 2026 — Election Forecast", _styles["title"]))
    story.append(Paragraph(
        f"Generated: {result.timestamp.strftime('%Y-%m-%d %H:%M')}  ·  "
        f"Simulations: {n_sim:,}  ·  Election date: {election_date}",
        _styles["small"],
    ))
    story.append(Spacer(1, 0.4 * cm))

    story.extend(_section_undecided(result, _styles))
    story.extend(_section_first_round(result, _styles))
    story.extend(_section_second_round(result, _styles))

    story.append(Paragraph(
        "brazil-election-montecarlo · Monte Carlo simulation · "
        "github.com/gabrielrv13/brazil-election-montecarlo",
        _styles["small"],
    ))

    doc.build(story)
    logger.info("PDF report saved: %s", out_path)
    return out_path