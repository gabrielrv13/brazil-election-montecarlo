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
import math
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
        First-round election date, used for the simulation horizon.
    as_of : date | None
        Reference for future-date validation, poll weights and simulation
        horizon. Set explicitly for reproducible historical runs. None uses
        today's date for live runs. Independent of election_date.
    scenario : str | None
        Select one value of the CSV's cenario column before validation.
        Multiple scenarios are rejected when no selection is supplied.
    required_candidates : tuple[str, ...] | None
        Candidate universe required by this simulation. None declares all
        candidates observed in the selected CSV scenario as required.
    sd_erro_comum_pp : float
        Election-level polling error shared by every poll (pp, sd of a
        candidate at 50%). Polls cannot reveal it, so it is a prior: default
        3.0, consistent with the 4-7 pp first-round misses of the leading
        right-wing candidate in 2018, 2022 and 2026. Calibrated in Phase 3.
    gl_erro_comum : float
        Degrees of freedom of the Student-t scale mixture that gives the
        common error heavy tails (> 2; ``inf`` gives a Normal-like shift).
    sd_deriva_30d_pp : float
        Opinion drift until election day, sd in pp per sqrt(30 days). Zero
        once the election date is reached.
    tau_dias : float
        Recency time constant of the poll aggregator (days).
    efeitos_instituto : bool
        Remove shrunk house effects before averaging polls.
    """

    csv_path: Path = field(default_factory=lambda: Path("data/pesquisas.csv"))
    n_sim: int = 40_000
    seed: int | None = None
    use_bayesian: bool = False
    scenario_overrides: dict = field(default_factory=dict)
    election_date: date = field(default_factory=lambda: date(2026, 10, 4))

    # Names in this simulation scenario, not a universal candidate registry.
    # None declares the candidate universe of this CSV as the scenario.
    required_candidates: tuple[str, ...] | None = None
    as_of: date | None = None
    scenario: str | None = None

    # Phase 2 error structure (see docstring). Priors until Phase 3 calibrates.
    sd_erro_comum_pp: float = 3.0
    gl_erro_comum: float = 5.0
    sd_deriva_30d_pp: float = 2.0
    tau_dias: float = 7.0
    efeitos_instituto: bool = True

    def __post_init__(self) -> None:
        self.csv_path = Path(self.csv_path)
        for nome in ("sd_erro_comum_pp", "sd_deriva_30d_pp"):
            valor = getattr(self, nome)
            if not math.isfinite(valor) or not 0 <= valor < 45:
                raise ValueError(f"{nome} must be finite and in [0, 45), got {valor!r}")
        if math.isnan(self.gl_erro_comum) or self.gl_erro_comum <= 2:
            raise ValueError(f"gl_erro_comum must be > 2, got {self.gl_erro_comum!r}")
        if not math.isfinite(self.tau_dias) or self.tau_dias <= 0:
            raise ValueError(f"tau_dias must be finite and > 0, got {self.tau_dias!r}")
        if self.as_of is not None and type(self.as_of) is not date:
            raise TypeError("as_of must be a datetime.date or None")
        if self.required_candidates is not None and not self.required_candidates:
            raise ValueError("required_candidates must not be empty")

        if self.n_sim < 1:
            raise ValueError(f"n_sim must be >= 1, got {self.n_sim}")
        if self.seed is not None and not isinstance(self.seed, int):
            raise TypeError(f"seed must be int or None, got {type(self.seed).__name__}")


@dataclass
class RunoffConfig:
    """
    Specification of one standalone runoff run (``python -m src runoff``).

    Shares the error model of :class:`SimulationConfig`; the runoff-specific
    fields are the dates, the post-first-round poll window, the bias
    scenario and the optional rejection ceiling.

    Fields
    ------
    csv_path : Path
        Runoff poll CSV (two candidates per poll).
    first_round_date, runoff_date : date
        Election days; the drift horizon runs to ``runoff_date``.
    data_min : date | None
        Ignore polls before this day. ``None`` means the day after
        ``first_round_date``: pre-first-round runoff questions are
        hypothetical matchups, a different question from the actual runoff.
    vies_pp, vies_candidato : float, str | None
        Bias scenario: shift of ``vies_pp`` toward the named candidate.
    usar_teto : bool
        Apply the rejection ceiling (off by default in a binary race).
    """

    csv_path: Path = field(default_factory=lambda: Path("data/pesquisas_2turno.csv"))
    n_sim: int = 40_000
    seed: int | None = None
    as_of: date | None = None
    first_round_date: date = field(default_factory=lambda: date(2026, 10, 4))
    runoff_date: date = field(default_factory=lambda: date(2026, 10, 25))
    data_min: date | None = None
    tau_dias: float = 7.0
    efeitos_instituto: bool = True
    sd_erro_comum_pp: float = 3.0
    gl_erro_comum: float = 5.0
    sd_deriva_30d_pp: float = 2.0
    vies_pp: float = 0.0
    vies_candidato: str | None = None
    usar_teto: bool = False

    def __post_init__(self) -> None:
        self.csv_path = Path(self.csv_path)
        for nome in ("as_of", "data_min"):
            valor = getattr(self, nome)
            if valor is not None and type(valor) is not date:
                raise TypeError(f"{nome} must be a datetime.date or None")
        if self.runoff_date <= self.first_round_date:
            raise ValueError("runoff_date must be after first_round_date")
        for nome in ("sd_erro_comum_pp", "sd_deriva_30d_pp"):
            valor = getattr(self, nome)
            if not math.isfinite(valor) or not 0 <= valor < 45:
                raise ValueError(f"{nome} must be finite and in [0, 45), got {valor!r}")
        if math.isnan(self.gl_erro_comum) or self.gl_erro_comum <= 2:
            raise ValueError(f"gl_erro_comum must be > 2, got {self.gl_erro_comum!r}")
        if not math.isfinite(self.tau_dias) or self.tau_dias <= 0:
            raise ValueError(f"tau_dias must be finite and > 0, got {self.tau_dias!r}")
        if not math.isfinite(self.vies_pp):
            raise ValueError("vies_pp must be finite")
        if self.vies_pp != 0 and not self.vies_candidato:
            raise ValueError("A nonzero vies_pp requires vies_candidato to bind its sign to a name")
        if self.n_sim < 1:
            raise ValueError(f"n_sim must be >= 1, got {self.n_sim}")
        if self.seed is not None and not isinstance(self.seed, int):
            raise TypeError(f"seed must be int or None, got {type(self.seed).__name__}")

    @property
    def janela_inicio(self) -> date:
        """First poll day used: ``data_min`` or the day after the first round."""
        from datetime import timedelta
        return self.data_min or self.first_round_date + timedelta(days=1)


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
        Final valid shares are in ``<candidate>_val``. ``vencedor`` is legacy
        argmax leadership; ``vencedor_1t`` is null without a direct winner.
        Also includes versioned event indicators/credits and diagnostics.
    df2 : pd.DataFrame
        Actual-runoff draws with tem_2turno, finalist names and valid votes
        (or explicit per-candidate win credits). Empty if not simulated.
    pv : dict[str, float]
        Deprecated legacy argmax leadership probability, in [0, 1].
        Use p_lideranca or p_vitoria_1t; pv has never measured direct victory.
        Example: ``{"Lula": 0.03, "Flávio Bolsonaro": 0.00, ...}``.
    p2v : dict[str, float]
        P(candidate wins | a second round occurs), in [0, 1].
        Includes qualification; NOT conditional on that candidate qualifying.
        Empty when no second-round simulation is available.
    p2t : float
        Probability that no candidate exceeds 50% of valid votes, in [0, 1].
    p_lideranca : dict[str, float]
        Leadership probability, sharing exact ties equally. Derived from *_val.
    p_vitoria_1t : dict[str, float]
        Direct majority victory: strictly >50% of final valid votes.
    p_classificacao_2t : dict[str, float]
        Joint probability of a runoff occurring and occupying a finalist slot.
        Exact boundary ties split remaining slots equally. Sum = 2 * p2t.
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
    desvio_base: float
        Base standard deviation propagated from ``PollData.desvio_base`` by
        the simulation engine (pp).  Required by the Polymarket entry gate
        (``desvio_base <= 8pp`` in the primary window) and by backtesting
        calibration audits.  Default 0.0 only for test fixtures; production
        code always receives a non-zero value from ``PollData``.
    timestamp : datetime
        UTC timestamp set automatically at object creation. Used by
        ``history.py`` to order forecasts chronologically.
    config : SimulationConfig | None
        The config that produced this result.  ``None`` only when constructing
        result objects in tests without a full config.  Production code always
        sets this field.
    """

    df1: pd.DataFrame
    df2: pd.DataFrame
    pv: dict[str, float]   # deprecated legacy argmax leadership, scale 0–1 (multiply by 100 for display)
    p2v: dict[str, float]  # win probability, scale 0–1 (multiply by 100 for display)
    p2t: float
    info_matchups: dict
    info_lim_1t: dict
    info_indecisos: dict
    margins: np.ndarray
    desvio_base: float = 0.0 # propagated from PollData; used by Polymarket entry gate (≤ 8pp) and calibration audit
    timestamp: datetime = field(default_factory=datetime.utcnow)
    config: SimulationConfig | None = None

    # Derived exclusively from final valid-vote draws (empty for legacy results).
    # Leadership and qualification split exact tie credits equally; no new draws.
    p_lideranca: dict[str, float] = field(default_factory=dict, init=False)
    p_vitoria_1t: dict[str, float] = field(default_factory=dict, init=False)
    p_classificacao_2t: dict[str, float] = field(default_factory=dict, init=False)
    event_contract_version: int = field(default=1, init=False)

    def __post_init__(self) -> None:
        from .events import resumir_eventos, probabilidades_vitoria_2t
        events = resumir_eventos(self.df1)
        for key, value in events.items():
            setattr(self, key, value)
        if self.event_contract_version == 2:
            # A legacy aggregate or hypothetical draw is insufficient evidence
            # for a probability conditional on an actual runoff.
            self.p2v = (probabilidades_vitoria_2t(self.df2, list(self.p_lideranca))
                        if self.p2t > 0 and "tem_2turno" in self.df2 else {})
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
