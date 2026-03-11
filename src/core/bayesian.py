"""
Bayesian MCMC model for brazil-election-montecarlo.

This module is the only place in src/core/ where PyMC is imported. It is called exclusively when ``config.use_bayesian is True``.

All other simulation paths use the Dirichlet frequentist sampler in ``src.core.simulation``, which is ~60 s faster per run.
"""

from __future__ import annotations

import numpy as np
import pymc as pm
import arviz as az

from src.core.config import PollData, SimulationConfig
from src.core.simulation import distribuir_indecisos, _calcular_desvio_ajustado
from datetime import date


def construir_modelo(
    config: SimulationConfig,
    poll_data: PollData,
) -> az.InferenceData:
    """
    Build and sample a Bayesian Dirichlet model of first-round vote shares.

    Uses PyMC with a Dirichlet prior whose concentration parameters are derived from the aggregated poll data.  Undecided voters are redistributed before parameterising the prior, using the same logic as the frequentist path in :func:`~src.core.simulation.simular_primeiro_turno`.

    This function should only be called when ``config.use_bayesian is True``.
    The caller (``src.cli`` or ``src.core.simulation``) is responsible for that guard — this module does not check it.

    Parameters
    ----------
    config:
        Simulation configuration.  Uses ``seed`` and ``election_date``.``n_sim`` is not used here; MCMC draw count is fixed at 10 000 draws × 4 chains = 40 000 posterior samples to match the
        frequentist default.
    poll_data:
        Aggregated poll data produced by ``src.io.loader.load_polls``.

    Returns
    -------
    az.InferenceData
        ArviZ InferenceData object containing the posterior trace.
        Pass to ``az.summary()`` or use ``.posterior["votos_proporcao"]`` to extract samples.

    Raises
    ------
    ValueError
        If any effective vote share is NaN or <= 0 after undecided redistribution, which would cause Dirichlet initialisation to fail.

    Notes
    -----
    The concentration factor is computed as ``100 / desvio_ajustado``, matching the frequentist Dirichlet parameterisation.  Higher desvio (more uncertainty) → lower concentration → wider posterior.
    """
    candidatos = poll_data.candidatos
    votos_media = poll_data.votos_media.copy()
    rejeicao = poll_data.rejeicao
    desvio_base = poll_data.desvio_base
    indecisos = poll_data.indecisos

    # ── Temporal uncertainty adjustment ───────────────────────────────────────
    desvio = _calcular_desvio_ajustado(desvio_base, config.election_date, date.today())

    # ── Undecided voter redistribution ────────────────────────────────────────
    votos_efetivos = votos_media.copy()
    if indecisos > 0:
        votos_efetivos, _ = distribuir_indecisos(
            votos_media, indecisos, rejeicao, candidatos
        )

    # ── Sanity checks (Dirichlet requires all alpha > 0) ──────────────────────
    if np.any(np.isnan(votos_efetivos)):
        raise ValueError(
            f"votos_media contains NaN after undecided redistribution: "
            f"{list(zip(candidatos, votos_efetivos))}\n"
            "Check the CSV for missing or invalid intencao_voto_pct values."
        )
    if np.any(votos_efetivos <= 0):
        bad = [candidatos[i] for i, v in enumerate(votos_efetivos) if v <= 0]
        raise ValueError(
            f"Candidates with zero or negative vote share after redistribution: {bad}\n"
            "Dirichlet requires all alpha parameters > 0."
        )

    # ── PyMC model ────────────────────────────────────────────────────────────
    fator_concentracao = 100.0 / desvio
    alphas = votos_efetivos * fator_concentracao

    with pm.Model():
        votos_proporcao = pm.Dirichlet(
            "votos_proporcao",
            a=alphas,
            shape=len(candidatos),
        )
        for i, cand in enumerate(candidatos):
            var_name = (
                cand.replace(" ", "_").replace("/", "_").replace("-", "_")
            )
            pm.Deterministic(var_name, votos_proporcao[i] * 100)

        trace = pm.sample(
            draws=10_000,
            tune=2_000,
            chains=4,
            return_inferencedata=True,
            random_seed=config.seed if config.seed is not None else 42,
        )

    return trace