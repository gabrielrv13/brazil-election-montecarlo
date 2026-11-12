"""Fragmento documental 2022, independente do motor e do catálogo 2018.

Reprodução offline: python data/historico_v2/coleta_2022/gerar_catalogo.py
Fontes e transcrições são entradas, nunca resultados estimados por este programa.
"""
import argparse
import csv
import hashlib
import io
import json
import sys
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parent.parent
sys.path.insert(0, str(REPO))
from src.historico_v2 import SCHEMA, PROTOCOL, validar  # noqa: E402


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def csv_write(path, fields, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        w = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def official(kind):
    with zipfile.ZipFile(ROOT / 'documentos' / '2022' / f'F22_{kind}.zip') as z:
        member = ('pesquisa_eleitoral_2022_BR.csv' if kind == 'REG'
                  else 'pesquisa_contratante_2022_BR.csv')
        return list(csv.DictReader(io.StringIO(z.read(member).decode('latin1')), delimiter=';'))


def normalize_date(raw):
    if not raw or raw == '#NULO#':
        return ''
    value = raw[:10]
    return date.fromisoformat(value).isoformat()


def derived_text(raw):
    """Remove só espaços finais de linhas da cópia derivada; ZIP original intacto."""
    return '\n'.join(line.rstrip() for line in raw.splitlines())


def qualify(raw):
    """Limite e não pontuou não são estimativas nem zeros exatos."""
    if raw == 'np':
        return '', 'nao_pontuou'
    if raw == 'ausente':
        return '', 'ausente'
    if raw.startswith('<'):
        return raw[1:], 'menor_que'
    return raw, 'zero_arredondado' if raw == '0' else 'exato'


def temporal(campo_fim, publicacao, disponibilidade, corte, janela):
    if not campo_fim:
        return 'campo_realizado_desconhecido_ou_conflitante'
    if not publicacao or not disponibilidade:
        return 'sem_prova_divulgacao'
    if max(publicacao, disponibilidade) > corte:
        return 'informacao_posterior_corte'
    age = (date.fromisoformat(corte) - date.fromisoformat(campo_fim)).days
    return 'compativel_temporalmente' if 0 <= age <= janela else 'fora_janela'


def build():
    curated = read_json(HERE / 'transcricoes.json')
    registry, contractors = official('REG'), official('CONTR')
    tables = {name: [] for name in SCHEMA}

    def row(table, **values):
        result = dict.fromkeys(SCHEMA[table]['campos'], '')
        result.update({k: str(v) for k, v in values.items()})
        return result

    logs = read_json(HERE/'acessos.json') + read_json(HERE/'acessos_questionarios.json')
    annotations = read_json(HERE/'anotacoes_fontes.json')
    for entry in logs:
        ann = annotations.get(entry['fonte_id'], {})
        tables['fontes'].append(row('fontes', **{
            k: entry.get(k, '') for k in ('fonte_id','url_original','titulo','tipo_fonte',
                                          'acessado_em_utc','caminho_local','sha256','status_acesso')},
            url_arquivo=entry.get('url_final',''), editor=ann.get('editor',''),
            data_publicacao_documento=ann.get('publicacao',''),
            data_atualizacao_documento=ann.get('atualizacao','')))
    sources = {f['fonte_id']: f for f in tables['fontes']}
    for fid, ann in annotations.items():
        if ann.get('lido_web') and not sources[fid]['caminho_local']:
            sources[fid]['status_acesso'] = 'lido_web_sem_copia_http'

    def evidence(table, target, field, fid, location, pub='', conflict=False):
        # No registration is represented as historical disclosure.
        is_registry = sources[fid]['tipo_fonte'] == 'registro_pesqele'
        identity = [table, *[target.get(k,'') for k in ('pesquisa_id','versao_id','cenario_id','resposta_id')], field, fid]
        eid = hashlib.sha256('|'.join(identity).encode()).hexdigest()[:24]
        available = max(pub, sources[fid]['data_atualizacao_documento']) if pub else ''
        tables['evidencias'].append(row('evidencias', evidencia_id='F22_E_'+eid,
            **{k:target.get(k,'') for k in ('pesquisa_id','versao_id','cenario_id','resposta_id','metrica')},
            campo_comprovado=field, valor_original=target[field], fonte_id=fid, pagina_trecho=location,
            data_publicacao='' if is_registry else pub, data_disponibilidade='' if is_registry else available,
            tipo_disponibilidade='registro_sem_prova_divulgacao' if is_registry else 'publica_historica',
            status_evidencia='comprovado', revisor='transcricao_2022_01_sem_segunda_conferencia',
            conflito='true' if conflict else 'false',
            decisao='Normalização documental explicitada em transcricoes.json; arredondamentos preservados; quarentena.'))

    coverage, matrix = [], []
    conflicts = read_json(HERE/'conflitos.json')
    recovered = set()
    for item in curated['pesquisas']:
        code = 'BR'+item['registro']+'2022'
        matches = [r for r in registry if r['NR_PROTOCOLO_REGISTRO'] == code]
        if len(matches) != 1:
            raise ValueError('identidade_ambigua:'+code)
        reg = matches[0]
        recovered.add((code, reg['NR_CNPJ_EMPRESA']))
        pid = 'BR-'+item['registro']+'-2022'
        key = dict(pesquisa_id=pid,versao_id=curated['versao'])
        cs = [c for c in contractors if c['NR_PROTOCOLO_REGISTRO'] == code]
        contratante = cs[0]['NM_CONTRATANTE'] if len(cs) == 1 else ''
        p = row('pesquisas', **key, ano='2022', eleicao_id='BR-2022-presidente-1t',
            cargo='presidente', turno='1', abrangencia='BR', instituto_id=reg['NR_CNPJ_EMPRESA'],
            instituto_original=item['instituto'], contratante=contratante,
            registro_tse='BR-'+item['registro']+'/2022', data_registro=normalize_date(reg['DT_REGISTRO']),
            data_divulgacao_prevista=normalize_date(reg['DT_DIVULGACAO']),
            data_inicio_campo=item['campo'][0],data_fim_campo=item['campo'][1],
            n_realizado=item['n_realizado'],metodo=item['metodo'],**item.get('metadados_adicionais',{}))
        tables['pesquisas'].append(p)
        for f, v in p.items():
            if not v or f in key:
                continue
            declared = f in {'registro_tse','data_registro','data_divulgacao_prevista','instituto_id','contratante'}
            fid = 'F22_CONTR' if f == 'contratante' else 'F22_REG' if declared else item['fonte']
            loc = (f'{code}; CNPJ executor {reg["NR_CNPJ_EMPRESA"]}; coluna {f}; membro BR do ZIP'
                   if declared else item['pagina'])
            evidence('pesquisas',p,f,fid,loc,item['publicacao'] if not declared else '')
        for sc in item['cenarios']:
            fid = sc.get('fonte',item['fonte'])
            pub = sc.get('publicacao', item['publicacao'])
            loc = sc.get('pagina',item['pagina'])
            skey = dict(**key,cenario_id=sc['id'])
            candidates = [r for r in sc['valores'] if r in curated['nomes'] and r not in {'bn','ns','nenhum','outros','bni','bna'}]
            text = item['pergunta'] if sc['id'] == 'estimulada_totais' else ''
            c = row('cenarios',**skey,tipo_pergunta=sc['tipo'],texto_pergunta=text,
                lista_candidatos_id=pid+'_'+sc['id']+'_lista_documental_01',
                candidatos_ids='|'.join(sorted(candidates)),respostas_ids='|'.join(sorted(sc['valores'])),
                base_percentual=sc['base'],completo='false',
                motivo_incompletude='Instrumento aplicado/número e lista integral ou segunda conferência pendentes; dependência desconhecida. Ver matriz e conflitos.')
            tables['cenarios'].append(c)
            for f in ('tipo_pergunta','texto_pergunta','lista_candidatos_id','candidatos_ids','respostas_ids','base_percentual'):
                if c[f]:
                    evidence('cenarios',c,f,fid,loc,pub)
            for rid, raw in sorted(sc['valores'].items()):
                value, qual = qualify(raw)
                typ = {'bn':'branco_nulo','ns':'ns_nr','nenhum':'nenhum','outros':'outros','bni':'outros','bna':'outros'}.get(rid,'candidato')
                name = sc.get('nomes',{}).get(rid,curated['nomes'][rid])
                r = row('resultados',**skey,resposta_id=rid,metrica='intencao_voto',
                    candidato_id=rid if typ=='candidato' else '',nome_original=name,tipo_resposta=typ,
                    valor_pct=value,qualificador_valor=qual,
                    motivo_ausencia='Não publicado' if qual=='ausente' else '',fonte_id=fid,pagina_tabela=loc)
                tables['resultados'].append(r)
                for f in ('metrica','candidato_id','nome_original','tipo_resposta','valor_pct','qualificador_valor'):
                    if r[f]:
                        conflicted = any(x['registro']==item['registro'] and rid in x.get('respostas',[]) for x in conflicts)
                        evidence('resultados',r,f,fid,loc+'; resposta '+name+'; expressão publicada '+raw,pub,
                                 conflicted and f in {'valor_pct','qualificador_valor'})
            availability = max(pub,sources[fid]['data_atualizacao_documento'])
            for cut in PROTOCOL['snapshots']:
                if not cut['snapshot_id'].startswith('2022_'):
                    continue
                for window in (14,28,42):
                    coverage.append(dict(**skey,corte=cut['as_of'],janela_dias=window,
                        data_fim_campo=p['data_fim_campo'],publicacao=pub,disponibilidade=availability,
                        diagnostico_temporal=temporal(p['data_fim_campo'],pub,availability,cut['as_of'],window),
                        elegibilidade_final='quarentena_documental',elegivel='false'))
            matrix.append(dict(**skey,registro_tse=p['registro_tse'],executor_cnpj=reg['NR_CNPJ_EMPRESA'],
                executor_original=reg['NM_EMPRESA'],contratante=contratante,
                data_registro=p['data_registro'],
                questionario_registrado={'09088':'F22_QT09088_1','00433':'F22_QT00433_1',
                    '04180':'F22_QT04180_1','05022':'F22_QT05022_1'}.get(item['registro'],'não recuperado'),
                campo_declarado=reg['DT_INICIO_PESQUISA']+' / '+reg['DT_FIM_PESQUISA'],
                campo_realizado=' / '.join(item['campo']),amostra_declarada=reg['QT_ENTREVISTADO'],
                amostra_realizada=item['n_realizado'],publicacao=pub,disponibilidade=availability,
                pergunta_aplicada=text or 'não recuperada integralmente',respostas_recuperadas=c['respostas_ids'],
                base=sc['base'],fonte_resultados=fid,localizacao=loc,
                dependencia='não determinada; executor comum não prova independência de ondas',
                estado='quarentena',pendencias=c['motivo_incompletude'],nota=item['nota']))
    inventory = []
    for ordinal, r in enumerate(registry,1):
        end = normalize_date(r['DT_FIM_PESQUISA'])
        if 'Presidente' not in r['DS_CARGO'] or not '2022-05-23' <= end <= '2022-09-25':
            continue
        code = r['NR_PROTOCOLO_REGISTRO']
        inventory.append(dict(linha_membro_br=ordinal,registro_original=code,executor_cnpj=r['NR_CNPJ_EMPRESA'],
            executor=r['NM_EMPRESA'],nome_fantasia=r['NM_EMPRESA_FANTASIA'],cargos=r['DS_CARGO'],
            inicio_declarado=normalize_date(r['DT_INICIO_PESQUISA']),fim_declarado=end,
            divulgacao_prevista=normalize_date(r['DT_DIVULGACAO']),amostra_declarada=r['QT_ENTREVISTADO'],
            contratantes=' | '.join(c['NM_CONTRATANTE'] for c in contractors if c['NR_PROTOCOLO_REGISTRO']==code),
            metodologia_declarada=derived_text(r['DS_METODOLOGIA_PESQUISA']),
            plano_amostral=derived_text(r['DS_PLANO_AMOSTRAL']),
            territorio='BR é código cadastral; abrangência nacional não comprovada por esse código',
            estado='resultado_parcial_recuperado' if (code,r['NR_CNPJ_EMPRESA']) in recovered else 'resultado_nao_recuperado_nesta_entrega',
            fonte='F22_REG',localizacao='pesquisa_eleitoral_2022_BR.csv; linha de dados '+str(ordinal)))
    return tables, inventory, coverage, matrix


def generate(destination):
    destination = Path(destination).resolve()
    # Never overwrite historical roots or unrelated existing directories.
    if destination != (HERE/'catalogo').resolve():
        if destination.exists() and any(destination.iterdir()):
            raise ValueError('destino_alternativo_deve_estar_vazio')
        if destination == ROOT.resolve() or ROOT.resolve() in destination.parents:
            raise ValueError('destino_protegido')
    destination.mkdir(parents=True,exist_ok=True)
    tables, inventory, coverage, matrix = build()
    for name, rows in tables.items():
        csv_write(destination/f'{name}.csv',SCHEMA[name]['campos'],rows)
    for name,rows in [('inventario_registros',inventory),('cobertura_documental',coverage),('matriz_documental',matrix)]:
        csv_write(destination/f'{name}.csv',list(rows[0]),rows)
    diagnostic = validar(tables)
    write_json(destination/'diagnostico_validacao.json',diagnostic)
    write_json(destination/'resumo.json',dict(contagens={k:len(v) for k,v in tables.items()},
        registros_inventariados=len(inventory),levantamentos_em_quarentena=len(tables['pesquisas']),
        elegiveis=0,diagnosticos=dict(Counter(d['codigo'] for d in diagnostic['diagnosticos']))))
    return tables


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destino',type=Path,default=HERE/'catalogo')
    args=parser.parse_args()
    generate(args.destino)
