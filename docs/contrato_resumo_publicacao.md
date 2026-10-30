# Contrato do resumo para publicação (A05)

`validar_resumo` valida o JSON antes de qualquer criação de diretório ou escrita
pelo CLI. Os dois idiomas são renderizados antes da escrita. Erros do contrato
são `ValueError` com o caminho do campo; o CLI informa a falha e retorna 1.
Campos adicionais são aceitos. Nenhum valor é convertido silenciosamente.

Todos os campos abaixo são obrigatórios. Objetos devem ser objetos JSON;
números são inteiros ou reais finitos, nunca booleanos ou strings numéricas.

| Campo | Contrato |
| --- | --- |
| `executado_em` | String ISO com fuso; idade até `max_horas` (36 por padrão), tolerância de 6 minutos no futuro |
| `cand_a`, `cand_b` | Strings não vazias, sem controles, distintas após strip/casefold |
| `fatia_a` | Número em (0, 100), média agregada das pesquisas **antes** do viés |
| `p_vitoria_a`, `p_vitoria_b` | Números em [0, 100]; soma 100 com tolerância absoluta de 0,01 pp e epsilon de ponto flutuante, pelo arredondamento independente a duas casas |
| `fatia_a_ic90` | Array de dois números em [0, 100], ordenados; quantis 5% e 95% da fatia simulada |
| `margem_mediana_pp` | Número em [0, 100]; mediana de `abs(voto_a - voto_b)` |
| `margem_votos_mediana` | Inteiro não negativo; mediana da diferença absoluta dos votos inteiros simulados |
| `parametros.sd_fatia_pp` | Número em (0, 4.9], domínio da calibração atual |
| `parametros.vies_pp_a` | Número finito; `fatia_a + vies_pp_a` em (0, 100) |
| `parametros.tau` | Número positivo (dias) |
| `parametros.data_min` | Data ISO ou null |
| `pesquisas.n` | Inteiro >= 1 |
| `pesquisas.n_institutos` | Inteiro entre 1 e n |
| `pesquisas.n_efetivo` | Número entre 1 e n, tamanho efetivo de Kish |
| `pesquisas.soma_media` | Número em [0, 200], soma média das duas intenções percentuais antes da normalização |
| `sensibilidade` | Objeto; pode ser vazio (o gerador omite frases sem as linhas opcionais) |
| `sensibilidade.<viés>` | Chave numérica finita, fatia + viés em (0, 100); objeto não vazio |
| `sensibilidade.<viés>.<sd>` | Chave numérica em (0, 4.9]; valor numérico em [0, 100] |

O gerador consome diretamente os campos do topo, o desvio, as contagens e o
tamanho efetivo das pesquisas. Na sensibilidade usa as linhas `1.0` e `-1.0`
e a coluna de desvio mais próxima do desvio da execução. O contrato valida
**todas** as células, inclusive as não selecionadas. Os outros parâmetros e
`soma_media` completam o esquema atual e permitem validar a entrada do modelo.

A mediana da margem absoluta deve estar entre a menor e a maior distância
absoluta a 50% permitidas pelo intervalo (limite inferior zero se cruza 50%).
A tolerância é 0,015 pp: 0,01 pela transformação dos quantis arredondados e
0,005 pelo arredondamento da mediana.

Não se exige que a média agregada esteja no intervalo simulado: são variáveis
diferentes e há viés configurável. Não se iguala margem mediana a duas vezes
a média menos 100. Não se convertem as duas medianas por um eleitorado fixo:
a abstenção varia e os votos são truncados por simulação. A tabela de
sensibilidade usa outra amostra Monte Carlo e não precisa coincidir com a
probabilidade principal nem ser estritamente monótona.

Resumos válidos do esquema atual continuam aceitos, inclusive soma 99,99 ou
100,01 por arredondamento e ausência das linhas opcionais de sensibilidade.
Valores incompletos, tipos coercíveis e números não finitos antes tolerados
passam a falhar. Falhas de validação/renderização preservam arquivos existentes.
Erros de disco durante a escrita são relatados; não há transação entre os dois
arquivos em caso de falha de I/O após a validação.

## A06 — contrato versão 2 e migração

O produtor passa a escrever `schema_version: 2`. Os campos históricos mantêm
seus significados: `fatia_a` é a agregação anterior ao viés; `fatia_a_ic90` e
`p_vitoria_a/b` vêm dos sorteios, nunca da agregação observada.

| Campo novo obrigatório na versão 2 | Significado |
| --- | --- |
| `fatia_agregada_a` | Alias explícito de `fatia_a`, em %, arredondado a 3 casas |
| `fatia_central_a` | `fatia_a + parametros.vies_pp_a`, entrada da Dirichlet, em %, 3 casas |
| `fatia_simulada_media_a` | Média efetiva de `voto_a` após todas as transformações, em %, 3 casas |
| `parametros.vies_candidato` | Identidade exata a que o viés informado se refere |
| `parametros.vies_pp` | Deslocamento assinado em pp para essa identidade |
| `transformacoes` | `usar_teto` booleano e `rej_a/rej_b` efetivos em [0,100] |

O sinal positivo favorece o candidato nomeado. `vies_pp_a` continua na coordenada
histórica A: igual ao viés nomeado se a referência é A, oposto se é B. O gate
verifica identidade, sinal, aliases, centro (tolerância 0,001 pp pelo
arredondamento) e tipos. Versões desconhecidas são rejeitadas. O resumo exige
metadados dos sorteios calibrados para evitar combinar parâmetros de outra execução.

Sem versão (ou versão 1), o JSON antigo continua aceito. O publicador separa a
fatia agregada, o centro reconstruído dos parâmetros e o intervalo simulado;
informa que a média dos sorteios está indisponível. Ela **não** é reconstruída
pelo centro nem pelos quantis. Para obtê-la, execute novamente a simulação.

Exemplo: agregada 51%, viés de -5 pp para A, centro 46%, média dos sorteios
aproximadamente 46%, intervalo de 90% aproximadamente [41,9%; 50,1%] e
P(A vencer) aproximadamente 5,4% (dependem da amostra). Com viés zero o centro
é 51%; com +5 pp é 56%. A média efetiva sempre vem dos sorteios.

O modelo mantém a categoria branca mínima de 0,1 na Dirichlet, os tetos
opcionais de rejeição e a renormalização para votos válidos. Sem teto, a
exclusão da categoria branca preserva o centro de A/(A+B); com teto, o centro
de entrada pode diferir sistematicamente da média final. Não se exige igualdade
nem que a agregada esteja no intervalo. Nenhuma dispersão foi recalibrada.
Gráficos usam os mesmos sorteios, distinguem a agregada e o centro de entrada,
e marcam a média simulada. Probabilidades e quantis também vêm desses sorteios.

Migração do CLI: viés não zero exige `--vies-candidato "Nome exato"`.
`--vies` mantém a unidade e o sentido positivo para a referência explicitamente
nomeada. Chamadas antigas sem identidade falham com mensagem; viés zero segue
compatível. A API `simular_calibrado(..., vies_pp_a=...)` mantém seu contrato
histórico explicitamente vinculado a `cand_a`. A tabela de sensibilidade mantém
cenários absolutos para A a partir da agregada, substituindo o viés principal;
não são incrementos sobre o cenário ajustado. Textos PT/EN explicitam isso.
