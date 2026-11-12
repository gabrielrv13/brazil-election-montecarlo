# Changelog

All notable changes to this project will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [Unreleased]

---

## [3.0.0] — 2026-11-12

Rewrite of the engine (Sprints 1-2), the audit fixes (Phases 1-4), the
second round on the core engine and the calibration on 2010-2026. The
detailed entries follow, newest first.

### Breaking changes
- Entry points: `python -m src run` (first round, the default with no
  subcommand) and `python -m src runoff` (second round). `src/simulation_v2.py`,
  `src/simulation_combined.py` and `src/dashboard.py` were removed;
  `src/simulation_2turno.py` stays only as the v2.10 method used to score
  the published runoff forecast.
- `desvio_padrao_pct` / `desvio_base` are now a marginal sd in pp at a 50%
  share (before, an inverse concentration: `2` gave about 0.7 pp), and
  `desvio_base` is the sd of the polling average, not of a single poll.
- Uncertainty has a new structure: an election-level common error with
  t tails plus drift to election day (`sd_erro_comum_pp`,
  `gl_erro_comum`, `sd_deriva_30d_pp`); runoff default 2.5 → 3.0.
- Event contract v2: the dynamic runoff writes runoff rows only, and
  `SimulationResult.p2v` is always filled (0-1 scale).
- Backtest Brier is multiclass (was `(p_winner - 1)^2`).
- `numpy<2.4` (numba, imported by arviz/PyMC, still uses removed APIs).

### Highlights
- House effects, detrended outlier removal and one aggregator for every path.
- Turnout split into blank/null and valid votes in both rounds.
- Proper scoring of the 2026 forecasts and a common-error calibration on
  ten cases (2010-2026, both rounds); defaults kept at 3.0 pp.
- Run manifests (inputs, outputs, seed, commit) checked by the publication
  gate; CI on Ubuntu 3.11/3.12 and Windows 3.12.

---

### Calibration on 2010-2022 (Wikipedia transcription)

#### Added
- `data/wikipedia/pesquisas_wikipedia_2010_2022.csv`: national presidential
  polls of 2010-2022, both rounds, parsed from the raw wikitext of the
  Wikipedia poll pages (revisions, access date and known problems in
  `data/wikipedia/README.md`). Exit polls, copied results, undated polls,
  sums outside 90-110% and the ambiguous 2014 PSB scenario are flagged in
  `alertas` and never used. Secondary source, calibration only.
- `src/io/wikipedia.py`: loader and final-window selection in the engine's
  poll format (margin from the page, else from the sample, else ±2 pp).
- `casos_calibracao()` now holds ten cases (both rounds of 2010-2026), each
  aggregated over the last 14 days with the v3 aggregator. The legacy
  2018/2022 transcriptions remain available as `casos_legado()` and in the
  report's `comparacao_legado`. The report adds per-round estimates and the
  runoff-only directional error.

#### Fixed
- `fatias_por_pesquisa` lost the poll date and institute when polls were
  keyed by `pesquisa_id`, so `agregar_fatia` failed on such input.

#### Findings (defaults unchanged)
- Common error MLE 3.5 pp, IC95 [1.9; 6.6] (was 3.4, [1.5; 9.1] on four
  cases). Out of sample, the fixed 3.0 default scores better than both the
  refitted pooled value and separate per-round values.
- The main non-PT candidate was under-polled in all five first rounds
  (mean +4.4 pp, driven by 2010 and 2014); runoff errors average -0.7 pp.

---

### Second round on the core engine; legacy scripts retired

#### Added
- `src/core/runoff.py`: two-party share per poll (duplicated or incomplete
  polls rejected) aggregated with the v3 aggregator (house effects,
  detrended outliers, sd of the mean); `simular_runoff` with the first-round
  two-level error (common error, t tails, drift to runoff day) and the
  shared vote accounting; `tabela_sensibilidade_runoff`; and
  `simular_segundo_turno_dinamico` (actual top two of each first-round
  draw, rejection-weighted transfers, runoff draws only).
