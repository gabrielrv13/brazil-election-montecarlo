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
| v2.7 | Simulação standalone do 2º turno (simulation_2turno) | 📋 Planejado |
| **v2.8** | **First-round margin distribution + polymarket_edge() + --n-sim** | 📋 Planejado |
| **v2.9** | **Backtesting module (2018/2022)** | 📋 Planejado |

---

## Issues Pendentes

### Issue #11 — Backtesting Module (v2.9)

**Motivação:**

Pré-requisito para uso do modelo como signal source na Polymarket. Sem calibração
histórica demonstrada (2018/2022), não é possível distinguir edge real de ruído
do modelo. Promovido de v3.3.0 para v2.9 por prioridade operacional.

**Arquivo:** `src/backtesting.py`  
**Dados:** `data/historico/`

**Ground truth:**

| Eleição | Candidato | 1T | 2T |
|---------|-----------|-----|-----|
| 2022 | Lula | 48.43% | 50.90% |
| 2022 | Bolsonaro | 43.20% | 49.10% |
| 2022 | Margem 1T | 5.23pp | — |
| 2022 | Margem 2T | — | 1.80pp |
| 2018 | Bolsonaro | 46.03% | 55.13% |
| 2018 | Haddad | 29.28% | 44.87% |
| 2018 | Margem 1T | 16.75pp | — |
| 2018 | Margem 2T | — | 10.26pp |

**Snapshots a coletar (mínimo por eleição):**

| Snapshot | T−90 | T−60 | T−30 | T−14 | T−7 |
|----------|------|------|------|------|-----|
| 2022 — min. polls/candidato | 3 | 4 | 5 | 5 | 3 |
| 2018 — min. polls/candidato | — | — | 4 | 4 | 3 |

Fontes: Datafolha, Quaest, Ipec (2022), PoderData, Paraná Pesquisas.  
Para 2018: usar apenas pesquisas com Haddad explícito (pós-11 set).

**Estrutura de arquivos:**
```
data/historico/
├── 2022_1t_T-90.csv
├── 2022_1t_T-60.csv
├── 2022_1t_T-30.csv
├── 2022_1t_T-14.csv
├── 2022_1t_T-7.csv
├── 2018_1t_T-30.csv
├── 2018_1t_T-14.csv
└── 2018_1t_T-7.csv
```

**Métricas por snapshot:**

| Métrica | Fórmula | Interpretação |
|---------|---------|---------------|
| Vote share RMSE | `sqrt(mean((pred_i - actual_i)^2))` | Menor = melhor |
| Winner correct | modelo atribuiu >50% ao vencedor real? | Booleano |
| Brier score | `(p_winner - 1)^2` | Menor = melhor |
| Margin error | `\|pred_margin − actual_margin\|` | pp de erro na margem |
| Runoff prediction | modelo acertou o par finalista? | Booleano |

**Alerta — Shy Bolsonaro Effect (2022):**

Em 2022 todos os institutos subestimaram Bolsonaro em 6–8pp (Datafolha mostrava 36%;
resultado: 43.2%). Este é viés sistemático por desejabilidade social, não erro aleatório.
O modelo herda esse viés das pesquisas que ingere. O backtesting vai quantificá-lo.

Implicação para Polymarket: se o modelo historicamente superestima o candidato
líder e subestima o segundo colocado, qualquer edge calculado a favor de
"candidato líder vence por margem ampla" deve ser descontado proporcionalmente.

**Esforço estimado:** ~9h total (coleta de dados: ~5h, implementação: ~3h, análise: ~1h)

---

## Issues Descartadas / Incorporadas

| Issue original | Decisão |
|---|---|
| #2 — Suporte para 5 candidatos | Incorporado na v2.3 (geração dinâmica de cores e estrutura N candidatos) |
| #4 — Detecção de outliers | Implementado na v2.3 como Modified Z-Score (MAD-based) |
| #7 — Relatório PDF | Implementado na v2.6 via `gerar_relatorio_pdf()` |
| #8 — Dashboard Streamlit | Implementado na v2.6 em `src/dashboard.py` |

---

## Impacto por Feature Pendente

| Feature | Prioridade operacional | Complexidade | Esforço |
|---|---|---|---|
| Issue #9 — Simulação standalone 2º turno | Alta | Baixa-média | ~3h |
| Issue #10 — Margin distribution + polymarket_edge() | Alta | Baixa | ~2h |
| Issue #11 — Backtesting module | Crítica (pré-requisito Polymarket) | Média | ~9h |

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
├── v2.7 📋  simulation_2turno standalone
│            CSV próprio · Dirichlet 3 categorias · reutiliza simulation_v2
├── v2.8 📋  First-round margin distribution + polymarket_edge() + --n-sim flag
│            Habilita P(margin > X) para mercados Polymarket de threshold
└── v2.9 📋  Backtesting module (promovido de v3.3.0)
             2018/2022 · Brier score · shy Bolsonaro quantification
             Pré-requisito para uso operacional na Polymarket

Abril 2026
└── v3.0.0  Historical tracker + SimulationConfig refactor + clean filenames

Outubro 2026 (pós-1º turno)
└── simulation_2turno em produção com dados reais do confronto definido
```