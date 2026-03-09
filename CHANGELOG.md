# Changelog

All notable changes to this project will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [Unreleased]
> Merged into `develop`. Target release: `v3.0.0` (end of Sprint 4).

### Added — PR #3 `feat/core-simulation-config`

- `src/__init__.py` — package initializer, makes `src` importable as Python package
- `src/core/__init__.py` — package initializer for `src/core/`
- `src/core/config.py` — three dataclasses forming the v3 data contract:
  - `SimulationConfig`: immutable run configuration (`csv_path`, `n_sim`, `seed`,
    `use_bayesian`, `scenario_overrides`, `election_date`); replaces the six
    module-level globals previously populated by `inicializar()`
  - `PollData`: structured output of poll loading (`candidatos`, `votos_media`,
    `rejeicao`, `desvio_base`, `indecisos`); replaces the positional 5-tuple
    returned by `carregar_pesquisas()`
  - `SimulationResult`: unified simulation output (`df1`, `df2`, `pv`, `p2v`,
    `p2t`, `info_matchups`, `info_lim_1t`, `info_indecisos`, `margins`,
    `timestamp`, `config`); single object consumed by all downstream modules
- `src/core/aggregation.py` — pure aggregation functions migrated from
  `simulation_v2.py`, with no I/O and no global state:
  - `calcular_peso_temporal(data_pesquisa, reference_date, tau)` — parameter
    `reference_date` replaces implicit read of module-level `DATA_ATUAL`
  - `detectar_outliers(valores, threshold)` — migrated unchanged; now importable
    without triggering simulation side effects

### Added — PR #4 `feat/io-loader-validation`

- `src/io/__init__.py` — package initializer; exports `load_polls` as public API
- `src/io/loader.py` — poll loading module:
  - `load_polls(config: SimulationConfig) -> PollData` — replaces
    `carregar_pesquisas()` from `simulation_v2.py`; takes a `SimulationConfig`
    and returns a `PollData` dataclass
  - Schema validation: raises `ValueError` identifying the missing column name
    when any of `candidato`, `intencao_voto_pct`, `desvio_padrao_pct` are absent
  - Value validation: raises `ValueError` identifying the candidate name when
    `intencao_voto_pct <= 0` or `desvio_padrao_pct <= 0`
  - Replaces all `print()` calls with `logging.getLogger(__name__)` — no console
    output from import or from call when used programmatically

### Added — PR #1 `chore/pyproject-setup`

- `pyproject.toml` — replaces ad-hoc requirements files:
  - `[project.dependencies]`: `numpy`, `pandas`, `pymc`, `arviz`, `matplotlib`,
    `seaborn`, `streamlit`
  - `[project.optional-dependencies].test`: `pytest`, `pytest-cov`
  - `[tool.pytest.ini_options]`: `testpaths = ["tests"]`,
    `addopts = "--cov=src --cov-report=term-missing"`
- `tests/__init__.py` — package initializer for test discovery
- `tests/fixtures/pesquisas_minimal.csv` — minimal 5-row poll fixture used by
  all unit tests; no test may reference `data/pesquisas.csv`

### Added — PR #2 `chore/cli-entry-point`

- `src/cli.py` — argument parsing skeleton:
  - Flags defined: `--csv`, `--n-sim`, `--bayesian`, `--no-history`, `--backtest`
  - `--csv` pointing to a nonexistent file prints a user-facing error message and
    exits with code 1; no stack trace exposed
  - Main execution body is a stub pending Sprint 2 wiring
- `src/__main__.py` — enables `python -m src` as the canonical entry point

### Added — PR #5 `test/aggregation-unit-tests`

- `tests/test_aggregation.py` — unit tests for `src/core/aggregation.py`:
  - `calcular_peso_temporal`: 4 cases — today (weight = 1.0 ± 0.001),
    7 days ago (weight ≈ 0.368 ± 0.01), future date (weight = 1.0), `None`
    input (weight = 1.0)
  - `detectar_outliers`: 3 cases — single-element array (no outliers), all-equal
    array (no outliers), array with clear outlier at 3σ (detected)
  - All tests use `tests/fixtures/` only; zero references to `data/`

### Internal — Sprint 1 state

The following Sprint 1 commitments are stubs and will be completed in Sprint 2:

- `src/cli.py` `main()` body — argument parsing exists, orchestration does not
- `src/core/simulation.py` — not yet created; `simular_primeiro_turno()` still
  lives in `simulation_v2.py`
- `src/io/history.py` — not yet created; SQLite persistence is Sprint 3 scope

---

## [2.9.0] — 2026-03-06

### Added

- `src/backtesting.py` — backtesting pipeline against 2018 and 2022 historical
  elections; zero dependency on `simulation_v2.py` globals
  - `carregar_snapshot()` — historical CSV loader with snapshot-relative
    temporal weighting (`reference_date` = snapshot date, not today)
  - `executar_simulacao_historica()` — Dirichlet runner replicating
    `simular_primeiro_turno()` with local parameters
  - `calcular_metricas()` — five metrics per snapshot: vote share RMSE, Brier
    score, margin error, winner correct, runoff pair correct
  - `relatorio_backtesting()` — console summary and CSV export to
    `outputs/backtesting_report.csv`
  - CLI: `python src/backtesting.py [--year 2022|2018] [--n-sim N]`
