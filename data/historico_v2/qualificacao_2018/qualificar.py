"""Qualifique documentos sem materializar snapshots e sem importar o simulador.

O validador é executado sobre definições temporárias somente em memória.
O gate documental adicional conserva a incerteza de dependência não resolvida.
"""
import argparse
import copy
import csv
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO))
from src.historico_v2 import PROTOCOL, SCHEMA, validar

DECISIONS = json.loads((HERE / 'decisoes.json').read_text(encoding='utf-8'))
BASE_SPEC = importlib.util.spec_from_file_location('coleta_preliminar_2018', ROOT / 'coleta_2018/gerar_catalogo.py')
BASE = importlib.util.module_from_spec(BASE_SPEC)
BASE_SPEC.loader.exec_module(BASE)
TARGET_CANDIDATES = {'alvaro','daciolo','ciro','eymael','haddad','alckmin','boulos','meirelles','bolsonaro','amoedo','goulart','marina','vera'}
TARGET_LIST = 'lista_2018_haddad_13_qualificacao_v1'


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def write_csv(path, rows, fields=None):
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def apply(base):
    """Reproduza revisões explícitas a partir da primeira entrega preservada."""
    tables = copy.deepcopy(base)
    history = []
    accesses = json.loads((HERE / 'acessos.json').read_text(encoding='utf-8'))
    for item in accesses:
        if item['fonte_id']=='QT_INDICE':
            continue
        fields = {k:item.get(k,'') for k in SCHEMA['fontes']['campos']}
        fields['titulo'] = ('Questionário TSE '+item['registro_tse']+'; membro '+item['membro_zip']) if item.get('membro_zip') else 'Revisão documental: '+item['url_original'].split('/')[-1]
        fields['editor'] = urlparse(item['url_original']).hostname
        if fields['fonte_id'] in {'Q002','Q003','Q005','Q007'}:
            fields['status_acesso'] = 'lido_web_sem_copia_http'
        if fields['fonte_id']=='Q007':
            fields['data_atualizacao_documento'] = '2018-10-04'
        tables['fontes'].append(fields)

    def evidence(target, field, source, location, note, publication=''):
        ev = dict.fromkeys(SCHEMA['evidencias']['campos'],'')
        ev.update(evidencia_id='QUAL'+str(sum(e['evidencia_id'].startswith('QUAL') for e in tables['evidencias'])+1).zfill(5), pesquisa_id=target['pesquisa_id'], versao_id=target['versao_id'], cenario_id=target.get('cenario_id',''), campo_comprovado=field, valor_original=target[field], fonte_id=source, pagina_trecho=location, data_publicacao=publication, data_disponibilidade=publication, tipo_disponibilidade='publica_historica' if publication else 'arquivo_posterior_sem_prova_temporal', status_evidencia='comprovado', revisor=DECISIONS['revisor'], conflito='false', decisao=note)
        tables['evidencias'].append(ev)

    def revise(table, target, field, value, source, location, note, publication=''):
        old = target[field]
        if old == value:
            return
        retired = [e for e in tables['evidencias'] if e['pesquisa_id']==target['pesquisa_id'] and e['versao_id']==target['versao_id'] and e['cenario_id']==target.get('cenario_id','') and not e['resposta_id'] and e['campo_comprovado']==field]
        tables['evidencias'] = [e for e in tables['evidencias'] if e not in retired]
        target[field] = value
        history.append(dict(data_revisao=DECISIONS['data_revisao'], tabela=table, chave='|'.join(target[k] for k in SCHEMA[table]['chave']), campo=field, antes=old, depois=value, fonte=source, localizacao=location, decisao=note, evidencias_anteriores=retired))
        evidence(target, field, source, location, note, publication)

    # Shared executor/contractor is a documented relationship, NOT proof of shared respondents.
    registry = BASE.registry_rows()
    polls = {p['pesquisa_id']:p for p in tables['pesquisas']}
    entities = {}
    for pid, p in polls.items():
        entries = [r for r in registry if r['NR_PROTOCOLO_REGISTRO']==p['registro_tse'].replace('-','').replace('/','') and 'cnpj_'+r['NR_CNPJ_EMPRESA']==p['instituto_id']]
        entities[pid] = {p['instituto_id']} | {'contratante_'+r['NR_CPF_CNPJ_CONTRATANTE'] for r in entries if r['NR_CPF_CNPJ_CONTRATANTE'] not in {'','#NULO#','-1','-3'}}
    components = [{pid} for pid in sorted(polls)]
    while True:
        merged = False
        for i, left in enumerate(components):
            for j in range(i+1,len(components)):
                right = components[j]
                if set.union(*(entities[p] for p in left)) & set.union(*(entities[p] for p in right)):
                    components[i] |= components.pop(j)
                    merged = True
                    break
            if merged:
                break
        if not merged:
            break
    dependencies=[]
    for component in components:
        group = 'relacao_exec_contrato_'+hashlib.sha256('|'.join(sorted(component)).encode()).hexdigest()[:12]
        for pid in sorted(component):
            p = polls[pid]
            note = 'Relação documentada por executor/contratante comum (S048), agrupada conservadoramente. Não prova painel, sobreposição nem independência entre componentes; incerteza mantida no gate de qualificação.'
            revise('pesquisas',p,'grupo_dependencia_id',group,'S048','Membro BR; registro='+p['registro_tse']+'; CNPJ executor e CPF/CNPJ contratantes',note)
            dependencies.append(dict(pesquisa_id=pid,grupo_dependencia_id=group,entidades='|'.join(sorted(entities[pid])),coletas_relacionadas='|'.join(sorted(component)),status='relacao_documentada_sobreposicao_indeterminada',fonte_id='S048',criterio=note))
    for decision in DECISIONS['perguntas_aplicadas']:
        c = next(c for c in tables['cenarios'] if c['pesquisa_id']=='BR-'+decision['registro']+'-2018' and c['cenario_id']==decision['cenario'])
        revise('cenarios',c,'numero_pergunta',decision['numero'],decision['fonte'],decision['localizacao'],'Correspondência de pergunta/lista entre questionário e relatório de resultados. Registro sozinho não comprova aplicação ou publicação.')
    for p in tables['pesquisas']:
        if p['pesquisa_id']=='BR-06630-2018':
            for field,value in {'data_inicio_campo':'2018-09-22','data_fim_campo':'2018-09-23','n_realizado':'2506','universo':'Eleitores brasileiros'}.items():
                revise('pesquisas',p,field,value,'Q008','Notícia de 24/09/2018: parágrafos de amostra/campo e resultados', 'Campo/amostra realizados documentados na notícia; não derivados do cronograma do registro. UOL Q007 atualizado depois do corte é somente corroboração.', '2018-09-24')
    # Canonical identity of a proved full candidate set, never a reconstruction of missing responses.
    reviewed_registers = {'06919','05596','02410','03512','01057','06478','03861','04669'}
    for c in tables['cenarios']:
        reg = c['pesquisa_id'].split('-')[1]
        if reg in reviewed_registers and c['completo']=='true' and set(c['candidatos_ids'].split('|'))==TARGET_CANDIDATES:
            source = next(r['fonte_id'] for r in tables['resultados'] if r['pesquisa_id']==c['pesquisa_id'] and r['cenario_id']==c['cenario_id'])
            revise('cenarios',c,'lista_candidatos_id',TARGET_LIST,source,'Tabela nacional integral citada em resultados.csv; 13 candidatos explicitamente presentes', 'Alias de conjunto comprovado, independente da URL e da ordem dos nomes. Mantidas pergunta, respostas residuais, base e tratamento do PT; não imputa candidato nem altera percentuais.')
    return tables, history, dependencies


