# src/core/config.py
"""
Core data contracts for brazil-election-montecarlo v3.0.

This module defines the three canonical dataclasses that every other module
in the project consumes. It has zero side effects: no I/O, no matplotlib,
no streamlit. It may only import from the standard library, numpy, and pandas.

Freezing these contracts early is intentional — downstream developers (I/O,
Viz, CLI, Tests) all depend on these interfaces. Any field addition requires
a minor version bump; any field removal or type change requires a major bump.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Input contract
# ---------------------------------------------------------------------------

@dataclass
class SimulationConfig:
    """
    Immutable specification of a single simulation run.

    Replaces the six module-level globals (CANDIDATOS, VOTOS_MEDIA, REJEICAO,
    DESVIO_BASE, INDECISOS, CORES) that ``inicializar()`` populated in v2.x.
    Creating two ``SimulationConfig`` instances with different parameters is
    sufficient to run two independent scenarios in the same process — no global
    state is involved.

    Fields
    ------
    csv_path : Path
        Location of the poll CSV file.  Relative paths are resolved from the
        working directory at call time, not from this file's location.
    n_sim : int
        Number of Monte Carlo draws.  40 000 is appropriate for general use;
        200 000 is recommended when ``model_prob < 0.05`` (tail markets).
    seed : int | None
        RNG seed for reproducibility.  ``None`` produces a non-deterministic
        run, which is the default for production.
    use_bayesian : bool
        When ``True``, the simulation engine uses PyMC MCMC sampling instead
        of the Dirichlet-based frequentist approach.  Adds ~60 s per run.
    scenario_overrides : dict
        Optional per-candidate overrides applied after poll aggregation.
        Keys are candidate names; values are dicts of field → value, e.g.::

            {"Lula": {"votos_media": 35.0, "rejeicao": 40.0}}

        Used by the backtesting module to inject ground-truth snapshots and
        by the CLI ``--scenario`` flag for what-if analysis.
    election_date : date
        First-round election date.  Temporal weighting in the aggregator uses
        this to anchor the decay curve.  Default is 2026-10-04.
    """

    csv_path: Path = field(default_factory=lambda: Path("data/pesquisas.csv"))
    n_sim: int = 40_000
    seed: int | None = None
    use_bayesian: bool = False
    scenario_overrides: dict = field(default_factory=dict)
    election_date: date = field(default_factory=lambda: date(2026, 10, 4))

    def __post_init__(self) -> None:
        self.csv_path = Path(self.csv_path)

        if self.n_sim < 1:
            raise ValueError(f"n_sim must be >= 1, got {self.n_sim}")
        if self.seed is not None and not isinstance(self.seed, int):
            raise TypeError(f"seed must be int or None, got {type(self.seed).__name__}")


# ---------------------------------------------------------------------------
# Aggregated poll contract  (output of src/io/loader.py)
# ---------------------------------------------------------------------------

@dataclass
class PollData:
    """
    Aggregated, validated poll data ready for Monte Carlo consumption.

    Produced exclusively by ``src.io.loader.load_polls(config)``.  No function
    in ``src/core/`` constructs this directly — the separation ensures that core
    simulation logic never touches disk or raw CSV parsing.

    All arrays are parallel: ``votos_media[i]``, ``rejeicao[i]``, and the
    corresponding entry in ``candidatos[i]`` all refer to the same candidate.

    Fields
    ------
    candidatos : list[str]
        Candidate names in the order they appear after aggregation (typically
        sorted by descending vote intention).
    votos_media : np.ndarray
        Weighted-mean vote intention for each candidate, in percentage points
        (not fractions).  Shape: ``(n_candidates,)``.
    rejeicao : np.ndarray
        Weighted-mean rejection rate for each candidate, in percentage points.
        Used as the electoral ceiling in ``aplicar_teto_rejeicao()``.
        Shape: ``(n_candidates,)``.
    desvio_base : float
        Mean of the aggregated per-candidate standard deviations, in percentage
        points.  Used as the base noise term in Dirichlet sampling.
    indecisos : float
        Weighted-mean share of undecided voters, in percentage points.
        Redistributed before each simulation draw via
        ``distribuir_indecisos()``.
    """

    candidatos: list[str]
    votos_media: np.ndarray
    rejeicao: np.ndarray
    desvio_base: float
    indecisos: float

    def __post_init__(self) -> None:
        n = len(self.candidatos)
        if self.votos_media.shape != (n,):
            raise ValueError(
                f"votos_media shape {self.votos_media.shape} does not match "
                f"len(candidatos)={n}"
            )
        if self.rejeicao.shape != (n,):
            raise ValueError(
                f"rejeicao shape {self.rejeicao.shape} does not match "
                f"len(candidatos)={n}"
            )
        if self.desvio_base < 0:
            raise ValueError(f"desvio_base must be >= 0, got {self.desvio_base}")
        if not (0.0 <= self.indecisos <= 100.0):
            raise ValueError(
                f"indecisos must be in [0, 100], got {self.indecisos}"
            )


# ---------------------------------------------------------------------------
# Simulation output contract
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    """
    Complete, self-contained output of one simulation run.

    Every downstream consumer — ``dashboard.py``, ``report.py``,
    ``history.py``, ``polymarket_edge()`` — reads exclusively from this
    dataclass.  None of them need to know how the simulation was computed.

    Lifecycle
    ---------
    1. ``src.core.simulation.simulate(config, poll_data)`` constructs and
       returns a ``SimulationResult``.
    2. ``src.io.history.save_result(result)`` serialises it to SQLite.
    3. ``src.viz.charts.render_*(result)`` reads ``df1``, ``df2``, ``margins``
       to produce matplotlib Figures.
    4. ``src.io.report.generate_pdf(result)`` renders the PDF report.

    Fields
    ------
    df1 : pd.DataFrame
        Per-simulation first-round vote shares.
        Columns: one per candidate + ``"winner"`` (name) + ``"margin"`` (pp).
        Shape: ``(n_sim, n_candidates + 2)``.
    df2 : pd.DataFrame
        Per-simulation second-round results for the most likely runoff pair.
        Columns: candidate names + ``"winner"``.
        Shape: ``(n_sim, 3)`` for a two-candidate runoff.
    pv : dict[str, float]
        First-round outright win probability per candidate, in [0, 1].
        Example: ``{"Lula": 0.03, "Flávio Bolsonaro": 0.00, ...}``.
    p2v : dict[str, float]
        Second-round win probability per candidate (conditional on reaching
        the second round), in [0, 1].
    p2t : float
        Probability that the election goes to a second round, in [0, 1].
    info_matchups : dict
        Head-to-head second-round matchup probabilities.
        Keys are ``"CandA vs CandB"`` strings; values are floats in [0, 1].
    info_lim_1t : dict
        Diagnostics from the rejection-ceiling step: per-candidate ceiling
        values and how many draws were clipped.
    info_indecisos : dict
        Diagnostics from undecided redistribution: original undecided share,
        redistribution method used, and per-candidate allocation.
    margins : np.ndarray
        First-round margin distribution: winner's share minus runner-up's
        share across all simulations, in percentage points.
        Shape: ``(n_sim,)``.  Used for Polymarket margin markets.
    timestamp : datetime
        UTC timestamp set automatically at object creation.  Used by
        ``history.py`` to order forecasts chronologically.
    config : SimulationConfig | None
        The config that produced this result.  ``None`` only when constructing
        result objects in tests without a full config.  Production code always
        sets this field.
    """

    df1: pd.DataFrame
    df2: pd.DataFrame
    pv: dict[str, float]   # win probability, scale 0–1 (multiply by 100 for display)
    p2v: dict[str, float]  # win probability, scale 0–1 (multiply by 100 for display)
    p2t: float
    info_matchups: dict
    info_lim_1t: dict
    info_indecisos: dict
    margins: np.ndarray
    timestamp: datetime = field(default_factory=datetime.utcnow)
    config: SimulationConfig | None = None

    def __post_init__(self) -> None:
        if not (0.0 <= self.p2t <= 1.0):
            raise ValueError(f"p2t must be in [0, 1], got {self.p2t}")

        for cand, prob in self.pv.items():
            if not (0.0 <= prob <= 1.0):
                raise ValueError(
                    f"pv['{cand}'] = {prob} is outside [0, 1]"
                )
        for cand, prob in self.p2v.items():
            if not (0.0 <= prob <= 1.0):
                raise ValueError(
                    f"p2v['{cand}'] = {prob} is outside [0, 1]"
                )