"""
brazil-election-montecarlo — backtesting module
================================================
Issue #11 / v2.9

Validates model accuracy against 2018 and 2022 historical elections.
For each snapshot (T-90 to T-7), loads historical poll data, runs the
simulation with those polls as input, then compares the forecast to the
known electoral result.

Operational purpose:
    Provides the Brier score and calibration evidence required before
    deploying model-derived edges on Polymarket. Without this, edges
    may reflect model noise rather than genuine market inefficiency.

Usage:
    python src/backtesting.py                  # all snapshots
    python src/backtesting.py --year 2022      # 2022 only
    python src/backtesting.py --year 2018      # 2018 only

Output:
    outputs/backtesting_report.csv             # per-snapshot metrics
    Console summary with Brier scores and shy-Bolsonaro bias table

Author: gabrielrv13
"""

import sys
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date
from typing import NamedTuple

# ─── PATHS ────────────────────────────────────────────────────────────────────

ROOT_DIR   = Path(__file__).resolve().parent.parent
DATA_DIR   = ROOT_DIR / "data" / "historico"
OUTPUT_DIR = ROOT_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# ─── GROUND TRUTH ─────────────────────────────────────────────────────────────
# Official TSE results.
# Source: https://resultados.tse.jus.br

GROUND_TRUTH: dict[str, dict] = {
    "2022": {
        "candidatos": ["Lula", "Bolsonaro"],
        "votos_1t":   {"Lula": 48.43, "Bolsonaro": 43.20},
        "vencedor_1t": "Lula",
        "margem_1t":   5.23,
        "par_finalista": frozenset(["Lula", "Bolsonaro"]),
    },
    "2018": {
        "candidatos": ["Bolsonaro", "Haddad"],
        "votos_1t":   {"Bolsonaro": 46.03, "Haddad": 29.28},
        "vencedor_1t": "Bolsonaro",
        "margem_1t":   16.75,
        "par_finalista": frozenset(["Bolsonaro", "Haddad"]),
    },
}

# Reference date for each snapshot — used for temporal poll weighting.
# T-N is measured from election day (Oct 4, 2022 / Oct 7, 2018).

SNAPSHOT_DATES: dict[str, dict[str, date]] = {
    "2022": {
        "T-90": date(2022, 7,  6),
        "T-60": date(2022, 8,  5),
        "T-30": date(2022, 9,  4),
        "T-14": date(2022, 9, 20),
        "T-7":  date(2022, 9, 27),
    },
    "2018": {
        "T-30": date(2018, 9,  7),
        "T-14": date(2018, 9, 23),
        "T-7":  date(2018, 9, 30),
    },
}

SNAPSHOTS_2022 = ["T-90", "T-60", "T-30", "T-14", "T-7"]
SNAPSHOTS_2018 = ["T-30", "T-14", "T-7"]

# ─── N_SIM ────────────────────────────────────────────────────────────────────

N_SIM_BACKTEST = 40_000

# ─── DATA STRUCTURES ──────────────────────────────────────────────────────────

class SnapshotResult(NamedTuple):
    """Holds the full result of backtesting one snapshot."""
    year:             str
    snapshot:         str
    rmse:             float
    brier:            float
    margin_error:     float
    winner_correct:   bool
    runoff_correct:   bool
    pred_winner_prob: float
    pred_margin:      float
    bias_per_cand:    dict


# ─── POLL AGGREGATION (local, no globals) ─────────────────────────────────────

def _calcular_peso_temporal(data_pesquisa: date, data_referencia: date, tau: int = 7) -> float:
    """Exponential temporal weight: peso = exp(-days_ago / tau)."""
    if data_pesquisa is None:
        return 1.0
    dias_atras = max(0, (data_referencia - data_pesquisa).days)
    return float(np.exp(-dias_atras / tau))


def _detectar_outliers(valores: np.ndarray, threshold: float = 2.5) -> np.ndarray:
    """Modified z-score outlier detection (MAD-based). Returns boolean mask."""
    if len(valores) < 3:
        return np.zeros(len(valores), dtype=bool)
    mediana = np.median(valores)
    mad = np.median(np.abs(valores - mediana))
    if mad == 0:
        return np.zeros(len(valores), dtype=bool)
    z_scores = 0.6745 * (valores - mediana) / mad
    return np.abs(z_scores) > threshold


