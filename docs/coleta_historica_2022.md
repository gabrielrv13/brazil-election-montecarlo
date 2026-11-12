# Coleta documental das pesquisas presidenciais de 2022

Entrega preliminar de 31/10/2026. Referências obrigatórias: [plano](plano_reconstrucao_historica.md), [coleta 2018](coleta_historica_2018.md), [qualificação 2018](qualificacao_historica_2018.md), [contrato histórico v2](historico_v2.md) e [protocolo congelado 2.0.0](../data/historico_v2/protocolo_v2.0.0.json).

## Estado documental

O fragmento separado contém **24 levantamentos, 27 cenários, 291 respostas, 48 fontes e 2.191 evidências de campo**. Todos os levantamentos e cenários permanecem em quarentena. Há transcrições parciais; a quantidade de respostas não comprova completude. Dependência, confronto integral do instrumento e segunda conferência estão pendentes. Nenhuma pesquisa foi liberada para backtesting. Os dois CSVs de snapshots têm somente cabeçalhos.

Os sete CSVs estão em `data/historico_v2/coleta_2022/catalogo/`, com os cabeçalhos do esquema v2 existente. Os CSVs da raiz v2 continuam representando a coleta de 2018, sem mescla. Não houve alteração de protocolo, legado, motor, coleta anterior ou outputs locais, nem execução de simulações ou materialização de snapshots. `preservacao.json` registra hashes de 281 arquivos preexistentes para conferência local; outputs não distribuídos continuam fora dos requisitos de reprodução após checkout.

## Busca sistemática

O ZIP oficial do TSE foi preservado integralmente. Seu membro `pesquisa_eleitoral_2022_BR.csv` tem 1.192 linhas; a triagem por cargo Presidente e fim **declarado** entre 23/05 e 25/09/2022 produziu **658 registros distintos**, detalhados em `catalogo/inventario_registros.csv`. Esse intervalo é a união das janelas de até 42 dias dos cinco cortes congelados. Não é um censo comprovado de pesquisas nacionais divulgadas: códigos BR também aparecem em pesquisas territoriais restritas. O plano amostral e a metodologia cadastrais permanecem no inventário para revisão territorial individual.

Dos 658 registros, 24 têm resultados ao menos parcialmente recuperados nesta entrega; **634 continuam sem transcrição de resultados**. Essa diferença explicita o universo de lacunas, incluindo registros que podem ser locais, não executados ou não divulgados. Nenhuma dessas hipóteses é automaticamente classificada como fato. Não se substituiu campo efetivo por cronograma registrado, nem amostra realizada pela cadastrada. Contratantes são ligados pelo código oficial; ambiguidades não autorizam escolher arbitrariamente uma entidade. A matriz conserva também o CNPJ e nome legal do executor.

A Wikipédia de 2022 foi usada como índice auxiliar de descoberta, sem evidenciar qualquer percentual, data ou cenário. O download HTTP dela falhou, embora a página tenha sido consultada pela ferramenta web. A busca incluiu TSE, Datafolha, relatórios FSB e publicações contemporâneas de CNN, Folha, SBT, InfoMoney, Agência Brasil, Agência Estado, Bloomberg Línea, O POVO, JC e Bahia Notícias. Diferentes veículos podem republicar a mesma agência; não são necessariamente confirmações independentes.

O acesso direto à interface PesqEle retornou 403. Os ZIPs de cadastros e contratantes foram recuperados. Quatro questionários oficiais foram recuperados por HTTP Range, sem baixar integralmente o arquivo grande de questionários. `indice_questionarios.json` preserva a listagem de membros; `acessos_questionarios.json` identifica membro, URL, data, bytes e hash de cada PDF. Questionário e registro comprovam instrumento declarado, nunca aplicação ou divulgação de resultados por si sós.

## Identidade, versões e transcrição

Os IDs de coleta usam `BR-<registro>-2022`, conferidos contra o CNPJ do executor no cadastro. O gerador exige identidade cadastral não ambígua para cada coleta transcrita. `documental_01` identifica a versão documental inicial; republicações são fontes adicionais da mesma pesquisa. Não foram inventadas retificações nem ondas novas a partir de matérias sobre a mesma coleta. Uma futura correção factual exige preservar esta versão e documentar a nova disponibilidade.

