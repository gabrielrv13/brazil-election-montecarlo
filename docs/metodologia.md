# Methodology

How the v3 engine turns polls into probabilities. The README has the short version. Calibration results are in [calibracao_fase3.md](calibracao_fase3.md), and the probability fields are defined in [probability_events.md](probability_events.md).

## 1. Poll aggregation

`src/core/aggregation.py: agregar_pesquisas` is used by the first round, the runoff, the backtest and the calibration alike. Each poll is read as `trend(date) + house effect(institute) + noise`.

- **Recency weight.** `weight = exp(-days_ago / τ)` with `τ = 7` days (`--tau` in the runoff).
- **House effects.** Each institute's residual is measured against a local trend built from the *other* institutes. The residuals are averaged, shrunk toward zero (`n_eff / (n_eff + 3)`) and centred on the industry average, iterating until stable. The adjustment is subtracted before averaging. The industry-wide error cannot be seen in the polls; the common error in section 4 handles it.
- **Outliers.** A modified z-score above 3.5 on detrended, house-adjusted residuals, applied only with at least five polls. A candidate whose support moved during the campaign is therefore not trimmed.
- **Uncertainty of the average.** The standard error of the weighted mean, `sqrt(Σw²(SE² + τ²)) / Σw`, with `SE = margin of error / 1.96` and `τ²` the dispersion beyond sampling. It is small (about 0.3 pp with 24 effective polls on the 2026 first-round data) because it measures how well the polls are known, not how wrong they may be.

## 2. Rejection ceiling

```
ceiling = 100% − rejection%
```

A candidate above the ceiling is fixed at it. The excess goes to the uncapped candidates in proportion to their share, repeating until no ceiling is violated (water-filling), so the ceilings hold in the final shares. A rejection of zero means "not measured" (ceiling 100). If the ceilings sum to less than 100, the run stops with an error, since no allocation can respect them.

In the runoff the ceiling is off by default (`--usar-teto` turns it on). In a two-way race the vote intention already reflects rejection, and rejections that sum above 100 would push both ceilings below 50%, compressing the result toward a coin flip.

## 3. Undecided redistribution

Undecided voters (`indecisos_pct`) are distributed in proportion to each candidate's available electoral space:

```
weight_i = vote_share_i × (100 − rejection_i) / 100
gain_i   = weight_i / Σweights × undecided × (1 − blank_fraction)
```

This rescales the means only; it does not change the spread.

## 4. Simulation

Each iteration (40,000 by default) draws a Dirichlet sample around the aggregated shares. The sd is a **marginal standard deviation in percentage points** for a candidate at 50%:

```
alpha0 = (50 / sd)^2 − 1        alpha_i = share_i × alpha0
```

A candidate further from 50% has a smaller sd, `sd × sqrt(4p(1−p))`.

The draw has two levels (`amostrar_proporcoes`). First, one election-level shift per simulation, `μ ~ Dirichlet(p × A)`, shared by every poll:

```
sd_shift² = sd_common² × V + sd_drift²
V         = (ν − 2) / χ²_ν                (mean 1: Student-t tails, same sd)
sd_drift  = sd_drift_30d × sqrt(days / 30)
```

Then the polling-average noise around that shift, `Dirichlet(μ × alpha0)`. The variances add: at 50% the total sd is about `sqrt(sd_mean² + sd_common² + sd_drift²)`.

| Parameter | Default | CLI | Meaning |
|---|---|---|---|
| `sd_erro_comum_pp` | 3.0 | `--sd-erro-comum` | Error shared by all polls of one election |
| `gl_erro_comum` | 5 | `--gl-erro-comum` | Tail heaviness (`inf` = Normal) |
| `sd_deriva_30d_pp` | 2.0 | `--sd-deriva` | Opinion drift per √30 days until election day |
| `efeitos_instituto` | on | `--sem-efeito-instituto` | House-effect adjustment |

Almost all the honest uncertainty comes from the common error. On the 2026-10-03 polls, setting it to zero gives Lula a 98.8% chance of leading; with the 3.0 default it is 66.6%.

`--bayesian` is rejected: the old PyMC module sampled a Dirichlet with fixed parameters and no likelihood, so it did not perform inference.

## 5. Vote accounting

Both rounds share `contabilizar_votos` and `dividir_validos` (`src/core/simulation.py`).

```
electorate (158.6 M) → turnout → blank/null + valid → candidates
```

| Quantity | First round | Runoff |
|---|---|---|
| Abstention | Normal(20%, σ 2%) | Normal(22%, σ 3%) |
| Blank/null share of turnout | the poll's `Brancos/Nulos` when present, else Normal(6%, σ 2%) | Normal(6%, σ 2.5%) |

The blank/null priors come from TSE results: 9.6% (2014), 8.8% (2018) and 4.4% (2022) in first rounds; 6.3%, 9.6%, 4.6% and about 3.2% (2026) in runoffs. Valid votes are split by largest remainder, so candidate votes add up exactly to the valid total.

## 6. Second round

**Dynamic runoff** (inside `python -m src run`). In every first-round draw, the actual top two face each other, so low-probability matchups are covered too. The other candidates' votes are transferred with a Dirichlet (concentration 100) weighted by each finalist's electoral space (100 − rejection), and 20% of them go to blank/null. `p2v` is the probability of winning conditional on a runoff.

**Standalone runoff** (`python -m src runoff`), once the finalists are known.

- Only polls after the first round are used by default; `--data-min` includes the earlier matchups, which ask a hypothetical question. Duplicated or incomplete polls are rejected.
- Each poll is reduced to the two-party share, `A / (A + B)`. Institutes report very different undecided levels (A + B ranges from about 82 to 97), so averaging each candidate separately would mix bases.
- The shares go through the aggregator of section 1, with house effects.
- The draw uses the first-round error model (common error, t tails, drift to runoff day, average noise) and the runoff vote accounting.
- `--vies PP --vies-candidato "Exact name"` shifts the share toward the named candidate. Use it as a scenario, never as the headline. Every run also computes a sensitivity table of fixed shifts and stores it in the summary.

The output contract of `resumo_2turno.json` (schema 2) is in [contrato_resumo_publicacao.md](contrato_resumo_publicacao.md).

### Legacy v2.10 runoff script

`src/simulation_2turno.py` is kept to reproduce and score the runoff forecast published in October 2026. It aggregates the two-party share without house effects and takes `--sd-fatia` (sd of the share in pp, default 3.0, published with 2.5; valid up to 4.9). Before v3, the Dirichlet `desvio` argument was an inverse concentration, not an sd. With the old default of about 2.4, the runoff share had an sd of only 0.8 pp, while the 2018/2022 backtests showed margin errors of 4.2 to 5.5 pp. `--base candidato` keeps the per-candidate v2.7 method. New forecasts should use `python -m src runoff`.

## 7. Evaluation and calibration

`python -m src.calibracao` scores the 2026 forecasts with proper scoring rules (`src/core/scoring.py`: multiclass Brier, log score, sample CRPS, PIT, interval coverage). It also estimates the common error from the final two weeks of polls of ten cases: both rounds of 2010-2026, with 2010-2022 transcribed from Wikipedia (see [data/wikipedia](../data/wikipedia/README.md)). Results and decisions are in [calibracao_fase3.md](calibracao_fase3.md).
