"""
tests/test_loader.py
====================
Unit tests for src/io/loader.py — carregar_pesquisas().

All tests use fixtures from tests/fixtures/ or construct CSVs inline via
tmp_path. No test reads from data/pesquisas.csv.

Tested behaviors:
    - Missing required column  → ValueError naming the absent column
    - intencao_voto_pct = 0    → ValueError after aggregation
    - Wrong file encoding       → raises (ValueError or UnicodeDecodeError)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.io.loader import carregar_pesquisas


class TestCarregarPesquisas:
    """Tests for carregar_pesquisas(csv_path) → PollData."""

    # -- Missing required column ----------------------------------------------

    def test_missing_intencao_voto_raises_value_error(
        self, csv_missing_column: Path
    ) -> None:
        """CSV without intencao_voto_pct must raise ValueError.

        The error message must name the missing column so the caller knows
        exactly what to fix in the data file.
        """
        with pytest.raises(ValueError, match="intencao_voto_pct"):
            carregar_pesquisas(csv_missing_column)

    def test_missing_column_error_names_the_column(
        self, tmp_path: Path
    ) -> None:
        """A CSV missing desvio_padrao_pct must name that column in the error."""
        csv = tmp_path / "missing_desvio.csv"
        csv.write_text(
            "candidato,intencao_voto_pct\n"
            "Lula,38.0\n"
            "Bolsonaro,30.0\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="desvio_padrao_pct"):
            carregar_pesquisas(csv)

    def test_missing_candidato_column_raises_value_error(
        self, tmp_path: Path
    ) -> None:
        """A CSV missing the candidato column must raise ValueError."""
        csv = tmp_path / "missing_candidato.csv"
        csv.write_text(
            "intencao_voto_pct,desvio_padrao_pct\n"
            "38.0,2.0\n"
            "30.0,2.0\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError):
            carregar_pesquisas(csv)

    # -- Zero / invalid vote share --------------------------------------------

    def test_zero_vote_share_raises_value_error(
        self, csv_zero_vote: Path
    ) -> None:
        """A candidate with intencao_voto_pct = 0 must raise ValueError.

        A zero alpha breaks the Dirichlet distribution used in simulation.
        The loader must catch this before the simulation ever runs.
        """
        with pytest.raises(ValueError):
            carregar_pesquisas(csv_zero_vote)

    def test_zero_vote_error_mentions_candidate(
        self, csv_zero_vote: Path
    ) -> None:
        """The ValueError for a zero-vote candidate must mention the candidate
        name or describe the problem clearly enough to be actionable."""
        with pytest.raises(ValueError, match=r"[Ii]nvalid|zero|0|Bolsonaro"):
            carregar_pesquisas(csv_zero_vote)

    def test_partial_second_poll_is_rejected_even_with_positive_average(
        self, tmp_path: Path
    ) -> None:
        """A second poll with only one candidate is incomplete."""
        csv = tmp_path / "zero_in_one_poll.csv"
        csv.write_text(
            "candidato,intencao_voto_pct,rejeicao_pct,"
            "desvio_padrao_pct,instituto,data\n"
            "Lula,38.0,42.0,2.0,Datafolha,2026-10-01\n"
            "Bolsonaro,0.0,48.0,2.0,Datafolha,2026-10-01\n"
            "Bolsonaro,5.0,47.0,2.0,Quaest,2026-10-03\n"
            "Ciro,8.0,30.0,2.5,Datafolha,2026-10-01\n"
            "Simone,6.0,25.0,2.5,Datafolha,2026-10-01\n"
            "Outros,8.0,0.0,3.0,Datafolha,2026-10-01\n",
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="Incomplete poll"):
            carregar_pesquisas(csv)

    def test_latin1_encoded_csv_raises(self, tmp_path: Path) -> None:
        """A CSV saved as Latin-1 with non-ASCII characters must not parse
        silently into corrupted data.

        Expected: raises UnicodeDecodeError or ValueError — any exception is
        acceptable as long as the function does not return corrupt PollData.

        Rationale: candidate names like 'Flávio' or 'Renán' contain non-ASCII
        code points that Latin-1 encodes differently from UTF-8. Silently
        reading them would produce wrong candidate names downstream without
        any warning, corrupting the simulation silently.
        """
        csv = tmp_path / "latin1.csv"
        # Write valid CSV content as Latin-1 (byte 0xe1 = 'á' in Latin-1,
        # invalid as UTF-8 start byte in this position)
        latin1_content = (
            "candidato,intencao_voto_pct,desvio_padrao_pct\r\n"
            "Fl\xe1vio,30.0,2.0\r\n"   # 'á' as raw Latin-1 byte
            "Lula,38.0,2.0\r\n"
        )
        csv.write_bytes(latin1_content.encode("latin-1"))

        with pytest.raises((UnicodeDecodeError, ValueError)):
            carregar_pesquisas(csv)

    # -- File not found -------------------------------------------------------

    def test_nonexistent_file_raises_file_not_found(
        self, tmp_path: Path
    ) -> None:
        """A path that does not exist must raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            carregar_pesquisas(tmp_path / "does_not_exist.csv")

    # -- Happy path (smoke) ---------------------------------------------------

    def test_minimal_csv_loads_without_error(self, csv_minimal: Path) -> None:
        """The minimal fixture must load without raising any exception."""
        from src.io.loader import load_polls
        from src.core.config import SimulationConfig
        result = load_polls(SimulationConfig(csv_path=csv_minimal, required_candidates=("Lula", "Bolsonaro")))
        assert result is not None

    def test_undated_single_poll_csv_is_rejected(
        self, csv_single_poll: Path
    ) -> None:
        """Undated legacy CSVs now require an explicit source date."""
        with pytest.raises(ValueError, match="missing data"):
            carregar_pesquisas(csv_single_poll)

    def test_no_rejeicao_csv_loads_without_error(
        self, csv_no_rejeicao: Path
    ) -> None:
        """CSV without the optional rejeicao_pct column must load cleanly."""
        from src.io.loader import load_polls
        from src.core.config import SimulationConfig
        result = load_polls(SimulationConfig(csv_path=csv_no_rejeicao, required_candidates=("Lula", "Bolsonaro")))
        assert result is not None