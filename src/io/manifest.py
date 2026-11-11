"""
Run manifests: what is needed to reproduce and verify a published artifact.

A manifest records, for one run: a run id, UTC time, code revision (and
whether the working tree had uncommitted changes), Python and library
versions, the as-of date, seed, number of draws, every parameter, and the
SHA-256 and size of each input and output file. ``verificar_manifesto``
re-hashes the files so a publication step can refuse artifacts that do not
belong to the recorded run (audit A13 / P1.8).

The manifest is written next to the outputs as ``<name>.manifest.json``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import uuid

VERSAO_MANIFESTO = 1
_RAIZ_CODIGO = Path(__file__).resolve().parents[2]
_PACOTES = ("numpy", "pandas", "scipy", "matplotlib")


def sha256_arquivo(path: Path) -> str:
    """SHA-256 of a file's bytes."""
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _descrever(path: Path, raiz: Path | None) -> dict:
    path = Path(path)
    nome = path.as_posix()
    if raiz is not None:
        try:
            nome = path.resolve().relative_to(raiz.resolve()).as_posix()
        except ValueError:
            pass
    if not path.exists():
        # Recorded so the gap is visible; verificar_manifesto reports it.
        return {"caminho": nome, "sha256": None, "bytes": None}
    return {"caminho": nome, "sha256": sha256_arquivo(path), "bytes": path.stat().st_size}


def revisao_codigo(raiz: Path) -> dict:
    """Current git commit and dirty flag; ``None`` values outside a repository."""
    def git(*args: str) -> str | None:
        try:
            out = subprocess.run(
                ["git", *args], cwd=raiz, capture_output=True, text=True, timeout=10, check=True
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout.strip()

    commit = git("rev-parse", "HEAD")
    status = git("status", "--porcelain", "--untracked-files=no")
    return {"commit": commit, "alteracoes_nao_commitadas": None if status is None else bool(status)}


def _versoes() -> dict:
    from importlib import metadata

    out = {"python": platform.python_version()}
    for pacote in _PACOTES:
        try:
            out[pacote] = metadata.version(pacote)
        except metadata.PackageNotFoundError:
            out[pacote] = None
    return out


def _json_seguro(valor):
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, Path):
        return valor.as_posix()
    if isinstance(valor, float) and not math.isfinite(valor):
        return str(valor)
    if isinstance(valor, Mapping):
        return {str(k): _json_seguro(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_json_seguro(v) for v in valor]
    return valor


def criar_manifesto(
    tipo: str,
    entradas: Iterable[Path],
    saidas: Iterable[Path],
    parametros: Mapping,
    *,
    as_of: date | None,
    seed: int | None,
    n_sim: int | None,
    raiz: Path | None = None,
) -> dict:
    """Build the manifest dictionary (files must already exist)."""
    raiz = Path(raiz) if raiz is not None else Path.cwd()
    return {
        "versao_manifesto": VERSAO_MANIFESTO,
        "tipo": tipo,
        "run_id": uuid.uuid4().hex,
        "criado_em_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # Revision of the code that ran, not of the working directory.
        "codigo": revisao_codigo(_RAIZ_CODIGO),
        "ambiente": _versoes(),
        "as_of": as_of.isoformat() if as_of else None,
        "seed": seed,
        "n_sim": n_sim,
        "parametros": _json_seguro(dict(parametros)),
        "entradas": [_descrever(p, raiz) for p in entradas],
        "saidas": [_descrever(p, raiz) for p in saidas],
    }


def salvar_manifesto(manifesto: dict, destino: Path) -> Path:
    """Write the manifest as UTF-8 JSON and return its path."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino


def caminho_manifesto(artefato: Path) -> Path:
    """Conventional manifest path for an artifact: ``<stem>.manifest.json``."""
    artefato = Path(artefato)
    return artefato.with_name(f"{artefato.stem}.manifest.json")


def verificar_manifesto(manifesto: dict, raiz: Path | None = None) -> list[str]:
    """Re-hash every recorded file; return a list of problems (empty = OK)."""
    raiz = Path(raiz) if raiz is not None else Path.cwd()
    problemas = []
    if manifesto.get("versao_manifesto") != VERSAO_MANIFESTO:
        problemas.append(f"unsupported manifest version: {manifesto.get('versao_manifesto')!r}")
    for grupo in ("entradas", "saidas"):
        for item in manifesto.get(grupo, []):
            path = Path(item["caminho"])
            path = path if path.is_absolute() else raiz / path
            if item.get("sha256") is None:
                problemas.append(f"{grupo}: {item['caminho']} was not hashed at run time")
            elif not path.exists():
                problemas.append(f"{grupo}: missing {item['caminho']}")
            elif sha256_arquivo(path) != item["sha256"]:
                problemas.append(f"{grupo}: {item['caminho']} changed since the run")
    return problemas