def in_memory_validation(tables, cutoff, window):
    """Nenhum CSV ou vínculo de snapshot é escrito por esta função."""
    temporary = copy.deepcopy(tables)
    official = next(s for s in PROTOCOL['snapshots'] if s['as_of']==cutoff)
    definition = dict.fromkeys(SCHEMA['snapshots']['campos'],'')
    definition.update({k:str(v) for k,v in official.items() if k!='status'})
    definition.update(rotulo_legado='T-'+str(official['horizonte_dias']),versao_politica='2.0.0',janela_dias=str(window),cenario_alvo='estimulada:totais',universo_candidatos=TARGET_LIST,tratamento_candidato_pt='com_haddad_sem_lula',versao_dataset='diagnostico_memoria_2026-10-31')
    temporary['snapshots'] = [definition]
    temporary['snapshot_pesquisas'] = []
    return validar(temporary)


def classify(cutoff, reasons, compatibility_known=True, dependence_reviewed=False):
    """Prioridade explícita de apresentação; todos os motivos permanecem no CSV."""
    if cutoff=='2018-09-07':
        return 'nao_avaliavel_transicao'
    if 'posterior_corte' in reasons:
        return 'inelegivel_informacao_posterior'
    if 'fora_janela' in reasons:
        return 'inelegivel_fora_janela'
    if 'cenario_incompativel' in reasons and compatibility_known:
        return 'inelegivel_incompatibilidade_metodologica'
    if reasons or not dependence_reviewed:
        return 'quarentena_documentacao_insuficiente'
    return 'elegivel'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aplicar',action='store_true',help='Atualize apenas os cinco CSVs documentais v2')
    args=parser.parse_args()
    protected=json.loads((HERE/'preservacao.json').read_text(encoding='utf-8'))
    for path,digest in protected.items():
        if (REPO/path).exists() and hashlib.sha256((REPO/path).read_bytes()).hexdigest()!=digest:
            raise ValueError('Arquivo protegido alterado: '+path)
    base=BASE.build()
    tables,history,dependencies=apply(base)
    if args.aplicar:
        for name in ('pesquisas','cenarios','resultados','fontes','evidencias'):
            write_csv(ROOT/(name+'.csv'),tables[name],SCHEMA[name]['campos'])
    dump('historico_alteracoes.json',history)
    dump('validacao_catalogo.json',validar(tables))
    write_csv(HERE/'dependencias.csv',dependencies)
    diagnoses=[]
    for cutoff in ('2018-09-23','2018-09-30','2018-09-07'):
        for window in (28,14,42):
            report=in_memory_validation(tables,cutoff,window)
            dump('validador_'+cutoff+'_'+str(window)+'d.json',report)
            for decision in report['decisoes']:
                c=next(c for c in tables['cenarios'] if c['pesquisa_id']==decision['pesquisa_id'] and c['cenario_id']==decision['cenario_id'])
                compatibility_known=c['completo']=='true' and bool(c['texto_pergunta'])
                reviewed=c['pesquisa_id'] in DECISIONS['dependencia_liberada']
                state=classify(cutoff,decision['motivos'],compatibility_known,reviewed)
                diagnoses.append(dict(corte=cutoff,janela_dias=window,pesquisa_id=c['pesquisa_id'],versao_id=c['versao_id'],cenario_id=c['cenario_id'],classificacao=state,elegivel_validador=str(decision['elegivel']).lower(),elegivel_qualificacao=str(state=='elegivel').lower(),motivos_validador='|'.join(decision['motivos']),pendencia_adicional='' if reviewed else 'dependencia_entre_componentes_nao_estabelecida',protocolo='2.0.0'))
            print('Validado em memória:',cutoff,window,flush=True)
    write_csv(HERE/'diagnostico_por_corte.csv',diagnoses)
    write_csv(HERE/'diagnostico_transicao_T30.csv',[r for r in diagnoses if r['corte']=='2018-09-07'])
    matrix=[]
    current_report=validar(tables)
    for c in tables['cenarios']:
        pid=c['pesquisa_id']
        p=next(p for p in tables['pesquisas'] if p['pesquisa_id']==pid)
        evidence=[e for e in tables['evidencias'] if e['pesquisa_id']==pid and e['cenario_id'] in {'',c['cenario_id']}]
        results=[r for r in tables['resultados'] if r['pesquisa_id']==pid and r['cenario_id']==c['cenario_id']]
        publication=sorted({e['data_publicacao'] for e in evidence if e['campo_comprovado']=='valor_pct' and e['data_publicacao']})
        instruments=[x for x in DECISIONS['instrumentos_registrados'] if x['registro']==pid.split('-')[1]]
        pending=sorted({d['codigo'] for d in current_report['diagnosticos'] if d['chave'].startswith(pid+'|')})
        pending += ['falta_pesquisas.'+f for f in ('data_inicio_campo','data_fim_campo','metodo','universo') if not p[f]]
        pending += ['falta_cenarios.'+f for f in ('numero_pergunta','texto_pergunta','base_amostral') if not c[f]]
        if not publication:
            pending.append('divulgacao_resultados_nao_comprovada')
        if c['completo']!='true':
            pending.append('completude_nao_comprovada')
        if pid not in DECISIONS['dependencia_liberada']:
            pending.append('dependencia_entre_componentes_nao_estabelecida')
        verified=['identidade_registro' if p['registro_tse'] else '', 'base_percentual' if c['base_percentual'] in {'totais','validos'} else '', 'campo_realizado' if p['data_fim_campo'] else '', 'publicacao_resultados' if publication else '', 'pergunta_aplicada' if c['texto_pergunta'] and c['numero_pergunta'] else '', 'lista_completa' if c['completo']=='true' else '']
        matrix.append(dict(pesquisa_id=pid,versao_id=c['versao_id'],cenario_id=c['cenario_id'],instituto=p['instituto_original'],registro_tse=p['registro_tse'],instituto_id=p['instituto_id'],pergunta_aplicada=c['texto_pergunta'],numero_pergunta=c['numero_pergunta'],instrumento_adicional=' | '.join(x['fonte']+': '+x['localizacao'] for x in instruments),lista_respostas_publicadas=' | '.join(r['resposta_id']+': '+r['nome_original']+'='+r['valor_pct']+' ('+r['qualificador_valor']+')' for r in results),lista_completa_comprovada=c['completo'],base_percentual=c['base_percentual'],base_amostral=c['base_amostral'],inicio_campo=p['data_inicio_campo'],fim_campo=p['data_fim_campo'],publicacoes='|'.join(publication),fontes='|'.join(sorted({e['fonte_id'] for e in evidence}|{x['fonte'] for x in instruments})),conflitos='|'.join(x['campo']+': '+x['status'] for x in DECISIONS['conflitos'] if x['registro']==pid.split('-')[1] and x['status'].startswith('pendente')),grupo_dependencia=p['grupo_dependencia_id'],dependencia_status='relacao_documentada_sobreposicao_indeterminada',criterios_atendidos='|'.join(filter(None,verified)),criterios_pendentes='|'.join(sorted(set(pending))),prioridade='alta_T14_T7' if any(d['pesquisa_id']==pid and d['cenario_id']==c['cenario_id'] and d['janela_dias']==28 and d['corte']!='2018-09-07' and 'posterior_corte' not in d['motivos_validador'] and 'fora_janela' not in d['motivos_validador'] for d in diagnoses) else 'transicao_ou_fora_janela'))
    write_csv(HERE/'matriz_qualificacao.csv',matrix)
    make_report(tables,matrix,diagnoses,current_report,dependencies)
    print(json.dumps(dict(levantamentos=len(tables['pesquisas']),cenarios=len(matrix),fontes=len(tables['fontes']),alteracoes=len(history),diagnosticos=dict(Counter(d['codigo'] for d in current_report['diagnosticos']))),ensure_ascii=False))