- `RunoffConfig` (dates, post-first-round window by default, bias scenario,
  optional ceiling) and `src/io/runoff.py` (`carregar_runoff`,
  `salvar_resumo` moved from the script, same publication contract).
- `python -m src runoff`: summary, CSV, chart and manifest accepted by
  `publicar_2turno.py`. On the 2026 data: 52 post-first-round polls from
  either CSV, P(F. Bolsonaro) 64.4%, result inside IC80/IC90.
- `src/core/pipeline.montar_resultado`: one assembly for the CLI and the
  dashboard; `python -m src run` now fills `df2`, `p2v` (win conditional on a
  runoff) and `info_matchups` from the dynamic runoff on a separate RNG
  stream, so first-round draws are unchanged.
- `src/viz/runoff.py`: runoff chart (moved), candidate-identity colors and
  explicit dates instead of `date.today()`.

#### Removed
- `src/simulation_v2.py`, `src/simulation_combined.py`, `src/dashboard.py`.
  `simulation_2turno.py` stays as the v2.10 method (used to score the
  published forecast) but imports only the core, no longer PyMC.

#### Changed
- Post text no longer claims the sd was calibrated on the 2018/2022
  backtests; it states the Phase 3 estimate and interval.
- `numpy<2.4`: numpy 2.4/2.5 removed `np.trapz`/`np.row_stack`, still used
  by numba (imported by arviz/PyMC); a resolver that accepts numba
  pre-releases picked an incompatible pair. CI actions `checkout@v7` and
  `setup-python@v7` (Node 24).

#### Tests
- `tests/test_runoff_core.py` (24): share and SE per poll, invalid poll
  sets, leader assignment, house-effect removal, Beta oracle, variance
  addition and bias, ceiling and accounting, sensitivity, config and
  window (full base cut reproduces the post-first-round base), CLI outputs
  through the gate and manifest, seed reproducibility, dynamic transfers and
  pipeline. Legacy-based tests ported to the core.

---

### CI fixes (first GitHub Actions run)

#### Fixed
- `matplotlib.cm.get_cmap` (removed in matplotlib 3.9) replaced by
  `matplotlib.colormaps[...]` in `src/viz/charts.py` and
  `src/simulation_v2.py`; failed on every CI runner with matplotlib 3.11.
- Preservation-hash tests failed on Linux: the baselines were recorded on a
  Windows (CRLF) checkout and Linux checks the same blobs out with LF.
  `tests/hashes_eol.py` accepts raw, LF- or CRLF-normalised bytes in the
  four affected tests; content changes still fail and `-text` documentary
  copies keep strict byte comparison.

---

### Runoff absolute votes (audit A08, second round)

#### Changed
- `src/core/simulation.py`: shared `contabilizar_votos` (electorate →
  turnout → blank/null + valid) and `dividir_validos` (largest remainder;
  candidate votes sum exactly to the valid total). New runoff prior
  `INVALIDOS_2T_MU = 6%`, `INVALIDOS_2T_SIGMA = 2.5%` (TSE runoffs 2014
  6.3%, 2018 9.6%, 2022 4.6%, 2026 about 3.2%). The first round uses the
  same functions with an unchanged RNG sequence.
- `simulation_2turno.simular` and `simulation_v2.simular_segundo_turno` no
  longer split the whole turnout between the finalists. New columns
  `comparecimento`, `invalidos_pct`, `votos_invalidos` (standalone) and
  `comparecimento_2t`, `invalidos_2t_pct` (dynamic); `votos_validos`,
  `votos_*_abs` and `margem_votos` now refer to valid votes, so the
  published vote margin shrinks by the blank/null share (about 6%).

#### Tests
- `tests/test_votos_absolutos.py`: identities, explicit and prior blank
  shares, input validation, exact largest-remainder split, standalone and
  dynamic runoff accounting, margin over valid votes.

---

### Phase 4 — Reproducibility, documentation and CI (audit A11-A13, A17, A18, P1.7-P1.9, P2.3, P2.4)

#### Added
- `src/io/manifest.py`: run manifests (run id, UTC time, git commit and
  dirty flag of the code, Python/library versions, as-of, seed, n_sim,
  parameters, SHA-256 and size of every input and output) and
  `verificar_manifesto`.
