# 📝 Issues Sugeridas para o GitHub

Cole esses textos diretamente como issues no GitHub para organizar o trabalho futuro.

---

## Issue #1: Agregação Automática de Múltiplas Pesquisas

**Título:** `[FEATURE] Agregação automática de múltiplas pesquisas com média ponderada`

**Labels:** `enhancement`, `v2.2`

**Descrição:**

Criar script que leia múltiplas pesquisas do CSV e agregue automaticamente, sem necessidade de calcular média manualmente.

**Funcionalidades:**
- Ler múltiplas linhas por candidato (uma por instituto)
- Calcular média ponderada por data (pesquisas recentes têm mais peso)
- Ajustar desvio padrão considerando discrepância entre institutos
- Detectar e avisar sobre outliers

**Formato do CSV:**
```csv
candidato,intencao_voto_pct,desvio_padrao_pct,instituto,data,amostra
Lula,38.0,2.0,Datafolha,2026-02-18,2000
Lula,36.0,2.0,Quaest,2026-02-19,2500
Lula,37.0,2.0,PoderData,2026-02-20,2200
```

**Fórmula proposta:**
```
peso(dias_atrás) = exp(-dias_atrás / 7)
σ_agregado = √(σ_médio² + σ_entre_institutos²)
```

**Arquivo:** `src/agregar_pesquisas.py`

**Prioridade:** Alta  
**Esforço estimado:** ~4 horas

**Referências:**
- Ver ROADMAP.md seção 2.2.1

---

## Issue #2: Suporte para até 5 Candidatos nos Gráficos

**Título:** `[FEATURE] Expandir paleta de cores para até 5 candidatos`

**Labels:** `enhancement`, `visualization`, `v2.2`

**Descrição:**

Permitir simulações com até 5 candidatos nomeados, com cores e layout ajustados automaticamente.

**Mudanças necessárias:**
1. Expandir paleta de cores:
```python
CORES = [
    "#e74c3c",  # Vermelho
    "#3498db",  # Azul
    "#2ecc71",  # Verde
    "#f39c12",  # Laranja
    "#9b59b6",  # Roxo
    "#95a5a6",  # Cinza - Outros
    "#34495e",  # Cinza escuro - Brancos/Nulos
]
```

2. Ajustar layout dos gráficos para acomodar mais candidatos
3. Reduzir tamanho de fonte automaticamente se >4 candidatos
4. Adicionar validação: avisar se CSV tem >5 candidatos válidos

**Prioridade:** Média  
**Esforço estimado:** ~2 horas

**Referências:**
- Ver ROADMAP.md seção 2.2.2

---

## Issue #3: Adicionar Categoria "Indecisos"

**Título:** `[FEATURE] Adicionar categoria "Indecisos" e modelar distribuição no 2º turno`

**Labels:** `enhancement`, `methodology`, `v2.2`

**Descrição:**

Adicionar categoria "Indecisos" e modelar sua distribuição no 2º turno de forma estatisticamente rigorosa.

**Tratamento proposto:**

**No 1º turno:**
- Indecisos não votam (reduzem votos válidos)
- Não entram no cálculo de vencedor

**No 2º turno:**
- Distribuir indecisos entre candidatos e brancos/nulos
- Usar modelo probabilístico:
  - 80% dos indecisos seguem proporção dos votos decididos
  - 20% viram brancos/nulos

**Exemplo de CSV:**
```csv
candidato,intencao_voto_pct,desvio_padrao_pct,instituto,data
Lula,35.0,2.0,Datafolha,2026-02-20
Flávio Bolsonaro,29.0,2.0,Datafolha,2026-02-20
Outros,18.0,2.0,Datafolha,2026-02-20
Indecisos,8.0,2.0,Datafolha,2026-02-20
Brancos/Nulos,10.0,2.0,Datafolha,2026-02-20
```

**Prioridade:** Média  
**Esforço estimado:** ~3 horas

**Referências:**
- Ver ROADMAP.md seção 2.2.3

---

## Issue #4: 2º Turno Baseado nos Mais Votados

**Título:** `[ENHANCEMENT] 2º turno deve usar os 2 mais votados do 1º turno`

**Labels:** `enhancement`, `v2.3`

**Descrição:**

Atualmente o 2º turno usa os 2 primeiros candidatos do CSV (ordem alfabética). Deve usar os 2 mais votados do 1º turno.

**Mudança:**
```python
# Antes: usa primeiros 2 do CSV
cand1, cand2 = candidatos_validos[0], candidatos_validos[1]

# Depois: usa os 2 mais votados do 1º turno
votos_medios = df1[candidatos_validos].mean()
top2 = votos_medios.nlargest(2).index.tolist()
cand1, cand2 = top2[0], top2[1]
```

**Prioridade:** Baixa  
**Esforço estimado:** ~1 hora

**Referências:**
- Ver ROADMAP.md seção 2.3.4

---

## Como usar essas issues

1. Vá para: `https://github.com/seu-usuario/brazil-election-montecarlo/issues/new`
2. Copie e cole o conteúdo de cada issue acima
3. Adicione as labels sugeridas
4. Clique em "Submit new issue"

Ou crie todas de uma vez usando a API do GitHub (avançado).