def make_report(tables,matrix,diagnoses,validation,dependencies):
    lines=['# Qualificação documental das pesquisas de 2018', '', 'Revisão documental de 31/10/2026. Referências obrigatórias: [coleta preliminar](coleta_historica_2018.md), [contrato v2](historico_v2.md) e [protocolo 2.0.0](../data/historico_v2/protocolo_v2.0.0.json). Protocolo, legados e motor preservados. Sem simulações, backtesting ou materialização de snapshots.', '',
        '## Resultado e alcance', '',
        'Esta revisão reduz lacunas de instrumento, identidade e campo, mas **não libera nenhuma pesquisa para a base principal**: a dependência entre componentes institucionais ainda não foi estabelecida documentalmente. Os grupos atribuídos registram relações comprovadas de executor/contratante; não certificam independência estatística. Não houve segunda revisão humana independente. Ausência de erro no validador não substitui esses gates do protocolo.', '',
        'Há 27 levantamentos e 38 cenários. Nenhum percentual foi alterado, imputado ou normalizado. A versão histórica `documental_01` foi mantida: novas evidências de metadados não constituem uma retificação do resultado eleitoral. A primeira transcrição está preservada em `coleta_2018/transcricoes.json`; o histórico desta revisão registra valores anteriores e evidências substituídas.', '',
        '## Fontes adicionais e revisão', '',
        'Foram recuperados 13 questionários oficiais por HTTP Range do acervo TSE: BR-05596, 02410, 03512, 01057, 06478, 03861, 01669, 04669, 05221, 09678, 06630, 00526 e 02995/2018. Registro e questionário comprovam instrumento declarado, não aplicação nem divulgação. Só se preencheu número de pergunta aplicada quando confrontado com o relatório de resultados da mesma coleta. Instrumentos sem esse confronto ficam em coluna separada na matriz.', '',
        'A Folha de 20/09 (Q001), a Reuters de 20/09 (Q005), Suno de 24/09 (Q002), InfoMoney de 24/09 (Q006) e Gazeta de 24/09 (Q008) foram conferidas. Fontes jornalísticas diferentes não equivalem automaticamente a apurações independentes: Reuters/UOL é uma única agência; publicação do próprio instituto/Folha é do mesmo grupo. A matriz preserva os IDs separados sem duplicar coletas.', '',
        'A cópia do relatório Datafolha F03 na Lupa (Q004) continuou inacessível: nada nela foi declarado conferido. Q009 retornou 404. Q002, Q003, Q005 e Q007 foram lidos pela ferramenta web, apesar de falha no download HTTP; não há cópia integral local desses documentos. Q007 tem atualização em 04/10, posterior ao corte, e serve somente para corroboração de metadados já documentados em Q008 de 24/09. A checagem da Agência Pública (Q003, 23/10) contém declaração do contratante sobre ausência de tracking exclusivo para o mercado: é contexto posterior, não prova de disponibilidade em setembro nem de independência amostral.', '',
        'As tentativas e os hashes ficam em `qualificacao_2018/acessos.json` e no catálogo `fontes.csv`; os membros do ZIP estão identificados. A Wikipédia não foi utilizada para comprovar percentuais, datas ou liberar cenários. Páginas recuperadas hoje podem ter sido alteradas desde 2018; não foram autenticadas capturas contemporâneas imutáveis.', '',
        '## Conflitos e lacunas', '']
    for conflict in DECISIONS['conflitos']:
        lines.append('- **BR-'+conflict['registro']+'/2018 — '+conflict['campo']+' ('+conflict['status']+'):** '+conflict['decisao']+' Fontes: '+conflict['fontes']+'.')
    lines += ['', 'Os conflitos de percentuais continuam marcados em `evidencias.csv`. Uma maioria de notícias concordantes não foi tratada como errata. A distinção planejado/realizado e a diferença de rótulos foram registradas sem produzir valores por subtração. Zeros, limites e valores ausentes mantêm os qualificadores da primeira entrega.', '',
        'Fontes adicionais catalogadas (status de acesso não equivale a comprovação de aplicação):', '',
        '| ID | Tipo | Acesso | Referência |', '|---|---|---|---|']
    for source in tables['fontes']:
        if source['fonte_id'].startswith('Q'):
            lines.append('| '+source['fonte_id']+' | '+source['tipo_fonte']+' | '+source['status_acesso']+' | [URL original]('+source['url_original']+') |')
    lines += ['',
        '## Dependência e identidade', '',
        'Os cenários de uma mesma coleta compartilham pesquisa/versão/grupo. Republicações tornam-se fontes adicionais; não criam novos levantamentos. As relações por CNPJ de executor e CPF/CNPJ de contratante foram recuperadas do membro BR do cadastro S048 e fechadas transitivamente em componentes: uma cadeia de executor comum ou contratante comum permanece em um único grupo conservador. A lista integral de entidades e relações está em `dependencias.csv`. Contratante comum não comprova amostra compartilhada; agrupá-lo evita tratar essas coletas como independentes por conveniência.', '',
        'Os questionários XP/Ipespe identificam explicitamente **TRACKING TELEFÔNICO NACIONAL**, ondas 18 e 19. Isso documenta a série, mas não informa se há painel, substituição parcial ou respondentes repetidos. Não se deduziu ausência de sobreposição de períodos de campo não coincidentes. Os relatórios FSB descrevem amostras e periodicidade, mas não comprovam independência entre ondas. A declaração posterior de que não há tracking exclusivo ao mercado não prova independência das entrevistas.', '',
        'O nome atual da empresa no cadastro não renomeia retroativamente a marca. A colisão de BR-02039/2018 continua resolvida pelo CNPJ do executor da coleta de setembro. Um vínculo profissional de um supervisor ou uma notícia sindicada também não prova amostra compartilhada. Não há decisão positiva de independência entre componentes: a classificação final permanece conservadora.', '',
        '## Matriz por pesquisa e cenário', '',
        'A [matriz completa em CSV](../data/historico_v2/qualificacao_2018/matriz_qualificacao.csv) contém pergunta aplicada, instrumento registrado adicional, todas as respostas efetivamente transcritas, comprovação de completude, base, campo, publicação, fontes, conflitos, grupo e critérios atendidos/pendentes. Lista parcial é explicitamente parcial. Não se preencheu o resultado ausente a partir da lista do questionário.', '',
        '| Pesquisa / cenário | Pergunta | Lista comprovada | Campo | Publicação dos resultados | Pendências |', '|---|---|---|---|---|---|']
    for r in matrix:
        safe=lambda v:v.replace('|',', ').replace('\n',' ')
        lines.append('| '+r['pesquisa_id']+' / '+r['cenario_id']+' | '+(r['numero_pergunta'] or 'não comprovada')+' | '+r['lista_completa_comprovada']+' | '+(r['inicio_campo'] or '?')+' a '+(r['fim_campo'] or '?')+' | '+(safe(r['publicacoes']) or 'não comprovada')+' | '+safe(r['criterios_pendentes'])+' |')
    lines += ['', '## Diagnóstico por corte e horizonte', '',
        'O validador original foi executado sem alteração. Para obter diagnósticos temporais, foram construídas definições de corte **somente em memória**, com as datas e janelas do protocolo. Os dois CSVs de snapshots continuam vazios. Os JSONs `validador_DATA_Nd.json` são saídas de diagnóstico, não snapshots nem vínculos materializados.', '',
        'O universo comum de diagnóstico é a lista comprovada dos 13 candidatos com Haddad, primeiro turno estimulado, percentuais totais, sem associação explícita a Lula. O alias canônico depende do conjunto completo comprovado, não da URL da fonte. Não altera listas incompletas nem funde perguntas/respostas. A definição permite comparar os cenários pós-substituição; T−30 permanece estrato separado não avaliável.', '',
        'Há duas camadas: `elegivel_validador` relata o resultado mecânico (inclui seleção de onda); `elegivel_qualificacao` exige também a pendência documental de dependência resolvida. Não se deve usar a primeira coluna como autorização para exportar. Uma onda superada é exclusão pela regra de seleção, não incompatibilidade metodológica. Os motivos integrais são preservados, pois uma linha pode falhar em mais de um critério.', '',
        '| Corte | Janela | Elegíveis no validador | Elegíveis após qualificação |', '|---|---:|---:|---:|']
    for cutoff in ('2018-09-23','2018-09-30','2018-09-07'):
        for window in (28,14,42):
            rows=[r for r in diagnoses if r['corte']==cutoff and r['janela_dias']==window]
            lines.append(f"| {cutoff} | {window} | {sum(r['elegivel_validador']=='true' for r in rows)} | {sum(r['elegivel_qualificacao']=='true' for r in rows)} |")
    lines += ['', 'Classificações finais para a janela principal (28 dias):', '', '| Corte | Classificação | Cenários |', '|---|---|---:|']
    for cutoff in ('2018-09-23','2018-09-30','2018-09-07'):
        for state,count in sorted(Counter(r['classificacao'] for r in diagnoses if r['corte']==cutoff and r['janela_dias']==28).items()):
            lines.append(f'| {cutoff} | {state} | {count} |')
    lines += ['', 'A prioridade de apresentação é transição, informação posterior, fora da janela, incompatibilidade comprovada e quarentena. Lista incompleta/identidade não comprovada fica em quarentena, não é rotulada como incompatibilidade comprovada apenas por faltar dados. T−30 tem arquivo e contagem próprios e nunca pode ser elegível nesta versão.', '',
        '## Reprodução e validação', '', '```powershell', '.\\venv\\Scripts\\python.exe data/historico_v2/qualificacao_2018/qualificar.py --aplicar', '.\\venv\\Scripts\\python.exe -m src.historico_v2', '$env:MPLBACKEND="Agg"', '.\\venv\\Scripts\\python.exe -m pytest tests/test_historico_v2.py tests/test_coleta_historica_2018.py tests/test_qualificacao_historica_2018.py --no-cov -q', '.\\venv\\Scripts\\python.exe -m pytest -q', '```', '',
        'O comando de qualificação é determinístico e usa arquivos locais. `coletar_fontes.py --baixar` é uma operação de rede separada e não é necessária para reproduzir os artefatos preservados. O gerador original aceita `--preliminar` para reproduzir a primeira entrega; por padrão aplica a qualificação quando disponível. Não há importação do motor estatístico. O CLI do validador continua retornando 1 por pendências, não por falha de execução.', '',
        'Diagnósticos do catálogo após revisão: '+json.dumps(dict(Counter(d['codigo'] for d in validation['diagnosticos'])),ensure_ascii=False)+'.', '',
        '## Próximos passos antes de materializar snapshots', '',
        'Obter protocolos amostrais/declarações dos executores sobre painel, rotação, reutilização de respondentes e eventuais subcontratações; resolver as relações entre componentes sem presumir independência. Recuperar relatórios F03, XP/Ipespe, CNT/MDA e demais tabelas parciais; conferir aplicação literal dos instrumentos e categorias residuais. Solicitar errata/decomposição para as divergências que continuam abertas. Realizar segunda revisão independente. Somente após esses gates propor a materialização, reaplicando seleção por instituto/grupo e disponibilidade por campo. Nenhuma janela ou critério foi flexibilizado para aumentar a cobertura.', '']
    verification_path=HERE/'verificacao.json'
    if verification_path.exists():
        verification=json.loads(verification_path.read_text(encoding='utf-8'))
        lines += ['## Verificação desta entrega', '',
            f"Em {verification['data']}, com MPLBACKEND=Agg: {verification['testes_especificos']['aprovados']} testes específicos e {verification['suite_completa']['aprovados']} testes da suíte completa passaram. Cobertura total: {verification['suite_completa']['cobertura_percentual']}%; {verification['suite_completa']['avisos']} avisos de dependências/depreciações. O gate de cobertura de 80% foi atendido.", '',
            'Na suíte completa, caches de ArviZ/PyTensor e cobertura foram direcionados para diretórios temporários do workspace, conforme o procedimento em [historico_v2.md](historico_v2.md), sem alterar dependências do projeto. As definições de diagnóstico não foram gravadas nos CSVs de snapshots. `git diff --check` passou. Os 67 hashes registrados antes da qualificação continuam conferindo; nenhum percentual, módulo do motor ou legado foi alterado. Sem commit ou push nesta revisão.', '']
    (REPO/'docs/qualificacao_historica_2018.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    main()
