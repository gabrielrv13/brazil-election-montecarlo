# Changelog v2.3

## [2.3.0] - 2026-02-23

### Added - Poll Aggregation System

#### Core Functionality
- **Automatic poll aggregation**: Reads and combines multiple polls per candidate
- **Temporal weighting**: Recent polls receive higher weight using `exp(-days/7)`
- **Outlier detection**: Modified z-score method automatically excludes anomalous polls
- **Combined standard deviation**: `√(σ_within² + σ_between²)` accounts for both sampling error and methodological differences

#### New Functions
- `calcular_peso_temporal(data_pesquisa, data_referencia, tau=7)`: Exponential decay weighting
- `detectar_outliers(valores, threshold=2.5)`: Robust outlier detection using MAD
- `agregar_pesquisas_candidato(df_candidato, data_referencia)`: Main aggregation logic

#### Enhanced Functions
- `carregar_pesquisas()`: Now supports both single and multiple polls per candidate
  - Detects multiple polls automatically
  - Aggregates when multiple polls found
  - Maintains backward compatibility with single-poll format
  - Provides detailed aggregation summary

#### Console Output Enhancements
- Poll aggregation summary showing:
  - Number of polls per candidate
  - Number of valid polls (after outlier exclusion)
  - Source institutes
  - Aggregated values
  - Within-poll and between-institute standard deviations
  - Outlier warnings with specific values and sources

### Changed

#### CSV Format (Optional Enhancements)
- Added optional `instituto` column for source tracking
- Added optional `data` column for temporal weighting
- Format remains backward compatible

#### Standard Deviation Calculation
- Now uses combined σ when multiple polls present
- Accounts for inter-institute variance
- More realistic uncertainty estimates

#### Output Files
- Results now saved as `resultados_1turno_v2.3.csv`
- Results now saved as `resultados_2turno_v2.3.csv`
- Visualization saved as `simulacao_eleicoes_brasil_2026_v2.3.png`

### Technical Details

#### Temporal Weighting Algorithm
```python
peso(t) = exp(-t / τ)
where:
  t = days since poll
  τ = 7 days (time constant)
  
Weights are then normalized to sum to 1.0
```

#### Outlier Detection Algorithm
```python
MAD = median(|Xi - median(X)|)
z_modified = 0.6745 * (Xi - median(X)) / MAD
is_outlier = |z_modified| > 2.5
```

#### Combined Standard Deviation
```python
σ_within = weighted_average(poll_std_devs)
σ_between = sqrt(weighted_variance(poll_values))
σ_combined = sqrt(σ_within² + σ_between²)
```

### Backward Compatibility

**100% backward compatible with v2.2:**
- Single poll per candidate: Works exactly as v2.2
- Missing `data` column: All polls get equal weight
- Missing `instituto` column: Aggregation still works, less detailed output
- All v2.2 features maintained:
  - Rejection index as electoral ceiling
  - Rejection-based vote transfer
  - Validation warnings
  - All 11 visualizations

### Performance

- No performance impact for single-poll mode
- Minimal overhead for multiple polls (<1% additional time)
- Scales linearly with number of polls

### Testing

Validated with:
- Single poll format (v2.2 compatibility)
- 2-10 polls per candidate
- Outlier scenarios
- Missing optional columns
- Old poll dates (30+ days)

### Documentation

New documentation files:
- `POLL_AGGREGATION_GUIDE.md`: Comprehensive usage guide
- `pesquisas_multiplas.csv`: Example file with 4 polls per candidate

### Known Limitations

1. **Minimum polls for outlier detection**: Requires 3+ polls for robust detection
2. **Temporal decay assumption**: Assumes exponential decay may not fit all scenarios
3. **Between-institute variance**: Assumes institutes are independent (may overestimate if correlated)

### Future Enhancements (Planned for v2.4)

- Sample size weighting (larger samples get more weight)
- Configurable time constant τ
- Multiple time constants for different candidate types
- Bayesian aggregation with prior beliefs
- Trend detection and extrapolation

---

## [2.2.0] - 2026-02-18

### Added
- Rejection index as electoral ceiling
- Rejection-based vote transfer in second round
- Validation warnings for unviable candidates
- Enhanced visualizations with rejection analysis

### Changed
- Second round transfer logic now based on available space
- Console output in professional English

---

## [2.1.1] - 2026-02-17

### Fixed
- Critical bug: alphabetic sorting breaking vote calculations
- Color index errors for multiple candidates
- Missing visualizations restored

### Added
- Dynamic color generation for any number of candidates

---

## [2.1.0] - 2026-02-15

### Added
- Dirichlet distribution (guarantees sum = 100%)
- Temporal uncertainty (funnel effect)
- CSV data loading
- Complete Bayesian model with PyMC
- 11 comprehensive visualizations

---

## [1.0.0] - 2026-02-10

### Initial Release
- Basic Monte Carlo simulation
- 40,000 iterations
- First and second round simulations
- Basic visualizations

---

**Note:** All versions maintain backward compatibility with previous CSV formats.
