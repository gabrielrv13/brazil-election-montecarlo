"""
src/io/history.py
=================
SQLite persistence for forecast history.

Every simulation run that reaches completion is persisted here via salvar_historico(). The dashboard reads it via carregar_historico() to render the probability-over-time chart — the primary v3.0 feature.

Design constraints
------------------
- df1 and df2 are NOT stored: at 40 000 rows each they are unsuitable for SQLite. Only summary statistics are persisted.
- pv and p2v are stored as JSON blobs. Consumers must not assume a specific scale — callers must pass values in the [0, 1] range. The column names include the suffix _json to make this unambiguous.
- The db file is created on first write; reads on a missing file raise FileNotFoundError rather than silently returning an empty DataFrame, so callers can distinguish "no history yet" from "wrong path".
- All public functions are safe to call concurrently from a single process; SQLite's WAL mode handles reader/writer overlap.

Public API
----------
    init_db(db_path)
    salvar_historico(result, db_path)
    carregar_historico(db_path, days=90) -> pd.DataFrame
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from src.core.config import SimulationResult

logger = logging.getLogger(__name__)

# Increment this when the schema changes in a backward-incompatible way.
_SCHEMA_VERSION = 1

_DDL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS forecasts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at          TEXT    NOT NULL,          -- ISO 8601, e.g. 2026-04-01T08:00:00
    n_sim           INTEGER NOT NULL,
    csv_path        TEXT,
    seed            INTEGER,                   -- NULL when no seed was set
    use_bayesian    INTEGER NOT NULL DEFAULT 0,-- 0 / 1
    election_date   TEXT,                      -- YYYY-MM-DD
    p2t             REAL    NOT NULL,          -- P(second round) in [0, 1]
    pv_json         TEXT    NOT NULL,          -- {"Lula": 0.72, ...}
    p2v_json        TEXT    NOT NULL,          -- {"Lula": 0.85, ...}
    info_matchups_json TEXT,                   -- serialized info_matchups dict
    margins_p5      REAL,
    margins_p50     REAL,
    margins_p95     REAL,
    desvio_base     REAL                       -- from PollData if available via config
);
"""


# ─── PRIVATE HELPERS ──────────────────────────────────────────────────────────

def _connect(db_path: Path) -> sqlite3.Connection:
    """
    Opens a WAL-mode connection to the SQLite database.

    WAL mode allows concurrent reads during a write, which matters when the dashboard and CLI are running simultaneously.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _ensure_schema_version(conn: sqlite3.Connection) -> None:
    """
    Inserts the current schema version if the table is empty.

    Does not perform migrations — version mismatches log a warning so future migration logic can be added without breaking existing DBs.
    """
    row = conn.execute("SELECT version FROM schema_version").fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO schema_version (version) VALUES (?)",
            (_SCHEMA_VERSION,),
        )
    elif row[0] != _SCHEMA_VERSION:
        logger.warning(
            "forecast_history.db schema version %d does not match "
            "expected version %d. Read may return unexpected columns.",
            row[0],
            _SCHEMA_VERSION,
        )


def _serialize_dict(d: dict) -> str:
    """
    Serializes a dict to a compact JSON string.

    numpy floats are cast to Python float for JSON compatibility.
    """
    def _cast(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating, float)):
            return float(obj)
        if isinstance(obj, dict):
            return {k: _cast(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_cast(i) for i in obj]
        return obj

    return json.dumps(_cast(d), ensure_ascii=False, separators=(",", ":"))


def _percentiles(arr: np.ndarray, qs: list[float]) -> list[float | None]:
    """
    Returns percentiles of arr, or [None, None, None] for empty arrays.
    """
    if arr is None or len(arr) == 0:
        return [None] * len(qs)
    return [float(np.percentile(arr, q * 100)) for q in qs]


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def init_db(db_path: Path) -> None:
    """
    Creates the forecasts table (and schema_version) if they do not exist.

    Safe to call on every application start — uses CREATE TABLE IF NOT EXISTS.
    Creates parent directories if they are absent.

    Args:
        db_path: Path to the SQLite file (e.g. Path("outputs/forecast_history.db")).
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with _connect(db_path) as conn:
        conn.executescript(_DDL)
        _ensure_schema_version(conn)

    logger.info("Database ready: %s", db_path)