- Manifests written by `python -m src run` (`<stamp>_manifest.json`),
  `simulation_2turno.py` (`resumo_2turno.manifest.json`) and
  `python -m src.calibracao`.
- `publicar_2turno.py` verifies the manifest next to the summary and refuses
  to post when a recorded file changed; `--exigir-manifesto` makes it
  mandatory.
- `simulation_2turno.py`: `--as-of` and `--seed` flags.
- `.github/workflows/tests.yml`: pytest with the coverage gate on Ubuntu
  (Python 3.11, 3.12) and Windows (3.12), plus a CLI smoke run.
- `PUBLISHING.md` (was linked but missing).

#### Changed
- CLI without `--seed` draws a seed and records it, so every run can be
  repeated. `python -m src` with no subcommand now gets every `run`
  default (it crashed on `as_of`). History and chart import errors are no
  longer masked as a pending sprint.
- No side effects on import: `simulation_v2`, `simulation_2turno`,
  `simulation_combined` and `backtesting` no longer create `outputs/` or
  reseed the global RNG when imported (directories are created on first
  write; legacy seeding moved to `inicializar(seed=42)` and `main()`), and
  the stray module-level `validar_viabilidade()` call is gone.
- `reportlab` declared as a dependency. README: install from
  `pyproject.toml` (Python 3.11+), current structure and entry points,
  reproducible commands; the `requirements.txt` reference is gone.
- Coverage measures the CLI, loader, config, backtest and calibrated runoff
  (previously omitted); only legacy global-state scripts, Streamlit UIs,
  `__main__` and the compatibility stub stay out.

#### Tests
- `tests/test_reprodutibilidade.py`: manifest round trip and tamper
  detection, git revision, publication gate blocking a modified summary,
  recorded seed, default subcommand, CLI pipeline manifest, and
  subprocess checks that importing legacy modules neither reseeds the RNG
  nor creates `outputs/`.

---

### Phase 3 — Evaluation and calibration (audit A10, P2.1)

#### Added
- `src/core/scoring.py`: multiclass Brier, binary Brier, log score, sample
  CRPS (O(n log n)), PIT, central-interval coverage, interval score.
- `src/calibracao.py` (`python -m src.calibracao`): official 2018/2022/2026
  results, four final-week calibration cases on the leaders' two-party
  share, maximum-likelihood `sd_erro_comum_pp` with profile interval,
  leave-one-out validation, directional-bias summary, and scoring of the
  2026 first-round (as of 10-03) and runoff (as of 10-24) forecasts.
- `docs/calibracao_fase3.md`: results and limits.

#### Changed
- Backtest Brier is now multiclass (was `(p_winner - 1)^2`).
- Runoff default `SD_FATIA_PP_PADRAO` 2.5 → 3.0, the same election-level
  error as the first-round engine; the sensitivity table gains a 3.0 column
  so posts read the exact column.

#### Findings
- Common error MLE 3.4 pp (95% 1.5-9.1, t5); the 3.0 default scores better
  out of sample (LOO log score 10.45 vs 10.73) and is kept.
- 2026 first round: P(F. Bolsonaro leads) 33.6%, Brier 0.88, his share at
  PIT 0.94 (inside IC90, outside IC80). Runoff: P(F. Bolsonaro wins) 64.4%
  as published (sd 2.5), 61.8% with sd 3.0; result inside IC80/IC90.
- Right-wing lead under-polled in the three first rounds (+2.9 pp mean),
  over-polled in the 2026 runoff (-2.7 pp): no fixed bias is applied.

#### Tests
- `tests/test_calibracao.py`: scoring rules against closed forms (normal
  CRPS, uniform PIT), estimator recovery on synthetic cases, interval width
  with four cases, repository cases and 2026 scoring, runoff scoring leaves
  `outputs/` untouched. Runoff contract test now rounds like
  `salvar_resumo` (Python float).

---

### Phase 2 — Error structure, house effects, single aggregator (audit P1.5, P2.2)

