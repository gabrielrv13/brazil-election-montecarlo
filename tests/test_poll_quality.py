"""Regression and integration coverage for audit A03/A04."""
from datetime import date
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from src.core.config import SimulationConfig
from src.io.loader import load_polls
from src.retrospectiva_1t import carregar_pesquisas_1t, fatias_validas, fatia_dois_candidatos


def write(tmp_path, rows):
    p = tmp_path / 'poll.csv'
    pd.DataFrame(rows).to_csv(p, index=False)
    return p


def rows():
    return [dict(candidato=c, intencao_voto_pct=v, desvio_padrao_pct=2,
                 instituto='A', data='2026-10-01', pesquisa_id='a')
            for c, v in [('Lula', 43), ('Flavio Bolsonaro', 39), ('Outros', 5)]]


@pytest.mark.parametrize('value', ['', '2026-10-0', '2026-02-30', '2100-01-01', '01/02/26'])
def test_loader_rejects_bad_dates_with_line(tmp_path, value):
    data = rows(); data[1]['data'] = value
    with pytest.raises(ValueError, match='line 3'):
        load_polls(SimulationConfig(csv_path=write(tmp_path, data)))


@pytest.mark.parametrize('value', [np.inf, -1, 101, np.nan])
def test_invalid_vote_rejected(tmp_path, value):
    data = rows(); data[1]['intencao_voto_pct'] = value
    with pytest.raises(ValueError):
        load_polls(SimulationConfig(csv_path=write(tmp_path, data)))


def test_incomplete_never_rebased_to_100(tmp_path):
    df, _ = carregar_pesquisas_1t(write(tmp_path, rows()[:1]), date(2026,10,3))
    shares = fatias_validas(df)
    assert shares.empty
    assert shares.attrs['pesquisas_excluidas']


def test_distinct_ids_same_institute_date_stay_separate(tmp_path):
    data = rows() + [dict(r, pesquisa_id='b', intencao_voto_pct=30) for r in rows()]
    df, _ = carregar_pesquisas_1t(write(tmp_path, data), date(2026,10,3))
    assert len(fatias_validas(df)) == 2
    df = df.drop(columns='pesquisa_id')
    with pytest.raises(ValueError, match='Ambiguous'):
        fatias_validas(df)


def test_pair_completeness_does_not_require_other_candidates(tmp_path):
    p = write(tmp_path, rows()[:2])
    poll = load_polls(SimulationConfig(csv_path=p, required_candidates=('Lula', 'Flavio Bolsonaro')))
    assert len(poll.candidatos) == 2
    df, _ = carregar_pesquisas_1t(p, date(2026,10,3))
    assert fatia_dois_candidatos(fatias_validas(df), date(2026,10,3), 7) == pytest.approx(39/82*100)


def test_audit_six_dates_and_partial_group(tmp_path):
    # Reproduce the committed audit data independently of local source edits.
    p = tmp_path/'audit.csv'
    p.write_bytes((Path(__file__).parent/'fixtures/pesquisas_auditoria_a03.csv').read_bytes())
    with pytest.raises(ValueError) as error:
        load_polls(SimulationConfig(csv_path=p))
    for line in range(325,331):
        assert f'line {line}:' in str(error.value)
    df, q = carregar_pesquisas_1t(p, date(2026,10,3))
    shares = fatias_validas(df)
    assert q['descartadas_valor_ou_data'] == 6
    assert len(shares.attrs['pesquisas_excluidas']) == 1
    assert not (shares['Lula'] == 100).any()


@pytest.mark.parametrize("field,value", [("rejeicao_pct", np.inf), ("indecisos_pct", -1)])
def test_optional_percentages_rejected(tmp_path, field, value):
    data = rows(); data[0][field] = value
    with pytest.raises(ValueError, match=field):
        load_polls(SimulationConfig(csv_path=write(tmp_path, data)))


def test_invalid_minor_candidate_excludes_whole_identified_poll(tmp_path):
    data = rows() + [dict(r, pesquisa_id='b') for r in rows()]
    data[2]['intencao_voto_pct'] = -1
    df, quality = carregar_pesquisas_1t(write(tmp_path, data), date(2026,10,3))
    assert set(df.pesquisa_id) == {'b'}
    assert quality['linhas_excluidas_com_grupo_invalido'] == [2,3,4]


