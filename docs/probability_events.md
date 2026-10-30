# Contratos dos eventos eleitorais — A02 / P0.3

Implementação de 30/10/2026. Contrato de eventos **v2**. Todos os novos valores
são frações em `[0, 1]`; telas e PDF multiplicam por 100. Os sorteios, alphas,
tetos, redistribuição, margens e sequência de números aleatórios são preservados.

## Contrato anterior e migração

| Campo/caminho | Antes | Agora |
|---|---|---|
| `SimulationResult.pv`, CLI e dashboard modular | Frequência de `argmax` (liderança), documentada/exibida como vitória direta | Mantém o valor legado, descontinuado. Não usar como vitória direta. Usar os campos explícitos abaixo. |
| `df1.vencedor` / `lider_1t` | Primeiro `argmax`, mesmo abaixo de 50%; empate resolvido pela ordem das colunas | Preservados como aliases legados de liderança, inclusive seu desempate. `vencedor_1t` é o novo vencedor direto ou nulo. |
| `p2t` / `tem_2turno` | `max(validos) < 50`, deixando exatamente 50% fora dos dois eventos | Complemento de qualquer vitória direta: `max(validos) <= 50`. |
| Classificação nos gráficos | Top-2 em todos os sorteios, inclusive quando não haveria segundo turno; empate por ordenação | Evento conjunto: haver segundo turno **e** ocupar uma das duas vagas. |
| `simulation_v2.p2v` | Vitória em confrontos hipotéticos de TODOS os sorteios, inclusive com vitória direta no primeiro turno | Vitória condicionada à realização do segundo turno, usando somente as linhas correspondentes, após gerar os mesmos sorteios de antes. CSV e gráficos também usam esse recorte. |
| Gráfico histórico | Substituía `p2v` ausente por `pv` por candidato | Um evento por série; ausência é ausência, sem substituir por outro evento. |
| Histórico SQLite | Sem identificação do contrato; impossível distinguir todos os significados | Migração aditiva do esquema 1 para 2 e versão do contrato em cada registro. |

A escala das funções legadas `simulation_v2.relatorio` continua **0–100** para
`pv`, `p2v`, `p2t`; o adaptador de PDF converte para **0–1**. Os novos resumos do
núcleo usam sempre **0–1**. A assinatura de retorno do relatório legado continua
`(pv, p2v, p2t)`, mas a correção de condicionamento de `p2v` exige que consumidores
externos adotem o contrato v2. Não confundir registros novos com os antigos.

## Eventos explícitos

Seja `V[i,c]` a participação **final dos votos válidos**, após os mesmos ajustes
e normalização já existentes. Brancos/nulos não entram no denominador destes
eventos. Não se aplica o limiar a votos totais nem à média/mediana dos sorteios.

- `p_lideranca[c]`: frequência de liderança após o desempate analítico descrito
  abaixo. Liderar não exige maioria absoluta.
- `p_vitoria_1t[c]`: frequência de `V[i,c] > 50`. O limiar é estrito, sem
  arredondamento de exibição nem margem de tolerância para declarar vitória.
- `p2t`: frequência de nenhum candidato superar 50% dos válidos.
- `p_classificacao_2t[c]`: probabilidade **incondicional** de haver segundo turno
  e o candidato ocupar uma das duas vagas. É zero nos sorteios com vitória direta.
  Quando `p2t > 0`, a probabilidade condicional de classificação é
  `p_classificacao_2t[c] / p2t`; quando `p2t == 0`, é indefinida.
- `p2v[c]`: `P(c vencer o segundo turno | ocorrer segundo turno)`. Já inclui a
  chance de classificação; NÃO é `P(vencer | o próprio c se classificar)`.
  Não é probabilidade de liderança, nem probabilidade final de eleição somando os
  dois turnos. É `{}` quando o segundo turno não foi simulado/não ocorre ou os
  dados não comprovam o evento. A CLI e o dashboard modulares ainda não simulam
  o segundo turno: continuam fornecendo `{}`.

