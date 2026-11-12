# Infraestrutura histórica v2 — protocolo 2.0.0

Esta entrega executa a etapa 1 da P0.2 e prepara armazenamento/validação. Não contém pesquisas históricas verificadas, snapshots reconstruídos, exportador ou métricas novas. O desenho é fixado pelo plano de reconstrução, sem consulta a resultados eleitorais ou otimização por backtesting.

## Artefatos e desenho congelado

`data/historico_v2/protocolo_v2.0.0.json` é o manifesto versionado: referências oficiais das eleições, oito cortes, hashes SHA-256 dos oito CSVs originais, regra principal, sensibilidades e tratamento da transição de 2018. Alterações metodológicas exigem novo arquivo de protocolo e revisão explícita; não editar silenciosamente uma versão congelada.

| Eleição | Horizontes | Cortes inclusivos em Brasília |
|---|---|---|
| 07/10/2018 | 30, 14, 7 | 07/09, 23/09, 30/09 |
| 02/10/2022 | 90, 60, 30, 14, 7 | 04/07, 03/08, 02/09, 18/09, 25/09 |

A janela principal aceita `0 <= (as_of - data_fim_campo).days <= 28`; sensibilidades usam 14 e 42. Não há expansão automática da janela. A seleção usa fim de campo e depois publicação comprovada, por instituto e cenário compatível; empates ficam em quarentena. Primeiro é selecionada a versão conhecida da coleta, depois a onda por instituto e por grupo de dependência. Grupos compartilhados entre institutos também não contam duas vezes. O catálogo deve documentar tracking, painel, sobreposição de respondentes e entidade executora. Um ID distinto de grupo não comprova independência: requer revisão documental.

2018 T−30 permanece não avaliável no estudo principal nesta versão. A coleta deve preservar cenários com Lula, sem Lula, com Haddad e associação a Lula. A liberação futura exige decisão de compatibilidade documentada e nova versão do protocolo; não basta preencher uma lista compatível. Um estudo condicionado ao par será outro experimento.

A sensibilidade com todas as ondas está registrada, mas sua execução depende de política de contribuição por grupo/onda ou correlação. Não há integração com o simulador.

## Contrato de armazenamento

Os sete CSVs começam somente com cabeçalho. `schema.json` define ordem das colunas e chaves; `src/historico_v2.py` define as restrições semânticas. UTF-8, datas ISO estritas, ponto decimal, IDs textuais e campos vazios para ausência. Booleanos usam `true`/`false`.

- `pesquisas`: uma versão de coleta, chave `(pesquisa_id, versao_id)`. Republicação vira fonte adicional; correção vira nova versão da mesma coleta. Registro TSE não é chave universal. IDs de instituto e eleição devem permanecer consistentes entre versões.
- `cenarios`: pergunta/lista/base específica, chave acrescida de `cenario_id`. `lista_candidatos_id` é uma lista versionada; `candidatos_ids` e `respostas_ids` são conjuntos explícitos separados por `|`, sem `|` nos IDs. A segunda lista inclui todas as respostas residuais. Esses campos permitem detectar tabela truncada sem inferir completude pela soma de percentuais. O dicionário histórico de aliases/listas será construído na coleta.
- `resultados`: chave acrescida de `resposta_id, metrica`. Métricas: `intencao_voto`, `rejeicao`. Tipos: `candidato`, `outros`, `branco`, `nulo`, `branco_nulo`, `nenhum`, `ns_nr`, `indeciso`. `candidato_id` só existe para tipo candidato. Não transportar rejeição de outra pergunta ou onda.
- `fontes`: versão de documento por `fonte_id`. Tipos: `registro_pesqele`, `relatorio`, `noticia`, `transmissao`, `arquivo_web`, `republicacao`. Preservar URL original, arquivo, página, datas, hash e acesso UTC quando disponíveis. Atualização não pode anteceder publicação. O validador verifica formato do hash, não autentica o documento nem baixa URLs.
- `evidencias`: um campo e um alvo por vínculo. Campos de pesquisa deixam cenário/resposta vazios; campos de cenário preenchem cenário; resultados preenchem cenário, resposta e métrica. `campo_comprovado` deve existir no alvo e `valor_original` deve reproduzir seu conteúdo textual. Para representar uma grafia/transcrição original diferente, conservar o trecho em `pagina_trecho` e documentar a normalização em `decisao`; não declarar equivalência sem revisão. Cada campo factual preenchido exige evidência `comprovado`, revisor, trecho e `conflito=false`. IDs técnicos e motivos de incompletude/ausência não exigem uma fonte própria.
- `snapshots`: futuras materializações do desenho, incluindo política, versão do dataset, cenário alvo `estimulada:totais` (ou combinação explícita suportada), lista e tratamento do candidato do PT. Nesta etapa as oito posições existem apenas no protocolo. Os CSVs não afirmam oito bases prontas.
- `snapshot_pesquisas`: vínculo muitos-para-muitos entre snapshot e coleta/versão/cenário. A mesma pesquisa pode reaparecer em vários cortes sem duplicar `pesquisas`. O gate confere a elegibilidade declarada, recência, grupo e existência da fonte temporal; não gera esses vínculos automaticamente.

Bases aceitas: `totais` e `validos`. Espontânea e estimulada são mantidas separadas. O coletor deve criar IDs diferentes para listas, perguntas e bases diferentes. O validador verifica consistência explícita, mas não pode deduzir a identidade real de duas entrevistas a partir do texto.

