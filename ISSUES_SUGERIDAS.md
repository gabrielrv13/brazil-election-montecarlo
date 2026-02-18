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

---

## Issue #5: Índice de Rejeição como Teto Eleitoral ⚠️

**Título:** `[FEATURE] Incorporar índice de rejeição como teto eleitoral`

**Labels:** `enhancement`, `methodology`, `high-priority`, `v2.2`

**Descrição:**

Implementar o índice de rejeição como limite máximo de votos que um candidato pode receber. Historicamente, **nenhum candidato à presidência do Brasil conseguiu se eleger com mais de 50% de rejeição**.

---

### Justificativa

A rejeição funciona como um "teto eleitoral" — independentemente de outros fatores, um candidato não consegue ultrapassar `(100 - rejeição)%` dos votos válidos.

**Dados históricos:**

| Ano | Candidato | Rejeição 2º Turno | Resultado |
|---|---|---|---|
| 2022 | Bolsonaro | 51% | ❌ Perdeu |
| 2022 | Lula | 49% | ✅ Venceu |
| 2018 | Bolsonaro | 46% | ✅ Venceu |
| 2014 | Dilma | 41% | ✅ Venceu |

**Padrão:** Rejeição >50% = derrota

---

### Funcionalidades

#### 1. Coleta de Dados

Adicionar coluna `rejeicao_pct` no CSV:

```csv
candidato,intencao_voto_pct,rejeicao_pct,desvio_padrao_pct,instituto,data
Lula,35.0,42.0,2.0,Datafolha,2026-02-20
Flávio Bolsonaro,29.0,48.0,2.0,Datafolha,2026-02-20
Outros,21.0,0.0,2.0,Datafolha,2026-02-20
```

#### 2. Aplicação do Teto

```python
teto_candidato = 100 - rejeicao
voto_final = min(voto_simulado, teto_candidato)
```

**Exemplo:**
- Lula: 42% rejeição → teto de **58%**
- Se simulação gera 62% → limita a 58%

#### 3. Impacto no 2º Turno

Votos de candidatos eliminados migram proporcionalmente ao **espaço disponível**:

```python
espaco_A = 100 - rejeicao_A
espaco_B = 100 - rejeicao_B

proporcao_A = espaco_A / (espaco_A + espaco_B)
```

**Lógica:** Eleitores migram para quem tem menos rejeição.

#### 4. Validações

Avisar quando rejeição >50%:

```
⚠️  ALERTA: Flávio Bolsonaro tem 53% de rejeição
    Teto eleitoral: 47% (insuficiente para vitória)
    Histórico: Nenhum presidente foi eleito com >50% de rejeição
```

---

### Implementação Técnica

**Arquivo:** `src/simulation_v2.3.py`

**Funções novas:**
- `aplicar_teto_rejeicao(votos, rejeicao)`
- `calcular_transferencia_por_rejeicao(rejeicoes)`
- `validar_viabilidade_eleitoral(candidato, rejeicao)`

**Mudanças no relatório:**
- Adicionar seção "Análise de Rejeição"
- Mostrar quantas simulações foram limitadas pelo teto
- Avisar sobre candidatos com >50% de rejeição

---

### Exemplo de Output

```
📊 ANÁLISE DE REJEIÇÃO:
  
  Lula:              42% → Teto: 58% ✓
  Flávio Bolsonaro:  48% → Teto: 52% ✓
  
  ℹ️  Nenhum candidato está acima do limite crítico de 50%.

🏆 2º TURNO (com limite de rejeição):
  Lula:   57.8%
  Flávio: 42.2%
  
  📉 Impacto da rejeição:
     Lula foi limitado em 2.1% das simulações
     Flávio foi limitado em 7.3% das simulações
```

---

### Prioridade

**🔴 ALTA** — Esta funcionalidade:

- ✅ Aumenta significativamente o realismo
- ✅ Reflete padrão histórico comprovado  
- ✅ Ajuda identificar cenários inviáveis
- ✅ Melhora previsões de 2º turno
- ✅ Fácil de explicar para público geral

**Esforço estimado:** ~4 horas  
**Versão alvo:** 2.2 ou 2.3

---

### Referências

- Datafolha: pesquisas de rejeição disponíveis publicamente
- Análise: "Por que a rejeição é mais importante que a intenção de voto" (Poder360)
- Histórico: Resultados eleições 2014-2022 (TSE)

---

### Checklist

- [ ] Adicionar coluna `rejeicao_pct` ao CSV
- [ ] Implementar função de teto eleitoral
- [ ] Ajustar transferência de votos no 2º turno
- [ ] Adicionar validações e avisos
- [ ] Atualizar documentação (ATUALIZANDO_PESQUISAS.md)
- [ ] Adicionar testes
- [ ] Atualizar visualizações

