"""Tests for src/retrospectiva_1t.py using synthetic poll files."""

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import retrospectiva_1t as r  # noqa: E402

CORTE = date(2026, 10, 3)


def _csv(tmp_path: Path, rows: list) -> Path:
    df = pd.DataFrame(rows, columns=["candidato", "intencao_voto_pct", "instituto", "data"])
    path = tmp_path / "pesquisas.csv"
    df.to_csv(path, index=False)
    return path


def _poll(inst, d, f, l, outros=5.0, bn=4.0):
    return [("Flávio Bolsonaro", f, inst, d), ("Lula", l, inst, d),
            ("Outros", outros, inst, d), ("Brancos/Nulos", bn, inst, d)]


def test_resultado_validos_sums_to_100():
    assert sum(r.resultado_validos().values()) == pytest.approx(100.0, abs=0.1)


def test_resultado_validos_matches_reported_shares():
    v = r.resultado_validos()
    assert v["Flavio Bolsonaro"] == pytest.approx(47.02, abs=0.01)
    assert v["Lula"] == pytest.approx(45.15, abs=0.01)


@pytest.mark.parametrize("nome,esperado", [
    ("Flávio Bolsonaro", "Flavio Bolsonaro"), ("Lula", "Lula"), ("Renan Santos", "Renan Santos"),
    ("Outros", "Outros"), ("Brancos/Nulos", None),
])
def test_chave_candidato(nome, esperado):
    assert r.chave_candidato(nome) == esperado


def test_text_numbers_and_dates_are_coerced(tmp_path):
    rows = [("Lula", "45,5", "A", "03/10/2026"), ("Flávio Bolsonaro", "44.0%", "A", "2026-10-03"),
            ("Lula", "n/d", "B", "2026-10-02")]
    df, q = r.carregar_pesquisas_1t(_csv(tmp_path, rows), CORTE)
    assert set(df["intencao_voto_pct"]) == {45.5, 44.0}
    assert q["descartadas_valor_ou_data"] == 1


def test_polls_after_cutoff_are_ignored(tmp_path):
    rows = _poll("A", "2026-10-02", 45, 44) + _poll("B", "2026-10-04", 60, 30)
    df, q = r.carregar_pesquisas_1t(_csv(tmp_path, rows), CORTE)
    assert q["apos_data_corte_ignoradas"] == 4
    assert (df["data"] <= CORTE).all()


def test_missing_column_raises(tmp_path):
    path = tmp_path / "x.csv"
    pd.DataFrame({"candidato": ["Lula"]}).to_csv(path, index=False)
    with pytest.raises(ValueError):
        r.carregar_pesquisas_1t(path, CORTE)


def test_blank_votes_are_excluded_from_denominator(tmp_path):
    rows = _poll("A", "2026-10-02", 40.0, 40.0, outros=10.0, bn=10.0)
    df, _ = r.carregar_pesquisas_1t(_csv(tmp_path, rows), CORTE)
    sh = r.fatias_validas(df)
    assert sh["Lula"].iloc[0] == pytest.approx(40 / 90 * 100)


def test_bias_sign_when_polls_underestimate_flavio(tmp_path):
    # Polls say 50/50 in the two-party share; the result implies about 51.0
    rows = _poll("A", "2026-10-02", 44.0, 44.0) + _poll("B", "2026-10-01", 45.0, 45.0)
    df, _ = r.carregar_pesquisas_1t(_csv(tmp_path, rows), CORTE)
    cal = r.calibrar(r.fatias_validas(df), CORTE, 7.0)
    assert cal["vies_sugerido_pp_flavio"] == pytest.approx(
        cal["fatia_flavio_resultado"] - 50.0, abs=0.01)
    assert cal["vies_sugerido_pp_flavio"] > 0.9


def test_main_writes_json(tmp_path):
    rows = _poll("A", "2026-10-02", 44.0, 44.0)
    saida = tmp_path / "out" / "cal.json"
    res = r.main(["--csv", str(_csv(tmp_path, rows)), "--saida", str(saida)])
    assert saida.exists()
    assert "calibracao" in res
