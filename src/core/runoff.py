"""
Second round on the core engine.

Two entry points:

* **Standalone runoff** (finalists known): each poll is reduced to the
  two-party share ``A / (A + B)``, aggregated with the v3 aggregator (house
  effects, detrended outliers, sd of the weighted mean) and simulated with
  the same two-level error as the first round (common election error with
  heavy tails + drift, then polling-average noise).
* **Dynamic runoff** (before the first round): for every first-round draw
  the actual top two face each other, the other candidates' votes are
  transferred with rejection-weighted proportions, and only draws in which a
  runoff happens are kept. This feeds ``SimulationResult.df2`` / ``p2v``.

Pure functions: no I/O, no global RNG. Absolute votes use the shared
accounting (``contabilizar_votos``) with the runoff blank/null prior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import math

import numpy as np
import pandas as pd

from src.core.aggregation import Z_MARGEM_ERRO, agregar_pesquisas
from src.core.events import eventos_primeiro_turno, probabilidades_vitoria_2t
from src.core.simulation import (
    INVALIDOS_2T_MU,
    INVALIDOS_2T_SIGMA,
    amostrar_proporcoes,
    aplicar_teto_rejeicao,
    contabilizar_votos,
    dividir_validos,
)

# Runoff abstention prior (TSE: 2018 21.3%, 2022 20.6%, 2026 about 19.2%).
ABSTENCAO_2T_MU: float = 0.22
ABSTENCAO_2T_SIGMA: float = 0.03

# Dynamic runoff: Dirichlet transfer of eliminated candidates' votes,
# [space_A, space_B, blank/null] with this total concentration and blank share.
CONCENTRACAO_TRANSFERENCIA: float = 100.0
FRACAO_NULO_TRANSFERENCIA: float = 0.20


# ─── Standalone runoff ────────────────────────────────────────────────────────

@dataclass
class AgregacaoRunoff:
    """Two-party-share aggregate of runoff polls (``cand_a`` leads)."""

    cand_a: str
    cand_b: str
    fatia_a: float          # aggregated share of cand_a, pp (>= 50)
    sd_media: float         # sd of that aggregate, pp
    rej_a: float = 0.0
    rej_b: float = 0.0
    info: dict = field(default_factory=dict)


def fatias_por_pesquisa(df: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    """One row per poll with the two-party share of the first candidate.

    Raises ``ValueError`` when the file does not hold exactly two candidates,
    when a poll repeats a candidate (the legacy ``pivot_table(mean)`` averaged
    duplicates silently, audit A14) or when a poll lists only one finalist.
    """
    cands = sorted(df["candidato"].unique())
    if len(cands) != 2:
        raise ValueError(f"Runoff polls must have exactly 2 candidates; found {cands}")
    dup = df.groupby([*chaves, "candidato"], dropna=False).size()
    if (dup > 1).any():
        raise ValueError(f"Duplicated candidate rows in runoff polls: {dup[dup > 1].index.tolist()[:5]}")
    wide = df.pivot(index=chaves, columns="candidato", values="intencao_voto_pct")
    incompletas = wide.index[wide.isna().any(axis=1)].tolist()
    if incompletas:
        raise ValueError(f"Incomplete runoff polls (one finalist missing): {incompletas[:5]}")
    moe = df.pivot(index=chaves, columns="candidato", values="desvio_padrao_pct").mean(axis=1)
    soma = wide[cands[0]] + wide[cands[1]]
    if (soma <= 0).any():
        raise ValueError("Runoff poll with zero support for both finalists")
    q = wide[cands[0]] / soma
    out = wide.reset_index()
    # With a pesquisa_id key the pivot drops the poll metadata; carry it over
    # (validate_identity guarantees one date and institute per poll).
    meta = [c for c in ("instituto", "data") if c in df.columns and c not in chaves]
    if meta:
        primeiro = df.groupby(chaves, sort=False)[meta].first().reset_index()
        out = out.merge(primeiro, on=chaves, how="left", validate="one_to_one")
    out["soma"] = soma.to_numpy()
    out["fatia"] = (q * 100.0).to_numpy()
    # SE of A/(A+B) from the poll's margin of error at 50%: the share is
    # measured on the s = (A+B)/100 fraction of respondents.
    out["desvio_fatia"] = (moe * 2.0 * np.sqrt(q * (1 - q)) / np.sqrt(soma / 100.0)).to_numpy()
    out.attrs["candidatos"] = cands
    return out


def agregar_fatia(
    df: pd.DataFrame,
    data_referencia: date,
    tau: float = 7.0,
    efeitos_instituto: bool = True,
) -> AgregacaoRunoff:
    """Aggregate runoff polls on the two-party share (already validated rows)."""
    from src.core.poll_quality import validate_identity

    chaves = validate_identity(df) or ["instituto", "data"]
    por_pesquisa = fatias_por_pesquisa(df, chaves)
    c0, c1 = por_pesquisa.attrs["candidatos"]
    serie = pd.DataFrame({
        "candidato": "fatia",
        "intencao_voto_pct": por_pesquisa["fatia"],
        "desvio_padrao_pct": por_pesquisa["desvio_fatia"],
        "instituto": por_pesquisa["instituto"] if "instituto" in por_pesquisa else "Unknown",
        "data": por_pesquisa["data"],
    })
    ag = agregar_pesquisas(serie, data_referencia, tau=tau, efeitos_instituto=efeitos_instituto)["fatia"]
    fatia0 = ag.voto
    cand_a, cand_b, fatia_a = (c0, c1, fatia0) if fatia0 >= 50 else (c1, c0, 100.0 - fatia0)

    rej = {}
    if "rejeicao_pct" in df:
        for c in (c0, c1):
            r = df.loc[df["candidato"] == c, "rejeicao_pct"].to_numpy(dtype=float)
            rej[c] = float(r[r > 0].mean()) if (r > 0).any() else 0.0
    info = {
        "n_pesquisas": int(len(por_pesquisa)),
        "n_efetivo": ag.info["n_efetivo"],
        "n_validas": ag.info["n_validas"],
        "institutos": sorted(serie["instituto"].astype(str).unique()),
        "soma_media": float(por_pesquisa["soma"].mean()),
        "soma_min": float(por_pesquisa["soma"].min()),
        "soma_max": float(por_pesquisa["soma"].max()),
        "fatia_bruta_a": ag.info["media_bruta"] if cand_a == c0 else 100 - ag.info["media_bruta"],
        "efeitos_instituto": ag.info["efeitos_instituto"],
        "outliers": ag.info["outliers"],
        "chaves_pesquisa": chaves,
    }
    return AgregacaoRunoff(cand_a, cand_b, fatia_a, ag.sd_media,
                           rej.get(cand_a, 0.0), rej.get(cand_b, 0.0), info)


def resolver_vies(cand_a: str, cand_b: str, candidato: str, vies_pp: float) -> float:
    """Bias in ``cand_a`` coordinates for a shift that favours ``candidato``."""
    if candidato not in (cand_a, cand_b):
        raise ValueError("vies_candidato: must identify one of the two candidates")
    if not np.isfinite(vies_pp):
        raise ValueError("vies_pp: must be finite")
    return float(vies_pp if candidato == cand_a else -vies_pp)


def simular_runoff(
    ag: AgregacaoRunoff,
    n_sim: int,
    rng: np.random.Generator,
    sd_comum_pp: float,
    gl_comum: float,
    sd_deriva_pp: float,
    vies_pp_a: float = 0.0,
    usar_teto: bool = False,
) -> pd.DataFrame:
    """Draw the runoff: two-party share of ``cand_a`` plus absolute votes.

    The columns match the legacy ``simulation_2turno.simular`` output, so the
    summary, chart and publication gate work unchanged; ``df.attrs
    ["calibracao"]`` records the aggregate, the centre after the bias shift
    and the ceiling settings for ``salvar_resumo``.
    """
    centro = ag.fatia_a + vies_pp_a
    if not (np.isfinite(centro) and 0.0 < centro < 100.0):
        raise ValueError(f"Shifted share out of range: {centro}")
    proporcoes, _ = amostrar_proporcoes(
        np.array([centro, 100.0 - centro]), ag.sd_media, n_sim, rng,
        sd_comum_pp=sd_comum_pp, gl_comum=gl_comum, sd_deriva_pp=sd_deriva_pp,
    )
    votos = proporcoes * 100.0
    if usar_teto:
        votos, _ = aplicar_teto_rejeicao(votos, np.array([ag.rej_a, ag.rej_b]), [ag.cand_a, ag.cand_b])
    voto_a, voto_b = votos[:, 0], votos[:, 1]

    contagem = contabilizar_votos(
        rng, n_sim, ABSTENCAO_2T_MU, ABSTENCAO_2T_SIGMA,
        invalidos_mu=INVALIDOS_2T_MU, invalidos_sigma=INVALIDOS_2T_SIGMA,
    )
    absolutos = dividir_validos(contagem["votos_validos"], votos)
    df = pd.DataFrame({
        "voto_a": voto_a,
        "voto_b": voto_b,
        "vencedor": np.where(voto_a > voto_b, ag.cand_a, ag.cand_b),
        "diferenca": np.abs(voto_a - voto_b),
        "abstencao_pct": contagem["abstencao"] * 100,
        "comparecimento": contagem["comparecimento"],
        "invalidos_pct": contagem["invalidos_frac"] * 100,
        "votos_invalidos": contagem["votos_invalidos"],
        "votos_validos": contagem["votos_validos"],
        "votos_a_abs": absolutos[:, 0],
        "votos_b_abs": absolutos[:, 1],
        "margem_votos": np.abs(absolutos[:, 0] - absolutos[:, 1]),
    })
    df.attrs["calibracao"] = {
        "cand_a": ag.cand_a, "cand_b": ag.cand_b,
        "fatia_agregada_a": float(ag.fatia_a), "fatia_central_a": float(centro),
        "vies_pp_a": float(vies_pp_a), "usar_teto": bool(usar_teto),
        "rej_a": float(ag.rej_a if usar_teto else 0.0),
        "rej_b": float(ag.rej_b if usar_teto else 0.0),
    }
    return df


def tabela_sensibilidade_runoff(
    ag: AgregacaoRunoff,
    sds_comum_pp: tuple = (0.8, 1.5, 2.5, 3.0, 3.5),
    vieses_pp: tuple = (-1.0, 0.0, 1.0, 2.0, 3.0),
    n_sim: int = 40_000,
    seed: int = 42,
    gl_comum: float = 5.0,
    sd_deriva_pp: float = 0.0,
) -> pd.DataFrame:
    """P(``cand_a`` wins), %, by bias shift (rows) and common-error sd (columns)."""
    rng = np.random.default_rng(seed)
    out = pd.DataFrame(index=list(vieses_pp), columns=list(sds_comum_pp), dtype=float)
    for vies in vieses_pp:
        centro = ag.fatia_a + vies
        for sd in sds_comum_pp:
            pr, _ = amostrar_proporcoes(np.array([centro, 100.0 - centro]), ag.sd_media, n_sim,
                                        rng, sd_comum_pp=sd, gl_comum=gl_comum,
                                        sd_deriva_pp=sd_deriva_pp)
            out.loc[vies, sd] = float((pr[:, 0] > 0.5).mean() * 100.0)
    out.index.name = "vies_pp_a"
    return out


# ─── Dynamic runoff from first-round draws ────────────────────────────────────

def simular_segundo_turno_dinamico(
    validos_final: np.ndarray,
    candidatos_validos: list[str],
    rejeicao_validos: np.ndarray,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, dict]:
    """Runoff between the actual top two of every first-round draw.

    The eliminated candidates' votes go to the finalists through
    ``Dirichlet([C(1-f) w_A, C(1-f) w_B, C f])`` with ``w`` proportional to
    each finalist's electoral space ``100 - rejection`` (equal without
    rejection data), ``C = CONCENTRACAO_TRANSFERENCIA`` and
    ``f = FRACAO_NULO_TRANSFERENCIA``. No rejection ceiling is applied in the
    binary race (as in the standalone default). All draws are sampled first;
    only draws with a runoff are returned (event contract v2).

    Returns:
        ``(df2, info_matchups)``. ``df2`` is empty when fewer than two
        candidates exist or an exact tie for second place leaves the
        finalists undefined.
    """
    v = np.asarray(validos_final, dtype=float)
    n, k = v.shape
    if k < 2:
        return pd.DataFrame(), {}
    rej = np.asarray(rejeicao_validos, dtype=float)

    top2 = np.sort(np.argsort(v, axis=1)[:, -2:], axis=1)
    ia, ib = top2[:, 0], top2[:, 1]
    linhas = np.arange(n)
    v_a, v_b = v[linhas, ia], v[linhas, ib]
    outros = 100.0 - v_a - v_b

    espaco = np.maximum(100.0 - rej, 1.0)
    w_a = espaco[ia] / (espaco[ia] + espaco[ib])
    c_fin = CONCENTRACAO_TRANSFERENCIA * (1.0 - FRACAO_NULO_TRANSFERENCIA)
    alphas = np.column_stack([c_fin * w_a, c_fin * (1 - w_a),
                              np.full(n, CONCENTRACAO_TRANSFERENCIA * FRACAO_NULO_TRANSFERENCIA)])
    g = rng.gamma(alphas)
    transf = g / g.sum(axis=1, keepdims=True)
    a2 = v_a + outros * transf[:, 0]
    b2 = v_b + outros * transf[:, 1]
    voto_a = a2 / (a2 + b2) * 100.0
    voto_b = 100.0 - voto_a

    contagem = contabilizar_votos(
        rng, n, ABSTENCAO_2T_MU, ABSTENCAO_2T_SIGMA,
        invalidos_mu=INVALIDOS_2T_MU, invalidos_sigma=INVALIDOS_2T_SIGMA,
    )
    absolutos = dividir_validos(contagem["votos_validos"], np.column_stack([voto_a, voto_b]))
    nomes = np.array(candidatos_validos, dtype=object)
    fa, fb = nomes[ia], nomes[ib]
    df = pd.DataFrame({
        "matchup": [f"{a} vs {b}" for a, b in zip(fa, fb)],
        "finalista_a": fa, "finalista_b": fb,
        "voto_a": voto_a, "voto_b": voto_b,
        "vencedor_2T": np.where(voto_a > voto_b, fa, fb),
        "diferenca": np.abs(voto_a - voto_b),
        "abstencao_2t_pct": contagem["abstencao"] * 100,
        "comparecimento_2t": contagem["comparecimento"],
        "invalidos_2t_pct": contagem["invalidos_frac"] * 100,
        "votos_validos_2t": contagem["votos_validos"],
        "votos_a_abs": absolutos[:, 0], "votos_b_abs": absolutos[:, 1],
        "margem_votos": np.abs(absolutos[:, 0] - absolutos[:, 1]),
    })

    eventos = eventos_primeiro_turno(v)
    df["tem_2turno"] = eventos["segundo_turno"]
    df["event_contract_version"] = 2
    df = df.loc[df["tem_2turno"]].copy()
    creditos = eventos["classificacao_2t"]
    if ((creditos > 0) & (creditos < 1)).any():
        # An exact tie for second place: the finalists are not defined.
        return pd.DataFrame(), {}
    if df.empty:
        return df, {}
    info = {}
    for matchup, grupo in df.groupby("matchup", sort=True):
        a, b = grupo.iloc[0][["finalista_a", "finalista_b"]]
        pa = probabilidades_vitoria_2t(grupo, [a, b])[a] * 100
        info[matchup] = dict(
            cand_a=a, cand_b=b, n_sims=int(len(grupo)),
            prob_matchup=len(grupo) / len(df) * 100, prob_a=pa, prob_b=100 - pa,
            rej_a=float(rej[candidatos_validos.index(a)]),
            rej_b=float(rej[candidatos_validos.index(b)]),
        )
    return df, info


def sd_deriva_runoff(sd_30d_pp: float, data_2t: date, data_referencia: date) -> float:
    """Drift until runoff day, ``sd_30d * sqrt(days / 30)`` (0 after it)."""
    dias = (data_2t - data_referencia).days
    return 0.0 if dias <= 0 else float(sd_30d_pp * math.sqrt(dias / 30.0))


__all__ = [
    "ABSTENCAO_2T_MU", "ABSTENCAO_2T_SIGMA", "AgregacaoRunoff", "Z_MARGEM_ERRO",
    "agregar_fatia", "fatias_por_pesquisa", "resolver_vies", "sd_deriva_runoff",
    "simular_runoff", "simular_segundo_turno_dinamico", "tabela_sensibilidade_runoff",
]
