# Fase 3 — Avaliação das previsões de 2026 e calibração do erro comum

Gerado com `python -m src.calibracao` (sementes fixas; JSON completo em `outputs/calibracao/calibracao_fase3.json`).

Resultados oficiais em % dos votos válidos, do TSE:
- 2026: [1º turno](https://www.cartacapital.com.br/politica/tse-encerra-apuracao-do-1o-turno/) e [2º turno](https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/presidente-do-tse-anuncia-reeleicao-de-lula-e-faz-balanco-do-2o-turno-das-eleicoes-2026);
- 2018 e 2022: os mesmos de `src/backtesting.py`;
- 2010 e 2014: totais oficiais do TSE.

## 1. Previsão do 1º turno (pesquisas até 03/10/2026)

Resultado: F. Bolsonaro 47,03%, Lula 45,16%. Flávio liderou.

| Parâmetro | P(Flávio lidera) | Brier liderança | Log score | PIT Flávio | IC90 Flávio | CRPS total (pp) |
|---|---:|---:|---:|---:|---|---:|
| Erro comum 3,0 (padrão) | 33,6% | 0,883 | 1,09 | 0,94 | [37,9; 47,3] | 6,69 |
| Erro comum 3,5 (estimativa) | 35,6% | 0,829 | 1,03 | 0,92 | [37,1; 48,1] | 6,50 |

O resultado de Flávio ficou dentro do IC90, mas fora do IC80 (PIT 0,94). O de Lula ficou perto do centro (PIT 0,58). O Brier de 0,88 é pior que o de uma moeda entre os dois (0,50): o modelo apostou no líder errado porque as pesquisas erraram na mesma direção.

## 2. Previsão do 2º turno (pesquisas pós-1º turno até 24/10/2026)

Resultado: Lula 51,79%, Flávio 48,21%. A média das pesquisas dava a Flávio 50,94% da fatia de dois partidos.

| Modelo | P(Flávio vence) | Brier | Log score | PIT | IC90 da fatia de Flávio | CRPS |
|---|---:|---:|---:|---:|---|---:|
| v2.10, `sd_fatia` 2,5 (publicado) | 64,4% | 0,414 | 1,03 | 0,14 | [46,7; 55,1] | 1,66 |
| v2.10, `sd_fatia` 3,0 | 61,8% | 0,382 | 0,96 | 0,18 | [45,9; 55,9] | 1,61 |
| v2.10, `sd_fatia` 3,5 (estimativa) | 60,1% | 0,361 | 0,92 | 0,22 | [45,1; 56,7] | 1,61 |
| Núcleo v3 (`python -m src runoff`) | 64,4% | 0,415 | 1,03 | 0,15 | [46,2; 55,6] | 1,66 |

O resultado ficou dentro do IC90 em todos os casos. Um DP maior pontua melhor aqui porque o favorito perdeu.

## 3. Calibração do erro comum

Cada caso compara o agregado das pesquisas dos **últimos 14 dias** antes da eleição com o resultado. O agregado usa o agregador v3 do motor, com efeitos de instituto e peso por recência. A comparação é feita na fatia de dois partidos do principal candidato não petista, `A/(A+B)`. Erro = resultado − pesquisas; positivo quer dizer que A foi subestimado.

Os casos de 2010 a 2022 vêm da transcrição da Wikipédia em [`data/wikipedia/`](../data/wikipedia/README.md), uma fonte secundária. Bocas de urna, datas ilegíveis e somas fora de 90–110% ficam de fora.

| Caso | Pesquisas | Resultado | Erro (pp) | Pesquisas usadas |
|---|---:|---:|---:|---:|
| 2010 1T (Serra × Dilma) | 34,46 | 41,01 | +6,55 | 19 |
| 2010 2T (Serra × Dilma) | 43,62 | 43,95 | +0,33 | 13 |
| 2014 1T (Aécio × Dilma) | 34,74 | 44,65 | +9,91 | 15 |
| 2014 2T (Aécio × Dilma) | 47,78 | 48,36 | +0,58 | 13 |
| 2018 1T (Bolsonaro × Haddad) | 59,85 | 61,12 | +1,27 | 24 |
| 2018 2T (Bolsonaro × Haddad) | 56,85 | 55,13 | −1,72 | 21 |
| 2022 1T (Bolsonaro × Lula) | 45,19 | 47,15 | +1,96 | 30 |
| 2022 2T (Bolsonaro × Lula) | 49,06 | 49,10 | +0,04 | 34 |
| 2026 1T (Flávio × Lula) | 48,85 | 51,01 | +2,17 | 56 |
| 2026 2T (Flávio × Lula) | 50,94 | 48,21 | −2,73 | 52 |

As transcrições legadas de `data/historico/` davam erro de +1,95 pp em 2018 1T e +4,43 pp em 2022 1T, com só três pesquisas cada. Elas ficam no relatório em `comparacao_legado`, mas saíram da estimativa.

**Estimativa (máxima verossimilhança, com a distribuição implicada pelo motor):**

| Casos | Caudas | `sd_erro_comum_pp` | IC95 (verossimilhança perfilada) |
|---|---|---:|---|
| Todos (10) | t de Student, ν = 5 (padrão) | 3,5 | [1,9; 6,6] |
| Todos (10) | Normais | 3,7 | [2,5; 6,2] |
| Só 1os turnos (5) | ν = 5 | 5,6 | [2,7; >12] |
| Só 2os turnos (5) | ν = 5 | 1,5 | [0,6; 3,9] |

Com quatro casos, o IC95 era [1,5; 9,1]. Os dez casos o estreitaram para [1,9; 6,6].

**Validação deixando um caso de fora (LOO), soma do log score (menor é melhor):**

| Regra | Log score |
|---|---:|
| Padrão fixo de 3,0 | **27,33** |
| Um erro único, reajustado sem o caso avaliado | 29,38 |
| Um erro por turno, reajustado sem o caso avaliado | 29,03 |

Os PITs fora da amostra foram 0,99 em 2010 1T e 1,00 em 2014 1T, ou seja, caudas. Nos outros oito casos, ficaram entre 0,18 e 0,75.

**Decisão: os padrões ficam como estão.** O 1º turno e o 2º turno continuam com 3,0 pp, porque o valor fixo pontuou melhor fora da amostra do que qualquer reajuste.

A separação por turno é sugestiva no ajuste dentro da amostra: o 1º turno sai com erro mais largo e o 2º turno mais estreito. Fora da amostra, porém, ela não se sustenta. Com cinco casos por turno, cada estimativa depende demais do caso deixado de fora. O exemplo mais claro: ajustado nos quatro segundos turnos anteriores, o erro de 2º turno sai 0,65 pp, e o 2º turno de 2026 passa a ser um evento extremo.

## 4. Viés direcional

No total, o erro médio é de +1,8 pp a favor do principal candidato não petista, com IC95 de [−0,9; +4,5]. A média esconde uma diferença nítida entre turnos:

- **1os turnos:** o candidato não petista foi subestimado nas cinco eleições, com média de +4,4 pp. Em um teste de sinais, cinco de cinco tem p = 0,06. A média vem sobretudo de 2010 (+6,6) e 2014 (+9,9), quando Marina Silva caiu na reta final e Serra e Aécio cresceram. A mediana é +2,2.
- **2os turnos:** a média é de −0,7 pp, sem direção consistente.

**Não há base para embutir um viés fixo no padrão.** Com cinco casos, a tendência de 1º turno não é estatisticamente firme. Ela mistura um efeito de pesquisa com movimentos de última hora que o modelo não prevê. O deslocamento continua disponível como cenário (`--vies` no 2º turno). Vale apresentar essa tendência como cenário nas publicações de 1º turno.

## 5. Limites

- **Amostra:** são dez casos de cinco eleições, e os dois turnos da mesma eleição não são independentes. A estimativa melhorou, mas segue imprecisa.
- **Proveniência:** os dados de 2010 a 2022 são da Wikipédia, e não dos registros do TSE. Em 2010 não há margem de erro nem amostra, então a calibração usa ±2 pp. A base auditada `data/historico_v2` ainda não tem nenhum recorte elegível.
- **Horizonte:** a calibração usa só as duas últimas semanas. A deriva (`sd_deriva_30d_pp = 2,0`) segue sendo um valor *a priori*. A base da Wikipédia já permite avaliá-la em horizontes mais longos, mas isso ainda não foi feito.
- **Caudas:** os 1os turnos de 2010 e 2014 caíram nas caudas da distribuição t com ν = 5. Isso sugere que um ν menor no 1º turno pode fazer sentido, mas dez casos ainda não bastam para estimá-lo.
