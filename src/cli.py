"""
Single canonical CLI entry point for brazil-election-montecarlo.

All public interfaces are stable across v3 sprints.  The implementation of
each subcommand handler will be swapped out as core modules are delivered:

    Sprint 1  — Argument structure only; handlers are compatibility bridges
                 to the legacy simulation_v2.py and backtesting.py modules.
    Sprint 2  — _handle_run() wired to src.core.simulation + src.io.loader.
    Sprint 3  — --no-history flag respected; src.io.history.salvar_historico
                 called at the end of every run.
    Sprint 4  — Legacy scripts deprecated; MIGRATION.md published.

Usage
-----
    python -m src                           # run simulation (default)
    python -m src run                       # explicit subcommand
    python -m src run --n-sim 200000        # tail-probability markets
    python -m src run --bayesian            # enable MCMC (20–30 s overhead)
    python -m src run --no-history          # skip SQLite persistence (CI)
    python -m src run --csv data/alt.csv    # alternative poll CSV
    python -m src run --seed 42             # reproducible run
    python -m src backtest                  # 2018 + 2022 snapshots
    python -m src backtest --year 2022      # single election year
    python -m src backtest --n-sim 40000    # override iterations
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_CSV: Path = Path("data/pesquisas.csv")
_DEFAULT_N_SIM: int = 40_000
_DEFAULT_N_SIM_BACKTEST: int = 10_000

_EXIT_OK: int = 0
_EXIT_ERR: int = 1


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argument parser.

    Returns
    -------
    argparse.ArgumentParser
        Configured parser with ``run`` and ``backtest`` subcommands.
    """
    parser = argparse.ArgumentParser(
        prog="python -m src",
        description=(
            "brazil-election-montecarlo — Monte Carlo simulation of the "
            "2026 Brazilian presidential election."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python -m src                            run simulation with defaults
  python -m src run --n-sim 200000         high-precision tail-probability run
  python -m src run --bayesian             enable MCMC (PyMC)
  python -m src run --no-history           skip SQLite history (CI mode)
  python -m src run --csv data/alt.csv     use alternative poll file
  python -m src backtest --year 2022       backtest against 2022 election
  python -m src backtest --n-sim 40000     override iterations for backtest
        """,
    )

    subparsers = parser.add_subparsers(
        dest="subcommand",
        metavar="SUBCOMMAND",
    )

    _add_run_subparser(subparsers)
    _add_backtest_subparser(subparsers)

    return parser


def _add_run_subparser(
    subparsers: argparse._SubParsersAction,  # type: ignore[type-arg]
) -> None:
    """Register the ``run`` subcommand with its flags.

    Parameters
    ----------
    subparsers:
        The subparser action returned by ``parser.add_subparsers()``.
    """
    run_parser = subparsers.add_parser(
        "run",
        help="Run the Monte Carlo simulation (default when no subcommand given).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Run a full simulation cycle: load polls, run Monte Carlo, "
            "generate charts and PDF report, persist result to history."
        ),
    )

    run_parser.add_argument(
        "--csv",
        type=Path,
        default=_DEFAULT_CSV,
        metavar="PATH",
        help=(
            f"Path to the first-round poll CSV file. "
            f"Default: {_DEFAULT_CSV}"
        ),
    )

    run_parser.add_argument(
        "--n-sim",
        type=int,
        default=_DEFAULT_N_SIM,
        metavar="N",
        help=(
            f"Number of Monte Carlo iterations. Default: {_DEFAULT_N_SIM:,}. "
            "Use 200000 when model_prob < 0.05 for tail-probability markets."
        ),
    )

    run_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="INT",
        help="Random seed for reproducible runs. Default: None (non-deterministic).",
    )

    run_parser.add_argument(
        "--bayesian",
        action="store_true",
        default=False,
        help=(
            "Enable PyMC MCMC model (construir_modelo). "
            "Adds 20–30 s to execution time. Default: off."
        ),
    )

    run_parser.add_argument(
        "--no-history",
        action="store_true",
        default=False,
        dest="no_history",
        help=(
            "Skip writing this run to the SQLite forecast history "
            "(outputs/forecast_history.db). Useful for CI and dry runs."
        ),
    )


def _add_backtest_subparser(
    subparsers: argparse._SubParsersAction,  # type: ignore[type-arg]
) -> None:
    """Register the ``backtest`` subcommand with its flags.

    Parameters
    ----------
    subparsers:
        The subparser action returned by ``parser.add_subparsers()``.
    """
    backtest_parser = subparsers.add_parser(
        "backtest",
        help="Run historical backtesting against 2018 and/or 2022 elections.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Evaluate model accuracy against historical election snapshots. "
            "Requires CSV files under data/historico/ (see ROADMAP.md §v2.9)."
        ),
    )

    backtest_parser.add_argument(
        "--year",
        choices=["2018", "2022"],
        default=None,
        metavar="YEAR",
        help=(
            "Restrict backtesting to a single election year. "
            "Accepted values: 2018, 2022. Default: both years."
        ),
    )

    backtest_parser.add_argument(
        "--n-sim",
        type=int,
        default=_DEFAULT_N_SIM_BACKTEST,
        metavar="N",
        help=(
            f"Monte Carlo iterations per snapshot. "
            f"Default: {_DEFAULT_N_SIM_BACKTEST:,}."
        ),
    )


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------


def _validate_run_args(args: argparse.Namespace) -> list[str]:
    """Validate arguments for the ``run`` subcommand.

    Parameters
    ----------
    args:
        Parsed namespace from the ``run`` subparser.

    Returns
    -------
    list[str]
        List of validation error messages. Empty list means all arguments
        are valid.
    """
    errors: list[str] = []

    if not args.csv.exists():
        errors.append(
            f"Poll CSV not found: {args.csv}\n"
            f"  Tip: pass a different path with --csv <PATH>"
        )

    if args.n_sim < 1_000:
        errors.append(
            f"--n-sim must be at least 1,000 (got {args.n_sim:,}). "
            "Standard runs use 40,000; tail-probability markets use 200,000."
        )

    if args.n_sim > 1_000_000:
        errors.append(
            f"--n-sim {args.n_sim:,} exceeds the 1,000,000 safety ceiling. "
            "Use 200,000 for tail markets."
        )

    return errors


def _validate_backtest_args(args: argparse.Namespace) -> list[str]:
    """Validate arguments for the ``backtest`` subcommand.

    Parameters
    ----------
    args:
        Parsed namespace from the ``backtest`` subparser.

    Returns
    -------
    list[str]
        List of validation error messages. Empty list means all arguments
        are valid.
    """
    errors: list[str] = []

    if args.n_sim < 1_000:
        errors.append(
            f"--n-sim must be at least 1,000 (got {args.n_sim:,})."
        )

    return errors


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def _handle_run(args: argparse.Namespace) -> int:
    """Execute the simulation pipeline for the ``run`` subcommand.

    Orchestration order (Sprint 2+ implementation):
        1. load_polls(config)           → PollData          [src.io.loader]
        2. simulate(config, poll_data)  → SimulationResult  [src.core.simulation]
        3. save_history(result)         → None              [src.io.history]  (unless --no-history)
        4. generate_charts(result)      → None              [src.viz.charts]
        5. generate_report(result)      → None              [src.io.report]

    Parameters
    ----------
    args:
        Parsed namespace from the ``run`` subparser.

    Returns
    -------
    int
        Exit code: 0 on success, 1 on error.
    """
    errors = _validate_run_args(args)
    if errors:
        for msg in errors:
            print(f"[ERROR] {msg}", file=sys.stderr)
        return _EXIT_ERR

    _print_run_header(args)

    # ------------------------------------------------------------------
    # COMPAT: Sprint 1 bridge to legacy simulation_v2.py.
    # Replace this block in Sprint 2 once src.core.simulation is ready.
    # ------------------------------------------------------------------
    try:
        return _run_legacy_simulation(args)
    except FileNotFoundError as exc:
        print(f"[ERROR] File not found: {exc}", file=sys.stderr)
        return _EXIT_ERR
    except ValueError as exc:
        print(f"[ERROR] Invalid data: {exc}", file=sys.stderr)
        return _EXIT_ERR
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Unexpected error: {exc}", file=sys.stderr)
        raise


def _handle_backtest(args: argparse.Namespace) -> int:
    """Execute historical backtesting for the ``backtest`` subcommand.

    Parameters
    ----------
    args:
        Parsed namespace from the ``backtest`` subparser.

    Returns
    -------
    int
        Exit code: 0 on success, 1 on error.
    """
    errors = _validate_backtest_args(args)
    if errors:
        for msg in errors:
            print(f"[ERROR] {msg}", file=sys.stderr)
        return _EXIT_ERR

    try:
        return _run_legacy_backtest(args)
    except FileNotFoundError as exc:
        print(f"[ERROR] File not found: {exc}", file=sys.stderr)
        return _EXIT_ERR
    except ValueError as exc:
        print(f"[ERROR] Invalid data: {exc}", file=sys.stderr)
        return _EXIT_ERR
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Unexpected error: {exc}", file=sys.stderr)
        raise


# ---------------------------------------------------------------------------
# Legacy compatibility bridges (Sprint 1 only — remove in Sprint 2/4)
# ---------------------------------------------------------------------------


def _run_legacy_simulation(args: argparse.Namespace) -> int:
    """Bridge to simulation_v2.py for Sprint 1 compatibility.

    This function imports the legacy module and invokes it with the parsed
    CLI arguments translated to the legacy global interface.  It will be
    replaced in Sprint 2 when src.core.simulation delivers SimulationConfig.

    Parameters
    ----------
    args:
        Parsed ``run`` namespace.

    Returns
    -------
    int
        Exit code.
    """
    # Inline import to avoid side effects when the CLI module is imported
    # for testing or by other tools.
    import importlib.util
    import os

    root = Path(__file__).resolve().parent.parent
    legacy_path = root / "simulation_v2.py"
    if not legacy_path.exists():
        # Try src/ layout in case files were partially reorganized.
        legacy_path = root / "src" / "simulation_v2.py"

    if not legacy_path.exists():
        print(
            "[ERROR] Cannot locate simulation_v2.py. "
            "Ensure the file exists at the project root.",
            file=sys.stderr,
        )
        return _EXIT_ERR

    # Override N_SIM via environment so the legacy module picks it up before
    # its module-level constant is set.  The legacy __main__ block reads
    # _args.n_sim and re-assigns N_SIM; we replicate that here.
    spec = importlib.util.spec_from_file_location("simulation_v2", legacy_path)
    assert spec is not None and spec.loader is not None  # noqa: S101
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]

    # Apply CLI overrides to the loaded module's global state.
    if args.n_sim != _DEFAULT_N_SIM:
        module.N_SIM = args.n_sim
        print(f"  [CLI] N_SIM overridden: {module.N_SIM:,}")

    if str(args.csv) != str(_DEFAULT_CSV):
        # The legacy module uses a module-level CSV_PATH; patch it if present.
        if hasattr(module, "CSV_PATH"):
            module.CSV_PATH = args.csv
        elif hasattr(module, "DATA_DIR"):
            # Cannot cleanly override DATA_DIR from here — warn the user.
            print(
                f"[WARN] Legacy module does not expose CSV_PATH directly. "
                f"--csv {args.csv} may not take effect. "
                "This limitation is resolved in Sprint 2.",
                file=sys.stderr,
            )

    # Run the legacy pipeline (mirrors simulation_v2.py __main__ block).
    module.inicializar()
    module.validar_viabilidade()

    if args.bayesian:
        trace = module.construir_modelo()
    else:
        trace = None

    df1, info_lim_1t, info_indecisos, validos_final, candidatos_validos = (
        module.simular_primeiro_turno()
    )

    import pandas as pd  # noqa: PLC0415

    df2 = pd.DataFrame()
    info_matchups: dict = {}

    pv, p2v, p2t = module.relatorio(
        df1, df2, info_lim_1t, info_matchups, info_indecisos
    )
    module.graficos(
        df1, df2, trace, pv, p2v, p2t, info_lim_1t, info_matchups, info_indecisos
    )

    if args.no_history:
        print("\n[INFO] --no-history set: skipping forecast_history.db write.")
    else:
        # TODO(Sprint 3): Call src.io.history.salvar_historico(result) here.
        print(
            "\n[INFO] History persistence not yet implemented (Sprint 3). "
            "Run with --no-history to suppress this message."
        )

    print("\nSimulation completed. Results available in outputs/")
    return _EXIT_OK


def _run_legacy_backtest(args: argparse.Namespace) -> int:
    """Bridge to backtesting.py for Sprint 1 compatibility.

    Parameters
    ----------
    args:
        Parsed ``backtest`` namespace.

    Returns
    -------
    int
        Exit code.
    """
    import importlib.util

    root = Path(__file__).resolve().parent.parent
    legacy_path = root / "backtesting.py"
    if not legacy_path.exists():
        legacy_path = root / "src" / "backtesting.py"

    if not legacy_path.exists():
        print(
            "[ERROR] Cannot locate backtesting.py. "
            "Ensure the file exists at the project root.",
            file=sys.stderr,
        )
        return _EXIT_ERR

    spec = importlib.util.spec_from_file_location("backtesting", legacy_path)
    assert spec is not None and spec.loader is not None  # noqa: S101
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]

    print(f"\nbrazil-election-montecarlo — backtesting")
    print(f"  Year filter : {args.year or 'all'}")
    print(f"  N_SIM       : {args.n_sim:,}\n")

    resultados = module.backtest_completo(year=args.year, n_sim=args.n_sim)

    if not resultados:
        print("No snapshots processed. Add historical CSV files to data/historico/")
        return _EXIT_OK

    module.relatorio_backtesting(resultados)
    return _EXIT_OK


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _print_run_header(args: argparse.Namespace) -> None:
    """Print the simulation run header to stdout.

    Parameters
    ----------
    args:
        Parsed ``run`` namespace.
    """
    line = "=" * 60
    print(line)
    print("  BRAZIL ELECTION MONTE CARLO — 2026")
    print(f"  CSV    : {args.csv}")
    print(f"  N_SIM  : {args.n_sim:,}")
    print(f"  Seed   : {args.seed if args.seed is not None else 'non-deterministic'}")
    print(f"  MCMC   : {'enabled' if args.bayesian else 'disabled'}")
    print(f"  History: {'disabled (--no-history)' if args.no_history else 'enabled'}")
    print(line)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> None:
    """Parse arguments and dispatch to the appropriate subcommand handler.

    When no subcommand is given, defaults to ``run`` with all default flags.
    This preserves backward compatibility: ``python -m src`` behaves the same
    as ``python -m src run``.

    Parameters
    ----------
    argv:
        Argument list to parse.  Defaults to ``sys.argv[1:]`` when ``None``.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Default to "run" when no subcommand is provided.
    if args.subcommand is None:
        args.subcommand = "run"
        # Inject defaults for the run subcommand's flags.
        args.csv = _DEFAULT_CSV
        args.n_sim = _DEFAULT_N_SIM
        args.seed = None
        args.bayesian = False
        args.no_history = False

    if args.subcommand == "run":
        sys.exit(_handle_run(args))
    elif args.subcommand == "backtest":
        sys.exit(_handle_backtest(args))
    else:
        parser.print_help()
        sys.exit(_EXIT_ERR)