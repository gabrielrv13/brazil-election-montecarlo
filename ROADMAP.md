# Roadmap — brazil-election-montecarlo

---

## Status por Versão

| Versão | Feature | Status |
|---|---|---|
| v2.2 | Índice de rejeição como teto eleitoral | ✅ Concluído |
| v2.3 | Agregação automática de pesquisas + outlier detection | ✅ Concluído |
| v2.4 | Categoria "Indecisos" com redistribuição proporcional | ✅ Concluído |
| v2.5 | 2º turno dinâmico baseado no top-2 real do 1º turno | ✅ Concluído |
| v2.6 | Votos absolutos com abstenção estocástica + PDF + Dashboard | ✅ Concluído |
| v2.7 | Simulação standalone do 2º turno (simulation_2turno) | ✅ Concluído |
| v2.8 | First-round margin distribution + polymarket_edge() + --n-sim | ✅ Concluído |
| v2.9 | Backtesting module (2018/2022) | ✅ Concluído |

---

## Timeline
```
Fevereiro 2026
├── v2.2 ✅  Rejeição como teto eleitoral
├── v2.3 ✅  Agregação de pesquisas + outliers
├── v2.4 ✅  Indecisos com redistribuição proporcional
└── v2.5 ✅  2º turno dinâmico (top-2 real por simulação)

Março 2026
├── v2.6 ✅  Votos absolutos + PDF + Dashboard Streamlit
├── v2.7 ✅  simulation_2turno standalone
│            CSV próprio · Dirichlet 3 categorias · reutiliza simulation_v2
├── v2.8 ✅  First-round margin distribution + polymarket_edge() + --n-sim flag
│            Habilita P(margin > X) para mercados Polymarket de threshold
└── v2.9 ✅  Backtesting module (promovido de v3.3.0)
             2018/2022 · Brier score · shy Bolsonaro quantification
             Pré-requisito para uso operacional na Polymarket

Abril 2026
└── v3.0.0  Historical tracker + SimulationConfig refactor + clean filenames

Outubro 2026 (pós-1º turno)
└── simulation_2turno em produção com dados reais do confronto definido
```