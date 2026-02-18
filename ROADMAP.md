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
