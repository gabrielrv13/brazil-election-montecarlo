"""
brazil-election-montecarlo — Standalone Second Round Simulation (v2.7)
=======================================================================
Dedicated simulation for the presidential runoff after the two finalists
are known from the first round result.

Rationale:
    Once the finalists are determined, running 40,000 first-round simulations
    to reach the second round is unnecessary. This script simulates the runoff
    directly with its own poll data, capturing second-round dynamics that differ
    from first-round surveys (smaller undecided pool, completed vote transfer,
    potential rejection shifts).

Usage:
    python src/simulation_2turno.py

CSV format (data/pesquisas_2turno.csv):
    candidato,intencao_voto_pct,rejeicao_pct,desvio_padrao_pct,instituto,data
    Lula,54.0,42.0,2.0,Datafolha,2026-10-08
    Lula,53.0,43.0,2.0,Quaest,2026-10-09
    Flávio Bolsonaro,46.0,48.0,2.0,Datafolha,2026-10-08
    Flávio Bolsonaro,47.0,47.0,2.0,Quaest,2026-10-09

    - Exactly two candidates expected (no "Outros" or "Brancos/Nulos" rows).
    - intencao_voto_pct values need not sum to 100; the gap is treated as
      residual (undecided + blank/null) and redistributed before simulation.
    - Aggregation, temporal weighting, and outlier detection come from
      src.core.aggregation. The canonical runoff is ``python -m src runoff``
      (src.core.runoff); this script keeps the v2.10 calibrated method.

Outputs:
    outputs/resultados_2turno_standalone.csv
    outputs/simulacao_2turno.png

License: MIT
"""

import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt  # noqa: F401  (tests patch s2.plt.savefig)
from pathlib import Path
from datetime import date

# Script mode (python src/simulation_2turno.py): put this checkout's root
# first so ``src`` is this code. The module no longer imports simulation_v2
# (and with it PyMC): everything comes from the core.
_RAIZ = str(Path(__file__).resolve().parent.parent)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from src.core.aggregation import (  # noqa: E402
    agregar_pesquisas_candidato,
    calcular_peso_temporal,
    detectar_outliers,
)
from src.core.runoff import (  # noqa: E402
    ABSTENCAO_2T_MU,
    ABSTENCAO_2T_SIGMA,
    resolver_vies,
)
from src.core.simulation import (  # noqa: E402
    ELEITORADO,
    INVALIDOS_2T_MU,
    INVALIDOS_2T_SIGMA,
    contabilizar_votos,
    dividir_validos,
)
from src.io.runoff import salvar_resumo  # noqa: E402,F401  (re-exported legacy API)

# ─── CONFIG ───────────────────────────────────────────────────────────────────

OUTPUT_DIR    = Path("outputs")  # created on first write, not on import

DATA_ELEICAO  = date(2026, 10, 4)
DATA_2T       = date(2026, 10, 25)   # Historical pattern: runoff ~3 weeks after 1st round
N_SIM         = 40_000
DESVIO_BASE   = 2.0                  # Overridden by aggregated value from CSV

SEED_PADRAO   = 42                # seeded in main(), not on import


# ─── DATA LOADING ─────────────────────────────────────────────────────────────

