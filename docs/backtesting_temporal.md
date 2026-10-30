# Corte temporal do backtesting — A01 / P0.1

Implementado em 29/10/2026. `data_referencia` é o `as_of`, inclusivo,
na granularidade de dia civil. Uma pesquisa publicada no próprio dia é elegível;
a interface não representa previsões intradiárias. Datas devem ser ISO
`YYYY-MM-DD`; timestamps e formatos ambíguos são rejeitados, sem truncamento.

## Contrato e política conservadora

- `data_inicio_campo` e `data_fim_campo`: realização da pesquisa.
- `data_publicacao`: dia de publicação, quando comprovado pela fonte.
- `data_disponibilidade`: dia de disponibilidade para o processo retrospectivo,
  quando comprovado pela fonte. Uma coleta tardia pode tornar este dia posterior
  à publicação; o corte verifica ambos quando presentes.
- `data`: coluna legada de significado não comprovado. Serve somente como
  referência de recência e restrição adicional; nunca comprova disponibilidade.

Exige-se pelo menos publicação ou disponibilidade explícita. Não se infere
publicação pelo fim do campo, pelo nome do arquivo ou pelo rótulo T-N. Toda data
informada deve ser válida e menor ou igual ao corte. Campos opcionais vazios não
fornecem evidência. Um valor inválido informado causa rejeição mesmo que exista
outra data válida. Início posterior ao fim e publicação/disponibilidade anterior
ao fim do campo também causam rejeição. A coluna legada, se presente sem fim
explícito, restringe igualmente a cronologia.

Para o peso temporal usa-se fim de campo, depois `data` legada, depois a mais
recente das datas comprovadas de publicação/disponibilidade. Esta última é uma
aproximação de recência quando não há data de campo; não cria uma data histórica.
Pesos rejeitam datas inválidas e futuras em vez de atribuir peso máximo.

O filtro precede seleção de candidatos, intenção, rejeição, dispersão, indecisos
e simulação. Exclusões parciais emitem aviso com motivos e contagens. Base vazia
lança `ValueError` com arquivo, corte e motivos, antes de chamar a simulação.
O lote exibe o erro de cada snapshot e segue o comportamento existente de
continuar os demais. Nenhuma métrica nova pode ser calculada com os CSVs atuais.

## Diagnóstico dos oito arquivos originais

Reproduzir sem simular nem escrever relatórios:

```powershell
venv/Scripts/python.exe src/backtesting.py --diagnostico-temporal
```

Contagens são de linhas (candidato/pesquisa), não de pesquisas distintas.
Motivos exclusivos: data inválida, data posterior, disponibilidade não comprovada,
cronologia inconsistente, nesta ordem. Uma linha futura sem metadados é contada
apenas em “posterior”; isso não significa que sua disponibilidade foi comprovada.

| Ano | Snapshot | as_of | Total | Aceitas | Rejeitadas | Posterior | Sem comprovação |
|---|---|---|---:|---:|---:|---:|---:|
| 2022 | T-90 | 2022-07-06 | 12 | 0 | 12 | 4 | 8 |
| 2022 | T-60 | 2022-08-05 | 12 | 0 | 12 | 8 | 4 |
| 2022 | T-30 | 2022-09-04 | 16 | 0 | 16 | 16 | 0 |
| 2022 | T-14 | 2022-09-20 | 16 | 0 | 16 | 8 | 8 |
| 2022 | T-7 | 2022-09-27 | 12 | 0 | 12 | 12 | 0 |
| 2018 | T-30 | 2018-09-07 | 16 | 0 | 16 | 16 | 0 |
| 2018 | T-14 | 2018-09-23 | 16 | 0 | 16 | 16 | 0 |
| 2018 | T-7 | 2018-09-30 | 12 | 0 | 12 | 12 | 0 |
| Total | | | 112 | 0 | 112 | 92 | 20 |

Todos carecem de publicação/disponibilidade. Um filtro apenas na coluna legada
aceitaria 20 linhas, mas não comprovaria que eram conhecidas naquele horizonte.
Reconstruir as fontes e seus metadados pertence a P0.2. CSVs e artefatos existentes
foram preservados; métricas antigas não constituem validação deste corte.

## Validação da entrega

Com `MPLBACKEND=Agg`:

- Novos testes: `python -m pytest tests/test_backtesting.py --no-cov -p no:cacheprovider --basetemp=<temporario-local>`: **39 passed**.
- Suíte completa: `python -m pytest -p no:cacheprovider --basetemp=<temporario-local>`: **307 passed, 3 warnings**, 38,27 s; cobertura configurada **89,75%**, gate de 80% aprovado. A configuração existente exclui backtesting da cobertura; o percentual não representa a cobertura deste módulo.
- `git diff --check`: aprovado.

O temporário local e a desativação do cache contornam permissões preexistentes
no temporário padrão e em `.pytest_cache`, sem alterar a configuração do projeto.