def _agregar_candidato(df_cand: pd.DataFrame, data_referencia: date) -> tuple:
    """
    Aggregates polls for a single candidate with temporal weighting.

    Returns:
        (voto, rejeicao, desvio)  — all floats in percent
    """
    if len(df_cand) == 1:
        row = df_cand.iloc[0]
        return (
            float(row["intencao_voto_pct"]),
            float(row.get("rejeicao_pct", 0.0)),
            float(row["desvio_padrao_pct"]),
        )

    pesos = np.array([
        _calcular_peso_temporal(d, data_referencia)
        for d in df_cand["data"].values
    ])
    pesos = pesos / pesos.sum()

    votos = df_cand["intencao_voto_pct"].values
    is_outlier = _detectar_outliers(votos)
    mask = ~is_outlier if (~is_outlier).sum() > 0 else np.ones(len(votos), dtype=bool)

    pesos_v = pesos[mask] / pesos[mask].sum()
    voto = float(np.average(votos[mask], weights=pesos_v))

    # Rejection: only rows that explicitly reported it (> 0)
    rejeicao = 0.0
    if "rejeicao_pct" in df_cand.columns:
        mask_rej = df_cand["rejeicao_pct"].values > 0
        if mask_rej.any():
            pw = pesos[mask_rej] / pesos[mask_rej].sum()
            rejeicao = float(np.average(df_cand["rejeicao_pct"].values[mask_rej], weights=pw))

    # Combined std dev: sqrt(within² + between²)
    desvio_medio = float(np.average(df_cand.loc[mask, "desvio_padrao_pct"].values, weights=pesos_v))
    variancia_entre = float(np.average((votos[mask] - voto) ** 2, weights=pesos_v))
    desvio = float(np.sqrt(desvio_medio ** 2 + variancia_entre))

    return voto, rejeicao, desvio


# ─── SNAPSHOT LOADER ──────────────────────────────────────────────────────────

