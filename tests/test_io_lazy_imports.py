"""Tests for the public lazy exports of src.io."""

import importlib
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

EXPORTS = [
    ("load_polls", "src.io.loader", "load_polls"),
    ("carregar_pesquisas", "src.io.loader", "carregar_pesquisas"),
    ("generate_pdf", "src.io.report", "generate_pdf"),
    ("save_csvs", "src.io.report", "save_csvs"),
    ("carregar_historico", "src.io.history", "carregar_historico"),
    ("init_db", "src.io.history", "init_db"),
    ("salvar_historico", "src.io.history", "salvar_historico"),
]


@pytest.fixture
def isolated_io(monkeypatch):
    # Execute the real source in a fresh namespace, without registering it in
    # sys.modules or touching the src.io instance used by the rest of the suite.
    path = Path(__file__).resolve().parents[1] / "src" / "io" / "__init__.py"
    spec = spec_from_file_location("src.io", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    importer = Mock(name="import_module")
    with monkeypatch.context() as patch:
        patch.setattr(importlib, "import_module", importer)
        spec.loader.exec_module(module)
    return module, importer


@pytest.mark.parametrize("name,module_name,attribute_name", EXPORTS)
def test_known_export_imports_expected_attribute(
    isolated_io, name, module_name, attribute_name
):
    module, importer = isolated_io
    expected = object()
    importer.return_value = SimpleNamespace(**{attribute_name: expected})

    assert getattr(module, name) is expected
    importer.assert_called_once_with(module_name)
    assert vars(module)[name] is expected


@pytest.mark.parametrize("name,module_name,attribute_name", EXPORTS)
def test_repeated_access_uses_cached_export(
    isolated_io, name, module_name, attribute_name
):
    module, importer = isolated_io
    expected = object()
    importer.return_value = SimpleNamespace(**{attribute_name: expected})

    assert getattr(module, name) is expected
    importer.side_effect = AssertionError("Cached access must not import again")
    assert getattr(module, name) is expected
    importer.assert_called_once_with(module_name)


def test_unknown_export_raises_without_importing(isolated_io):
    module, importer = isolated_io
    name = "unknown_export"

    with pytest.raises(AttributeError) as exc_info:
        getattr(module, name)

    assert str(exc_info.value) == f"module 'src.io' has no attribute {name!r}"
    importer.assert_not_called()
    assert name not in vars(module)


@pytest.mark.parametrize("error_type", [ImportError, ModuleNotFoundError])
def test_import_failure_propagates_without_caching(isolated_io, error_type):
    module, importer = isolated_io
    error = error_type("simulated import failure")
    importer.side_effect = error

    with pytest.raises(error_type) as exc_info:
        module.load_polls

    assert exc_info.value is error
    importer.assert_called_once_with("src.io.loader")
    assert "load_polls" not in vars(module)


def test_missing_destination_attribute_raises_without_caching(isolated_io):
    module, importer = isolated_io
    importer.return_value = SimpleNamespace()

    with pytest.raises(AttributeError, match="load_polls"):
        module.load_polls

    importer.assert_called_once_with("src.io.loader")
    assert "load_polls" not in vars(module)


def test_package_initialization_does_not_import_exports(isolated_io):
    module, importer = isolated_io

    importer.assert_not_called()
    assert all(name not in vars(module) for name, _, _ in EXPORTS)


def test_all_lists_the_seven_public_exports(isolated_io):
    module, importer = isolated_io

    assert len(module.__all__) == len(EXPORTS)
    assert set(module.__all__) == {name for name, _, _ in EXPORTS}
    importer.assert_not_called()