def test_declared_scenario_requires_minor_candidate(tmp_path):
    df, _ = carregar_pesquisas_1t(write(tmp_path, rows()[:2]), date(2026,10,3))
    assert fatias_validas(df, ('Flavio Bolsonaro', 'Lula', 'Outros')).empty


def test_partial_poll_rejected_by_loader(tmp_path):
    data = rows() + [dict(rows()[0], pesquisa_id='b')]
    with pytest.raises(ValueError, match='Incomplete poll'):
        load_polls(SimulationConfig(csv_path=write(tmp_path,data)))


@pytest.mark.parametrize('value', [None, '2100-01-01', '2026-10-0'])
def test_single_candidate_aggregator_cannot_bypass_date_validation(value):
    from src.core.aggregation import agregar_pesquisas_candidato
    data = pd.DataFrame(rows()[:1]); data['data'] = value
    with pytest.raises(ValueError):
        agregar_pesquisas_candidato(data, date(2026,10,3))


def test_as_of_rejects_historical_future_and_accepts_boundary(tmp_path):
    from src.io.loader import carregar_pesquisas
    p = write(tmp_path, rows())
    with pytest.raises(ValueError, match='future dates'):
        load_polls(SimulationConfig(csv_path=p, as_of=date(2026, 9, 30)))
    result = carregar_pesquisas(p, as_of=date(2026, 10, 1))
    assert result.votos_media.tolist() == [43, 39, 5]


def test_explicit_as_of_makes_csv_to_simulation_independent_of_clock(tmp_path, monkeypatch):
    from src.io import loader
    from src.core import simulation
    data = rows() + [dict(r, pesquisa_id='b', data='2026-09-24',
                         intencao_voto_pct=r['intencao_voto_pct'] + 2) for r in rows()]
    config = SimulationConfig(csv_path=write(tmp_path, data), as_of=date(2026, 10, 1),
                              seed=42, n_sim=200)
    results = []
    for today in (date(2020, 1, 1), date(2040, 1, 1)):
        class Clock(date):
            @classmethod
            def today(cls):
                return today
        monkeypatch.setattr(loader, 'date', Clock)
        monkeypatch.setattr(simulation, 'date', Clock)
        poll = loader.load_polls(config)
        expected = (43 + 45 * np.exp(-1)) / (1 + np.exp(-1))
        assert poll.votos_media[0] == pytest.approx(expected)
        results.append(simulation.simular_primeiro_turno(config, poll))
    pd.testing.assert_frame_equal(results[0].df, results[1].df)
    np.testing.assert_array_equal(results[0].validos_final, results[1].validos_final)


@pytest.mark.parametrize('invalid', ['2026-10-01', pd.NaT, 123])
def test_as_of_requires_explicit_date_type(invalid):
    with pytest.raises(TypeError, match='as_of'):
        SimulationConfig(as_of=invalid)


def test_leading_zero_ids_remain_distinct(tmp_path):
    data = [dict(r, pesquisa_id='01') for r in rows()]
    data += [dict(r, pesquisa_id='1') for r in rows()]
    poll = load_polls(SimulationConfig(csv_path=write(tmp_path, data), as_of=date(2026, 10, 1)))
    assert poll.votos_media.tolist() == [43, 39, 5]


def scenario_rows():
    # One survey measures two different scenarios; a second survey has another ID.
    return ([dict(r, cenario='full') for r in rows()]
            + [dict(r, cenario='pair', intencao_voto_pct=40) for r in rows()[:2]]
            + [dict(r, cenario='pair', pesquisa_id='b', intencao_voto_pct=30)
               for r in rows()[:2]])


def test_id_and_scenario_form_separate_identities(tmp_path):
    from src.core.poll_quality import validate_identity
    df = pd.DataFrame(scenario_rows())
    keys = validate_identity(df)
    assert keys == ['pesquisa_id', 'cenario']
    assert df.groupby(keys).ngroups == 3
    p = write(tmp_path, scenario_rows())
    pair_config = SimulationConfig(csv_path=p, scenario='pair', as_of=date(2026, 10, 1),
                                    required_candidates=('Lula', 'Flavio Bolsonaro'))
    poll = load_polls(pair_config)
    assert poll.candidatos == ['Lula', 'Flavio Bolsonaro']
    np.testing.assert_array_equal(poll.votos_media, [35, 35])
    df, _ = carregar_pesquisas_1t(p, date(2026, 10, 3), cenario='pair')
    assert len(fatias_validas(df)) == 2


