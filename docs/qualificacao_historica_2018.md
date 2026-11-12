# Qualificação documental das pesquisas de 2018

Revisão documental de 31/10/2026. Referências obrigatórias: [coleta preliminar](coleta_historica_2018.md), [contrato v2](historico_v2.md) e [protocolo 2.0.0](../data/historico_v2/protocolo_v2.0.0.json). Protocolo, legados e motor preservados. Sem simulações, backtesting ou materialização de snapshots.

## Resultado e alcance

Esta revisão reduz lacunas de instrumento, identidade e campo, mas **não libera nenhuma pesquisa para a base principal**: a dependência entre componentes institucionais ainda não foi estabelecida documentalmente. Os grupos atribuídos registram relações comprovadas de executor/contratante; não certificam independência estatística. Não houve segunda revisão humana independente. Ausência de erro no validador não substitui esses gates do protocolo.

Há 27 levantamentos e 38 cenários. Nenhum percentual foi alterado, imputado ou normalizado. A versão histórica `documental_01` foi mantida: novas evidências de metadados não constituem uma retificação do resultado eleitoral. A primeira transcrição está preservada em `coleta_2018/transcricoes.json`; o histórico desta revisão registra valores anteriores e evidências substituídas.

## Fontes adicionais e revisão

Foram recuperados 13 questionários oficiais por HTTP Range do acervo TSE: BR-05596, 02410, 03512, 01057, 06478, 03861, 01669, 04669, 05221, 09678, 06630, 00526 e 02995/2018. Registro e questionário comprovam instrumento declarado, não aplicação nem divulgação. Só se preencheu número de pergunta aplicada quando confrontado com o relatório de resultados da mesma coleta. Instrumentos sem esse confronto ficam em coluna separada na matriz.

A Folha de 20/09 (Q001), a Reuters de 20/09 (Q005), Suno de 24/09 (Q002), InfoMoney de 24/09 (Q006) e Gazeta de 24/09 (Q008) foram conferidas. Fontes jornalísticas diferentes não equivalem automaticamente a apurações independentes: Reuters/UOL é uma única agência; publicação do próprio instituto/Folha é do mesmo grupo. A matriz preserva os IDs separados sem duplicar coletas.

A cópia do relatório Datafolha F03 na Lupa (Q004) continuou inacessível: nada nela foi declarado conferido. Q009 retornou 404. Q002, Q003, Q005 e Q007 foram lidos pela ferramenta web, apesar de falha no download HTTP; não há cópia integral local desses documentos. Q007 tem atualização em 04/10, posterior ao corte, e serve somente para corroboração de metadados já documentados em Q008 de 24/09. A checagem da Agência Pública (Q003, 23/10) contém declaração do contratante sobre ausência de tracking exclusivo para o mercado: é contexto posterior, não prova de disponibilidade em setembro nem de independência amostral.

As tentativas e os hashes ficam em `qualificacao_2018/acessos.json` e no catálogo `fontes.csv`; os membros do ZIP estão identificados. A Wikipédia não foi utilizada para comprovar percentuais, datas ou liberar cenários. Páginas recuperadas hoje podem ter sido alteradas desde 2018; não foram autenticadas capturas contemporâneas imutáveis.

## Conflitos e lacunas

- **BR-06919/2018 — valor_pct:bn (pendente_decomposicao_categorias):** S055 p.8 e Q001 tabela BRASIL informam 12 para branco/nulo/nenhum. S055 p.2 e S002 texto informam 11 para branco ou nulo. Há diferença de rótulo potencialmente explicativa, mas não foi localizada decomposição ou errata explícita. Não subtrair 11 de 12 nem retirar a marca de conflito. Fontes: S055|S002|Q001|Q005.
- **BR-03861/2018 — valor_pct:amoedo (pendente_sem_errata):** S033 p.13, BNews e Suno informam 3; Correio informa 4. A evidência reforça a transcrição primária de 3, mas não comprova retificação do documento divergente. Manter alternativas e conflito. Fontes: S033|S066|Q002|Q006.
- **BR-08687/2018 — n_realizado (pendente_relatorio_original):** 9.072 é planejado no cadastro e aparece em notícia; 9.000 é realizado em outra notícia. Nova tentativa da cópia Lupa não recuperou o PDF. Não declarar resolução definitiva. Fontes: S005|S006|S048|Q004.
- **BR-06630/2018 — campo_realizado_e_publicacao (resolvido_lacuna):** Gazeta de 24/09 informa campo 22-23/09, 2.506 entrevistas e BR-06630/2018. UOL de 24/09 confirma, mas está atualizado em 04/10 e é usado só para corroboração. A publicação de TV Brasil em 25/09 não é a primeira divulgação. Preencher campo/amostra e comprovar disponibilidade de metadados em 24/09 por Q008; os resultados existentes permanecem vinculados à fonte S046 de 25/09. Fontes: Q007|Q008|S046.
- **BR-06919/2018 — n_planejado_vs_realizado (resolvido_distincao):** 8.596 planejadas no cadastro versus 8.601 realizadas no relatório p.6 e Reuters. São grandezas diferentes, não corrigir uma pela outra. Fontes: S048|S055|Q005.

