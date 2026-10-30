"""
src/io/loader.py
================
Poll CSV loading with schema validation and aggregation.

This is the ONLY module that reads pesquisas.csv from disk.
No function outside src/io/ should call open() or pd.read_csv() on poll data.

Public API
----------
    load_polls(config: SimulationConfig) -> PollData
        Primary interface. Reads the CSV path defined in config.

    carregar_pesquisas(csv_path=None) -> PollData
        Backward-compatible wrapper that accepts an optional path string/Path.
        Preserves the call signature used by simulation_v2.py and dashboard.py.

"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.core.config import PollData, SimulationConfig

logger = logging.getLogger(__name__)

# Required columns that must exist in every poll CSV.
_REQUIRED_COLUMNS: list[str] = [
    "candidato",
    "intencao_voto_pct",
    "desvio_padrao_pct",
]


# ─── PRIVATE AGGREGATION HELPERS ──────────────────────────────────────────────
# These are pure functions (no I/O, no globals).  They live here temporarily
# until src/core/aggregation.py is created by the Core Architect.

from src.core.aggregation import (
    calcular_peso_temporal as _calcular_peso_temporal,
    detectar_outliers as _detectar_outliers,
    agregar_pesquisas_candidato as _agregar_pesquisas_candidato,
)


def _validate_schema(df: pd.DataFrame, csv_path: Path) -> None:
    """
    Validates required columns and numeric constraints on the raw DataFrame.

    Called once after pd.read_csv(), before any aggregation logic.

    Args:
        df:       Raw DataFrame as loaded from disk.
        csv_path: Path used only for error messages.

    Raises:
        ValueError: Missing required column — message includes column name.
        ValueError: Non-numeric dtype in a numeric column — message includes
                    column name and offending candidates.
        ValueError: Value <= 0 in a numeric column — message includes column
                    name and offending candidates.
        ValueError: NaN in a numeric column — message includes column name
                    and offending candidates.
    """
    # ── Task 2: required columns ──────────────────────────────────────────────
    for col in _REQUIRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(
                f"Required column '{col}' is missing from {csv_path}. "
                f"Present columns: {list(df.columns)}"
            )

    # ── Task 3: float > 0 per candidate ──────────────────────────────────────
    for col in ("rejeicao_pct", "indecisos_pct"):
        if col in df:
            values = pd.to_numeric(df[col], errors="coerce")
            bad = ~np.isfinite(values) | ~values.between(0, 100)
            if bad.any():
                raise ValueError(f"Invalid {col} at CSV lines {(df.index[bad] + 2).tolist()}")
            df[col] = values

    for col in ("intencao_voto_pct", "desvio_padrao_pct"):
        # Guard: non-numeric dtype (e.g. column contains strings)
        if not pd.api.types.is_numeric_dtype(df[col]):
            values = pd.to_numeric(df[col], errors="coerce")
            bad = df[values.isna()]["candidato"].unique()
            if len(bad):
                raise ValueError(
                    f"Column '{col}' must be numeric. "
                    f"Non-numeric values found for candidates: {list(bad)}"
                )
            df[col] = values

        nan_mask = ~np.isfinite(df[col])
        if nan_mask.any():
            bad = df[nan_mask]["candidato"].unique()
            raise ValueError(
                f"Column '{col}' has NaN for candidates: {list(bad)}. "
                f"All rows in {csv_path} must have a numeric value."
            )

        if col == "intencao_voto_pct":
            invalid_values = df[(df[col] < 0) | (df[col] > 100)]["candidato"].unique()
            requirement = ">= 0"
        else:
            invalid_values = df[df[col] <= 0]["candidato"].unique()
            requirement = "> 0"
        if len(invalid_values) > 0:
            raise ValueError(
                f"Column '{col}' must be {requirement} for all rows. "
                f"Candidates with invalid values: {list(invalid_values)}"
            )

# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def load_polls(config: SimulationConfig) -> PollData:
    """
    Loads, validates, and aggregates poll data for a simulation run.

    This is the canonical entry point.  Use carregar_pesquisas() only when
    calling code predates SimulationConfig (e.g. dashboard.py during migration).

    Args:
        config: SimulationConfig whose csv_path determines the data source.

    Returns:
        PollData dataclass with aggregated vote shares, rejection rates,
        base standard deviation, and undecided voter share.

    Raises:
        FileNotFoundError: If config.csv_path does not exist.
        ValueError:        If required columns are absent, or numeric constraints
                           are violated. The message names the offending column
                           or candidate for easy debugging.
    """
    csv_path = config.csv_path

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Poll CSV not found: {csv_path}. "
            "Check SimulationConfig.csv_path or the --csv flag."
        )

    df = pd.read_csv(csv_path, dtype={"pesquisa_id": str, "cenario": str})

    from src.core.poll_quality import select_scenario, validate_dates, validate_identity
    data_referencia = config.as_of if config.as_of is not None else date.today()
    df = select_scenario(df, config.scenario)
    _validate_schema(df, csv_path)
    df = validate_dates(df, data_referencia, str(csv_path))
    keys = validate_identity(df)
    # The CSV is one declared simulation scenario; different scenarios must be
    # selected upstream, never pooled into one simulation.
    required = set(config.required_candidates or df["candidato"].unique())
    if keys:
        for key, group in df.groupby(keys, dropna=False):
            missing = required - set(group["candidato"])
            if missing:
                raise ValueError(f"Incomplete poll {key}: missing {sorted(missing)}")

    if config.required_candidates is not None:
        df = df[df["candidato"].isin(required)].copy()
    if df.empty:
        raise ValueError("No poll observations in the declared scenario")

    candidatos_unicos: list[str] = df["candidato"].unique().tolist()
    contagem = df["candidato"].value_counts()
    multiplas_pesquisas = bool((contagem > 1).any())

    if multiplas_pesquisas:
        logger.info(
            "Loaded %s | mode=aggregation | reference_date=%s | candidates=%d",
            csv_path,
            data_referencia,
            len(candidatos_unicos),
        )
    else:
        logger.info(
            "Loaded %s | mode=single-poll | candidates=%d",
            csv_path,
            len(candidatos_unicos),
        )

    candidatos: list[str] = []
    votos_agregados: list[float] = []
    rejeicao_agregada: list[float] = []
    desvios_agregados: list[float] = []

    for candidato in candidatos_unicos:
        df_cand = df[df["candidato"] == candidato].copy()
        voto, rej, desv, info = _agregar_pesquisas_candidato(df_cand, data_referencia)

        candidatos.append(candidato)
        votos_agregados.append(voto)
        rejeicao_agregada.append(rej)
        desvios_agregados.append(desv)

        if info["n_pesquisas"] > 1:
            logger.debug(
                "%s | polls=%d | valid=%d | vote=%.2f%% | rejection=%.2f%% "
                "| sigma=%.2f%% | outliers=%d",
                candidato,
                info["n_pesquisas"],
                info["n_validas"],
                voto,
                rej,
                desv,
                len(info["outliers"]),
            )
            if info["outliers"]:
                for o in info["outliers"]:
                    logger.warning(
                        "Outlier excluded — %s / %s: %.2f%%",
                        candidato,
                        o["instituto"],
                        o["valor"],
                    )
        else:
            logger.debug(
                "%s | single poll | vote=%.2f%% | rejection=%.2f%% | sigma=%.2f%%",
                candidato,
                voto,
                rej,
                desv,
            )

    votos_media = np.array(votos_agregados, dtype=float)
    rejeicao = np.array(rejeicao_agregada, dtype=float)
    desvio_base = float(np.mean(desvios_agregados))

    # Final guard: NaN / zero vote shares would silently break Dirichlet sampling.
    # _validate_schema() catches this at the row level; this catches it post-aggregation.
    nan_mask = np.isnan(votos_media)
    zero_mask = votos_media <= 0
    if nan_mask.any() or zero_mask.any():
        bad = [c for c, n, z in zip(candidatos, nan_mask, zero_mask) if n or z]
        raise ValueError(
            f"Candidates with invalid vote share after aggregation: {bad}. "
            "All candidates must have intencao_voto_pct > 0."
        )

    # Undecided voters: poll-level statistic — aggregate as global weighted mean
    indecisos = 0.0
    if "indecisos_pct" in df.columns:
        if "data" in df.columns:
            pesos_globais = df["data"].apply(
                lambda d: _calcular_peso_temporal(d, data_referencia)
            ).values.astype(float)
            pesos_globais = pesos_globais / pesos_globais.sum()
        else:
            pesos_globais = np.ones(len(df), dtype=float) / len(df)

        indecisos = float(
            np.average(df["indecisos_pct"].fillna(0).values, weights=pesos_globais)
        )
        logger.info("Undecided voters: %.2f%% (will be redistributed before simulation)", indecisos)
    else:
        logger.info("Column 'indecisos_pct' absent — running without undecided redistribution")

    if not (rejeicao > 0).any():
        logger.info("Column 'rejeicao_pct' absent or all zero — running without electoral ceiling")

    return PollData(
        candidatos=candidatos,
        votos_media=votos_media,
        rejeicao=rejeicao,
        desvio_base=desvio_base,
        indecisos=indecisos,
    )


def carregar_pesquisas(
    csv_path: str | Path | None = None, *, as_of: date | None = None,
) -> PollData:
    """
    Backward-compatible wrapper around load_polls().

    Preserves the call signature used by simulation_v2.py, dashboard.py,
    and backtesting.py during the incremental migration to v3.

    Previously returned a 5-tuple (candidatos, votos_media, rejeicao,
    desvio_base, indecisos).  Now returns a PollData dataclass with
    identical named fields — positional unpacking still works:

        candidatos, votos_media, rejeicao, desvio_base, indecisos = carregar_pesquisas()

    because PollData implements __iter__ via dataclass iteration... actually it
    does NOT by default.  Callers that relied on tuple unpacking must be updated
    to attribute access:

        poll = carregar_pesquisas()
        poll.candidatos      # was: result[0]
        poll.votos_media     # was: result[1]

    Args:
        csv_path: Optional path override (str or Path). Defaults to
                  "data/pesquisas.csv", matching the v2 behavior.

    Returns:
        PollData dataclass (not a tuple).
    """
    path = Path(csv_path) if csv_path is not None else Path("data/pesquisas.csv")
    config = SimulationConfig(csv_path=path, as_of=as_of)
    return load_polls(config)
