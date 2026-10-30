# Qualidade das pesquisas: A03 e A04

Política do carregador modular e da retrospectiva. Não altera CSVs originais nem inventa valores. O carregamento próprio de `simulation_v2.py` não foi migrado nesta alteração.

## Validação

- Datas aceitas: `YYYY-MM-DD` e `DD/MM/YYYY`, com largura exata e validade no calendário. Não há reparo automático nem datas abreviadas.
- O carregador rejeita toda a entrada selecionada quando uma data é inválida, ausente ou posterior à referência, informando linhas e valores. `SimulationConfig.as_of` fixa explicitamente a referência para validação, ponderação e horizonte de incerteza da simulação. Sem `as_of`, a execução corrente usa `date.today()`. A função temporal compartilhada lança `ValueError`, inclusive para pesquisa única. Não existe peso máximo de fallback. Tau deve ser finito e positivo.
- Intenção deve ser finita entre 0 e 100; desvio finito e positivo. Rejeição e indecisos, quando presentes, devem ser finitos entre 0 e 100. Ausência da coluna conserva a convenção anterior de métrica não medida; células vazias em colunas presentes são rejeitadas.
- A retrospectiva exclui registros inválidos com diagnóstico por linha e todas as linhas da mesma identidade conhecida. Datas posteriores ao corte são ignoradas antes da ponderação. Falha se nenhuma linha sobrevive. O JSON registra linhas inválidas, linhas excluídas com seus grupos e pesquisas incompletas excluídas.

## Cenário e completude

Completude depende da métrica e do cenário declarado, não de todos os candidatos possíveis.

No carregador, a análise representa um cenário. `SimulationConfig.required_candidates=(...)` seleciona os candidatos e exige cada um em cada pesquisa antes da agregação. Outros candidatos são removidos somente após a validação. Sem seleção explícita, a união dos nomes do cenário selecionado declara o universo de candidatos: pesquisas com subconjuntos diferentes são rejeitadas. Ao analisar apenas o par, declare explicitamente seus dois nomes: uma pesquisa com terceiros e outra sem eles permanecem elegíveis para essa métrica.

Arquivos com mais de um `cenario` exigem `SimulationConfig.scenario` ou `--cenario`; não são agregados em conjunto. A seleção ocorre antes da validação e da definição do universo de candidatos, preservando os números originais das linhas. O identificador do cenário não pode estar vazio. Na retrospectiva, use `carregar_pesquisas_1t(..., cenario=...)` ou `--cenario`; sem seleção, múltiplos cenários também são rejeitados.

Exemplo de simulação histórica pela API: `SimulationConfig(csv_path=Path("pesquisas.csv"), as_of=date(2026, 10, 1), scenario="par", required_candidates=("Lula", "F. Bolsonaro"), seed=42)`. Pela CLI: `python -m src run --csv pesquisas.csv --as-of 2026-10-01 --cenario par --candidato-necessario Lula --candidato-necessario "F. Bolsonaro" --seed 42`. A data da eleição continua independente, em `election_date`; `as_of` controla a referência das estimativas, não os timestamps de geração dos artefatos. A retrospectiva usa o corte explícito `data_corte`/`--data-corte` como referência.

Na retrospectiva, `fatias_validas(df, candidatos_necessarios=...)` exige as chaves canônicas declaradas antes de normalizar. O padrão exige Flavio Bolsonaro e Lula, adequado à análise dos finalistas. Para cenários com outros candidatos obrigatórios, passe-os explicitamente ou repita `--candidato-necessario` na CLI. Não há exigência universal de todos os nomes de `RESULTADO_1T_TOTAL`.

As fatias de votos válidos são condicionadas à cobertura declarada: o programa não pode inferir candidatos ausentes da fonte. O denominador contém todos os votos observados, inclusive nomes desconhecidos, exceto brancos/nulos/indecisos. A fatia do par exige ambos e denominador positivo. Uma pesquisa só de Lula é excluída antes de produzir fatias; não vira 100%.

## Identidade

Prefira `pesquisa_id` estável. A identidade é `(pesquisa_id, cenario)` quando há cenário, ou apenas `pesquisa_id` quando não há. Assim, a mesma pesquisa pode medir cenários diferentes sem fundi-los. IDs distintos preservam observações com mesmo instituto e data; a leitura mantém IDs como texto, inclusive zeros à esquerda. Cada identidade exige instituto e data consistentes e uma observação por candidato. Metadados são verificados antes do corte retrospectivo, para não esconder inconsistências removendo somente parte de uma pesquisa. Aliases que colidem na mesma chave canônica dentro de uma pesquisa são erro; aliases usados em pesquisas diferentes são reunidos por candidato sem perder observações. O pivot não calcula médias de duplicatas.

