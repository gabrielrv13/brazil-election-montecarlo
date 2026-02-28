
# 🗺️ Roadmap — Melhorias Futuras (Atualizado)

Este documento lista melhorias planejadas para versões futuras do projeto.

---

## 🎯 Priorização Atualizada

| # | Melhoria | Prioridade | Complexidade | Esforço | Versão |
|---|---|---|---|---|---|
| **5** | **Índice de rejeição como teto eleitoral** | 🔴 **ALTA** | Média | ~4h | **2.2** |
| 1 | Agregação automática de pesquisas | 🔴 Alta | Média | ~4h | 2.2 |
| 3 | Categoria "Indecisos" | 🟡 Média | Média | ~3h | 2.2 |
| 2 | Suporte para 5 candidatos | 🟡 Média | Baixa | ~2h | 2.2 |
| 4 | 2º turno baseado em mais votados | 🟢 Baixa | Baixa | ~1h | 2.3 |
| 6 | Detecção de outliers | 🟢 Baixa | Média | ~3h | 2.3 |
| 7 | Relatório PDF | 🟢 Baixa | Alta | ~6h | 2.3 |
| 8 | Dashboard Streamlit | 🟢 Baixa | Alta | ~8h | 2.4 |

**Total v2.2:** ~13 horas (4 funcionalidades prioritárias)  
**Total v2.3:** ~10 horas (3 funcionalidades secundárias)  
**Total v2.4:** ~8 horas (1 funcionalidade avançada)

---

## 📋 Versão 2.2 (Próxima Release — Prioridade)

### ⚠️ Funcionalidade #1: Índice de Rejeição (NOVA — Prioridade Máxima)

**Por que é prioridade máxima:**
- Historicamente comprovado: >50% rejeição = derrota
- Aumenta drasticamente o realismo das simulações
- Fácil de implementar e explicar
- Impacto alto nas previsões de 2º turno

Ver seção completa no ROADMAP.md (final do arquivo).

---

### Funcionalidade #2: Agregação de Múltiplas Pesquisas

**Por que é importante:**
- Evita trabalho manual de calcular médias
- Estatisticamente mais rigoroso
- Considera discrepância entre institutos

Ver detalhes no ROADMAP.md seção 2.2.1

---

### Funcionalidade #3: Categoria "Indecisos"

**Por que é importante:**
- Presente em todas as pesquisas reais
- Impacta distribuição no 2º turno
- Mais honesto estatisticamente

Ver detalhes no ROADMAP.md seção 2.2.3

---

### Funcionalidade #4: Suporte para 5 Candidatos

**Por que é importante:**
- Flexibilidade para eleições com mais candidatos
- Fácil de implementar (só expandir cores)

Ver detalhes no ROADMAP.md seção 2.2.2

---

## 📊 Impacto Estimado por Funcionalidade

| Funcionalidade | Realismo | Complexidade | ROI |
|---|---|---|---|
| **Rejeição** | 🔴🔴🔴🔴🔴 | 🟡🟡🟡 | **Altíssimo** |
| Agregação de pesquisas | 🔴🔴🔴🔴 | 🟡🟡🟡 | Alto |
| Indecisos | 🔴🔴🔴 | 🟡🟡🟡 | Médio |
| 5 candidatos | 🔴🔴 | 🟢 | Médio |
| 2º turno inteligente | 🔴 | 🟢 | Baixo |

**Legenda:**
- 🔴 = Impacto no realismo
- 🟡 = Complexidade técnica
- 🟢 = Fácil de implementar

---

## 🚀 Ordem de Implementação Recomendada

### Sprint 1 (v2.2 — ~6-8 horas)
1. ✅ **Rejeição** (~4h) — CRÍTICO
2. ✅ **5 candidatos** (~2h) — Rápido e útil

### Sprint 2 (v2.2 — ~7 horas)
3. ✅ **Agregação de pesquisas** (~4h) — Importante
4. ✅ **Indecisos** (~3h) — Complementa rejeição

### Sprint 3 (v2.3 — conforme necessidade)
5. Funcionalidades secundárias

---

## 💡 Por que Rejeição é Prioridade #1?

1. **Histórico irrefutável:**
   - 2022: Bolsonaro 51% rejeição → perdeu
   - 2022: Lula 49% rejeição → venceu
   - Padrão consistente desde redemocratização

2. **Impacto nas simulações:**
   - Sem rejeição: superestima candidatos rejeitados
   - Com rejeição: reflete realidade do eleitorado

3. **Facilidade de implementação:**
   - 1 coluna no CSV
   - 1 função de teto
   - Ajuste na transferência de votos
   - ~4 horas de trabalho

4. **Facilidade de comunicação:**
   - Público geral entende facilmente
   - Jornalistas podem explicar
   - Resultados mais críveis

---

## 📅 Timeline Proposto

```
Fevereiro 2026
├── v2.1 ✅ CONCLUÍDO (CSV + Dirichlet + Temporal)
│
Março 2026
├── v2.2 🔄 EM DESENVOLVIMENTO
│   ├── Sprint 1: Rejeição + 5 candidatos
│   └── Sprint 2: Agregação + Indecisos
│
Abril 2026
├── v2.3 📋 PLANEJADO
│   └── Melhorias secundárias
│
Maio-Setembro 2026
├── v2.4 💭 FUTURO
│   └── Dashboard interativo (se houver demanda)
```

---

## ✅ Checklist v2.2

- [ ] Issue #5: Implementar rejeição
- [ ] Issue #2: Expandir para 5 candidatos
- [ ] Issue #1: Agregação de pesquisas
- [ ] Issue #3: Categoria indecisos
- [ ] Atualizar documentação
- [ ] Criar testes automatizados
- [ ] Release v2.2

---

**Próxima ação:** Implementar Issue #5 (Rejeição) 🎯
=======
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