def salvar_historico(result: SimulationResult, db_path: Path) -> int:
    """
    Serializes a SimulationResult and inserts one row into forecasts.

    Only summary statistics are stored — df1 and df2 are not persisted.
    The caller is responsible for calling init_db() at least once before calling this function.

    Args:
        result:  Completed SimulationResult. result.config may be None
                 for results produced outside the v3 CLI.
        db_path: Path to the SQLite file produced by init_db().

    Returns:
        The rowid of the inserted row.

    Raises:
        FileNotFoundError: If db_path does not exist (init_db not called).
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found: {db_path}. Call init_db(db_path) first."
        )

    cfg = result.config
    p5, p50, p95 = _percentiles(result.margins, [0.05, 0.50, 0.95])

    row = {
        "run_at":             result.timestamp.isoformat(timespec="seconds"),
        "n_sim":              cfg.n_sim if cfg else len(result.df1),
        "csv_path":           str(cfg.csv_path) if cfg else None,
        "seed":               cfg.seed if cfg else None,
        "use_bayesian":       int(cfg.use_bayesian) if cfg else 0,
        "election_date":      cfg.election_date.isoformat() if cfg else None,
        "p2t":                float(result.p2t),
        "pv_json":            _serialize_dict(result.pv),
        "p2v_json":           _serialize_dict(result.p2v),
        "info_matchups_json": _serialize_dict(result.info_matchups)
                              if result.info_matchups else None,
        "margins_p5":         p5,
        "margins_p50":        p50,
        "margins_p95":        p95,
        "desvio_base":        cfg.csv_path and None,  # populated below
    }

    # desvio_base is not on SimulationResult directly; it lives on PollData.
    # If the CLI passes it through config.scenario_overrides or another field,
    # retrieve it here. For now it remains NULL until the contract is extended.
    # TODO: expose desvio_base on SimulationResult in a follow-up task.

    sql = """
        INSERT INTO forecasts (
            run_at, n_sim, csv_path, seed, use_bayesian, election_date,
            p2t, pv_json, p2v_json, info_matchups_json,
            margins_p5, margins_p50, margins_p95, desvio_base
        ) VALUES (
            :run_at, :n_sim, :csv_path, :seed, :use_bayesian, :election_date,
            :p2t, :pv_json, :p2v_json, :info_matchups_json,
            :margins_p5, :margins_p50, :margins_p95, :desvio_base
        )
    """
    with _connect(db_path) as conn:
        cursor = conn.execute(sql, row)
        rowid = cursor.lastrowid

    logger.info(
        "Forecast saved: id=%d run_at=%s p2t=%.1f%%",
        rowid,
        row["run_at"],
        result.p2t * 100,
    )
    return rowid


def carregar_historico(db_path: Path, days: int = 90) -> pd.DataFrame:
    """
    Returns forecast rows from the last N days as a DataFrame.

    Each row corresponds to one simulation run. The pv and p2v columns are returned as dicts (deserialized from JSON), not as raw strings.

    Columns returned
    ----------------
    id, run_at (datetime), n_sim, csv_path, seed, use_bayesian,
    election_date, p2t, pv (dict), p2v (dict), info_matchups (dict),
    margins_p5, margins_p50, margins_p95, desvio_base

    Args:
        db_path: Path to the SQLite file.
        days:    Window in calendar days from now (default 90).
                 Pass days=0 to return all rows.

    Returns:
        DataFrame sorted by run_at ascending. Empty DataFrame if the
        table exists but has no rows in the requested window.

    Raises:
        FileNotFoundError: If db_path does not exist.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found: {db_path}. "
            "Run at least one simulation to create it."
        )

    if days > 0:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
        sql = "SELECT * FROM forecasts WHERE run_at >= ? ORDER BY run_at ASC"
        params: tuple = (cutoff,)
    else:
        sql = "SELECT * FROM forecasts ORDER BY run_at ASC"
        params = ()

    with _connect(db_path) as conn:
        df = pd.read_sql_query(sql, conn, params=params)

    if df.empty:
        return df

    # Deserialize JSON columns to Python dicts
    df["run_at"] = pd.to_datetime(df["run_at"])
    df["pv"]     = df["pv_json"].apply(json.loads)
    df["p2v"]    = df["p2v_json"].apply(json.loads)
    df["info_matchups"] = df["info_matchups_json"].apply(
        lambda x: json.loads(x) if x else {}
    )

    # Drop raw JSON strings — consumers use the dict columns
    df = df.drop(columns=["pv_json", "p2v_json", "info_matchups_json"])

    logger.debug("Loaded %d forecast rows (last %d days)", len(df), days)
    return df