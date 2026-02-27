# Changelog

## [2.2.0] - 2026-02-18

### Added
- Rejection index as electoral ceiling
  - Candidates cannot exceed (100 - rejection)% of valid votes
  - Historical validation: no candidate with >50% rejection has won since redemocratization
- Rejection-based proportional vote transfer in second round
  - Votes from eliminated candidates migrate proportionally to available space
  - Candidates with lower rejection receive more transferred votes
- Automatic viability validation
  - Pre-simulation analysis of candidate viability
  - Warnings for candidates above 50% rejection (unviable)
  - Warnings for candidates between 45-50% rejection (high difficulty)
- Enhanced visualizations
  - New rejection index bar chart with color coding (green/orange/red)
  - Rejection ceiling lines on valid votes graphs
  - Ceiling limitation statistics in console output
- Comprehensive limitation tracking
  - First round: tracks simulations limited by ceiling
  - Second round: tracks simulations limited by ceiling
  - Detailed statistics per candidate

### Changed
- `carregar_pesquisas()` now returns rejection data as fourth element
- `simular_primeiro_turno()` now applies rejection ceiling and returns limitation info
- `simular_segundo_turno()` now uses rejection-based transfer instead of fixed [40,35,25]
- `relatorio()` now includes rejection analysis section
- `graficos()` now includes rejection visualization and ceiling markers
- Console output now uses professional English formatting

### Technical
- Added `validar_viabilidade()` function for pre-simulation validation
- Added `aplicar_teto_rejeicao()` function for ceiling application
- Improved variable name sanitization (handles hyphens)
- Updated output filename to v2.2

### Backward Compatibility
- Fully backward compatible with v2.1.1
- CSV without 'rejeicao_pct' column works normally (rejection = 0 for all)
- All existing code continues to function without modification

## [2.1.1] - 2026-02-17

### Fixed
- Critical bug: alphabetic sorting causing incorrect vote calculations
- Fixed color index errors for multiple candidates
- Restored all 11 visualizations

### Added
- Dynamic color generation for any number of candidates

## [2.1.0] - 2026-02-15

### Added
- Dirichlet distribution (guarantees sum = 100%)
- Temporal uncertainty (funnel effect)
- CSV data loading
- Complete documentation

## [1.0.0] - 2026-02-10

### Initial Release
- Basic Monte Carlo simulation
- Bayesian model with PyMC
- First and second round simulations
- Basic visualizations
