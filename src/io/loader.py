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

Aggregation helpers
-------------------
_calcular_peso_temporal, _detectar_outliers, _agregar_pesquisas_candidato are
private copies of the pure functions currently in simulation_v2.py.

TODO(core-architect): Once src/core/aggregation.py is delivered, replace the
three private helpers below with:
    from src.core.aggregation import (
        calcular_peso_temporal as _calcular_peso_temporal,
        detectar_outliers as _detectar_outliers,
        agregar_pesquisas_candidato as _agregar_pesquisas_candidato,
    )
The public API of this module does not change.
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

def _calcular_peso_temporal(
    data_pesquisa: Any,
    data_referencia: date,
    tau: int = 7,
) -> float:
    """
    Temporal weight for a single poll via exponential decay.

    peso = exp(−dias_atras / tau)

    Args:
        data_pesquisa:  Poll date (string YYYY-MM-DD, date object, or None/NaN).
        data_referencia: Reference date (typically today).
        tau:            Time constant in days.

    Returns:
        Weight in (0, 1]. Unknown dates receive weight 1.0 (treated as most recent).
    """
    if data_pesquisa is None:
        return 1.0
    if isinstance(data_pesquisa, float):
        # NaN read from CSV arrives as float
        return 1.0
    if hasattr(data_pesquisa, "__class__") and data_pesquisa.__class__.__name__ == "NaTType":
        return 1.0
    if isinstance(data_pesquisa, str):
        data_pesquisa = pd.to_datetime(data_pesquisa).date()

    dias_atras = max(0, (data_referencia - data_pesquisa).days)
    return float(np.exp(-dias_atras / tau))


def _detectar_outliers(valores: np.ndarray, threshold: float = 2.5) -> np.ndarray:
    """
    Detects outliers using the modified z-score (MAD-based), robust to outliers.

    Arrays with fewer than 3 elements are returned with no outliers flagged.

    Args:
        valores:   1-D numeric array.
        threshold: Modified z-score cutoff (default 2.5).

    Returns:
        Boolean array of the same length; True indicates an outlier.
    """
    if len(valores) < 3:
        return np.zeros(len(valores), dtype=bool)

    mediana = np.median(valores)
    mad = np.median(np.abs(valores - mediana))

    if mad == 0:
        return np.zeros(len(valores), dtype=bool)

    z_scores = 0.6745 * (valores - mediana) / mad
    return np.abs(z_scores) > threshold


