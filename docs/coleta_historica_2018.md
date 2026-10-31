# Coleta documental de pesquisas presidenciais de 2018

Primeira entrega, coletada em 30/10/2026. Referências: [plano](plano_reconstrucao_historica.md), [infraestrutura v2](historico_v2.md) e [protocolo congelado](../data/historico_v2/protocolo_v2.0.0.json). Não houve simulação, backtesting, alteração do protocolo ou seleção orientada por resultados eleitorais.

## Estado da entrega

Foram transcritos 27 levantamentos, 38 cenários e 382 respostas, com 67 fontes catalogadas e 2.960 vínculos de evidência. O catálogo inclui transcrições parciais: quantidade não significa elegibilidade. Todos os levantamentos permanecem em quarentena: grupos de dependência não foram arbitrados e a segunda revisão está pendente. Os dois CSVs de snapshots continuam somente com cabeçalhos. T−30 permanece não avaliável no protocolo principal.

## Levantamento sistemático e limites

Consultou-se o acervo aberto oficial do TSE, incluindo ZIPs de pesquisas e contratantes e o índice do ZIP de questionários. O membro BR contém 714 linhas e 657 códigos distintos. O inventário de triagem inclui 277 variantes de 274 códigos com cargo Presidente e fim declarado entre 27/07 e 30/09/2018. Inclui pesquisas locais que perguntaram sobre presidente: não é um censo de pesquisas nacionais publicadas. A classificação territorial das entradas restantes ainda exige leitura documental. Datas declaradas no registro não substituem campo efetivamente realizado.

O acesso direto ao PesqEle retornou 403. Os ZIPs oficiais permitiram recuperar os cadastros e os três questionários de F01–F03. O ZIP completo de questionários não foi baixado: índice e membros foram recuperados por HTTP Range. Há colisões de códigos entre CNPJs no próprio arquivo do TSE; a identificação usa também CNPJ, período e amostra. BR-02039/2018 foi vinculado ao CNPJ 29550908000150, DataPoder360, e não à entrada de abril de outra empresa.

A Wikipédia de 2018 e a lista da Gazeta foram usadas como índices para descobrir referências; não comprovam os percentuais transcritos. A Wikipédia de 2022 foi catalogada apenas como referência futura indicada pelo usuário. O arquivo CESOP 4405 refere-se a São Paulo e foi descartado como evidência de pesquisa nacional. BR-02553/2018 teve cancelamento documentado em S043: registro sem aplicação não gera resultado.

Há tentativas sem recuperação integral: relatórios CNT/MDA (falha TLS), Lupa/Datafolha F03 (403/limite de tamanho), relatório XP (falha TLS), páginas R7 e Istoé (404), imagens/gráficos XP não transcritos. Esses casos permanecem no inventário de fontes; nada foi completado a partir de lembrança ou inferência. A coleta ainda não é exaustiva: o cadastro bruto reduz a invisibilidade das lacunas, mas não resolve cobertura nacional, execução ou publicação.

## Cobertura por corte

Contagens abaixo exigem fim de campo realizado conhecido e publicação documentada até o corte, com idade inclusiva de 0 a N dias. Não aplicam compatibilidade, completude, instituto ou dependência e **não são contagens de pesquisas elegíveis**. Um levantamento pode aparecer em vários cortes sem ser duplicado no catálogo.

| Corte | Janela | Levantamentos com cobertura temporal | Cenários |
|---|---:|---:|---:|
| 2018-09-07 | 14 | 4 | 9 |
| 2018-09-07 | 28 | 6 | 13 |
| 2018-09-07 | 42 | 6 | 13 |
| 2018-09-23 | 14 | 11 | 14 |
| 2018-09-23 | 28 | 15 | 23 |
| 2018-09-23 | 42 | 17 | 27 |
| 2018-09-30 | 14 | 12 | 13 |
| 2018-09-30 | 28 | 21 | 27 |
| 2018-09-30 | 42 | 23 | 32 |

A janela principal é de 28 dias; 14 e 42 são sensibilidades congeladas. Publicação posterior, campo desconhecido e fora da janela constam individualmente em `cobertura_documental.csv`. Não se inferiu divulgação a partir de cadastro ou data prevista.

## Inventário de transcrições

