<<<<<<< HEAD
# 🗺️ Roadmap — Melhorias Futuras

Este documento lista melhorias planejadas para versões futuras do projeto.

---

## 📋 Versão 2.2 (Próxima)

### 1. Agregação Automática de Múltiplas Pesquisas

**Status:** 🔴 Planejado  
**Prioridade:** Alta  
**Complexidade:** Média

**Objetivo:**  
Script que lê múltiplas pesquisas do CSV e agrega automaticamente, sem necessidade de calcular média manualmente.

**Funcionalidades:**
- Ler múltiplas linhas por candidato (uma por instituto)
- Calcular média ponderada por data (pesquisas recentes têm mais peso)
- Ajustar desvio padrão considerando discrepância entre institutos
- Detectar e avisar sobre outliers (pesquisas muito diferentes da média)

**Formato do CSV:**
```csv
candidato,intencao_voto_pct,desvio_padrao_pct,instituto,data,amostra
Lula,38.0,2.0,Datafolha,2026-02-18,2000
Lula,36.0,2.0,Quaest,2026-02-19,2500
Lula,37.0,2.0,PoderData,2026-02-20,2200
Flávio Bolsonaro,27.0,2.0,Datafolha,2026-02-18,2000
...
```

**Fórmula de ponderação temporal:**
```python
peso(dias_atrás) = exp(-dias_atrás / 7)
# Pesquisa de hoje: peso = 1.0
# Pesquisa de 7 dias atrás: peso ≈ 0.37
# Pesquisa de 14 dias atrás: peso ≈ 0.14
```

**Cálculo de desvio agregado:**
```python
σ_agregado = √(σ_médio² + σ_entre_institutos²)
# Considera tanto a margem de erro quanto a variação entre institutos
```

**Arquivo:** `src/agregar_pesquisas.py`

---

### 2. Suporte para até 5 Candidatos

**Status:** 🔴 Planejado  
**Prioridade:** Média  
**Complexidade:** Baixa

**Objetivo:**  
Permitir simulações com até 5 candidatos nomeados (além de brancos/nulos), com cores e layout ajustados automaticamente.

**Mudanças necessárias:**

**Paleta de cores expandida:**
```python
CORES = [
    "#e74c3c",  # Vermelho - Candidato 1
    "#3498db",  # Azul - Candidato 2
    "#2ecc71",  # Verde - Candidato 3
    "#f39c12",  # Laranja - Candidato 4
    "#9b59b6",  # Roxo - Candidato 5
    "#95a5a6",  # Cinza - Outros
    "#34495e",  # Cinza escuro - Brancos/Nulos
]
```

**Layout dos gráficos:**
- Ajustar automaticamente número de subplots
- Reduzir tamanho de fonte se >4 candidatos
- Usar grid 4×3 em vez de 3×4 para mais espaço vertical

**Validação:**
- Avisar se CSV tem >5 candidatos válidos
- Sugerir agregar candidatos com <5% em "Outros"

---

### 3. Categoria "Indecisos"

**Status:** 🔴 Planejado  
**Prioridade:** Média  
**Complexidade:** Média

**Objetivo:**  
Adicionar categoria "Indecisos" e modelar sua distribuição no 2º turno.

**Mudanças no 1º turno:**
```csv
candidato,intencao_voto_pct,desvio_padrao_pct,instituto,data
Lula,35.0,2.0,Datafolha,2026-02-20
Flávio Bolsonaro,29.0,2.0,Datafolha,2026-02-20
Outros,18.0,2.0,Datafolha,2026-02-20
Indecisos,8.0,2.0,Datafolha,2026-02-20
Brancos/Nulos,10.0,2.0,Datafolha,2026-02-20
```

**Tratamento:**
- No 1º turno: indecisos não votam (reduzem votos válidos)
- No 2º turno: distribuir indecisos entre candidatos e brancos/nulos

**Modelo de distribuição no 2º turno:**
```python
# Indecisos se distribuem proporcionalmente aos votos dos candidatos
# com uma componente aleatória

# Exemplo: se Lula tem 55% e Flávio 45% dos votos decididos,
# os indecisos se distribuem aproximadamente:
# - 55% × 0.8 para Lula (80% seguem a proporção)
# - 45% × 0.8 para Flávio
# - 20% para brancos/nulos (indecisos que não decidem)
```

