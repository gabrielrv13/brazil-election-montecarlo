"""Phase 1 contracts for the first-round engine (audit items A07, A08, A09, A11).

Analytic oracle: a Dirichlet marginal is Beta(alpha_i, alpha0 - alpha_i), so
the sd and tail probabilities of a two-candidate race without ceilings can be
checked against scipy instead of a second Monte Carlo.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

from src.core.config import PollData, SimulationConfig
from src.core.simulation import (
    aplicar_teto_rejeicao,
    concentracao_dirichlet,
    simular_primeiro_turno,
)

ELECTION = date(2026, 10, 4)
N = 200_000


def _config(as_of: date = ELECTION, n_sim: int = N, seed: int = 7, **kw) -> SimulationConfig:
    # Phase 1 contracts concern the polling-average layer only, so the
    # Phase 2 common error and drift are switched off unless a test asks.
    kw.setdefault("sd_erro_comum_pp", 0.0)
    kw.setdefault("sd_deriva_30d_pp", 0.0)
    return SimulationConfig(
        csv_path=Path("unused.csv"), n_sim=n_sim, seed=seed,
        election_date=ELECTION, as_of=as_of, **kw,
    )


def _polls(cands, votes, rej=None, sd=2.0, undecided=0.0) -> PollData:
    return PollData(
        candidatos=list(cands), votos_media=np.array(votes, float),
        rejeicao=np.zeros(len(cands)) if rej is None else np.array(rej, float),
        desvio_base=sd, indecisos=undecided,
    )


# ── A09: desvio_base is a marginal sd in percentage points ───────────────────

class TestUncertaintyInPercentagePoints:

    @pytest.mark.parametrize("sd", [1.0, 2.5, 5.0])
    def test_sd_at_fifty_percent_matches_input(self, sd):
        df = simular_primeiro_turno(_config(), _polls("AB", [50, 50], sd=sd)).df
        # sd of a sample sd for n=200k is ~0.16% relative.
        assert df["A_val"].std() == pytest.approx(sd, rel=0.01)

    @pytest.mark.parametrize("share", [40.0, 51.5, 60.0])
    def test_marginal_matches_beta_oracle(self, share):
        sd = 2.5
        df = simular_primeiro_turno(
            _config(), _polls("AB", [share, 100 - share], sd=sd)
        ).df
        a0 = concentracao_dirichlet(sd)
        beta = stats.beta(share / 100 * a0, (100 - share) / 100 * a0)
        assert df["A_val"].mean() == pytest.approx(share, abs=0.03)
        assert df["A_val"].std() == pytest.approx(100 * beta.std(), rel=0.01)
        p_win = beta.sf(0.5)
        mc_se = np.sqrt(p_win * (1 - p_win) / N)
        assert (df["A_val"] > 50).mean() == pytest.approx(p_win, abs=4 * mc_se + 1e-6)

    def test_drift_grows_with_square_root_of_horizon(self):
        # Phase 2: the horizon adds drift on top of the polling-average sd.
        polls = _polls("AB", [50, 50], sd=2.0)
        near = simular_primeiro_turno(
            _config(as_of=ELECTION, sd_deriva_30d_pp=2.0), polls
        ).df["A_val"].std()
        far = simular_primeiro_turno(
            _config(as_of=date(2026, 6, 6), sd_deriva_30d_pp=2.0), polls  # 120 days
        ).df["A_val"].std()
        assert near == pytest.approx(2.0, rel=0.02)
        assert far == pytest.approx(np.sqrt(2.0**2 + (2.0 * 2) ** 2), rel=0.02)

    def test_undecided_redistribution_does_not_shrink_uncertainty(self):
        base = simular_primeiro_turno(_config(), _polls("AB", [40, 40], sd=2.0)).df
        und = simular_primeiro_turno(
            _config(), _polls("AB", [40, 40], sd=2.0, undecided=20.0)
        ).df
        assert und["A_val"].std() == pytest.approx(base["A_val"].std(), rel=0.02)

    @pytest.mark.parametrize("sd", [0.0, -1.0, 50.0, float("nan"), float("inf")])
    def test_invalid_sd_is_rejected(self, sd):
        with pytest.raises(ValueError, match="sd must be finite"):
            concentracao_dirichlet(sd)


# ── A07: the rejection ceiling holds in the final shares ─────────────────────

class TestRejectionCeiling:

    def test_audit_example_80_20_with_ceiling_60(self):
        out, info = aplicar_teto_rejeicao(np.array([[80.0, 20.0]]), np.array([40.0, 0.0]), ["A", "B"])
        np.testing.assert_allclose(out, [[60.0, 40.0]])
        assert info["A"]["n_simulacoes_limitadas"] == 1

    def test_excess_cascades_to_a_second_capped_candidate(self):
        out, _ = aplicar_teto_rejeicao(
            np.array([[70.0, 20.0, 10.0]]), np.array([40.0, 85.0, 0.0]), ["A", "B", "C"]
        )
        np.testing.assert_allclose(out, [[60.0, 15.0, 25.0]])

    def test_infeasible_ceilings_raise(self):
        with pytest.raises(ValueError, match="Infeasible rejection ceilings"):
            aplicar_teto_rejeicao(np.array([[50.0, 50.0]]), np.array([60.0, 60.0]), ["A", "B"])

    @pytest.mark.parametrize("rej", [-1.0, 101.0, float("nan")])
    def test_out_of_range_rejection_raises(self, rej):
        with pytest.raises(ValueError, match="Rejection rates"):
            aplicar_teto_rejeicao(np.array([[50.0, 50.0]]), np.array([rej, 0.0]), ["A", "B"])

    def test_engine_output_respects_every_ceiling(self):
        polls = _polls("ABC", [55, 30, 15], rej=[50, 40, 0], sd=4.0)
        res = simular_primeiro_turno(_config(n_sim=20_000), polls)
        tetos = np.array([50.0, 60.0, 100.0])
        assert (res.validos_final <= tetos + 1e-9).all()
        np.testing.assert_allclose(res.validos_final.sum(axis=1), 100.0, atol=1e-9)
        assert res.info_lim_1t["A"]["pct_simulacoes_limitadas"] > 50


# ── A08: electorate → turnout → valid + blank/null ───────────────────────────

class TestAbsoluteVotes:

    def test_identities_with_explicit_blank_category(self):
        polls = _polls(["A", "B", "Brancos/Nulos"], [45, 35, 20], sd=2.0)
        df = simular_primeiro_turno(_config(n_sim=20_000), polls).df
        assert (df["votos_validos_1t"] + df["votos_invalidos_1t"] == df["comparecimento_1t"]).all()
        assert df["votos_validos_1t"].div(df["comparecimento_1t"]).mean() == pytest.approx(0.80, abs=0.002)
        assert (df["A_abs"] + df["B_abs"] <= df["votos_validos_1t"]).all()
        assert (df["votos_validos_1t"] - df["A_abs"] - df["B_abs"] <= 2).all()

    def test_blank_share_is_sampled_when_not_in_polls(self):
        df = simular_primeiro_turno(_config(n_sim=20_000), _polls("AB", [55, 45])).df
        assert df["invalidos_1t_pct"].mean() == pytest.approx(6.0, abs=0.1)
        assert df["invalidos_1t_pct"].std() > 1.0
        assert (df["votos_validos_1t"] < df["comparecimento_1t"]).all()


# ── A11: --bayesian is refused instead of mislabelling Dirichlet output ──────

class TestBayesianFlag:

    def test_engine_refuses_use_bayesian(self):
        with pytest.raises(ValueError, match="use_bayesian=True is not supported"):
            simular_primeiro_turno(_config(use_bayesian=True), _polls("AB", [55, 45]))

    def test_cli_rejects_flag_before_running(self, tmp_path, capsys):
        from src import cli
        csv = tmp_path / "polls.csv"
        csv.write_text("x\n", encoding="utf-8")
        args = cli._build_parser().parse_args(["run", "--csv", str(csv), "--bayesian"])
        assert cli._handle_run(args) == 1
        assert "--bayesian is not available" in capsys.readouterr().err

    def test_cli_result_carries_poll_sd(self):
        from src import cli
        polls = _polls("ABC", [45, 35, 20], sd=2.3)
        out = cli._run_simulation(_config(n_sim=2_000), polls)
        assert out.desvio_base == pytest.approx(2.3)
