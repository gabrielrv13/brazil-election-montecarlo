import copy
import csv
import hashlib
import json
import random

import pytest

from src.historico_v2 import PROTOCOL, ROOT, SCHEMA, carregar, validar


def row(table, **values):
    return dict.fromkeys(SCHEMA[table]['campos'], '') | values


def fixture():
    t = {k: [] for k in SCHEMA}
    t['pesquisas'] = [row('pesquisas', pesquisa_id='p1', versao_id='v1', ano='2022', eleicao_id='BR-2022-presidente-1t', cargo='presidente', turno='1', abrangencia='BR', instituto_id='i1', instituto_original='Instituto sintetico', data_inicio_campo='2022-09-10', data_fim_campo='2022-09-12', metodo='telefone', universo='eleitores', grupo_dependencia_id='g1')]
    t['cenarios'] = [row('cenarios', pesquisa_id='p1', versao_id='v1', cenario_id='c1', tipo_pergunta='estimulada', numero_pergunta='1', texto_pergunta='Pergunta sintetica', lista_candidatos_id='lista1', candidatos_ids='a|b', respostas_ids='a|b|ns', base_percentual='totais', base_amostral='1000', tratamento_candidato_pt='sem_associacao', completo='true')]
    t['resultados'] = [row('resultados', pesquisa_id='p1', versao_id='v1', cenario_id='c1', resposta_id=r, metrica='intencao_voto', candidato_id=r if r != 'ns' else '', nome_original=r, tipo_resposta='candidato' if r != 'ns' else 'ns_nr', valor_pct=v, qualificador_valor='zero_observado' if v == '0' else 'exato', fonte_id='f1', pagina_tabela='1') for r, v in [('a', '60'), ('b', '40'), ('ns', '0')]]
    t['fontes'] = [row('fontes', fonte_id='f1', url_original='https://example.org/sintetico', titulo='Documento sintetico', tipo_fonte='relatorio', data_publicacao_documento='2022-09-13', status_acesso='acessivel')]
    s = next(s for s in PROTOCOL['snapshots'] if s['snapshot_id'] == '2022_1t_T-14')
    t['snapshots'] = [row('snapshots', **{k: str(v) for k, v in s.items() if k != 'status'}, rotulo_legado='T-14', versao_politica='2.0.0', janela_dias='28', cenario_alvo='estimulada:totais', universo_candidatos='lista1', tratamento_candidato_pt='sem_associacao', versao_dataset='sintetico')]
    evidence(t)
    return t


def evidence(t):
    t['evidencias'] = []
    technical = {'pesquisa_id', 'versao_id', 'cenario_id', 'resposta_id', 'fonte_id', 'pagina_tabela', 'motivo_ausencia', 'motivo_incompletude', 'completo'}
    for table in ('pesquisas', 'cenarios', 'resultados'):
        for r in t[table]:
            for f, v in r.items():
                if v and f not in technical:
                    t['evidencias'].append(row('evidencias', evidencia_id=f'e{len(t["evidencias"])}', pesquisa_id=r['pesquisa_id'], versao_id=r['versao_id'], cenario_id=r.get('cenario_id', ''), resposta_id=r.get('resposta_id', ''), metrica=r.get('metrica', ''), campo_comprovado=f, valor_original=v, fonte_id='f1', pagina_trecho='1: trecho sintetico', data_publicacao='2022-09-13', data_disponibilidade='2022-09-13', tipo_disponibilidade='publica_historica', status_evidencia='comprovado', revisor='teste', conflito='false'))


def codes(t):
    return {d['codigo'] for d in validar(t)['diagnosticos']}


def reasons(t):
    return validar(t)['decisoes'][0]['motivos']


def test_valid_and_zero():
    t = fixture()
    assert codes(t) == {'baixa_diversidade'}
    assert validar(t)['decisoes'][0]['elegivel']


@pytest.mark.parametrize('field', ['data_publicacao', 'data_disponibilidade'])
def test_late_publication(field):
    t = fixture()
    for e in t['evidencias']:
        if e['campo_comprovado'] == 'valor_pct': e[field] = '2022-09-19'
    assert 'posterior_corte' in reasons(t)


def test_registration_is_not_publication():
    t = fixture()
    t['pesquisas'][0]['data_registro'] = '2022-09-01'
    evidence(t)
    t['fontes'][0]['tipo_fonte'] = 'registro_pesqele'
    assert 'sem_prova_divulgacao' in reasons(t)
    t['fontes'][0]['tipo_fonte'] = 'relatorio'
    for e in t['evidencias']: e['data_publicacao'] = '2022-09-19'
    assert 'posterior_corte' in reasons(t)


