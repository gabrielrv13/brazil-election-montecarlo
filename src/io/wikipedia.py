"""
Final-week polls of past elections (2010-2022) transcribed from Wikipedia.

``data/wikipedia/pesquisas_wikipedia_2010_2022.csv`` is a long table (one
row per poll, scenario and candidate) extracted from the Wikipedia poll
pages; see ``data/wikipedia/README.md`` for sources, access date and known
problems. Every poll group carries an ``alertas`` field; groups with any
alert (exit poll, official result, missing date, sum outside 90-110%,
ambiguous 2014 PSB scenario) are dropped here.

This is a secondary source used only for calibration. It does not replace
the TSE-based catalogue in ``data/historico_v2``.
"""

from __future__ import annotations

from datetime import date
import math
from pathlib import Path
import re

import pandas as pd

from src.core.aggregation import Z_MARGEM_ERRO

ARQUIVO_WIKIPEDIA = (
    Path(__file__).resolve().parents[2] / "data/wikipedia/pesquisas_wikipedia_2010_2022.csv")

# Columns that are not candidates: blank/null, undecided, others, abstention.
_NAO_CANDIDATO = re.compile(r"branc|nulo|indecis|outro|absten|abst\.|decid|nenhum", re.I)
# Fallback margin of error (pp at 95%) when the page gives neither margin nor sample.
MOE_PADRAO_PP = 2.0


def carregar_wikipedia(caminho: Path = ARQUIVO_WIKIPEDIA) -> pd.DataFrame:
    """Read the transcription and drop every poll group with an alert."""
    df = pd.read_csv(caminho, dtype=str, keep_default_na=False)
    df = df[df["alertas"] == ""].copy()
    df["pct"] = pd.to_numeric(df["pct"], errors="coerce")
    df = df[df["pct"].notna()]
    df["data"] = pd.to_datetime(df["data_fim"], errors="raise").dt.date
    fonte = df["fonte"].str.contains("en.wikipedia").map({True: "en", False: "pt"})
    df["pesquisa_id"] = fonte + ":" + df["linha_wiki"] + ":" + df["cenario"]
    return df


def _moe(grupo: pd.DataFrame) -> float:
    """Margin of error (pp, 95%) of one poll: stated, else from sample, else default."""
    m = pd.to_numeric(grupo["margem_erro_pp"], errors="coerce").dropna()
    if not m.empty and m.iloc[0] > 0:
        return float(m.iloc[0])
    n = pd.to_numeric(grupo["amostra"], errors="coerce").dropna()
    if not n.empty and n.iloc[0] > 0:
        return float(Z_MARGEM_ERRO * 50.0 / math.sqrt(n.iloc[0]))
    return MOE_PADRAO_PP


def pesquisas_reta_final(
    df: pd.DataFrame, ano: str, turno: str, nomes: dict[str, str],
    inicio: date, fim: date, so_dois: bool = False,
) -> pd.DataFrame:
    """Polls of one election round in ``[inicio, fim]`` in the engine's format.

    Args:
        df: Output of :func:`carregar_wikipedia`.
        ano: Election year (``"2010"`` ... ``"2022"``).
        turno: ``"1"`` or ``"2"``.
        nomes: ``{canonical name: case-insensitive substring}`` for the two
            tracked candidates; matching rows are renamed to the canonical
            name. Both must be present for a poll to be kept.
        inicio: First fieldwork end date kept.
        fim: Last fieldwork end date kept (the as-of date).
        so_dois: Keep only head-to-head polls between the two candidates.

    Returns:
        Rows ``pesquisa_id, instituto, data, candidato, intencao_voto_pct,
        desvio_padrao_pct``. When an institute released several scenarios on
        the same date, the one with most candidates is kept.
    """
    s = df[(df["ano"] == ano) & (df["turno"] == turno)
           & (df["data"] >= inicio) & (df["data"] <= fim)]
    s = s[~s["candidato"].str.contains(_NAO_CANDIDATO)].copy()
    canon = pd.Series(pd.NA, index=s.index, dtype=object)
    for nome, padrao in nomes.items():
        canon[s["candidato"].str.contains(padrao, case=False, regex=False)] = nome
    s["candidato"] = canon.fillna(s["candidato"])

    grupos = []
    for _, g in s.groupby("pesquisa_id", sort=False):
        presentes = set(g["candidato"])
        if not set(nomes) <= presentes:
            continue
        if so_dois and presentes != set(nomes):
            continue
        if g["candidato"].duplicated().any():
            continue  # two columns matched the same canonical name
        grupos.append(g.assign(desvio_padrao_pct=_moe(g), _n=len(g)))
    if not grupos:
        raise ValueError(f"No usable {ano} round-{turno} polls between {inicio} and {fim}")
    out = pd.concat(grupos)
    melhor = (out.groupby(["instituto", "data", "pesquisa_id"])["_n"].first()
              .reset_index().sort_values("_n", ascending=False)
              .drop_duplicates(["instituto", "data"]))
    out = out[out["pesquisa_id"].isin(melhor["pesquisa_id"])]
    return (out.rename(columns={"pct": "intencao_voto_pct"})
            [["pesquisa_id", "instituto", "data", "candidato", "intencao_voto_pct",
              "desvio_padrao_pct"]]
            .reset_index(drop=True))
