from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.core.config import SimulationResult
from src.io.report import (
    _candidate_columns,
    _iso_timestamp,
    _section_first_round,
    _section_second_round,
    _section_undecided,
    _build_table_style,
    generate_pdf,
    save_csvs,
)


@pytest.fixture
def result_completo():
    df1 = pd.DataFrame({
        "Alice": [42.0, 44.0, 46.0, 43.0, 45.0, 41.0, 47.0, 44.0, 43.0, 45.0],
        "Bruno": [35.0, 34.0, 33.0, 36.0, 34.0, 37.0, 32.0, 35.0, 36.0, 34.0],
        "Carla": [23.0, 22.0, 21.0, 21.0, 21.0, 22.0, 21.0, 21.0, 21.0, 21.0],
        "margem_1t": [7.0, 10.0, 13.0, 5.0, 11.0, 4.0, 15.0, 9.0, 6.0, 12.0],
        "vencedor": ["Alice"] * 8 + ["Bruno"] * 2,
        "tem_2turno": [True] * 10,
        "Alice_val": [42, 44, 46, 43, 45, 41, 47, 44, 43, 45],
        "Bruno_val": [35, 34, 33, 36, 34, 37, 32, 35, 36, 34],
        "Carla_val": [23, 22, 21, 21, 21, 22, 21, 21, 21, 21],
        "Alice_abs": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    })

    df2 = pd.DataFrame({
        "Alice": [52.0, 54.0, 51.0, 53.0],
        "Bruno": [48.0, 46.0, 49.0, 47.0],
        "finalista_a": ["Alice"] * 4, "finalista_b": ["Bruno"] * 4,
        "voto_a": [52.,54.,51.,53.], "voto_b": [48.,46.,49.,47.],
        "tem_2turno": [True] * 4,
    })

    return SimulationResult(
        df1=df1,
        df2=df2,
        pv={"Alice": 0.8, "Bruno": 0.2},
        p2v={"Alice": 0.65, "Bruno": 0.35},
        p2t=1.0,
        info_matchups={
            "Alice x Bruno": {
                "cand_a": "Alice",
                "cand_b": "Bruno",
                "n_sims": 70,
                "prob_matchup": 70.0,
                "prob_a": 65.0,
                "prob_b": 35.0,
                "rej_a": 0.2,
                "rej_b": 0.3,
            },
            "Bruno x Carla": {
                "cand_a": "Bruno",
                "cand_b": "Carla",
                "n_sims": 30,
                "prob_matchup": 30.0,
                "prob_a": 55.0,
                "prob_b": 45.0,
                "rej_a": 0.3,
                "rej_b": 0.2,
            },
        },
        info_lim_1t={},
        info_indecisos={
            "indecisos_total": 12.0,
            "indecisos_redistribuiveis": 9.0,
            "indecisos_para_brancos": 3.0,
            "blank_fraction": 0.25,
        },
        margins=np.array([7.0, 10.0, 13.0, 5.0, 11.0, 4.0, 15.0, 9.0, 6.0, 12.0]),
        timestamp=datetime(2026, 10, 21, 12, 30, 45),
    )


def test_candidate_columns_exclude_metadata_and_derived_columns():
    df = pd.DataFrame(columns=[
        "Alice", "Bruno", "vencedor", "tem_2turno",
        "abstencao_1t_pct", "votos_validos_1t", "margem_1t",
        "lider_1t", "Alice_val", "Alice_abs", "margem_extra",
    ])

    assert _candidate_columns(df) == ["Alice", "Bruno"]


def test_iso_timestamp_uses_filesystem_safe_format(result_completo):
    assert _iso_timestamp(result_completo) == "2026-10-21T12-30-45"


def test_save_csvs_writes_both_rounds(tmp_path, result_completo):
    path_1t, path_2t = save_csvs(result_completo, tmp_path / "nested")

    assert path_1t.exists()
    assert path_2t is not None
    assert path_2t.exists()
    assert path_1t.name == "2026-10-21T12-30-45_resultados_1turno.csv"
    assert path_2t.name == "2026-10-21T12-30-45_resultados_2turno.csv"
    assert len(pd.read_csv(path_1t)) == len(result_completo.df1)
    assert len(pd.read_csv(path_2t)) == len(result_completo.df2)