Cada cenário tem ID próprio por pergunta/base. Há 24 cenários estimulados sobre totais, dois cenários **parciais** sobre válidos e um espontâneo **parcial**. Segundo turno, rejeição e aprovação encontrados nas mesmas fontes não foram misturados às respostas de primeiro turno. O inventário de registros não permite classificar turno/pergunta de entradas ainda não recuperadas.

As tabelas originais dos seis relatórios Datafolha/FSB utilizados para transcrição foram conferidas visualmente. Foram usadas as colunas correntes, sem reconstruir ondas anteriores a partir de tabelas comparativas que retiram candidatos. Traços e asteriscos não viram zeros. Os nomes técnicos e aliases estão em `transcricoes.json` e `preparar_transcricoes.py`; a evidência indica a resposta e a expressão publicada. Os conjuntos `candidatos_ids` e `respostas_ids` descrevem **apenas o conteúdo recuperado**, não uma declaração de lista integral. Todos os cenários têm `completo=false`.

Zeros impressos permanecem `zero_arredondado`; não são tratados como contagem observada de zero entrevistas. “Não pontuou” conserva valor vazio e qualificador próprio. “Menos de 1%” conserva o limite 1 com `menor_que`. O agregado de brancos/nulos/indecisos de Ipec 29/08 e o agregado que inclui não comparecimento da Quaest 31/08 permanecem respostas `outros` com rótulo explícito; não foram decompostos. A nota FSB de 27/06 informa que candidatos publicados como zero somam conjuntamente 1%; não houve redistribuição nem normalização.

Metadados desconhecidos, inclusive base amostral efetiva ponderada, universo sem comprovação na fonte utilizada, número da pergunta e ordem do cartão, continuam vazios. Amostra base de 2.556 mais expansões na Datafolha não foi confundida com as 5.744 ou 6.754 entrevistas efetivamente realizadas. A amostra Paraná de julho não foi preenchida somando números regionais. Campos comprovados têm vínculos individuais em `evidencias.csv`, com localização e decisão de normalização. Isso registra uma primeira transcrição; não substitui segunda revisão independente ou autenticação da fonte.

## Disponibilidade e conflitos

Datas de publicação e atualização ficam em `anotacoes_fontes.json` e `fontes.csv`. A disponibilidade é conservadoramente a maior dessas datas, quando a atualização absoluta é conhecida. PDFs são datados pela página que os disponibilizou, sem supor que o arquivo completo estava disponível no dia de uma notícia anterior. Datas atuais de acesso e geração do acervo cadastral não viram prova histórica.

Páginas atuais podem ter sido alteradas desde 2022. Não foram autenticadas capturas imutáveis contemporâneas. Quando só há atualização relativa ou ausência de histórico editorial, a limitação permanece em quarentena. Os horários são mantidos nas cópias originais; o esquema usa dia civil inclusivo conforme o protocolo.

Conflitos e decisões estão preservados em `conflitos.json`:

- **FSB BR-05938/2022:** Bloomberg informa Bolsonaro 32 no subtítulo e 31 no corpo; a Agência Brasil informa 31. Conservou-se a transcrição 31, com conflito nas evidências, sem declarar errata resolvida.
- **Quaest BR-00585/2022:** Folha atribui 1% a Pablo Marçal e não pontuação a Felipe D’Avila; UOL atribui 1% a Felipe. As alternativas estão registradas; não se combinam as listas.
- **Ipec BR-00922/2022:** UOL informa campo 30/08–05/09; Folha informa 02–04/09. O campo realizado ficou vazio, preservando o cronograma apenas no inventário.
- **Datafolha BR-04099/2022:** CNN escreve “terça-feira (13)” e “quinta (9)”. Não se corrigiu automaticamente para 15; campo realizado continua vazio. Tabela comparativa posterior existe no PDF de 22/09, mas não foi utilizada retroativamente para liberar o corte de 18/09.
- **Datafolha BR-04180/2022:** a prosa escreve Simone Thronicke; a tabela identifica Soraya. Transcreveu-se a tabela sem confundir Soraya com Simone Tebet.
- **Paraná BR-09417/2022:** comparação interna com a onda anterior é inconsistente. Preservaram-se somente os valores atuais diretamente publicados, sem reconstruir a onda anterior.

