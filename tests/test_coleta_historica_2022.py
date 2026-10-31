"""Integridade e limites da coleta documental, sem executar o simulador."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from src.historico_v2 import carregar, validar

REPO = Path(__file__).resolve().parents[1]
HERE = REPO/'data/historico_v2/coleta_2022'
CAT = HERE/'catalogo'
spec = importlib.util.spec_from_file_location('coleta2022',HERE/'gerar_catalogo.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def read(name):
    with (CAT/(name+'.csv')).open(encoding='utf-8',newline='') as f:
        return list(csv.DictReader(f))


@pytest.mark.parametrize('raw,expected',[
    ('0',('0','zero_arredondado')),('np',('','nao_pontuou')),
    ('<1',('1','menor_que')),('ausente',('','ausente')),('0.2',('0.2','exato'))])
def test_qualifiers_preserve_information(raw,expected):
    assert module.qualify(raw)==expected


@pytest.mark.parametrize('end,pub,available,cut,window,expected',[
    ('2022-08-02','2022-08-04','2022-08-04','2022-08-03',28,'informacao_posterior_corte'),
    ('2022-09-18','2022-09-19','2022-09-19','2022-09-18',28,'informacao_posterior_corte'),
    ('2022-09-01','2022-09-01','2022-09-03','2022-09-02',28,'informacao_posterior_corte'),
    ('','','','2022-09-02',28,'campo_realizado_desconhecido_ou_conflitante'),
    ('2022-06-06','2022-06-07','2022-06-07','2022-07-04',28,'compativel_temporalmente'),
    ('2022-06-05','2022-06-06','2022-06-06','2022-07-04',28,'fora_janela'),
    ('2022-09-01','','','2022-09-02',28,'sem_prova_divulgacao')])
def test_temporal_gate(end,pub,available,cut,window,expected):
    assert module.temporal(end,pub,available,cut,window)==expected


def test_fragment_is_quarantined_and_has_no_snapshots():
    t=carregar(CAT)
    assert len(t['pesquisas'])==24
    assert len(t['cenarios'])==27
    assert len(t['resultados'])==291
    assert not t['snapshots'] and not t['snapshot_pesquisas']
    assert all(p['grupo_dependencia_id']=='' for p in t['pesquisas'])
    assert all(c['completo']=='false' for c in t['cenarios'])
    d=validar(t)
    assert not d['decisoes']
    assert {x['codigo'] for x in d['diagnosticos']}=={
        'identidade_incompleta','cenario_sem_identidade','cenario_incompleto','campo_sem_evidencia'}
    assert d==json.loads((CAT/'diagnostico_validacao.json').read_text(encoding='utf-8'))


def test_validator_invariant_to_order():
    t=carregar(CAT)
    assert validar(t)==validar({k:list(reversed(v)) for k,v in t.items()})


def test_exact_offline_reproduction(tmp_path):
    dest=tmp_path/'catalogo'
    module.generate(dest)
    for path in CAT.iterdir():
        assert path.read_bytes()==(dest/path.name).read_bytes(),path.name


def test_no_overwrite_of_protected_catalog():
    with pytest.raises(ValueError):
        module.generate(HERE.parent)
    with pytest.raises(ValueError):
        module.generate(HERE.parent/'coleta_2018')


def test_preserved_files():
    baseline=json.loads((HERE/'preservacao.json').read_text(encoding='utf-8'))
    assert len(baseline)==281
    # Local outputs are deliberately not repository prerequisites after checkout.
    for rel,sha in baseline.items():
        path=REPO/rel
        if path.exists():
            assert hashlib.sha256(path.read_bytes()).hexdigest()==sha,rel


def test_sources_are_traceable_and_original_copies_unchanged():
    fs={r['fonte_id']:r for r in read('fontes')}
    for source in fs.values():
        assert source['url_original'].startswith('https://')
        if source['caminho_local']:
            path=REPO/source['caminho_local']
            assert path.is_file()
            assert hashlib.sha256(path.read_bytes()).hexdigest()==source['sha256']
    for e in read('evidencias'):
        assert e['fonte_id'] in fs and e['pagina_trecho']
        assert 'WIKI' not in e['fonte_id']
        if fs[e['fonte_id']]['tipo_fonte']=='registro_pesqele':
            assert not e['data_publicacao'] and not e['data_disponibilidade']
            assert e['campo_comprovado']!='valor_pct'


def test_planned_field_does_not_fill_actual_field_conflicts():
    p={r['registro_tse']:r for r in read('pesquisas')}
    for reg in ['BR-00922/2022','BR-04099/2022']:
        assert p[reg]['data_inicio_campo']==p[reg]['data_fim_campo']==''
    assert p['BR-09408/2022']['n_realizado']==''
    assert p['BR-09404/2022']['n_realizado']=='5744'
    assert p['BR-04180/2022']['n_realizado']=='6754'


def test_inventory_includes_unrecovered_records_and_all_cuts():
    inventory=read('inventario_registros')
    assert len(inventory)==658
    assert any(r['estado']=='resultado_nao_recuperado_nesta_entrega' for r in inventory)
    rows=read('cobertura_documental')
    assert len(rows)==27*5*3
    assert {r['corte'] for r in rows}=={'2022-07-04','2022-08-03','2022-09-02','2022-09-18','2022-09-25'}
    assert {r['janela_dias'] for r in rows}=={'14','28','42'}
    assert all(r['elegivel']=='false' for r in rows)
    assert len({r['pesquisa_id'] for r in rows})==24
    # One identity, many temporal diagnostic rows; republication never creates a poll.
    assert len({p['pesquisa_id'] for p in read('pesquisas')})==24


def test_totals_valid_and_spontaneous_not_combined():
    cs=read('cenarios')
    r=read('resultados')
    assert len([c for c in cs if c['base_percentual']=='validos'])==2
    assert len([c for c in cs if c['tipo_pergunta']=='espontanea'])==1
    valid_ids={(c['pesquisa_id'],c['cenario_id']) for c in cs if c['base_percentual']=='validos'}
    assert all(x['resposta_id'] not in {'bn','ns'} for x in r if (x['pesquisa_id'],x['cenario_id']) in valid_ids)
    assert any(x['qualificador_valor']=='nao_pontuou' and x['valor_pct']=='' for x in r)
    assert any(x['qualificador_valor']=='zero_arredondado' and x['valor_pct']=='0' for x in r)
    assert any(x['qualificador_valor']=='menor_que' for x in r)


def test_conflicts_remain_flagged():
    conflicts=[e for e in read('evidencias') if e['conflito']=='true']
    assert {e['pesquisa_id'] for e in conflicts}=={'BR-05938-2022','BR-00585-2022'}
    assert all(e['status_evidencia']=='comprovado' for e in conflicts)


def test_no_large_artifact_or_engine_import():
    sources=read('fontes')
    assert all((REPO/f['caminho_local']).stat().st_size<5_000_000 for f in sources if f['caminho_local'])
    import ast
    tree=ast.parse((HERE/'gerar_catalogo.py').read_text(encoding='utf-8'))
    imports={n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
    assert not any(n and any(s in n for s in ('simulation','montecarlo','backtest')) for n in imports)
