"""Verificações documentais da primeira entrega, sem executar o motor."""
import csv
import hashlib
import importlib.util
import json
import random
import subprocess
import sys
from pathlib import Path

import pytest

from src.historico_v2 import ROOT, SCHEMA, carregar, validar

REPO = ROOT.parents[1]
COLLECTION = ROOT / 'coleta_2018'


@pytest.fixture(scope='module')
def catalog():
    # Regression of the approved preliminary delivery, retained as a reproducible input.
    spec = importlib.util.spec_from_file_location('coleta_preliminar_tests', COLLECTION / 'gerar_catalogo.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build()


@pytest.fixture(scope='module')
def diagnostic(catalog):
    return validar(catalog)


def test_pending_documents_are_not_structural_failures(catalog, diagnostic):
    assert {k: len(catalog[k]) for k in ('pesquisas', 'cenarios', 'resultados', 'fontes', 'evidencias')} == dict(pesquisas=27, cenarios=38, resultados=382, fontes=67, evidencias=2960)
    assert {d['codigo'] for d in diagnostic['diagnosticos']} == {'identidade_incompleta', 'cenario_sem_identidade', 'cenario_incompleto', 'campo_sem_evidencia', 'base_pergunta_invalida'}
    assert not catalog['snapshots'] and not catalog['snapshot_pesquisas']
    assert diagnostic['decisoes'] == []
    quarantined = {d['chave'] for d in diagnostic['diagnosticos'] if d['codigo']=='identidade_incompleta'}
    assert quarantined == {p['pesquisa_id']+'|'+p['versao_id'] for p in catalog['pesquisas']}
    for name, table in catalog.items():
        keys = [tuple(r[k] for k in SCHEMA[name]['chave']) for r in table]
        assert len(keys) == len(set(keys))


def test_preserved_sources_and_protected_files(catalog):
    for source in catalog['fontes']:
        if source['caminho_local']:
            assert hashlib.sha256((REPO / source['caminho_local']).read_bytes()).hexdigest() == source['sha256']
        else:
            assert source['sha256'] == ''
    for path, digest in json.loads((COLLECTION / 'preservacao.json').read_text(encoding='utf-8')).items():
        if not (REPO / path).exists() and not path.startswith(('data/', 'src/')):
            continue  # Local outputs are intentionally absent from clean checkouts.
        assert hashlib.sha256((REPO / path).read_bytes()).hexdigest() == digest


def test_sample_identity_and_conflicting_values(catalog):
    polls = {p['pesquisa_id']: p for p in catalog['pesquisas']}
    assert polls['BR-02039-2018']['instituto_id'] == 'cnpj_29550908000150'
    assert polls['BR-08687-2018']['n_planejado'] == '9072'
    assert polls['BR-08687-2018']['n_realizado'] == '9000'
    assert polls['BR-06919-2018']['n_planejado'] == '8596'
    assert polls['BR-06919-2018']['n_realizado'] == '8601'
    target = next(r for r in catalog['resultados'] if r['pesquisa_id']=='BR-06919-2018' and r['resposta_id']=='bn')
    assert target['valor_pct'] == '12'
    assert any(e['pesquisa_id']==target['pesquisa_id'] and e['resposta_id']=='bn' and e['campo_comprovado']=='valor_pct' and e['conflito']=='true' for e in catalog['evidencias'])


def test_qualifiers_and_conditional_scenarios(catalog):
    zeros = [r for r in catalog['resultados'] if r['valor_pct']=='0']
    assert zeros and all(r['qualificador_valor']=='zero_arredondado' for r in zeros)
    limits = [r for r in catalog['resultados'] if r['qualificador_valor']=='menor_que']
    assert limits and all(r['valor_pct']=='1' for r in limits)
    conditional = next(s for s in catalog['cenarios'] if s['cenario_id']=='transferencia_lula_haddad')
    assert conditional['base_percentual']=='' and conditional['base_amostral']
    for register in ('BR-02891-2018', 'BR-01669-2018'):
        scenarios = [s for s in catalog['cenarios'] if s['pesquisa_id']==register]
        assert len({s['tratamento_candidato_pt'] for s in scenarios}) == 2
    registry_sources = {s['fonte_id'] for s in catalog['fontes'] if s['tipo_fonte']=='registro_pesqele'}
    assert not any(r['fonte_id'] in registry_sources for r in catalog['resultados'])


def test_inventory_retains_unrecovered_entries():
    with (COLLECTION / 'inventario_registros_tse.csv').open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    assert len(rows)==277 and len({r['registro_tse'] for r in rows})==274
    assert any(r['status']=='pendente_recuperacao' for r in rows)
    with (COLLECTION / 'ocorrencias_sem_resultado.csv').open(encoding='utf-8', newline='') as f:
        occurrences = list(csv.DictReader(f))
    assert any(r['status']=='cancelamento_documentado' and r['registro_tse']=='BR-02553/2018' for r in occurrences)


def test_order_does_not_change_documentary_diagnostics(catalog, diagnostic):
    shuffled = {name: list(rows) for name, rows in catalog.items()}
    rng = random.Random(2018)
    for rows in shuffled.values():
        rng.shuffle(rows)
    assert validar(shuffled) == diagnostic


def test_generator_reproduces_only_documentary_tables(tmp_path, catalog):
    subprocess.run([sys.executable, str(COLLECTION / 'gerar_catalogo.py'), '--destino', str(tmp_path), '--preliminar'], check=True, cwd=REPO, capture_output=True)
    for name in ('pesquisas','cenarios','resultados','fontes','evidencias'):
        with (tmp_path / (name+'.csv')).open(encoding='utf-8',newline='') as f:
            assert list(csv.DictReader(f)) == catalog[name]
    assert not (tmp_path / 'snapshots.csv').exists()
    assert not (tmp_path / 'snapshot_pesquisas.csv').exists()
