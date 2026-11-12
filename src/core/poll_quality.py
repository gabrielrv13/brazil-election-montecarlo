"""Shared conservative poll date and identity contracts."""
from datetime import date, datetime
import re
import pandas as pd


def parse_date(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date) and not pd.isna(value):
        return value
    if isinstance(value, str):
        for pattern, fmt in [(r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
                             (r"\d{2}/\d{2}/\d{4}", "%d/%m/%Y")]:
            if re.fullmatch(pattern, value):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    pass
    return None


def validate_dates(df, ref, source):
    if "data" not in df:
        raise ValueError(f"{source}: missing data column")
    parsed = df["data"].map(parse_date)
    bad = parsed.map(lambda d: d is None or pd.isna(d) or d > ref)
    if bad.any():
        details = [f"line {i + 2}: data={df.loc[i, 'data']!r}" for i in df.index[bad]]
        raise ValueError(f"{source}: invalid/missing/future dates: " + "; ".join(details))
    out = df.copy()
    out["data"] = parsed
    return out


def identity_columns(df):
    if "pesquisa_id" in df:
        if df["pesquisa_id"].isna().any() or df["pesquisa_id"].astype(str).str.strip().eq("").any():
            raise ValueError("Missing pesquisa_id")
        return ["pesquisa_id"] + (["cenario"] if "cenario" in df else [])
    return [c for c in ("instituto", "data", "cenario") if c in df]


def validate_identity(df):
    keys = identity_columns(df)
    if "cenario" in df and (df["cenario"].isna().any() or
                            df["cenario"].astype(str).str.strip().eq("").any()):
        raise ValueError("Missing cenario")
    if "pesquisa_id" not in df:
        import logging
        logging.getLogger(__name__).warning(
            "Legacy poll identity inferred from %s; provide pesquisa_id for distinct observations", keys)
    if "instituto" in df and df["instituto"].isna().any():
        raise ValueError("Missing instituto")
    if df["candidato"].isna().any() or df["candidato"].astype(str).str.strip().eq("").any():
        raise ValueError("Missing candidato")
    if keys and df.duplicated(keys + ["candidato"]).any():
        raise ValueError("Ambiguous/duplicate poll observations; supply distinct pesquisa_id values")
    if "pesquisa_id" in df:
        for _, g in df.groupby(keys, dropna=False):
            if any(g[c].nunique(dropna=False) != 1 for c in ("data", "instituto") if c in g):
                raise ValueError("Inconsistent metadata for pesquisa_id")
    return keys


def select_scenario(df, scenario=None):
    """Select one declared scenario; never pool different candidate universes."""
    if "cenario" not in df:
        if scenario is not None:
            raise ValueError("Cannot select scenario: missing cenario column")
        return df
    if df["cenario"].isna().any() or df["cenario"].astype(str).str.strip().eq("").any():
        raise ValueError("Missing cenario")
    if scenario is not None:
        selected = df[df["cenario"] == scenario].copy()
        if selected.empty:
            raise ValueError(f"Unknown cenario: {scenario}")
        return selected
    if df["cenario"].nunique() != 1:
        raise ValueError("Select one cenario before calculating estimates")
    return df
