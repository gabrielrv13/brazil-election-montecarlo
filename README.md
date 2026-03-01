# 🗳️ brazil-election-montecarlo

> Simulação de Monte Carlo + Modelo Bayesiano (PyMC) para as **Eleições Presidenciais Brasileiras de 2026**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Inspirado no trabalho de visualização de dados das eleições húngaras de 2026 ([r/dataisbeautiful](https://www.reddit.com/r/dataisbeautiful/s/ZspHq3TH3R)), este projeto aplica a mesma metodologia ao contexto eleitoral brasileiro, com 40.000 simulações Monte Carlo e análise Bayesiana hierárquica.

---

## ✨ Versão 2.5 (Atual)

### Principais características:

1. **📊 Dados via CSV** — Atualize as pesquisas editando apenas `data/pesquisas.csv`, sem mexer no código!
2. **🎲 Distribuição Dirichlet** — Garante matematicamente que os votos sempre somam 100%
3. **⏳ Incerteza Temporal** — O desvio padrão aumenta com a distância da eleição (efeito "funil")

---

## 🚀 Início Rápido

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/brazil-election-montecarlo.git
cd brazil-election-montecarlo
```

### 2. Instale as dependências
```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### 3. Atualize os dados (opcional)
Edite `data/pesquisas.csv` com os valores mais recentes:

```csv
candidato,intencao_voto_pct,desvio_padrao_pct,fonte,data
Lula,37.0,2.0,Datafolha,2026-02-20
Flávio Bolsonaro,27.0,2.0,Datafolha,2026-02-20
Outros,21.0,2.0,Datafolha,2026-02-20
Brancos/Nulos,15.0,2.0,Datafolha,2026-02-20
```

📖 Guia completo: [ATUALIZANDO_PESQUISAS.md](ATUALIZANDO_PESQUISAS.md)

### 4. Execute a simulação
```bash
python src/simulation_v2.py
```

Os resultados estarão em `outputs/`!

---

## 📁 Estrutura do repositório

```
brazil-election-montecarlo/
│
├── src/
│   ├── simulation.py           # v1 original (mantida)
│   ├── simulation_v2.py         # v2 atual ⭐
│   └── comparar_v1_v2.py        # Comparação entre versões
│
├── data/
│   ├── pesquisas.csv                      # ← Edite aqui! 
│   └── pesquisas_exemplo_multiplas.csv    # Exemplo de agregação
│
├── outputs/                     # Gerado automaticamente
│   ├── simulacao_eleicoes_brasil_2026_v2.png
│   ├── resultados_1turno_v2.csv
│   └── resultados_2turno_v2.csv
│
├── ATUALIZANDO_PESQUISAS.md    # Guia de atualização de dados
├── CHANGELOG_v2.md              # Histórico de mudanças
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

---

## ⚙️ Metodologia

### 1. Modelo Bayesiano (PyMC)
Usa distribuição **Dirichlet** como prior para garantir que as proporções sempre somem 100%, com amostragem MCMC (No-U-Turn Sampler) em 4 cadeias paralelas.

### 2. Simulações Monte Carlo — 1º Turno
- 40.000 iterações
- Sorteia votos usando Dirichlet (garante soma = 100%)
- Calcula votos válidos e identifica vencedor
- Determina necessidade de 2º turno

### 3. Simulações Monte Carlo — 2º Turno
- Modela transferência de votos dos candidatos eliminados
- Usa Dirichlet para garantir proporções válidas
- Assume incerteza na migração de votos

### 4. Incerteza Temporal
Fórmula: `σ(t) = σ_base × √(dias_restantes / 30)`

| Distância | Desvio padrão |
|---|---|
| 240 dias (8 meses) | 5.66% |
| 120 dias (4 meses) | 4.00% |
| 30 dias (1 mês) | 2.00% |
| 7 dias (1 semana) | 0.96% |

---

## 📊 Outputs gerados

| Arquivo | Descrição |
|---|---|
| `simulacao_eleicoes_brasil_2026_v2.png` | Painel com 11 gráficos |
| `resultados_1turno_v2.csv` | 40.000 linhas com todas as simulações do 1º turno |
| `resultados_2turno_v2.csv` | 40.000 linhas com todas as simulações do 2º turno |

---

## 🔄 Workflow típico

```bash
# 1. Saiu uma nova pesquisa? Atualize o CSV
nano data/pesquisas.csv

# 2. Rode a simulação
python src/simulation_v2.py

# 3. Veja os resultados
open outputs/simulacao_eleicoes_brasil_2026_v2.png

# 4. Suba no GitHub
git add .
git commit -m "chore: update polls with Datafolha 2026-02-20"
git push
```

---

## 📦 Dependências

| Pacote | Versão | Uso |
|---|---|---|
| `numpy` | ≥1.26 | Cálculos numéricos |
| `pandas` | ≥2.1 | Manipulação de dados e CSV |
| `pymc` | ≥5.10 | Modelagem Bayesiana |
| `arviz` | ≥0.18 | Visualização de posteriors |
| `matplotlib` | ≥3.8 | Gráficos |
| `seaborn` | ≥0.13 | Estilo dos gráficos |

---

## 🧠 Referências

- [Metodologia Chronicler-v2](https://www.szazkilencvenkilenc.hu/methodology-v2/) — Modelo húngaro que inspirou este projeto
- [PyMC Documentation](https://www.pymc.io/)
- [ArviZ — Exploratory Analysis of Bayesian Models](https://python.arviz.org/)
- [Post original — r/dataisbeautiful](https://www.reddit.com/r/dataisbeautiful/s/ZspHq3TH3R)

---

## 🤝 Contribuindo

Pull requests são bem-vindos! Para mudanças maiores:

1. Crie uma branch: `git checkout -b feature/nova-funcionalidade`
2. Commit suas mudanças: `git commit -m "feat: adiciona nova funcionalidade"`
3. Push para a branch: `git push origin feature/nova-funcionalidade`
4. Abra um Pull Request

---

## ⚠️ Aviso

Este projeto é estritamente **educacional e metodológico**. Os resultados não constituem previsão eleitoral oficial. Pesquisas eleitorais reais devem ser obtidas junto a institutos certificados pelo TSE.

---

## 📄 Licença

MIT — veja [LICENSE](LICENSE) para detalhes.

---

## 📧 Contato

Dúvidas? Abra uma [issue](https://github.com/seu-usuario/brazil-election-montecarlo/issues)!
