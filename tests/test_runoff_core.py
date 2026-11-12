"""Second round on the core engine: aggregation, simulation, CLI and pipeline."""

from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from src.core.config import PollData, RunoffConfig, SimulationConfig
from src.core.runoff import (
    AgregacaoRunoff,
    agregar_fatia,
    fatias_por_pesquisa,
    resolver_vies,
    simular_runoff,
    simular_segundo_turno_dinamico,
    tabela_sensibilidade_runoff,
)
from src.core.simulation import concentracao_dirichlet

ROOT = Path(__file__).resolve().parents[1]
REF = date(2026, 10, 24)


def _polls(rows):
    """rows: (instituto, days_ago, A, B, moe)."""
    out = []
    for inst, ago, a, b, moe in rows:
        d = (REF - timedelta(days=ago)).isoformat()
        out += [dict(candidato="Alfa", intencao_voto_pct=a, desvio_padrao_pct=moe, instituto=inst, data=d),
                dict(candidato="Beta", intencao_voto_pct=b, desvio_padrao_pct=moe, instituto=inst, data=d)]
    return pd.DataFrame(out)


def _ag(fatia=52.0, sd=0.5, rej=(0.0, 0.0)):
    return AgregacaoRunoff("Alfa", "Beta", fatia, sd, *rej, info={})


class TestAggregation:

    def test_share_and_standard_error_per_poll(self):
        df = fatias_por_pesquisa(_polls([("X", 0, 45.0, 45.0, 2.0)]), ["instituto", "data"])
        assert df.fatia.iloc[0] == pytest.approx(50.0)
        # SE of the share is the 50% margin scaled by 1/sqrt(s): s = 0.9.
        assert df.desvio_fatia.iloc[0] == pytest.approx(2.0 / np.sqrt(0.9))

    @pytest.mark.parametrize("mutar,erro", [
        (lambda d: pd.concat([d, d.iloc[[0]]]), "Duplicated"),
        (lambda d: d.iloc[:-1], "Incomplete"),
        (lambda d: pd.concat([d, d.iloc[[0]].assign(candidato="Gama")]), "exactly 2"),
    ])
    def test_invalid_poll_sets_are_rejected(self, mutar, erro):
        df = mutar(_polls([("X", 0, 45.0, 44.0, 2.0), ("Y", 1, 46.0, 43.0, 2.0)]))
        with pytest.raises(ValueError, match=erro):
            fatias_por_pesquisa(df, ["instituto", "data"])

    def test_pesquisa_id_key_keeps_date_and_institute(self):
        df = _polls([("X", 0, 45.0, 44.0, 2.0), ("X", 0, 47.0, 42.0, 2.0)])
        df["pesquisa_id"] = ["p1", "p1", "p2", "p2"]
        por = fatias_por_pesquisa(df, ["pesquisa_id"])
        assert list(por["instituto"]) == ["X", "X"] and por["data"].notna().all()
        df["data"] = pd.to_datetime(df["data"]).dt.date
        assert agregar_fatia(df, REF).info["n_pesquisas"] == 2

    def test_leader_becomes_cand_a(self):
        ag = agregar_fatia(_polls([("X", d, 40.0, 50.0, 2.0) for d in range(3)]), REF)
        assert (ag.cand_a, ag.cand_b) == ("Beta", "Alfa")
        assert ag.fatia_a == pytest.approx(100 * 50 / 90, abs=0.01)

    def test_house_effect_on_the_share_is_removed(self):
        rng = np.random.default_rng(4)
        rows = []
        for d in range(0, 30, 3):
            for inst, ago, vies in (("N1", d + 3, 0.0), ("N2", d + 5, 0.0), ("Alta", d, 3.0)):
                e = rng.normal(0, 0.5)
                rows.append((inst, ago, 46.0 + vies + e, 44.0 - vies - e, 2.0))
        df = _polls(rows)
        bruto = agregar_fatia(df, REF, efeitos_instituto=False)
        ajustado = agregar_fatia(df, REF, efeitos_instituto=True)
        alvo = 51.0 + 3.0 / 3  # industry average: one of three houses is +3 on the share
        assert abs(ajustado.fatia_a - alvo) < abs(bruto.fatia_a - alvo)


class TestSimulation:

    def test_beta_oracle_without_common_error(self):
        df = simular_runoff(_ag(52.0, 1.0), 200_000, np.random.default_rng(1), 0.0, 5.0, 0.0)
        a0 = concentracao_dirichlet(1.0)
        beta = stats.beta(0.52 * a0, 0.48 * a0)
        assert df.voto_a.std() == pytest.approx(100 * beta.std(), rel=0.01)
        assert (df.vencedor == "Alfa").mean() == pytest.approx(beta.sf(0.5), abs=0.005)

    def test_variances_add_and_bias_shifts_the_centre(self):
        df = simular_runoff(_ag(50.0, 0.4), 200_000, np.random.default_rng(2), 3.0, np.inf, 1.0,
                            vies_pp_a=-2.0)
        assert df.voto_a.std() == pytest.approx(np.sqrt(0.4**2 + 3**2 + 1), rel=0.02)
        assert df.voto_a.mean() == pytest.approx(48.0, abs=0.05)
        meta = df.attrs["calibracao"]
        assert (meta["fatia_agregada_a"], meta["fatia_central_a"], meta["vies_pp_a"]) == (50.0, 48.0, -2.0)

    def test_accounting_and_optional_ceiling(self):
        df = simular_runoff(_ag(55.0, 0.5, (48.0, 30.0)), 20_000, np.random.default_rng(3),
                            3.0, 5.0, 0.0, usar_teto=True)
        assert (df.voto_a <= 52.0 + 1e-9).all()
        assert (df.votos_a_abs + df.votos_b_abs == df.votos_validos).all()
        assert (df.votos_validos + df.votos_invalidos == df.comparecimento).all()
        with pytest.raises(ValueError, match="Infeasible"):
            simular_runoff(_ag(55.0, 0.5, (60.0, 60.0)), 100, np.random.default_rng(3),
                           3.0, 5.0, 0.0, usar_teto=True)

    def test_sensitivity_is_monotone_in_bias(self):
        t = tabela_sensibilidade_runoff(_ag(51.0, 0.3), n_sim=20_000)
        for sd in t.columns:
            assert t[sd].is_monotonic_increasing
        assert list(t.columns) == [0.8, 1.5, 2.5, 3.0, 3.5]

    def test_bias_resolution(self):
        assert resolver_vies("A", "B", "B", 2.0) == -2.0
        with pytest.raises(ValueError, match="vies_candidato"):
            resolver_vies("A", "B", "C", 1.0)


