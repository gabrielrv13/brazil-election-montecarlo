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

"""

import sys
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date
from typing import NamedTuple

# ─── PATHS ────────────────────────────────────────────────────────────────────

ROOT_DIR     = Path(__file__).resolve().parent.parent
DATA_DIR     = ROOT_DIR / "data" / "historico"
OUTPUT_DIR   = ROOT_DIR / "outputs"
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

# Snapshots where data files are expected to exist
SNAPSHOTS_2022 = ["T-90", "T-60", "T-30", "T-14", "T-7"]
SNAPSHOTS_2018 = ["T-30", "T-14", "T-7"]   # T-90/T-60 excluded: Haddad not in race yet

# ─── N_SIM ────────────────────────────────────────────────────────────────────

N_SIM_BACKTEST = 40_000   # Sufficient for winner probability; override via CLI if needed

# ─── DATA STRUCTURES ──────────────────────────────────────────────────────────

class SnapshotResult(NamedTuple):
    """Holds the full result of backtesting one snapshot."""
    year:           str
    snapshot:       str
    rmse:           float     # vote share RMSE (pp)
    brier:          float     # Brier score for winner prediction
    margin_error:   float     # |predicted_margin - actual_margin| (pp)
    winner_correct: bool      # model assigned >50% to actual winner?
    runoff_correct: bool      # model predicted correct runoff pair?
    pred_winner_prob: float   # model's probability for actual winner (%)
    pred_margin:    float     # model's median predicted margin (pp)
    bias_per_cand:  dict      # {candidato: pred_vote - actual_vote}  (signed pp)


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
            Matches the signature expected by the simulation functions.

    CSV format expected:
        candidato, intencao_voto_pct, rejeicao_pct, desvio_padrao_pct,
        indecisos_pct, instituto, data_pesquisa, snapshot
    """
    raise NotImplementedError("carregar_snapshot() — to be implemented in Phase 4")


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
    in simulation_v2.py without depending on its module-level globals.
    This ensures backtesting results are fully reproducible regardless
    of the current state of pesquisas.csv.

    Args:
        candidatos:   List of candidate names.
        votos_media:  Array of aggregated vote intentions (%).
        rejeicao:     Array of rejection rates (%).
        desvio:       Combined poll standard deviation (pp).
        indecisos:    Undecided voter share (%).
        n_sim:        Number of Monte Carlo iterations.

    Returns:
        dict with keys:
            "prob_vencedor"  : {candidato: float} — win probability (0–1)
            "mediana_votos"  : {candidato: float} — median vote share (%)
            "mediana_margem" : float              — median first-round margin (pp)
            "prob_par"       : dict[frozenset, float] — runoff pair probabilities
    """
    raise NotImplementedError("executar_simulacao_historica() — to be implemented in Phase 4")


# ─── METRICS ──────────────────────────────────────────────────────────────────

def calcular_metricas(
    resultado_simulacao: dict,
    ground_truth:        dict,
    year:                str,
    snapshot:            str,
) -> SnapshotResult:
    """
    Computes the five backtesting metrics for a single snapshot.

    Metrics:
        1. Vote share RMSE  — sqrt(mean((pred_i - actual_i)^2))  across candidates
        2. Winner correct   — model assigned >50% win prob to actual winner
        3. Brier score      — (p_winner - 1)^2  for the actual winner
        4. Margin error     — |predicted_median_margin - actual_margin|  (pp)
        5. Runoff correct   — model's top-2 pair matches actual runoff pair

    Args:
        resultado_simulacao: Output dict from executar_simulacao_historica().
        ground_truth:        Dict from GROUND_TRUTH[year].
        year:                Election year string ("2022" or "2018").
        snapshot:            Snapshot label ("T-7", "T-14", etc.).

    Returns:
        SnapshotResult populated with all five metrics plus bias_per_cand.
    """
    raise NotImplementedError("calcular_metricas() — to be implemented in Phase 4")


# ─── SINGLE SNAPSHOT ORCHESTRATOR ─────────────────────────────────────────────

def backtest_snapshot(year: str, snapshot: str, n_sim: int = N_SIM_BACKTEST) -> SnapshotResult:
    """
    Runs the full backtesting pipeline for one (year, snapshot) pair.

    Pipeline:
        1. Resolve CSV path: data/historico/{year}_1t_{snapshot}.csv
        2. Load and aggregate polls with carregar_snapshot()
        3. Run simulation with executar_simulacao_historica()
        4. Compute metrics with calcular_metricas()
        5. Return SnapshotResult

    Args:
        year:     "2022" or "2018"
        snapshot: One of "T-90", "T-60", "T-30", "T-14", "T-7"
        n_sim:    Number of Monte Carlo iterations.

    Returns:
        SnapshotResult for this snapshot.

    Raises:
        FileNotFoundError: If the expected CSV does not exist.
        ValueError:        If year or snapshot are not recognized.
    """
    raise NotImplementedError("backtest_snapshot() — to be implemented in Phase 4")


# ─── FULL BACKTESTING RUN ─────────────────────────────────────────────────────

def backtest_completo(year: str | None = None, n_sim: int = N_SIM_BACKTEST) -> list[SnapshotResult]:
    """
    Runs backtesting across all available snapshots for one or both elections.

    Skips snapshots whose CSV file does not exist yet (data collection
    may be partial). Prints a warning for each missing file.

    Args:
        year:  "2022", "2018", or None (runs both).
        n_sim: Number of Monte Carlo iterations per snapshot.

    Returns:
        List of SnapshotResult, one per successfully processed snapshot.
    """
    raise NotImplementedError("backtest_completo() — to be implemented in Phase 4")


# ─── REPORTING ────────────────────────────────────────────────────────────────

def relatorio_backtesting(resultados: list[SnapshotResult]) -> None:
    """
    Prints a structured summary and saves outputs/backtesting_report.csv.

    Console output:
        - Per-snapshot table: RMSE, Brier, margin error, winner correct, runoff correct
        - Aggregated Brier score per election year
        - Shy-Bolsonaro bias table: mean signed error per candidate across snapshots
        - Overall model accuracy verdict (pass/fail vs 3pp RMSE threshold)

    CSV output (outputs/backtesting_report.csv):
        One row per SnapshotResult. All SnapshotResult fields as columns.
        Used by dashboard.py in a future feature (v3.x historical accuracy panel).

    Args:
        resultados: List of SnapshotResult from backtest_completo().
    """
    raise NotImplementedError("relatorio_backtesting() — to be implemented in Phase 4")


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