Os conflitos de percentuais continuam marcados em `evidencias.csv`. Uma maioria de notícias concordantes não foi tratada como errata. A distinção planejado/realizado e a diferença de rótulos foram registradas sem produzir valores por subtração. Zeros, limites e valores ausentes mantêm os qualificadores da primeira entrega.

Fontes adicionais catalogadas (status de acesso não equivale a comprovação de aplicação):

| ID | Tipo | Acesso | Referência |
|---|---|---|---|
| Q001 | noticia | lido_http_com_copia | [URL original](https://www1.folha.uol.com.br/poder/2018/09/bolsonaro-domina-com-folga-no-df-e-haddad-lidera-em-pe-segundo-datafolha.shtml) |
| Q002 | noticia | lido_web_sem_copia_http | [URL original](https://www.suno.com.br/noticias/btg-pactual-bolsonaro-haddad/) |
| Q003 | noticia | lido_web_sem_copia_http | [URL original](https://apublica.org/checagem/2018/10/truco-pesquisa-falsa-coloca-bolsonaro-com-52-e-haddad-com-48/) |
| Q004 | relatorio | nao_recuperado | [URL original](https://uploads.agencialupa.org/2022/02/4261674.pdf) |
| Q005 | noticia | lido_web_sem_copia_http | [URL original](https://economia.uol.com.br/noticias/reuters/2018/09/20/bolsonaro-vai-a-28-haddad-a-16-e-ciro-mantem-13-diz-datafolha.htm) |
| Q006 | noticia | lido_http_com_copia | [URL original](https://www.infomoney.com.br/politica/bolsonaro-tem-33-dos-votos-e-haddad-vai-de-16-para-23-isolando-se-em-2o-lugar-mostra-pesquisa/) |
| QT05596_1 | registro_pesqele | lido_http_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip) |
| QT02410_1 | registro_pesqele | lido_http_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip) |
| QT03512_1 | registro_pesqele | lido_http_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip) |
| QT01057_1 | registro_pesqele | lido_http_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip) |
| QT06478_1 | registro_pesqele | lido_http_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip) |
| QT03861_1 | registro_pesqele | lido_http_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip) |
| QT01669_1 | registro_pesqele | lido_http_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip) |
| QT04669_1 | registro_pesqele | lido_http_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip) |
| QT05221_1 | registro_pesqele | lido_http_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip) |
| QT09678_1 | registro_pesqele | lido_http_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip) |
| QT06630_1 | registro_pesqele | lido_http_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip) |
| QT00526_1 | registro_pesqele | lido_http_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip) |
| QT02995_1 | registro_pesqele | lido_http_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip) |
| Q007 | noticia | lido_web_sem_copia_http | [URL original](https://noticias.uol.com.br/politica/eleicoes/2018/noticias/2018/09/24/pesquisa-ibope-presidente-24-setembro-bolsonaro-haddad-ciro-alckmin-marina.htm) |
| Q008 | noticia | lido_http_com_copia | [URL original](https://www.gaz.com.br/ibope-bolsonaro-lidera-com-28-e-haddad-aparece-com-22/) |
| Q009 | noticia | nao_recuperado | [URL original](https://www1.folha.uol.com.br/poder/2018/09/bolsonaro-perde-para-ciro-haddad-e-alckmin-no-segundo-turno-aponta-ibope.shtml) |

## Dependência e identidade

Os cenários de uma mesma coleta compartilham pesquisa/versão/grupo. Republicações tornam-se fontes adicionais; não criam novos levantamentos. As relações por CNPJ de executor e CPF/CNPJ de contratante foram recuperadas do membro BR do cadastro S048 e fechadas transitivamente em componentes: uma cadeia de executor comum ou contratante comum permanece em um único grupo conservador. A lista integral de entidades e relações está em `dependencias.csv`. Contratante comum não comprova amostra compartilhada; agrupá-lo evita tratar essas coletas como independentes por conveniência.

Os questionários XP/Ipespe identificam explicitamente **TRACKING TELEFÔNICO NACIONAL**, ondas 18 e 19. Isso documenta a série, mas não informa se há painel, substituição parcial ou respondentes repetidos. Não se deduziu ausência de sobreposição de períodos de campo não coincidentes. Os relatórios FSB descrevem amostras e periodicidade, mas não comprovam independência entre ondas. A declaração posterior de que não há tracking exclusivo ao mercado não prova independência das entrevistas.

O nome atual da empresa no cadastro não renomeia retroativamente a marca. A colisão de BR-02039/2018 continua resolvida pelo CNPJ do executor da coleta de setembro. Um vínculo profissional de um supervisor ou uma notícia sindicada também não prova amostra compartilhada. Não há decisão positiva de independência entre componentes: a classificação final permanece conservadora.

## Matriz por pesquisa e cenário

A [matriz completa em CSV](../data/historico_v2/qualificacao_2018/matriz_qualificacao.csv) contém pergunta aplicada, instrumento registrado adicional, todas as respostas efetivamente transcritas, comprovação de completude, base, campo, publicação, fontes, conflitos, grupo e critérios atendidos/pendentes. Lista parcial é explicitamente parcial. Não se preencheu o resultado ausente a partir da lista do questionário.

| Pesquisa / cenário | Pergunta | Lista comprovada | Campo | Publicação dos resultados | Pendências |
|---|---|---|---|---|---|
| BR-05003-2018 / p04b_haddad | P04B | false | 2018-09-01 a 2018-09-03 | 2018-09-05 | completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_pesquisas.universo, identidade_incompleta |
| BR-06919-2018 / p2_haddad | P.2 | true | 2018-09-18 a 2018-09-19 | 2018-09-20 | campo_sem_evidencia, dependencia_entre_componentes_nao_estabelecida |
| BR-08687-2018 / p2_haddad | P.2 | false | 2018-09-26 a 2018-09-28 | 2018-09-28 | completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_pesquisas.universo, identidade_incompleta |
| BR-05596-2018 / p2_haddad | P.2 | true | 2018-09-13 a 2018-09-14 | 2018-09-17 | dependencia_entre_componentes_nao_estabelecida |
| BR-02410-2018 / cenario1_haddad | P.6 | true | 2018-09-07 a 2018-09-11 | 2018-09-12 | dependencia_entre_componentes_nao_estabelecida |
| BR-03512-2018 / haddad | P.6 | true | 2018-09-23 a 2018-09-25 | 2018-09-26 | dependencia_entre_componentes_nao_estabelecida |
| BR-02891-2018 / cenario1_lula | não comprovada | true | 2018-08-09 a 2018-08-13 | não comprovada | cenario_sem_identidade, dependencia_entre_componentes_nao_estabelecida, divulgacao_resultados_nao_comprovada, falta_cenarios.numero_pergunta |
| BR-02891-2018 / cenario2_haddad | não comprovada | true | 2018-08-09 a 2018-08-13 | não comprovada | cenario_sem_identidade, dependencia_entre_componentes_nao_estabelecida, divulgacao_resultados_nao_comprovada, falta_cenarios.numero_pergunta |
| BR-01057-2018 / haddad | P.11 | true | 2018-09-01 a 2018-09-02 | 2018-09-03 | dependencia_entre_componentes_nao_estabelecida |
| BR-01057-2018 / lula | P.09 | true | 2018-09-01 a 2018-09-02 | 2018-09-03 | dependencia_entre_componentes_nao_estabelecida |
| BR-06478-2018 / haddad | P.09 | true | 2018-09-15 a 2018-09-16 | 2018-09-17 | dependencia_entre_componentes_nao_estabelecida |
| BR-03861-2018 / haddad | P.09 | true | 2018-09-22 a 2018-09-23 | 2018-09-24 | campo_sem_evidencia, dependencia_entre_componentes_nao_estabelecida |
| BR-01669-2018 / lula | não comprovada | false | 2018-09-07 a 2018-09-11 | 2018-09-13 | cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta |
| BR-01669-2018 / haddad_apoio_lula | não comprovada | false | 2018-09-07 a 2018-09-11 | 2018-09-13 | cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta |
| BR-03303-2018 / haddad | não comprovada | false | 2018-09-27 a 2018-09-28 | 2018-09-30 | cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |
| BR-04362-2018 / haddad | não comprovada | false | 2018-09-12 a 2018-09-15 | 2018-09-17 | cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |
| BR-07252-2018 / haddad | não comprovada | false | 2018-08-27 a 2018-08-29 | 2018-08-31 | cenario_incompleto, cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |
| BR-07252-2018 / haddad_apoio_lula | não comprovada | false | 2018-08-27 a 2018-08-29 | 2018-08-31 | cenario_incompleto, cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |
| BR-07252-2018 / lula | não comprovada | false | 2018-08-27 a 2018-08-29 | não comprovada | cenario_incompleto, cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, divulgacao_resultados_nao_comprovada, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |
| BR-00339-2018 / haddad | não comprovada | false | 2018-09-03 a 2018-09-05 | 2018-09-07 | cenario_incompleto, cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |
| BR-00339-2018 / haddad_apoio_lula | não comprovada | false | 2018-09-03 a 2018-09-05 | 2018-09-07 | cenario_incompleto, cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |
| BR-00339-2018 / lula | não comprovada | false | 2018-09-03 a 2018-09-05 | não comprovada | cenario_incompleto, cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, divulgacao_resultados_nao_comprovada, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |
| BR-07277-2018 / haddad | não comprovada | false | 2018-09-10 a 2018-09-12 | 2018-09-14 | cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |
| BR-07277-2018 / haddad_apoio_lula | não comprovada | false | 2018-09-10 a 2018-09-12 | 2018-09-14 | cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |
| BR-02995-2018 / haddad | não comprovada | false | 2018-09-17 a 2018-09-19 | 2018-09-21 | cenario_incompleto, cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta |
| BR-02995-2018 / haddad_apoio_lula | não comprovada | false | 2018-09-17 a 2018-09-19 | não comprovada | cenario_incompleto, cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, divulgacao_resultados_nao_comprovada, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta |
| BR-00526-2018 / haddad | não comprovada | false | 2018-09-24 a 2018-09-26 | 2018-09-28 | cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta |
| BR-01665-2018 / haddad | não comprovada | false | 2018-08-17 a 2018-08-19 | 2018-08-20 | cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |
| BR-01665-2018 / lula | não comprovada | false | 2018-08-17 a 2018-08-19 | 2018-08-20 | cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |
| BR-09086-2018 / lula | não comprovada | false | 2018-08-15 a 2018-08-18 | 2018-08-20 | base_pergunta_invalida, cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |
| BR-09086-2018 / transferencia_lula_haddad | não comprovada | false | 2018-08-15 a 2018-08-18 | 2018-08-20 | base_pergunta_invalida, cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |
| BR-05221-2018 / haddad | não comprovada | false | 2018-09-08 a 2018-09-10 | 2018-09-11 | cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |
| BR-09678-2018 / haddad | não comprovada | false | 2018-09-16 a 2018-09-18 | 2018-09-18 | cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |
| BR-06630-2018 / haddad | não comprovada | false | 2018-09-22 a 2018-09-23 | 2018-09-25 | cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.base_amostral, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta |
| BR-04669-2018 / haddad | P04 | true | 2018-09-22 a 2018-09-24 | 2018-09-26 | dependencia_entre_componentes_nao_estabelecida |
| BR-00592-2018 / haddad | não comprovada | false | 2018-09-25 a 2018-09-26 | 2018-09-27 | cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |
| BR-01687-2018 / haddad | não comprovada | false | ? a ? | 2018-09-21 | cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.data_fim_campo, falta_pesquisas.data_inicio_campo, falta_pesquisas.universo, identidade_incompleta |
| BR-02039-2018 / haddad | não comprovada | false | 2018-09-19 a 2018-09-20 | 2018-09-21 | cenario_sem_identidade, completude_nao_comprovada, dependencia_entre_componentes_nao_estabelecida, falta_cenarios.numero_pergunta, falta_cenarios.texto_pergunta, falta_pesquisas.universo, identidade_incompleta |

## Diagnóstico por corte e horizonte

O validador original foi executado sem alteração. Para obter diagnósticos temporais, foram construídas definições de corte **somente em memória**, com as datas e janelas do protocolo. Os dois CSVs de snapshots continuam vazios. Os JSONs `validador_DATA_Nd.json` são saídas de diagnóstico, não snapshots nem vínculos materializados.

O universo comum de diagnóstico é a lista comprovada dos 13 candidatos com Haddad, primeiro turno estimulado, percentuais totais, sem associação explícita a Lula. O alias canônico depende do conjunto completo comprovado, não da URL da fonte. Não altera listas incompletas nem funde perguntas/respostas. A definição permite comparar os cenários pós-substituição; T−30 permanece estrato separado não avaliável.

Há duas camadas: `elegivel_validador` relata o resultado mecânico (inclui seleção de onda); `elegivel_qualificacao` exige também a pendência documental de dependência resolvida. Não se deve usar a primeira coluna como autorização para exportar. Uma onda superada é exclusão pela regra de seleção, não incompatibilidade metodológica. Os motivos integrais são preservados, pois uma linha pode falhar em mais de um critério.

| Corte | Janela | Elegíveis no validador | Elegíveis após qualificação |
|---|---:|---:|---:|
| 2018-09-23 | 28 | 3 | 0 |
| 2018-09-23 | 14 | 3 | 0 |
| 2018-09-23 | 42 | 3 | 0 |
| 2018-09-30 | 28 | 3 | 0 |
| 2018-09-30 | 14 | 3 | 0 |
| 2018-09-30 | 42 | 3 | 0 |
| 2018-09-07 | 28 | 0 | 0 |
| 2018-09-07 | 14 | 0 | 0 |
| 2018-09-07 | 42 | 0 | 0 |

Classificações finais para a janela principal (28 dias):

| Corte | Classificação | Cenários |
|---|---|---:|
| 2018-09-23 | inelegivel_fora_janela | 6 |
| 2018-09-23 | inelegivel_incompatibilidade_metodologica | 1 |
| 2018-09-23 | inelegivel_informacao_posterior | 8 |
| 2018-09-23 | quarentena_documentacao_insuficiente | 23 |
| 2018-09-30 | inelegivel_fora_janela | 9 |
| 2018-09-30 | inelegivel_incompatibilidade_metodologica | 1 |
| 2018-09-30 | quarentena_documentacao_insuficiente | 28 |
| 2018-09-07 | nao_avaliavel_transicao | 38 |

A prioridade de apresentação é transição, informação posterior, fora da janela, incompatibilidade comprovada e quarentena. Lista incompleta/identidade não comprovada fica em quarentena, não é rotulada como incompatibilidade comprovada apenas por faltar dados. T−30 tem arquivo e contagem próprios e nunca pode ser elegível nesta versão.

## Reprodução e validação

```powershell
.\venv\Scripts\python.exe data/historico_v2/qualificacao_2018/qualificar.py --aplicar
.\venv\Scripts\python.exe -m src.historico_v2
$env:MPLBACKEND="Agg"
.\venv\Scripts\python.exe -m pytest tests/test_historico_v2.py tests/test_coleta_historica_2018.py tests/test_qualificacao_historica_2018.py --no-cov -q
.\venv\Scripts\python.exe -m pytest -q
```

O comando de qualificação é determinístico e usa arquivos locais. `coletar_fontes.py --baixar` é uma operação de rede separada e não é necessária para reproduzir os artefatos preservados. O gerador original aceita `--preliminar` para reproduzir a primeira entrega; por padrão aplica a qualificação quando disponível. Não há importação do motor estatístico. O CLI do validador continua retornando 1 por pendências, não por falha de execução.

Diagnósticos do catálogo após revisão: {"base_pergunta_invalida": 1, "campo_sem_evidencia": 2, "cenario_incompleto": 3, "cenario_sem_identidade": 27, "identidade_incompleta": 14}.

## Próximos passos antes de materializar snapshots

Obter protocolos amostrais/declarações dos executores sobre painel, rotação, reutilização de respondentes e eventuais subcontratações; resolver as relações entre componentes sem presumir independência. Recuperar relatórios F03, XP/Ipespe, CNT/MDA e demais tabelas parciais; conferir aplicação literal dos instrumentos e categorias residuais. Solicitar errata/decomposição para as divergências que continuam abertas. Realizar segunda revisão independente. Somente após esses gates propor a materialização, reaplicando seleção por instituto/grupo e disponibilidade por campo. Nenhuma janela ou critério foi flexibilizado para aumentar a cobertura.

## Verificação desta entrega

Em 2026-10-31, com MPLBACKEND=Agg: 54 testes específicos e 701 testes da suíte completa passaram. Cobertura total: 90.81%; 14 avisos de dependências/depreciações. O gate de cobertura de 80% foi atendido.

Na suíte completa, caches de ArviZ/PyTensor e cobertura foram direcionados para diretórios temporários do workspace, conforme o procedimento em [historico_v2.md](historico_v2.md), sem alterar dependências do projeto. As definições de diagnóstico não foram gravadas nos CSVs de snapshots. `git diff --check` passou. Os 67 hashes registrados antes da qualificação continuam conferindo; nenhum percentual, módulo do motor ou legado foi alterado. Sem commit ou push nesta revisão.