Sem ID, a compatibilidade legada usa `(instituto, data, cenario quando presente)` com aviso explícito no log. Duplicatas de candidato nessa chave são rejeitadas e exigem IDs distintos. Duas observações com listas disjuntas de candidatos não podem ser distinguidas apenas por esses campos: essas fontes precisam fornecer IDs. A inferência legada não confirma a identidade na fonte.

Incompatibilidades: entradas sem data, percentuais vazios/não finitos, datas futuras, duplicatas e pesquisas parciais antes aceitas passam a falhar ou ser excluídas com diagnóstico. Fixtures com coberturas diferentes agora declaram explicitamente o cenário do par. O novo campo opcional do contrato foi acrescentado ao final para preservar argumentos posicionais.

## Diagnóstico

A versão registrada no Git contém `2026-10-0` nas linhas **325–330**, todas Real Time (cabeçalho na linha 1):

| Linha | Candidato |
|---|---|
| 325 | F. Bolsonaro |
| 326 | Caiado |
| 327 | Zema |
| 328 | Santos |
| 329 | Cury |
| 330 | Outros |

O dia é incompleto/zero, inválido no calendário. A linha 324 (Lula, 43%) tem `2026-10-01` e fica isolada quando se removem apenas as seis linhas.

A cópia de trabalho já estava modificada ao iniciar: essas seis células contêm `2026-10-01`. Essa alteração preexistente foi preservada. O fixture `tests/fixtures/pesquisas_auditoria_a03.csv` conserva a entrada auditada sem depender de futuras versões de HEAD.

## Comparação controlada

Entrada auditada copiada para diretório temporário; código anterior preservado antes da edição. Referência da agregação anterior fixada em **29/10/2026**; corte retrospectivo **03/10/2026**, tau **7**. Somente as alterações indicadas variam entre experimentos. Em datas válidas passadas, a mudança da referência tem fator comum que cancela na normalização. Evidência detalhada em [comparacao_a03_a04.json](comparacao_a03_a04.json).

| Experimento | Lula (%) | F. Bolsonaro (%) | Santos (%) | Desvio global |
|---|---:|---:|---:|---:|
| Anterior, entrada auditada | 41,60283 | 39,23425 | 3,76487 | 2,31013 |
| Anterior, apenas seis linhas excluídas | 41,60283 | 39,82172 | 2,93238 | 2,60111 |
| Validado, seis linhas e grupo parcial excluídos | 41,20262 | 39,82172 | 2,93238 | 2,57351 |
| Hipótese: seis datas alteradas para 01/10 | 41,60283 | 39,78563 | 3,09496 | 2,58259 |

A entrada auditada inteira é rejeitada pelo novo carregador, sem estimativas. Remover somente seis linhas também é rejeitado por incompletude. A terceira linha só é produzida sobre cópia temporária explicitamente preparada.

A hipótese de 01/10 é um experimento, não uma correção confirmada da fonte. A cópia local preexistente possui essas datas e suas estimativas antes/depois são idênticas. Não há efeito comprovado da validação sobre essa entrada já válida.

Na retrospectiva auditada, o grupo isolado deixa de ser 100% Lula. A estimativa ponderada de Lula passa de **47,01% para 44,58%**; a de Flavio permanece em **42,66%**. O viés do par permanece **+2,13 pp**, pois a métrica anterior já exigia ambos. Não atribuir a mudança da comparação de Lula ao viés do par.

## Verificação

Python do `venv`, `MPLBACKEND=Agg`. Temporários do pytest dentro de `.work_a03` e cacheprovider desativado devido às restrições de escrita. O lançador redireciona somente o diretório de cache do ArviZ via `platformdirs.user_cache_dir`; não altera funções do projeto nem simula resultados. O Python global não possui pytest.

Validação inicial: 86 testes relevantes e 606 testes na suíte completa aprovados, com cobertura de 90,99%. A revisão final acrescenta regressões de `as_of`, seleção de cenários, IDs textuais, compatibilidade legada, cobertura do par e aliases entre pesquisas.

Revisão final: **130 testes relevantes aprovados** (incluindo `tests/test_simulation.py`); **623 testes aprovados na suíte completa**, 13 avisos e cobertura **90,86%**, acima do mínimo de 80%. Ambos executados com `MPLBACKEND=Agg`. Logs locais: `.work_a03/compat_relevant_final.txt` e `.work_a03/compat_full.txt`. A alteração preexistente em `data/pesquisas.csv` foi conferida por SHA-256 e preservada fora do staging.
