"""
tests/conftest.py
=================
Shared pytest fixtures for the brazil-election-montecarlo test suite.

Design principles:
- No fixture reads from data/. All data is either inline or from tests/fixtures/.
- Fixtures that do not touch disk are marked so callers know they are pure.
- Simulation-output DataFrames (df1_stub) are constructed programmatically to
  decouple unit tests of consumers (polymarket_edge, charts) from the simulation
  engine itself.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Fixture directory
# ---------------------------------------------------------------------------

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fixture_dir() -> Path:
    """Return the absolute path to tests/fixtures/.

    Use this fixture instead of hard-coding relative paths in test files so
    that tests are location-independent.
    """
    return FIXTURE_DIR


# ---------------------------------------------------------------------------
# CSV path fixtures (no I/O — just resolve paths)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def csv_minimal(fixture_dir: Path) -> Path:
    """Path to the main happy-path fixture: multiple polls, all optional columns."""
    return fixture_dir / "pesquisas_minimal.csv"


@pytest.fixture(scope="session")
def csv_single_poll(fixture_dir: Path) -> Path:
    """Path to the backward-compatible single-poll-per-candidate fixture."""
    return fixture_dir / "pesquisas_single_poll.csv"


@pytest.fixture(scope="session")
def csv_missing_column(fixture_dir: Path) -> Path:
    """Path to the fixture that is missing the required intencao_voto_pct column."""
    return fixture_dir / "pesquisas_missing_column.csv"


@pytest.fixture(scope="session")
def csv_zero_vote(fixture_dir: Path) -> Path:
    """Path to the fixture where Bolsonaro has intencao_voto_pct = 0."""
    return fixture_dir / "pesquisas_zero_vote.csv"


@pytest.fixture(scope="session")
def csv_no_rejeicao(fixture_dir: Path) -> Path:
    """Path to the fixture without the optional rejeicao_pct column."""
    return fixture_dir / "pesquisas_no_rejeicao.csv"


@pytest.fixture(scope="session")
def csv_outlier(fixture_dir: Path) -> Path:
    """Path to the fixture with a clear outlier poll for Lula (62% among 37–38%)."""
    return fixture_dir / "pesquisas_outlier.csv"


@pytest.fixture(scope="session")
def csv_2turno_minimal(fixture_dir: Path) -> Path:
    """Path to the second-round fixture with exactly 2 candidates."""
    return fixture_dir / "pesquisas_2turno_minimal.csv"


@pytest.fixture(scope="session")
def csv_snapshot_historico(fixture_dir: Path) -> Path:
    """Path to the historical snapshot fixture used by backtesting tests."""
    return fixture_dir / "snapshot_historico_minimal.csv"


# ---------------------------------------------------------------------------
# In-memory DataFrame fixtures (pure — no disk I/O)
# ---------------------------------------------------------------------------

@pytest.fixture
def df_pesquisas_minimal() -> pd.DataFrame:
    """In-memory equivalent of pesquisas_minimal.csv.

    Two polls each for Lula and Bolsonaro; one poll for Outros.
    Suitable for unit-testing aggregation functions without touching disk.
    """
    return pd.DataFrame(
        {
            "candidato":        ["Lula", "Lula", "Bolsonaro", "Bolsonaro", "Outros"],
            "intencao_voto_pct":[38.0,   36.0,   30.0,        31.0,        12.0  ],
            "rejeicao_pct":     [42.0,   43.0,   48.0,        47.0,        20.0  ],
            "desvio_padrao_pct":[2.0,    2.0,    2.0,         2.0,         3.0   ],
            "indecisos_pct":    [10.0,   11.0,   10.0,        11.0,        10.0  ],
            "instituto":        ["Datafolha", "Quaest", "Datafolha", "Quaest", "Datafolha"],
            "data": pd.to_datetime(
                ["2026-02-01", "2026-02-08", "2026-02-01", "2026-02-08", "2026-02-01"]
            ).date,
        }
    )


@pytest.fixture
def df_candidato_lula_dois_polls() -> pd.DataFrame:
    """Single-candidate DataFrame for Lula with two polls.

    Used by tests of agregar_pesquisas_candidato() that need a clean
    multi-poll input with no outlier.
    """
    return pd.DataFrame(
        {
            "candidato":        ["Lula", "Lula"],
            "intencao_voto_pct":[38.0,   36.0  ],
            "rejeicao_pct":     [42.0,   43.0  ],
            "desvio_padrao_pct":[2.0,    2.0   ],
            "instituto":        ["Datafolha", "Quaest"],
            "data": pd.to_datetime(["2026-02-01", "2026-02-08"]).date,
        }
    )


@pytest.fixture
def df_candidato_tres_polls_com_outlier() -> pd.DataFrame:
    """Single-candidate DataFrame with a clear outlier in the third poll (62%).

    The first two polls cluster at 37–38%; the third at 62% is a clear outlier
    (modified z-score > 2.5). detectar_outliers() must flag index 2.
    """
    return pd.DataFrame(
        {
            "candidato":        ["Lula", "Lula", "Lula"  ],
            "intencao_voto_pct":[38.0,   37.0,   62.0   ],
            "rejeicao_pct":     [42.0,   42.0,   42.0   ],
            "desvio_padrao_pct":[2.0,    2.0,    2.0    ],
            "instituto":        ["Datafolha", "Quaest", "OutlierInstitute"],
            "data": pd.to_datetime(
                ["2026-02-01", "2026-02-08", "2026-02-15"]
            ).date,
        }
    )


@pytest.fixture
def df_candidato_poll_unico() -> pd.DataFrame:
    """Single-candidate DataFrame with exactly one poll.

    agregar_pesquisas_candidato() must return the raw values unchanged
    (no aggregation, desvio_entre = 0).
    """
    return pd.DataFrame(
        {
            "candidato":        ["Bolsonaro"],
            "intencao_voto_pct":[30.0     ],
            "rejeicao_pct":     [48.0     ],
            "desvio_padrao_pct":[2.0      ],
            "instituto":        ["Datafolha"],
            "data": pd.to_datetime(["2026-02-01"]).date,
        }
    )


# ---------------------------------------------------------------------------
# Simulation-output stub (df1) for polymarket_edge() tests
# ---------------------------------------------------------------------------

@pytest.fixture
def df1_stub() -> pd.DataFrame:
    """Minimal first-round simulation output DataFrame.

    Constructs 1,000 synthetic rows with the columns that polymarket_edge()
    and related consumers expect. Values are drawn from a fixed seed so that
    tests are deterministic without depending on the simulation engine.

    Columns produced:
        Lula, Bolsonaro, Outros          – raw vote shares (sum to 100)
        Lula_val, Bolsonaro_val          – valid (post-ceiling) shares
        vencedor                         – winner per simulation
        tem_2turno                       – bool
        margem_1t                        – unsigned margin (pp)
        lider_1t                         – leading candidate name
        margem_Lula, margem_Bolsonaro    – signed margins
    """
    rng = np.random.default_rng(seed=42)
    n = 1_000

    # Lula wins ~60% of simulations in this stub
    lula_val    = rng.normal(loc=45.0, scale=4.0, size=n).clip(30, 65)
    bolsonaro_val = rng.normal(loc=32.0, scale=3.5, size=n).clip(20, 50)
    outros_val  = 100.0 - lula_val - bolsonaro_val

    # Re-normalize to ensure they sum to exactly 100
    total = lula_val + bolsonaro_val + outros_val
    lula_val      = lula_val      / total * 100
    bolsonaro_val = bolsonaro_val / total * 100
    outros_val    = outros_val    / total * 100

    margem_lula      = lula_val - bolsonaro_val          # signed
    margem_bolsonaro = bolsonaro_val - lula_val          # signed
    margem_1t        = np.abs(margem_lula)               # unsigned gap between 1st and 2nd

    vencedor = np.where(lula_val > bolsonaro_val, "Lula", "Bolsonaro")
    tem_2turno = lula_val < 50

    return pd.DataFrame(
        {
            "Lula":              lula_val,
            "Bolsonaro":         bolsonaro_val,
            "Outros":            outros_val,
            "Lula_val":          lula_val,
            "Bolsonaro_val":     bolsonaro_val,
            "vencedor":          vencedor,
            "tem_2turno":        tem_2turno,
            "margem_1t":         margem_1t,
            "lider_1t":          vencedor,
            "margem_Lula":       margem_lula,
            "margem_Bolsonaro":  margem_bolsonaro,
        }
    )


# ---------------------------------------------------------------------------
# Reference dates
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def reference_date_hoje() -> date:
    """Frozen reference date representing 'today' in tests.

    Using a fixed date makes calcular_peso_temporal() tests deterministic
    regardless of when the test suite runs.
    """
    return date(2026, 3, 7)


@pytest.fixture(scope="session")
def reference_date_2022_snapshot() -> date:
    """Reference date for the 2022 T-14 backtesting snapshot."""
    return date(2022, 10, 2)  # 14 days before 2022-10-16 first round
