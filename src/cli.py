"""
Single canonical CLI entry point for brazil-election-montecarlo.

All public interfaces are stable across v3 sprints.  The implementation of
each subcommand handler will be swapped out as core modules are delivered:

    Sprint 1  — Argument structure only; handlers were compatibility bridges
                 to the v2 scripts (removed in v3) and backtesting.py.
    Sprint 2  — _handle_run() wired to src.core.simulation + src.io.loader.
    Sprint 3  — --no-history flag respected; src.io.history.salvar_historico
                 called at the end of every run.
    Sprint 4  — Legacy scripts deprecated; MIGRATION.md published.

Usage
-----
    python -m src                           # run simulation (default)
    python -m src run                       # explicit subcommand
    python -m src run --n-sim 200000        # tail-probability markets
    python -m src run --bayesian            # rejected: no validated MCMC path
    python -m src run --no-history          # skip SQLite persistence (CI)
    python -m src run --csv data/alt.csv    # alternative poll CSV
    python -m src run --seed 42             # reproducible run
    python -m src backtest                  # 2018 + 2022 snapshots
    python -m src backtest --year 2022      # single election year
    python -m src backtest --n-sim 40000    # override iterations
"""

from __future__ import annotations

import argparse
from datetime import date
import sys
import pandas as pd
from pathlib import Path
from typing import Sequence

