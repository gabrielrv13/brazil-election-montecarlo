"""Phase 2 contracts: error structure, house effects and a single aggregator."""

from __future__ import annotations

from datetime import date, timedelta
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.core.aggregation import (
    Z_MARGEM_ERRO,
    agregar_pesquisas,
    estimar_efeitos_instituto,
    sd_referencia_50,
)
from src.core.config import SimulationConfig
from src.core.simulation import amostrar_proporcoes, sd_deriva

REF = date(2026, 10, 3)
ROOT = Path(__file__).resolve().parents[1]


def _polls(rows):
    """rows: (instituto, days_ago, {cand: value}, moe)."""
    out = []
    for inst, ago, vals, moe in rows:
        for cand, v in vals.items():
            out.append(dict(candidato=cand, intencao_voto_pct=v, desvio_padrao_pct=moe,
                            instituto=inst, data=(REF - timedelta(days=ago)).isoformat()))
    return pd.DataFrame(out)


# ── Two-level sampler ─────────────────────────────────────────────────────────

class TestSampler:

    @pytest.mark.parametrize("sdm,sdc,sdd", [(1.0, 3.0, 0.0), (0.5, 2.0, 2.0), (2.0, 0.0, 1.5)])
    def test_variances_add(self, sdm, sdc, sdd):
        rng = np.random.default_rng(1)
        pr, _ = amostrar_proporcoes(np.array([50.0, 50.0]), sdm, 300_000, rng,
                                    sd_comum_pp=sdc, gl_comum=math.inf, sd_deriva_pp=sdd)
        assert (pr[:, 0] * 100).std() == pytest.approx(math.sqrt(sdm**2 + sdc**2 + sdd**2), rel=0.01)

    def test_student_t_mixture_gives_heavy_tails_with_same_sd(self):
        def stats(gl):
            pr, _ = amostrar_proporcoes(np.array([50.0, 50.0]), 0.5, 400_000,
                                        np.random.default_rng(2), sd_comum_pp=3.0, gl_comum=gl)
            x = pr[:, 0] * 100 - 50
            return x.std(), (x**4).mean() / x.var() ** 2
        sd_normal, kurt_normal = stats(math.inf)
        sd_t, kurt_t = stats(5.0)
        assert sd_t == pytest.approx(sd_normal, rel=0.02)
        assert kurt_normal == pytest.approx(3.0, abs=0.1)
        assert kurt_t > 5.0

    def test_common_error_is_shared_by_candidates_and_zero_sum(self):
        pr, _ = amostrar_proporcoes(np.array([45.0, 35.0, 20.0]), 0.3, 50_000,
                                    np.random.default_rng(3), sd_comum_pp=3.0)
        np.testing.assert_allclose(pr.sum(axis=1), 1.0)
        corr = np.corrcoef(pr[:, 0], pr[:, 1])[0, 1]
        assert corr < -0.5  # one candidate's gain is another's loss

    def test_reproducible_with_same_generator_seed(self):
        a, _ = amostrar_proporcoes(np.array([40.0, 60.0]), 1.0, 1000, np.random.default_rng(9), 3.0, 5.0, 1.0)
        b, _ = amostrar_proporcoes(np.array([40.0, 60.0]), 1.0, 1000, np.random.default_rng(9), 3.0, 5.0, 1.0)
        np.testing.assert_array_equal(a, b)

    def test_drift_horizon(self):
        assert sd_deriva(2.0, date(2026, 10, 4), date(2026, 10, 4)) == 0.0
        assert sd_deriva(2.0, date(2026, 10, 4), date(2026, 10, 10)) == 0.0
        assert sd_deriva(2.0, date(2026, 10, 4), date(2026, 6, 6)) == pytest.approx(4.0)

    @pytest.mark.parametrize("field,value", [
        ("sd_erro_comum_pp", -1.0), ("sd_erro_comum_pp", 45.0), ("sd_erro_comum_pp", float("nan")),
        ("gl_erro_comum", 2.0), ("gl_erro_comum", float("nan")),
        ("sd_deriva_30d_pp", float("inf")), ("tau_dias", 0.0),
    ])
    def test_config_rejects_invalid_error_parameters(self, field, value):
        with pytest.raises(ValueError, match=field):
            SimulationConfig(**{field: value})

    def test_config_accepts_infinite_degrees_of_freedom(self):
        assert SimulationConfig(gl_erro_comum=math.inf).gl_erro_comum == math.inf


