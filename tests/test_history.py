
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import closing

import numpy as np
import pandas as pd
import pytest

from src.core.config import SimulationResult
from src.io.history import (
    _percentiles,
    _serialize_dict,
    carregar_historico,
    init_db,
    salvar_historico,
)


def _make_result(
    *,
    timestamp: datetime | None = None,
    config=None,
) -> SimulationResult:
    """Build a minimal SimulationResult for history persistence tests."""
    df1 = pd.DataFrame(
        {
            "Lula": [40.0, 42.0, 41.0],
            "Bolsonaro": [35.0, 34.0, 36.0],
            "margem_1t": [5.0, 8.0, 5.0],
        }
    )
    df2 = pd.DataFrame()

    return SimulationResult(
        df1=df1,
        df2=df2,
        pv={"Lula": 0.8, "Bolsonaro": 0.2},
        p2v={"Lula": 0.7, "Bolsonaro": 0.3},
        p2t=0.25,
        info_matchups={"Lula vs Bolsonaro": 0.7},
        info_lim_1t={},
        info_indecisos={},
        margins=np.array([5.0, 8.0, 5.0]),
        timestamp=timestamp or datetime.now(),
        config=config,
        desvio_base=2.0,
    )

def test_init_db_creates_database_and_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "history.db"

    init_db(db_path)

    assert db_path.exists()

    with closing(sqlite3.connect(db_path)) as conn:
        with conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            assert {"schema_version", "forecasts"} <= tables
            assert conn.execute(
                "SELECT version FROM schema_version"
            ).fetchone() == (1,)


def test_init_db_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"

    init_db(db_path)
    init_db(db_path)

    with closing(sqlite3.connect(db_path)) as conn:
        with conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM schema_version"
            ).fetchone()[0] == 1


def test_save_and_load_history_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    init_db(db_path)

    result = _make_result()
    row_id = salvar_historico(result, db_path)

    history = carregar_historico(db_path, days=0)

    assert row_id == 1
    assert len(history) == 1
    assert history.iloc[0]["pv"] == result.pv
    assert history.iloc[0]["p2v"] == result.p2v
    assert history.iloc[0]["info_matchups"] == result.info_matchups
    assert history.iloc[0]["p2t"] == pytest.approx(0.25)
    assert history.iloc[0]["desvio_base"] == pytest.approx(2.0)
    assert pd.api.types.is_datetime64_any_dtype(history["run_at"])
    assert "pv_json" not in history.columns
    assert "p2v_json" not in history.columns
    assert "info_matchups_json" not in history.columns


def test_save_history_requires_initialized_database(tmp_path: Path) -> None:
    db_path = tmp_path / "missing.db"

    with pytest.raises(FileNotFoundError, match="Call init_db"):
        salvar_historico(_make_result(), db_path)


def test_load_history_requires_existing_database(tmp_path: Path) -> None:
    db_path = tmp_path / "missing.db"

    with pytest.raises(FileNotFoundError, match="Run at least one simulation"):
        carregar_historico(db_path)


def test_load_history_returns_empty_dataframe_for_empty_database(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "history.db"
    init_db(db_path)

    history = carregar_historico(db_path)

    assert isinstance(history, pd.DataFrame)
    assert history.empty

def test_load_history_filters_by_days(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    init_db(db_path)

    now = datetime.now()
    salvar_historico(_make_result(timestamp=now - timedelta(days=120)), db_path)
    salvar_historico(_make_result(timestamp=now - timedelta(days=10)), db_path)

    recent = carregar_historico(db_path, days=30)
    all_rows = carregar_historico(db_path, days=0)

    assert len(recent) == 1
    assert len(all_rows) == 2

def test_load_history_orders_rows_by_timestamp(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    init_db(db_path)

    now = datetime.now()
    salvar_historico(_make_result(timestamp=now), db_path)
    salvar_historico(_make_result(timestamp=now - timedelta(days=1)), db_path)

    history = carregar_historico(db_path, days=0)

    assert history["run_at"].is_monotonic_increasing

def test_serialize_dict_handles_numpy_scalars() -> None:
    payload = _serialize_dict(
        {"integer": np.int64(3), "float": np.float64(1.5), "nested": [np.int64(2)]}
    )

    assert json.loads(payload) == {
        "integer": 3,
        "float": 1.5,
        "nested": [2],
    }

def test_percentiles_returns_none_for_empty_array() -> None:
    assert _percentiles(np.array([]), [0.05, 0.5, 0.95]) == [
        None,
        None,
        None,
    ]


def test_percentiles_calculates_requested_quantiles() -> None:
    result = _percentiles(np.array([0.0, 10.0, 20.0]), [0.0, 0.5, 1.0])

    assert result == [0.0, 10.0, 20.0]