`SimulationResult` deriva os novos campos e `p2t` de `*_val`, em vez de confiar
em resumos antigos. Para `p2v` v2 exige linhas com `tem_2turno` e dados explícitos
de votos/finalistas (ou créditos de vitória). Sem as colunas de votos válidos, o
objeto mantém contrato legado v1 e deixa os novos eventos vazios; não os inventa.

## Empates

Exatamente 50% **não** é maioria absoluta, incluindo o caso 50/50. Não há
arredondamento prévio: 50,0000001% supera o limiar, 49,9999999% não supera.

O modelo não dispõe de metadados de desempate. A convenção v2 divide o crédito de
liderança igualmente entre os empatados no máximo. Para classificação, quem está
acima do limiar da segunda colocação recebe uma vaga; as vagas restantes dividem-se
igualmente entre os empatados nesse limiar. Em 40/30/30, os créditos são 1, 1/2,
1/2; em um empate triplo, 2/3 para cada. São expectativas analíticas de desempate
uniforme, **não** probabilidades de co-liderança simultânea nem uma implementação
de critérios legais. Nenhuma chamada adicional ao RNG é feita.

Se o motor legado de segundo turno não consegue escolher um par único por causa
de empate na última vaga, ele informa a limitação e retorna segundo turno
indisponível, em vez de publicar probabilidades para um par arbitrário. Os
sorteios hipotéticos já realizados não são alterados. Empates exatos nos votos de
um confronto final dividem o crédito de vitória por metade nos resumos; a coluna
legada `vencedor_2T` conserva seu desempate anterior, e não deve gerar resumos v2.

## Identidades e exemplo

Para resultados completos do contrato v2:

```
sum(p_lideranca.values()) = 1
sum(p_vitoria_1t.values()) + p2t = 1
sum(p_classificacao_2t.values()) = 2 * p2t
p_vitoria_1t[c] <= p_lideranca[c]
p_classificacao_2t[c] <= p2t
```

Se `p2v` estiver disponível, sua soma é 1. Para um motor condicional completo,
`p2v[c] <= p_classificacao_2t[c] / p2t`. Não preencher `p2v` com zeros quando
indefinido e não somá-lo diretamente à vitória no primeiro turno.

No cenário constante **45/35/20**: liderança de A = 100%, vitória direta de todos
= 0%, segundo turno = 100%, classificação de A/B/C = 100%/100%/0%. O teste com o
motor real e semente 42 em 10.000 sorteios reproduz essa distinção; outros
parâmetros podem produzir algumas vitórias diretas, calculadas sorteio a sorteio.

## Persistência e consumidores

- CSV por sorteio: mantém votos e campos legados, adiciona `event_contract_version`,
  `vencedor_1t` e colunas `evento_lideranca_*`, `evento_vitoria_1t_*`,
  `evento_classificacao_2t_*`. Os créditos podem ser fracionários nos empates.
- Exportação modular: CSV adicional `<timestamp>_probabilidades.csv` com os quatro
  eventos, `p2v` e versão. `p2v` ausente é célula vazia, não zero.
- SQLite: adiciona `events_json`, sem reescrever probabilidades ou datas de linhas
  antigas. A leitura não altera o banco; a migração ocorre na inicialização.
  Registros antigos recebem versão 1 na leitura e novos eventos vazios, pois a
  liderança agregada não permite reconstruir maiorias, empates ou classificados.
- PDF e dashboards: liderança, vitória direta e classificação têm rótulos distintos;
  o PDF informa maioria estrita e a chance de segundo turno. Downloads modulares
  apontam aos arquivos da execução atual, evitando apresentar relatórios antigos.
- Gráfico de histórico: `event="p_lideranca"`, `"p_vitoria_1t"`,
  `"p_classificacao_2t"` ou `"p2v"`. Registros legados não são misturados com
  os eventos v2. A chamada antiga `use_p2v=False` preserva a visão de liderança
  `pv` em DataFrames antigos sem novos campos, com rótulo corrigido. DataFrames
  sem versão contendo `p2v` são rotulados como contrato legado.