def carregar_snapshot(csv_path: Path, data_referencia: date) -> tuple:
    """
    Loads a historical poll snapshot and aggregates it using the same
    temporal-weighting logic as carregar_pesquisas() in simulation_v2.py.

    The key difference from the live loader: data_referencia is the
    snapshot date, NOT today. This ensures polls are weighted relative
    to the moment of the forecast, not the moment backtesting runs.

    Args:
        csv_path:        Path to historical CSV file.
        data_referencia: Snapshot date (e.g. date(2022, 9, 20) for T-14).

    Returns:
        tuple: (candidatos, votos_media, rejeicao, desvio_base, indecisos)
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Snapshot CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date

    required = {"candidato", "intencao_voto_pct", "desvio_padrao_pct"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {csv_path.name}: {missing}")

    candidatos = list(df["candidato"].unique())
    votos_list, rejeicao_list, desvio_list = [], [], []

    for cand in candidatos:
        df_cand = df[df["candidato"] == cand].copy()
        voto, rej, desv = _agregar_candidato(df_cand, data_referencia)
        votos_list.append(voto)
        rejeicao_list.append(rej)
        desvio_list.append(desv)

    votos_media = np.array(votos_list, dtype=float)
    rejeicao    = np.array(rejeicao_list, dtype=float)
    desvio_base = float(np.mean(desvio_list))

    # Undecided voters: weighted mean across all rows
    indecisos = 0.0
    if "indecisos_pct" in df.columns:
        pesos_g = np.array([
            _calcular_peso_temporal(d, data_referencia)
            for d in df["data"].values
        ])
        pesos_g = pesos_g / pesos_g.sum()
        indecisos = float(np.average(df["indecisos_pct"].fillna(0).values, weights=pesos_g))

    return candidatos, votos_media, rejeicao, desvio_base, indecisos


# ─── SIMULATION RUNNER ────────────────────────────────────────────────────────

def executar_simulacao_historica(
    candidatos:  list[str],
    votos_media: np.ndarray,
    rejeicao:    np.ndarray,
    desvio:      float,
    indecisos:   float,
    n_sim:       int = N_SIM_BACKTEST,
) -> dict:
    """
    Runs first-round Monte Carlo simulation using historical poll inputs.

    Replicates the Dirichlet sampling logic from simular_primeiro_turno()
    without depending on module-level globals.

    Returns:
        dict with keys:
            "prob_vencedor"  : {candidato: float} — win probability (0–1)
            "mediana_votos"  : {candidato: float} — median vote share (%)
            "mediana_margem" : float              — median first-round margin (pp)
            "prob_par"       : dict[frozenset, float] — runoff pair probabilities
    """
    # ── Undecided redistribution ───────────────────────────────────────────────
    votos_efetivos = votos_media.copy()
    if indecisos > 0:
        espaco = np.maximum(100.0 - rejeicao, 0.0) / 100.0
        pesos_dist = votos_media * espaco
        total_peso = pesos_dist.sum()
        if total_peso > 0:
            proporcoes = pesos_dist / total_peso
            votos_efetivos += proporcoes * indecisos * 0.85  # 15% to blank/null

    # Guard against invalid alphas
    votos_efetivos = np.maximum(votos_efetivos, 0.01)

    # ── Dirichlet sampling ────────────────────────────────────────────────────
    fator = 100.0 / max(desvio, 0.5)
    alphas = votos_efetivos * fator
    proporcoes = np.random.dirichlet(alphas, size=n_sim)
    votos_norm = proporcoes * 100.0

    # ── Rejection ceiling ─────────────────────────────────────────────────────
    tetos = 100.0 - rejeicao
    votos_limitados = np.minimum(votos_norm, tetos[np.newaxis, :])
    totais = votos_limitados.sum(axis=1, keepdims=True)
    totais = np.where(totais == 0, 1.0, totais)
    votos_final = votos_limitados / totais * 100.0

    # ── Winner per simulation ─────────────────────────────────────────────────
    idx_vencedor = np.argmax(votos_final, axis=1)
    vencedores = np.array(candidatos)[idx_vencedor]

    prob_vencedor = {
        c: float((vencedores == c).mean())
        for c in candidatos
    }
    mediana_votos = {
        c: float(np.median(votos_final[:, i]))
        for i, c in enumerate(candidatos)
    }

    # ── Margin distribution ───────────────────────────────────────────────────
    sorted_votes = np.sort(votos_final, axis=1)[:, ::-1]
    margens = sorted_votes[:, 0] - sorted_votes[:, 1]
    mediana_margem = float(np.median(margens))

    # ── Runoff pair probabilities ─────────────────────────────────────────────
    top2_idx = np.argsort(votos_final, axis=1)[:, -2:]
    top2_sorted = np.sort(top2_idx, axis=1)
    par_labels = [
        frozenset([candidatos[a], candidatos[b]])
        for a, b in top2_sorted
    ]
    prob_par: dict[frozenset, float] = {}
    for par in par_labels:
        prob_par[par] = prob_par.get(par, 0) + 1
    for par in prob_par:
        prob_par[par] /= n_sim

    return {
        "prob_vencedor":  prob_vencedor,
        "mediana_votos":  mediana_votos,
        "mediana_margem": mediana_margem,
        "prob_par":       prob_par,
    }


# ─── METRICS ──────────────────────────────────────────────────────────────────

def calcular_metricas(
    resultado: dict,
    ground_truth: dict,
    year: str,
    snapshot: str,
) -> SnapshotResult:
    """
    Computes the five backtesting metrics for a single snapshot.

    Metrics:
        1. Vote share RMSE  — sqrt(mean((pred_i - actual_i)^2)) across ground-truth candidates
        2. Winner correct   — model assigned highest win prob to actual winner
        3. Brier score      — (p_winner - 1)^2 for the actual winner
        4. Margin error     — |predicted_median_margin - actual_margin| (pp)
        5. Runoff correct   — model's highest-prob pair matches actual runoff pair
    """
    gt = ground_truth
    vencedor_real  = gt["vencedor_1t"]
    margem_real    = gt["margem_1t"]
    par_real       = gt["par_finalista"]
    votos_reais    = gt["votos_1t"]

    med_votos  = resultado["mediana_votos"]
    prob_vitoria = resultado["prob_vencedor"]

    # 1. Vote share RMSE (only over ground-truth candidates)
    erros = [
        (med_votos.get(c, 0.0) - votos_reais[c]) ** 2
        for c in votos_reais
    ]
    rmse = float(np.sqrt(np.mean(erros)))

    # 2. Winner correct
    vencedor_modelo = max(prob_vitoria, key=prob_vitoria.get)
    winner_correct  = vencedor_modelo == vencedor_real

    # 3. Brier score
    p_winner = prob_vitoria.get(vencedor_real, 0.0)
    brier = float((p_winner - 1.0) ** 2)

    # 4. Margin error
    margin_error = float(abs(resultado["mediana_margem"] - margem_real))

    # 5. Runoff pair correct
    prob_par = resultado["prob_par"]
    if prob_par:
        par_modelo = max(prob_par, key=prob_par.get)
        runoff_correct = par_modelo == par_real
    else:
        runoff_correct = False

    # Signed bias per candidate: predicted - actual (positive = overestimate)
    bias_per_cand = {
        c: round(med_votos.get(c, 0.0) - votos_reais[c], 2)
        for c in votos_reais
    }

    return SnapshotResult(
        year=year,
        snapshot=snapshot,
        rmse=round(rmse, 3),
        brier=round(brier, 4),
        margin_error=round(margin_error, 2),
        winner_correct=winner_correct,
        runoff_correct=runoff_correct,
        pred_winner_prob=round(p_winner, 4),
        pred_margin=round(resultado["mediana_margem"], 2),
        bias_per_cand=bias_per_cand,
    )


# ─── SINGLE SNAPSHOT ORCHESTRATOR ─────────────────────────────────────────────

def backtest_snapshot(year: str, snapshot: str, n_sim: int = N_SIM_BACKTEST) -> SnapshotResult:
    """
    Runs the full backtesting pipeline for one (year, snapshot) pair.

    Pipeline:
        1. Resolve CSV path
        2. Load and aggregate polls with carregar_snapshot()
        3. Run simulation with executar_simulacao_historica()
        4. Compute metrics with calcular_metricas()
        5. Return SnapshotResult
    """
    if year not in GROUND_TRUTH:
        raise ValueError(f"Unknown year: {year}. Valid: {list(GROUND_TRUTH.keys())}")
    if year not in SNAPSHOT_DATES or snapshot not in SNAPSHOT_DATES[year]:
        raise ValueError(f"Unknown snapshot {snapshot} for year {year}")

    csv_path = DATA_DIR / f"{year}_1t_{snapshot}.csv"
    data_ref = SNAPSHOT_DATES[year][snapshot]

    candidatos, votos_media, rejeicao, desvio_base, indecisos = carregar_snapshot(
        csv_path, data_ref
    )

    resultado = executar_simulacao_historica(
        candidatos, votos_media, rejeicao, desvio_base, indecisos, n_sim
    )

    return calcular_metricas(resultado, GROUND_TRUTH[year], year, snapshot)


# ─── FULL BACKTESTING RUN ─────────────────────────────────────────────────────

def backtest_completo(year: str | None = None, n_sim: int = N_SIM_BACKTEST) -> list[SnapshotResult]:
    """
    Runs backtesting across all available snapshots for one or both elections.

    Skips snapshots whose CSV file does not exist (partial data collection).
    Prints a warning for each missing file.
    """
    schedule: list[tuple[str, str]] = []

    years = [year] if year else ["2022", "2018"]
    snap_map = {"2022": SNAPSHOTS_2022, "2018": SNAPSHOTS_2018}

    for yr in years:
        for snap in snap_map[yr]:
            schedule.append((yr, snap))

    resultados: list[SnapshotResult] = []

    for yr, snap in schedule:
        csv_path = DATA_DIR / f"{yr}_1t_{snap}.csv"
        if not csv_path.exists():
            print(f"  [SKIP] {csv_path.name} not found — skipping")
            continue

        print(f"  [RUN]  {yr} {snap} ...", end=" ", flush=True)
        try:
            resultado = backtest_snapshot(yr, snap, n_sim)
            resultados.append(resultado)
            status = "OK" if resultado.winner_correct else "WRONG WINNER"
            print(f"RMSE={resultado.rmse:.2f}pp  Brier={resultado.brier:.4f}  [{status}]")
        except Exception as exc:
            print(f"ERROR — {exc}")

    return resultados


# ─── REPORTING ────────────────────────────────────────────────────────────────

def relatorio_backtesting(resultados: list[SnapshotResult]) -> None:
    """
    Prints a structured summary and saves outputs/backtesting_report.csv.

    Console output:
        - Per-snapshot table
        - Brier score per election year
        - Shy-Bolsonaro bias table (mean signed error per candidate)
        - Overall verdict vs 3pp RMSE threshold
    """
    sep = "=" * 70

    print(f"\n{sep}")
    print("  BACKTESTING REPORT — brazil-election-montecarlo v2.9")
    print(sep)

    # ── Per-snapshot table ────────────────────────────────────────────────────
    header = f"{'Year':<6} {'Snap':<6} {'RMSE':>6} {'Brier':>7} {'MarginErr':>10} {'Winner':>8} {'Runoff':>8}"
    print(f"\n{header}")
    print("-" * 56)

    for r in resultados:
        win  = "YES" if r.winner_correct  else "NO"
        run  = "YES" if r.runoff_correct  else "NO"
        print(
            f"{r.year:<6} {r.snapshot:<6} "
            f"{r.rmse:>6.2f} {r.brier:>7.4f} "
            f"{r.margin_error:>10.2f} "
            f"{win:>8} {run:>8}"
        )

    # ── Brier score per year ──────────────────────────────────────────────────
    print(f"\n{'─'*40}")
    print("  BRIER SCORE BY YEAR")
    print(f"{'─'*40}")
    for yr in ["2022", "2018"]:
        yr_results = [r for r in resultados if r.year == yr]
        if yr_results:
            brier_medio = np.mean([r.brier for r in yr_results])
            rmse_medio  = np.mean([r.rmse  for r in yr_results])
            wins = sum(r.winner_correct for r in yr_results)
            print(
                f"  {yr}  Brier={brier_medio:.4f}  "
                f"RMSE={rmse_medio:.2f}pp  "
                f"Winner correct: {wins}/{len(yr_results)}"
            )

    # ── Shy Bolsonaro bias table ──────────────────────────────────────────────
    print(f"\n{'─'*40}")
    print("  CANDIDATE BIAS  (predicted − actual, pp)")
    print("  Positive = model overestimated; Negative = underestimated")
    print(f"{'─'*40}")

    all_cands: set[str] = set()
    for r in resultados:
        all_cands.update(r.bias_per_cand.keys())

    for cand in sorted(all_cands):
        biases = [r.bias_per_cand[cand] for r in resultados if cand in r.bias_per_cand]
        if biases:
            media = np.mean(biases)
            direction = "OVERESTIMATED" if media > 1.5 else ("UNDERESTIMATED" if media < -1.5 else "calibrated")
            print(f"  {cand:<22}  mean bias = {media:+.2f}pp  [{direction}]")

    # ── Overall verdict ───────────────────────────────────────────────────────
    print(f"\n{'─'*40}")
    rmse_geral = np.mean([r.rmse for r in resultados])
    verdict = "PASS" if rmse_geral < 3.0 else "FAIL"
    print(f"  Overall mean RMSE : {rmse_geral:.2f}pp  (threshold: 3.00pp)  [{verdict}]")
    print(f"  Total snapshots   : {len(resultados)}")
    print(sep)

    # ── Save CSV ──────────────────────────────────────────────────────────────
    rows = []
    for r in resultados:
        row = r._asdict()
        row["bias_per_cand"] = str(r.bias_per_cand)
        rows.append(row)

    out_path = OUTPUT_DIR / "backtesting_report.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"\n  Report saved: {out_path}")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtesting module — brazil-election-montecarlo v2.9",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/backtesting.py
  python src/backtesting.py --year 2022
  python src/backtesting.py --year 2018 --n-sim 200000
        """,
    )
    parser.add_argument(
        "--year",
        choices=["2022", "2018"],
        default=None,
        help="Restrict backtesting to one election year (default: both)",
    )
    parser.add_argument(
        "--n-sim",
        type=int,
        default=N_SIM_BACKTEST,
        metavar="N",
        help=f"Monte Carlo iterations per snapshot (default: {N_SIM_BACKTEST})",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point for CLI execution."""
    args = _parse_args()
    print(f"\nbrazil-election-montecarlo — backtesting v2.9")
    print(f"  Year filter : {args.year or 'all'}")
    print(f"  N_SIM       : {args.n_sim:,}\n")

    resultados = backtest_completo(year=args.year, n_sim=args.n_sim)

    if not resultados:
        print("No snapshots processed. Add historical CSV files to data/historico/")
        sys.exit(0)

    relatorio_backtesting(resultados)


if __name__ == "__main__":
    main()