def carregar_pesquisas_2t(csv_path=None):
    """
    Loads and aggregates second-round poll data.

    Reuses agregar_pesquisas_candidato() from src.core.aggregation for temporal
    weighting and outlier detection. Expects exactly two candidates.

    Args:
        csv_path: Path to CSV (str or Path). Defaults to data/pesquisas_2turno.csv.

    Returns:
        tuple: (cand_a, cand_b, voto_a, voto_b, rej_a, rej_b, desvio, residual)
            - cand_a / cand_b: Candidate names (sorted by descending aggregated vote)
            - voto_a / voto_b: Aggregated vote intentions (%)
            - rej_a / rej_b: Aggregated rejection rates (%)
            - desvio: Combined standard deviation (%)
            - residual: 100 - (voto_a + voto_b), represents undecided + blank/null

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If the CSV does not contain exactly two distinct candidates.
    """
    csv_path = Path(csv_path) if csv_path else Path("data/pesquisas_2turno.csv")

    if not csv_path.exists():
        raise FileNotFoundError(
            f"File not found: {csv_path}\n"
            "Create data/pesquisas_2turno.csv with second-round poll data.\n"
            "See ROADMAP.md (Issue #9) for the expected CSV format."
        )

    df = pd.read_csv(csv_path)

    required = {"candidato", "intencao_voto_pct", "desvio_padrao_pct"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date

    candidatos_unicos = df["candidato"].unique()
    if len(candidatos_unicos) != 2:
        raise ValueError(
            f"Expected exactly 2 candidates; found {len(candidatos_unicos)}: "
            f"{list(candidatos_unicos)}\n"
            "Remove 'Outros' and 'Brancos/Nulos' rows — residual is computed automatically."
        )

    data_ref = date.today()
    resultados = {}

    print("\n" + "=" * 70)
    print("  SECOND ROUND POLL AGGREGATION")
    print("=" * 70)

    for cand in candidatos_unicos:
        df_cand = df[df["candidato"] == cand].copy()
        voto, rej, desv, info = agregar_pesquisas_candidato(df_cand, data_ref)

        resultados[cand] = {
            "voto": voto,
            "rej": rej,
            "desv": desv,
            "info": info,
        }

        n = info["n_pesquisas"]
        print(f"\nCandidate: {cand}")
        print(f"   Polls aggregated: {n}")
        print(f"   Valid polls: {info['n_validas']}")
        if "institutos" in info and n > 1:
            print(f"   Sources: {', '.join(info['institutos'])}")
        print(f"   Aggregated vote: {voto:.2f}%")
        if rej > 0:
            print(f"   Aggregated rejection: {rej:.2f}%")
        if n > 1:
            print(f"   Base std dev: {info['desvio_medio']:.2f}%")
            print(f"   Inter-institute std dev: {info['desvio_entre']:.2f}%")
        print(f"   Combined std dev: {desv:.2f}%")
        if info.get("outliers"):
            print(f"   WARNING: {len(info['outliers'])} outlier(s) excluded:")
            for o in info["outliers"]:
                print(f"      - {o['instituto']}: {o['valor']:.2f}%")

    print("=" * 70)

    # Sort candidates by descending vote share (leader first)
    cands_sorted = sorted(resultados.keys(), key=lambda c: resultados[c]["voto"], reverse=True)
    cand_a, cand_b = cands_sorted

    voto_a = resultados[cand_a]["voto"]
    voto_b = resultados[cand_b]["voto"]
    rej_a  = resultados[cand_a]["rej"]
    rej_b  = resultados[cand_b]["rej"]
    desvio = float(np.mean([resultados[c]["desv"] for c in candidatos_unicos]))

    # Residual: undecided + blank/null implicit in the poll gap
    residual = max(0.0, 100.0 - voto_a - voto_b)

    print(f"\nResidual (undecided + blank/null): {residual:.2f}%")
    print(f"Combined std dev: {desvio:.2f}%")
    print(f"Electorate: {ELEITORADO:,}")

    return cand_a, cand_b, voto_a, voto_b, rej_a, rej_b, desvio, residual


# ─── RESIDUAL REDISTRIBUTION ──────────────────────────────────────────────────

def redistribuir_residual(voto_a, voto_b, rej_a, rej_b, residual, blank_fraction=0.20):
    """
    Distributes the residual (undecided + blank/null) between the two finalists
    and a blank/null pool proportionally to each candidate's available electoral space.

    In second-round polls, intencao_voto_pct values frequently sum to less than 100%
    because a fraction of respondents are undecided or will vote blank/null.
    This function redistributes the residual before Dirichlet parameterization.

    Args:
        voto_a: Aggregated vote intention for candidate A (%)
        voto_b: Aggregated vote intention for candidate B (%)
        rej_a: Rejection rate for candidate A (%)
        rej_b: Rejection rate for candidate B (%)
        residual: Undecided + blank/null gap (100 - voto_a - voto_b) (%)
        blank_fraction: Fraction of residual allocated to blank/null (default: 0.20)

    Returns:
        tuple: (voto_a_adj, voto_b_adj, residual_final)
            - voto_a_adj / voto_b_adj: Adjusted vote intentions after redistribution
            - residual_final: Final blank/null proportion for Dirichlet third category

    Formula:
        weight_i = vote_share_i * max(100 - rejection_i, 0) / 100
        gain_i = (weight_i / sum(weights)) * residual * (1 - blank_fraction)
    """
    if residual <= 0:
        return voto_a, voto_b, 0.0

    espaco_a = max(100.0 - rej_a, 0.0) / 100.0
    espaco_b = max(100.0 - rej_b, 0.0) / 100.0

    peso_a = voto_a * espaco_a
    peso_b = voto_b * espaco_b
    total_peso = peso_a + peso_b

    if total_peso == 0:
        # Fallback: equal split if both candidates have 100% rejection
        prop_a = prop_b = 0.5
    else:
        prop_a = peso_a / total_peso
        prop_b = peso_b / total_peso

    redistribuivel = residual * (1.0 - blank_fraction)
    residual_final = residual * blank_fraction

    voto_a_adj = voto_a + prop_a * redistribuivel
    voto_b_adj = voto_b + prop_b * redistribuivel

    print(f"\n   Residual redistribution (blank_fraction={blank_fraction:.0%}):")
    print(f"   Redistributable to candidates: {redistribuivel:.2f}%")
    print(f"   Allocated to blank/null: {residual_final:.2f}%")
    print(f"   Candidate A gain: +{prop_a * redistribuivel:.2f}pp "
          f"({voto_a:.2f}% → {voto_a_adj:.2f}%)")
    print(f"   Candidate B gain: +{prop_b * redistribuivel:.2f}pp "
          f"({voto_b:.2f}% → {voto_b_adj:.2f}%)")

    return voto_a_adj, voto_b_adj, residual_final


# ─── CALIBRATED RUNOFF (v2.10) ────────────────────────────────────────────────
# Two-party-share aggregation and explicit uncertainty. The legacy path above
# (carregar_pesquisas_2t + simular) is unchanged and remains available via
# --base candidato.

# Effective sd of the two-party share (pp). Phase 3 (src/calibracao.py): the
# election-level error estimated from four final-week cases is 3.4 pp (95%
# profile interval 1.5-9.1) and the shared prior of the first-round engine
# (3.0) scores better out of sample, so the runoff uses the same 3.0 instead
# of the 2.5 derived from the contaminated legacy backtest.
SD_FATIA_PP_PADRAO = 3.0
SD_FATIA_PP_MAX    = 4.9   # Above this, simular() floors the Dirichlet concentration at 100


def sd_fatia_para_desvio(sd_fatia_pp: float) -> float:
    """
    Converts the desired sd of the two-party share into the ``desvio`` argument
    expected by ``simular()``.

    ``simular()`` draws a Dirichlet with total concentration ``10000 / desvio``.
    For a two-way split near 50%, the sd of the share is ``50 / sqrt(alpha0 + 1)``
    percentage points, so ``desvio = 10000 / ((50 / sd) ** 2 - 1)``.

    Args:
        sd_fatia_pp: Target standard deviation of the two-party share (pp).

    Returns:
        Value to pass as ``desvio`` to ``simular()``.

    Raises:
        ValueError: If ``sd_fatia_pp`` is outside (0, SD_FATIA_PP_MAX].
    """
    if not 0.0 < sd_fatia_pp <= SD_FATIA_PP_MAX:
        raise ValueError(
            f"sd_fatia_pp must be in (0, {SD_FATIA_PP_MAX}], got {sd_fatia_pp}"
        )
    return 10_000.0 / ((50.0 / sd_fatia_pp) ** 2 - 1.0)


def agregar_fatia_dois_candidatos(
    df: pd.DataFrame,
    data_ref: date,
    tau: float = 7.0,
    data_min: date | None = None,
) -> tuple[str, str, float, dict]:
    """
    Aggregates runoff polls on the two-party share ``A / (A + B)``.

    Each poll is reduced to the share between the two finalists before
    averaging, which removes differences in the undecided / blank level across
    institutes. Polls are weighted by exponential temporal decay.

    Args:
        df: Poll rows with columns candidato, intencao_voto_pct, instituto, data
            (``data`` already parsed to ``datetime.date``).
        data_ref: Reference date for the temporal weights.
        tau: Decay constant in days.
        data_min: If given, polls dated before this day are ignored.

    Returns:
        (cand_a, cand_b, fatia_a, info) where ``cand_a`` is the candidate with
        the larger aggregated share, ``fatia_a`` is its share in percent and
        ``info`` holds n_pesquisas, n_efetivo (Kish), soma_media, soma_min,
        soma_max and the institute list.

    Raises:
        ValueError: If columns are missing, the file does not hold exactly two
            candidates, or no complete poll remains after filtering.
    """
    required = {"candidato", "intencao_voto_pct", "instituto", "data"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    cands = sorted(df["candidato"].unique())
    if len(cands) != 2:
        raise ValueError(f"Expected exactly 2 candidates; found {cands}")
    if data_min is not None:
        df = df[df["data"] >= data_min]
    if df["candidato"].nunique() != 2:
        raise ValueError("No complete runoff poll left after filtering")

    wide = df.pivot_table(
        index=["instituto", "data"], columns="candidato",
        values="intencao_voto_pct", aggfunc="mean",
    ).dropna().reset_index()
    wide = wide[(wide[cands[0]] + wide[cands[1]]) > 0]
    if wide.empty:
        raise ValueError("No complete runoff poll left after filtering")

    soma = wide[cands[0]] + wide[cands[1]]
    share_first = wide[cands[0]] / soma * 100.0
    w = np.array([calcular_peso_temporal(d, data_ref, tau) for d in wide["data"]])
    w = w / w.sum()
    fatia_first = float(np.sum(w * share_first.values))

    if fatia_first >= 50.0:
        cand_a, cand_b, fatia_a = cands[0], cands[1], fatia_first
    else:
        cand_a, cand_b, fatia_a = cands[1], cands[0], 100.0 - fatia_first
    info = {
        "n_pesquisas": int(len(wide)),
        "n_efetivo": float(1.0 / np.sum(w ** 2)),
        "soma_media": float(soma.mean()),
        "soma_min": float(soma.min()),
        "soma_max": float(soma.max()),
        "institutos": sorted(wide["instituto"].unique()),
    }
    return cand_a, cand_b, fatia_a, info


def carregar_pesquisas_2t_fatia(
    csv_path=None,
    data_ref: date | None = None,
    tau: float = 7.0,
    data_min: date | None = None,
    retornar_info: bool = False,
) -> tuple:
    """
    Loads runoff polls and aggregates them on the two-party share.

    Returns the same tuple layout as ``carregar_pesquisas_2t()`` so callers can
    swap loaders: ``(cand_a, cand_b, voto_a, voto_b, rej_a, rej_b, desvio,
    residual)``. Here ``voto_a + voto_b == 100``, rejection is not used
    (``rej_a = rej_b = 0``) and ``residual == 0``. With ``retornar_info=True``
    the return value is ``(tuple, info)`` where ``info`` is the dictionary from
    ``agregar_fatia_dois_candidatos()``.

    Raises:
        FileNotFoundError: If the CSV does not exist.
    """
    csv_path = Path(csv_path) if csv_path else Path("data/pesquisas_2turno.csv")
    if not csv_path.exists():
        raise FileNotFoundError(f"File not found: {csv_path}")
    df = pd.read_csv(csv_path)
    df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date
    ref = data_ref or date.today()

    cand_a, cand_b, fatia_a, info = agregar_fatia_dois_candidatos(
        df, ref, tau=tau, data_min=data_min
    )
    print("\n" + "=" * 70)
    print("  SECOND ROUND POLL AGGREGATION (two-party share)")
    print("=" * 70)
    print(f"   Polls: {info['n_pesquisas']}  (effective n: {info['n_efetivo']:.1f})")
    print(f"   Institutes: {len(info['institutos'])}")
    print(f"   Sum of both candidates per poll: mean {info['soma_media']:.1f}, "
          f"range [{info['soma_min']:.1f}, {info['soma_max']:.1f}]")
    print(f"   {cand_a}: {fatia_a:.2f}%   {cand_b}: {100 - fatia_a:.2f}%")
    print("=" * 70)
    resultado = (cand_a, cand_b, fatia_a, 100.0 - fatia_a, 0.0, 0.0,
                 sd_fatia_para_desvio(SD_FATIA_PP_PADRAO), 0.0)
    return (resultado, info) if retornar_info else resultado


def simular_calibrado(
    cand_a: str,
    cand_b: str,
    fatia_a: float,
    sd_fatia_pp: float = SD_FATIA_PP_PADRAO,
    vies_pp_a: float = 0.0,
    usar_teto: bool = False,
    rej_a: float = 0.0,
    rej_b: float = 0.0,
) -> pd.DataFrame:
    """
    Runs ``simular()`` with an explicit sd of the two-party share and an
    optional poll-bias shift.

    Args:
        cand_a: Candidate whose share is ``fatia_a``.
        cand_b: Opponent.
        fatia_a: Aggregated two-party share of ``cand_a`` (percent).
        sd_fatia_pp: Effective sd of the share (pp), in (0, SD_FATIA_PP_MAX].
        vies_pp_a: Shift added to ``cand_a`` and removed from ``cand_b`` before
            sampling (positive favors ``cand_a``). Use it to model a known
            house effect, for example under-measured right-wing vote.
        usar_teto: Apply the rejection ceiling. Off by default: in a binary race
            the vote intention already reflects rejection.
        rej_a: Rejection of ``cand_a`` (only used when ``usar_teto``).
        rej_b: Rejection of ``cand_b`` (only used when ``usar_teto``).

    Returns:
        The DataFrame produced by ``simular()``.
    """
    voto_a = fatia_a + vies_pp_a
    if not np.isfinite(voto_a):
        raise ValueError("Shifted share must be finite")
    if not 0.0 < voto_a < 100.0:
        raise ValueError(f"Shifted share out of range: {voto_a}")
    df = simular(
        cand_a, cand_b, voto_a, 100.0 - voto_a,
        rej_a if usar_teto else 0.0, rej_b if usar_teto else 0.0,
        sd_fatia_para_desvio(sd_fatia_pp), 0.0,
    )

    df.attrs["calibracao"] = {
        "cand_a": cand_a, "cand_b": cand_b,
        "fatia_agregada_a": float(fatia_a), "vies_pp_a": float(vies_pp_a),
        "fatia_central_a": float(voto_a), "usar_teto": bool(usar_teto),
        "rej_a": float(rej_a if usar_teto else 0),
        "rej_b": float(rej_b if usar_teto else 0),
    }
    return df


def tabela_sensibilidade(
    fatia_a: float,
    sds_pp: tuple = (0.8, 1.5, 2.5, 3.0, 3.5),
    vieses_pp: tuple = (-1.0, 0.0, 1.0, 2.0, 3.0),
    n_sim: int = 40_000,
    seed: int = 42,
) -> pd.DataFrame:
    """
    P(A wins) in percent for each combination of bias shift and sd.

    Uses a local RNG and writes nothing to disk. Rows are bias shifts (pp added
    to A), columns are the effective sd of the share (pp).
    """
    rng = np.random.default_rng(seed)
    out = pd.DataFrame(index=list(vieses_pp), columns=list(sds_pp), dtype=float)
    for vies in vieses_pp:
        a = fatia_a + vies
        for sd in sds_pp:
            fator = max(100.0 / sd_fatia_para_desvio(sd), 1.0)
            share = rng.dirichlet([a * fator, (100.0 - a) * fator], size=n_sim)[:, 0]
            out.loc[vies, sd] = float((share > 0.5).mean() * 100.0)
    out.index.name = "vies_pp_a"
    return out


def imprimir_sensibilidade(tabela: pd.DataFrame, cand_a: str) -> None:
    """Prints the sensitivity table produced by ``tabela_sensibilidade()``."""
    print("\n" + "=" * 60)
    print(f"  SENSITIVITY: P({cand_a} wins), %")
    print("  rows = bias shift toward first candidate (pp); columns = sd of share (pp)")
    print("=" * 60)
    print(tabela.round(1).to_string())
    print("=" * 60)


# ─── SIMULATION ───────────────────────────────────────────────────────────────

def simular(cand_a, cand_b, voto_a, voto_b, rej_a, rej_b, desvio, residual):
    """
    Runs 40,000 second-round simulations using a 3-category Dirichlet.

    The three Dirichlet categories are:
        [candidate A votes, candidate B votes, blank/null votes]

    Rejection ceilings are applied to each finalist. The winner is determined
    by the vote share among [A, B] only (blank/null votes excluded from the
    valid vote denominator, consistent with Brazilian electoral law).

    Absolute vote projections use stochastic abstention sampled from
    Normal(ABSTENCAO_2T_MU, ABSTENCAO_2T_SIGMA) per simulation.

    Args:
        cand_a: Name of candidate A (leader by aggregated vote)
        cand_b: Name of candidate B (trailer)
        voto_a: Adjusted vote intention for A after residual redistribution (%)
        voto_b: Adjusted vote intention for B after residual redistribution (%)
        rej_a: Rejection rate for A (%)
        rej_b: Rejection rate for B (%)
        desvio: Combined standard deviation for Dirichlet concentration factor
        residual: Final blank/null proportion (Dirichlet third category) (%)

    Returns:
        pd.DataFrame: One row per simulation with columns:
            voto_a, voto_b, vencedor, diferenca,
            abstencao_pct, comparecimento, invalidos_pct, votos_invalidos,
            votos_validos, votos_a_abs, votos_b_abs, margem_votos
            (``votos_a_abs + votos_b_abs == votos_validos`` and
            ``votos_validos + votos_invalidos == comparecimento``)
    """
    print(f"\n[SIM] Running {N_SIM:,} second-round simulations...")
    print(f"   {cand_a}: {voto_a:.2f}%  (rejection: {rej_a:.1f}%,  ceiling: {100-rej_a:.1f}%)")
    print(f"   {cand_b}: {voto_b:.2f}%  (rejection: {rej_b:.1f}%,  ceiling: {100-rej_b:.1f}%)")
    print(f"   Blank/null pool: {residual:.2f}%")

    # Ensure all Dirichlet alphas are positive (required by numpy)
    blank_pool = max(residual, 0.1)
    fator = max(100.0 / desvio, 1.0)
    alphas = np.array([voto_a, voto_b, blank_pool]) * fator

    proporcoes = np.random.dirichlet(alphas, size=N_SIM)  # (N_SIM, 3)

    # Apply electoral ceiling before computing valid vote shares
    teto_a = max(100.0 - rej_a, 1.0)
    teto_b = max(100.0 - rej_b, 1.0)

    p_a_raw = proporcoes[:, 0] * 100
    p_b_raw = proporcoes[:, 1] * 100

    p_a_raw = np.minimum(p_a_raw, teto_a)
    p_b_raw = np.minimum(p_b_raw, teto_b)

    # Valid vote share excludes blank/null (Brazilian runoff rule)
    total_valido = p_a_raw + p_b_raw
    voto_a_sim = p_a_raw / total_valido * 100
    voto_b_sim = p_b_raw / total_valido * 100

    diferenca = np.abs(voto_a_sim - voto_b_sim)
    vencedor  = np.where(voto_a_sim > voto_b_sim, cand_a, cand_b)

    # Absolute votes: electorate → turnout → blank/null + valid. Before this
    # the whole turnout was split between A and B. The drawn blank/null share
    # is used only when the polls supplied an explicit pool (legacy base);
    # otherwise it comes from the runoff prior.
    votos = contabilizar_votos(
        np.random, N_SIM, ABSTENCAO_2T_MU, ABSTENCAO_2T_SIGMA,
        invalidos_frac=proporcoes[:, 2] if residual >= 1.0 else None,
        invalidos_mu=INVALIDOS_2T_MU, invalidos_sigma=INVALIDOS_2T_SIGMA,
        eleitorado=ELEITORADO,
    )
    absolutos = dividir_validos(votos["votos_validos"], np.column_stack([voto_a_sim, voto_b_sim]))
    votos_a_abs, votos_b_abs = absolutos[:, 0], absolutos[:, 1]

    df = pd.DataFrame({
        "voto_a":       voto_a_sim,
        "voto_b":       voto_b_sim,
        "vencedor":     vencedor,
        "diferenca":    diferenca,
        "abstencao_pct": votos["abstencao"] * 100,
        "comparecimento": votos["comparecimento"],
        "invalidos_pct": votos["invalidos_frac"] * 100,
        "votos_invalidos": votos["votos_invalidos"],
        "votos_validos": votos["votos_validos"],
        "votos_a_abs":  votos_a_abs,
        "votos_b_abs":  votos_b_abs,
        "margem_votos": np.abs(votos_a_abs - votos_b_abs),
    })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / "resultados_2turno_standalone.csv"
    df.to_csv(out, index=False)
    print(f"   Results saved: {out}")
    print("   OK")
    return df


# ─── REPORT ───────────────────────────────────────────────────────────────────

def relatorio(df, cand_a, cand_b, rej_a, rej_b):
    """Prints a structured summary of second-round simulation results."""
    sep = "=" * 60
    print(f"\n{sep}")
    print("  SECOND ROUND STANDALONE REPORT [v2.7]")
    print(sep)

    n = len(df)
    prob_a = (df["vencedor"] == cand_a).mean() * 100
    prob_b = (df["vencedor"] == cand_b).mean() * 100

    print(f"\nVictory probability:")
    print(f"  {cand_a:26s} {prob_a:.2f}%")
    print(f"  {cand_b:26s} {prob_b:.2f}%")

    print(f"\nVote share distribution (valid votes, IC 90%):")
    for label, col, rej in [(cand_a, "voto_a", rej_a), (cand_b, "voto_b", rej_b)]:
        mean_v = df[col].mean()
        ci_lo  = df[col].quantile(0.05)
        ci_hi  = df[col].quantile(0.95)
        print(f"  {label:26s} {mean_v:.2f}%  90% CI: [{ci_lo:.2f}% – {ci_hi:.2f}%]"
              f"  (rej: {rej:.1f}%)")

    print(f"\nMargin of victory:")
    print(f"  Close race (<3pp):      {(df['diferenca'] < 3).mean() * 100:.1f}% of scenarios")
    print(f"  Photo-finish (<1pp):    {(df['diferenca'] < 1).mean() * 100:.1f}% of scenarios")
    print(f"  Comfortable (>5pp):     {(df['diferenca'] >= 5).mean() * 100:.1f}% of scenarios")
    print(f"  Median margin:          {df['diferenca'].median():.2f}pp")

    p5m, p50m, p95m = df["margem_votos"].quantile([0.05, 0.50, 0.95])
    med_abs = df["abstencao_pct"].median()
    med_turn = df["comparecimento"].median() if "comparecimento" in df else df["votos_validos"].median()

    print(f"\nAbsolute vote projections:")
    print(f"  Electorate:             {ELEITORADO:>15,}")
    print(f"  Median turnout:         {int(med_turn):>15,}  (abstention: {med_abs:.1f}%)")
    if "invalidos_pct" in df:
        print(f"  Median valid votes:     {int(df['votos_validos'].median()):>15,}"
              f"  (blank/null: {df['invalidos_pct'].median():.1f}%)")
    for label, col in [(cand_a, "votos_a_abs"), (cand_b, "votos_b_abs")]:
        p5, p50, p95 = df[col].quantile([0.05, 0.50, 0.95])
        print(f"  {label:26s} {int(p50):>10,} votes  90% CI: [{int(p5):,} – {int(p95):,}]")
    print(f"  Median absolute margin: {int(p50m):>10,} votes  90% CI: [{int(p5m):,} – {int(p95m):,}]")

    print(sep)
    return prob_a, prob_b


# ─── VISUALIZATIONS ───────────────────────────────────────────────────────────

def graficos(df, cand_a, cand_b, rej_a, rej_b, prob_a, prob_b):
    """Legacy wrapper: the chart now lives in ``src.viz.runoff.plot_runoff``."""
    from src.viz.runoff import plot_runoff
    return plot_runoff(df, cand_a, cand_b, prob_a, prob_b, OUTPUT_DIR / "simulacao_2turno.png")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def _parse_args(argv=None) -> argparse.Namespace:
    """Parses CLI arguments for the standalone runoff simulation."""
    p = argparse.ArgumentParser(description="Standalone second round simulation")
    p.add_argument("--csv", default=None, help="Runoff poll CSV (default: data/pesquisas_2turno.csv)")
    p.add_argument("--base", choices=["fatia", "candidato"], default="fatia",
                   help="fatia: aggregate A/(A+B) per poll (default); "
                        "candidato: legacy per-candidate aggregation")
    p.add_argument("--sd-fatia", type=float, default=SD_FATIA_PP_PADRAO,
                   help="Effective sd of the two-party share in pp (fatia mode)")
    p.add_argument("--vies", type=float, default=0.0,
                   help="Signed shift in pp for --vies-candidato (fatia mode)")
    p.add_argument("--vies-candidato", help="Exact candidate name; required for nonzero --vies")
    p.add_argument("--data-min", default=None, help="Ignore polls before YYYY-MM-DD")
    p.add_argument("--tau", type=float, default=7.0, help="Temporal decay in days")
    p.add_argument("--seed", type=int, default=SEED_PADRAO,
                   help=f"Seed of the NumPy global RNG (default: {SEED_PADRAO})")
    p.add_argument("--as-of", type=date.fromisoformat, default=None, metavar="YYYY-MM-DD",
                   help="Reference date for poll weights (default: today)")
    return p.parse_args(argv)


def main(argv=None) -> None:
    """Runs the runoff simulation, report and charts."""
    args = _parse_args(argv)
    if args.base != "fatia" and (args.vies != 0 or args.vies_candidato):
        raise ValueError("Bias options require --base fatia")
    if args.vies != 0 and not args.vies_candidato:
        raise ValueError("Nonzero --vies requires --vies-candidato to bind its sign to a name")
    data_min = date.fromisoformat(args.data_min) if args.data_min else None
    np.random.seed(args.seed)

    print("=" * 60)
    print("  BRAZIL ELECTION - STANDALONE SECOND ROUND [v2.10]")
    print(f"  Aggregation base: {args.base}")
    print("=" * 60)

    if args.base == "fatia":
        (cand_a, cand_b, voto_a, voto_b, rej_a, rej_b, _, _), info = (
            carregar_pesquisas_2t_fatia(
                args.csv, data_ref=args.as_of, tau=args.tau, data_min=data_min,
                retornar_info=True,
            )
        )
        referencia = args.vies_candidato or cand_a
        vies_a = resolver_vies(cand_a, cand_b, referencia, args.vies)
        df = simular_calibrado(cand_a, cand_b, voto_a, args.sd_fatia, vies_a)
        prob_a, prob_b = relatorio(df, cand_a, cand_b, rej_a, rej_b)
        tabela = tabela_sensibilidade(voto_a)
        imprimir_sensibilidade(tabela, cand_a)
        params = {"sd_fatia_pp": args.sd_fatia, "vies_pp_a": vies_a,
                  "vies_candidato": referencia, "vies_pp": args.vies,
                  "tau": args.tau, "data_min": args.data_min}
        salvar_resumo(OUTPUT_DIR / "resumo_2turno.json", df, cand_a, cand_b,
                      voto_a, params, info, tabela)
    else:
        cand_a, cand_b, voto_a, voto_b, rej_a, rej_b, desvio, residual = (
            carregar_pesquisas_2t(args.csv)
        )
        voto_a_adj, voto_b_adj, residual_final = redistribuir_residual(
            voto_a, voto_b, rej_a, rej_b, residual
        )
        df = simular(cand_a, cand_b, voto_a_adj, voto_b_adj, rej_a, rej_b,
                     desvio, residual_final)
        prob_a, prob_b = relatorio(df, cand_a, cand_b, rej_a, rej_b)

    graficos(df, cand_a, cand_b, rej_a, rej_b, prob_a, prob_b)

    print("\nSimulation completed. Results in /outputs:")
    print("  resultados_2turno_standalone.csv")
    print("  simulacao_2turno.png")
    if args.base == "fatia":
        manifesto = escrever_manifesto_2t(args, params)
        print("  resumo_2turno.json")
        print(f"  {manifesto.name}")


def escrever_manifesto_2t(args: argparse.Namespace, params: dict) -> Path:
    """Manifest binding the runoff summary, CSV and chart to their inputs.

    ``publicar_2turno`` refuses to post when this manifest exists and any
    recorded file no longer matches its hash.
    """
    # Script mode: put this checkout's root first so ``src`` is this code,
    # not another installed copy.
    raiz_codigo = str(Path(__file__).resolve().parent.parent)
    if raiz_codigo not in sys.path:
        sys.path.insert(0, raiz_codigo)
    from src.io.manifest import caminho_manifesto, criar_manifesto, salvar_manifesto

    resumo = OUTPUT_DIR / "resumo_2turno.json"
    csv = Path(args.csv) if args.csv else Path("data/pesquisas_2turno.csv")
    saidas = [resumo, OUTPUT_DIR / "resultados_2turno_standalone.csv",
              OUTPUT_DIR / "simulacao_2turno.png"]
    manifesto = criar_manifesto(
        "segundo_turno", [csv], saidas, {**params, "base": args.base},
        as_of=args.as_of or date.today(), seed=args.seed, n_sim=N_SIM,
    )
    return salvar_manifesto(manifesto, caminho_manifesto(resumo))


if __name__ == "__main__":
    main()