- O intervalo histórico continua uma aproximação Monte Carlo; no evento
  condicional `p2v` v2, o denominador é o número de sorteios com segundo turno.
- `simulation_combined.py` só recebe `pv`/`p2t` do relatório legado para o primeiro
  turno, sem usá-los como vitória direta. Seu confronto binário separado e os
  publicadores de segundo turno não consomem esses campos; não foram recalibrados.
- O backtesting usa seu motor próprio e métricas de liderança (`prob_vencedor`,
  `pred_winner_prob` são nomes legados). Não passam a medir maioria absoluta nesta
  correção e não servem como Brier de vitória direta; A01 continua bloqueando os
  snapshots sem disponibilidade comprovada.

## Incompatibilidades intencionais

Consumidores de `pv` como vitória direta precisam migrar para `p_vitoria_1t`.
Consumidores de `p2v` legado precisam distinguir a versão: o denominador corrigido
é o subconjunto de segundo turno. Gráficos de classificação deixam de somar 200%
quando há chance de vitória direta. A migração antiga não preenche retroativamente
os novos eventos; dados insuficientes ficam indisponíveis. Exportações ganham
colunas/arquivo adicionais, mas as colunas de votos e aliases legados permanecem.

## Validação

Testes de fronteira, empates, identidades, entradas inválidas, cenário 45/35/20,
regressão numérica contra o motor pré-A02, integração CLI → CSV/PDF/SQLite,
Streamlit real (AppTest), migração de banco legado e seleção condicional de
segundo turno. Toda escrita de teste fica em temporários; os artefatos existentes
em `outputs/` não são sobrescritos.

Validação final com `MPLBACKEND=Agg`: **342 passed, 14 warnings**, em 37,74 s.
Cobertura configurada: **90,81%**, gate de 80% aprovado. São **35 testes novos**
em `tests/test_election_events.py`; expectativas antigas foram corrigidas onde
codificavam a mistura de eventos ou o desempate pela ordem das colunas. Os avisos
são de APIs antigas de Matplotlib/datetime e do aviso de migração do ArviZ, sem falhas de teste. O PDF do fluxo
45/35/20 foi renderizado com Poppler e inspecionado visualmente.

Comando usado no PowerShell:

```powershell
$env:MPLBACKEND = 'Agg'
$env:WIN_PD_OVERRIDE_LOCAL_APPDATA = Join-Path (Get-Location).Path '.test_tmp_a02_review_cache'
venv/Scripts/python.exe -m pytest -p no:cacheprovider --basetemp=.test_tmp_a02_review_full -q
```

O override redireciona o cache de bibliotecas para um temporário local. Sem ele,
o ArviZ encontrou acesso negado ao atualizar seu aviso diário em LocalAppData.
O cache do pytest também foi desativado por permissões preexistentes. Nenhuma
dependência nem configuração permanente do ambiente foi alterada.

`git diff --check` passou. A revisão semântica também executou os testes relevantes:
**129 passed, 13 warnings**, incluindo a regressão do denominador comum de p2v.


## Verificação final de p2v

O denominador é o total de sorteios em que ocorre segundo turno, comum a todos
os candidatos. Cada candidato recebe crédito zero nos sorteios em que não se
classifica; vitória recebe 1 e empate final recebe 1/2. Não se divide pelo número
de classificações do próprio candidato. Por exemplo, em quatro segundos turnos,
um candidato que se classifica e vence apenas um tem `p2v = 1/4`, não 100%.
No formato alternativo `<candidato>_win`, os créditos devem ser explícitos,
finitos e somar 1 em cada linha. NaN é rejeitado: ignorá-lo na média mudaria
silenciosamente o denominador. Os registros legados permanecem identificados
como versão 1 e não são reinterpretados.
