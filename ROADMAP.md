# Roadmap — brazil-election-montecarlo

---

## Status por Versão

| Versão | Feature | Status |
|---|---|---|
| v2.2 | Índice de rejeição como teto eleitoral | ✅ Concluído |
| v2.3 | Agregação automática de pesquisas + outlier detection | ✅ Concluído |
| v2.4 | Categoria "Indecisos" com redistribuição proporcional | ✅ Concluído |
| v2.5 | 2º turno dinâmico baseado no top-2 real do 1º turno | ✅ Concluído |
| **v2.6** | **Simulação de votos absolutos com abstenção estocástica** | 📋 Planejado |

---

## Issues Pendentes

### Issue #6 — Simulação de Votos Absolutos com Abstenção Estocástica (v2.6)

**Motivação:**

As simulações atuais produzem apenas percentuais de intenção de voto. Converter para votos absolutos torna os resultados mais concretos e permite análises adicionais (margem em votos, total de votos válidos por candidato). O principal insumo para essa conversão é a taxa de abstenção, que não é constante e deve ser modelada como variável aleatória.

**Dados históricos utilizados como priors:**

| Eleição | Turno | Abstenção | Contexto |
|---|---|---|---|
| 2022 presidencial (Lula vs Bolsonaro) | 1º | ~20% | Alta polarização |
| 2022 presidencial (Lula vs Bolsonaro) | 2º | ~20% | Alta polarização |
| 2024 municipal | 1º | ~20% | Baixa mobilização |
| 2024 municipal | 2º | ~29% | Baixa mobilização |

**Conclusão dos dados:** A abstenção do 1º turno é estável (~20%) independente do contexto. A abstenção do 2º turno é sensível ao grau de polarização — em eleições presidenciais altamente polarizadas ela se mantém próxima do 1º turno; em eleições menos engajantes sobe ~9pp.

**Modelo proposto:**

```python
ELEITORADO = 158_600_000  # TSE 2026

# 1º turno: historicamente estável em eleições gerais
abstencao_1t = Normal(μ=0.20, σ=0.02)
# σ=0.02 → 90% dos cenários entre 16.7% e 23.3%

# 2º turno: mais incerto; bounded entre 2022 (20%) e 2024 municipal (29%)
# μ=0.22 reflete que mesmo em eleições polarizadas há variação residual
abstencao_2t = Normal(μ=0.22, σ=0.03)
# σ=0.03 → 90% dos cenários entre 17.1% e 26.9%
```

**Parâmetros via CSV (opcional):**

```csv
parametro,valor
eleitorado,158600000
abstencao_1t_media,0.20
abstencao_1t_sigma,0.02
abstencao_2t_media,0.22
abstencao_2t_sigma,0.03
```

Se o arquivo não existir, o modelo usa os defaults acima.

**Outputs adicionais:**

No 1º turno, cada simulação produz:
```
votos_validos_1t = ELEITORADO * (1 - abstencao_1t_simulada)
votos_candidato_i = votos_validos_1t * percentual_candidato_i / 100
```

No 2º turno:
```
votos_validos_2t = ELEITORADO * (1 - abstencao_2t_simulada)
votos_finalista_a = votos_validos_2t * percentual_a / 100
votos_finalista_b = votos_validos_2t * percentual_b / 100
margem_votos = |votos_finalista_a - votos_finalista_b|
```

**Novos campos no relatório:**

```
ABSOLUTE VOTE PROJECTIONS (v2.6)
  Electorate:          158,600,000
  
  First round (median scenario):
    Estimated turnout:   127,034,000  (abstention: 19.9%)
    Lula:                 52,247,000 votes  [48.2M - 56.3M 90% CI]
    Flávio Bolsonaro:     48,012,000 votes  [44.1M - 51.9M 90% CI]
    ...

  Second round (median scenario):
    Estimated turnout:   123,708,000  (abstention: 22.0%)
    Lula:                 63,924,000 votes  [59.1M - 68.7M 90% CI]
    Flávio Bolsonaro:     59,784,000 votes  [55.0M - 64.5M 90% CI]
    Margin (median):       4,140,000 votes
```

**Novo gráfico:** distribuição da margem de vitória em votos absolutos no 2º turno.

**Complexidade:** Baixa — não altera lógica de simulação, apenas escala os percentuais já existentes por uma variável aleatória adicional por simulação.

**Esforço estimado:** ~2h

**Retrocompatibilidade:** 100% — outputs percentuais existentes são mantidos; votos absolutos são adicionados como colunas extras nos CSVs de resultado.

---

### Issues Descartadas / Incorporadas

| Issue original | Decisão |
|---|---|
| #2 — Suporte para 5 candidatos | Incorporado na v2.3 (geração dinâmica de cores e estrutura N candidatos) |
| #4 — Detecção de outliers | Implementado na v2.3 como Modified Z-Score (MAD-based) |
| #7 — Relatório PDF | Sem previsão |
| #8 — Dashboard Streamlit | Sem previsão |

---

## Impacto por Feature Pendente

| Feature | Realismo | Complexidade | Esforço |
|---|---|---|---|
| Issue #6 — Votos absolutos + abstenção | Alto | Baixa | ~2h |

---

## Timeline

```
Fevereiro 2026
├── v2.2 ✅  Rejeição como teto eleitoral
├── v2.3 ✅  Agregação de pesquisas + outliers
├── v2.4 ✅  Indecisos com redistribuição proporcional
└── v2.5 ✅  2º turno dinâmico (top-2 real por simulação)
            fix: rejeição 0.0 tratada como "não medido"

Março 2026
└── v2.6 📋  Votos absolutos com abstenção estocástica
```