from src.core.config import SimulationConfig
from src.io import load_polls
from src.io.report import generate_pdf, save_csvs

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
  python -m src run --bayesian             rejected (no validated MCMC path)
  python -m src run --no-history           skip SQLite history (CI mode)
  python -m src run --csv data/alt.csv     use alternative poll file
  python -m src runoff --as-of 2026-10-24  standalone second round (core engine)
  python -m src backtest --year 2022       backtest against 2022 election
  python -m src backtest --n-sim 40000     override iterations for backtest
        """,
    )

    subparsers = parser.add_subparsers(
        dest="subcommand",
        metavar="SUBCOMMAND",
    )

    _add_run_subparser(subparsers)
    _add_runoff_subparser(subparsers)
    _add_backtest_subparser(subparsers)

    return parser


def _add_runoff_subparser(subparsers) -> None:
    """Register the ``runoff`` subcommand (standalone second round)."""
    from src.core.config import RunoffConfig  # noqa: PLC0415

    d = RunoffConfig()
    p = subparsers.add_parser(
        "runoff",
        help="Standalone second round between the two finalists (core engine).",
        description=(
            "Aggregate runoff polls on the two-party share (house effects, "
            "detrended outliers), simulate with the common election error, and "
            "write the summary, CSV, chart and manifest used by publicar_2turno.py."
        ),
    )
    p.add_argument("--csv", type=Path, default=d.csv_path, metavar="PATH",
                   help=f"Runoff poll CSV. Default: {d.csv_path}")
    p.add_argument("--n-sim", type=int, default=d.n_sim, metavar="N")
    p.add_argument("--seed", type=int, default=None, metavar="INT",
                   help="Random seed (drawn and recorded when omitted).")
    p.add_argument("--as-of", type=date.fromisoformat, default=None, metavar="YYYY-MM-DD",
                   help="Reference date for poll validation, weights and horizon.")
    p.add_argument("--data-min", type=date.fromisoformat, default=None, metavar="YYYY-MM-DD",
                   help="First poll day used (default: the day after the first round).")
    p.add_argument("--tau", type=float, default=d.tau_dias, help="Recency time constant (days).")
    p.add_argument("--sd-erro-comum", type=float, default=d.sd_erro_comum_pp, metavar="PP")
    p.add_argument("--gl-erro-comum", type=float, default=d.gl_erro_comum, metavar="NU")
    p.add_argument("--sd-deriva", type=float, default=d.sd_deriva_30d_pp, metavar="PP")
    p.add_argument("--sem-efeito-instituto", action="store_true", default=False)
    p.add_argument("--vies", type=float, default=0.0, metavar="PP",
                   help="Bias scenario: shift toward --vies-candidato (pp).")
    p.add_argument("--vies-candidato", default=None, metavar="NOME")
    p.add_argument("--usar-teto", action="store_true", default=False,
                   help="Apply the rejection ceiling (off by default in a binary race).")
    p.add_argument("--saida", type=Path, default=Path("outputs"), metavar="DIR")


def _handle_runoff(args: argparse.Namespace) -> int:
    """Run the standalone runoff on the core engine; 0 on success, 1 on error."""
    from src.core.config import RunoffConfig  # noqa: PLC0415

    if not args.csv.exists():
        print(f"[ERROR] Runoff poll CSV not found: {args.csv}", file=sys.stderr)
        return _EXIT_ERR
    if args.seed is None:
        import secrets  # noqa: PLC0415
        args.seed = secrets.randbelow(2**31)
    try:
        config = RunoffConfig(
            csv_path=args.csv, n_sim=args.n_sim, seed=args.seed, as_of=args.as_of,
            data_min=args.data_min, tau_dias=args.tau,
            efeitos_instituto=not args.sem_efeito_instituto,
            sd_erro_comum_pp=args.sd_erro_comum, gl_erro_comum=args.gl_erro_comum,
            sd_deriva_30d_pp=args.sd_deriva, vies_pp=args.vies,
            vies_candidato=args.vies_candidato, usar_teto=args.usar_teto,
        )
        resumo = _run_runoff_pipeline(config, args.saida)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return _EXIT_ERR
    print(f"\n{resumo['cand_a']} {resumo['p_vitoria_a']:.1f}% | "
          f"{resumo['cand_b']} {resumo['p_vitoria_b']:.1f}%  "
          f"(share of {resumo['cand_a']}: {resumo['fatia_a']:.2f}%, "
          f"IC90 {resumo['fatia_a_ic90']})")
    print(f"Results in {args.saida}/ (resumo_2turno.json + manifest)")
    return _EXIT_OK


def _run_runoff_pipeline(config, output_dir: Path) -> dict:
    """Load → simulate → summary/CSV/chart → manifest. Returns the summary."""
    import json  # noqa: PLC0415
    import math  # noqa: PLC0415

    import numpy as np  # noqa: PLC0415

    from src.core.runoff import (  # noqa: PLC0415
        resolver_vies,
        sd_deriva_runoff,
        simular_runoff,
        tabela_sensibilidade_runoff,
    )
    from src.io.manifest import caminho_manifesto, criar_manifesto, salvar_manifesto  # noqa: PLC0415
    from src.io.runoff import carregar_runoff, salvar_resumo  # noqa: PLC0415
    from src.viz.runoff import plot_runoff  # noqa: PLC0415

    referencia = config.as_of or date.today()
    ag = carregar_runoff(config)
    candidato_vies = config.vies_candidato or ag.cand_a
    vies_a = resolver_vies(ag.cand_a, ag.cand_b, candidato_vies, config.vies_pp)
    deriva = sd_deriva_runoff(config.sd_deriva_30d_pp, config.runoff_date, referencia)
    rng = np.random.default_rng(config.seed)
    df = simular_runoff(ag, config.n_sim, rng, config.sd_erro_comum_pp,
                        config.gl_erro_comum, deriva, vies_a, config.usar_teto)
    tabela = tabela_sensibilidade_runoff(ag, seed=config.seed, gl_comum=config.gl_erro_comum,
                                         sd_deriva_pp=deriva)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "resultados_2turno_standalone.csv"
    df.to_csv(csv_path, index=False)
    params = {
        # Effective sd of the simulated share (gate and sensitivity column).
        "sd_fatia_pp": round(math.sqrt(config.sd_erro_comum_pp**2 + ag.sd_media**2 + deriva**2), 3),
        "vies_pp_a": vies_a, "vies_candidato": candidato_vies, "vies_pp": config.vies_pp,
        "tau": config.tau_dias, "data_min": config.janela_inicio.isoformat(),
        "modelo": "core_v3", "sd_erro_comum_pp": config.sd_erro_comum_pp,
        "gl_erro_comum": config.gl_erro_comum, "sd_deriva_pp": round(deriva, 3),
        "sd_media_pp": round(ag.sd_media, 3), "efeitos_instituto": config.efeitos_instituto,
        "as_of": referencia.isoformat(),
    }
    resumo_path = salvar_resumo(output_dir / "resumo_2turno.json", df, ag.cand_a, ag.cand_b,
                                ag.fatia_a, params, ag.info, tabela)
    p_a = float((df["vencedor"] == ag.cand_a).mean() * 100)
    png = plot_runoff(df, ag.cand_a, ag.cand_b, p_a, 100 - p_a,
                      output_dir / "simulacao_2turno.png",
                      data_2t=config.runoff_date, data_referencia=referencia)
    manifesto = criar_manifesto(
        "segundo_turno", [config.csv_path], [resumo_path, csv_path, png],
        {**params, "csv_path": config.csv_path, "usar_teto": config.usar_teto},
        as_of=referencia, seed=config.seed, n_sim=config.n_sim,
    )
    salvar_manifesto(manifesto, caminho_manifesto(resumo_path))
    return json.loads(resumo_path.read_text(encoding="utf-8"))


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
        "--as-of", type=date.fromisoformat, default=None, metavar="YYYY-MM-DD",
        help="Reference date for poll validation, weighting and simulation horizon.",
    )
    _err = SimulationConfig()
    run_parser.add_argument(
        "--sd-erro-comum", type=float, default=_err.sd_erro_comum_pp, metavar="PP",
        help=("sd (pp, candidate at 50%%) of the election-level polling error shared "
              f"by all polls. Prior until calibrated. Default: {_err.sd_erro_comum_pp}."),
    )
    run_parser.add_argument(
        "--gl-erro-comum", type=float, default=_err.gl_erro_comum, metavar="NU",
        help=("Degrees of freedom of the heavy-tailed common error (> 2; 'inf' for "
              f"Normal-like tails). Default: {_err.gl_erro_comum}."),
    )
    run_parser.add_argument(
        "--sd-deriva", type=float, default=_err.sd_deriva_30d_pp, metavar="PP",
        help=("Opinion drift until election day, sd in pp per sqrt(30 days). "
              f"Default: {_err.sd_deriva_30d_pp}."),
    )
    run_parser.add_argument(
        "--sem-efeito-instituto", action="store_true", default=False,
        help="Disable the house-effect adjustment of the poll aggregator.",
    )
    run_parser.add_argument(
        "--cenario", dest="scenario", default=None,
        help="Select one scenario from the poll CSV.",
    )
    run_parser.add_argument(
        "--candidato-necessario", action="append", dest="required_candidates",
        help="Candidate required in this simulation scenario (repeatable).",
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
            "Reserved. The MCMC path has no validated implementation yet, "
            "so this flag is rejected instead of silently running the "
            "Dirichlet engine."
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

    if getattr(args, "bayesian", False):
        errors.append(
            "--bayesian is not available: the MCMC model has no likelihood "
            "and is not wired into the engine. Run without --bayesian."
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
    """Execute the full simulation pipeline for the ``run`` subcommand.

    Orchestration order:
        1. Build SimulationConfig from CLI args
        2. load_polls(config)           → PollData          [src.io.loader]
        3. simulate(config, poll_data)  → SimulationResult  [src.core.simulation]
        4. save_history(result)         → None              [src.io.history]
        5. generate_charts(result)      → None              [src.io.report]
        6. generate_report(result)      → None              [src.io.report]

    Steps 4–6 are skipped or no-ops when the relevant flag is set (e.g.
    ``--no-history``) or when the output module is not yet wired (Sprint 3).

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

    config = _build_simulation_config(args)

    try:
        return _run_pipeline(config, args)
    except FileNotFoundError as exc:
        print(f"[ERROR] File not found: {exc}", file=sys.stderr)
        return _EXIT_ERR
    except ValueError as exc:
        # No stack trace — message from loader/validator is already descriptive.
        print(f"[ERROR] {exc}", file=sys.stderr)
        return _EXIT_ERR
    except Exception:  # noqa: BLE001
        # Unexpected errors: let the stack trace surface for diagnosis.
        raise

