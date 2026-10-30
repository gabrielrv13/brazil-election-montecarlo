"""Tests for the calibrated runoff additions in src/simulation_2turno.py (v2.10)."""

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import simulation_2turno as s2  # noqa: E402

REF = date(2026, 10, 13)


def _polls(rows: list) -> pd.DataFrame:
    """Builds a runoff poll frame from (instituto, data, cand, value) tuples."""
    df = pd.DataFrame(rows, columns=["instituto", "data", "candidato", "intencao_voto_pct"])
    df["rejeicao_pct"] = 0.0
    df["desvio_padrao_pct"] = 2.0
    return df


def _pair(inst: str, d: date, a: float, b: float) -> list:
    return [(inst, d, "Alpha", a), (inst, d, "Beta", b)]


# ── sd_fatia_para_desvio ──────────────────────────────────────────────────────

@pytest.mark.parametrize("bad", [0.0, -1.0, 5.0, 50.0])
def test_sd_fatia_rejects_out_of_range(bad):
    with pytest.raises(ValueError):
        s2.sd_fatia_para_desvio(bad)


def test_sd_fatia_is_increasing():
    sds = [0.5, 1.0, 2.5, 4.0]
    ds = [s2.sd_fatia_para_desvio(s) for s in sds]
    assert ds == sorted(ds)


@pytest.mark.parametrize("target", [0.8, 1.5, 2.5, 3.5])
def test_sd_fatia_matches_empirical_sd(target):
    fator = max(100.0 / s2.sd_fatia_para_desvio(target), 1.0)
    rng = np.random.default_rng(0)
    share = rng.dirichlet([51 * fator, 49 * fator], size=200_000)[:, 0] * 100
    assert share.std() == pytest.approx(target, rel=0.05)


# ── agregar_fatia_dois_candidatos ─────────────────────────────────────────────

def test_fatia_ignores_undecided_level():
    rows = _pair("High", date(2026, 10, 12), 46.0, 44.0) + _pair("Low", date(2026, 10, 12), 40.0, 38.0)
    cand_a, cand_b, fatia, info = s2.agregar_fatia_dois_candidatos(_polls(rows), REF)
    assert cand_a == "Alpha"
    assert fatia == pytest.approx((46 / 90 + 40 / 78) / 2 * 100, abs=1e-6)
    assert info["soma_min"] == pytest.approx(78.0)
    assert info["soma_max"] == pytest.approx(90.0)


def test_fatia_orders_leader_first():
    rows = _pair("X", date(2026, 10, 12), 40.0, 50.0)
    cand_a, cand_b, fatia, _ = s2.agregar_fatia_dois_candidatos(_polls(rows), REF)
    assert (cand_a, cand_b) == ("Beta", "Alpha")
    assert fatia == pytest.approx(50 / 90 * 100)


def test_fatia_recent_poll_weighs_more():
    old = _pair("X", date(2026, 8, 1), 40.0, 50.0)
    new = _pair("Y", date(2026, 10, 12), 50.0, 40.0)
    _, _, fatia, info = s2.agregar_fatia_dois_candidatos(_polls(old + new), REF)
    assert fatia > 54.0
    assert info["n_efetivo"] < 2.0


def test_fatia_data_min_filters():
    old = _pair("X", date(2026, 9, 1), 40.0, 50.0)
    new = _pair("Y", date(2026, 10, 12), 50.0, 40.0)
    _, _, fatia, info = s2.agregar_fatia_dois_candidatos(
        _polls(old + new), REF, data_min=date(2026, 10, 5)
    )
    assert info["n_pesquisas"] == 1
    assert fatia == pytest.approx(50 / 90 * 100)


def test_fatia_requires_two_candidates():
    rows = _pair("X", date(2026, 10, 12), 40.0, 50.0) + [("X", date(2026, 10, 12), "Gamma", 5.0)]
    with pytest.raises(ValueError):
        s2.agregar_fatia_dois_candidatos(_polls(rows), REF)


def test_fatia_empty_after_filter_raises():
    rows = _pair("X", date(2026, 9, 1), 40.0, 50.0)
    with pytest.raises(ValueError):
        s2.agregar_fatia_dois_candidatos(_polls(rows), REF, data_min=date(2026, 10, 5))


# ── tabela_sensibilidade ──────────────────────────────────────────────────────

def test_sensibilidade_symmetry_at_fifty():
    t = s2.tabela_sensibilidade(50.0, vieses_pp=(0.0,), n_sim=100_000)
    assert t.loc[0.0].between(48.5, 51.5).all()


def test_sensibilidade_monotonic():
    t = s2.tabela_sensibilidade(51.0, vieses_pp=(0.0, 1.0, 2.0, 3.0), n_sim=60_000)
    assert (t.diff().iloc[1:] > 0).all().all()          # more bias -> higher P
    assert (t.diff(axis=1).iloc[:, 1:] < 0).all().all()  # more sd -> lower P


def test_sensibilidade_matches_normal_approximation():
    t = s2.tabela_sensibilidade(51.5, sds_pp=(2.5,), vieses_pp=(0.0,), n_sim=200_000)
    assert t.iloc[0, 0] == pytest.approx(norm.cdf(1.5 / 2.5) * 100, abs=1.0)


def test_sensibilidade_is_reproducible():
    a = s2.tabela_sensibilidade(51.0, n_sim=10_000, seed=1)
    b = s2.tabela_sensibilidade(51.0, n_sim=10_000, seed=1)
    pd.testing.assert_frame_equal(a, b)


# ── simular_calibrado ─────────────────────────────────────────────────────────

