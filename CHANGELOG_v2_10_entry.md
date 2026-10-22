## [2.10.0] - Unreleased

### Added
- `simulation_2turno.py`: two-party-share aggregation for runoff polls
  (`agregar_fatia_dois_candidatos`, `carregar_pesquisas_2t_fatia`). Each poll is
  reduced to A/(A+B) before weighting, which removes differences in undecided
  level across institutes.
- `sd_fatia_para_desvio`, `simular_calibrado`: explicit sd of the two-party share
  (default 2.5 pp, calibrated against the 2018/2022 backtest margin error of
  4.2-5.5 pp) and optional poll-bias shift toward the first candidate.
- `tabela_sensibilidade`, `imprimir_sensibilidade`: P(win) grid by bias (-1 to +3 pp)
  and sd; `salvar_resumo`: JSON summary of the run.
- CLI flags: `--base {fatia,candidato}`, `--sd-fatia`, `--vies`, `--data-min`,
  `--tau`, `--csv`.
- `src/retrospectiva_1t.py`: first-round poll average vs official result, suggested
  bias for the runoff (`outputs/calibracao_1t.json`).
- `src/publicar_2turno.py`: publication gate and Portuguese/English post generator.
- Tests: `test_runoff_calibration.py`, `test_retrospectiva_1t.py`,
  `test_publicar_2turno.py` (synthetic data only).

### Changed
- Default runoff aggregation is now `--base fatia`. The legacy path is kept as
  `--base candidato` and its functions are unchanged.
- Rejection ceiling is off by default in the calibrated path (binary race).
- README: v2.8 to v2.10 features, runoff calibration methodology, publication.

Commit: feat(runoff): aggregate runoff polls on two-party share with explicit sd