def _build_simulation_config(args: argparse.Namespace) -> SimulationConfig:
    """Translate parsed CLI arguments into a ``SimulationConfig`` dataclass.

    Parameters
    ----------
    args:
        Parsed namespace from the ``run`` subparser.

    Returns
    -------
    SimulationConfig
        Immutable configuration object consumed by the simulation pipeline.
    """
    seed = args.seed
    if seed is None:
        # Draw and record a seed so every run is reproducible from its manifest.
        import secrets  # noqa: PLC0415
        seed = secrets.randbelow(2**31)
        args.seed = seed
    return SimulationConfig(
        csv_path=args.csv,
        n_sim=args.n_sim,
        seed=seed,
        use_bayesian=args.bayesian,
        as_of=args.as_of,
        sd_erro_comum_pp=getattr(args, "sd_erro_comum", SimulationConfig.sd_erro_comum_pp),
        gl_erro_comum=getattr(args, "gl_erro_comum", SimulationConfig.gl_erro_comum),
        sd_deriva_30d_pp=getattr(args, "sd_deriva", SimulationConfig.sd_deriva_30d_pp),
        efeitos_instituto=not getattr(args, "sem_efeito_instituto", False),
        scenario=args.scenario,
        required_candidates=tuple(args.required_candidates) if args.required_candidates else None,
    )