class TestConfigAndWindow:

    def test_default_window_starts_after_first_round(self):
        assert RunoffConfig().janela_inicio == date(2026, 10, 5)
        assert RunoffConfig(data_min=date(2026, 9, 1)).janela_inicio == date(2026, 9, 1)

    @pytest.mark.parametrize("kw,erro", [
        (dict(vies_pp=1.0), "vies_candidato"),
        (dict(runoff_date=date(2026, 10, 4)), "runoff_date"),
        (dict(sd_erro_comum_pp=-1.0), "sd_erro_comum_pp"),
        (dict(gl_erro_comum=2.0), "gl_erro_comum"),
    ])
    def test_invalid_config(self, kw, erro):
        with pytest.raises(ValueError, match=erro):
            RunoffConfig(**kw)

    def test_full_base_cut_reproduces_post_first_round_base(self):
        from src.io.runoff import carregar_runoff
        a = carregar_runoff(RunoffConfig(csv_path=ROOT / "data/pesquisas_2turno.csv", as_of=REF))
        b = carregar_runoff(RunoffConfig(csv_path=ROOT / "data/pesquisas_only_2turno.csv", as_of=REF))
        assert a.info["n_pesquisas"] == b.info["n_pesquisas"] == 52
        assert a.fatia_a == pytest.approx(b.fatia_a)

    def test_empty_window_is_an_error(self, tmp_path):
        from src.io.runoff import carregar_runoff
        csv = tmp_path / "p.csv"
        _polls([("X", 30, 45.0, 44.0, 2.0)]).to_csv(csv, index=False)
        with pytest.raises(ValueError, match="No runoff polls"):
            carregar_runoff(RunoffConfig(csv_path=csv, as_of=REF))


class TestCliRunoff:

    def _run(self, tmp_path, seed=7):
        from src import cli
        args = cli._build_parser().parse_args(
            ["runoff", "--csv", str(ROOT / "data/pesquisas_only_2turno.csv"), "--as-of", "2026-10-24",
             "--seed", str(seed), "--n-sim", "5000", "--saida", str(tmp_path)])
        assert cli._handle_runoff(args) == 0
        return json.loads((tmp_path / "resumo_2turno.json").read_text(encoding="utf-8"))

    def test_outputs_pass_the_publication_gate(self, tmp_path):
        sys.path.insert(0, str(ROOT / "src"))
        import publicar_2turno as pub
        from src.io.manifest import caminho_manifesto, verificar_manifesto
        resumo = self._run(tmp_path)
        pub.validar_resumo(resumo, max_horas=24)
        assert resumo["parametros"]["modelo"] == "core_v3"
        manifesto = json.loads(caminho_manifesto(tmp_path / "resumo_2turno.json").read_text(encoding="utf-8"))
        assert verificar_manifesto(manifesto) == []
        assert {Path(s["caminho"]).name for s in manifesto["saidas"]} == {
            "resumo_2turno.json", "resultados_2turno_standalone.csv", "simulacao_2turno.png"}

    def test_same_seed_same_forecast(self, tmp_path):
        a = self._run(tmp_path / "a")
        b = self._run(tmp_path / "b")
        assert a["p_vitoria_a"] == b["p_vitoria_a"] and a["fatia_a_ic90"] == b["fatia_a_ic90"]

    def test_missing_csv_is_reported(self, tmp_path, capsys):
        from src import cli
        args = cli._build_parser().parse_args(["runoff", "--csv", str(tmp_path / "nada.csv")])
        assert cli._handle_runoff(args) == 1
        assert "not found" in capsys.readouterr().err


class TestDynamicRunoff:

    def test_lower_rejection_finalist_gets_more_transfers(self):
        votos = np.array([[40.0, 40.0, 20.0]] * 20_000)
        out, _ = simular_segundo_turno_dinamico(votos, ["A", "B", "C"], np.array([60.0, 20.0, 0.0]),
                                                np.random.default_rng(5))
        assert out.voto_a.mean() < 50 < out.voto_b.mean()

    def test_pipeline_keeps_first_round_draws_and_fills_runoff(self):
        from src.core.pipeline import montar_resultado
        from src.core.simulation import simular_primeiro_turno
        polls = PollData(candidatos=["A", "B", "C"], votos_media=np.array([42.0, 38.0, 20.0]),
                         rejeicao=np.zeros(3), desvio_base=0.5, indecisos=0.0)
        cfg = SimulationConfig(n_sim=4_000, seed=11, election_date=date(2020, 1, 1))
        result = montar_resultado(cfg, polls)
        sozinho = simular_primeiro_turno(cfg, polls)
        pd.testing.assert_frame_equal(result.df1, sozinho.df)
        assert sum(result.p2v.values()) == pytest.approx(1.0)
        assert result.info_matchups and not result.df2.empty