Qualificadores: `exato`, `zero_observado`, `zero_arredondado`, `nao_pontuou`, `menor_que`, `ausente`. Para `menor_que`, valor é o limite publicado; não uma estimativa pontual. `nao_pontuou` pode ter valor vazio, pois não deve ser convertido artificialmente em zero: conservar o qualificador e a expressão original na evidência; a tabela fica documentalmente incompleta para seleção. `ausente` exige valor vazio e `motivo_ausencia`; zero exige valor numérico zero. A distinção é preservada, sem imputação, normalização ou conversão em parâmetro de simulação. Não há teste rígido de soma 100, pois arredondamento e categorias agregadas requerem revisão; a declaração explícita de respostas é obrigatória.

## Execução e diagnósticos

Na raiz do projeto, em PowerShell:

```powershell
.\venv\Scripts\python.exe -m src.historico_v2
# Ou um catálogo separado com os mesmos sete cabeçalhos:
.\venv\Scripts\python.exe -m src.historico_v2 caminho/do/catalogo
```

A saída JSON contém `diagnosticos` (código, tabela, chave) e `decisoes` (por snapshot e cenário, elegibilidade e todos os motivos). Nada é escrito no catálogo. Código de saída 0 significa ausência de pendências; 1 indica pendências ou exclusões; 2 indica falha de leitura/cabeçalho. No catálogo entregue, o resultado esperado é `catalogo_vazio`, código 1: infraestrutura válida não significa base pronta para avaliação.

Principais famílias:

| Diagnóstico | Interpretação / ação |
|---|---|
| `chave_invalida_ou_duplicada`, `*_inexistente` | Corrigir identidade, chave ou referência; nunca deduplicar automaticamente por instituto/data |
| `data_invalida`, `campo_invertido`, `divulgacao_antes_campo` | Corrigir com fonte; datas não são inferidas |
| `campo_sem_evidencia`, `evidencia_*`, `fonte_em_quarentena` | Completar vínculo campo–documento e revisão; hipóteses não liberam dados |
| `cenario_incompleto`, `lista_candidatos_inconsistente` | Completar toda a pergunta, incluindo respostas residuais |
| `ausencia_qualificador_invalido`, `percentual_invalido` | Preservar ausência, zero, limite e arredondamento corretamente |
| `posterior_corte`, `sem_prova_divulgacao` | Excluir do corte; PesqEle e cronograma não provam divulgação |
| `cenario_incompativel`, `transicao_nao_avaliavel` | Preservar cenário original e documentar incompatibilidade |
| `onda_superada`, `empate_quarentena` | Resultado da regra pré-fixada; empate exige revisão de identidade |
| `base_vazia`, `baixa_diversidade` | Não executar estudo principal; uma coleta é apenas exploratória |
| `snapshot_fora_protocolo`, `vinculo_snapshot_inconsistente` | Corrigir materialização ou versionar formalmente a política |

Falhas documentais invalidam conservadoramente a versão inteira da pesquisa. Exclusões de janela/cenário/corte são atômicas por cenário: nunca há aproveitamento dos candidatos restantes. Datas de publicação e disponibilidade restringem cada evidência da versão; datas atuais de acesso não substituem prova histórica. Uma retificação tardia não apaga a versão anterior. Fonte PesqEle nunca libera um percentual como resultado divulgado.

O programa é determinístico por conteúdo: ordenar as linhas de qualquer tabela não altera a saída, inclusive diante de chaves duplicadas. A validação é independente do motor, usa apenas a biblioteca padrão e não roda backtesting.

## Testes e próximos gates

```powershell
$env:MPLBACKEND='Agg'
.\venv\Scripts\python.exe -m pytest tests/test_historico_v2.py --no-cov -q -p no:cacheprovider --basetemp=.work_historico_v2_unit
.\venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.work_historico_v2_full
```

`--basetemp` deve apontar para um diretório descartável novo: pytest gerencia seu conteúdo. A suíte completa mantém o gate de cobertura do projeto. Nesta execução, ArviZ tentou gravar cache fora da área permitida; alterar `LOCALAPPDATA` não bastou. A execução bem-sucedida redirecionou `platformdirs.user_cache_dir` somente no processo de testes, sem alterar dependências:

```powershell
$env:MPLBACKEND='Agg'
$env:COVERAGE_FILE='.work_historico_v2.coverage'
$env:PYTENSOR_FLAGS="base_compiledir=$PWD/.work_historico_v2_pytensor"
@'
from pathlib import Path
import platformdirs
import pytest
cache = Path('.work_historico_v2_cache').resolve()
cache.mkdir(exist_ok=True)
platformdirs.user_cache_dir = lambda *args, **kwargs: str(cache)
raise SystemExit(pytest.main(['-q', '-p', 'no:cacheprovider', '--basetemp=.work_historico_v2_full']))
'@ | .\venv\Scripts\python.exe -
```

Verificação em 30/10/2026: **36 testes específicos passaram; suíte completa: 683 passaram**, com 14 avisos de dependências/deprecações, cobertura total **90,38%** e cobertura do módulo novo **85%**. O CLI retornou `catalogo_vazio`, código 1, como esperado. Os testes conferem os oito hashes legados contra o manifesto.

Ficam para a coleta: censo de institutos/ondas (inclusive fontes inacessíveis), consulta individual ao PesqEle, documentos preservados e hashes, transcrição integral, dicionário de candidatos/aliases/listas, identificação de republicações e dependência, comprovação de disponibilidade por versão/campo e dupla conferência humana. O validador não verifica autenticidade de URLs, exatidão da transcrição, independência estatística ou completude da busca documental. O controle de conjuntos declarados impede omissão acidental, mas não prova que uma lista declarada corresponde ao questionário real.

Exportação, política de rejeição ausente/dispersão, adaptação da agregação de indecisos, reconstrução dos oito snapshots, simulação e reavaliação permanecem etapas posteriores. Os CSVs legados, dados eleitorais, relatórios e motor não são alterados por esta infraestrutura.