def _run_pipeline(config: SimulationConfig, args: argparse.Namespace) -> int:
    """Execute the ordered simulation pipeline given a resolved config.

    Separated from ``_handle_run`` so that each stage can be tested
    independently without re-parsing CLI arguments.

    Parameters
    ----------
    config:
        Fully-resolved ``SimulationConfig`` instance.
    args:
        Original parsed namespace, used only for the ``--no-history`` flag.

    Returns
    -------
    int
        Exit code: 0 on success.
    """
    # Stage 1 — Load polls.
    # ValueError raised here if CSV schema is invalid (missing column,
    # non-positive vote share, etc.).  The caller catches it without traceback.
    print("[1/4] Loading polls...", flush=True)
    poll_data = load_polls(config)

    # Stage 2 — Run Monte Carlo simulation.
    print("[2/4] Running simulation...", flush=True)
    result = _run_simulation(config, poll_data)

    # Stage 3 — Persist to SQLite history (skipped with --no-history).
    # Import errors are real failures now that the module exists; they are no
    # longer masked as a pending sprint (audit A11).
    if args.no_history:
        print("[3/4] Skipping history (--no-history).", flush=True)
    else:
        from src.io.history import save_history  # noqa: PLC0415
        print("[3/4] Saving to forecast history...", flush=True)
        save_history(result)

    # Stage 4 — Generate outputs (charts + PDF/CSV report) and the manifest.
    print("[4/4] Generating outputs...", flush=True)

    output_dir = Path("outputs")
    saidas: list[Path] = []

    from src.viz.charts import generate_charts  # noqa: PLC0415
    saidas.extend(generate_charts(result, output_dir=output_dir).values())

    saidas.extend(p for p in save_csvs(result, output_dir=output_dir) if p is not None)
    try:
        saidas.append(generate_pdf(result, output_dir=output_dir))
    except ImportError as exc:
        print(f"         [WARN] PDF skipped: {exc}", flush=True)

    manifesto = _write_manifest(config, result, saidas, output_dir)
    print(f"\nSimulation completed. Results in outputs/ (manifest: {manifesto.name})")
    return _EXIT_OK


def _write_manifest(config: SimulationConfig, result, saidas: list[Path], output_dir: Path) -> Path:
    """Record inputs, parameters, seed and output hashes of this run."""
    from dataclasses import fields  # noqa: PLC0415

    from src.io.manifest import criar_manifesto, salvar_manifesto  # noqa: PLC0415

    referencia = config.as_of or date.today()
    parametros = {
        f.name: getattr(config, f.name) for f in fields(config)
        if f.name not in ("csv_path", "seed", "n_sim", "as_of", "scenario_overrides")
    }
    parametros["desvio_base"] = float(getattr(result, "desvio_base", 0.0))
    stamp = result.timestamp.strftime("%Y-%m-%dT%H-%M-%S")
    # save_csvs also writes the event-probability table under the same stamp.
    probabilidades = output_dir / f"{stamp}_probabilidades.csv"
    if probabilidades.exists() and probabilidades not in saidas:
        saidas = [*saidas, probabilidades]
    manifesto = criar_manifesto(
        "primeiro_turno", [config.csv_path], saidas, parametros,
        as_of=referencia, seed=config.seed, n_sim=config.n_sim,
    )
    return salvar_manifesto(manifesto, output_dir / f"{stamp}_manifest.json")


def _run_simulation(
    config: SimulationConfig,
    poll_data,  # PollData — typed loosely to avoid circular import at module level
) -> object:  # SimulationResult
    """Invoke the simulation engine and return a ``SimulationResult``.

    Delegates to ``src.core.pipeline.montar_resultado``: first round plus
    the dynamic runoff between each draw's actual top two.

    Parameters
    ----------
    config:
        Resolved simulation configuration.
    poll_data:
        ``PollData`` instance returned by ``load_polls``.

    Returns
    -------
    SimulationResult
        Populated result dataclass consumed by downstream output stages.
    """
    from src.core.pipeline import montar_resultado  # noqa: PLC0415

    result = montar_resultado(config, poll_data)

    print("First-round event probabilities (contract v2):")
    for cand in result.p_lideranca:
        print(f"  {cand}: leadership={result.p_lideranca[cand]:.2%}; "
              f"direct victory (>50% valid)={result.p_vitoria_1t[cand]:.2%}; "
              f"runoff qualification={result.p_classificacao_2t[cand]:.2%}")
    print(f"  Second round occurs: {result.p2t:.2%}")
    if result.p2v:
        print("Runoff victory, conditional on a runoff (dynamic top two):")
        for cand, prob in sorted(result.p2v.items(), key=lambda x: -x[1]):
            print(f"  {cand}: {prob:.2%}")
    return result


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
        # Re-parse as "run" so every run flag gets its declared default
        # (injecting a hand-picked subset missed as_of, scenario, etc.).
        args = parser.parse_args(["run"])

    if args.subcommand == "run":
        sys.exit(_handle_run(args))
    elif args.subcommand == "runoff":
        sys.exit(_handle_runoff(args))
    elif args.subcommand == "backtest":
        sys.exit(_handle_backtest(args))
    else:
        parser.print_help()
        sys.exit(_EXIT_ERR)
