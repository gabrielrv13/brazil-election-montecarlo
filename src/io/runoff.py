"""
Runoff I/O: poll loading and the JSON summary consumed by the publication gate.

``carregar_runoff`` applies the same validation as the first-round loader
(schema, scenario, dates not after the reference date, poll identity) and
keeps only polls inside the runoff window. ``salvar_resumo`` writes the
schema-2 summary described in ``docs/contrato_resumo_publicacao.md``.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path

import pandas as pd

from src.core.config import RunoffConfig
from src.core.runoff import AgregacaoRunoff, agregar_fatia, resolver_vies


def carregar_runoff(config: RunoffConfig) -> AgregacaoRunoff:
    """Load, validate and aggregate runoff polls for ``config``.

    Raises:
        FileNotFoundError: Missing CSV.
        ValueError: Invalid schema, dates after the reference date, duplicate
            or incomplete polls, or no poll left in the runoff window.
    """
    from src.core.poll_quality import parse_date, select_scenario, validate_dates
    from src.io.loader import _validate_schema

    if not config.csv_path.exists():
        raise FileNotFoundError(f"Runoff poll CSV not found: {config.csv_path}")
    df = pd.read_csv(config.csv_path, dtype={"pesquisa_id": str, "cenario": str})
    referencia = config.as_of or date.today()
    df = select_scenario(df, None)
    _validate_schema(df, config.csv_path)
    df = validate_dates(df, referencia, str(config.csv_path))
    inicio = config.janela_inicio
    df = df[df["data"].map(parse_date) >= inicio].copy()
    if df.empty:
        raise ValueError(
            f"No runoff polls on or after {inicio} up to {referencia}; "
            "pass data_min for pre-first-round matchups."
        )
    ag = agregar_fatia(df, referencia, tau=config.tau_dias,
                       efeitos_instituto=config.efeitos_instituto)
    ag.info["janela"] = [inicio.isoformat(), referencia.isoformat()]
    return ag


def salvar_resumo(
    path: Path,
    df: pd.DataFrame,
    cand_a: str,
    cand_b: str,
    fatia_a: float,
    params: dict,
    info: dict,
    sensibilidade: pd.DataFrame,
) -> Path:
    """
    Write the JSON summary of a runoff run for the publication step.

    Args:
        path: Destination file.
        df: Runoff draws with ``df.attrs["calibracao"]`` (``simular_runoff``
            or the legacy ``simular_calibrado``).
        cand_a: Leading candidate (share ``fatia_a``).
        cand_b: Opponent.
        fatia_a: Aggregated two-party share of ``cand_a`` (percent).
        params: Run parameters (sd_fatia_pp, vies_pp_a, tau, data_min, ...).
        info: Aggregation info (n_pesquisas, n_efetivo, institutos, soma_media).
        sensibilidade: P(A wins) table by bias and sd.

    Returns:
        The path written.
    """
    q05, q95 = df["voto_a"].quantile([0.05, 0.95])
    meta = df.attrs.get("calibracao")
    if meta is None or any(meta[k] != v for k, v in {
        "cand_a": cand_a, "cand_b": cand_b, "fatia_agregada_a": float(fatia_a),
        "vies_pp_a": float(params["vies_pp_a"]),
    }.items()):
        raise ValueError("calibracao: summary must match the calibrated draws")
    params = dict(params)
    params.setdefault("vies_candidato", cand_a)
    params.setdefault("vies_pp", params["vies_pp_a"])
    if resolver_vies(cand_a, cand_b, params["vies_candidato"], params["vies_pp"]) != params["vies_pp_a"]:
        raise ValueError("parametros.vies_candidato: inconsistent bias")
    resumo = {
        "schema_version": 2,
        "fatia_agregada_a": round(float(fatia_a), 3),
        "fatia_central_a": round(meta["fatia_central_a"], 3),
        "fatia_simulada_media_a": round(float(df["voto_a"].mean()), 3),
        "transformacoes": {k: meta[k] for k in ("usar_teto", "rej_a", "rej_b")},
        "executado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cand_a": cand_a,
        "cand_b": cand_b,
        "fatia_a": round(float(fatia_a), 3),
        "p_vitoria_a": round(float((df["vencedor"] == cand_a).mean() * 100), 2),
        "p_vitoria_b": round(float((df["vencedor"] == cand_b).mean() * 100), 2),
        "fatia_a_ic90": [round(float(q05), 2), round(float(q95), 2)],
        "margem_mediana_pp": round(float(df["diferenca"].median()), 2),
        "margem_votos_mediana": int(df["margem_votos"].median()),
        "parametros": params,
        "pesquisas": {
            "n": info["n_pesquisas"],
            "n_efetivo": round(info["n_efetivo"], 1),
            "n_institutos": len(info["institutos"]),
            "soma_media": round(info["soma_media"], 1),
        },
        "sensibilidade": {
            str(v): {str(sd): round(float(x), 1) for sd, x in row.items()}
            for v, row in sensibilidade.iterrows()
        },
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