def test_simular_calibrado_probability(monkeypatch, tmp_path):
    monkeypatch.setattr(s2, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(s2, "N_SIM", 40_000)
    df = s2.simular_calibrado("Alpha", "Beta", 51.5, sd_fatia_pp=2.5)
    prob = (df["vencedor"] == "Alpha").mean()
    assert prob == pytest.approx(norm.cdf(1.5 / 2.5), abs=0.02)
    assert (tmp_path / "resultados_2turno_standalone.csv").exists()


def test_simular_calibrado_bias_shifts_probability(monkeypatch, tmp_path):
    monkeypatch.setattr(s2, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(s2, "N_SIM", 20_000)
    base = s2.simular_calibrado("A", "B", 50.5, vies_pp_a=0.0)
    shifted = s2.simular_calibrado("A", "B", 50.5, vies_pp_a=2.0)
    assert (shifted["vencedor"] == "A").mean() > (base["vencedor"] == "A").mean() + 0.1


@pytest.mark.parametrize("fatia,vies", [(99.0, 2.0), (1.0, -2.0)])
def test_simular_calibrado_rejects_shift_out_of_range(fatia, vies):
    with pytest.raises(ValueError):
        s2.simular_calibrado("A", "B", fatia, vies_pp_a=vies)


# ── salvar_resumo ─────────────────────────────────────────────────────────────

def test_salvar_resumo_roundtrip(monkeypatch, tmp_path):
    import json
    monkeypatch.setattr(s2, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(s2, "N_SIM", 5_000)
    df = s2.simular_calibrado("Alpha", "Beta", 51.5)
    tabela = s2.tabela_sensibilidade(51.5, n_sim=5_000)
    info = {"n_pesquisas": 10, "n_efetivo": 6.4, "institutos": ["X", "Y"], "soma_media": 90.0}
    caminho = s2.salvar_resumo(tmp_path / "r.json", df, "Alpha", "Beta", 51.5,
                               {"sd_fatia_pp": 2.5, "vies_pp_a": 0.0, "tau": 7.0, "data_min": None},
                               info, tabela)
    r = json.loads(caminho.read_text(encoding="utf-8"))
    assert r["p_vitoria_a"] + r["p_vitoria_b"] == pytest.approx(100.0, abs=0.01)
    assert r["pesquisas"]["n_institutos"] == 2
    assert "-1.0" in r["sensibilidade"] and "2.5" in r["sensibilidade"]["0.0"]

@pytest.mark.parametrize("bias", [-5.0, 0.0, 5.0])
@pytest.mark.parametrize("reverse", [False, True])
def test_a06_contract_draws_chart_and_posts(monkeypatch, tmp_path, bias, reverse):
    import json
    import publicar_2turno as pub
    monkeypatch.setattr(s2, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(s2, "N_SIM", 40_000)
    np.random.seed(123)
    a, b, share = ("Beta", "Alpha", 49.0) if reverse else ("Alpha", "Beta", 51.0)
    signed = s2.resolver_vies(a, b, "Alpha", bias)
    df = s2.simular_calibrado(a, b, share, vies_pp_a=signed)
    expected = share + signed
    assert df.voto_a.mean() == pytest.approx(expected, abs=0.06)
    info = {"n_pesquisas": 2, "n_efetivo": 2., "institutos": ["X"], "soma_media": 100.}
    params = {"sd_fatia_pp": 2.5, "vies_pp_a": signed, "vies_candidato": "Alpha",
              "vies_pp": bias, "tau": 7., "data_min": None}
    path = s2.salvar_resumo(tmp_path / "r.json", df, a, b, share, params, info, pd.DataFrame())
    r = json.loads(path.read_text(encoding="utf-8"))
    pub.validar_resumo(r)
    assert r["fatia_a"] == r["fatia_agregada_a"] == share
    assert r["fatia_central_a"] == expected
    assert r["fatia_simulada_media_a"] == round(df.voto_a.mean(), 3)
    assert r["fatia_a_ic90"] == [round(x, 2) for x in df.voto_a.quantile([.05, .95])]
    assert r["p_vitoria_a"] == round((df.vencedor == a).mean() * 100, 2)
    for lang in ("pt", "en"):
        text = pub.gerar_post(r, lang)
        sep = "," if lang == "pt" else "."
        assert f"{df.voto_a.mean():.1f}%".replace(".", sep) in text
        assert f"{share:.1f}%".replace(".", sep) in text
    figures = []
    monkeypatch.setattr(s2.plt, "savefig", lambda *args, **kwargs: figures.append(s2.plt.gcf()))
    s2.graficos(df, a, b, 0, 0, r["p_vitoria_a"], r["p_vitoria_b"])
    ax = figures[0].axes[1]
    lines = [line.get_xdata()[0] for line in ax.lines]
    assert df.voto_a.mean() in lines
    assert share in lines and expected in lines
    assert any("simulad" in t.get_text() for t in ax.texts)
    r["parametros"]["vies_pp"] += 1
    with pytest.raises(ValueError, match="vies_pp"):
        pub.validar_resumo(r)


def test_a06_ceiling_mean_is_measured_not_inferred(monkeypatch, tmp_path):
    monkeypatch.setattr(s2, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(s2, "N_SIM", 10_000)
    np.random.seed(42)
    df = s2.simular_calibrado("A", "B", 51, vies_pp_a=-5, usar_teto=True, rej_a=70)
    assert df.attrs["calibracao"]["fatia_central_a"] == 46
    assert df.voto_a.mean() < 40  # ceiling and valid-vote renormalization follow sampling


def test_a06_cli_requires_identity():
    with pytest.raises(ValueError, match="vies-candidato"):
        s2.main(["--vies", "-5"])
    with pytest.raises(ValueError, match="vies_candidato"):
        s2.resolver_vies("A", "B", "unknown", -5)