def test_save_csvs_skips_empty_second_round(tmp_path, result_completo):
    result_completo.df2 = pd.DataFrame()

    path_1t, path_2t = save_csvs(result_completo, tmp_path)

    assert path_1t.exists()
    assert path_2t is None
    assert len(list(tmp_path.glob("*_resultados_2turno.csv"))) == 0


def test_build_table_style_returns_reportlab_style():
    from reportlab.platypus import TableStyle

    assert isinstance(_build_table_style(), TableStyle)


def test_undecided_section_is_empty_when_no_data(result_completo):
    result_completo.info_indecisos = {}

    assert _section_undecided(result_completo, {}) == []


def test_undecided_section_is_created_when_data_exists(result_completo):
    from reportlab.lib.styles import getSampleStyleSheet

    story = _section_undecided(
        result_completo, getSampleStyleSheet()
    )

    assert len(story) == 3


def test_first_round_section_with_probabilities_and_margins(result_completo):
    from reportlab.lib.styles import getSampleStyleSheet

    story = _section_first_round(
        result_completo, getSampleStyleSheet()
    )

    assert len(story) == 6


def test_first_round_fallback_candidates_without_probabilities(result_completo):
    from reportlab.lib.styles import getSampleStyleSheet

    result_completo.pv = {}

    story = _section_first_round(
        result_completo, getSampleStyleSheet()
    )

    assert len(story) == 6


def test_first_round_without_margin_column(result_completo):
    from reportlab.lib.styles import getSampleStyleSheet

    result_completo.df1 = result_completo.df1.drop(columns=["margem_1t"])
    story = _section_first_round(
        result_completo, getSampleStyleSheet()
    )

    assert len(story) == 3


def test_second_round_section_is_empty_without_data(result_completo):
    result_completo.df2 = pd.DataFrame()

    assert _section_second_round(result_completo, {}) == []


def test_second_round_section_is_empty_without_matchups(result_completo):
    result_completo.info_matchups = {}

    assert _section_second_round(result_completo, {}) == []


def test_second_round_section_with_matchups_and_probabilities(result_completo):
    from reportlab.lib.styles import getSampleStyleSheet

    story = _section_second_round(
        result_completo, getSampleStyleSheet()
    )

    assert len(story) >= 4


def test_second_round_section_without_overall_probabilities(result_completo):
    from reportlab.lib.styles import getSampleStyleSheet

    result_completo.p2v = {}

    story = _section_second_round(
        result_completo, getSampleStyleSheet()
    )

    assert len(story) >= 3


def test_generate_pdf_creates_valid_pdf(tmp_path, result_completo):
    path = generate_pdf(result_completo, tmp_path)

    assert path.exists()
    assert path.suffix == ".pdf"
    assert path.stat().st_size > 0

    with path.open("rb") as file:
        assert file.read(5) == b"%PDF-"


def test_generate_pdf_without_config_and_optional_sections(tmp_path, result_completo):
    result_completo.config = None
    result_completo.df2 = pd.DataFrame()
    result_completo.info_matchups = {}
    result_completo.info_indecisos = {}

    path = generate_pdf(result_completo, tmp_path)

    assert path.exists()
    assert path.stat().st_size > 0


def test_first_round_skips_candidate_missing_from_dataframe(result_completo):
    from reportlab.lib.styles import getSampleStyleSheet

    result_completo.pv["Candidato ausente"] = 0.1

    story = _section_first_round(
        result_completo, getSampleStyleSheet()
    )

    paragraphs = [
        item.getPlainText()
        for item in story
        if hasattr(item, "getPlainText")
    ]
    assert not any("Candidato ausente" in text for text in paragraphs)


def test_generate_pdf_raises_clear_error_when_reportlab_missing(
    tmp_path, result_completo, monkeypatch
):
    import builtins

    original_import = builtins.__import__

    def import_without_reportlab(name, *args, **kwargs):
        if name == "reportlab" or name.startswith("reportlab."):
            raise ImportError("simulated missing reportlab")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_reportlab)

    with pytest.raises(
        ImportError,
        match="reportlab is required for PDF generation: pip install reportlab",
    ) as exc_info:
        generate_pdf(result_completo, tmp_path)

    assert isinstance(exc_info.value.__cause__, ImportError)
    assert str(exc_info.value.__cause__) == "simulated missing reportlab"
