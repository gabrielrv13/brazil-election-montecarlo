"""
Core Monte Carlo simulation engine for brazil-election-montecarlo.

All functions are pure: they receive data as parameters, return data as
results, and have zero side effects — no I/O, no global state, no matplotlib,
no streamlit imports.

Migrated from ``simulation_v2.py`` (v2.8) as part of the v3.0 refactor.
Globals ``CANDIDATOS``, ``VOTOS_MEDIA``, ``REJEICAO``, ``INDECISOS``,
``DESVIO``, ``N_SIM`` are replaced by explicit parameters sourced from
:class:`~src.core.config.SimulationConfig` and
:class:`~src.core.config.PollData`.
"""

from __future__ import annotations

import math
from datetime import date
from typing import NamedTuple

import numpy as np
import pandas as pd

from src.core.config import PollData, SimulationConfig


# ── Electorate constants (TSE 2026) ───────────────────────────────────────────
# Empirical constants. If these need to vary between scenarios, add them as
# optional fields on SimulationConfig.

ELEITORADO: int = 158_600_000
ABSTENCAO_1T_MU: float = 0.20
ABSTENCAO_1T_SIGMA: float = 0.02


# ── Output type ───────────────────────────────────────────────────────────────

class FirstRoundResult(NamedTuple):
    """
    Return type of :func:`simular_primeiro_turno`.

    Fields
    ------
    df : pd.DataFrame
        Per-simulation data frame. Columns include raw vote shares for every
        candidate, normalised valid-vote shares (``<n>_val``), absolute
        vote counts (``<n>_abs``), ``vencedor``, ``tem_2turno``,
        ``margem_1t``, ``lider_1t``, and signed per-candidate margins
        (``margem_<n>``).
    validos_final : np.ndarray
        Array of shape ``(n_sim, n_valid_candidates)`` containing the final
        normalised valid-vote shares after the rejection ceiling is applied.
        Required by :func:`simular_segundo_turno`.
    candidatos_validos : list[str]
        Names of valid candidates in column order of ``validos_final``
        (i.e. without ``"Brancos"`` / ``"Nulos"`` entries).
    info_lim_1t : dict
        Diagnostics from :func:`aplicar_teto_rejeicao`: which candidates
        were ceiling-clipped, how often, and by how much.
    info_indecisos : dict
        Diagnostics from :func:`distribuir_indecisos`: total undecided share,
        redistributable share, blank allocation, and per-candidate gain.
    """

    df: pd.DataFrame
    validos_final: np.ndarray
    candidatos_validos: list[str]
    info_lim_1t: dict
    info_indecisos: dict


# ── Private helpers ───────────────────────────────────────────────────────────

def _calcular_desvio_ajustado(
    desvio_base: float,
    election_date: date,
    reference_date: date,
) -> float:
    """
    Adjust base standard deviation by time remaining until election.

    Implements the funnel effect: uncertainty increases with distance from
    election day. Once the election has passed, ``desvio_base`` is returned
    unchanged.

    Parameters
    ----------
    desvio_base:
        Base standard deviation from poll aggregation (pp).
    election_date:
        First-round election date.
    reference_date:
        Date against which remaining days are measured (typically
        ``date.today()`` for live runs).

    Returns
    -------
    float
        Adjusted standard deviation >= ``desvio_base``.
    """
    dias_restantes = (election_date - reference_date).days
    if dias_restantes <= 0:
        return desvio_base
    return max(desvio_base, desvio_base * math.sqrt(dias_restantes / 30))


# ── Public functions ──────────────────────────────────────────────────────────

def aplicar_teto_rejeicao(
    votos: np.ndarray,
    rejeicao_array: np.ndarray,
    candidatos: list[str],
) -> tuple[np.ndarray, dict]:
    """
    Clip each candidate's vote share to their electoral ceiling.

    A candidate cannot exceed ``(100 - rejection)%`` of valid votes.
    Blank/null candidates (names containing ``"Brancos"`` or ``"Nulos"``)
    and candidates with zero rejection are excluded from the diagnostic info
    but are still subject to clipping.

    Parameters
    ----------
    votos:
        Array of shape ``(n_sim, n_candidates)`` with per-simulation vote
        share percentages.
    rejeicao_array:
        Array of shape ``(n_candidates,)`` with rejection rates (pp).
        Must be parallel to ``candidatos``.
    candidatos:
        Candidate names in the same order as the columns of ``votos`` and
        the elements of ``rejeicao_array``.

    Returns
    -------
    tuple[np.ndarray, dict]
        ``(votos_ajustados, info)`` where ``votos_ajustados`` has the same
        shape as ``votos`` with values clipped to their respective ceilings,
        and ``info`` maps candidate name → dict with keys
        ``n_simulacoes_limitadas``, ``pct_simulacoes_limitadas``, ``teto``,
        ``rejeicao``. Only candidates clipped in at least one simulation
        appear in ``info``.
    """
    tetos = 100.0 - rejeicao_array
    ultrapassou = votos > tetos[np.newaxis, :]
    votos_limitados = np.minimum(votos, tetos[np.newaxis, :])

    info: dict = {}
    for i, cand in enumerate(candidatos):
        if "Brancos" in cand or "Nulos" in cand or rejeicao_array[i] == 0:
            continue
        n_limitado = int(ultrapassou[:, i].sum())
        if n_limitado > 0:
            info[cand] = {
                "n_simulacoes_limitadas": n_limitado,
                "pct_simulacoes_limitadas": float(n_limitado / len(votos) * 100),
                "teto": float(tetos[i]),
                "rejeicao": float(rejeicao_array[i]),
            }

    return votos_limitados, info


