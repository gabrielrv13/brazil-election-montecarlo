# brazil-election-montecarlo

Monte Carlo simulation for the 2026 Brazilian presidential election — poll aggregation with house effects, a two-level error model (common election error with heavy tails, drift, polling-average noise), rejection ceilings, a calibrated runoff model, proper-scoring evaluation and reproducible run manifests.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-3.0.0--dev-green.svg)](CHANGELOG.md)
[![Tests](https://github.com/gabrielrv13/brazil-election-montecarlo/actions/workflows/tests.yml/badge.svg)](https://github.com/gabrielrv13/brazil-election-montecarlo/actions/workflows/tests.yml)

---
## Inspiration

Inspired by the Hungarian election visualization published on [r/dataisbeautiful](https://www.reddit.com/r/dataisbeautiful/s/ZspHq3TH3R) by [u/Exciting-Lab1263](https://www.reddit.com/user/Exciting-Lab1263/), which applied Monte Carlo simulation to the 2026 Hungarian parliamentary election using the [Chronicler-v2 methodology](https://www.szazkilencvenkilenc.hu/methodology-v2/). This project adapts the same core approach to the Brazilian electoral context.

---
## Overview

| Entry point | What it does |
|---|---|
| `python -m src run` | **Canonical first-round forecast.** Loads and validates `data/pesquisas.csv`, aggregates polls (`src/core/aggregation.py`), simulates (`src/core/simulation.py`), writes CSV/PNG/PDF, the SQLite history and a run manifest. |
| `python src/simulation_2turno.py` | Standalone runoff once the finalists are known: two-party-share aggregation, explicit sd (default 3.0 pp), bias sensitivity, summary JSON and manifest. |
| `python -m src.calibracao` | Scores the 2026 forecasts against the official results and calibrates the common error (see *Evaluation and calibration*). |
| `python src/retrospectiva_1t.py` | First-round poll average versus the official result, per candidate. |
| `python src/publicar_2turno.py` | Publication gate: validates the runoff summary and its manifest, then writes PT/EN posts. |
| `python -m src backtest` | Historical backtest (2018/2022) through the same core aggregator and sampler. |
| `streamlit run src/viz/dashboard.py` | Interactive dashboard on the modular engine. |

`src/simulation_v2.py`, `src/simulation_combined.py` and `src/dashboard.py` are the pre-v3 global-state scripts. They now delegate aggregation, sampling and the ceiling to `src/core`, and are kept only for compatibility.

---

## Features

| Version | Feature |
|---|---|
| v2.2 | Rejection index as electoral ceiling |
| v2.3 | Poll aggregation — temporal weighting + outlier detection |
| v2.4 | Undecided voter redistribution (rejection-adjusted) |
| v2.5 | Dynamic second round from actual per-simulation top-2 |
| v2.6 | Absolute vote projections + stochastic abstention + PDF report + Streamlit dashboard |
| v2.7 | Standalone second-round simulation (`simulation_2turno.py`) |
| v2.8 | First-round margin distribution, `polymarket_edge()`, `--n-sim` flag |
| v2.9 | Backtesting module against the 2018 and 2022 elections |
| v2.10 | Calibrated runoff: two-party-share aggregation, explicit uncertainty, bias sensitivity, publication step |
| v3.0-dev | sd in pp, water-filled ceiling, turnout accounting; house effects, common error with heavy tails, single aggregator; proper scoring and calibration; run manifests and CI (see [CHANGELOG](CHANGELOG.md)) |

---

## Repository Structure

```
brazil-election-montecarlo/
├── src/
│   ├── cli.py, __main__.py       # python -m src run | backtest
│   ├── core/                     # pure logic: config, aggregation, simulation,
│   │                             #   events, scoring, poll_quality, polymarket
│   ├── io/                       # loader, report (CSV/PDF), history (SQLite), manifest
│   ├── viz/                      # charts, colors, Streamlit dashboard
│   ├── calibracao.py             # 2026 evaluation + common-error calibration
│   ├── backtesting.py            # historical backtest on the core engine
│   ├── simulation_2turno.py      # standalone calibrated runoff
│   ├── retrospectiva_1t.py       # first-round retrospective
│   ├── publicar_2turno.py        # publication gate and posts
│   ├── historico_v2.py           # auditable historical catalogue validator
│   └── simulation_v2.py, simulation_combined.py, dashboard.py   # legacy
├── data/
│   ├── pesquisas.csv             # first-round polls
│   ├── pesquisas_2turno.csv      # runoff polls (pre- and post-first round)
│   ├── pesquisas_only_2turno.csv # runoff polls after the first round
│   ├── historico/                # legacy 2018/2022 snapshots
│   └── historico_v2/             # audited historical catalogue (quarantined)
├── docs/                         # methodology contracts, audits, calibration report
├── tests/                        # pytest suite (fixtures in tests/fixtures/)
├── .github/workflows/tests.yml   # CI on Windows and Linux
├── outputs/                      # generated (gitignored)
├── pyproject.toml, CHANGELOG.md, PUBLISHING.md, CONTRIBUTING.md, LICENSE
└── README.md
```

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/gabrielrv13/brazil-election-montecarlo.git
cd brazil-election-montecarlo

python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/macOS

pip install -e ".[dev]"      # runtime + test tools (Python 3.11+)
```

### 2. Update poll data

Edit `data/pesquisas.csv` with the latest numbers:

```csv
candidato,intencao_voto_pct,rejeicao_pct,desvio_padrao_pct,indecisos_pct,instituto,data
Lula,40.0,48.2,2.2,5.1,Parana Pesquisas,2026-02-27
Flávio Bolsonaro,35.9,46.4,2.2,5.1,Parana Pesquisas,2026-02-27
Romeu Zema,4.0,36.4,2.2,5.1,Parana Pesquisas,2026-02-27
Outros,7.6,0.0,2.2,5.1,Parana Pesquisas,2026-02-27
Brancos/Nulos,7.2,0.0,2.2,5.1,Parana Pesquisas,2026-02-27
```

- Every row of one poll must list the same candidates; dates must be valid ISO dates and not later than the reference date.
- `desvio_padrao_pct` is the poll's published margin of error (95%).
- `rejeicao_pct` sets the electoral ceiling (0 = not measured).
- `indecisos_pct` is optional; if present, undecided voters are redistributed proportionally.

### 3. Run

```bash
# First-round forecast (reproducible: fixed reference date and seed)
python -m src run --as-of 2026-10-03 --seed 42

# Error-model options (defaults shown)
python -m src run --sd-erro-comum 3.0 --gl-erro-comum 5 --sd-deriva 2.0

# Standalone runoff (after the finalists are confirmed)
python src/simulation_2turno.py --csv data/pesquisas_only_2turno.csv --as-of 2026-10-24
python src/simulation_2turno.py --sd-fatia 3.0 --vies 0.0 --tau 7 --seed 42
python src/simulation_2turno.py --base candidato        # legacy aggregation

# Evaluation and calibration report (outputs/calibracao/)
python -m src.calibracao

# Publication gate and posts (verifies the runoff manifest)
python src/publicar_2turno.py --exigir-manifesto

# Tests (headless)
pytest
```

Results are saved to `outputs/`. Every run writes a manifest (`*_manifest.json` or `<summary>.manifest.json`) with the run id, git commit, library versions, reference date, seed, parameters and the SHA-256 of every input and output. Without `--seed` the CLI draws one and records it, so any run can be repeated from its manifest.

---

## Methodology

### Poll Aggregation

Multiple polls are combined using exponential temporal decay:

```
weight = exp(-days_ago / τ)   where τ = 7 days
```

Each poll is read as `trend(date) + house effect(institute) + noise`. Since v3 (`src/core/aggregation.py: agregar_pesquisas`), used by the CLI, the legacy script and the backtest alike:

- **House effects.** Each institute's residual against a local trend built from the *other* institutes is averaged, shrunk toward zero (`n_eff / (n_eff + 3)`) and centred on the industry average, iterating until stable. The adjustment is subtracted before averaging. The industry-wide error cannot be seen in the polls and is handled by the common error below.
- **Outliers** use the modified z-score (> 3.5) on detrended, house-adjusted residuals, so a candidate whose support moved during the campaign is no longer trimmed.
- **Uncertainty of the average** is the standard error of the weighted mean, `sqrt(Σw²(SE² + τ²)) / Σw`, with `SE = margin of error / 1.96` and `τ²` the dispersion beyond sampling. It is small (about 0.3 pp with 24 effective polls) because it measures only how well the polls are known, not how wrong they may be.

### Rejection Ceiling

Each candidate has a hard electoral ceiling derived from their rejection rate:

```
ceiling = 100% - rejection%
```

A candidate above the ceiling is fixed at it and the excess goes to the uncapped candidates in proportion to their share, repeating until no ceiling is violated (water-filling). The ceilings therefore hold in the final shares. A rejection of zero means "not measured" (ceiling 100). If the ceilings sum to less than 100 the run stops with an error, since no allocation can respect them.

### Undecided Redistribution

Undecided voters are distributed among candidates proportionally to their available electoral space:

```
weight_i = vote_share_i × (100 - rejection_i) / 100
gain_i   = weight_i / Σweights × undecided × (1 - blank_fraction)
```

### Simulation

Each of the 40,000 iterations draws a Dirichlet sample parameterized by the aggregated poll estimates. The aggregated `desvio_base` is a **marginal standard deviation in percentage points**: the total concentration is set so that a candidate at 50% has exactly that sd,

```
alpha0 = (50 / sd)^2 - 1        alpha_i = share_i × alpha0
```

and candidates further from 50% have a smaller sd, `sd × sqrt(4p(1-p))`. Undecided redistribution only rescales the means and does not change the spread.

The draw has two levels (`amostrar_proporcoes`). First, one election-level shift per simulation, `μ ~ Dirichlet(p × A)`, shared by every poll, with

```
sd_shift² = sd_common² × V + sd_drift²
V = (ν − 2) / χ²_ν                 (mean 1: Student-t tails, same sd)
sd_drift = sd_drift_30d × sqrt(days / 30)
```

then the polling-average noise around that shift, `Dirichlet(μ × alpha0)`. The variances add: at 50% the total sd is about `sqrt(sd_mean² + sd_common² + sd_drift²)`.

| Parameter | Default | CLI | Meaning |
|---|---|---|---|
| `sd_erro_comum_pp` | 3.0 | `--sd-erro-comum` | Error shared by all polls (prior) |
| `gl_erro_comum` | 5 | `--gl-erro-comum` | Tail heaviness (`inf` = Normal) |
| `sd_deriva_30d_pp` | 2.0 | `--sd-deriva` | Opinion drift per √30 days |
| `efeitos_instituto` | on | `--sem-efeito-instituto` | House-effect adjustment |

On the 2026-10-03 polls, removing the common error would give Lula a 98.8% chance of leading; almost all the honest uncertainty comes from `sd_erro_comum_pp`.

### Evaluation and calibration (Phase 3)

`python -m src.calibracao` scores the 2026 forecasts against the official TSE results with proper scoring rules (`src/core/scoring.py`: multiclass Brier, log score, sample CRPS, PIT, interval coverage) and estimates the common error from the final-week polling averages of 2018, 2022 and 2026 (both rounds), on the leaders' two-party share. Full report: [docs/calibracao_fase3.md](docs/calibracao_fase3.md).

- Maximum likelihood gives 3.4 pp (95% profile interval 1.5–9.1) with t5 tails. The 3.0 default scores better in leave-one-out validation and is kept; the runoff now uses the same 3.0.
- The right-wing lead was under-polled in all three first rounds (+2.9 pp on average) but over-polled in the 2026 runoff (−2.7 pp); no fixed directional bias is applied.
- Four cases from three elections leave the common error poorly identified. The drift and tail parameters remain priors.

Abstention is sampled per iteration from a Normal distribution calibrated to historical Brazilian elections. Turnout is split into blank/null and valid votes; candidates divide only the valid votes. The blank/null share comes from the poll's `Brancos/Nulos` category when present, otherwise from a Normal(6%, σ=2%) prior (TSE first rounds: 9.6% in 2014, 8.8% in 2018, 4.4% in 2022).

| Round | Abstention |
|---|---|
| First round | Normal(20%, σ=2%) |
| Second round | Normal(22%, σ=3%) |

`--bayesian` is currently rejected: the PyMC module samples a Dirichlet with fixed parameters and no likelihood, so it does not perform inference.

### Second Round (v2.5+)

The finalists in each simulation are the actual top-2 vote-getters from that specific first-round draw — not fixed in advance. This captures the full distribution of possible matchups, including low-probability scenarios.

### Standalone Second Round (v2.7)

After the first round, when the two finalists are known, `simulation_2turno.py` simulates the runoff directly against second-round-specific poll data, without the overhead of the first-round model. v2.7 used a 3-category Dirichlet `[A, B, blank/null]` fed by per-candidate poll averages.

### Calibrated Second Round (v2.10)

Two changes address problems seen when the model met real runoff polls.

**Two-party-share aggregation.** Institutes report different undecided levels, so the sum of both candidates ranges from about 82 to 97 across polls. Averaging each candidate separately mixes those bases and the outlier filter can discard legitimate polls from institutes with many undecided. Each poll is now reduced to:

```
share_A = A / (A + B)
```

and the shares are averaged with the same temporal weights (`exp(-days/7)`).

**Explicit uncertainty.** In the Dirichlet parametrization the `desvio` argument is not a standard deviation in percentage points. With the previous default (about 2.4) the effective sd of the two-party share was 0.8 pp, while the 2018 and 2022 backtests show margin errors of 4.2 to 5.5 pp. The new `--sd-fatia` argument is the sd of the share in pp (default 3.0 since Phase 3, previously 2.5; valid up to 4.9) and is converted internally:

```
desvio = 10000 / ((50 / sd)^2 - 1)
```

**Bias sensitivity.** For a nonzero shift, use `--vies -5 --vies-candidato "Exact candidate name"`. Positive values favor the named candidate regardless of poll ordering. The Python API retains `vies_pp_a` in candidate A's coordinate. Every run prints absolute bias scenarios from the aggregated share. `retrospectiva_1t.py` suggests a shift for Flavio; use the exact name in the runoff CSV when exploring that scenario. JSON version 2 separates aggregated share, input center and actual draw mean; see [the publication contract](docs/contrato_resumo_publicacao.md).

**Rejection ceiling.** Off by default in the calibrated path: in a binary race the vote intention already reflects rejection, and rejections that sum above 100 push both ceilings below 50%, compressing results toward a coin flip.

---

## Outputs

| File | Description |
|---|---|
| `simulacao_eleicoes_brasil_2026.png` | 11-panel visualization (first round) |
| `resultados_1turno.csv` | 40,000 rows — per-simulation first-round results |
| `resultados_2turno.csv` | 40,000 rows — per-simulation second-round results |
| `relatorio_simulacao.pdf` | PDF summary report |
| `simulacao_2turno.png` | 3-panel standalone second-round visualization |
| `resultados_2turno_standalone.csv` | 40,000 rows — standalone second-round results |
| `resumo_2turno.json` | Runoff summary (probabilities, parameters, sensitivity) consumed by `publicar_2turno.py` |
| `calibracao_1t.json` | First-round error by candidate and suggested bias |
| `post_2turno_pt.md`, `post_2turno_en.md` | Ready-to-post texts with disclaimer |

---

## Dependencies

All are declared in `pyproject.toml` (Python ≥ 3.11); `pip install -e ".[dev]"` adds pytest, pytest-cov, pytest-mock and ruff.

| Package | Version | Purpose |
|---|---|---|
| `numpy` | ≥1.26 | Numerical computation |
| `pandas` | ≥2.1 | Data manipulation |
| `scipy` | ≥1.11 | Distributions for calibration and tests |
| `pymc` | ≥5.10 | Legacy MCMC module (the `--bayesian` flag is currently rejected) |
| `arviz` | ≥0.18 | Legacy MCMC diagnostics |
| `matplotlib` | ≥3.8 | Visualization |
| `seaborn` | ≥0.13 | Plot styling |
| `streamlit` | ≥1.32 | Interactive dashboard |
| `reportlab` | ≥4.1 | PDF report generation |

---

## Typical Workflow

```bash
# New poll released
# 1. Add it to pesquisas.csv
# 2. Run (the manifest in outputs/ records seed, inputs and outputs)
python -m src run --as-of <poll date>

# 3. Commit
git add data/pesquisas.csv
git commit -m "chore: update polls - <institute> <date>"
git push
```

---

## Publishing the Runoff Forecast

See [PUBLISHING.md](PUBLISHING.md) for the checklist: final run, publication gate, posting rules and the post-election retrospective.

---

## Disclaimer

This project is strictly educational and methodological. Results do not constitute official electoral forecasting. Real electoral polling must be obtained from TSE-certified institutes.

---

## License

MIT — see [LICENSE](LICENSE) for details.


### Contratos de probabilidade (A02 / P0.3)

Liderança, vitória direta por mais de 50% dos votos válidos e classificação ao
segundo turno são eventos distintos. `pv` preserva a liderança legada; novos
consumidores devem usar `p_lideranca`, `p_vitoria_1t` e `p_classificacao_2t`.
Consulte [os contratos v2 e a migração do histórico](docs/probability_events.md),
incluindo o condicionamento de `p2v`, os empates e as incompatibilidades.
