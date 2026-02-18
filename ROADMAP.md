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
