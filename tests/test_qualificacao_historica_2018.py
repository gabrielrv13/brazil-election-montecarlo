"""Gates da qualificação documental sem escrita de snapshots ou simulação."""
import copy
import csv
import hashlib
import importlib.util
import json
import random
import subprocess
import sys

import pytest

from src.historico_v2 import ROOT, carregar, validar

HERE = ROOT / 'qualificacao_2018'
REPO = ROOT.parents[1]
SPEC = importlib.util.spec_from_file_location('qualificacao_tests', HERE / 'qualificar.py')
QUAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(QUAL)


@pytest.fixture(scope='module')
def catalog():
    return carregar(ROOT)


@pytest.fixture(scope='module')
def report(catalog):
    return validar(catalog)


def read(name):
    with (HERE / name).open(encoding='utf-8',newline='') as f:
        return list(csv.DictReader(f))


def test_revisions_preserve_every_published_percentage(catalog):
    base = QUAL.BASE.build()
    assert catalog['resultados'] == base['resultados']
    assert len(catalog['pesquisas'])==27 and len(catalog['cenarios'])==38
    assert catalog['snapshots']==[] and catalog['snapshot_pesquisas']==[]
    for path,digest in json.loads((HERE / 'preservacao.json').read_text(encoding='utf-8')).items():
        if (REPO / path).exists():
            assert hashlib.sha256((REPO / path).read_bytes()).hexdigest()==digest


def test_realized_field_is_not_inferred_from_registration(catalog):
    poll = next(p for p in catalog['pesquisas'] if p['pesquisa_id']=='BR-06630-2018')
    assert (poll['data_inicio_campo'],poll['data_fim_campo'],poll['n_realizado'])==('2018-09-22','2018-09-23','2506')
    evidence = [e for e in catalog['evidencias'] if e['pesquisa_id']==poll['pesquisa_id'] and e['campo_comprovado']=='data_fim_campo']
    assert len(evidence)==1 and evidence[0]['fonte_id']=='Q008'
    assert evidence[0]['data_disponibilidade']=='2018-09-24'
    assert not any(e['fonte_id']=='Q007' for e in catalog['evidencias'])


def test_applied_question_requires_report_confrontation(catalog):
    for d in QUAL.DECISIONS['perguntas_aplicadas']:
        scenario = next(c for c in catalog['cenarios'] if c['pesquisa_id']=='BR-'+d['registro']+'-2018' and c['cenario_id']==d['cenario'])
        assert scenario['numero_pergunta']==d['numero']
        assert 'confronto' in d['localizacao']
    # A tracking questionnaire alone does not assert complete applied results.
    for c in catalog['cenarios']:
        if c['pesquisa_id'] in {'BR-02995-2018','BR-00526-2018'}:
            assert c['completo']=='false' and c['numero_pergunta']==''


def test_candidate_list_alias_only_for_complete_proved_set(catalog):
    canonical = [c for c in catalog['cenarios'] if c['lista_candidatos_id']==QUAL.TARGET_LIST]
    assert len(canonical)>=5
    assert all(c['completo']=='true' and set(c['candidatos_ids'].split('|'))==QUAL.TARGET_CANDIDATES for c in canonical)
    assert all(c['lista_candidatos_id']!=QUAL.TARGET_LIST for c in catalog['cenarios'] if c['completo']=='false')


def test_conflicts_not_silently_resolved(catalog,report):
    assert {d['chave'].split('|')[0] for d in report['diagnosticos'] if d['codigo']=='campo_sem_evidencia'}=={'BR-06919-2018','BR-03861-2018'}
    assert sum(e['campo_comprovado']=='valor_pct' and e['conflito']=='true' for e in catalog['evidencias'])==2
    assert 'base_pergunta_invalida' in {d['codigo'] for d in report['diagnosticos']}
    assert {d['codigo'] for d in report['diagnosticos']} <= {'identidade_incompleta','cenario_sem_identidade','cenario_incompleto','campo_sem_evidencia','base_pergunta_invalida'}


def test_dependency_relations_do_not_certify_independence(catalog):
    dependencies=read('dependencias.csv')
    assert len(dependencies)==27
    assert all(d['status']=='relacao_documentada_sobreposicao_indeterminada' for d in dependencies)
    # One executor is never split into groups to admit additional waves.
    for institute in {p['instituto_id'] for p in catalog['pesquisas']}:
        assert len({p['grupo_dependencia_id'] for p in catalog['pesquisas'] if p['instituto_id']==institute})==1
    assert QUAL.classify('2018-09-30',[])=='quarentena_documentacao_insuficiente'
    assert QUAL.classify('2018-09-30',[],dependence_reviewed=True)=='elegivel'


def test_cut_diagnostics_keep_all_reasons_and_t30_separate():
    rows=read('diagnostico_por_corte.csv')
    assert len(rows)==38*3*3
    assert all(r['classificacao']=='nao_avaliavel_transicao' for r in rows if r['corte']=='2018-09-07')
    assert not any(r['elegivel_qualificacao']=='true' for r in rows)
    assert all(r['classificacao']=='inelegivel_informacao_posterior' for r in rows if r['corte']!='2018-09-07' and 'posterior_corte' in r['motivos_validador'])
    assert QUAL.classify('2018-09-30',['cenario_incompativel'],compatibility_known=False)=='quarentena_documentacao_insuficiente'
    assert QUAL.classify('2018-09-30',['cenario_incompativel'])=='inelegivel_incompatibilidade_metodologica'


def test_matrix_covers_every_scenario_and_remains_partial(catalog):
    rows=read('matriz_qualificacao.csv')
    assert {(r['pesquisa_id'],r['cenario_id']) for r in rows}=={(c['pesquisa_id'],c['cenario_id']) for c in catalog['cenarios']}
    assert all(r['criterios_pendentes'] and r['fontes'] and r['registro_tse'] for r in rows)
    assert all('dependencia_entre_componentes_nao_estabelecida' in r['criterios_pendentes'] for r in rows)


def test_source_references_and_preserved_bytes(catalog):
    ids={s['fonte_id'] for s in catalog['fontes']}
    assert len(ids)==len(catalog['fontes'])
    assert all(e['fonte_id'] in ids and e['pagina_trecho'] for e in catalog['evidencias'])
    for source in catalog['fontes']:
        if source['caminho_local']:
            assert hashlib.sha256((REPO/source['caminho_local']).read_bytes()).hexdigest()==source['sha256']


def test_current_generator_reproduces_qualified_catalog(tmp_path,catalog):
    subprocess.run([sys.executable,str(ROOT/'coleta_2018/gerar_catalogo.py'),'--destino',str(tmp_path)],check=True,cwd=REPO,capture_output=True)
    for table in ('pesquisas','cenarios','resultados','fontes','evidencias'):
        with (tmp_path/(table+'.csv')).open(encoding='utf-8',newline='') as f:
            assert list(csv.DictReader(f))==catalog[table]
    assert not (tmp_path/'snapshots.csv').exists() and not (tmp_path/'snapshot_pesquisas.csv').exists()


def test_validator_order_invariance_after_review(catalog,report):
    shuffled=copy.deepcopy(catalog)
    rng=random.Random(31)
    for rows in shuffled.values():
        rng.shuffle(rows)
    assert validar(shuffled)==report
