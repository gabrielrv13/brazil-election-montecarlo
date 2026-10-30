from datetime import date
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from src import backtesting as bt

CUTOFF = date(2022, 9, 20)


def row(**changes):
    return dict(candidato='Lula', intencao_voto_pct=45., rejeicao_pct=30.,
                desvio_padrao_pct=2., indecisos_pct=5., **changes)


@pytest.mark.parametrize('column', ['data_publicacao', 'data_disponibilidade'])
@pytest.mark.parametrize('value,expected', [
    ('2022-09-19', 'accepted'), ('2022-09-20', 'accepted'),
    ('2022-09-21', 'after_as_of'), ('invalid', 'invalid_date'),
    ('2022-02-30', 'invalid_date'), ('20/09/2022', 'invalid_date'),
    ('', 'unproven_availability'), (None, 'unproven_availability'),
])
def test_availability_boundary(column, value, expected):
    eligible, status = bt.filtrar_snapshot_temporal(
        pd.DataFrame([row(data='2022-09-18', **{column: value})]), CUTOFF)
    assert status.tolist() == [expected]
    assert len(eligible) == int(expected == 'accepted')


@pytest.mark.parametrize('changes,expected', [
    ({'data': '2022-09-21'}, 'after_as_of'),
    ({'data': 'broken'}, 'invalid_date'),
    ({'data_fim_campo': '2022-09-21'}, 'after_as_of'),
    ({'data_publicacao': '2022-09-21'}, 'after_as_of'),
    ({'data_inicio_campo': '2022-09-19', 'data_fim_campo': '2022-09-18'}, 'inconsistent_dates'),
    ({'data_fim_campo': '2022-09-20', 'data_publicacao': '2022-09-19'}, 'inconsistent_dates'),
    ({'data': None}, 'accepted'),
])
def test_all_supplied_dates_checked(changes, expected):
    poll = row(data_publicacao='2022-09-20', data_disponibilidade='2022-09-20')
    poll.update(changes)
    _, status = bt.filtrar_snapshot_temporal(pd.DataFrame([poll]), CUTOFF)
    assert status.tolist() == [expected]


@pytest.mark.parametrize('value', [None, pd.NaT, 'invalid', date(2022, 9, 21)])
def test_weight_rejects_invalid_or_future(value):
    with pytest.raises(ValueError):
        bt._calcular_peso_temporal(value, CUTOFF)


@pytest.mark.parametrize('polls', [[], [row(data='2022-09-18')],
    [row(data_publicacao='2022-09-21')], [row(data_publicacao='invalid')]])
def test_empty_cutoff_never_simulates(tmp_path, monkeypatch, polls):
    path = tmp_path / '2022_1t_T-14.csv'
    pd.DataFrame(polls, columns=list(row(data='').keys()) + ['data_publicacao']).to_csv(path, index=False)
    monkeypatch.setattr(bt, 'DATA_DIR', tmp_path)
    simulate = Mock()
    monkeypatch.setattr(bt, 'executar_simulacao_historica', simulate)
    with pytest.raises(ValueError, match='No eligible polls.*as_of=2022-09-20'):
        bt.backtest_snapshot('2022', 'T-14')
    simulate.assert_not_called()


def test_cutoff_precedes_every_aggregate_and_simulation(tmp_path, monkeypatch):
    clean = [row(data='2022-09-18', data_publicacao='2022-09-19'),
             dict(row(data='2022-09-19', data_publicacao='2022-09-20'),
                  intencao_voto_pct=47., indecisos_pct=7.),
             dict(row(data='2022-09-20', data_publicacao='2022-09-20'), candidato='Bolsonaro', intencao_voto_pct=35.)]
    dirty = clean + [dict(row(data='2022-09-21', data_publicacao='2022-09-21'),
                         candidato='Future', intencao_voto_pct=99., rejeicao_pct=99.,
                         desvio_padrao_pct=99., indecisos_pct=99.)]
    path = tmp_path / '2022_1t_T-14.csv'
    pd.DataFrame(clean).to_csv(path, index=False)
    expected = bt.carregar_snapshot(path, CUTOFF)
    pd.DataFrame(dirty).to_csv(path, index=False)
    monkeypatch.setattr(bt, 'DATA_DIR', tmp_path)
    simulate = Mock(return_value={})
    monkeypatch.setattr(bt, 'executar_simulacao_historica', simulate)
    monkeypatch.setattr(bt, 'calcular_metricas', Mock(return_value='ok'))
    with pytest.warns(UserWarning, match='after_as_of'):
        assert bt.backtest_snapshot('2022', 'T-14', n_sim=10) == 'ok'
    actual = simulate.call_args.args
    assert actual[0] == expected[0]
    for result, wanted in zip(actual[1:5], expected[1:]):
        np.testing.assert_allclose(result, wanted)


def test_legacy_fixture_has_no_proven_availability(csv_snapshot_historico):
    with pytest.raises(ValueError, match='unproven_availability'):
        bt.carregar_snapshot(csv_snapshot_historico, CUTOFF)


@pytest.mark.parametrize('cutoff', [None, 'bad', '2022-02-30'])
def test_invalid_cutoff(cutoff):
    with pytest.raises(ValueError, match='as_of'):
        bt.filtrar_snapshot_temporal(pd.DataFrame([row()]), cutoff)


@pytest.mark.parametrize('metadata,expected', [
    ({'data_fim_campo': '2022-09-17', 'data': '2022-09-18',
      'data_publicacao': '2022-09-19'}, date(2022, 9, 17)),
    ({'data': '2022-09-18', 'data_publicacao': '2022-09-19'}, date(2022, 9, 18)),
    ({'data_publicacao': '2022-09-19', 'data_disponibilidade': '2022-09-20'}, CUTOFF),
])
def test_weight_date_policy(metadata, expected):
    eligible, _ = bt.filtrar_snapshot_temporal(pd.DataFrame([row(**metadata)]), CUTOFF)
    assert eligible['data'].tolist() == [expected]
    assert bt._calcular_peso_temporal(expected, CUTOFF) == pytest.approx(
        np.exp(-(CUTOFF - expected).days / 7))
