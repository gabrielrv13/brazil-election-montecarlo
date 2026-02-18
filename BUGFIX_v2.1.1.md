# 🐛 BUGFIX v2.1.1

## Problema Identificado

A versão 2.1 tinha um **bug crítico** que causava resultados incorretos nas simulações:

### Sintoma
- "Outros" aparecia com ~99% de probabilidade de vitória
- Resultados não faziam sentido com os dados de entrada

### Causa Raiz

O código estava **ordenando alfabeticamente** os candidatos após carregar do CSV:

```python
# ❌ CÓDIGO COM BUG (v2.1)
df = df.sort_values("candidato").reset_index(drop=True)
```

**Problema:**  
Se o CSV tinha esta ordem:
1. Lula (35%)
2. Flávio Bolsonaro (29%)
3. Outros (21%)
4. Brancos/Nulos (15%)

Após ordenar alfabeticamente ficava:
1. **Brancos/Nulos** (15%) ← índice 0
2. **Flávio Bolsonaro** (29%) ← índice 1
3. **Lula** (35%) ← índice 2
4. **Outros** (21%) ← índice 3

Depois, ao calcular votos válidos, o código fazia:

```python
# ❌ Pegava os primeiros 3 índices
validos = votos_norm[:, :3]  # índices 0, 1, 2
```

Isso **incluía Brancos/Nulos erradamente** e **excluía Outros**!

Na hora de identificar o vencedor:
```python
# ❌ Procurava entre os 3 primeiros do CSV ordenado
candidatos_validos = ['Brancos/Nulos', 'Flávio Bolsonaro', 'Lula']
```

Como "Outros" tinha 21% mas não estava na lista de válidos, o código não conseguia identificá-lo corretamente.

---

## Correção Aplicada (v2.1.1)

### 1. Não ordenar alfabeticamente

```python
# ✅ CÓDIGO CORRETO (v2.1.1)
# Mantém ordem original do CSV
candidatos = df["candidato"].tolist()
```

### 2. Identificar índices válidos dinamicamente

```python
# ✅ Identifica índices de candidatos válidos (não brancos/nulos)
indices_validos = [i for i, c in enumerate(CANDIDATOS) 
                  if "Brancos" not in c and "Nulos" not in c]

# ✅ Usa esses índices para extrair votos válidos
validos = votos_norm[:, indices_validos]
```

### 3. Mapear vencedor corretamente

```python
# ✅ Identifica vencedor entre candidatos válidos
idx_vencedor_local = np.argmax(validos, axis=1)
vencedores = np.array(candidatos_validos)[idx_vencedor_local]
```

---

## Verificação

Após a correção, com os dados:
- Lula: 35%
- Flávio: 29%
- Outros: 21%
- Brancos: 15%

**Resultado esperado:**
- Lula vence em ~75-85% das simulações
- Flávio vence em ~15-20% das simulações
- Outros vence em ~1-3% das simulações

---

## Arquivos Alterados

- ✅ `src/simulation_v2.py` — Corrigido
- ✅ `src/simulation_v2_buggy.py` — Backup da versão com bug (para referência)

---

## Como Testar

```bash
python src/simulation_v2.py
```

Verifique no relatório:
```
🏆 Prob. vitória 1º turno:
  Lula                   : 75-85%  ✓
  Flávio Bolsonaro       : 15-20%  ✓
  Outros                 : 1-3%    ✓
```

Se "Outros" aparecer com >50%, **ainda tem bug**.

---

## Lição Aprendida

❌ **NÃO** assumir ordem alfabética quando a ordem importa  
✅ **SIM** manter ordem original do CSV  
✅ **SIM** usar índices explícitos em vez de faixas fixas  
✅ **SIM** adicionar logs de debug para verificar ordem

---

## Agradecimento

Bug reportado por: **@gabrielrv13**  
Data: 2026-02-18  
Versão corrigida: **v2.1.1**

---

**Status:** ✅ CORRIGIDO

---

## Correção Adicional — Gráficos Completos

### Problema #2

Na primeira correção do bug, simplifiquei demais a função de gráficos e **removi vários gráficos importantes**:

❌ Faltavam:
- Posterior Bayesiano dos candidatos
- Votos válidos de cada candidato
- Probabilidade de vitória no 1º e 2º turno
- Distribuições do 2º turno

### Solução

Restaurei **todos os 11 gráficos** originais:

1. ✅ Distribuição de votos — 1º turno
2. ✅ Probabilidade de vitória — 1º turno (barras horizontais)
3. ✅ Posterior Bayesiano — Candidato 1
4. ✅ Votos válidos — Candidato 1
5. ✅ Votos válidos — Candidato 2
6. ✅ Probabilidade de 2º turno (pizza)
7. ✅ Posterior Bayesiano — Candidato 2
8. ✅ Distribuição 2º turno — Candidato 1
9. ✅ Distribuição 2º turno — Candidato 2
10. ✅ Probabilidade de vitória — 2º turno (barras)
11. ✅ Posterior Bayesiano — Outros

---

## Status Final

**Versão:** v2.1.1 (Completa)  
**Bugs corrigidos:**
- ✅ Ordenação alfabética causando cálculo errado
- ✅ Gráficos faltantes restaurados

**Data:** 2026-02-18  
**Testado:** ✅
