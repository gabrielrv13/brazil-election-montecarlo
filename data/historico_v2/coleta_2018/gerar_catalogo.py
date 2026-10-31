"""Materialize transcrições documentais, sem rede ou importação do simulador.

Requer --destino explícito. Fontes e decisões permanecem no catálogo de origem;
somente os cinco CSVs documentais são escritos no destino. Snapshots são etapa futura.
"""
import argparse
import csv
import hashlib
import html
import io
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
DOCS = ROOT / 'documentos' / '2018'
COLLECTION = ROOT / 'coleta_2018'
SCHEMA = json.loads((ROOT / 'schema.json').read_text(encoding='utf-8'))['tabelas']
TRANSCRIPTION = json.loads((COLLECTION / 'transcricoes.json').read_text(encoding='utf-8'))

EXTRA_SOURCES = {
    'S055': ('https://media.folha.uol.com.br/datafolha/2018/09/20/c6d9234d38849c25e6db553ce1470962IVB2.pdf', 'datafolha_2018-09-19.pdf', 'Datafolha: intenção de voto, campo 18 e 19/09/2018'),
    'S056': ('https://paranapesquisas.com.br/wp-content/uploads/2018/09/Brasil-Set18.pdf', 'parana_2018-09.pdf', 'Paraná Pesquisas: Brasil, setembro de 2018, BR-02410/2018'),
    'S057': ('https://uploads.agencialupa.org/2022/02/4261674.pdf', '', 'Relatório Datafolha de 26 a 28/09/2018 procurado na Lupa'),
    'S058': ('https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip', '', 'TSE: acervo de questionários de 2018, consulta por HTTP Range'),
    'S059': ('https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip', 'questionario_1_BR086872018_125701_questionario_pesquisa.pdf', 'TSE: questionário registrado BR-08687/2018, membro BR086872018_125701_questionario_pesquisa.pdf'),
    'S060': ('https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip', 'questionario_2_BR050032018_118851_questionario_pesquisa.pdf', 'TSE: questionário registrado BR-05003/2018, membro BR050032018_118851_questionario_pesquisa.pdf'),
    'S061': ('https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip', 'questionario_3_BR069192018_122889_questionario_pesquisa.pdf', 'TSE: questionário registrado BR-06919/2018, membro BR069192018_122889_questionario_pesquisa.pdf'),
    'S062': ('https://www.tribunapr.com.br/noticias/politica/bolsonaro-lidera-com-266-aponta-levantamento-do-parana-pesquisas/', '', 'Paraná Pesquisas: divulgação de 12/09/2018 na Tribuna'),
    'S063': ('https://exame.com/brasil/bolsonaro-cresce-e-alcanca-312-haddad-fica-em-2o-lugar-com-202/', '', 'Paraná Pesquisas: divulgação de 26/09/2018, Reuters/Exame'),
    'S064': ('https://especiais.gazetadopovo.com.br/eleicoes/2018/pesquisas-eleitorais/fsb-pesquisa/btg-fsb-bolsonaro-sobe-para-33-haddad-e-ciro-empatam-em-2o-lugar/', '', 'FSB: divulgação de 17/09/2018, Gazeta do Povo'),
    'S065': ('https://www.bnews.com.br/noticias/eleicoes/216790-fsbbtg-pactual-segundo-colocado-haddad-cresce-7-e-bolsonaro-fica-estagnado-na-lideranca-com-33.html', '', 'FSB: divulgação de 24/09/2018, BNews'),
    'S066': ('https://www.correiobraziliense.com.br/app/noticia/politica/2018/09/24/interna_politica%2C707823/bolsonaro-mantem-33-e-haddad-salta-para-23-aponta-fsb-btg.shtml', '', 'FSB: notícia com Amoêdo 4%, em conflito com tabela original de 3%'),
    'S067': ('https://pt.wikipedia.org/wiki/Pesquisas_de_opini%C3%A3o_para_a_elei%C3%A7%C3%A3o_presidencial_no_Brasil_em_2022', '', 'Wikipédia 2022: índice indicado pelo usuário para coleta futura, sem transcrição'),
}

