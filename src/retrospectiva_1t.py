"""
brazil-election-montecarlo — First-round retrospective and runoff calibration
=============================================================================
Compares the poll average as of the day before the first round with the
official result and derives the bias (pp, two-party share) to feed into the
runoff simulation.

What it does:
    1. Loads data/pesquisas.csv (first-round polls), coercing text numbers such
       as "41,5" or "41.5%" and dates in ISO or dd/mm/yyyy.
    2. Keeps polls dated up to ``--data-corte`` (default 2026-10-03).
    3. Converts every poll to valid-vote shares (blank/null/undecided rows are
       excluded from the denominator) and averages them with exponential decay.
    4. Compares each candidate with the result and reports the error.
    5. Computes the Flavio/(Flavio+Lula) two-party share predicted by polls
       against the share implied by the result. The difference is the
       suggested bias for ``simulation_2turno.py --vies``.

Usage:
    python src/retrospectiva_1t.py
    python src/retrospectiva_1t.py --csv data/pesquisas.csv --data-corte 2026-10-03

Output:
    outputs/calibracao_1t.json

License: MIT
"""

import sys
import json
import argparse
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Official first-round result, percent of TOTAL votes (blank/null included).
RESULTADO_1T_TOTAL = {
    "Flavio Bolsonaro": 44.78,
    "Lula": 43.00,
    "Cury": 2.75,
    "Renan Santos": 2.13,
    "Ronaldo Caiado": 2.07,
    "Romeu Zema": 0.25,
    "Outros": 0.22,
}
BRANCOS_NULOS_TOTAL = 4.77

# Token searched (accent-insensitive) in the poll's candidate name -> canonical key.
TOKENS = {
    "bolsonaro": "Flavio Bolsonaro",
    "lula": "Lula",
    "cury": "Cury",
    "santos": "Renan Santos",
    "caiado": "Ronaldo Caiado",
    "zema": "Romeu Zema",
    "outros": "Outros",
}
EXCLUIR_DA_BASE = ("branco", "nulo", "indeciso", "nao sabe", "ns/nr")


def normalizar(texto: str) -> str:
    """Lower-cases and strips accents."""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def resultado_validos() -> dict:
    """First-round result converted to percent of valid votes."""
    base = 100.0 - BRANCOS_NULOS_TOTAL
    return {c: v / base * 100.0 for c, v in RESULTADO_1T_TOTAL.items()}


def chave_candidato(nome: str) -> str | None:
    """Maps a poll candidate name to the canonical key, or None if unknown."""
    n = normalizar(nome)
    for token, chave in TOKENS.items():
        if token in n:
            return chave
    return None


def _para_numero(serie: pd.Series) -> pd.Series:
    """Coerces text such as '41,5' or '41.5%' to float (NaN when impossible)."""
    txt = serie.astype(str).str.replace("%", "", regex=False).str.strip()
    txt = txt.str.replace(",", ".", regex=False)
    return pd.to_numeric(txt, errors="coerce")


def _parse_datas(serie: pd.Series) -> pd.Series:
    """Parse only complete ISO or DD/MM/YYYY calendar dates."""
    from src.core.poll_quality import parse_date
    return serie.map(parse_date)


