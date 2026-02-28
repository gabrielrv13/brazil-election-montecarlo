# 🗳️ brazil-election-montecarlo

> Simulação de Monte Carlo + Modelo Bayesiano (PyMC) para as **Eleições Presidenciais Brasileiras de 2026**

Inspirado no trabalho de visualização de dados das eleições húngaras de 2026 ([r/dataisbeautiful](https://www.reddit.com/r/dataisbeautiful/s/ZspHq3TH3R)), este projeto aplica a mesma metodologia ao contexto eleitoral brasileiro, com 40.000 simulações Monte Carlo e análise Bayesiana hierárquica.

---

## 📊 Dados de entrada

| Candidato | Intenção de voto | Desvio padrão |
|---|---|---|
| Lula | 35% | ± 2% |
| Flávio Bolsonaro | 29% | ± 2% |
| Outros | 21% | ± 2% |
| Brancos / Nulos | 15% | ± 2% |

> Os dados usados são estimativas hipotéticas para fins metodológicos. Substitua pelos valores reais de pesquisas em `data/pesquisas.csv` e nos parâmetros de `src/simulation.py`.

---

## ⚙️ Metodologia

### 1. Modelo Bayesiano (PyMC)
Cada candidato recebe um **prior Normal** centrado na sua média de pesquisas com σ = desvio padrão declarado. O modelo é amostrado com **MCMC (No-U-Turn Sampler)** em 4 cadeias paralelas, gerando 40.000 amostras das distribuições posteriores.

```
voto_candidato ~ Normal(μ = média_pesquisa, σ = desvio_padrão)
```

### 2. Simulações Monte Carlo — 1º Turno
Para cada uma das 40.000 iterações:
1. Sorteia votos de `Normal(μ, σ)` para cada candidato
2. Trunca valores negativos em zero
3. Normaliza para somar 100%
4. Calcula votos válidos (excluindo brancos/nulos)
5. Determina vencedor e se há necessidade de 2º turno (nenhum candidato supera 50% dos votos válidos)

### 3. Simulações Monte Carlo — 2º Turno
Modela a transferência de votos de "Outros" com incerteza:
- **40%** → Lula (com σ = 5%)
- **35%** → Flávio Bolsonaro (com σ = 5%)
- **25%** → Brancos/Nulos (descartados)

---

## 📁 Estrutura do repositório

```
brazil-election-montecarlo/
│
├── src/
│   └── simulation.py        # Script principal
│
├── data/
│   └── pesquisas.csv        # Dados de entrada das pesquisas
│
├── outputs/                 # Gerado automaticamente
│   ├── simulacao_eleicoes_brasil_2026.png
│   ├── resultados_1turno.csv
│   └── resultados_2turno.csv
│
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🚀 Como usar

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/brazil-election-montecarlo.git
cd brazil-election-montecarlo
```

### 2. Crie um ambiente virtual (recomendado)
```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Execute a simulação
```bash
python src/simulation.py
```

Os resultados serão salvos automaticamente na pasta `outputs/`.

---

## 📈 Outputs gerados

| Arquivo | Descrição |
|---|---|
| `simulacao_eleicoes_brasil_2026.png` | Painel com 11 gráficos (distribuições, probabilidades, posteriors Bayesianos) |
| `resultados_1turno.csv` | 40.000 linhas com todos os resultados simulados do 1º turno |
| `resultados_2turno.csv` | 40.000 linhas com todos os resultados simulados do 2º turno |

---

## 🔧 Personalizando

Para usar com dados reais, edite as constantes no topo de `src/simulation.py`:

```python
CANDIDATOS  = ['Candidato A', 'Candidato B', 'Outros', 'Brancos/Nulos']
VOTOS_MEDIA = np.array([35.0, 29.0, 21.0, 15.0])   # médias das pesquisas
DESVIO      = 2.0                                    # desvio padrão (margem de erro)
N_SIM       = 40_000                                 # número de simulações
```

---

## 📦 Dependências

| Pacote | Versão mínima | Uso |
|---|---|---|
| `numpy` | 1.26 | Cálculos numéricos e simulações |
| `pandas` | 2.1 | Manipulação de dados |
| `pymc` | 5.10 | Modelagem Bayesiana e MCMC |
| `arviz` | 0.18 | Visualização de posteriors Bayesianos |
| `matplotlib` | 3.8 | Gráficos |
| `seaborn` | 0.13 | Estilo dos gráficos |
| `scipy` | 1.12 | Distribuições estatísticas |

---

## 🧠 Referências

- [What is Monte Carlo Simulation?](https://en.wikipedia.org/wiki/Monte_Carlo_method)
- [PyMC Documentation](https://www.pymc.io/)
- [ArviZ — Exploratory Analysis of Bayesian Models](https://python.arviz.org/)
- [Post original — Eleições Húngaras 2026](https://www.reddit.com/r/dataisbeautiful/s/ZspHq3TH3R)
- [Forecast metodológico (szazkilencvenkilenc.hu)](https://www.szazkilencvenkilenc.hu/forecast-2026-02-09/)

---

## ⚠️ Aviso

Este projeto é estritamente **educacional e metodológico**. Os resultados não constituem previsão eleitoral oficial. Pesquisas eleitorais reais devem ser obtidas junto a institutos certificados pelo TSE.

---

## 📄 Licença

MIT — veja [LICENSE](LICENSE) para detalhes.

---

## 🆕 Versão 2.0 (NEW!)

Uma versão aprimorada está disponível com as seguintes melhorias metodológicas:

### ✨ Novidades

1. **Distribuição Dirichlet**: Garante que os votos sempre somem exatamente 100% de forma matematicamente rigorosa
2. **Incerteza Temporal**: O desvio padrão aumenta proporcionalmente à distância da eleição (efeito "funil")

### 🚀 Como usar

```bash
python src/simulation_v2.py
```

### 📊 Comparação v1 vs v2

| Aspecto | v1 (original) | v2 (nova) |
|---|---|---|
| Distribuição de votos | Normais independentes | Dirichlet (simplex) |
| Incerteza | Fixa (2%) | Temporal (cresce com distância) |
| Garantia soma = 100% | Por normalização | Por construção |
| Realismo estatístico | Bom | Melhor |

📖 Veja o [CHANGELOG_v2.md](CHANGELOG_v2.md) para detalhes técnicos completos.

**Ambas as versões continuam disponíveis no repositório.**

