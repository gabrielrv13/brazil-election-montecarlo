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

# Every consumed leaf is required, including nested fields.
REQUIRED_PATHS = [(key,) for key in pub.CAMPOS] + [
    ("parametros", key) for key in ("sd_fatia_pp", "vies_pp_a", "tau", "data_min")
] + [("pesquisas", key) for key in ("n", "n_efetivo", "n_institutos", "soma_media")]


@pytest.mark.parametrize("path", REQUIRED_PATHS)
def test_all_required_fields(path):
    r = _resumo()
    parent = r if len(path) == 1 else r[path[0]]
    del parent[path[-1]]
    with pytest.raises(ValueError, match=path[-1]):
        pub.validar_resumo(r, agora=AGORA)


INVALID = [
    ("p_vitoria_a", x) for x in (float("nan"), float("inf"), -float("inf"), -10, 110, True, "68.6", None)
] + [
    ("cand_b", " alpha "), ("cand_a", ""), ("cand_a", 3),
    ("fatia_a_ic90", [55, 47]), ("fatia_a_ic90", [1]),
    ("fatia_a_ic90", [float("nan"), 55]), ("fatia_a_ic90", [-1, 101]),
    ("margem_mediana_pp", -1), ("margem_mediana_pp", 99),
    ("margem_votos_mediana", -1), ("margem_votos_mediana", 1.5),
    ("parametros", []), ("pesquisas", None), ("sensibilidade", []),
    ("executado_em", "bad"), ("executado_em", "2026-10-24T12:00:00"),
    ("executado_em", None), ("fatia_a", float("inf")),
    ("parametros.sd_fatia_pp", 0), ("parametros.sd_fatia_pp", 5),
    ("parametros.tau", 0), ("parametros.vies_pp_a", 50),
    ("parametros.data_min", "not-date"), ("parametros.data_min", 42),
    ("pesquisas.n", True), ("pesquisas.n", 0),
    ("pesquisas.n_efetivo", 65), ("pesquisas.n_institutos", 65),
    ("pesquisas.soma_media", float("nan")),
    ("sensibilidade", {"nan": {"2.5": 50}}),
    ("sensibilidade", {"bad": {"2.5": 50}}),
    ("sensibilidade", {"1.0": {"nan": 50}}),
    ("sensibilidade", {"1.0": {"bad": 50}}),
    ("sensibilidade", {"1.0": {"0": 50}}),
    ("sensibilidade", {"1.0": {"2.5": 101}}),
    ("sensibilidade", {"1.0": {}}),
]


def _invalid(path, value):
    r = _resumo()
    keys = path.split(".")
    parent = r
    for key in keys[:-1]:
        parent = parent[key]
    parent[keys[-1]] = value
    return r


@pytest.mark.parametrize("path,value", INVALID)
def test_invalid_fields(path, value):
    with pytest.raises(ValueError, match=path):
        pub.validar_resumo(_invalid(path, value), agora=AGORA)


@pytest.mark.parametrize("path,value", INVALID)
@pytest.mark.parametrize("existing", [False, True])
def test_invalid_publication_leaves_outputs_untouched(tmp_path, capsys, path, value, existing):
    r = _invalid(path, value)
    if path != "executado_em":
        r["executado_em"] = datetime.now(timezone.utc).isoformat()
    source = tmp_path / "summary.json"
    source.write_text(json.dumps(r), encoding="utf-8")
    output = tmp_path / "posts"
    if existing:
        output.mkdir()
        for lang in ("pt", "en"):
            (output / f"post_2turno_{lang}.md").write_bytes(b"original")
    assert pub.main(["--resumo", str(source), "--saida", str(output)]) == 1
    assert "Traceback" not in capsys.readouterr().out
    if existing:
        assert all(p.read_bytes() == b"original" for p in output.iterdir())
    else:
        assert not output.exists()


@pytest.mark.parametrize("idioma", ["pt", "en"])
def test_valid_publication_integration(tmp_path, idioma):
    r = _resumo()
    r["executado_em"] = datetime.now(timezone.utc).isoformat()
    source = tmp_path / "summary.json"
    source.write_text(json.dumps(r), encoding="utf-8")
    output = tmp_path / "posts"
    assert pub.main(["--resumo", str(source), "--saida", str(output)]) == 0
    text = (output / f"post_2turno_{idioma}.md").read_text(encoding="utf-8")
    assert text == pub.gerar_post(r, idioma)
    assert pub.AVISO[idioma] in text


@pytest.mark.parametrize("root", [None, [], 1, "summary"])
def test_invalid_root(root):
    with pytest.raises(ValueError, match="resumo"):
        pub.validar_resumo(root, agora=AGORA)


