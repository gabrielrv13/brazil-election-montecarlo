# Fase 3 — Avaliação das previsões de 2026 e calibração do erro comum

Gerado com `python -m src.calibracao` (sementes fixas; JSON completo em `outputs/calibracao/calibracao_fase3.json`). Resultados oficiais em % dos votos válidos, do TSE: [1º turno](https://www.cartacapital.com.br/politica/tse-encerra-apuracao-do-1o-turno/) e [2º turno](https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/presidente-do-tse-anuncia-reeleicao-de-lula-e-faz-balanco-do-2o-turno-das-eleicoes-2026). Os de 2018 e 2022 são os que já estavam em `src/backtesting.py`.

## 1. Previsão do 1º turno (pesquisas até 03/10/2026)

Resultado: F. Bolsonaro 47,03%, Lula 45,16%. Flávio liderou.

| Parâmetro | P(Flávio lidera) | Brier liderança | Log score | PIT Flávio | IC90 Flávio | CRPS total (pp) |
|---|---:|---:|---:|---:|---|---:|
| Erro comum 3,0 (padrão) | 33,6% | 0,883 | 1,09 | 0,94 | [37,9; 47,3] | 6,69 |
| Erro comum 3,4 (estimativa) | 35,2% | 0,840 | 1,04 | 0,92 | [37,3; 48,0] | 6,52 |

O resultado de Flávio ficou dentro do IC90, mas fora do IC80 (PIT 0,94). O de Lula ficou perto do centro (PIT 0,58). O Brier de 0,88 é pior que o de uma moeda entre os dois (0,50): o modelo apostou no líder errado porque as pesquisas erraram na mesma direção.

## 2. Previsão do 2º turno (pesquisas pós-1º turno até 24/10/2026)

Resultado: Lula 51,79%, Flávio 48,21%. A média das pesquisas dava a Flávio 50,94% da fatia de dois partidos.

| `sd_fatia` | P(Flávio vence) | Brier | Log score | PIT | IC90 da fatia de Flávio | CRPS |
|---|---:|---:|---:|---:|---|---:|
| 2,5 (publicado) | 64,4% | 0,414 | 1,03 | 0,14 | [46,7; 55,1] | 1,66 |
| 3,0 (novo padrão) | 61,8% | 0,382 | 0,96 | 0,18 | [45,9; 55,9] | 1,61 |
| 3,4 (estimativa) | 60,4% | 0,365 | 0,93 | 0,21 | [45,3; 56,5] | 1,61 |

O resultado ficou dentro do IC80 e do IC90 nos três casos. Um DP maior pontua melhor aqui porque o favorito perdeu.

## 3. Calibração do erro comum

Cada caso compara a média das pesquisas da última semana com o resultado, na fatia de dois partidos do candidato da direita que liderava a disputa (`A/(A+B)`). Erro = resultado − pesquisas.

| Caso | Pesquisas | Resultado | Erro (pp) | Pesquisas usadas | Ressalva |
|---|---:|---:|---:|---:|---|
| 2018 1T (Bolsonaro × Haddad) | 59,17 | 61,12 | +1,95 | 3 | transcrição legada sem proveniência |
| 2022 1T (Bolsonaro × Lula) | 42,72 | 47,15 | +4,43 | 3 | transcrição legada sem proveniência |
| 2026 1T (Flávio × Lula) | 48,85 | 51,01 | +2,17 | 56 | base do projeto, datas validadas |
| 2026 2T (Flávio × Lula) | 50,94 | 48,21 | −2,73 | 52 | base pós-1º turno |

**Estimativa (máxima verossimilhança, com a distribuição implicada pelo motor):**

| Caudas | `sd_erro_comum_pp` | IC95 (verossimilhança perfilada) |
|---|---:|---|
| t de Student, ν = 5 (padrão) | 3,4 | [1,5; 9,1] |
| Normais | 2,7 | [1,4; 6,9] |

**Validação deixando um caso de fora (LOO):** somando o log score fora da amostra, o padrão fixo de 3,0 obtém 10,45, contra 10,73 da estimativa refeita sem o caso avaliado (menor é melhor). Os PITs fora da amostra são 0,70, 0,94, 0,74 e 0,17, todos dentro do esperado para uma distribuição uniforme com quatro observações.

**Decisão:** o padrão de 3,0 pp foi mantido no 1º turno. A estimativa de 3,4 não é distinguível dele e pontuou pior fora da amostra. O 2º turno passou de 2,5 para o mesmo 3,0, porque mede a mesma grandeza. O 2,5 vinha do backtest legado com vazamento temporal (auditoria A10).

## 4. Viés direcional

O erro médio a favor do candidato da direita é de +1,45 pp, com IC95 de [−3,3; +6,2]. Nos três 1os turnos o erro foi sempre positivo (média de +2,85 pp), mas no 2º turno de 2026 ele se inverteu (−2,73 pp). **Não há evidência para embutir um viés fixo no padrão.** O deslocamento continua disponível como cenário (`--vies` no 2º turno). A hipótese de um viés específico de 1º turno precisa de mais eleições para ser testada.

## 5. Limites

- **Amostra:** são quatro casos de três eleições. A largura do IC95 (fator de 6 entre os extremos) é o principal resultado: o erro comum continua mal identificado.
- **Proveniência:** os casos de 2018 e 2022 vêm das transcrições legadas de `data/historico/`. Não há fonte documentada para elas, e a base auditada `data/historico_v2` ainda não tem nenhum recorte elegível (todos em quarentena).
- **Horizonte:** a calibração usa só a última semana. A deriva (`sd_deriva_30d_pp = 2,0`) segue sendo um valor *a priori* sem validação; para avaliar horizontes longos é preciso liberar os recortes de 2018 e 2022 em `historico_v2`.
- **Caudas:** com quatro casos não dá para estimar ν. O valor 5 continua sendo uma hipótese.