Agência Estado/UOL FSB 19/09, UOL Quaest 31/08 e UOL Ipec 05/09 foram lidas na web, mas a cópia HTTP integral não foi obtida. O status distingue essas situações das fontes copiadas e das não recuperadas. As referências originais e os diagnósticos da tentativa continuam nos logs; a reprodução offline recompõe a transcrição registrada, mas não permite reconferir integralmente essas páginas sem nova obtenção.

## Dependência e cobertura

O CNPJ identifica executores compartilhados entre ondas; contratantes e fontes da mesma coleta estão na matriz. Isso não comprova independência entre ondas, entre executores ou entre amostras. Sobreposição, tracking, painéis e relações societárias ainda precisam de revisão documental. `grupo_dependencia_id` permanece vazio, sem criar grupos artificiais para liberar pesquisas. A mesma pesquisa pode aparecer em vários cortes diagnósticos, mantendo uma única linha em `pesquisas`.

As contagens abaixo exigem campo realizado conhecido e disponibilidade documentada até o corte, com idade inclusiva de 0 a N dias. **Compatibilidade temporal não é elegibilidade final**: não aplica completude, compatibilidade integral do cenário, dependência ou seleção por instituto. Publicações posteriores, campos conflitantes e observações fora da janela constam individualmente em `cobertura_documental.csv`.

| Corte | Janela | Levantamentos temporalmente compatíveis | Cenários |
|---|---:|---:|---:|
| 04/07/2022 | 14 | 3 | 3 |
| 04/07/2022 | 28 | 3 | 3 |
| 04/07/2022 | 42 | 3 | 3 |
| 03/08/2022 | 14 | 3 | 3 |
| 03/08/2022 | 28 | 3 | 3 |
| 03/08/2022 | 42 | 7 | 7 |
| 02/09/2022 | 14 | 3 | 4 |
| 02/09/2022 | 28 | 5 | 6 |
| 02/09/2022 | 42 | 9 | 10 |
| 18/09/2022 | 14 | 2 | 2 |
| 18/09/2022 | 28 | 5 | 6 |
| 18/09/2022 | 42 | 7 | 8 |
| 25/09/2022 | 14 | 7 | 9 |
| 25/09/2022 | 28 | 11 | 14 |
| 25/09/2022 | 42 | 13 | 16 |

Em todos os cortes e janelas, a elegibilidade final desta entrega é **zero**. PoderData de 04/08 não é liberada em 03/08; Ipec de 19/09 não é liberada em 18/09, ainda que o campo tenha encerrado no corte. Os cortes legados incorretos não foram reutilizados.

## Reprodução e diagnósticos

As entradas são `transcricoes.json`, `anotacoes_fontes.json`, `conflitos.json`, logs de acesso, os dois ZIPs oficiais e documentos sob `data/historico_v2/documentos/2022/`. `fontes_planejadas.json` relaciona as URLs; `fontes_complementares.json` preserva um lote de descoberta já incorporado, sem necessidade de nova mescla. `.gitattributes` preserva os bytes originais. No inventário derivado, apenas espaços finais das linhas de metodologia/plano foram removidos; os ZIPs originais estão intactos. Nenhum arquivo individual necessário excede 5 MB; o ZIP completo de questionários não está incluído nem é necessário para gerar o catálogo.

Na raiz do projeto:

```powershell
# Reprodução offline: não consulta a rede nem escreve na coleta de 2018.
.\venv\Scripts\python.exe data/historico_v2/coleta_2022/gerar_catalogo.py
# Destino alternativo deve estar vazio e fora da árvore histórica protegida.
.\venv\Scripts\python.exe data/historico_v2/coleta_2022/gerar_catalogo.py --destino .work_repro_2022
.\venv\Scripts\python.exe -m src.historico_v2 data/historico_v2/coleta_2022/catalogo
```

O validador retorna código **1**, esperado por pendências: 24 diagnósticos `identidade_incompleta`, 27 `cenario_sem_identidade`, cinco `cenario_incompleto` por não pontuação sem valor, e três `campo_sem_evidencia` nos cenários com conflitos. Não há erro de chave, referência, formato percentual ou data. Não há decisões de snapshots porque eles não foram criados. O arquivo `diagnostico_validacao.json` é reproduzido diretamente pela API independente do motor.

