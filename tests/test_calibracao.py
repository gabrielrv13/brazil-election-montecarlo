"""Phase 3: proper scoring rules, calibration estimator and 2026 evaluation."""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import stats

from src import calibracao as cal
from src.core import scoring


# ── Scoring rules ─────────────────────────────────────────────────────────────

class TestScoring:

    def test_multiclass_brier_counts_mass_on_wrong_classes(self):
        p = {"A": 0.6, "B": 0.3, "C": 0.1}
        assert scoring.brier_multiclasse(p, "A") == pytest.approx(0.4**2 + 0.3**2 + 0.1**2)
        # Old backtest formula (p_winner - 1)^2 would give 0.16 here.
        assert scoring.brier_multiclasse(p, "A") > (0.6 - 1) ** 2

    def test_multiclass_brier_unlisted_winner(self):
        assert scoring.brier_multiclasse({"A": 1.0}, "Z") == pytest.approx(2.0)

    def test_binary_brier_and_log_score(self):
        assert scoring.brier_binario(0.7, True) == pytest.approx(0.09)
        assert scoring.brier_binario(0.7, False) == pytest.approx(0.49)
        assert scoring.log_score(1.0) == pytest.approx(-math.log(1 - 1e-4))
        assert math.isfinite(scoring.log_score(0.0))

    @pytest.mark.parametrize("y", [-1.0, 0.0, 0.7, 2.5])
    def test_sample_crps_matches_normal_closed_form(self, y):
        x = np.random.default_rng(0).normal(0, 1.5, 400_000)
        z = y / 1.5
        exact = 1.5 * (z * (2 * stats.norm.cdf(z) - 1) + 2 * stats.norm.pdf(z) - 1 / math.sqrt(math.pi))
        assert scoring.crps_amostral(x, y) == pytest.approx(exact, rel=0.01, abs=2e-3)

    def test_crps_of_point_mass_is_absolute_error(self):
        assert scoring.crps_amostral([3.0, 3.0, 3.0], 5.0) == pytest.approx(2.0)

    def test_pit_is_uniform_for_calibrated_draws(self):
        rng = np.random.default_rng(1)
        amostras = rng.normal(0, 1, 5_000)
        pits = [scoring.pit(amostras, y) for y in rng.normal(0, 1, 2_000)]
        assert stats.kstest(pits, "uniform").pvalue > 0.01

    def test_coverage_and_interval_score(self):
        x = np.linspace(0, 100, 10_001)
        assert scoring.cobertura(x, 50.0) == {0.5: True, 0.8: True, 0.9: True}
        assert scoring.cobertura(x, 93.0) == {0.5: False, 0.8: False, 0.9: True}
        assert scoring.interval_score(5, 95, 50, 0.1) == pytest.approx(90)
        assert scoring.interval_score(5, 95, 100, 0.1) == pytest.approx(90 + 20 * 5)
        with pytest.raises(ValueError):
            scoring.interval_score(5, 4, 0, 0.1)
        with pytest.raises(ValueError):
            scoring.interval_score(1, 2, 0, 1.5)
        with pytest.raises(ValueError):
            scoring.crps_amostral([], 1.0)


def test_backtest_uses_multiclass_brier():
    from src import backtesting as bt
    resultado = {"prob_vencedor": {"Lula": 0.6, "Bolsonaro": 0.4},
                 "mediana_votos": {"Lula": 50.0, "Bolsonaro": 45.0},
                 "mediana_margem": 5.0,
                 "prob_par": {frozenset(["Lula", "Bolsonaro"]): 1.0}}
    r = bt.calcular_metricas(resultado, bt.GROUND_TRUTH["2022"], "2022", "T-7")
    assert r.brier == pytest.approx(round(0.4**2 + 0.4**2, 4))


# ── Calibration estimator ─────────────────────────────────────────────────────

def _caso(erro, q=50.0, s=1.0, sd_media=0.0, dias=0):
    return cal.Caso("x", "2T", "A", "B", q, q + erro, s, sd_media, dias, "2026-01-01", 1, "")