def duplicate_poll(t, poll='p2', version='v1'):
    for table in ('pesquisas', 'cenarios', 'resultados'):
        extra = copy.deepcopy(t[table])
        for r in extra:
            r['pesquisa_id'], r['versao_id'] = poll, version
        t[table].extend(extra)
    evidence(t)


def test_correction_after_cut_preserves_original():
    t = fixture()
    duplicate_poll(t, 'p1', 'v2')
    for e in t['evidencias']:
        if e['versao_id'] == 'v2': e['data_publicacao'] = e['data_disponibilidade'] = '2022-09-20'
    ds = validar(t)['decisoes']
    assert ds[0]['elegivel'] and not ds[1]['elegivel']


def test_two_polls_same_institute_same_day_quarantined():
    t = fixture()
    duplicate_poll(t)
    assert all(not d['elegivel'] for d in validar(t)['decisoes'])
    assert all('empate_quarentena' in d['motivos'] for d in validar(t)['decisoes'])


def test_republication_is_source_not_poll():
    t = fixture()
    t['fontes'].append(t['fontes'][0] | {'fonte_id': 'f2', 'data_publicacao_documento': '2022-09-20'})
    assert len(validar(t)['decisoes']) == 1
    assert validar(t)['decisoes'][0]['elegivel']


@pytest.mark.parametrize('mutation,code', [
    ('missing', 'cenario_incompleto'), ('duplicate', 'chave_invalida_ou_duplicada'),
    ('orphan', 'fonte_inexistente'), ('date', 'data_invalida'),
    ('inverted', 'campo_invertido'), ('value', 'percentual_invalido'),
    ('base', 'base_pergunta_invalida'), ('evidence', 'campo_sem_evidencia'),
    ('candidate', 'lista_candidatos_inconsistente'),
])
def test_atomic_validation(mutation, code):
    t = fixture()
    if mutation == 'missing': t['resultados'].pop()
    if mutation == 'duplicate': t['resultados'].append(t['resultados'][0].copy())
    if mutation == 'orphan': t['resultados'][0]['fonte_id'] = 'missing'
    if mutation == 'date': t['pesquisas'][0]['data_fim_campo'] = '2022-02-30'
    if mutation == 'inverted': t['pesquisas'][0]['data_inicio_campo'] = '2022-09-14'
    if mutation == 'value': t['resultados'][0]['valor_pct'] = 'NaN'
    if mutation == 'base': t['cenarios'][0]['base_percentual'] = 'desconhecida'
    if mutation == 'evidence': t['evidencias'] = []
    if mutation == 'candidate': t['cenarios'][0]['candidatos_ids'] = 'a|lula'
    assert code in codes(t)
    assert not validar(t)['decisoes'][0]['elegivel']


def test_missing_versus_zero():
    t = fixture()
    t['resultados'][-1].update(valor_pct='', qualificador_valor='ausente', motivo_ausencia='nao divulgado')
    evidence(t)
    assert 'cenario_incompleto' in codes(t)
    assert not validar(t)['decisoes'][0]['elegivel']
    t['resultados'][-1]['valor_pct'] = '0'
    assert 'ausencia_qualificador_invalido' in codes(t)


def test_2018_transition_and_distinct_candidates():
    t = fixture()
    p = t['pesquisas'][0]
    p.update(ano='2018', eleicao_id='BR-2018-presidente-1t', data_inicio_campo='2018-09-01', data_fim_campo='2018-09-03')
    s = next(s for s in PROTOCOL['snapshots'] if s['snapshot_id'] == '2018_1t_T-30')
    t['snapshots'][0].update({k: str(v) for k, v in s.items() if k != 'status'})
    t['cenarios'][0].update(candidatos_ids='lula|b', tratamento_candidato_pt='com_lula')
    t['resultados'][0]['candidato_id'] = 'lula'
    evidence(t)
    for e in t['evidencias']: e['data_publicacao'] = e['data_disponibilidade'] = '2018-09-05'
    assert 'cenario_incompativel' in reasons(t)
    assert 'transicao_nao_avaliavel' in reasons(t)


def test_multiple_snapshots_one_collection():
    t = fixture()
    s = next(s for s in PROTOCOL['snapshots'] if s['snapshot_id'] == '2022_1t_T-7')
    t['snapshots'].append(t['snapshots'][0] | {k: str(v) for k, v in s.items() if k != 'status'})
    assert len(t['pesquisas']) == 1
    assert len(validar(t)['decisoes']) == 2
    assert all(d['elegivel'] for d in validar(t)['decisoes'])


def test_order_invariance():
    t = fixture()
    duplicate_poll(t)
    reference = validar(t)
    for seed in range(5):
        for rows in t.values(): random.Random(seed).shuffle(rows)
        assert validar(t) == reference


