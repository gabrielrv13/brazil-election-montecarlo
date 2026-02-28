# Changelog v2.4

## [2.4.0] - 2026-02-26

### Added - Undecided Voter Category

#### Core Functionality
- **Undecided voter redistribution**: Reads optional `indecisos_pct` column and redistributes
  undecided voters proportionally before parameterizing the Dirichlet simulation
- **Rejection-adjusted weights**: Candidates with higher rejection absorb proportionally fewer
  undecided voters, reflecting realistic voter behavior
- **Configurable blank fraction**: A fixed fraction (default 15%) of undecided voters is
  allocated to blank/null categories rather than declared candidates

#### New Function
- `distribuir_indecisos(votos_base, indecisos_total, rejeicao_array, blank_fraction=0.15)`
  - Computes per-candidate redistribution weights: `weight_i = vote_share_i * (100 - rejection_i) / 100`
  - Normalizes weights and distributes `indecisos_total * (1 - blank_fraction)` among declared candidates
  - Allocates remaining `indecisos_total * blank_fraction` to blank/null entries
  - Returns adjusted vote intentions and detailed info dictionary

#### Enhanced Functions
- `carregar_pesquisas()`: Reads and aggregates `indecisos_pct` column (optional)
  - Temporal weighting applied when `data` column is present
  - Returns 5-tuple (candidatos, votos_media, rejeicao, desvio_base, indecisos)
  - Prints undecided percentage if column is found
- `construir_modelo()`: Uses redistribution-adjusted means for Bayesian priors
- `simular_primeiro_turno()`: Applies redistribution before Dirichlet parameterization
  - Prints per-candidate gain table
  - Returns 3-tuple (df, info_limitacoes, info_indecisos)
- `relatorio()`: Added `UNDECIDED VOTERS` section with full redistribution breakdown
- `graficos()`: Added undecided redistribution bar chart (panel gs[1,3])

### Changed

#### CSV Format (New Optional Column)
```csv
candidato,intencao_voto_pct,rejeicao_pct,desvio_padrao_pct,indecisos_pct,instituto,data
Lula,38.0,42.0,2.0,12.0,Datafolha,2026-02-18
Lula,36.0,43.0,2.0,13.0,Quaest,2026-02-19
Flávio Bolsonaro,29.0,48.0,2.0,12.0,Datafolha,2026-02-18
```
- `indecisos_pct` is a poll-level statistic; the same value is expected for all candidates
  in the same poll
- Aggregated as temporally-weighted mean across all rows

#### Output Files
- Results saved as `resultados_1turno_v2.4.csv`
- Results saved as `resultados_2turno_v2.4.csv`
- Visualization saved as `simulacao_eleicoes_brasil_2026_v2.4.png`

### Technical Details

#### Distribution Algorithm
```
weight_i = vote_share_i * max(100 - rejection_i, 0) / 100
proporcao_i = weight_i / sum(weights)
gain_i = proporcao_i * indecisos_total * (1 - blank_fraction)
```

Example (12% undecided, 15% blank fraction):
- 10.2% distributed to declared candidates (proportional to weight)
- 1.8% added to blank/null category

#### Why Rejection-Adjusted Weights
- A purely vote-proportional distribution overestimates gain for highly-rejected candidates
- Multiplying by `(100 - rejection) / 100` corrects this: a candidate with 48% rejection
  receives roughly half the boost of an equally-polling candidate with 0% rejection
- Consistent with the v2.2 electoral ceiling logic

### Backward Compatibility

**100% backward compatible with v2.3:**
- Missing `indecisos_pct` column: `INDECISOS = 0.0`, no redistribution applied
- Behavior is identical to v2.3 when `indecisos_pct` is absent
- `relatorio()` and `graficos()` accept `info_indecisos=None` (default)

### Testing

Validated with:
- CSV without `indecisos_pct` (v2.3 compatibility)
- CSV with uniform `indecisos_pct` across all rows
- CSV with varying `indecisos_pct` across polls (temporal weighting)
- Candidates with 0% rejection (maximum absorption)
- Candidates with >50% rejection (near-zero absorption)

### Known Limitations

1. **Poll-level statistic**: `indecisos_pct` is expected to be the same for all candidates
   in the same poll; per-candidate values are averaged, which may not reflect intent
2. **Fixed blank fraction**: The 15% default is heuristic; no empirical calibration
3. **Static redistribution**: All N_SIM simulations use the same adjusted means;
   stochastic redistribution (per-simulation Dirichlet over undecided) is a future enhancement

### Future Enhancements (Planned for v2.5)

- Per-simulation stochastic undecided distribution (Dirichlet over undecided pool)
- Configurable `blank_fraction` via CLI argument or CSV metadata row
- Issue #3: Second round based on actual top-2 from first round
- Sample-size weighting in poll aggregation

---

## Previous Versions

See `CHANGELOG_v2.3.md` for v2.3.0 and earlier.