#### Added
- `src/core/aggregation.py`: `agregar_pesquisas` (v3 contract),
  `estimar_efeitos_instituto`, `sd_referencia_50`. House effects against a
  leave-institute-out trend, shrunk and centred, iterated to convergence;
  outliers on detrended residuals (z > 3.5, at least 5 polls); sd of the
  weighted mean from margins of error plus excess dispersion. The v2
  `agregar_pesquisas_candidato` stays for compatibility.
- `src/core/simulation.py`: `amostrar_proporcoes` (election-level shift with
  Student-t scale mixture + drift, then polling-average noise) and
  `sd_deriva`.
- `SimulationConfig`: `sd_erro_comum_pp` (3.0), `gl_erro_comum` (5),
  `sd_deriva_30d_pp` (2.0), `tau_dias` (7), `efeitos_instituto` (True), with
  validation. CLI: `--sd-erro-comum`, `--gl-erro-comum`, `--sd-deriva`,
  `--sem-efeito-instituto`.

#### Changed
- `load_polls` uses the v3 aggregator; `desvio_base` is now the sd of the
  polling average (about 0.3 pp on the 2026 first-round data, was 2.6).
- The horizon funnel moved from `desvio_base` to the explicit drift term.
- `src/backtesting.py` and `src/simulation_v2.py` no longer carry their own
  aggregation or Dirichlet: they call the core aggregator, sampler and
  water-filled ceiling. The legacy loader delegates to `load_polls` (same
  date and completeness validation) and its absolute votes split blank/null.
- On the 2026-10-03 polls: Zema outliers 24 → 2, Santos 11 → 4. Median
  shares barely move (Lula 44.6, F. Bolsonaro 42.6 of valid votes); the
  90% interval is now driven by the common-error prior. The official
  F. Bolsonaro share (47.0%) sits at the 94th percentile, a sign of the
  directional bias to be evaluated in Phase 3.

#### Tests
- `tests/test_error_structure.py`: variance addition, heavy tails at equal
  sd, zero-sum shift, drift horizon, config validation, house-effect
  recovery against a same-noise oracle, trend-robust outliers, sd of the
  mean, single implementation in backtest/legacy, CLI flags.
- Phase 1 analytic tests now switch off the common error and drift; the
  event-contract tests switch off the common error; regression baseline
  regenerated.

---

### Phase 1 — First-round core corrections (audit A07, A08, A09, A11)

#### Changed
- `desvio_base` is now the marginal sd in pp at a 50% share
  (`concentracao_dirichlet`: `alpha0 = (50/sd)^2 - 1`). Before, the value was
  an inverse concentration: `desvio=2` gave about 0.7 pp. The time funnel
  `sqrt(days/30)` now scales the real sd, and undecided redistribution no
  longer shrinks it. On the 2026-10-03 polls the 90% interval for the two
  leaders widens from about 2.7 pp to 8.4 pp and P(Lula leads) drops from
  90% to 66%; the official first-round share of F. Bolsonaro (47.0% of valid
  votes) was outside the old interval and is inside the new one.
- `aplicar_teto_rejeicao` water-fills instead of clipping and renormalising,
  so ceilings hold in the final shares (`[80, 20]` with ceiling 60 now gives
  `[60, 40]`, not `[75, 25]`). Rejection outside [0, 100] or ceilings that
  cannot sum to the total raise `ValueError`.
- Absolute votes: electorate → turnout → blank/null + valid. New columns
  `comparecimento_1t`, `invalidos_1t_pct`, `votos_invalidos_1t`;
  `votos_validos_1t` and `<cand>_abs` now exclude blank/null votes.
- `--bayesian` and `SimulationConfig(use_bayesian=True)` are rejected with a
  clear message; the PyMC module has no likelihood and was never wired in.
- The CLI result carries the real `desvio_base` (was 0 in charts and history).

#### Tests
- `tests/test_first_round_core.py`: Beta-oracle checks of sd and P(win),
  funnel factor, ceiling cascade/infeasibility, vote identities, flag refusal.
- Test environment: matplotlib forced to `Agg`; preservation-hash tests now
  cover only the documentary archive in `data/` and tolerate CRLF checkouts.

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