Para obter novamente as fontes (opcional, com rede; arquivos atuais podem ter mudado):

```powershell
.\venv\Scripts\python.exe data/historico_v2/coleta_2022/coletar_fontes.py --baixar
.\venv\Scripts\python.exe data/historico_v2/coleta_2022/recuperar_questionarios.py --baixar
```

O coletor pula IDs já presentes em `acessos.json`; para repetir uma tentativa, usar uma cópia de trabalho e remover ali a entrada correspondente, preservando o log original. O recuperador de questionários requer HTTP Range e valida respostas parciais. Dependências de download: `requests`; extração auxiliar de texto: `pypdf`, com páginas delimitadas; conferência visual: PyMuPDF. PDFs e HTML são as evidências originais; `.txt` é derivado auxiliar e pode conter problemas de codificação de fontes do PDF. Nenhum extrator participa da geração dos percentuais.

`preparar_transcricoes.py` reproduz o JSON curado; não lê a Wikipédia nem estima valores. Após mudanças documentais aprovadas, executar esse script antes do gerador. Uma reprodução da versão entregue usa diretamente o JSON preservado.

```powershell
$env:MPLBACKEND='Agg'
.\venv\Scripts\python.exe -m pytest tests/test_coleta_historica_2022.py tests/test_historico_v2.py tests/test_coleta_historica_2018.py tests/test_qualificacao_historica_2018.py --no-cov -q -p no:cacheprovider --basetemp=.work_2022_unit
```

A suíte completa usa o procedimento de cache local documentado em [historico_v2.md](historico_v2.md), com diretórios descartáveis próprios de 2022 e `MPLBACKEND=Agg`. Os testes cobrem limites temporais inclusivos, divulgação e retificação posteriores, ausência versus zero e limite, separação de bases/perguntas, identidade compartilhada entre cortes, conflitos, hashes, reprodução offline, integridade referencial e invariância à ordem.

Verificação em 31/10/2026: **77 testes específicos passaram; suíte completa: 724 passaram**, com 14 avisos de dependências/deprecações e cobertura total de **90,81%**. O CLI retornou 1 pelas pendências documentais descritas acima. Os 281 hashes preexistentes foram conferidos sem ausências ou alterações. `git diff --check` e a checagem equivalente dos arquivos novos passaram. Após o ajuste de espaços finais e finais de linha dos artefatos derivados, os 23 testes da nova coleta foram repetidos.

## Pendências para a próxima revisão

Revisar territorialmente os registros restantes, ampliar a recuperação de resultados de outros executores, confrontar instrumentos com aplicação, obter listas integrais e suas categorias residuais, recuperar páginas indisponíveis e capturas históricas, resolver conflitos somente com prova, investigar dependência e realizar segunda conferência. A existência do inventário não prova exaustividade de pesquisas efetivamente publicadas. Não há recomendação de materializar snapshots antes desses gates.

O inventário de transcrições e todas as referências de fontes seguem abaixo. A matriz detalhada reproduzível está em `catalogo/matriz_documental.csv`.

## Inventário das transcrições