class TestEstimator:

    def test_model_sd_at_fifty_percent_two_way(self):
        c = _caso(0.0, sd_media=0.4)
        assert cal.sd_erro_modelo(c, 3.0, 0.0) == pytest.approx(math.hypot(3.0, 0.4), rel=1e-3)

    def test_third_candidates_widen_the_two_party_error(self):
        assert cal.sd_erro_modelo(_caso(0, s=0.75), 3.0, 0.0) > cal.sd_erro_modelo(_caso(0, s=1.0), 3.0, 0.0)

    def test_drift_enters_for_longer_horizons(self):
        assert cal.sd_erro_modelo(_caso(0, dias=30), 3.0, 2.0) == pytest.approx(math.hypot(3, 2), rel=1e-3)

    @pytest.mark.parametrize("gl", [5.0, math.inf])
    def test_mle_recovers_true_sd_with_many_cases(self, gl):
        rng = np.random.default_rng(5)
        sd = 3.0
        if math.isinf(gl):
            erros = rng.normal(0, sd, 400)
        else:
            erros = rng.standard_t(gl, 400) * sd * math.sqrt((gl - 2) / gl)
        est = cal.estimar_sd_comum([_caso(e) for e in erros], gl)
        assert est["sd_mle"] == pytest.approx(sd, rel=0.1)
        assert est["ic95"][0] < sd < est["ic95"][1]
        assert est["ic95"][1] - est["ic95"][0] < 1.5

    def test_few_cases_give_a_wide_interval(self):
        est = cal.estimar_sd_comum([_caso(e) for e in (2.0, 4.4, 2.2, -2.7)])
        assert est["ic95"][1] / est["ic95"][0] > 3

    def test_loo_and_bias_shapes(self):
        casos = [_caso(e) for e in (1.0, -2.0, 3.0)]
        loo = cal.validacao_loo(casos)
        assert len(loo) == 3 and all(0 < row["pit_loo"] < 1 for row in loo)
        vies = cal.vies_direcional(casos)
        assert vies["media_pp"] == pytest.approx(2 / 3)
        assert vies["ic95_pp"][0] < 0 < vies["ic95_pp"][1]
        assert vies["so_primeiros_turnos_pp"] is None  # all synthetic cases are runoffs


# ── Real 2026 evaluation (repository data + official results) ────────────────

class TestEvaluation2026:

    def test_official_results_are_consistent(self):
        um = cal.RESULTADOS_OFICIAIS[("2026", "1T")]
        assert sum(um.values()) == pytest.approx(100.0, abs=0.05)
        dois = cal.RESULTADOS_OFICIAIS[("2026", "2T")]
        assert sum(dois.values()) == pytest.approx(100.0)

    def test_cases_from_repository(self):
        casos = {f"{c.eleicao} {c.turno}": c for c in cal.casos_calibracao()}
        assert set(casos) == {"2018 1T", "2022 1T", "2026 1T", "2026 2T"}
        assert casos["2026 1T"].fatia_real == pytest.approx(100 * 47.03 / (47.03 + 45.16))
        assert casos["2026 2T"].fatia_real == pytest.approx(48.21)
        # Right-wing lead under-polled in every first round, over-polled in the 2026 runoff.
        assert all(casos[k].erro > 0 for k in ("2018 1T", "2022 1T", "2026 1T"))
        assert casos["2026 2T"].erro < 0

    def test_first_round_scoring(self):
        r = cal.pontuar_primeiro_turno_2026(n_sim=4_000, seed=1)
        assert r["lider_real"] == "F. Bolsonaro"
        assert 0 <= r["brier_lideranca"] <= 2
        assert sum(r["p_lideranca"].values()) == pytest.approx(1.0)
        fb = r["candidatos"]["F. Bolsonaro"]
        assert 0.85 < fb["pit"] < 0.99  # outcome in the upper tail of the forecast
        assert fb["crps"] > 0

    def test_runoff_scoring_does_not_touch_outputs(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        r = cal.pontuar_segundo_turno_2026(sd_fatia_pp=2.5, seed=3)
        assert r["cand_a"] == "Flávio Bolsonaro" and r["venceu_a"] is False
        assert 0.55 < r["p_vitoria_a"] < 0.75
        assert r["cobertura"]["0.9"] is True
        assert not any(tmp_path.rglob("*.csv"))