@pytest.mark.parametrize('entry_point', ['loader', 'retrospective', 'shares'])
def test_multiple_scenarios_require_selection(tmp_path, entry_point):
    p = write(tmp_path, scenario_rows())
    with pytest.raises(ValueError, match='Select one cenario'):
        if entry_point == 'loader':
            load_polls(SimulationConfig(csv_path=p, as_of=date(2026, 10, 1)))
        elif entry_point == 'retrospective':
            carregar_pesquisas_1t(p, date(2026, 10, 3))
        else:
            fatias_validas(pd.DataFrame(scenario_rows()))


def test_legacy_identity_warns_and_rejects_duplicates(tmp_path, caplog):
    data = [{k: v for k, v in r.items() if k != 'pesquisa_id'} for r in rows()]
    p = write(tmp_path, data)
    load_polls(SimulationConfig(csv_path=p, as_of=date(2026, 10, 1)))
    assert 'Legacy poll identity inferred' in caplog.text
    p = write(tmp_path, data + data)
    with pytest.raises(ValueError, match='Ambiguous'):
        load_polls(SimulationConfig(csv_path=p, as_of=date(2026, 10, 1)))


@pytest.mark.parametrize('ids', [True, False])
def test_pair_accepts_surveys_with_different_legitimate_coverage(tmp_path, ids):
    data = rows() + [dict(r, pesquisa_id='b', data='2026-09-30') for r in rows()[:2]]
    if not ids:
        data = [{k: v for k, v in r.items() if k != 'pesquisa_id'} for r in data]
    p = write(tmp_path, data)
    poll = load_polls(SimulationConfig(csv_path=p, as_of=date(2026, 10, 1),
                                       required_candidates=('Lula', 'Flavio Bolsonaro')))
    assert poll.candidatos == ['Lula', 'Flavio Bolsonaro']
    df, _ = carregar_pesquisas_1t(p, date(2026, 10, 3))
    assert len(fatias_validas(df)) == 2


def test_cli_propagates_reference_and_scenario():
    from src.cli import _build_parser, _build_simulation_config
    args = _build_parser().parse_args(['run', '--as-of', '2026-10-01', '--cenario', 'pair',
                                      '--candidato-necessario', 'Lula',
                                      '--candidato-necessario', 'Flavio Bolsonaro'])
    config = _build_simulation_config(args)
    assert config.as_of == date(2026, 10, 1)
    assert config.scenario == 'pair'
    assert config.required_candidates == ('Lula', 'Flavio Bolsonaro')


def test_selected_scenario_ignores_unrelated_invalid_observations(tmp_path):
    data = scenario_rows()
    data[0]['data'] = '2100-01-01'
    data[0]['intencao_voto_pct'] = 'n/d'
    p = write(tmp_path, data)
    poll = load_polls(SimulationConfig(csv_path=p, scenario='pair', as_of=date(2026, 10, 1)))
    np.testing.assert_array_equal(poll.votos_media, [35, 35])


def test_aliases_across_surveys_do_not_drop_legitimate_pair(tmp_path):
    data = rows() + [dict(r, pesquisa_id='b') for r in rows()[:2]]
    data[4]['candidato'] = 'F. Bolsonaro'
    df, _ = carregar_pesquisas_1t(write(tmp_path, data), date(2026, 10, 3))
    shares = fatias_validas(df)
    assert len(shares.dropna(subset=['Lula', 'Flavio Bolsonaro'])) == 2


def test_metadata_checked_before_cutoff_can_hide_partial_id(tmp_path):
    data = rows()
    data[-1]['data'] = '2026-10-05'
    with pytest.raises(ValueError, match='Inconsistent metadata'):
        carregar_pesquisas_1t(write(tmp_path, data), date(2026, 10, 3))