# ── v3 aggregator ─────────────────────────────────────────────────────────────

class TestHouseEffects:

    def _biased_panel(self, bias=3.0):
        # Truth: A=40, B=35 every day, plus sampling noise (sd 0.8). "Alta"
        # overstates A by `bias` and polls most recently, which drags a plain
        # recency average.
        rng = np.random.default_rng(11)
        rows = []
        for d in range(0, 30, 3):
            for inst, ago, shift in (("Neutro1", d + 3, 0.0), ("Neutro2", d + 5, 0.0), ("Alta", d, bias)):
                e = rng.normal(0, 0.8, 2)
                rows.append((inst, ago, {"A": 40.0 + shift + e[0], "B": 35.0 + e[1]}, 2.0))
        return _polls(rows)

    def test_effect_is_recovered_with_shrinkage_and_centred(self):
        ef = estimar_efeitos_instituto(self._biased_panel(), REF)
        # Relative to the industry average (+1) Alta is +2; shrinkage with
        # ~10 polls and pseudo-count 3 pulls it toward zero (about x0.77).
        assert 1.1 < ef[("Alta", "A")] < 2.0
        assert ef[("Neutro1", "A")] < 0 and ef[("Neutro2", "A")] < 0
        assert abs(ef[("Alta", "B")]) < 0.6

    def test_adjustment_removes_recency_drag(self):
        df = self._biased_panel()
        raw = agregar_pesquisas(df, REF, efeitos_instituto=False)["A"].voto
        adj = agregar_pesquisas(df, REF, efeitos_instituto=True)["A"].voto
        # Oracle: same noise, no house bias, shifted to the industry average
        # (one of three houses is +3, so +1).
        clean = self._biased_panel(bias=0.0)
        clean.loc[clean.candidato == "A", "intencao_voto_pct"] += 1.0
        oracle = agregar_pesquisas(clean, REF, efeitos_instituto=False)["A"].voto
        assert raw - oracle > 0.4                       # recent Alta polls drag
        assert abs(adj - oracle) < 0.5 * (raw - oracle)  # adjustment removes most of it

    def test_single_institute_has_no_identifiable_effect(self):
        df = _polls([("Solo", d, {"A": 40.0, "B": 35.0}, 2.0) for d in range(5)])
        assert estimar_efeitos_instituto(df, REF) == {}


class TestOutliersAndUncertainty:

    def test_trending_candidate_is_not_trimmed(self):
        # Support falls from 10 to 1 over the campaign: v2 trimmed the
        # early polls as outliers; detrended residuals keep them.
        rows = [(f"I{d % 3}", d, {"A": 1.0 + 0.3 * d, "B": 40.0}, 1.0) for d in range(30)]
        res = agregar_pesquisas(_polls(rows), REF)
        assert res["A"].info["outliers"] == []

    def test_isolated_spike_is_flagged(self):
        rows = [(f"I{d % 3}", d, {"A": 20.0 + (0.2 if d % 2 else -0.2), "B": 40.0}, 2.0)
                for d in range(20)]
        rows.append(("Spike", 5, {"A": 35.0, "B": 40.0}, 2.0))
        res = agregar_pesquisas(_polls(rows), REF, efeitos_instituto=False)
        assert [o["valor"] for o in res["A"].info["outliers"]] == [35.0]

    def test_single_poll_sd_is_its_standard_error(self):
        res = agregar_pesquisas(_polls([("X", 0, {"A": 40.0, "B": 35.0}, 2.0)]), REF)
        assert res["A"].sd_media == pytest.approx(2.0 / Z_MARGEM_ERRO)

    def test_sd_of_mean_shrinks_with_effective_sample(self):
        rows = [(f"I{i}", 0, {"A": 40.0, "B": 35.0}, 2.0) for i in range(4)]
        res = agregar_pesquisas(_polls(rows), REF, efeitos_instituto=False)
        assert res["A"].sd_media == pytest.approx(2.0 / Z_MARGEM_ERRO / 2.0)
        assert res["A"].info["n_efetivo"] == pytest.approx(4.0)

    def test_disagreement_beyond_sampling_inflates_sd(self):
        rows = [(f"I{i}", 0, {"A": v, "B": 35.0}, 1.0) for i, v in enumerate([36.0, 44.0, 38.0, 42.0])]
        res = agregar_pesquisas(_polls(rows), REF, efeitos_instituto=False)
        assert res["A"].info["sd_extra"] > 2.0
        assert res["A"].sd_media > 1.0 / Z_MARGEM_ERRO / 2.0

    def test_future_poll_is_rejected(self):
        df = _polls([("X", -1, {"A": 40.0, "B": 35.0}, 2.0)])
        with pytest.raises(ValueError, match="future"):
            agregar_pesquisas(df, REF)

    def test_reference_sd_uses_contenders(self):
        res = agregar_pesquisas(_polls([("X", 0, {"A": 50.0, "B": 45.0, "C": 5.0}, 2.0)]), REF)
        assert sd_referencia_50(res) == pytest.approx(2.0 / Z_MARGEM_ERRO, rel=0.01)


