"""Tests for src/publicar_2turno.py and the JSON summary of simulation_2turno.py."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import publicar_2turno as pub  # noqa: E402

AGORA = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)


def _resumo(horas_atras: float = 2.0) -> dict:
    return {
        "executado_em": (AGORA - timedelta(hours=horas_atras)).isoformat(timespec="seconds"),
        "cand_a": "Alpha", "cand_b": "Beta", "fatia_a": 51.2,
        "p_vitoria_a": 68.6, "p_vitoria_b": 31.4, "fatia_a_ic90": [47.1, 55.3],
        "margem_mediana_pp": 3.8, "margem_votos_mediana": 4_700_000,
        "parametros": {"sd_fatia_pp": 2.5, "vies_pp_a": 0.0, "tau": 7.0, "data_min": None},
        "pesquisas": {"n": 64, "n_efetivo": 18.9, "n_institutos": 13, "soma_media": 90.7},
        "sensibilidade": {
            "-1.0": {"0.8": 70.0, "1.5": 55.0, "2.5": 57.0, "3.5": 55.0},
            "0.0": {"0.8": 93.0, "1.5": 78.0, "2.5": 68.6, "3.5": 63.0},
            "1.0": {"0.8": 99.0, "1.5": 90.0, "2.5": 79.9, "3.5": 71.0},
        },
    }


def test_valid_summary_passes():
    pub.validar_resumo(_resumo(), agora=AGORA)


def test_stale_summary_fails():
    with pytest.raises(ValueError, match="old"):
        pub.validar_resumo(_resumo(horas_atras=48), agora=AGORA)


def test_missing_field_fails():
    r = _resumo()
    del r["sensibilidade"]
    with pytest.raises(ValueError, match="missing"):
        pub.validar_resumo(r, agora=AGORA)


def test_probabilities_must_add_to_100():
    r = _resumo()
    r["p_vitoria_b"] = 40.0
    with pytest.raises(ValueError, match="add up"):
        pub.validar_resumo(r, agora=AGORA)


@pytest.mark.parametrize("idioma", ["pt", "en"])
def test_post_contains_numbers_and_disclaimer(idioma):
    texto = pub.gerar_post(_resumo(), idioma)
    sep = "," if idioma == "pt" else "."
    assert f"68{sep}6%" in texto and f"31{sep}4%" in texto
    assert pub.AVISO[idioma] in texto
    assert f"79{sep}9%" in texto     # +1pp sensitivity row at sd 2.5
    assert f"57{sep}0%" in texto     # -1pp sensitivity row at sd 2.5


def test_post_unsupported_language():
    with pytest.raises(ValueError):
        pub.gerar_post(_resumo(), "es")


def test_sensitivity_picks_closest_sd_column():
    r = _resumo()
    r["parametros"]["sd_fatia_pp"] = 2.4
    assert pub._linha_sensibilidade(r, "0.0") == 68.6


def test_main_writes_files_and_gate_returns_codes(tmp_path):
    ok = tmp_path / "resumo.json"
    ok.write_text(json.dumps(_resumo(horas_atras=0.0).copy() | {
        "executado_em": datetime.now(timezone.utc).isoformat(timespec="seconds")}))
    assert pub.main(["--resumo", str(ok), "--saida", str(tmp_path)]) == 0
    assert (tmp_path / "post_2turno_pt.md").exists()
    assert (tmp_path / "post_2turno_en.md").exists()
    assert pub.main(["--resumo", str(tmp_path / "nao_existe.json")]) == 1
