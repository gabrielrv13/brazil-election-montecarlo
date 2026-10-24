"""Pacote de entrada e saída."""

from importlib import import_module
from typing import Any

_EXPORTS = {
    "load_polls": ("src.io.loader", "load_polls"),
    "carregar_pesquisas": ("src.io.loader", "carregar_pesquisas"),
    "generate_pdf": ("src.io.report", "generate_pdf"),
    "save_csvs": ("src.io.report", "save_csvs"),
    "carregar_historico": ("src.io.history", "carregar_historico"),
    "init_db": ("src.io.history", "init_db"),
    "salvar_historico": ("src.io.history", "salvar_historico"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        )

    module_name, attribute_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value