@pytest.mark.integration
def test_csv_roundtrip(tmp_path):
    t = fixture()
    for table, rows in t.items():
        with (tmp_path / f'{table}.csv').open('w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, SCHEMA[table]['campos'])
            w.writeheader()
            w.writerows(rows)
    assert validar(carregar(tmp_path)) == validar(t)
    (tmp_path / 'pesquisas.csv').write_text('wrong\n', encoding='utf-8')
    with pytest.raises(ValueError, match='cabecalho'): carregar(tmp_path)


def test_manifest_and_empty_storage():
    assert len(PROTOCOL['snapshots']) == 8
    from datetime import date
    for s in PROTOCOL['snapshots']:
        assert (date.fromisoformat(s['data_eleicao']) - date.fromisoformat(s['as_of'])).days == s['horizonte_dias']
    for path, digest in PROTOCOL['legados_sha256'].items():
        assert hashlib.sha256((ROOT.parents[1] / path).read_bytes()).hexdigest() == digest
    assert codes(carregar(ROOT)) == {'catalogo_vazio'}

@pytest.mark.parametrize('change,expected', [
    ('date_future', 'posterior_corte'), ('window', 'fora_janela'),
    ('incomplete', 'quarentena_documental'), ('conflict', 'quarentena_documental'),
])
def test_snapshot_gates(change, expected):
    t = fixture()
    if change == 'date_future':
        for e in t['evidencias']: e['data_disponibilidade'] = '2022-09-19'
    if change == 'window':
        t['pesquisas'][0].update(data_inicio_campo='2022-08-01', data_fim_campo='2022-08-02')
        evidence(t)
    if change == 'incomplete': t['cenarios'][0].update(completo='false', motivo_incompletude='tabela parcial')
    if change == 'conflict': t['evidencias'][0]['conflito'] = 'true'
    assert expected in reasons(t)


def test_latest_wave_and_dependency():
    t = fixture()
    duplicate_poll(t)
    t['pesquisas'][1].update(data_fim_campo='2022-09-14', grupo_dependencia_id='g2')
    evidence(t)
    for e in t['evidencias']:
        if e['pesquisa_id'] == 'p2': e['data_publicacao'] = e['data_disponibilidade'] = '2022-09-15'
    ds = validar(t)['decisoes']
    assert not ds[0]['elegivel'] and ds[1]['elegivel']
    t['pesquisas'][1]['instituto_id'] = 'i2'
    t['pesquisas'][1]['grupo_dependencia_id'] = 'g1'
    evidence(t)
    for e in t['evidencias']:
        if e['pesquisa_id'] == 'p2': e['data_publicacao'] = e['data_disponibilidade'] = '2022-09-15'
    assert sum(d['elegivel'] for d in validar(t)['decisoes']) == 1


def test_duplicate_different_rows_order_invariance():
    t = fixture()
    t['resultados'].append(t['resultados'][0] | {'valor_pct': '33'})
    reference = validar(t)
    t['resultados'].reverse()
    assert validar(t) == reference


def test_structural_error_fails_closed():
    t = fixture()
    t['resultados'][0][None] = ['extra']
    assert codes(t) == {'estrutura_invalida'}


def test_snapshot_links_and_protocol():
    t = fixture()
    t['snapshot_pesquisas'] = [row('snapshot_pesquisas', snapshot_id='2022_1t_T-14', pesquisa_id='p1', versao_id='v1', cenario_id='c1', elegivel='true', motivo='selecionada', data_recencia='2022-09-12', fonte_temporal_id='f1', grupo_dependencia_id='g1', regra_selecao='principal')]
    assert 'vinculo_snapshot_inconsistente' not in codes(t)
    t['snapshot_pesquisas'][0]['elegivel'] = 'false'
    assert 'vinculo_snapshot_inconsistente' in codes(t)
    t['snapshots'][0]['as_of'] = '2022-09-20'
    assert 'snapshot_fora_protocolo' in codes(t)


@pytest.mark.parametrize('field,value,expected', [
    ('sha256', 'bad', 'hash_invalido'),
    ('acessado_em_utc', '2026-10-30', 'acesso_utc_invalido'),
    ('data_atualizacao_documento', '2022-09-01', 'atualizacao_antes_publicacao'),
])
def test_source_integrity(field, value, expected):
    t = fixture()
    t['fontes'][0][field] = value
    assert expected in codes(t)
    assert not validar(t)['decisoes'][0]['elegivel']

@pytest.mark.parametrize('qualifier,value', [('nao_pontuou', ''), ('menor_que', '1'), ('zero_arredondado', '0')])
def test_qualifiers_preserved(qualifier, value):
    t = fixture()
    t['resultados'][-1].update(qualificador_valor=qualifier, valor_pct=value)
    evidence(t)
    assert 'ausencia_qualificador_invalido' not in codes(t)
    assert t['resultados'][-1]['qualificador_valor'] == qualifier
    if not value: assert 'cenario_incompleto' in codes(t)