# ── One implementation for live runs, backtest and legacy ─────────────────────

class TestSingleImplementation:

    def test_legacy_scripts_are_retired_and_runoff_uses_the_core(self):
        for nome in ("simulation_v2.py", "simulation_combined.py", "dashboard.py"):
            assert not (ROOT / "src" / nome).exists()
        src = (ROOT / "src/simulation_2turno.py").read_text(encoding="utf-8")
        assert "from simulation_v2" not in src and "import simulation_v2" not in src
        assert "from src.core.aggregation import" in src

    def test_backtest_has_no_private_engine(self):
        src = (ROOT / "src/backtesting.py").read_text(encoding="utf-8")
        assert "def _agregar_candidato(" not in src
        assert "np.random.dirichlet" not in src
        assert "amostrar_proporcoes" in src and "agregar_pesquisas" in src

    def test_backtest_runner_respects_ceiling_and_seed(self):
        from src import backtesting as bt
        args = (["A", "B", "C"], np.array([55.0, 30.0, 15.0]), np.array([50.0, 0.0, 0.0]), 1.0, 0.0, 5_000)
        r1 = bt.executar_simulacao_historica(*args, dias_ate_eleicao=7, seed=4)
        r2 = bt.executar_simulacao_historica(*args, dias_ate_eleicao=7, seed=4)
        assert r1 == r2
        assert r1["mediana_votos"]["A"] <= 50.0 + 1e-9

    def test_loader_uses_v3_aggregator(self, tmp_path):
        from src.io.loader import load_polls
        csv = tmp_path / "p.csv"
        self_df = TestHouseEffects()._biased_panel()
        self_df.to_csv(csv, index=False)
        poll = load_polls(SimulationConfig(csv_path=csv, as_of=REF))
        expected = agregar_pesquisas(self_df, REF)
        assert poll.votos_media[0] == pytest.approx(expected["A"].voto)
        assert poll.desvio_base == pytest.approx(sd_referencia_50(expected))


def test_cli_flags_reach_config():
    from src import cli
    args = cli._build_parser().parse_args(
        ["run", "--sd-erro-comum", "2.5", "--gl-erro-comum", "inf",
         "--sd-deriva", "1.0", "--sem-efeito-instituto"])
    cfg = cli._build_simulation_config(args)
    assert (cfg.sd_erro_comum_pp, cfg.gl_erro_comum, cfg.sd_deriva_30d_pp,
            cfg.efeitos_instituto) == (2.5, math.inf, 1.0, False)
    default = cli._build_simulation_config(cli._build_parser().parse_args(["run"]))
    assert default.sd_erro_comum_pp == SimulationConfig().sd_erro_comum_pp
    assert default.efeitos_instituto is True
