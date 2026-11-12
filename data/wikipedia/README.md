# Pesquisas presidenciais 2010–2022 (transcrição da Wikipédia)

`pesquisas_wikipedia_2010_2022.csv` reúne as pesquisas nacionais de intenção de voto para presidente das eleições de 2010, 2014, 2018 e 2022, nos dois turnos, transcritas das tabelas da Wikipédia. Ele é usado só para calibrar o erro comum das pesquisas (`python -m src.calibracao`).

É uma **fonte secundária**. Não substitui o catálogo auditado de `data/historico_v2`, que parte dos registros do TSE, e não deve alimentar previsões publicadas.

## Fontes

Acesso em 2026-11-11. As revisões abaixo eram as mais recentes nessa data.

| Eleição | Página | Revisão |
|---|---|---|
| 2010, 1º turno | [pt: Pesquisas de opinião … 2010](https://pt.wikipedia.org/wiki/Pesquisas_de_opini%C3%A3o_para_a_elei%C3%A7%C3%A3o_presidencial_no_Brasil_em_2010) | 73055941 |
| 2010, 2º turno | [en: Opinion polling for the 2010 Brazilian presidential election](https://en.wikipedia.org/wiki/Opinion_polling_for_the_2010_Brazilian_presidential_election) (a página em português não tem tabela de 2º turno) | 1373536970 |
| 2014 | [pt: … 2014](https://pt.wikipedia.org/wiki/Pesquisas_de_opini%C3%A3o_para_a_elei%C3%A7%C3%A3o_presidencial_no_Brasil_em_2014); as tabelas vêm das predefinições transcluídas do 1º e do 2º turno | 73055945 (página) |
| 2018 | [pt: … 2018](https://pt.wikipedia.org/wiki/Pesquisas_de_opini%C3%A3o_para_a_elei%C3%A7%C3%A3o_presidencial_no_Brasil_em_2018) | 73055947 |
| 2022 | [pt: … 2022](https://pt.wikipedia.org/wiki/Pesquisas_de_opini%C3%A3o_para_a_elei%C3%A7%C3%A3o_presidencial_no_Brasil_em_2022) | 73271090 |

O conteúdo da Wikipédia é licenciado sob CC BY-SA 4.0.

## Como foi extraído

Cada página foi baixada em wikitext bruto (`action=raw`) e lida por um parser determinístico de tabelas wiki, com `rowspan` e `colspan` tratados. Nenhum valor foi digitado à mão. A coluna `linha_wiki` aponta a linha da pesquisa no wikitext da revisão acima. Em 2014, ela usa o formato `t1.wikitext:N` ou `t2.wikitext:N`, que remete às predefinições do 1º e do 2º turno.

As notas de cada extração (tabelas lidas, linhas descartadas e ambiguidades) estão em `notas_<ano>.md`.

## Formato

Há uma linha por pesquisa, cenário e candidato:

`ano, turno, secao, cenario, tipo, instituto, contratante, data_inicio, data_fim, amostra, margem_erro_pp, registro_tse, candidato, pct, linha_wiki, soma_pct, alertas, fonte, acesso`

- `pct` é o percentual sobre o total de entrevistados, como aparece na tabela. Colunas que não são candidatos (brancos e nulos, indecisos, outros) aparecem como linhas próprias.
- `soma_pct` é a soma da pesquisa naquele cenário.
- `alertas` é preenchido por pesquisa. Qualquer alerta tira a pesquisa da calibração.

| Alerta | Grupos | Significado |
|---|---|---|
| `boca_de_urna` | 3 | Pesquisa no dia da eleição ou boca de urna, como as do IBOPE em 2018 com 30 mil entrevistas. Revela o resultado. |
| `resultado` | 3 | Linha do resultado oficial copiada da tabela. |
| `sem_data` | 20 | Data de campo ilegível (só o mês, intervalos partidos ou erro de digitação). |
| `soma_fora` | 87 | Soma fora de 90–110%. Quase todas são cenários antigos ou parciais. |
| `cenario_psb_ambiguo` | 16 | Pesquisas de 2014 antes de 13/08. A coluna do PSB mistura Eduardo Campos e Marina Silva. |

## Limitações conhecidas

- 2010 não tem amostra nem margem de erro. Quando a margem falta, a calibração usa `1,96 × 50 / √n` se houver amostra e ±2 pp se não houver.
- Em 2010 e 2014, `tipo` e `contratante` estão vazios ou foram inferidos do texto da página.
- Em 2018 e 2022, os cenários "Cenário k" são numerados pela posição na tabela. A Wikipédia não dá nome a eles.
- Os percentuais são os da tabela. Algumas referências citam votos válidos, mas as tabelas trazem votos totais.
- A pesquisa Modalmais/Futura da linha 3252 de 2022 tem um layout que o parser não reconstrói por inteiro. Ela fica fora da janela de calibração.