def carregar_pesquisas_1t(
    csv_path: Path, data_corte: date, *, cenario: str | None = None,
) -> tuple[pd.DataFrame, dict]:
    """
    Loads first-round polls dated up to ``data_corte``.

    Returns:
        (df, qualidade) where ``qualidade`` counts rows read, rows dropped for
        non-numeric values or invalid dates, rows after the cutoff and the date range.

    Raises:
        FileNotFoundError: If the CSV does not exist.
        ValueError: If required columns are missing or no row survives.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"File not found: {csv_path}")
    df = pd.read_csv(csv_path, dtype=str)
    faltam = {"candidato", "intencao_voto_pct", "instituto", "data"} - set(df.columns)
    if faltam:
        raise ValueError(f"Missing required columns: {sorted(faltam)}")

    q = {"linhas_lidas": int(len(df))}
    df["linha_csv"] = df.index + 2
    from src.core.poll_quality import select_scenario
    df = select_scenario(df, cenario)
    q["cenario"] = cenario
    q["linhas_cenario"] = int(len(df))
    df["intencao_voto_pct"] = _para_numero(df["intencao_voto_pct"])
    df["data"] = _parse_datas(df["data"])
    invalid = (~np.isfinite(df["intencao_voto_pct"]) |
               ~df["intencao_voto_pct"].between(0, 100) | df["data"].isna() |
               df["candidato"].isna() | df["instituto"].isna())
    q["diagnosticos"] = df.loc[invalid, ["linha_csv", "candidato"]].to_dict("records")
    q["descartadas_valor_ou_data"] = int(invalid.sum())
    from src.core.poll_quality import identity_columns
    keys = identity_columns(df)
    # A bad observation invalidates its entire known poll, not only its row.
    invalid_groups = df.loc[invalid, keys].drop_duplicates()
    if not invalid_groups.empty:
        marked = df[keys].merge(invalid_groups.assign(_bad=True), on=keys, how="left")
        invalid = marked["_bad"].eq(True).to_numpy(dtype=bool)
    q["linhas_excluidas_com_grupo_invalido"] = df.loc[invalid, "linha_csv"].tolist()
    df = df[~invalid].copy()
    df = df.dropna(subset=["intencao_voto_pct", "data"])
    from src.core.poll_quality import validate_identity
    validate_identity(df)
    q["apos_data_corte_ignoradas"] = int((df["data"] > data_corte).sum())
    df = df[df["data"] <= data_corte]
    if df.empty:
        raise ValueError("No poll left after cleaning and cutoff")
    q["periodo"] = [str(df["data"].min()), str(df["data"].max())]
    return df, q


def fatias_validas(df: pd.DataFrame, candidatos_necessarios=("Flavio Bolsonaro", "Lula")) -> pd.DataFrame:
    """
    Converts each poll (instituto, data) to valid-vote shares per canonical candidate.

    Blank/null/undecided rows count in neither numerator nor denominator.
    Candidates not in ``TOKENS`` stay in the denominator (they are real votes)
    but are not reported.
    """
    from src.core.poll_quality import select_scenario, validate_identity
    df = select_scenario(df).copy()
    keys = validate_identity(df)
    diagnostics = []
    keep = []
    for key, group in df.groupby(keys, dropna=False):
        present = set(group["candidato"].map(chave_candidato).dropna())
        canonical = group["candidato"].map(chave_candidato).dropna()
        if canonical.duplicated().any():
            raise ValueError(f"Duplicate canonical candidate in poll {key}")
        missing = set(candidatos_necessarios) - present
        if missing:
            diagnostics.append({"pesquisa": str(key), "faltam": sorted(missing),
                                "linhas": group.get("linha_csv", pd.Series(dtype=int)).tolist()})
        else:
            keep.extend(group.index)
    df = df.loc[keep]
    if df.empty:
        out = pd.DataFrame(columns=list(dict.fromkeys(keys + ["instituto", "data"] + list(candidatos_necessarios))))
        out.attrs["pesquisas_excluidas"] = diagnostics
        return out
    df["chave"] = df["candidato"].map(chave_candidato)
    df["excluir"] = df["candidato"].map(
        lambda n: any(t in normalizar(n) for t in EXCLUIR_DA_BASE)
    )
    df = df[~df["excluir"]]
    wide = df.pivot(index=list(dict.fromkeys(keys + ["instituto", "data"])), columns="candidato",
                          values="intencao_voto_pct")
    total = wide.sum(axis=1)
    wide = wide.loc[total > 0]
    total = total.loc[total > 0]
    if wide.empty:
        out = pd.DataFrame(columns=list(dict.fromkeys(keys + ["instituto", "data"] + list(candidatos_necessarios))))
        out.attrs["pesquisas_excluidas"] = diagnostics
        return out
    shares = wide.div(total, axis=0) * 100.0
    cols = {}
    for nome in shares.columns:
        chave = chave_candidato(nome)
        if chave is not None:
            cols[chave] = (cols[chave].combine_first(shares[nome])
                           if chave in cols else shares[nome])
    out = pd.DataFrame(cols).reset_index()
    out.attrs["pesquisas_excluidas"] = diagnostics
    return out


def media_ponderada(valores: pd.Series, datas: pd.Series, ref: date, tau: float) -> float:
    """Exponential-decay weighted mean ignoring NaN. ``tau <= 0`` gives a simple mean."""
    from src.core.poll_quality import parse_date
    parsed = datas.map(parse_date)
    if parsed.map(lambda d: d is None or pd.isna(d) or d > ref).any():
        raise ValueError("Invalid/missing/future weighting date")
    m = valores.notna()
    if not m.any():
        return float("nan")
    if tau <= 0:
        return float(valores[m].mean())
    dias = np.array([max(0, (ref - d).days) for d in datas[m]])
    w = np.exp(-dias / tau)
    return float(np.average(valores[m], weights=w))


def comparar(shares: pd.DataFrame, ref: date, tau: float) -> dict:
    """Poll average, result and error (poll minus result, pp) per candidate."""
    real = resultado_validos()
    out = {}
    for chave, alvo in real.items():
        if chave not in shares.columns:
            continue
        prev = media_ponderada(shares[chave], shares["data"], ref, tau)
        out[chave] = {"previsto": round(prev, 2), "resultado": round(alvo, 2),
                      "erro_pp": round(prev - alvo, 2)}
    return out


def fatia_dois_candidatos(shares: pd.DataFrame, ref: date, tau: float,
                          dias_janela: int | None = None) -> float:
    """Weighted Flavio/(Flavio+Lula) share (percent) across polls, optional window."""
    if not {"Flavio Bolsonaro", "Lula"} <= set(shares.columns):
        return float("nan")
    s = shares.dropna(subset=["Flavio Bolsonaro", "Lula"])
    if dias_janela is not None:
        s = s[[(ref - d).days <= dias_janela for d in s["data"]]]
    if s.empty:
        return float("nan")
    f2 = s["Flavio Bolsonaro"] / (s["Flavio Bolsonaro"] + s["Lula"]) * 100.0
    return media_ponderada(f2.reset_index(drop=True), s["data"].reset_index(drop=True), ref, tau)


def calibrar(shares: pd.DataFrame, ref: date, tau: float) -> dict:
    """
    Two-party-share error by averaging window and the suggested bias.

    The suggested bias is ``result - poll average`` for the tau-weighted window,
    in pp toward Flavio Bolsonaro (positive means polls under-measured him).
    """
    real = resultado_validos()
    f2_real = real["Flavio Bolsonaro"] / (real["Flavio Bolsonaro"] + real["Lula"]) * 100.0
    janelas = {
        f"tau_{tau:g}": fatia_dois_candidatos(shares, ref, tau),
        "ultimos_14_dias": fatia_dois_candidatos(shares, ref, 0, 14),
        "ultimos_7_dias": fatia_dois_candidatos(shares, ref, 0, 7),
        "media_simples": fatia_dois_candidatos(shares, ref, 0),
    }
    erros = {k: {"previsto": round(v, 2), "erro_pp": round(v - f2_real, 2)}
             for k, v in janelas.items()}
    return {
        "fatia_flavio_resultado": round(f2_real, 2),
        "janelas": erros,
        "vies_sugerido_pp_flavio": round(f2_real - janelas[f"tau_{tau:g}"], 2),
    }


def imprimir(q: dict, por_cand: dict, cal: dict) -> None:
    """Prints data quality, per-candidate errors and the calibration summary."""
    print("=" * 66)
    print("  FIRST-ROUND RETROSPECTIVE (valid votes)")
    print("=" * 66)
    print(f"  Rows read: {q['linhas_lidas']}  dropped (value/date): "
          f"{q['descartadas_valor_ou_data']}  after cutoff (ignored): "
          f"{q['apos_data_corte_ignoradas']}")
    print(f"  Poll period used: {q['periodo'][0]} to {q['periodo'][1]}")
    print(f"\n  {'Candidate':<18}{'Polls':>8}{'Result':>9}{'Error pp':>10}")
    for c, v in por_cand.items():
        print(f"  {c:<18}{v['previsto']:>8.2f}{v['resultado']:>9.2f}{v['erro_pp']:>+10.2f}")
    print(f"\n  Two-party share of Flavio (result): {cal['fatia_flavio_resultado']:.2f}%")
    for k, v in cal["janelas"].items():
        print(f"    {k:<18} poll {v['previsto']:6.2f}%   error {v['erro_pp']:+.2f} pp")
    print(f"\n  Suggested bias toward Flavio: {cal['vies_sugerido_pp_flavio']:+.2f} pp")
    print("  Single election: use as a sensitivity row, not as a fixed correction.")
    print("=" * 66)


def main(argv=None) -> dict:
    """CLI entry point. Returns the calibration dictionary."""
    p = argparse.ArgumentParser(description="First-round retrospective")
    p.add_argument("--csv", default="data/pesquisas.csv")
    p.add_argument("--data-corte", default="2026-10-03")
    p.add_argument("--cenario", help="Select one scenario from the CSV")
    p.add_argument("--candidato-necessario", action="append", dest="necessarios",
                   help="Required canonical candidate for this scenario (repeatable)")
    p.add_argument("--tau", type=float, default=7.0)
    p.add_argument("--saida", default="outputs/calibracao_1t.json")
    a = p.parse_args(argv)
    corte = date.fromisoformat(a.data_corte)

    df, q = carregar_pesquisas_1t(Path(a.csv), corte, cenario=a.cenario)
    required = tuple(a.necessarios or ("Flavio Bolsonaro", "Lula"))
    shares = fatias_validas(df, required)
    q["candidatos_necessarios"] = list(required)
    q["pesquisas_excluidas"] = shares.attrs.get("pesquisas_excluidas", [])
    por_cand = comparar(shares, corte, a.tau)
    cal = calibrar(shares, corte, a.tau)
    imprimir(q, por_cand, cal)

    saida = {"executado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "data_corte": a.data_corte, "tau": a.tau, "qualidade": q,
             "por_candidato": por_cand, "calibracao": cal}
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(a.saida).write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    return saida


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)
