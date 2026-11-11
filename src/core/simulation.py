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

# Blank + null votes as a share of turnout, used only when the poll input has
# no explicit "Brancos/Nulos" category. TSE first rounds: 2014 ≈ 9.6%,
# 2018 ≈ 8.8%, 2022 ≈ 4.4%.
INVALIDOS_1T_MU: float = 0.06
INVALIDOS_1T_SIGMA: float = 0.02

# Blank + null share of turnout in presidential runoffs (TSE): 2014 6.3%,
# 2018 9.6%, 2022 4.6%, 2026 about 3.2% (128.2 M voters, 124.1 M valid).
INVALIDOS_2T_MU: float = 0.06
INVALIDOS_2T_SIGMA: float = 0.025

# Reference share at which ``sd_pp`` is the exact marginal standard deviation
# of a Dirichlet component. 50% is where the variance p(1-p) peaks, so every
# other component has a smaller sd. Same convention as the calibrated runoff
# (``simulation_2turno.sd_fatia_para_desvio``).
_SD_REFERENCE_SHARE: float = 0.5


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

    The returned value is a marginal standard deviation in percentage points
    (see :func:`concentracao_dirichlet`), so the simulated sd grows with the
    square root of the horizon, ``sqrt(dias / 30)``. Before this was made
    explicit the value was used as an inverse concentration and the real sd
    grew only with the fourth root.

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

def concentracao_dirichlet(sd_pp: float) -> float:
    """
    Total Dirichlet concentration whose marginal sd at 50% equals ``sd_pp``.

    For a Dirichlet with total concentration ``alpha0`` a component with mean
    share ``p`` has ``Var(100 X) = 10000 p (1 - p) / (alpha0 + 1)``. Solving
    at ``p = 0.5`` gives ``alpha0 = (50 / sd_pp)^2 - 1``. Components with
    other means get a smaller sd, ``sd_pp * sqrt(4 p (1 - p))``.

    Parameters
    ----------
    sd_pp:
        Target marginal standard deviation in percentage points. Must be
        finite and in ``(0, 50)``.

    Returns
    -------
    float
        ``alpha0`` > 0.

    Raises
    ------
    ValueError
        If ``sd_pp`` is not finite or is outside ``(0, 50)``.
    """
    if not math.isfinite(sd_pp) or sd_pp <= 0 or sd_pp >= 50:
        raise ValueError(
            f"First-round sd must be finite and in (0, 50) pp, got {sd_pp!r}. "
            "Check desvio_padrao_pct in the poll CSV."
        )
    p = _SD_REFERENCE_SHARE
    return p * (1.0 - p) * 10_000.0 / sd_pp**2 - 1.0


def contabilizar_votos(
    rng,
    n: int,
    abstencao_mu: float,
    abstencao_sigma: float,
    invalidos_frac: np.ndarray | None = None,
    invalidos_mu: float = INVALIDOS_1T_MU,
    invalidos_sigma: float = INVALIDOS_1T_SIGMA,
    eleitorado: int = ELEITORADO,
) -> dict[str, np.ndarray]:
    """Electorate → turnout → blank/null + valid votes, one row per draw.

    Abstention is drawn first, then (only when ``invalidos_frac`` is not
    given) the blank/null share of turnout, so the RNG sequence matches the
    pre-refactor first round. ``rng`` is a NumPy ``Generator`` or the legacy
    ``np.random`` module (anything with ``normal``).

    Returns:
        Arrays ``abstencao`` (fraction), ``comparecimento``,
        ``invalidos_frac``, ``votos_invalidos`` and ``votos_validos``, with
        ``votos_validos + votos_invalidos == comparecimento`` exactly.
    """
    abstencao = rng.normal(abstencao_mu, abstencao_sigma, n).clip(0.05, 0.45)
    if invalidos_frac is None:
        invalidos = rng.normal(invalidos_mu, invalidos_sigma, n).clip(0.01, 0.20)
    else:
        invalidos = np.asarray(invalidos_frac, dtype=float)
        if invalidos.shape != (n,) or np.any(~np.isfinite(invalidos)) or np.any(
            (invalidos < 0) | (invalidos >= 1)
        ):
            raise ValueError("invalidos_frac must be n finite fractions in [0, 1)")
    comparecimento = np.floor(eleitorado * (1.0 - abstencao)).astype(np.int64)
    votos_invalidos = np.floor(comparecimento * invalidos).astype(np.int64)
    return {
        "abstencao": abstencao,
        "comparecimento": comparecimento,
        "invalidos_frac": invalidos,
        "votos_invalidos": votos_invalidos,
        "votos_validos": comparecimento - votos_invalidos,
    }