PUBLICATION = {
    'S001': '2018-09-05', 'S002': '2018-09-20', 'S003': '2018-09-20',
    'S004': '2018-09-28', 'S005': '2018-09-28', 'S006': '2018-09-28',
    'S007': '2018-09-28', 'S010': '2018-09-06', 'S011': '2018-09-30',
    'S012': '2018-09-17', 'S013': '2018-09-13', 'S014': '2018-09-26',
    'S015': '2018-08-31', 'S016': '2018-09-28', 'S017': '2018-09-21',
    'S018': '2018-09-03', 'S019': '2018-09-03', 'S020': '2018-09-17',
    'S021': '2018-08-20', 'S022': '2018-08-20', 'S038': '2018-09-27',
    'S039': '2018-09-21', 'S040': '2018-09-07', 'S041': '2018-09-14',
    'S042': '2018-09-21', 'S043': '2018-09-04', 'S044': '2018-09-18',
    'S045': '2018-09-11', 'S046': '2018-09-25', 'S055': '2018-09-20',
    'S035': '2018-09-17', 'S062': '2018-09-12', 'S063': '2018-09-26',
    'S064': '2018-09-17', 'S065': '2018-09-24', 'S066': '2018-09-24',
}
WEB_READ = {'S001', 'S003', 'S007', 'S008', 'S011', 'S019', 'S029', 'S051'}
REGISTRY_SOURCES = {'S008', 'S009', 'S047', 'S048', 'S049', 'S058', 'S059', 'S060', 'S061'}
PENDING_DEPENDENCE = 'Grupo de dependência não atribuído: sobreposição/painel/entidade e dupla conferência pendentes.'


def row(table, **values):
    return dict.fromkeys(SCHEMA[table]['campos'], '') | values