def distribuir_indecisos(
    votos_base: np.ndarray,
    indecisos_total: float,
    rejeicao_array: np.ndarray,
    candidatos: list[str],
    blank_fraction: float = 0.15,
) -> tuple[np.ndarray, dict]:
    """
    Redistribute undecided voter share proportionally among declared candidates.

    Distribution weights are the product of each candidate's vote share and
    available electoral space (``(100 - rejection) / 100``), so candidates
    with higher rejection absorb fewer undecided voters. A configurable
    fraction (``blank_fraction``) is routed to blank/null categories instead.

    Parameters
    ----------
    votos_base:
        Array of shape ``(n_candidates,)`` with base vote intentions (pp).
    indecisos_total:
        Total undecided voter share (pp). Returns a copy of ``votos_base``
        unchanged when <= 0.
    rejeicao_array:
        Array of shape ``(n_candidates,)`` with rejection rates (pp).
    candidatos:
        Candidate names parallel to ``votos_base`` and ``rejeicao_array``.
    blank_fraction:
        Fraction of undecided voters routed to blank/null (default: 0.15).

    Returns
    -------
    tuple[np.ndarray, dict]
        ``(votos_ajustados, info)`` where ``votos_ajustados`` is a copy of
        ``votos_base`` with the redistributed share added, and ``info``
        contains keys ``indecisos_total``, ``indecisos_redistribuiveis``,
        ``indecisos_para_brancos``, ``blank_fraction``,
        ``ganho_por_candidato``.

    Notes
    -----
    Formula::

        weight_i = vote_share_i * max(100 - rejection_i, 0) / 100
        gain_i   = (weight_i / sum(weights)) * indecisos_total * (1 - blank_fraction)

    If all weights are zero the gain is distributed uniformly among
    distributable candidates (fallback).
    """
    if indecisos_total <= 0:
        return votos_base.copy(), {}

    votos_ajustados = votos_base.copy()

    mask_distributable = np.array(
        ["Brancos" not in c and "Nulos" not in c for c in candidatos]
    )
    mask_brancos = ~mask_distributable

    espaco = np.maximum(100.0 - rejeicao_array, 0.0) / 100.0
    pesos = votos_base * espaco * mask_distributable

    total_peso = pesos.sum()
    if total_peso == 0:
        n_dist = float(mask_distributable.sum())
        if n_dist == 0:
            return votos_base.copy(), {}
        pesos = mask_distributable.astype(float) / n_dist
        total_peso = 1.0

    proporcoes = pesos / total_peso
    indecisos_redistribuiveis = indecisos_total * (1.0 - blank_fraction)
    indecisos_para_brancos = indecisos_total * blank_fraction

    ganho = proporcoes * indecisos_redistribuiveis
    votos_ajustados += ganho

    if mask_brancos.any():
        n_brancos = float(mask_brancos.sum())
        votos_ajustados[mask_brancos] += indecisos_para_brancos / n_brancos

    ganho_por_candidato = {
        candidatos[i]: float(ganho[i])
        for i in range(len(candidatos))
        if ganho[i] > 0.01
    }

    info: dict = {
        "indecisos_total": float(indecisos_total),
        "indecisos_redistribuiveis": float(indecisos_redistribuiveis),
        "indecisos_para_brancos": float(indecisos_para_brancos),
        "blank_fraction": float(blank_fraction),
        "ganho_por_candidato": ganho_por_candidato,
    }

    return votos_ajustados, info


