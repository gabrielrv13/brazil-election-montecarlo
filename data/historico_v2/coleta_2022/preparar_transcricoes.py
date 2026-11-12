"""Curadoria explícita de transcrições; não extrai nem estima percentuais.

Executado separadamente do gerador. As linhas são conferidas nas fontes indicadas;
uma lista parcial nunca é promovida a lista completa pela soma dos percentuais.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOMES = dict(lula='Lula', bolsonaro='Jair Bolsonaro', ciro='Ciro Gomes',
             tebet='Simone Tebet', janones='André Janones', pablo='Pablo Marçal',
             vera='Vera Lúcia', sofia='Sofia Manzano', felipe="Felipe D’Avila",
             santos='Santos Cruz', bivar='Luciano Bivar', eymael='José Maria Eymael',
             leo='Léo Péricles', soraya='Soraya Thronicke', roberto='Roberto Jefferson',
             kelmon='Padre Kelmon', bn='Branco/nulo', ns='Não sabe/não respondeu',
             nenhum='Nenhum', outros='Outros', bni='Brancos/nulos/indecisos (agregado)',
             bna='Branco/nulo/não comparecer (agregado)')
QUESTION = ('Se a eleição para presidente fosse hoje e os candidatos fossem estes '
            '(MOSTRE CARTÃO 1), em quem você votaria?')
EARLY = ('Alguns nomes já estão sendo cogitados como candidatos a presidente esse ano. '
         'Se a eleição para presidente fosse hoje e os candidatos fossem estes '
         '(MOSTRE CARTÃO), em quem você votaria?')


def preparar():
    polls = []

    def add(reg, instituto, campo, n, fonte, publicacao, valores, *, pagina='',
            metodo='', pergunta='', nota='', nomes=None):
        item = dict(registro=reg, instituto=instituto, campo=campo.split('/') if campo else ['', ''],
                    n_realizado=str(n) if n else '', fonte=fonte, publicacao=publicacao,
                    pagina=pagina or 'corpo: primeiro turno estimulado e metodologia',
                    metodo=metodo, pergunta=pergunta, nota=nota, cenarios=[])
        item['cenarios'].append(dict(id='estimulada_totais', tipo='estimulada', base='totais',
                                     valores=valores, nomes=nomes or {}))
        polls.append(item)
        return item

    df = 'presencial em pontos de fluxo'
    first = 'lula bolsonaro ciro janones tebet pablo vera sofia felipe santos bivar eymael leo bn ns'

    def vector(names, values):
        return dict(zip(names.split(), values.split(), strict=True))

    add('09088','Datafolha','2022-06-22/2022-06-23',2556,'F22_DFPDF0623','2022-06-24',
        vector(first,'47 28 8 2 1 1 1 0 0 0 0 0 0 7 4'),pagina='PDF p.2 metodologia; p.9 tabela estimulada, coluna 22 e 23/06',
        metodo=df,pergunta=EARLY,nomes={'bn':'Em branco/nulo/nenhum'},
        nota='Disponibilidade conservadora do PDF em 24/06; notícia SBT F22_DF0623 em 23/06 é fonte adicional, não data presumida do PDF.')
    add('01192','Datafolha','2022-07-27/2022-07-28',2556,'F22_DFPDF0728','2022-07-29',
        vector(first,'47 29 8 1 2 1 1 0 0 0 0 0 0 6 3'),pagina='PDF p.2 metodologia; p.9 estimulada, coluna 27 e 28/07',
        metodo=df,pergunta=EARLY,nomes={'bn':'Em branco/nulo/nenhum'},nota='Notícia SBT em 28/07; PDF localizado na publicação primária de 29/07.')
    add('09404','Datafolha','2022-08-16/2022-08-18',5744,'F22_DFPDF0818','2022-08-19',
        vector('lula bolsonaro ciro tebet vera pablo roberto felipe sofia leo soraya eymael bn ns',
               '47 32 7 2 1 0 0 0 0 0 0 0 6 2'),pagina='PDF p.2 metodologia; p.10 estimulada, última coluna 16 a 18/08',
        metodo=df,pergunta=QUESTION,nomes={'bn':'Em branco/nulo/nenhum'},
        nota='5.744 entrevistas realizadas; amostra base de 2.556 mais ampliações não é n realizado. Traços nas colunas de nomes retirados não são zeros.')
    add('00433','Datafolha','2022-08-30/2022-09-01',5734,'F22_DF0901','2022-09-01',
        vector('lula bolsonaro ciro tebet soraya pablo felipe vera sofia eymael leo roberto bn ns',
               '45 32 9 5 1 1 1 0 0 0 0 0 4 2'),metodo=df,
        nota='CNN atualizada em 02/09: disponibilidade desta versão em 02/09. Instrumento TSE ESTIMU não comprova sozinho a pergunta aplicada.')
    add('07422','Datafolha','2022-09-08/2022-09-09',2676,'F22_DFPDF0909','2022-09-10',
        vector('lula bolsonaro ciro tebet soraya pablo felipe sofia vera leo eymael kelmon bn ns',
               '45 34 7 5 1 0 0 0 0 0 0 0 4 3'),pagina='PDF p.2 metodologia; p.10 estimulada, coluna 08 e 09/09',metodo=df,pergunta=QUESTION,
        nomes={'bn':'Em branco/nulo/nenhum'})
    add('04099','Datafolha','',5926,'F22_DF0915','2022-09-15',
        vector('lula bolsonaro ciro tebet soraya felipe sofia vera leo eymael kelmon bn ns',
               '45 33 8 5 2 0 0 0 0 0 0 4 2'),metodo=df,
        nota='CNN contém campo "terça-feira (13) e esta quinta (9)". Não corrigir para 15 por inferência; campo realizado pendente. Atualização em 16/09.')
    p = add('04180','Datafolha','2022-09-20/2022-09-22',6754,'F22_DFPDF0922','2022-09-23',
        vector('lula bolsonaro ciro tebet soraya felipe sofia vera leo eymael kelmon bn ns',
               '47 33 7 5 1 0 0 0 0 0 0 4 2'),pagina='PDF p.2 metodologia; p.9 estimulada, coluna 20 a 22/09',metodo=df,pergunta=QUESTION,
        nomes={'bn':'Em branco/nulo/nenhum'},nota='PDF disponível conservadoramente em 23/09. Notícia CNN de 22/09 é fonte adicional. Prosa primária escreve Simone Thronicke; tabela identifica Soraya.')
    p['cenarios'].append(dict(id='estimulada_validos_parcial',tipo='estimulada',base='validos',
        valores=vector('lula bolsonaro ciro tebet soraya','50 35 7 5 2'),fonte='F22_DF0923',
        publicacao='2022-09-23',pagina='corpo: votos válidos',nomes={}))
    add('03980','Ipec','2022-08-12/2022-08-14',2000,'F22_IPEC0815','2022-08-15',
        vector('lula bolsonaro ciro tebet vera eymael felipe leo pablo sofia soraya bn ns',
               '44 32 6 2 1 0 0 0 0 0 0 8 7'),metodo='presencial domiciliar')
    p = add('01979','Ipec','2022-08-26/2022-08-28',2000,'F22_IPEC0829','2022-08-29',
        vector('lula bolsonaro ciro tebet felipe eymael leo roberto sofia soraya vera bni',
               '44 32 7 3 1 <1 <1 <1 <1 <1 <1 13'),metodo='presencial domiciliar',
        nota='Fonte agrega brancos, nulos e indecisos em 13%; não decompor. Menos de 1% é limite publicado, não zero. Número de municípios requer confronto.')
    p['cenarios'].append(dict(id='espontanea_totais_parcial',tipo='espontanea',base='totais',
        valores=vector('lula bolsonaro ciro tebet','40 31 4 2'),nomes={},pagina='corpo: pesquisa espontânea'))
    add('00922','Ipec','',2512,'F22_IPEC0905','2022-09-05',
        vector('lula bolsonaro ciro tebet felipe soraya vera eymael pablo leo sofia roberto bn ns',
               '44 31 8 4 1 1 0 0 0 0 0 0 6 5'),metodo='presencial domiciliar',
        nota='Campo conflitante: UOL 30/08–05/09; outras publicações 02–04/09. Não preencher campo realizado. UOL atualizada em 06/09, sem cópia HTTP local.')
    add('01390','Ipec','2022-09-09/2022-09-11',2512,'F22_IPEC0912','2022-09-12',
        vector('lula bolsonaro ciro tebet felipe soraya eymael leo sofia vera kelmon bn ns',
               '46 31 7 4 1 1 0 0 0 0 0 6 4'),metodo='presencial domiciliar')
    add('00073','Ipec','2022-09-17/2022-09-18',3008,'F22_IPEC0919','2022-09-19',
        vector('lula bolsonaro ciro tebet soraya bn ns','47 31 7 5 1 5 4'),metodo='presencial domiciliar',
        nota='Transcrição parcial: demais candidatos não recuperados nesta tabela; divulgação posterior ao corte de 18/09, apesar de registro anterior.')
    add('05022','FSB','2022-06-24/2022-06-26',2000,'F22_FSB0627','2022-06-27',
        vector('lula bolsonaro ciro tebet janones pablo felipe eymael vera sofia bivar leo nenhum bn ns',
               '43 33 8 3 2 1 0 0 0 0 0 0 5 1 2'),pagina='PDF p.4 metodologia; p.12 primeiro turno estimulado',metodo='CATI por telefone',
        pergunta='Agora, se as eleições para Presidente da República fossem hoje e os candidatos fossem estes que vou ler, em quem você votaria para presidente do Brasil? Por favor, espere eu ler todos os nomes antes de dar sua resposta. (ESTIMULADA E ÚNICA)',
        nota='Seis zeros arredondados somam conjuntamente 1% segundo nota da p.12; não normalizar. Cópia do relatório original hospedada em veículo jornalístico; notícia contemporânea F22_FSB0627N corrobora divulgação.')
    add('05938','FSB','2022-07-22/2022-07-24',2000,'F22_FSB0725','2022-07-25',
        vector('lula bolsonaro ciro tebet janones pablo nenhum bn ns','44 31 9 2 2 1 5 2 3'),metodo='telefone',
        nota='Lista parcial: demais nomes não identificados. Bloomberg F22_FSB0725N tem 32 no subtítulo e 31 no corpo para Bolsonaro; conflito não resolvido.')
    p = add('07560','FSB','2022-09-16/2022-09-18',2000,'F22_FSB0919','2022-09-19',
        vector('lula bolsonaro ciro tebet soraya bn ns','44 35 7 5 1 4 3'),metodo='telefone',
        nota='Totais parcialmente recuperados; demais candidatos não convertidos em zero. F22_FSB0919, Agência Estado/UOL, lida na web sem cópia HTTP.')
    p['cenarios'].append(dict(id='estimulada_validos_parcial',tipo='estimulada',base='validos',
        valores=vector('lula bolsonaro ciro tebet outros','47 37 8 6 2'),fonte='F22_FSB0919V',nomes={},pagina='corpo: votos válidos; demais candidatos agregados'))
    add('02546','Quaest','2022-07-28/2022-07-31',2000,'F22_QUA0803','2022-08-03',
        vector('lula bolsonaro ciro janones tebet pablo vera eymael sofia felipe bivar leo bn ns',
               '44 32 5 2 2 1 np np np np np np 6 6'),metodo='presencial domiciliar',
        nota='Não pontuaram preservado sem valor numérico. F22_QUA0803N é fonte adicional, não levantamento distinto.')
    add('00585','Quaest','2022-08-25/2022-08-28',2000,'F22_QUA0831','2022-08-31',
        vector('lula bolsonaro ciro tebet vera pablo felipe eymael sofia soraya leo bna ns',
               '44 32 8 3 1 1 np np np np np 5 6'),metodo='presencial domiciliar',
        nota='Conflito: Folha atribui 1% a Pablo Marçal; UOL F22_QUA0831N atribui 1% a Felipe D’Avila. Preservar versões sem decidir por maioria. Categoria branco/nulo/não comparecer é agregada, não branco/nulo simples.')
    add('04459','Quaest','2022-09-17/2022-09-20',2000,'F22_QUA0921','2022-09-21',
        vector('lula bolsonaro ciro tebet','44 34 6 5'),metodo='presencial domiciliar',nota='Tabela recuperada parcialmente, sem imputar demais respostas.')
    add('07003','PoderData','2022-06-19/2022-06-21',3000,'F22_PD0622','2022-06-22',
        vector('lula bolsonaro ciro janones tebet bivar eymael felipe sofia pablo leo vera',
               '44 34 6 2 1 1 1 np np np np np'),metodo='telefone fixo e móvel',nota='Respostas residuais não transcritas por ausência na notícia; não pontuou não equivale a zero exato.')
    add('06550','PoderData','2022-07-03/2022-07-05',3000,'F22_PD0706','2022-07-06',
        vector('lula bolsonaro ciro','44 36 5'),metodo='telefone',nota='Transcrição parcial; campo encerra e publicação ocorrem após o corte corrigido de 04/07.')
    add('08398','PoderData','2022-07-31/2022-08-02',3500,'F22_PD0804','2022-08-04',
        vector('lula bolsonaro ciro tebet janones felipe eymael','43 35 7 4 2 1 1'),metodo='telefone',
        nota='Divulgação em 04/08 posterior ao corte de 03/08; 3.500 entrevistados segundo fonte contemporânea. Respostas residuais pendentes.')
    add('00407','PoderData','2022-09-18/2022-09-20',3500,'F22_PD0921','2022-09-21',
        vector('lula bolsonaro ciro tebet felipe soraya eymael leo kelmon sofia vera',
               '44 37 7 4 1 1 np np np np np'),metodo='telefone',nota='Respostas residuais não recuperadas.')
    add('09408','Paraná Pesquisas','2022-06-30/2022-07-05',None,'F22_PAR0706','2022-07-06',
        vector('lula bolsonaro ciro tebet janones pablo vera felipe bivar outros bn ns',
               '41.1 35.1 7.4 2.2 1.5 0.6 0.6 0.4 0.3 0.4 6.6 3.7'),metodo='presencial',
        nota='Amostra realizada total não transcrita por soma das regiões. Registro informa 2.020 planejadas. Publicação posterior ao corte de 04/07.')
    add('09417','Paraná Pesquisas','2022-09-15/2022-09-19',2020,'F22_PAR0920','2022-09-20',
        vector('lula bolsonaro ciro tebet soraya felipe sofia vera kelmon eymael leo bn ns',
               '40.1 36.4 7.2 4.6 0.7 0.2 0.2 0.2 0.1 np np 5.6 4.7'),metodo='presencial',
        nota='Texto compara valores anteriores de maneira aritmeticamente inconsistente; transcrever apenas coluna atual, sem reconstruir anterior. Atualização relativa sem data exata conhecida.')
    for p in polls:
        if p['fonte'].startswith('F22_DFPDF'):
            p['metadados_adicionais'] = dict(universo='Eleitores brasileiros com 16 anos ou mais',
                margem_erro_pp='2',nivel_confianca_pct='95')
        if p['registro'] == '09408':
            p['metadados_adicionais'] = dict(universo='Eleitores com 16 anos ou mais',
                margem_erro_pp='2.2',nivel_confianca_pct='95')
    return {'versao':'documental_01','revisao':'2026-10-31','nomes':NOMES,'pesquisas':polls,
            'politica':'Todos em quarentena; dependência e segunda conferência pendentes; nenhum snapshot.'}


if __name__ == '__main__':
    (HERE/'transcricoes.json').write_text(json.dumps(preparar(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
