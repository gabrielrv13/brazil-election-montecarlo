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

### Issue #10 — First-Round Margin Distribution (v2.8)

**Motivação:**

Mercados da Polymarket como "Lula vence 1T com margem >15pp" requerem
`P(margin_1T > threshold)` como output direto do modelo. A margem entre 1º e
2º colocado já está implícita em cada simulação mas nunca é surfaceada como
métrica. Esta issue a formaliza.

**Arquivos modificados:** `src/simulation_v2.py`, `src/dashboard.py`

**Implementação — `simular_primeiro_turno()`:**
```python
sorted_votes = np.sort(validos_final, axis=1)[:, ::-1]
margin_1t    = sorted_votes[:, 0] - sorted_votes[:, 1]   # sempre positivo
df1["margem_1t"] = margin_1t
df1["lider_1t"]  = [candidatos_validos[np.argmax(row)] for row in validos_final]

# Margem signed por candidato (positivo = liderando):
for i, cand in enumerate(candidatos_validos):
    others_max = np.max(np.delete(validos_final, i, axis=1), axis=1)
    df1[f"margem_{cand}"] = validos_final[:, i] - others_max
```

**Constante de configuração (adicionar ao bloco CONFIG):**
```python
MARGIN_THRESHOLDS = [5, 10, 15, 20, 25]  # pp — P(margin > X) reportado para cada
```

**Adição ao `relatorio()`:**
```
FIRST-ROUND MARGIN ANALYSIS
  Median margin (1st vs 2nd):  X.Xpp   90% CI: [X.X – X.X]
  Close race  (<3pp):          X.X% of simulations
  Comfortable (>10pp):         X.X% of simulations

  Threshold probabilities:
    P(margin >  5pp):  XX.X%
    P(margin > 10pp):  XX.X%
    P(margin > 15pp):  XX.X%   ← Polymarket market
    P(margin > 20pp):  XX.X%
    P(margin > 25pp):  XX.X%
```

**Nova função `polymarket_edge()`:**
```python
def polymarket_edge(df1: pd.DataFrame, threshold: float,
                    market_prob: float) -> dict:
    """
    Computes edge between model and Polymarket for a margin threshold market.

    Args:
        df1:          First-round simulation results DataFrame.
        threshold:    Margin threshold in percentage points (e.g., 15.0).
        market_prob:  Polymarket implied probability as a decimal (e.g., 0.55).

    Returns:
        dict with model_prob, market_prob, edge, kelly_fraction.
    """
    model_prob = float((df1["margem_1t"] > threshold).mean())
    edge       = model_prob - market_prob
    b          = (1.0 / market_prob) - 1.0
    kelly      = (b * model_prob - (1.0 - model_prob)) / b
    return {
        "threshold_pp":   threshold,
        "model_prob":     round(model_prob, 4),
        "market_prob":    market_prob,
        "edge":           round(edge, 4),
        "kelly_fraction": round(max(kelly, 0.0), 4),
    }
```

**Flag `--n-sim`:**

O default `N_SIM = 40_000` é adequado para probabilidades centrais (p ≈ 30–70%),
onde o erro Monte Carlo é ±0.25pp — irrelevante frente à incerteza do modelo.
Para mercados de threshold com p < 5%, rodar com N elevado antes de tomar posição:
```bash
python src/simulation_v2.py --n-sim 200000
```

Isso reduz o erro Monte Carlo de ±0.25pp para ±0.11pp. O default não muda;
a flag cobre o caso de uso de cauda sem impactar o runtime normal.

**Regra prática:** se `polymarket_edge()` retornar `model_prob < 0.05`,
rerodare com `--n-sim 200000` antes de considerar o edge acionável.

**Complexidade:** Baixa — a margem já está implícita nos arrays existentes.  
**Esforço estimado:** ~2h  
**Retrocompatibilidade:** Aditiva. `df1` ganha novas colunas; nenhum consumer existente quebra.

---

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