def simular_primeiro_turno(
    config: SimulationConfig,
    poll_data: PollData,
) -> FirstRoundResult:
    """
    Simulate the first round of the Brazilian presidential election.

    Runs ``config.n_sim`` Monte Carlo draws using a Dirichlet distribution
    parameterised by the aggregated poll data. Applies undecided voter
    redistribution and the rejection ceiling before computing per-candidate
    statistics.

    Parameters
    ----------
    config:
        Simulation configuration. Uses ``n_sim``, ``seed``,
        and ``election_date``.
    poll_data:
        Aggregated poll data produced by ``src.io.loader.load_polls``.

    Returns
    -------
    FirstRoundResult
        Named tuple with fields ``df``, ``validos_final``,
        ``candidatos_validos``, ``info_lim_1t``, ``info_indecisos``.

    Notes
    -----
    **Probability scale:** ``pv`` and ``p2v`` in
    :class:`~src.core.config.SimulationResult` must be populated in 0–1
    scale. Display layers multiply by 100 for output.
    """
    rng = np.random.default_rng(config.seed)
    n_sim = config.n_sim

    candidatos = poll_data.candidatos
    votos_media = poll_data.votos_media.copy()
    rejeicao = poll_data.rejeicao
    desvio_base = poll_data.desvio_base
    indecisos = poll_data.indecisos

    # ── Temporal uncertainty adjustment ───────────────────────────────────────
    desvio = _calcular_desvio_ajustado(desvio_base, config.election_date, date.today())

    # ── Undecided voter redistribution ────────────────────────────────────────
    info_indecisos: dict = {}
    votos_efetivos = votos_media.copy()
    if indecisos > 0:
        votos_efetivos, info_indecisos = distribuir_indecisos(
            votos_media, indecisos, rejeicao, candidatos
        )

    if np.any(np.isnan(votos_efetivos)) or np.any(votos_efetivos <= 0):
        bad = [
            (candidatos[i], float(v))
            for i, v in enumerate(votos_efetivos)
            if np.isnan(v) or v <= 0
        ]
        raise ValueError(
            f"Invalid vote shares before first-round simulation: {bad}\n"
            "All candidates must have intencao_voto_pct > 0."
        )

    # ── Dirichlet sampling ────────────────────────────────────────────────────
    fator_concentracao = 100.0 / desvio
    alphas = votos_efetivos * fator_concentracao

    proporcoes = rng.dirichlet(alphas, size=n_sim)
    votos_norm = proporcoes * 100.0

    # ── Separate blank/null from valid candidates ─────────────────────────────
    indices_validos = [
        i for i, c in enumerate(candidatos)
        if "Brancos" not in c and "Nulos" not in c
    ]
    candidatos_validos = [candidatos[i] for i in indices_validos]

    validos = votos_norm[:, indices_validos]
    validos_norm = validos / validos.sum(axis=1, keepdims=True) * 100.0

    # ── Rejection ceiling ─────────────────────────────────────────────────────
    rejeicao_validos = rejeicao[indices_validos]
    validos_com_teto, info_lim_1t = aplicar_teto_rejeicao(
        validos_norm, rejeicao_validos, candidatos_validos
    )

    # Re-normalise after ceiling
    validos_final = (
        validos_com_teto / validos_com_teto.sum(axis=1, keepdims=True) * 100.0
    )

    # ── Winner and second-round flag ──────────────────────────────────────────
    idx_vencedor_local = np.argmax(validos_final, axis=1)
    vencedores = np.array(candidatos_validos)[idx_vencedor_local]

    # ── Build per-simulation data frame ───────────────────────────────────────
    data: dict = {}
    for i, cand in enumerate(candidatos):
        data[cand] = votos_norm[:, i]
    for i, cand in enumerate(candidatos_validos):
        data[f"{cand}_val"] = validos_final[:, i]
    data["vencedor"] = vencedores
    data["tem_2turno"] = validos_final.max(axis=1) < 50.0

    # ── Absolute vote projections (v2.6) ──────────────────────────────────────
    abstencao_1t_sim = rng.normal(
        ABSTENCAO_1T_MU, ABSTENCAO_1T_SIGMA, n_sim
    ).clip(0.05, 0.45)
    votos_validos_1t = (ELEITORADO * (1.0 - abstencao_1t_sim)).astype(np.int64)
    data["abstencao_1t_pct"] = abstencao_1t_sim * 100.0
    data["votos_validos_1t"] = votos_validos_1t
    for i, cand in enumerate(candidatos_validos):
        data[f"{cand}_abs"] = (
            votos_validos_1t * validos_final[:, i] / 100.0
        ).astype(np.int64)

    df = pd.DataFrame(data)

    # ── First-round margin distribution (v2.8) ────────────────────────────────
    sorted_votes = np.sort(validos_final, axis=1)[:, ::-1]
    df["margem_1t"] = sorted_votes[:, 0] - sorted_votes[:, 1]
    df["lider_1t"] = pd.array(
        [candidatos_validos[int(np.argmax(row))] for row in validos_final],
        dtype=object,
    )
    for i, cand in enumerate(candidatos_validos):
        others_max = np.max(np.delete(validos_final, i, axis=1), axis=1)
        df[f"margem_{cand}"] = validos_final[:, i] - others_max

    return FirstRoundResult(
        df=df,
        validos_final=validos_final,
        candidatos_validos=candidatos_validos,
        info_lim_1t=info_lim_1t,
        info_indecisos=info_indecisos,
    )