def write_csv(path, fields, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def registry_rows():
    """Leia explicitamente o membro BR, preservando ZIP e números originais."""
    with zipfile.ZipFile(DOCS / 'S048.zip') as archive:
        raw = archive.read('pesquisa_eleitoral_2018_BR.csv').decode('latin1')
    return list(csv.DictReader(io.StringIO(raw), delimiter=';'))


def iso(value):
    return '-'.join(reversed(value.split('/')))


def sources():
    logs = []
    for name in ('acessos_http.json', 'acessos_http_2.json'):
        logs += json.loads((DOCS / name).read_text(encoding='utf-8'))
    by_id = {e['fonte_id']: e for e in logs}
    for sid, (url, filename, title) in EXTRA_SOURCES.items():
        by_id[sid] = {'fonte_id': sid, 'url': url, 'titulo': title,
                      'acessado_em_utc': ''}
        if filename:
            by_id[sid]['caminho_local'] = (DOCS / filename).relative_to(REPO).as_posix()
    downloads = json.loads((DOCS / 'downloads.json').read_text(encoding='utf-8'))
    for sid, item in zip(('S055', 'S057', 'S056'), downloads):
        by_id[sid].update(acessado_em_utc=item['acessado_em_utc'], status_http=item['status_http'])
    qlog = json.loads((DOCS / 'questionarios_acesso.json').read_text(encoding='utf-8'))
    for sid in ('S058', 'S059', 'S060', 'S061'):
        by_id[sid]['acessado_em_utc'] = qlog['acessado_em_utc']
    output = []
    for sid, item in sorted(by_id.items()):
        local = item.get('caminho_local', '')
        title = item.get('titulo', '')
        digest = ''
        if local:
            path = REPO / local
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if path.suffix == '.html':
                match = re.search(r'<title[^>]*>(.*?)</title>', path.read_text(encoding='utf-8', errors='replace'), flags=re.S | re.I)
                if match:
                    title = html.unescape(re.sub(r'\s+', ' ', match[1])).strip()
        if not title:
            title = 'Documento procurado: ' + item['url'].split('/')[-1]
        kind = 'registro_pesqele' if sid in REGISTRY_SOURCES else 'arquivo_web' if sid in {'S023', 'S028', 'S029', 'S051', 'S067'} else 'relatorio' if local.endswith('.pdf') or sid in {'S002', 'S020', 'S055', 'S056', 'S057'} else 'noticia'
        status = 'lido_http_com_copia' if local else 'lido_web_sem_copia_http' if sid in WEB_READ or sid in {'S062','S063','S064','S065','S066','S067'} else 'indice_zip_lido_sem_baixar_integral' if sid == 'S058' else 'erro_tls' if 'erro' in item else f"http_{item.get('status_http', 'nao_recuperado')}"
        output.append(row('fontes', fonte_id=sid, url_original=item['url'], titulo=title,
                          editor=urlparse(item['url']).hostname, tipo_fonte=kind,
                          data_publicacao_documento=PUBLICATION.get(sid, ''),
                          data_atualizacao_documento={'S001':'2018-09-05','S011':'2018-09-30','S017':'2018-09-21','S021':'2018-08-20','S019':'2025-04-26','S062':'2018-09-12'}.get(sid,''),
                          acessado_em_utc=item.get('acessado_em_utc',''), caminho_local=local,
                          sha256=digest, status_acesso=status))
    return output


def build():
    tables = {name: [] for name in SCHEMA}
    tables['fontes'] = sources()
    registry = registry_rows()
    all_by_register = {}
    for ordinal, r in enumerate(registry, start=1):
        all_by_register.setdefault(r['NR_PROTOCOLO_REGISTRO'], []).append((ordinal, r))
    for wave in TRANSCRIPTION['levantamentos']:
        reg = wave['registro']
        pkey = {'pesquisa_id': f'BR-{reg}-2018', 'versao_id': 'documental_01'}
        entries = all_by_register[f'BR{reg}2018']
        if wave.get('cnpj_registro'):
            entries = [(i,r) for i,r in entries if r['NR_CNPJ_EMPRESA']==wave['cnpj_registro']]
        first = entries[0][1]
        contractors = ' | '.join(sorted({r['NM_CONTRATANTE'] for _, r in entries}))
        p = row('pesquisas', **pkey, ano='2018', eleicao_id='BR-2018-presidente-1t',
                cargo='presidente', turno='1', abrangencia='BR',
                instituto_id='cnpj_' + first['NR_CNPJ_EMPRESA'], instituto_original=wave['marca_fonte'],
                contratante=contractors, registro_tse=f'BR-{reg}/2018', data_registro=iso(first['DT_REGISTRO']),
                data_inicio_campo=wave['inicio'], data_fim_campo=wave['fim'],
                n_planejado=wave.get('n_planejado', ''), n_realizado=wave['n_realizado'],
                metodo=first['DS_METODOLOGIA_PESQUISA'] if first['DS_METODOLOGIA_PESQUISA'] != '#NULO#' else '',
                margem_erro_pp=wave.get('margem',''), nivel_confianca_pct=wave.get('confianca',''))
        # Universo is transcribed only when stated by the selected report/article.
        universes = {
            '06919':'Eleitores com 16 anos ou mais do país', '05596':'Eleitores com 16 anos ou mais do país',
            '02410':'Eleitores brasileiros com 16 anos ou mais', '03512':'Eleitores brasileiros com 16 anos ou mais',
            '02891':'Eleitores brasileiros com 16 anos ou mais', '01057':'Eleitores com idade a partir de 16 anos nas 27 UFs',
            '06478':'Eleitores com idade a partir de 16 anos nas 27 UFs', '03861':'Eleitores com idade a partir de 16 anos nas 27 UFs',
            '01669':'População brasileira com 16 anos ou mais, áreas urbanas e rurais',
            '00526':'Eleitores brasileiros com acesso a telefone fixo ou celular', '02995':'Eleitores brasileiros com acesso a telefone fixo ou celular',
            '04669':'Eleitores com 16 anos ou mais',
        }
        p['universo'] = universes.get(reg, '')
        tables['pesquisas'].append(p)

        def evidence(target, table, field, sid, location, pub='', conflict=False, status='comprovado', note=''):
            tables['evidencias'].append(row('evidencias', evidencia_id=f"E{len(tables['evidencias'])+1:05}",
                **pkey, cenario_id=target.get('cenario_id',''), resposta_id=target.get('resposta_id',''),
                metrica=target.get('metrica','') if table=='resultados' else '', campo_comprovado=field,
                valor_original=target[field], fonte_id=sid, pagina_trecho=location,
                data_publicacao=pub, data_disponibilidade=pub,
                tipo_disponibilidade='publica_historica' if pub else 'arquivo_posterior_sem_prova_temporal',
                status_evidencia=status, revisor='codex_transcricao_01_sem_segunda_revisao', conflito=str(conflict).lower(),
                decisao=note or 'Valor do alvo normalizado para o esquema; grafia/transcrição original no documento indicado. Segunda revisão humana pendente.'))

        for field, value in p.items():
            if not value or field in pkey:
                continue
            actual = field in {'data_inicio_campo','data_fim_campo','n_realizado','universo','margem_erro_pp','nivel_confianca_pct'}
            sid = wave['fonte_metodologia'] if actual or field=='instituto_original' else 'S048'
            location = 'Metodologia/especificações; ver páginas e parágrafos no inventário da coleta' if actual else f"pesquisa_eleitoral_2018_BR.csv; NR_PROTOCOLO_REGISTRO=BR{reg}2018; registros ordinais " + '|'.join(str(i) for i,_ in entries)
            locations={'S055':'p.6, Metodologia','S035':'p.6, Metodologia','S056':'p.4, Metodologia','S036':'p.4, Metodologia','S037':'p.3, Metodologia','S031':'p.4, Metodologia','S032':'p.4, Metodologia','S033':'p.4, Metodologia','S024':'p.4, ficha de campo','S027':'p.2, Especificacoes Tecnicas'}
            if actual or field=='instituto_original':
                location=locations.get(sid,'Corpo da noticia: paragrafo de campo/amostra/metodologia ou titulo e instituto citado')
            evidence(p,'pesquisas',field,sid,location)

        for specification in wave['cenarios']:
            cid = specification['id']
            key = pkey | {'cenario_id':cid}
            response_ids = list(specification['valores'])
            candidate_ids = [rid for rid in response_ids if rid not in {'bn','ns','nenhum','outros','bni'}]
            identity = '|'.join([specification['fonte_id'],cid,specification['base_percentual'],specification['tratamento_candidato_pt'],*candidate_ids])
            c = row('cenarios', **key, tipo_pergunta=specification['tipo_pergunta'],
                    numero_pergunta=specification.get('numero_pergunta',''), texto_pergunta=specification.get('pergunta',''),
                    lista_candidatos_id='lista_documental_' + hashlib.sha256(identity.encode()).hexdigest()[:16],
                    candidatos_ids='|'.join(candidate_ids), respostas_ids='|'.join(response_ids),
                    base_percentual=specification['base_percentual'],
                    base_amostral=specification.get('base_amostral','Total da amostra' if p['n_realizado'] else ''),
                    tratamento_candidato_pt=specification['tratamento_candidato_pt'],
                    completo=str(specification['completo']).lower(), motivo_incompletude=specification.get('motivo',''))
            tables['cenarios'].append(c)
            for field,value in c.items():
                if value and field not in {*key,'completo','motivo_incompletude'}:
                    question = field in {'numero_pergunta','texto_pergunta'}
                    sid = specification.get('fonte_pergunta',specification['fonte_id']) if question else specification['fonte_id']
                    loc = specification.get('localizacao_pergunta',specification['localizacao']) if question else specification['localizacao']
                    evidence(c,'cenarios',field,sid,loc)
            for rid, value in specification['valores'].items():
                kind = specification.get('tipos',{}).get(rid, 'branco_nulo' if rid=='bn' else 'ns_nr' if rid=='ns' else 'nenhum' if rid=='nenhum' else 'outros' if rid in {'outros','bni'} else 'candidato')
                qualifier = 'menor_que' if value.startswith('<') else 'zero_arredondado' if value=='0' else 'exato'
                result = row('resultados', **key, resposta_id=rid, metrica='intencao_voto',
                             candidato_id=rid if kind=='candidato' else '',
                             nome_original=specification.get('rotulos',{}).get(rid,TRANSCRIPTION['nomes'][rid]),
                             tipo_resposta=kind,valor_pct=value.lstrip('<'),qualificador_valor=qualifier,
                             fonte_id=specification['fonte_id'],pagina_tabela=specification['localizacao'])
                tables['resultados'].append(result)
                for field,v in result.items():
                    if v and field not in {*key,'resposta_id','fonte_id','pagina_tabela'}:
                        evidence(result,'resultados',field,specification['fonte_id'],specification['localizacao'],
                                 specification.get('publicacao',''),field=='valor_pct' and rid in specification.get('conflitos',[]),
                                 note='Transcrição do valor publicado, sem normalização numérica, imputação ou conversão de zero arredondado em zero exato. ' + specification.get('nota_temporal',''))
            # Independent contemporary publication proves release; PDF cover schedules alone do not.
            temporal = {'02410':'S062','03512':'S063','06478':'S064','03861':'S065','01669':'S013','04669':'S014','06919':'S002','05596':'S020','01057':'S018'}.get(reg)
            if temporal:
                evidence(c,'cenarios','tratamento_candidato_pt',temporal,'Notícia contemporânea datada vinculada ao levantamento; números e metadados no texto',specification.get('publicacao',''))
    return tables


def census():
    grouped = {}
    for r in registry_rows():
        if 'Presidente' not in r['DS_CARGOS'] or not '2018-07-27' <= iso(r['DT_FIM_PESQUISA']) <= '2018-09-30':
            continue
        identity=tuple(r[k] for k in ('NR_PROTOCOLO_REGISTRO','NR_CNPJ_EMPRESA','DT_INICIO_PESQUISA','DT_FIM_PESQUISA','QT_ENTREVISTADOS'))
        grouped.setdefault(identity,[]).append(r)
    known = {f"BR{w['registro']}2018":w for w in TRANSCRIPTION['levantamentos']}
    output = []
    for identity, rows in sorted(grouped.items()):
        raw=identity[0]
        r=rows[0]
        w=known.get(raw)
        if w and w.get('cnpj_registro') and w['cnpj_registro'] != r['NR_CNPJ_EMPRESA']:
            w=None
        text=' '.join(r[k] for k in ('DS_METODOLOGIA_PESQUISA','DS_PLANO_AMOSTRAL','DS_DADO_MUNICIPIO'))
        signal=bool(re.search(r'eleitorado brasileiro|eleitores brasileiros|nacional|todo o pa.s|27 unidades|26 estados|abrang.ncia.*Brasil',text,re.I))
        output.append({'registro_tse':raw[:2]+'-'+raw[2:7]+'/'+raw[7:],
                       'cnpj_instituto':r['NR_CNPJ_EMPRESA'],'instituto_registrado':r['NM_EMPRESA'],
                       'data_registro':iso(r['DT_REGISTRO']),'inicio_declarado':iso(r['DT_INICIO_PESQUISA']),
                       'fim_declarado':iso(r['DT_FIM_PESQUISA']),'amostra_declarada':r['QT_ENTREVISTADOS'],
                       'contratantes':' | '.join(sorted({x['NM_CONTRATANTE'] for x in rows})),
                       'cargo_registrado':r['DS_CARGOS'],'territorio_cadastro':r['NM_UE'],
                       'triagem_abrangencia':'nacional_com_fonte_de_resultado' if w else 'indicio_textual_nacional_requer_revisao' if signal else 'abrangencia_nao_conferida_inclui_amostras_locais',
                       'pesquisa_id':f"BR-{w['registro']}-2018" if w else '',
                       'status':'quarentena' if w else 'cancelada_sem_aplicacao' if raw=='BR025532018' else 'pendente_recuperacao',
                       'motivo':PENDING_DEPENDENCE if w else 'Cancelamento documentado em S043; sem resultado aplicado.' if raw=='BR025532018' else 'Registro não prova execução, abrangência nacional ou divulgação. Nenhum resultado imputado.',
                       'fonte_id':'S048','localizacao':'pesquisa_eleitoral_2018_BR.csv; NR_PROTOCOLO_REGISTRO='+raw,
                       'metodologia_declarada':r['DS_METODOLOGIA_PESQUISA'],'plano_amostral_declarado':r['DS_PLANO_AMOSTRAL'],
                       'territorio_descricao':r['DS_DADO_MUNICIPIO']})
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destino',type=Path,required=True)
    parser.add_argument('--preliminar',action='store_true',help='Reproduza somente a entrega documental inicial, sem qualificações posteriores')
    args=parser.parse_args()
    args.destino.mkdir(parents=True,exist_ok=True)
    tables=build()
    qualification = ROOT / 'qualificacao_2018/qualificar.py'
    if not args.preliminar and qualification.exists():
        import runpy
        tables, _, _ = runpy.run_path(str(qualification))['apply'](tables)
    for name in ('pesquisas','cenarios','resultados','fontes','evidencias'):
        write_csv(args.destino/(name+'.csv'),SCHEMA[name]['campos'],tables[name])
    inventory=census()
    dest=args.destino/'coleta_2018'
    dest.mkdir(exist_ok=True)
    # Presentation-only trailing whitespace removal; originals remain in S048.zip.
    inventory = [{k: v.rstrip() if isinstance(v, str) else v for k, v in r.items()} for r in inventory]
    write_csv(dest/'inventario_registros_tse.csv',list(inventory[0]),inventory)
    print(json.dumps({k:len(v) for k,v in tables.items()} | {'registros_tse_no_intervalo':len(inventory)},ensure_ascii=False))


if __name__=='__main__':
    main()