| Registro | Instituto | Campo realizado | Fonte principal |
|---|---|---|---|
| BR-09088/2022 | Datafolha | 2022-06-22 a 2022-06-23 | F22_DFPDF0623 |
| BR-01192/2022 | Datafolha | 2022-07-27 a 2022-07-28 | F22_DFPDF0728 |
| BR-09404/2022 | Datafolha | 2022-08-16 a 2022-08-18 | F22_DFPDF0818 |
| BR-00433/2022 | Datafolha | 2022-08-30 a 2022-09-01 | F22_DF0901 |
| BR-07422/2022 | Datafolha | 2022-09-08 a 2022-09-09 | F22_DFPDF0909 |
| BR-04099/2022 | Datafolha | pendente/conflitante | F22_DF0915 |
| BR-04180/2022 | Datafolha | 2022-09-20 a 2022-09-22 | F22_DFPDF0922 |
| BR-03980/2022 | Ipec | 2022-08-12 a 2022-08-14 | F22_IPEC0815 |
| BR-01979/2022 | Ipec | 2022-08-26 a 2022-08-28 | F22_IPEC0829 |
| BR-00922/2022 | Ipec | pendente/conflitante | F22_IPEC0905 |
| BR-01390/2022 | Ipec | 2022-09-09 a 2022-09-11 | F22_IPEC0912 |
| BR-00073/2022 | Ipec | 2022-09-17 a 2022-09-18 | F22_IPEC0919 |
| BR-05022/2022 | FSB | 2022-06-24 a 2022-06-26 | F22_FSB0627 |
| BR-05938/2022 | FSB | 2022-07-22 a 2022-07-24 | F22_FSB0725 |
| BR-07560/2022 | FSB | 2022-09-16 a 2022-09-18 | F22_FSB0919 |
| BR-02546/2022 | Quaest | 2022-07-28 a 2022-07-31 | F22_QUA0803 |
| BR-00585/2022 | Quaest | 2022-08-25 a 2022-08-28 | F22_QUA0831 |
| BR-04459/2022 | Quaest | 2022-09-17 a 2022-09-20 | F22_QUA0921 |
| BR-07003/2022 | PoderData | 2022-06-19 a 2022-06-21 | F22_PD0622 |
| BR-06550/2022 | PoderData | 2022-07-03 a 2022-07-05 | F22_PD0706 |
| BR-08398/2022 | PoderData | 2022-07-31 a 2022-08-02 | F22_PD0804 |
| BR-00407/2022 | PoderData | 2022-09-18 a 2022-09-20 | F22_PD0921 |
| BR-09408/2022 | Paraná Pesquisas | 2022-06-30 a 2022-07-05 | F22_PAR0706 |
| BR-09417/2022 | Paraná Pesquisas | 2022-09-15 a 2022-09-19 | F22_PAR0920 |

## Fontes e acesso