| Registro | Instituto na fonte | Campo realizado | Publicação dos cenários | Fontes de resultados | Cenários |
|---|---|---|---|---|---:|
| BR-05003/2018 | Ibope | 2018-09-01 a 2018-09-03 | 2018-09-05 | S001 | 1 |
| BR-06919/2018 | Datafolha | 2018-09-18 a 2018-09-19 | 2018-09-20 | S055 | 1 |
| BR-08687/2018 | Datafolha | 2018-09-26 a 2018-09-28 | 2018-09-28 | S005 | 1 |
| BR-05596/2018 | Datafolha | 2018-09-13 a 2018-09-14 | 2018-09-17 | S035 | 1 |
| BR-02410/2018 | Paraná Pesquisas | 2018-09-07 a 2018-09-11 | 2018-09-12 | S056 | 1 |
| BR-03512/2018 | Paraná Pesquisas | 2018-09-23 a 2018-09-25 | 2018-09-26 | S036 | 1 |
| BR-02891/2018 | Paraná Pesquisas | 2018-08-09 a 2018-08-13 | ausente | S037 | 2 |
| BR-01057/2018 | Instituto FSB Pesquisa | 2018-09-01 a 2018-09-02 | 2018-09-03 | S031 | 2 |
| BR-06478/2018 | Instituto FSB Pesquisa | 2018-09-15 a 2018-09-16 | 2018-09-17 | S032 | 1 |
| BR-03861/2018 | Instituto FSB Pesquisa | 2018-09-22 a 2018-09-23 | 2018-09-24 | S033 | 1 |
| BR-01669/2018 | Vox Populi | 2018-09-07 a 2018-09-11 | 2018-09-13 | S024 | 2 |
| BR-03303/2018 | MDA | 2018-09-27 a 2018-09-28 | 2018-09-30 | S011 | 1 |
| BR-04362/2018 | MDA | 2018-09-12 a 2018-09-15 | 2018-09-17 | S012 | 1 |
| BR-07252/2018 | Ipespe | 2018-08-27 a 2018-08-29 | 2018-08-31 | S015 | 3 |
| BR-00339/2018 | Ipespe | 2018-09-03 a 2018-09-05 | 2018-09-07 | S040 | 3 |
| BR-07277/2018 | Ipespe | 2018-09-10 a 2018-09-12 | 2018-09-14 | S041 | 2 |
| BR-02995/2018 | Ipespe | 2018-09-17 a 2018-09-19 | 2018-09-21 | S039 | 2 |
| BR-00526/2018 | Ipespe | 2018-09-24 a 2018-09-26 | 2018-09-28 | S016 | 1 |
| BR-01665/2018 | Ibope | 2018-08-17 a 2018-08-19 | 2018-08-20 | S021 | 2 |
| BR-09086/2018 | MDA | 2018-08-15 a 2018-08-18 | 2018-08-20 | S022 | 2 |
| BR-05221/2018 | Ibope | 2018-09-08 a 2018-09-10 | 2018-09-11 | S045 | 1 |
| BR-09678/2018 | Ibope | 2018-09-16 a 2018-09-18 | 2018-09-18 | S044 | 1 |
| BR-06630/2018 | Ibope | não comprovado a não comprovado | 2018-09-25 | S046 | 1 |
| BR-04669/2018 | Ibope | 2018-09-22 a 2018-09-24 | 2018-09-26 | S027 | 1 |
| BR-00592/2018 | Brasilis | 2018-09-25 a 2018-09-26 | 2018-09-27 | S038 | 1 |
| BR-01687/2018 | Brasilis | não comprovado a não comprovado | 2018-09-21 | S017 | 1 |
| BR-02039/2018 | DataPoder360 | 2018-09-19 a 2018-09-20 | 2018-09-21 | S042 | 1 |

## F01–F03, conflitos e decisões de transcrição

- **F01, BR-05003/2018:** campo realizado de 01–03/09, notícia publicada em 05/09. O registro previa período mais amplo e divulgação em 04/09. O questionário contém alternativas com Lula e Haddad; somente o cenário aplicado com Haddad tem resultados transcritos. Não foram inventados resultados do formulário com Lula. Falta conferir relatório original e categorias residuais.
- **F02, BR-06919/2018:** campo de 18–19/09, divulgação em 20/09, 8.601 entrevistas realizadas versus 8.596 planejadas no cadastro. Relatório p. 8 apresenta 12% para branco/nulo/nenhum; texto do instituto informa 11%. Foi transcrito 12 com conflito explícito, mantendo 11 no inventário de conflitos. Não há resolução automática.
- **F03, BR-08687/2018:** campo de 26–28/09, divulgação em 28/09. Registro planejava 9.072 entrevistas; notícia contemporânea informa 9.000 realizadas em 343 municípios. Outra notícia usa 9.072. A distinção planejado/realizado não elimina a divergência jornalística: falta o relatório original. Não se declarou a amostra definitivamente resolvida.
- **FSB BR-03861/2018:** Amoêdo 3% no relatório original, p. 13, versus 4% em notícia. Valor 3 mantido com conflito; alternativa preservada.
- **CNT/MDA BR-09086/2018:** os 17,3% de Haddad na pergunta de transferência referem-se aos eleitores de Lula, não à amostra nacional. Cenário separado, base amostral explicitada e base percentual vazia: o esquema atual não representa essa base condicional. Diagnóstico esperado; não houve conversão para percentual nacional.
- **Vox Populi:** cenário com Lula separado do cenário com Haddad explicitamente apoiado por Lula. Sem misturar perguntas ou completar nomes ausentes com zero.