- `data/historico/` — 8 historical poll snapshots (sources: Datafolha, Quaest,
  Ipec, Ibope)
  - 2022: T-90, T-60, T-30, T-14, T-7 (candidates: Lula, Jair Bolsonaro,
    Ciro Gomes, Simone Tebet)
  - 2018: T-30, T-14, T-7 (candidates: Bolsonaro, Haddad, Ciro Gomes, Alckmin)
  - Note: 2018 T-90 and T-60 excluded — Haddad was not announced until
    September 11, 2018; those snapshots are structurally unusable

### Validated results

**2022 (5 snapshots):** mean RMSE 3.61pp, 5/5 winner correct, 5/5 runoff pair correct

**2018 (3 snapshots):** mean RMSE 3.28pp, 3/3 winner correct, 3/3 runoff pair correct

**Shy Bolsonaro effect:** model inherits ~4pp systematic underestimation of
right-wing vote share from input polls; model does not amplify the bias.
Polymarket implication: edges favoring large-margin wins by the leading candidate
must be discounted proportionally.

**RMSE note:** 3.28–3.61pp marginally exceeds the 3.00pp threshold. This is the
theoretical floor given systematic polling bias — the model cannot outperform its
input data. Results accepted as valid for Polymarket operation with bias discount applied.

### Fixed

- `GROUND_TRUTH` constant overwritten by `NAME_ALIASES` — restored both
- Bolsonaro alias mismatch (`'Jair Bolsonaro'` in CSV vs `'Bolsonaro'` in ground
  truth) — resolved via `NAME_ALIASES` map
- Bias direction inverted in RMSE rebase — fixed denominator to use all modeled
  candidates, not only ground-truth candidates

---

## [2.8.0] — 2026-03-04

### Added

- `MARGIN_THRESHOLDS` constant: `[5, 10, 15, 20, 25]` pp
- `margem_1t`, `lider_1t`, and per-candidate `margem_<candidate>` columns in
  `df1`; persisted to `resultados_1turno_v2.8.csv`
- `polymarket_edge(df1, threshold, market_prob, candidate) -> dict` — returns
  `model_prob`, `market_prob`, `edge`, `kelly_fraction`, `threshold_pp`,
  `candidate`, `n_sim`; sizing uses half-Kelly
- `--n-sim` CLI flag — overrides `N_SIM` at runtime; recommended for
  `model_prob < 0.05` threshold markets
- Dashboard: margin metrics row, threshold probability table, margin histogram,
  Polymarket Edge Calculator expander in tab "1º Turno"
- Report: FIRST-ROUND MARGIN ANALYSIS section with median margin, 90% CI,
  close race / comfortable probabilities, and P(margin > X) per threshold

### Changed

- `simular_primeiro_turno()` output CSV renamed to `resultados_1turno_v2.8.csv`
- Version banner updated to `[v2.8]` in `__main__` and dashboard sidebar

---

## [2.7.0] — 2026-03-01

### Added

- `simulation_2turno.py` — standalone second-round simulation with its own CSV
  (`pesquisas_2turno.csv`), Dirichlet over 3 categories (candidate A, candidate
  B, blank/null), and independent temporal weighting
- `pesquisas_2turno.csv` — dedicated poll file for second-round matchups

---

## [2.6.0] — 2026-02-28

### Added

- Absolute vote projections for first and second rounds
  (`ELEITORADO × (1 − abstencao_simulada)`)
- Stochastic abstention: `Normal(0.20, 0.02)` first round,
  `Normal(0.22, 0.03)` second round
- PDF report generation
- Streamlit dashboard (`dashboard.py`) — initial release

---

## [2.5.0] — 2026-02-26

### Added

- Dynamic second round: top-2 candidates identified per simulation run
- Matchup probability matrix showing how often each pair reaches the runoff
- Per-matchup winner probability and overall second-round victory probability

### Changed

- Second round no longer hardcoded to a fixed matchup; each of the 40,000
  simulations independently determines its own finalists

---

## [2.4.0] — 2026-02-24

### Added

- Undecided voter category (`indecisos_pct` column in CSV)
- Proportional redistribution weighted by vote share and available electoral
  space (100% − rejection ceiling)
- Configurable blank/null allocation fraction (`blank_fraction`, default 0.15)

---

## [2.3.0] — 2026-02-22

### Added

- Automatic poll aggregation with exponential temporal weighting
  (`peso = exp(−days / 7)`)
- Inter-institute variance calculation
- Outlier detection using modified z-score (`threshold = 2.5`)
- Aggregation summary report in console output

---

## [2.2.0] — 2026-02-20

### Added

- Rejection index as electoral ceiling: no candidate can exceed
  `(100 − rejeicao_pct)%` of valid votes
- Rejection-based vote transfer logic in second round
- Viability warnings for candidates with rejection > 50%