"""Phase 4: run manifests, publication verification and side-effect-free imports."""

from __future__ import annotations

from argparse import Namespace
from datetime import date
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
import pytest

from src.core.config import PollData, SimulationConfig
from src.io.manifest import (
    caminho_manifesto,
    criar_manifesto,
    revisao_codigo,
    salvar_manifesto,
    verificar_manifesto,
)

ROOT = Path(__file__).resolve().parents[1]


def _arquivos(tmp_path):
    entrada = tmp_path / "polls.csv"
    entrada.write_text("candidato,intencao_voto_pct\nA,50\n", encoding="utf-8")
    saida = tmp_path / "out" / "r.json"
    saida.parent.mkdir()
    saida.write_text("{}", encoding="utf-8")
    return entrada, saida


class TestManifest:

    def test_roundtrip_records_everything_and_verifies(self, tmp_path):
        entrada, saida = _arquivos(tmp_path)
        m = criar_manifesto("teste", [entrada], [saida], {"x": float("inf"), "d": date(2026, 1, 2)},
                            as_of=date(2026, 1, 2), seed=7, n_sim=10, raiz=tmp_path)
        assert re.fullmatch(r"[0-9a-f]{32}", m["run_id"])
        assert m["entradas"][0]["caminho"] == "polls.csv"
        assert m["saidas"][0]["caminho"] == "out/r.json"
        assert (m["seed"], m["n_sim"], m["as_of"]) == (7, 10, "2026-01-02")
        assert m["parametros"] == {"x": "inf", "d": "2026-01-02"}
        assert m["ambiente"]["numpy"] == np.__version__
        caminho = salvar_manifesto(m, caminho_manifesto(saida))
        assert caminho.name == "r.manifest.json"
        assert verificar_manifesto(json.loads(caminho.read_text(encoding="utf-8")), tmp_path) == []

    def test_changed_or_missing_files_are_reported(self, tmp_path):
        entrada, saida = _arquivos(tmp_path)
        m = criar_manifesto("teste", [entrada, tmp_path / "ausente.csv"], [saida], {},
                            as_of=None, seed=None, n_sim=None, raiz=tmp_path)
        saida.write_text('{"edited": true}', encoding="utf-8")
        entrada.unlink()
        problemas = verificar_manifesto(m, tmp_path)
        assert any("missing polls.csv" in p for p in problemas)
        assert any("ausente.csv was not hashed" in p for p in problemas)
        assert any("out/r.json changed" in p for p in problemas)

    def test_code_revision_is_the_repository_commit(self):
        rev = revisao_codigo(ROOT)
        if rev["commit"] is None:
            pytest.skip("git not available")
        assert re.fullmatch(r"[0-9a-f]{40}", rev["commit"])
        assert isinstance(rev["alteracoes_nao_commitadas"], bool)


class TestPublicationGate:

    def _pub(self):
        sys.path.insert(0, str(ROOT / "src"))
        import publicar_2turno as pub
        return pub

    def test_mismatch_blocks_posts(self, tmp_path):
        pub = self._pub()
        sys.path.insert(0, str(ROOT / "tests"))
        from test_publicar_2turno import _resumo
        resumo = tmp_path / "resumo_2turno.json"
        resumo.write_text(json.dumps(_resumo()), encoding="utf-8")
        m = criar_manifesto("segundo_turno", [], [resumo], {}, as_of=None, seed=1, n_sim=1,
                            raiz=tmp_path)
        salvar_manifesto(m, caminho_manifesto(resumo))
        pub.verificar_artefatos(resumo, raiz=tmp_path)  # untouched: passes
        data = json.loads(resumo.read_text(encoding="utf-8"))
        data["p_vitoria_a"], data["p_vitoria_b"] = data["p_vitoria_b"], data["p_vitoria_a"]
        resumo.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="changed since the run"):
            pub.verificar_artefatos(resumo, raiz=tmp_path)

    def test_required_manifest(self, tmp_path):
        pub = self._pub()
        resumo = tmp_path / "resumo_2turno.json"
        resumo.write_text("{}", encoding="utf-8")
        pub.verificar_artefatos(resumo)  # optional by default: warns only
        with pytest.raises(ValueError, match="manifest missing"):
            pub.verificar_artefatos(resumo, exigir=True)


class TestCli:

    def test_missing_seed_is_drawn_and_recorded(self, tmp_path):
        from src import cli
        csv = tmp_path / "p.csv"
        csv.write_text("x\n", encoding="utf-8")
        args = cli._build_parser().parse_args(["run", "--csv", str(csv)])
        assert args.seed is None
        cfg = cli._build_simulation_config(args)
        assert isinstance(cfg.seed, int) and args.seed == cfg.seed

    def test_no_subcommand_gets_every_run_default(self, monkeypatch):
        from src import cli
        seen = {}
        monkeypatch.setattr(cli, "_handle_run", lambda a: seen.setdefault("args", a) and 0)
        with pytest.raises(SystemExit):
            cli.main([])
        a = seen["args"]
        assert a.subcommand == "run" and a.as_of is None and a.scenario is None
        assert a.sd_erro_comum == SimulationConfig().sd_erro_comum_pp

    def test_pipeline_writes_verifiable_manifest(self, tmp_path, monkeypatch):
        from src import cli
        csv = tmp_path / "polls.csv"
        csv.write_text("placeholder\n", encoding="utf-8")
        polls = PollData(candidatos=["A", "B", "C"], votos_media=np.array([45.0, 35.0, 20.0]),
                         rejeicao=np.zeros(3), desvio_base=1.0, indecisos=0.0)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(cli, "load_polls", lambda _: polls)
        cfg = SimulationConfig(csv_path=csv, n_sim=2_000, seed=5, as_of=date(2026, 10, 3))
        assert cli._run_pipeline(cfg, Namespace(no_history=True)) == 0
        [man] = (tmp_path / "outputs").glob("*_manifest.json")
        m = json.loads(man.read_text(encoding="utf-8"))
        assert (m["seed"], m["n_sim"], m["as_of"]) == (5, 2_000, "2026-10-03")
        nomes = {Path(s["caminho"]).name for s in m["saidas"]}
        assert any(n.endswith("_probabilidades.csv") for n in nomes)
        assert any(n.endswith(".pdf") for n in nomes)
        assert m["parametros"]["sd_erro_comum_pp"] == 3.0
        assert verificar_manifesto(m, tmp_path) == []


@pytest.mark.parametrize("modulo", ["src.backtesting", "src.simulation_2turno", "src.cli"])
def test_imports_have_no_side_effects(tmp_path, modulo):
    codigo = (
        "import numpy as np, importlib\n"
        "np.random.seed(1); antes = np.random.get_state()[1][:8].tolist()\n"
        f"importlib.import_module('{modulo}')\n"
        "assert np.random.get_state()[1][:8].tolist() == antes, 'global RNG reseeded'\n"
    )
    env = {**os.environ, "PYTHONPATH": str(ROOT), "MPLBACKEND": "Agg", "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, "-c", codigo], cwd=tmp_path, env=env,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    assert not (tmp_path / "outputs").exists()
    assert "ELECTORAL VIABILITY" not in r.stdout
