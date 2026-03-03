# brazil-election-montecarlo

Monte Carlo simulation for the 2026 Brazilian presidential election — 40,000 iterations with Dirichlet sampling, poll aggregation, rejection ceilings, and a dedicated standalone second-round model.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-2.7.0-green.svg)](https://github.com/gabrielrv13/brazil-election-montecarlo/releases/tag/v2.7.0)

---
## Inspiration

Inspired by the Hungarian election visualization published on [r/dataisbeautiful](https://www.reddit.com/r/dataisbeautiful/s/ZspHq3TH3R) by [u/Exciting-Lab1263](https://www.reddit.com/user/Exciting-Lab1263/), which applied Monte Carlo simulation to the 2026 Hungarian parliamentary election using the [Chronicler-v2 methodology](https://www.szazkilencvenkilenc.hu/methodology-v2/). This project adapts the same core approach to the Brazilian electoral context.

---
## Overview

This project models the 2026 Brazilian presidential election through two complementary simulations:

- **`simulation_v2.py`** — Full first-round simulation with dynamic second-round derivation. Aggregates polls from multiple institutes, applies temporal weighting and outlier detection, redistributes undecided voters, and propagates the actual top-2 finalists per simulation into the runoff.

- **`simulation_2turno.py`** — Standalone second-round simulation for use after the two finalists are confirmed. Operates on its own poll data (`pesquisas_2turno.csv`) and uses a 3-category Dirichlet directly, without running the full first-round model.

---

## Features

| Version | Feature |
|---|---|
| v2.2 | Rejection index as electoral ceiling |
| v2.3 | Poll aggregation — temporal weighting + outlier detection |
| v2.4 | Undecided voter redistribution (rejection-adjusted) |
| v2.5 | Dynamic second round from actual per-simulation top-2 |
| v2.6 | Absolute vote projections + stochastic abstention + PDF report + Streamlit dashboard |
| v2.7 | Standalone second-round simulation (`simulation_2turno.py`) |

---

## Repository Structure

```
brazil-election-montecarlo/
├── src/
│   ├── simulation_v2.py          # Full first-round + dynamic second-round model
│   ├── simulation_2turno.py      # Standalone second-round model (v2.7)
│   └── dashboard.py              # Streamlit dashboard
├── data/
│   ├── pesquisas.csv             # First-round poll data
│   └── pesquisas_2turno.csv      # Second-round poll data (post-October 5)
├── tests/
│   ├── test_simulation.py
│   └── test_rejeicao.py
├── outputs/                      # Generated automatically (gitignored)
├── .github/ISSUE_TEMPLATE/
├── requirements.txt
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/gabrielrv13/brazil-election-montecarlo.git
cd brazil-election-montecarlo

python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
```

### 2. Update poll data

Edit `data/pesquisas.csv` with the latest numbers:

```csv
candidato,intencao_voto_pct,rejeicao_pct,desvio_padrao_pct,indecisos_pct,instituto,data
Lula,40.0,48.2,2.2,5.1,Parana Pesquisas,2026-02-27
Flávio Bolsonaro,35.9,46.4,2.2,5.1,Parana Pesquisas,2026-02-27
Romeu Zema,4.0,36.4,2.2,5.1,Parana Pesquisas,2026-02-27
Outros,7.6,0.0,2.2,5.1,Parana Pesquisas,2026-02-27
Brancos/Nulos,7.2,0.0,2.2,5.1,Parana Pesquisas,2026-02-27
```

- Multiple polls from different institutes can be added — the model aggregates them with temporal weighting.
- `rejeicao_pct` sets the electoral ceiling for each candidate.
- `indecisos_pct` is optional; if present, undecided voters are redistributed proportionally.

### 3. Run the simulation

```bash
# First round + dynamic second round
python src/simulation_v2.py

# Standalone second round (after finalists are confirmed)
python src/simulation_2turno.py

# Dashboard
streamlit run src/dashboard.py
```

Results are saved to `outputs/`.

---

## Methodology

### Poll Aggregation

Multiple polls are combined using exponential temporal decay:

```
weight = exp(-days_ago / τ)   where τ = 7 days
```

Combined standard deviation accounts for both within-poll variance and inter-institute disagreement. Outliers are excluded using a Modified Z-Score (MAD-based) threshold.

### Rejection Ceiling

Each candidate has a hard electoral ceiling derived from their rejection rate:

```
ceiling = 100% - rejection%
```

Vote shares are clipped to this ceiling before normalization.

### Undecided Redistribution

Undecided voters are distributed among candidates proportionally to their available electoral space:

```
weight_i = vote_share_i × (100 - rejection_i) / 100
gain_i   = weight_i / Σweights × undecided × (1 - blank_fraction)
```

### Simulation

Each of the 40,000 iterations draws a Dirichlet sample parameterized by the aggregated poll estimates. Abstention is sampled per iteration from a Normal distribution calibrated to historical Brazilian elections:

| Round | Abstention |
|---|---|
| First round | Normal(20%, σ=2%) |
| Second round | Normal(22%, σ=3%) |

### Second Round (v2.5+)

The finalists in each simulation are the actual top-2 vote-getters from that specific first-round draw — not fixed in advance. This captures the full distribution of possible matchups, including low-probability scenarios.

### Standalone Second Round (v2.7)

After October 5, when the two finalists are known, `simulation_2turno.py` runs a 3-category Dirichlet `[A, B, blank/null]` directly against second-round-specific poll data, without the overhead of the first-round model.

---

## Outputs

| File | Description |
|---|---|
| `simulacao_eleicoes_brasil_2026.png` | 11-panel visualization (first round) |
| `resultados_1turno.csv` | 40,000 rows — per-simulation first-round results |
| `resultados_2turno.csv` | 40,000 rows — per-simulation second-round results |
| `relatorio_simulacao.pdf` | PDF summary report |
| `simulacao_2turno.png` | 3-panel standalone second-round visualization |
| `resultados_2turno_standalone.csv` | 40,000 rows — standalone second-round results |

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `numpy` | ≥1.26 | Numerical computation |
| `pandas` | ≥2.1 | Data manipulation |
| `pymc` | ≥5.10 | Bayesian prior construction |
| `arviz` | ≥0.18 | Posterior visualization |
| `matplotlib` | ≥3.8 | Visualization |
| `seaborn` | ≥0.13 | Plot styling |
| `streamlit` | ≥1.32 | Interactive dashboard |
| `reportlab` | ≥4.1 | PDF report generation |

---

## Typical Workflow

```bash
# New poll released
# 1. Add it to pesquisas.csv
# 2. Run
python src/simulation_v2.py

# 3. Commit
git add data/pesquisas.csv
git commit -m "chore: update polls - <institute> <date>"
git push
```

---

## Disclaimer

This project is strictly educational and methodological. Results do not constitute official electoral forecasting. Real electoral polling must be obtained from TSE-certified institutes.

---

## License

MIT — see [LICENSE](LICENSE) for details.
