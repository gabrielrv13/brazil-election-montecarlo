# Changelog v2.8

## [2.8.0] — 2026-03-04

### Added — First-Round Margin Distribution

#### Core Metrics (`simulation_v2.py`)
- **`MARGIN_THRESHOLDS`** constant in CONFIG block: `[5, 10, 15, 20, 25]` pp.
- **`margem_1t`** column in `df1`: unsigned gap between 1st and 2nd place valid
  vote shares per simulation.
- **`lider_1t`** column in `df1`: name of the first-round leader per simulation.
- **`margem_<candidate>`** columns: signed margin for each valid candidate
  (positive = leading, negative = trailing).
- Columns persisted to `resultados_1turno_v2.8.csv`.

#### Report (`relatorio()`)
New **FIRST-ROUND MARGIN ANALYSIS** section:
- Median margin with 90% CI.
- Close race (<3pp) and comfortable (>10pp) probabilities.
- P(margin > X) for each threshold in `MARGIN_THRESHOLDS`, with Polymarket annotation at 15pp.
- Leader distribution across simulations.

#### New function `polymarket_edge()`
```python
polymarket_edge(df1, threshold, market_prob, candidate=None) -> dict
```
Returns `model_prob`, `market_prob`, `edge`, `kelly_fraction`, `threshold_pp`,
`candidate`, `n_sim`. Kelly sizing uses **half-Kelly**; full Kelly is not
appropriate with a two-election backtesting sample.

#### CLI flag `--n-sim`
```bash
python simulation_v2.py --n-sim 200000
```
Overrides `N_SIM` at runtime. Recommended for threshold markets where
`model_prob < 0.05` to reduce sampling noise.

#### Dashboard (`dashboard.py`)
- **Margin metrics** row (median, close race %, comfortable %) in tab "1º Turno".
- **Threshold probability table** with Polymarket annotation column.
- **Margin histogram** with reference lines at 3, 10, 15 pp.
- **Polymarket Edge Calculator** expander: interactive threshold/probability/candidate
  inputs with edge and half-Kelly output.

### Changed
- `simular_primeiro_turno()` output CSV renamed to `resultados_1turno_v2.8.csv`.
- Version banner updated to `[v2.8]` in `__main__` and dashboard sidebar.

### Notes
- `polymarket_edge()` output is only operationally reliable after v2.9
  backtesting confirms model calibration. Any calculated edge before that
  is a model estimate, not a validated signal.
- The `margem_1t` column measures the first-round gap; it is a proxy for
  the eventual runoff margin. Structural correlation is high but not 1:1.
```