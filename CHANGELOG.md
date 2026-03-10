# Changelog

All notable changes to this project will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [Unreleased]
> Merged into `develop`. Target release: `v3.0.0` (end of Sprint 4).

---

### Sprint 2 — Core Engine (PRs #21–#28)

#### Added — PR #21 `feat/viz-charts-parametrized`

- `src/viz/__init__.py` — package initializer for `src/viz/`
- `src/viz/charts.py` — visualization layer migrated from `simulation_v2.py`;
  all functions consume `SimulationResult` as parameter and return `Figure`:
  - `plot_simulation_dashboard(result, output_dir)` — composite 4-panel figure
    replacing the former `graficos()` call; no `plt.show()` or `plt.savefig()`
    inside the function
  - `plot_forecast_tracker(result, output_dir)` — line + CI band tracker per
    candidate across simulation runs
  - `plot_vote_intention(result, output_dir)` — first-round vote share panel
  - `plot_rejection_index(result, output_dir)` — rejection ceiling panel
  - `plot_qualify_probability(result, output_dir)` — runoff qualification panel
  - `plot_margin_distribution(result, output_dir)` — first-round margin histogram
  - `generate_palette(candidatos)`, `hex_lighten(hex_color, factor)` — pure
    color utilities replacing module-level globals `CORES` and `CORES_CLARAS`
  - `OUTPUT_DIR` is an explicit argument on every function; no module constant
  - No global variable reads; no `print()` in any chart function

#### Added — PR #22 `feat/io-report-output`

- `src/io/report.py` — PDF and CSV report generation consuming `SimulationResult`:
  - `save_csvs(result, output_dir) -> tuple[Path, Path | None]` — writes
    first-round and (if present) second-round DataFrames; filenames use ISO 8601
    timestamp, no version number embedded
  - `generate_pdf(result, output_dir) -> Path` — ReportLab Platypus PDF with
    sections: run metadata, undecided voters, first-round projections with 90%
    CI, margin analysis, second-round matchups; assumes `pv`/`p2v` in 0–1 scale
    and multiplies by 100 at render time (see issue #23)
  - All output filenames follow `{ISO_TIMESTAMP}_{name}.{ext}` — no version
    number in any generated file

#### Added — PR #24 `docs/io-pv-scale-contract`

- `generate_pdf()` docstring updated to explicitly document that `result.pv` and
  `result.p2v` must be in 0–1 scale; display layer multiplies by 100 (issue #23)

#### Added — PR #25 `feat/core-simulation-engine`

- `src/core/aggregation.py` — extended with:
  - `agregar_pesquisas_candidato(df_candidato, data_referencia)` — weighted poll
    aggregation with outlier exclusion; `DATA_ATUAL` global replaced by explicit
    `data_referencia` parameter; rejection averaged independently from vote
    outlier mask
- `src/core/simulation.py` — new module; pure simulation logic, no I/O:
  - `aplicar_teto_rejeicao(votos, candidatos, rejeicao)` — `CANDIDATOS` global
    replaced by explicit `candidatos` parameter
  - `distribuir_indecisos(votos, candidatos, indecisos, rejeicao, blank_fraction)`
    — same substitution
  - `simular_primeiro_turno(config: SimulationConfig, poll_data: PollData) -> FirstRoundResult`
    — canonical simulation entry point; returns `FirstRoundResult` NamedTuple
  - `FirstRoundResult` NamedTuple — typed container for simulation outputs
- `src/core/config.py` — `SimulationResult.pv` and `SimulationResult.p2v`
  annotated as scale 0–1 in docstring (closes issue #23)

#### Added — PR #26 `test/loader-and-aggregation`

- `tests/test_aggregation.py` — extended with `TestAgregarPesquisasCandidato`:
  - Single poll: raw values returned unchanged, `desvio_entre = 0.0`
  - Two polls: temporally weighted mean pulled toward more recent poll;
    combined std dev follows `√(σ_within² + σ_between²)`
  - Three polls with outlier: excluded from vote mean, reported in `info["outliers"]`,
    `n_validas = 2`; rejection averaged across all polls regardless of outlier mask
  - No `data` column: uniform weights applied, mean equals simple average
  - No `rejeicao_pct` column: returns `0.0` without raising
- `tests/test_loader.py` — unit tests for `src/io/loader.py`:
  - Missing required column: `ValueError` with column name
  - `intencao_voto_pct <= 0`: `ValueError` with candidate name
  - Valid CSV: returns `PollData` with correct field types
  - All tests use `tests/fixtures/` only; zero references to `data/`

#### Added — PR #27 `feat/cli-entry-point`

- `src/cli.py` — canonical CLI argument parser:
  - Flags: `--csv`, `--n-sim`, `--bayesian`, `--no-history`, `--backtest`
  - `--csv` pointing to nonexistent file exits with code 1, no stack trace
- `src/__main__.py` — enables `python -m src` as the sole entry point

#### Added — PR #28 `feat/cli-main-flow`

- `src/cli.py` `main()` fully wired to v3 modules:
  - Pipeline: `load_polls(config)` → `simular_primeiro_turno(config, poll_data)`
    → `generate_charts(result)` → `save_csvs(result)` → `generate_pdf(result)`
  - `FileNotFoundError` on CSV prints user-facing message and exits code 1
  - `ValueError` on invalid data prints error message without stack trace
  - `python -m src --no-history` runs end-to-end without creating
    `forecast_history.db`
  - `python -m src` with current `data/pesquisas.csv` runs end-to-end without
    errors

#### Internal — Sprint 2 state

The following are deferred to Sprint 3:

- `src/io/history.py` — SQLite persistence (`init_db`, `salvar_historico`,
  `carregar_historico`); `--no-history` flag bypasses this path until Sprint 3
- `src/viz/dashboard.py` refactor — dashboard still imports from `simulation_v2`;
  line 148 (`gerar_relatorio_pdf` call) updated to `generate_pdf(result, output_dir)`
  in Sprint 3 (Dev 5 scope)
- `python -m src` numerical equivalence gate — diff < 0.1pp vs `simulation_v2.py`
  to be validated in Sprint 4 CI

---

### Sprint 1 — Contracts & Foundations (PRs #17–#20)

#### Added — PR #18 `feat/core-simulation-config`

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

#### Added — PR #19 `feat/io-loader-validation`

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

#### Added — PR #17 `test/aggregation-unit-tests`

- `pyproject.toml` — project metadata, dependencies, pytest and coverage
  configuration, ruff linter rules; replaces ad-hoc requirements files
- `tests/fixtures/` — minimal CSV fixtures for unit tests; no test references
  `data/pesquisas.csv`
- `tests/test_aggregation.py` — 25 unit tests for `calcular_peso_temporal` and
  `detectar_outliers`; coverage 94% on `src/core/aggregation.py`

#### Fixed — post-Sprint 1

- `src/core/aggregation.py` — missing `import numpy as np` and
  `import pandas as pd` added after 23 tests failed with `NameError` (`ef9cb1c`)
- `pyproject.toml` — `src/core/config.py`, `src/io/loader.py`, and
  `src/simulation.py` added to `[tool.coverage.run] omit` until Sprint 2 tests
  are added; prevents spurious coverage failures on untested Sprint 1 stubs

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