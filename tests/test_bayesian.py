from datetime import date
from unittest.mock import MagicMock, call

import arviz as az
import numpy as np
import pytest

from src.core.config import PollData, SimulationConfig
from src.core import bayesian


@pytest.fixture
def config():
    return SimulationConfig(
        n_sim=100,
        seed=123,
        use_bayesian=True,
        election_date=date(2026, 10, 4),
    )


@pytest.fixture
def poll_data():
    return PollData(
        candidatos=["Alice", "Bruno", "Carla"],
        votos_media=np.array([40.0, 30.0, 20.0]),
        rejeicao=np.array([20.0, 25.0, 30.0]),
        desvio_base=5.0,
        indecisos=0.0,
    )


def preparar_mocks(monkeypatch, desvio=5.0):
    mock_model = MagicMock()
    mock_model_context = MagicMock()
    mock_model.return_value.__enter__.return_value = mock_model_context
    mock_model.return_value.__exit__.return_value = False

    mock_dirichlet = MagicMock(return_value="variavel_dirichlet")
    mock_deterministic = MagicMock()
    mock_sample = MagicMock(return_value="trace_simulado")

    monkeypatch.setattr(bayesian.pm, "Model", mock_model)
    monkeypatch.setattr(bayesian.pm, "Dirichlet", mock_dirichlet)
    monkeypatch.setattr(bayesian.pm, "Deterministic", mock_deterministic)
    monkeypatch.setattr(bayesian.pm, "sample", mock_sample)
    monkeypatch.setattr(
        bayesian,
        "_calcular_desvio_ajustado",
        MagicMock(return_value=desvio),
    )

    return mock_model, mock_dirichlet, mock_deterministic, mock_sample


def test_construir_modelo_configura_amostragem(
    config, poll_data, monkeypatch
):
    _, mock_dirichlet, mock_deterministic, mock_sample = preparar_mocks(
        monkeypatch
    )

    resultado = bayesian.construir_modelo(config, poll_data)

    assert resultado == "trace_simulado"
    mock_dirichlet.assert_called_once()
    assert mock_dirichlet.call_args.args[0] == "votos_proporcao"
    np.testing.assert_allclose(
        mock_dirichlet.call_args.kwargs["a"],
        np.array([40.0, 30.0, 20.0]) * 20.0,
    )
    assert mock_dirichlet.call_args.kwargs["shape"] == 3

    assert mock_deterministic.call_count == 3
    assert [
        c.args[0] for c in mock_deterministic.call_args_list
    ] == ["Alice", "Bruno", "Carla"]

    mock_sample.assert_called_once_with(
        draws=10_000,
        tune=2_000,
        chains=4,
        return_inferencedata=True,
        random_seed=123,
    )


def test_usa_semente_42_quando_config_seed_e_none(
    config, poll_data, monkeypatch
):
    config.seed = None
    _, _, _, mock_sample = preparar_mocks(monkeypatch)

    bayesian.construir_modelo(config, poll_data)

    assert mock_sample.call_args.kwargs["random_seed"] == 42


def test_redistribui_indecisos_antes_de_criar_modelo(
    config, poll_data, monkeypatch
):
    poll_data.indecisos = 10.0
    mock_distribuir = MagicMock(
        return_value=(np.array([45.0, 35.0, 20.0]), 0.0)
    )
    monkeypatch.setattr(bayesian, "distribuir_indecisos", mock_distribuir)
    preparar_mocks(monkeypatch)

    bayesian.construir_modelo(config, poll_data)

    mock_distribuir.assert_called_once()
    np.testing.assert_allclose(
        mock_distribuir.call_args.args[0],
        np.array([40.0, 30.0, 20.0]),
    )
    assert mock_distribuir.call_args.args[1] == 10.0
    np.testing.assert_allclose(
        mock_distribuir.call_args.args[2],
        np.array([20.0, 25.0, 30.0]),
    )
    assert mock_distribuir.call_args.args[3] == [
        "Alice", "Bruno", "Carla"
    ]


@pytest.mark.parametrize(
    "votos",
    [
        np.array([40.0, np.nan, 20.0]),
        np.array([40.0, np.inf, 20.0]),
        np.array([40.0, -1.0, 20.0]),
        np.array([40.0, 0.0, 20.0]),
    ],
    ids=["nan", "infinito", "negativo", "zero"],
)
def test_rejeita_shares_invalidos(config, poll_data, monkeypatch, votos):
    poll_data.votos_media = votos
    preparar_mocks(monkeypatch)

    if not np.isfinite(votos).all():
        with pytest.raises(ValueError, match="non-finite"):
            bayesian.construir_modelo(config, poll_data)
    else:
        with pytest.raises(ValueError, match="zero or negative"):
            bayesian.construir_modelo(config, poll_data)


def test_rejeita_share_zero_apos_redistribuicao(
    config, poll_data, monkeypatch
):
    poll_data.indecisos = 10.0
    monkeypatch.setattr(
        bayesian,
        "distribuir_indecisos",
        MagicMock(return_value=(np.array([45.0, 0.0, 20.0]), 0.0)),
    )
    preparar_mocks(monkeypatch)

    with pytest.raises(ValueError, match="Bruno"):
        bayesian.construir_modelo(config, poll_data)


def test_normaliza_nomes_das_variaveis_deterministicas(
    config, monkeypatch
):
    poll_data = PollData(
        candidatos=["José Silva", "Candidato/A", "Candidato-B"],
        votos_media=np.array([40.0, 30.0, 20.0]),
        rejeicao=np.array([20.0, 25.0, 30.0]),
        desvio_base=5.0,
        indecisos=0.0,
    )
    _, _, mock_deterministic, _ = preparar_mocks(monkeypatch)

    bayesian.construir_modelo(config, poll_data)

    nomes = [
        c.args[0] for c in mock_deterministic.call_args_list
    ]
    assert nomes == ["José_Silva", "Candidato_A", "Candidato_B"]