def dividir_validos(votos_validos: np.ndarray, shares_pct: np.ndarray) -> np.ndarray:
    """Split valid votes among candidates by largest remainder.

    ``shares_pct`` has shape ``(n, k)`` and each row sums to 100. The result
    is integer, sums exactly to ``votos_validos`` per row and differs from
    the exact proportional split by less than one vote per candidate.
    """
    v = np.asarray(votos_validos, dtype=np.int64)
    exato = v[:, np.newaxis] * (np.asarray(shares_pct, dtype=float) / 100.0)
    base = np.floor(exato).astype(np.int64)
    sobra = v - base.sum(axis=1)
    if sobra.size and sobra.max() > 0:
        ordem = np.argsort(-(exato - base), axis=1, kind="stable")
        rank = np.empty_like(ordem)
        np.put_along_axis(rank, ordem, np.arange(base.shape[1])[np.newaxis, :], axis=1)
        base += (rank < sobra[:, np.newaxis]).astype(np.int64)
    return base


def sd_deriva(sd_30d_pp: float, election_date: date, reference_date: date) -> float:
    """Opinion drift until election day: ``sd_30d * sqrt(days / 30)`` (pp)."""
    dias = (election_date - reference_date).days
    return 0.0 if dias <= 0 else float(sd_30d_pp * math.sqrt(dias / 30.0))


def _dirichlet_linhas(rng: np.random.Generator, alphas: np.ndarray) -> np.ndarray:
    """One Dirichlet draw per row of ``alphas`` via normalised Gammas."""
    g = rng.gamma(np.maximum(alphas, 1e-6))
    s = g.sum(axis=1, keepdims=True)
    return g / np.where(s > 0, s, 1.0)


