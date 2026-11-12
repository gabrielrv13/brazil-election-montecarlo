"""
Single assembly of a full forecast: first round + dynamic runoff → SimulationResult.

Used by the CLI (``python -m src run``) and the Streamlit dashboard, so both
publish exactly the same events. Pure: no I/O.
"""

from __future__ import annotations

import numpy as np

from src.core.config import PollData, SimulationConfig, SimulationResult
from src.core.runoff import simular_segundo_turno_dinamico
from src.core.simulation import FirstRoundResult, simular_primeiro_turno


def montar_resultado(
    config: SimulationConfig,
    poll_data: PollData,
    primeiro: FirstRoundResult | None = None,
) -> SimulationResult:
    """Run the first round (unless given) and the dynamic runoff.

    The runoff uses its own generator stream derived from ``config.seed``
    (``SeedSequence([seed, 2])``), so adding it does not change the
    first-round draws of a seeded run.
    """
    first = primeiro if primeiro is not None else simular_primeiro_turno(config, poll_data)
    rejeicao = np.array([
        poll_data.rejeicao[poll_data.candidatos.index(c)] for c in first.candidatos_validos
    ], dtype=float)
    rng = (np.random.default_rng(np.random.SeedSequence([config.seed, 2]))
           if config.seed is not None else np.random.default_rng())
    df2, info_matchups = simular_segundo_turno_dinamico(
        first.validos_final, first.candidatos_validos, rejeicao, rng,
    )
    pv = {c: float((first.df["vencedor"] == c).mean()) for c in first.candidatos_validos}
    return SimulationResult(
        df1=first.df,
        df2=df2,
        pv=pv,
        p2v={},  # derived from df2 by SimulationResult (P(win | runoff), contract v2)
        p2t=float(first.df["tem_2turno"].mean()),
        desvio_base=float(poll_data.desvio_base),
        info_matchups=info_matchups,
        info_lim_1t=first.info_lim_1t,
        info_indecisos=first.info_indecisos,
        margins=first.df["margem_1t"].to_numpy(),
        config=config,
    )