def _agregar_pesquisas_candidato(
    df_candidato: pd.DataFrame,
    data_referencia: date,
) -> tuple[float, float, float, dict[str, Any]]:
    """
    Aggregates all polls for a single candidate into one weighted estimate.

    Args:
        df_candidato:   DataFrame rows belonging to one candidate.
        data_referencia: Reference date for temporal weighting.

    Returns:
        (voto_agregado, rejeicao_agregada, desvio_agregado, info)
        - voto_agregado:    Weighted mean vote intention (%).
        - rejeicao_agregada: Weighted mean rejection rate (%).
        - desvio_agregado:  Combined std dev √(σ_within² + σ_between²) (%).
        - info:             Aggregation metadata dict for logging/reporting.
    """
    n_pesquisas = len(df_candidato)

    # ── Single poll: no aggregation needed ───────────────────────────────────
    if n_pesquisas == 1:
        row = df_candidato.iloc[0]
        return (
            float(row["intencao_voto_pct"]),
            float(row.get("rejeicao_pct", 0.0) or 0.0),
            float(row["desvio_padrao_pct"]),
            {
                "n_pesquisas": 1,
                "n_validas": 1,
                "institutos": [row.get("instituto", "Unknown")],
                "outliers": [],
                "desvio_medio": float(row["desvio_padrao_pct"]),
                "desvio_entre": 0.0,
            },
        )

    # ── Temporal weights ──────────────────────────────────────────────────────
    if "data" in df_candidato.columns:
        pesos = df_candidato["data"].apply(
            lambda d: _calcular_peso_temporal(d, data_referencia)
        ).values.astype(float)
    else:
        pesos = np.ones(n_pesquisas, dtype=float)

    pesos = pesos / pesos.sum()

    # ── Outlier detection on vote intention ──────────────────────────────────
    votos = df_candidato["intencao_voto_pct"].values.astype(float)
    is_outlier = _detectar_outliers(votos)
    mask_validos = ~is_outlier

    if mask_validos.sum() == 0:
        # All polls flagged as outliers — keep all rather than lose the candidate
        mask_validos = np.ones(n_pesquisas, dtype=bool)

    pesos_validos = pesos[mask_validos]
    pesos_validos = pesos_validos / pesos_validos.sum()

    # ── Weighted vote intention ───────────────────────────────────────────────
    voto_agregado = float(
        np.average(
            df_candidato.loc[mask_validos, "intencao_voto_pct"].values.astype(float),
            weights=pesos_validos,
        )
    )

    # ── Weighted rejection ────────────────────────────────────────────────────
    # Rejection is an independent measurement: outlier exclusion from vote
    # intention does NOT carry over here.  Only rows where rejeicao_pct > 0
    # are included (0 means "not measured", not "true zero rejection").
    rejeicao_agregada = 0.0
    if "rejeicao_pct" in df_candidato.columns:
        mask_tem_rejeicao = df_candidato["rejeicao_pct"].values > 0
        if mask_tem_rejeicao.any():
            pesos_rej = pesos[mask_tem_rejeicao]
            pesos_rej = pesos_rej / pesos_rej.sum()
            rejeicao_agregada = float(
                np.average(
                    df_candidato["rejeicao_pct"].values[mask_tem_rejeicao],
                    weights=pesos_rej,
                )
            )

    # ── Combined standard deviation ───────────────────────────────────────────
    # σ_agregado = √(σ_médio² + σ_entre²)
    desvio_medio = float(
        np.average(
            df_candidato.loc[mask_validos, "desvio_padrao_pct"].values.astype(float),
            weights=pesos_validos,
        )
    )
    variancia_entre = float(
        np.average(
            (
                df_candidato.loc[mask_validos, "intencao_voto_pct"].values.astype(float)
                - voto_agregado
            )
            ** 2,
            weights=pesos_validos,
        )
    )
    desvio_entre = float(np.sqrt(variancia_entre))
    desvio_agregado = float(np.sqrt(desvio_medio**2 + desvio_entre**2))

    # ── Info dict ─────────────────────────────────────────────────────────────
    institutos = (
        df_candidato["instituto"].tolist()
        if "instituto" in df_candidato.columns
        else ["Unknown"] * n_pesquisas
    )
    outliers_info = [
        {"instituto": inst, "valor": float(val)}
        for inst, val, is_out in zip(institutos, votos, is_outlier)
        if is_out
    ]
    info: dict[str, Any] = {
        "n_pesquisas": n_pesquisas,
        "n_validas": int(mask_validos.sum()),
        "institutos": institutos,
        "outliers": outliers_info,
        "desvio_medio": desvio_medio,
        "desvio_entre": desvio_entre,
    }

    return voto_agregado, rejeicao_agregada, desvio_agregado, info


# ─── SCHEMA VALIDATION ────────────────────────────────────────────────────────

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
    for col in ("intencao_voto_pct", "desvio_padrao_pct"):
        # Guard: non-numeric dtype (e.g. column contains strings)
        if not pd.api.types.is_numeric_dtype(df[col]):
            bad = df[
                ~pd.to_numeric(df[col], errors="coerce").notna()
            ]["candidato"].unique()
            raise ValueError(
                f"Column '{col}' must be numeric. "
                f"Non-numeric values found for candidates: {list(bad)}"
            )

        nan_mask = df[col].isna()
        if nan_mask.any():
            bad = df[nan_mask]["candidato"].unique()
            raise ValueError(
                f"Column '{col}' has NaN for candidates: {list(bad)}. "
                f"All rows in {csv_path} must have a numeric value."
            )

        non_positive = df[df[col] <= 0]["candidato"].unique()
        if len(non_positive) > 0:
            raise ValueError(
                f"Column '{col}' must be > 0 for all rows. "
                f"Candidates with invalid values: {list(non_positive)}"
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

    df = pd.read_csv(csv_path)

    # Parse date column; unparseable values become NaT (weight falls back to 1.0)
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date

    _validate_schema(df, csv_path)

    candidatos_unicos: list[str] = df["candidato"].unique().tolist()
    contagem = df["candidato"].value_counts()
    multiplas_pesquisas = bool((contagem > 1).any())

    data_referencia = date.today()

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


def carregar_pesquisas(csv_path: str | Path | None = None) -> PollData:
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
    config = SimulationConfig(csv_path=path)
    return load_polls(config)