def amostrar_proporcoes(
    medias: np.ndarray,
    sd_media_pp: float,
    n_sim: int,
    rng: np.random.Generator,
    sd_comum_pp: float = 0.0,
    gl_comum: float = math.inf,
    sd_deriva_pp: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Draw first-round shares with a two-level error structure.

    1. **Election-level shift** (one per simulation, shared by all polls):
       ``mu ~ Dirichlet(p * A)``, with ``A`` set by
       ``sd_shift^2 = sd_comum^2 * V + sd_deriva^2``. ``V`` is an
       inverse-chi-square multiplier with mean 1 (``(gl-2)/chi2_gl``), a
       Student-t scale mixture that gives the common error heavy tails while
       keeping its sd at ``sd_comum``.
    2. **Uncertainty of the polling average**:
       ``shares ~ Dirichlet(mu * concentracao_dirichlet(sd_media))``.

    Every sd is in pp for a candidate at 50%; the variances of the two
    levels add, so the total sd at 50% is about
    ``sqrt(sd_media^2 + sd_comum^2 + sd_deriva^2)``. With ``sd_comum`` and
    ``sd_deriva`` at zero this is the plain Dirichlet of Phase 1.

    Args:
        medias: Mean shares (any positive scale; normalised internally).
        sd_media_pp: sd of the polling average, in ``(0, 50)``.
        n_sim: Number of draws.
        rng: NumPy generator (the caller owns the seed).
        sd_comum_pp: sd of the common election error.
        gl_comum: Degrees of freedom of the tail mixture (> 2, or ``inf``).
        sd_deriva_pp: sd of the drift until election day.

    Returns:
        ``(proporcoes, sd_shift)``: shares in ``[0, 1]`` of shape
        ``(n_sim, n_cand)`` summing to 1 per row, and the per-simulation
        shift sd (pp) actually used.
    """
    medias = np.asarray(medias, dtype=float)
    total = medias.sum()
    if not np.isfinite(total) or total <= 0:
        raise ValueError("Mean shares must be finite with a positive sum.")
    p = medias / total
    alpha0 = concentracao_dirichlet(sd_media_pp)

    if sd_comum_pp > 0 and math.isfinite(gl_comum):
        mult = (gl_comum - 2.0) / rng.chisquare(gl_comum, n_sim)
    else:
        mult = np.ones(n_sim)
    sd_shift = np.sqrt(sd_comum_pp**2 * mult + sd_deriva_pp**2)
    # Extreme tail draws are capped below the 50 pp singularity.
    sd_shift = np.minimum(sd_shift, 45.0)

    mu = np.broadcast_to(p, (n_sim, p.size)).copy()
    com_shift = sd_shift > 0
    if com_shift.any():
        a_shift = 2_500.0 / sd_shift[com_shift] ** 2 - 1.0
        mu[com_shift] = _dirichlet_linhas(rng, p[np.newaxis, :] * a_shift[:, np.newaxis])
    proporcoes = _dirichlet_linhas(rng, mu * alpha0)
    return proporcoes, sd_shift


def aplicar_teto_rejeicao(
    votos: np.ndarray,
    rejeicao_array: np.ndarray,
    candidatos: list[str],
) -> tuple[np.ndarray, dict]:
    """
    Cap each candidate at their electoral ceiling and reallocate the excess.

    A candidate cannot exceed ``(100 - rejection)%`` of valid votes. Simple
    clipping followed by renormalisation, the pre-v3 behaviour, pushed capped
    candidates back above their ceiling (``[80, 20]`` with ceiling 60 ended at
    ``[75, 25]``). This function instead water-fills: capped candidates are
    fixed at the ceiling and the excess goes to the uncapped candidates in
    proportion to their share, repeating until no ceiling is violated. Each
    row keeps its original total, so the result needs no renormalisation and
    the ceilings hold in the final shares.

    A rejection of zero means "not measured" and gives a ceiling of 100.
    Blank/null candidates (names containing ``"Brancos"`` or ``"Nulos"``)
    and candidates with zero rejection are excluded from the diagnostic info
    but are still subject to the ceiling.

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
        shape and row totals as ``votos``, with every value at or below its
        ceiling, and ``info`` maps candidate name → dict with keys
        ``n_simulacoes_limitadas``, ``pct_simulacoes_limitadas``, ``teto``,
        ``rejeicao``. Only candidates capped in at least one simulation
        appear in ``info``.

    Raises
    ------
    ValueError
        If rejection is outside ``[0, 100]`` or the ceilings sum to less than
        a row total. In that case no allocation can respect every ceiling:
        rejection and vote intention are measured on incompatible bases and
        the input must be reviewed rather than silently forced.
    """
    votos = np.asarray(votos, dtype=float)
    rejeicao_array = np.asarray(rejeicao_array, dtype=float)
    if np.any(~np.isfinite(rejeicao_array)) or np.any(
        (rejeicao_array < 0) | (rejeicao_array > 100)
    ):
        raise ValueError(
            f"Rejection rates must be finite and within [0, 100]: "
            f"{dict(zip(candidatos, rejeicao_array.tolist()))}"
        )
    tetos = 100.0 - rejeicao_array
    totais = votos.sum(axis=1)
    tol = 1e-9 * np.maximum(totais, 1.0)
    if np.any(tetos.sum() < totais - tol):
        raise ValueError(
            f"Infeasible rejection ceilings: they sum to {tetos.sum():.2f}, "
            f"below the vote total of {totais.max():.2f}. No allocation can "
            f"respect them: {dict(zip(candidatos, tetos.tolist()))}"
        )

    v = votos.copy()
    limitado = np.zeros(v.shape, dtype=bool)
    # Each pass caps at least one new candidate per violating row, so
    # n_candidates passes always suffice.
    for _ in range(v.shape[1] + 1):
        excede = (v > tetos[np.newaxis, :] + 1e-12) & ~limitado
        if not excede.any():
            break
        limitado |= excede
        v = np.where(limitado, tetos[np.newaxis, :], v)
        sobra = totais - v.sum(axis=1)
        livre = ~limitado
        base = np.where(livre, v, 0.0)
        soma_base = base.sum(axis=1)
        # Fallback when every free candidate has zero share: fill by headroom.
        folga = np.where(livre, tetos[np.newaxis, :] - v, 0.0)
        pesos = np.where(
            (soma_base > 0)[:, np.newaxis], base, folga
        )
        soma_pesos = pesos.sum(axis=1, keepdims=True)
        incremento = np.divide(
            pesos * sobra[:, np.newaxis], soma_pesos,
            out=np.zeros_like(v), where=soma_pesos > 0,
        )
        v = v + incremento
    votos_limitados = v

    info: dict = {}
    for i, cand in enumerate(candidatos):
        if "Brancos" in cand or "Nulos" in cand or rejeicao_array[i] == 0:
            continue
        n_limitado = int(limitado[:, i].sum())
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
    if config.use_bayesian:
        # src.core.bayesian samples a Dirichlet with fixed parameters and no
        # likelihood, so it is not Bayesian inference and its draws are not
        # wired into this engine. Refuse instead of labelling Dirichlet
        # output as MCMC.
        raise ValueError(
            "use_bayesian=True is not supported: the MCMC path has no "
            "validated implementation. Run without --bayesian."
        )

    rng = np.random.default_rng(config.seed)
    n_sim = config.n_sim

    candidatos = poll_data.candidatos
    votos_media = poll_data.votos_media.copy()
    rejeicao = poll_data.rejeicao
    desvio_base = poll_data.desvio_base
    indecisos = poll_data.indecisos

    # ── Horizon: drift until election day ─────────────────────────────────────
    # Phase 2 moved the funnel from the sd of the polling average (which does
    # not grow with time) to an explicit drift term.
    reference_date = config.as_of if config.as_of is not None else date.today()
    deriva = sd_deriva(config.sd_deriva_30d_pp, config.election_date, reference_date)

    # ── Undecided voter redistribution ────────────────────────────────────────
    info_indecisos: dict = {}
    votos_efetivos = votos_media.copy()
    if indecisos > 0:
        votos_efetivos, info_indecisos = distribuir_indecisos(
            votos_media, indecisos, rejeicao, candidatos
        )

    if np.any(~np.isfinite(votos_efetivos)) or np.any(votos_efetivos < 0):
        bad = [
            (candidatos[i], float(v))
            for i, v in enumerate(votos_efetivos)
            if not np.isfinite(v) or v < 0
        ]
        raise ValueError(
            f"Invalid vote shares before first-round simulation: {bad}\n"
            "All candidates must have finite, non-negative vote shares."
        )

    # -- Two-level sampling (see amostrar_proporcoes) ------------------
    # ``desvio_base`` is the sd of the polling average at a 50% share; the
    # common election error and the drift are added on top of it. Means are
    # normalised, so the undecided redistribution (which only rescales the
    # total) does not change the spread.
    if votos_efetivos.sum() <= 0:
        raise ValueError("All vote shares are zero; nothing to simulate.")
    proporcoes, sd_shift = amostrar_proporcoes(
        votos_efetivos, desvio_base, n_sim, rng,
        sd_comum_pp=config.sd_erro_comum_pp,
        gl_comum=config.gl_erro_comum,
        sd_deriva_pp=deriva,
    )

    # Convert simulated proportions to percentages (0-100).
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
    # Water-filling keeps each row at 100, so the ceilings hold in the final
    # shares; renormalising afterwards would break them again.
    rejeicao_validos = rejeicao[indices_validos]
    validos_final, info_lim_1t = aplicar_teto_rejeicao(
        validos_norm, rejeicao_validos, candidatos_validos
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
    data["tem_2turno"] = validos_final.max(axis=1) <= 50.0

    # ── Absolute vote projections ─────────────────────────────────────────────
    # electorate → turnout → (valid + blank/null). Candidates split only the
    # valid votes. Before v3 the whole turnout was treated as valid, which
    # overstated valid votes by the blank/null share.
    indices_invalidos = [
        i for i in range(len(candidatos)) if i not in set(indices_validos)
    ]
    votos = contabilizar_votos(
        rng, n_sim, ABSTENCAO_1T_MU, ABSTENCAO_1T_SIGMA,
        invalidos_frac=(
            votos_norm[:, indices_invalidos].sum(axis=1) / 100.0
            if indices_invalidos else None
        ),
    )
    data["abstencao_1t_pct"] = votos["abstencao"] * 100.0
    data["comparecimento_1t"] = votos["comparecimento"]
    data["invalidos_1t_pct"] = votos["invalidos_frac"] * 100.0
    data["votos_invalidos_1t"] = votos["votos_invalidos"]
    data["votos_validos_1t"] = votos["votos_validos"]
    absolutos = dividir_validos(votos["votos_validos"], validos_final)
    for i, cand in enumerate(candidatos_validos):
        data[f"{cand}_abs"] = absolutos[:, i]

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

    from src.core.events import adicionar_eventos
    adicionar_eventos(df, candidatos_validos)

    return FirstRoundResult(
        df=df,
        validos_final=validos_final,
        candidatos_validos=candidatos_validos,
        info_lim_1t=info_lim_1t,
        info_indecisos=info_indecisos,
    )