Ausência de valor é ausência; zero impresso é `zero_arredondado`, não zero exato observado; “menos de 1%” é valor-limite 1 com `menor_que`. `exato` nos números não nulos identifica a transcrição literal do valor publicado, sem desfazer arredondamento. A troca de vírgula decimal por ponto é apenas representação. Categorias agregadas de brancos/nulos/indecisos permanecem agregadas. Nome original e identificador normalizado são campos distintos.

## Fontes e rastreabilidade

O catálogo completo está em `fontes.csv`: URL, tipo, status de acesso, caminho preservado e SHA-256 quando há cópia. `evidencias.csv` vincula fonte e localização aos campos; `transcricoes.json` preserva decisões e motivos de incompletude. Há notícias acessadas apenas pela ferramenta web, sem cópia HTTP: o status explicita essa limitação. Conteúdo recuperado em 2026 pode ter sido alterado desde 2018; datas históricas não equivalem à verificação de uma captura arquivada contemporânea. Cadastros e questionários não comprovam publicação de resultados.

Relatórios recuperados incluem Datafolha de 13–14 e 18–19/09; Paraná de agosto e duas rodadas de setembro; FSB de 03, 17 e 24/09; Vox Populi; CNI/Ibope. O relatório FSB de 01/10 está preservado como tentativa de pesquisa, mas excluído das transcrições dos cortes por publicação posterior. Questionários oficiais de F01–F03 foram extraídos, com leitura das páginas relevantes. Logs HTTP, índice de questionários e consultas web ficam nos diretórios auxiliares.

O inventário TSE preserva nome jurídico presente na exportação atual; o catálogo usa a marca contemporânea indicada na fonte. Não se assumiu que alterações cadastrais posteriores descrevem a marca histórica. Contratantes e metodologia declarada provêm do cadastro, sem afirmar execução integral do plano.

## Validação e reprodução

A partir da raiz, usando o Python do ambiente do projeto:

```powershell
.\venv\Scripts\python.exe -m src.historico_v2
.\venv\Scripts\python.exe data/historico_v2/coleta_2018/auditar_entrega.py
$env:MPLBACKEND="Agg"
.\venv\Scripts\python.exe -m pytest tests/test_historico_v2.py tests/test_coleta_historica_2018.py --no-cov -q
```

O validador retorna **1**, por pendências documentais esperadas; isso não significa catálogo aprovado. O relatório integral está em `diagnostico_validacao.json`. Não há decisões de snapshots, pois não foram materializados. Diagnósticos atuais:

| Código | Quantidade |
|---|---:|
| base_pergunta_invalida | 1 |
| campo_sem_evidencia | 2 |
| cenario_incompleto | 3 |
| cenario_sem_identidade | 34 |
| identidade_incompleta | 27 |

`identidade_incompleta` inclui grupos de dependência ainda vazios; `cenario_sem_identidade` e `cenario_incompleto` sinalizam instrumento/lista/categorias não integralmente comprovados; `campo_sem_evidencia` inclui os dois percentuais em conflito; `base_pergunta_invalida` conserva a pergunta condicional sem forçar base incorreta. Os testes distinguem essas pendências de erros de chave, referência e tipos. O validador continua independente do motor.

Para reproduzir os cinco CSVs documentais em **outro diretório**, executar `gerar_catalogo.py --destino CAMINHO`. O gerador usa apenas cópias locais e transcrições; não busca rede, não escreve snapshots e não importa o simulador. `auditar_entrega.py` verifica os hashes protegidos, gera cobertura, conflitos, diagnóstico e este relatório. A versão de coleta é documental_01; segunda revisão humana não foi simulada.

## Trabalho pendente para a coleta histórica

Conferir abrangência de todas as entradas candidatas do TSE; recuperar fontes originais e capturas contemporâneas ausentes; transcrever gráficos ainda não lidos; conferir pergunta literal, listas completas e respostas residuais; resolver conflitos com evidência adicional; estudar dependência, republicações e amostras sobrepostas; registrar segunda revisão. Só então propor elegibilidade e materialização de snapshots conforme protocolo. T−30 exige decisão metodológica explícita posterior. A coleta de 2022 permanece fora desta entrega.

Preservação conferida por SHA-256 para 41 arquivos previamente existentes registrados em `preservacao.json`, incluindo protocolo, oito legados, validador e arquivos locais ali inventariados. Arquivos locais ausentes em uma cópia limpa não são exigidos; arquivos protegidos sob data/ e src/ continuam obrigatórios. O motor não integra o diff. Esta entrega é documental preliminar, sem aprovação para simulação.