def test_rounding_and_statistical_definitions():
    r = _resumo()
    r["p_vitoria_b"] = 31.39  # independent rounding at two decimals
    r["fatia_a"] = 70  # input mean need not lie inside simulated interval
    r["parametros"]["vies_pp_a"] = -19
    r["sensibilidade"] = {}  # renderer supports absent optional rows
    r["margem_votos_mediana"] = 0  # no fixed conversion of medians
    pub.validar_resumo(r, agora=AGORA)


def test_render_failure_does_not_write(tmp_path, monkeypatch):
    source = tmp_path / "summary.json"
    r = _resumo()
    r["executado_em"] = datetime.now(timezone.utc).isoformat()
    source.write_text(json.dumps(r), encoding="utf-8")
    original = pub.gerar_post
    def render(summary, language):
        if language == "en":
            raise ValueError("render failed")
        return original(summary, language)
    monkeypatch.setattr(pub, "gerar_post", render)
    output = tmp_path / "posts"
    assert pub.main(["--resumo", str(source), "--saida", str(output)]) == 1
    assert not output.exists()

@pytest.mark.parametrize("path", [
    "fatia_a", "p_vitoria_a", "p_vitoria_b", "margem_mediana_pp",
    "margem_votos_mediana", "parametros.sd_fatia_pp", "parametros.vies_pp_a",
    "parametros.tau", "pesquisas.n", "pesquisas.n_efetivo",
    "pesquisas.n_institutos", "pesquisas.soma_media",
])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, "1", None])
def test_numeric_contract(path, value):
    with pytest.raises(ValueError, match=path):
        pub.validar_resumo(_invalid(path, value), agora=AGORA)


@pytest.mark.parametrize("prob_b,valid", [(31.39, True), (31.41, True), (31.42, False)])
def test_complement_rounding_tolerance(prob_b, valid):
    r = _resumo()
    r["p_vitoria_b"] = prob_b
    if valid:
        pub.validar_resumo(r, agora=AGORA)
    else:
        with pytest.raises(ValueError, match="p_vitoria"):
            pub.validar_resumo(r, agora=AGORA)


def test_absolute_margin_interval_lower_bound():
    r = _resumo()
    r["fatia_a_ic90"] = [60, 70]
    with pytest.raises(ValueError, match="margem_mediana_pp"):
        pub.validar_resumo(r, agora=AGORA)


@pytest.mark.parametrize("limit", [float("nan"), float("inf"), -1, True])
def test_invalid_age_limit(limit):
    with pytest.raises(ValueError, match="max_horas"):
        pub.validar_resumo(_resumo(), max_horas=limit, agora=AGORA)


def test_future_timestamp():
    with pytest.raises(ValueError, match="executado_em"):
        pub.validar_resumo(_resumo(-1), agora=AGORA)


def _resumo_v2():
    r = _resumo()
    r.update(schema_version=2, fatia_agregada_a=51.2, fatia_central_a=51.2,
             fatia_simulada_media_a=51.19,
             transformacoes={"usar_teto": False, "rej_a": 0., "rej_b": 0.})
    r["parametros"].update(vies_candidato="Alpha", vies_pp=0.)
    return r


@pytest.mark.parametrize("path,value", [
    ("schema_version", True), ("schema_version", 3),
    ("fatia_agregada_a", 52), ("fatia_central_a", 46),
    ("fatia_simulada_media_a", float("nan")), ("fatia_simulada_media_a", True),
    ("parametros.vies_candidato", "unknown"), ("parametros.vies_pp", 1),
    ("transformacoes.usar_teto", 1), ("transformacoes.rej_a", 1),
    ("transformacoes.rej_b", -1),
])
def test_a06_invalid_version_two_fields(path, value):
    r = _resumo_v2()
    keys = path.split(".")
    parent = r if len(keys) == 1 else r[keys[0]]
    parent[keys[-1]] = value
    with pytest.raises(ValueError):
        pub.validar_resumo(r, agora=AGORA)


@pytest.mark.parametrize("field", ["fatia_agregada_a", "fatia_central_a",
                                  "fatia_simulada_media_a", "transformacoes"])
def test_a06_version_two_requires_new_fields(field):
    r = _resumo_v2()
    del r[field]
    with pytest.raises(ValueError, match=field):
        pub.validar_resumo(r, agora=AGORA)


def test_a06_legacy_mean_unavailable_and_version_two_mean_explicit():
    r = _resumo()
    r["fatia_simulada_media_a"] = "unvalidated extension"
    for lang, unavailable, mean in [("pt", "indispon", "Média simulada"),
                                    ("en", "unavailable", "Simulated mean")]:
        assert unavailable in pub.gerar_post(r, lang)
        assert mean not in pub.gerar_post(r, lang)
        pub.validar_resumo(_resumo_v2(), agora=AGORA)
        assert mean in pub.gerar_post(_resumo_v2(), lang)
