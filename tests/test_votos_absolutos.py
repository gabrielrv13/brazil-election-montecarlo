"""Absolute-vote accounting shared by both rounds (audit A08, runoff)."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

from src.core.events import eventos_primeiro_turno, probabilidades_vitoria_2t
from src.core.simulation import (
    INVALIDOS_2T_MU,
    contabilizar_votos,
    dividir_validos,
)

ROOT = Path(__file__).resolve().parents[1]


class TestAccounting:

    def test_identities_and_prior(self):
        v = contabilizar_votos(np.random.default_rng(1), 50_000, 0.22, 0.03,
                               invalidos_mu=0.06, invalidos_sigma=0.025, eleitorado=158_600_000)
        assert (v["votos_validos"] + v["votos_invalidos"] == v["comparecimento"]).all()
        assert v["invalidos_frac"].mean() == pytest.approx(0.06, abs=0.002)
        assert v["comparecimento"].mean() == pytest.approx(158_600_000 * 0.78, rel=0.003)

    def test_explicit_blank_share_is_used(self):
        frac = np.full(10, 0.05)
        v = contabilizar_votos(np.random.default_rng(1), 10, 0.2, 0.0, invalidos_frac=frac,
                               eleitorado=1_000_000)
        np.testing.assert_array_equal(v["votos_invalidos"], 40_000)
        np.testing.assert_array_equal(v["votos_validos"], 760_000)

    @pytest.mark.parametrize("frac", [np.full(3, 1.0), np.full(3, -0.1), np.full(2, 0.1),
                                      np.array([0.1, np.nan, 0.1])])
    def test_invalid_blank_share_rejected(self, frac):
        with pytest.raises(ValueError, match="invalidos_frac"):
            contabilizar_votos(np.random.default_rng(1), 3, 0.2, 0.01, invalidos_frac=frac)

    def test_largest_remainder_split_is_exact(self):
        rng = np.random.default_rng(2)
        shares = rng.dirichlet(np.ones(4), 2_000) * 100
        validos = rng.integers(0, 10_000_000, 2_000)
        out = dividir_validos(validos, shares)
        np.testing.assert_array_equal(out.sum(axis=1), validos)
        assert (np.abs(out - validos[:, None] * shares / 100) < 1).all()
        assert out.dtype == np.int64


@pytest.fixture
def s2(monkeypatch, tmp_path):
    sys.path.insert(0, str(ROOT / "src"))
    import simulation_2turno as mod
    monkeypatch.setattr(mod, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(mod, "N_SIM", 20_000)
    return mod


class TestStandaloneRunoff:

    def test_calibrated_path_splits_valid_votes_only(self, s2):
        np.random.seed(5)
        df = s2.simular_calibrado("A", "B", 51.0, sd_fatia_pp=3.0)
        assert (df.votos_a_abs + df.votos_b_abs == df.votos_validos).all()
        assert (df.votos_validos + df.votos_invalidos == df.comparecimento).all()
        # No explicit blank pool in the two-party path: the runoff prior is used.
        assert df.invalidos_pct.mean() == pytest.approx(INVALIDOS_2T_MU * 100, abs=0.1)
        assert (df.votos_validos < df.comparecimento).all()
        assert df.margem_votos.equals((df.votos_a_abs - df.votos_b_abs).abs())

    def test_legacy_pool_uses_drawn_blank_share(self, s2):
        np.random.seed(6)
        df = s2.simular("A", "B", 46.0, 44.0, 0.0, 0.0, s2.sd_fatia_para_desvio(2.0), 10.0)
        assert df.invalidos_pct.mean() == pytest.approx(10.0, abs=0.3)
        assert (df.votos_a_abs + df.votos_b_abs == df.votos_validos).all()

    def test_median_margin_reflects_valid_votes(self, s2):
        np.random.seed(7)
        df = s2.simular_calibrado("A", "B", 52.0, sd_fatia_pp=0.5)
        # 4 pp margin over valid votes, not over turnout.
        esperado = 0.04 * df.votos_validos.median()
        assert df.margem_votos.median() == pytest.approx(esperado, rel=0.05)


def test_legacy_dynamic_runoff_accounting(tmp_path):
    sys.path.insert(0, str(ROOT / "tests"))
    from test_election_events import CANDIDATES, extract_function

    def confronto(a, b, outros, ra, rb, n):
        return np.full(n, 55.0), np.full(n, 45.0)

    namespace = dict(np=np, pd=pd, CANDIDATOS=CANDIDATES, REJEICAO=np.zeros(3),
                     OUTPUT_DIR=tmp_path, ABSTENCAO_2T_MU=.22, ABSTENCAO_2T_SIGMA=.03,
                     ELEITORADO=100_000, _simular_confronto=confronto,
                     eventos_primeiro_turno=eventos_primeiro_turno,
                     probabilidades_vitoria_2t=probabilidades_vitoria_2t)
    simulate = extract_function(str(ROOT / "src/simulation_v2.py"), "simular_segundo_turno", namespace)
    np.random.seed(3)
    out, _ = simulate(np.array([[45.0, 35.0, 20.0]] * 200), CANDIDATES)
    assert (out.votos_a_abs + out.votos_b_abs == out.votos_validos_2t).all()
    assert (out.votos_validos_2t < out.comparecimento_2t).all()
    assert out.invalidos_2t_pct.mean() == pytest.approx(INVALIDOS_2T_MU * 100, abs=0.5)
