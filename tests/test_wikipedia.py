"""Wikipedia transcription of 2010-2022 polls (calibration input)."""

from __future__ import annotations

from datetime import date
import math

import pandas as pd
import pytest

from src.core.aggregation import Z_MARGEM_ERRO
from src.io import wikipedia as wk

COLUNAS = ["ano", "turno", "secao", "cenario", "tipo", "instituto", "contratante",
           "data_inicio", "data_fim", "amostra", "margem_erro_pp", "registro_tse",
           "candidato", "pct", "linha_wiki", "soma_pct", "alertas", "fonte", "acesso"]


def _linha(linha, inst, fim, cand, pct, turno="1", cenario="", moe="", n="", alertas=""):
    return dict(ano="2018", turno=turno, secao="s", cenario=cenario, tipo="", instituto=inst,
                contratante="", data_inicio=fim, data_fim=fim, amostra=n, margem_erro_pp=moe,
                registro_tse="", candidato=cand, pct=pct, linha_wiki=str(linha), soma_pct="",
                alertas=alertas, fonte="https://pt.wikipedia.org/wiki/X", acesso="2026-11-11")


@pytest.fixture
def csv(tmp_path):
    rows = [
        # poll 10: full first-round scenario with a margin
        *[_linha(10, "A", "2018-10-05", c, p, moe="2.0") for c, p in
          (("Bolsonaro", "40"), ("Haddad", "25"), ("Gomes", "13"), ("Brancos/Nulos", "10"),
           ("Indecisos", "12"))],
        # poll 20: same institute and date, smaller scenario -> dropped
        *[_linha(20, "A", "2018-10-05", c, p, moe="2.0") for c, p in
          (("Bolsonaro", "45"), ("Haddad", "30"))],
        # poll 30: no margin, sample only
        *[_linha(30, "B", "2018-10-04", c, p, n="2500") for c, p in
          (("Bolsonaro", "38"), ("Haddad", "27"), ("Gomes", "12"))],
        # poll 40: missing Haddad -> dropped
        *[_linha(40, "C", "2018-10-03", c, p) for c, p in (("Bolsonaro", "39"), ("Gomes", "14"))],
        # poll 50: exit poll flagged -> dropped on load
        *[_linha(50, "D", "2018-10-07", c, p, alertas="boca_de_urna") for c, p in
          (("Bolsonaro", "45"), ("Haddad", "28"))],
        # poll 60: runoff head-to-head with a non-candidate column
        *[_linha(60, "A", "2018-10-26", c, p, turno="2", cenario="Haddad x Bolsonaro") for c, p in
          (("Haddad", "39"), ("Bolsonaro", "47"), ("Abst./Não decid.", "14"))],
    ]
    caminho = tmp_path / "w.csv"
    pd.DataFrame(rows, columns=COLUNAS).to_csv(caminho, index=False)
    return caminho


def test_load_drops_alerted_groups(csv):
    df = wk.carregar_wikipedia(csv)
    assert "50" not in set(df["linha_wiki"])
    assert df["data"].map(type).eq(date).all()
    assert df["pesquisa_id"].str.startswith("pt:").all()


def test_final_window_in_engine_format(csv):
    df = wk.carregar_wikipedia(csv)
    out = wk.pesquisas_reta_final(df, "2018", "1", {"Bolsonaro": "bolso", "Haddad": "Haddad"},
                                  date(2018, 9, 23), date(2018, 10, 6))
    assert set(out["pesquisa_id"].str.split(":").str[1]) == {"10", "30"}
    assert not out["candidato"].str.contains("Brancos|Indecisos").any()
    moe = out.groupby("pesquisa_id")["desvio_padrao_pct"].first()
    assert moe.min() == pytest.approx(Z_MARGEM_ERRO * 50 / math.sqrt(2500))
    assert moe.max() == pytest.approx(2.0)


def test_runoff_head_to_head_and_default_margin(csv):
    df = wk.carregar_wikipedia(csv)
    out = wk.pesquisas_reta_final(df, "2018", "2", {"Bolsonaro": "Bolsonaro", "Haddad": "Haddad"},
                                  date(2018, 10, 14), date(2018, 10, 27), so_dois=True)
    assert sorted(out["candidato"]) == ["Bolsonaro", "Haddad"]
    assert out["desvio_padrao_pct"].eq(wk.MOE_PADRAO_PP).all()


def test_empty_window_raises(csv):
    df = wk.carregar_wikipedia(csv)
    with pytest.raises(ValueError, match="No usable"):
        wk.pesquisas_reta_final(df, "2018", "1", {"Bolsonaro": "Bolsonaro", "Haddad": "Haddad"},
                                date(2018, 1, 1), date(2018, 1, 31))


def test_repository_file_integrity():
    df = pd.read_csv(wk.ARQUIVO_WIKIPEDIA, dtype=str, keep_default_na=False)
    assert list(df.columns) == COLUNAS
    assert set(df["ano"]) == {"2010", "2014", "2018", "2022"}
    # Election-day rows (exit polls, results) are always flagged.
    dias = {("2010", "1"): "2010-10-03", ("2010", "2"): "2010-10-31",
            ("2014", "1"): "2014-10-05", ("2014", "2"): "2014-10-26",
            ("2018", "1"): "2018-10-07", ("2018", "2"): "2018-10-28",
            ("2022", "1"): "2022-10-02", ("2022", "2"): "2022-10-30"}
    dia = df.apply(lambda r: dias[(r["ano"], r["turno"])], axis=1)
    no_dia = df[(df["data_fim"] != "") & (df["data_fim"] >= dia)]
    assert no_dia["alertas"].ne("").all()
    limpo = df[df["alertas"] == ""]
    assert pd.to_numeric(limpo["soma_pct"]).between(90, 110).all()