**Arquivo:** `src/simulation_v2.3.py`

---

## 📋 Versão 2.3 (Futuro)

### 4. 2º Turno Baseado nos Mais Votados do 1º Turno

**Status:** 🔴 Planejado  
**Prioridade:** Baixa  
**Complexidade:** Baixa

**Objetivo:**  
No 2º turno, usar automaticamente os 2 candidatos mais votados do 1º turno (não os primeiros do CSV).

**Mudança:**
```python
# Antes: usa primeiros 2 do CSV
cand1, cand2 = candidatos_validos[0], candidatos_validos[1]

# Depois: usa os 2 mais votados do 1º turno
votos_medios = df1.groupby('vencedor').size().sort_values(ascending=False)
cand1, cand2 = votos_medios.index[0], votos_medios.index[1]
```

---

### 5. Detecção Automática de Outliers

**Status:** 🔴 Planejado  
**Prioridade:** Baixa  
**Complexidade:** Média

**Objetivo:**  
Detectar pesquisas muito discrepantes da média e avisar o usuário.

**Critério:**
- Se uma pesquisa está >2 desvios padrão da média → marcar como outlier
- Exibir aviso no console
- Permitir exclusão automática com flag `--remove-outliers`

**Exemplo:**
```
⚠️  OUTLIER DETECTADO:
    Instituto XYZ reporta Lula com 45% (média: 35% ± 2%)
    Diferença de +10pp está fora do intervalo esperado.
    
    Deseja excluir esta pesquisa? (s/N)
```

---

### 6. Exportação de Relatório PDF

**Status:** 🔴 Planejado  
**Prioridade:** Baixa  
**Complexidade:** Alta

**Objetivo:**  
Gerar relatório em PDF com:
- Resumo executivo
- Metodologia
- Todos os gráficos
- Tabelas de probabilidades
- Histórico de pesquisas

**Biblioteca:** `reportlab` ou `weasyprint`

**Arquivo:** `src/gerar_relatorio.py`

---

### 7. Dashboard Interativo (Streamlit)

**Status:** 🔴 Planejado  
**Prioridade:** Baixa  
**Complexidade:** Alta

**Objetivo:**  
Interface web interativa onde é possível:
- Ajustar parâmetros em tempo real
- Visualizar resultados instantaneamente
- Fazer análise de sensibilidade
- Baixar gráficos e dados

**Stack:** Streamlit + Plotly

**Arquivo:** `src/app.py`

**Comandos:**
```bash
pip install streamlit plotly
streamlit run src/app.py
```

---

## 🎯 Priorização

| Melhoria | Prioridade | Complexidade | Esforço | Versão |
|---|---|---|---|---|
| Agregação automática de pesquisas | 🔴 Alta | Média | ~4h | 2.2 |
| Suporte para 5 candidatos | 🟡 Média | Baixa | ~2h | 2.2 |
| Categoria "Indecisos" | 🟡 Média | Média | ~3h | 2.2 |
| 2º turno baseado em mais votados | 🟢 Baixa | Baixa | ~1h | 2.3 |
| Detecção de outliers | 🟢 Baixa | Média | ~3h | 2.3 |
| Relatório PDF | 🟢 Baixa | Alta | ~6h | 2.3 |
| Dashboard Streamlit | 🟢 Baixa | Alta | ~8h | 2.4 |

---

## 💡 Como Contribuir

Quer implementar alguma dessas melhorias? Siga este workflow:

1. **Escolha uma issue do roadmap**
2. **Crie uma branch:** `git checkout -b feature/nome-da-melhoria`
3. **Implemente e teste**
4. **Abra um Pull Request** referenciando este roadmap
5. **Aguarde review**

Dúvidas? Abra uma [issue no GitHub](https://github.com/seu-usuario/brazil-election-montecarlo/issues)!

---

## 📅 Histórico de Implementações

| Versão | Data | Melhorias |
|---|---|---|
| 2.1 | 2026-02-18 | Leitura de dados via CSV |
| 2.0 | 2026-02-18 | Dirichlet + Incerteza temporal |
| 1.0 | 2026-02-17 | Versão inicial com Normais |

---

**Última atualização:** 2026-02-18  
**Próxima revisão:** Quando v2.2 for lançada
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
>>>>>>> main