| ID | Tipo | Acesso | Referência |
|---|---|---|---|
| F22_TSE | registro_pesqele | lido_http_com_copia | [URL original](https://dadosabertos.tse.jus.br/dataset/pesquisas-eleitorais-2022) |
| F22_REG | registro_pesqele | lido_http_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/pesquisa_eleitoral_2022.zip) |
| F22_CONTR | registro_pesqele | lido_http_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/pesquisa_contratante_2022.zip) |
| F22_PESQELE | registro_pesqele | nao_recuperado | [URL original](https://pesqele-divulgacao.tse.jus.br/app/pesquisa/listar.xhtml) |
| F22_WIKI | arquivo_web | lido_web_sem_copia_http | [URL original](https://pt.wikipedia.org/wiki/Pesquisas_de_opini%C3%A3o_para_a_elei%C3%A7%C3%A3o_presidencial_no_Brasil_em_2022) |
| F22_DF0624 | relatorio | lido_http_com_copia | [URL original](https://datafolha.folha.uol.com.br/eleicoes/2022/06/estavel-disputa-presidencial-tem-lula-a-frente-e-bolsonaro-em-segundo.shtml) |
| F22_DF0728 | noticia | lido_http_com_copia | [URL original](https://tv.sbt.com.br/programas/jornalismo/portal-sbt-news/noticia/218202-datafolha-lula-lidera-com-47-e-bolsonaro-tem-29) |
| F22_DF0819 | relatorio | lido_http_com_copia | [URL original](https://datafolha.folha.uol.com.br/eleicoes/2022/08/lula-mantem-47-das-intencoes-de-voto-e-bolsonaro-vai-a-32.shtml) |
| F22_DF0901 | noticia | lido_http_com_copia | [URL original](https://www.cnnbrasil.com.br/politica/pesquisa-datafolha-para-presidente-lula-tem-45-bolsonaro-32/) |
| F22_DF0623 | noticia | lido_http_com_copia | [URL original](https://tv.sbt.com.br/programas/jornalismo/portal-sbt-news/noticia/214074-datafolha-lula-lidera-com-47-bolsonaro-tem-28) |
| F22_IPEC0829 | noticia | lido_http_com_copia | [URL original](https://www.infomoney.com.br/politica/ipec-lula-lidera-corrida-presidencial-com-44-bolsonaro-tem-32/) |
| F22_IPEC0919 | noticia | lido_http_com_copia | [URL original](https://www1.folha.uol.com.br/poder/2022/09/ipec-lula-vai-a-47-e-bolsonaro-segue-com-31-no-1o-turno.shtml) |
| F22_FSB0627 | relatorio | lido_http_com_copia | [URL original](https://www.esmaelmorais.com.br/wp-content/uploads/2022/06/Pesquisa-BTG-FSB-27Jun2022.pdf) |
| F22_FSB0627N | noticia | lido_http_com_copia | [URL original](https://www.bloomberglinea.com.br/2022/06/27/diferenca-entre-lula-e-bolsonaro-cai-de-12-para-10-pontos-em-pesquisa-btgfsb/) |
| F22_DFPDF0623 | relatorio | lido_http_com_copia | [URL original](https://media.folha.uol.com.br/datafolha/2022/06/24/intencaoxe390nf8enow85ndvoo-junsrwv222.pdf) |
| F22_DFPDF0818 | relatorio | lido_http_com_copia | [URL original](https://media.folha.uol.com.br/datafolha/2022/08/19/voto-br4802y234085290hvjsioh2ago1.pdf) |
| F22_DF0915 | noticia | lido_http_com_copia | [URL original](https://www.cnnbrasil.com.br/politica/pesquisa-datafolha-para-presidente-lula-tem-45-e-bolsonaro-33/) |
| F22_DF0922 | noticia | lido_http_com_copia | [URL original](https://www.cnnbrasil.com.br/politica/pesquisa-datafolha-para-presidente-lula-tem-47-e-bolsonaro-33/) |
| F22_DF0923 | relatorio | lido_http_com_copia | [URL original](https://datafolha.folha.uol.com.br/eleicoes/2022/09/lula-oscila-de-45-para-47-e-bolsonaro-mantem-33.shtml) |
| F22_DF0910 | relatorio | lido_http_com_copia | [URL original](https://datafolha.folha.uol.com.br/eleicoes/2022/09/bolsonaro-passa-de-32-para-34-e-lula-mantem-45.shtml) |
| F22_IPEC0912 | noticia | lido_http_com_copia | [URL original](https://www.cnnbrasil.com.br/politica/pesquisa-ipec-para-presidente-lula-tem-46-bolsonaro-31/) |
| F22_QUA0803 | noticia | lido_http_com_copia | [URL original](https://www1.folha.uol.com.br/poder/2022/08/quaest-lula-tem-44-contra-32-de-bolsonaro-no-primeiro-turno.shtml) |
| F22_QUA0803N | noticia | lido_http_com_copia | [URL original](https://www.infomoney.com.br/politica/lula-lidera-com-44-e-bolsonaro-soma-32-vantagem-do-petista-diminui-mostra-pesquisa-genial-quaest/) |
| F22_FSB0725 | noticia | lido_http_com_copia | [URL original](https://www.jornaldocomercio.com/politica/2022/07/amp/856707-lula-tem-44-bolsonaro-31-ciro-9-e-tebet-2-diz-pesquisa-fsb-btg.html) |
| F22_FSB0725N | noticia | lido_http_com_copia | [URL original](https://www.bloomberglinea.com.br/2022/07/25/lula-sobe-e-bolsonaro-oscila-na-margem-de-erro-em-pesquisa-btgfsb/) |
| F22_PD0622 | noticia | lido_http_com_copia | [URL original](https://tv.sbt.com.br/programas/jornalismo/portal-sbt-news/noticia/213795-lula-amplia-vantagem-sobre-bolsonaro-no-2-turno-das-eleicoes) |
| F22_PD0706 | noticia | lido_http_com_copia | [URL original](https://www.opovo.com.br/eleicoes-2022/2022/07/06/pesquisa-poder-data-lula-44-bolsonaro-36-ciro-gomes-5.html) |
| F22_PD0921 | noticia | lido_http_com_copia | [URL original](https://sbtnews.sbt.com.br/noticia/eleicoes/224205-pesquisa-poderdata-lula-tem-44-dos-votos-e-bolsonaro-37) |
| F22_REGIONAIS | arquivo_web | lido_http_com_copia | [URL original](https://www.infomoney.com.br/politica/eleicoes-2022-o-que-as-pesquisas-para-presidente-por-estado-revelam-sobre-a-corrida-eleitoral/) |
| F22_QUA0831 | noticia | lido_http_com_copia | [URL original](https://www1.folha.uol.com.br/poder/2022/08/quaest-lula-tem-44-contra-32-de-bolsonaro-no-1o-turno.shtml) |
| F22_QUA0831N | noticia | lido_web_sem_copia_http | [URL original](https://noticias.uol.com.br/eleicoes/2022/08/31/pesquisa-quaest-presidente-lula-bolsonaro-agosto.htm) |
| F22_PD0804 | noticia | lido_http_com_copia | [URL original](https://www.opovo.com.br/eleicoes-2022/2022/08/04/poderdata-bolsonaro-oscila-dois-pontos-para-baixo-e-tem-35-lula-segue-com-43.html) |
| F22_FSB0919 | noticia | lido_web_sem_copia_http | [URL original](https://noticias.uol.com.br/ultimas-noticias/agencia-estado/2022/09/19/pesquisa-btgfsb-mostra-alta-de-lula-para-44-bolsonaro-tem-35-e-ciro-7.amp.htm) |
| F22_QUA0921 | noticia | lido_http_com_copia | [URL original](https://www.opovo.com.br/eleicoes-2022/2022/09/21/pesquisa-quaest-lula-44-bolsonaro-34-ciro-6-tebet-5.html) |
| F22_PAR0920 | noticia | lido_http_com_copia | [URL original](https://sbtnews.sbt.com.br/noticia/eleicoes/224145-parana-pesquisas-lula-tem-401-contra-364-de-bolsonaro) |
| F22_IPEC0905 | noticia | lido_web_sem_copia_http | [URL original](https://noticias.uol.com.br/eleicoes/2022/09/05/pesquisa-ipec-presidente-lula-bolsonaro-setembro.amp.htm) |
| F22_IPEC0905N | noticia | lido_http_com_copia | [URL original](https://www1.folha.uol.com.br/poder/2022/09/ipec-lula-tem-44-contra-31-de-bolsonaro-no-1-turno.shtml) |
| F22_DFPDF0922 | relatorio | lido_http_com_copia | [URL original](https://media.folha.uol.com.br/datafolha/2022/09/23/472bvaj37yfsfsesvjvw282intencao-de-voto-presidente-22-09-22.pdf) |
| F22_DFPDF0909 | relatorio | lido_http_com_copia | [URL original](https://media.folha.uol.com.br/datafolha/2022/09/10/ivprsdnt-stbro.pdf) |
| F22_DF0729 | relatorio | lido_http_com_copia | [URL original](https://datafolha.folha.uol.com.br/eleicoes/2022/07/lula-tem-18-pontos-de-vantagem-sobre-bolsonaro-no-1o-turno.shtml) |
| F22_IPEC0815 | noticia | lido_http_com_copia | [URL original](https://jc.uol.com.br/politica/2022/08/15063378-ultima-pesquisa-para-presidente-2022-veja-os-numeros-da-pesquisa-ipec-globo.html) |
| F22_PAR0706 | noticia | lido_http_com_copia | [URL original](https://www.bahianoticias.com.br/noticia/270211-parana-pesquisas-lula-lidera-e-distancia-para-bolsonaro-se-mantem-estavel) |
| F22_FSB0919V | noticia | lido_http_com_copia | [URL original](https://jc.uol.com.br/dinheiro/2022/09/15082578-pesquisa-fsb-btg-para-presidente-2022-confira-a-intencao-de-votos-validos-para-lula-e-bolsonaro.html) |
| F22_DFPDF0728 | relatorio | lido_http_com_copia | [URL original](https://media.folha.uol.com.br/datafolha/2022/07/29/intencao-de-voto-presidente-jul-22.pdf) |
| F22_QT09088_1 | registro_pesqele | lido_http_range_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2022.zip) |
| F22_QT00433_1 | registro_pesqele | lido_http_range_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2022.zip) |
| F22_QT04180_1 | registro_pesqele | lido_http_range_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2022.zip) |
| F22_QT05022_1 | registro_pesqele | lido_http_range_com_copia | [URL original](https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2022.zip) |
