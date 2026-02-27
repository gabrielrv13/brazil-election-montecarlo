# Changelog — Versão 2.0

## O que mudou

### 1. **Distribuição Dirichlet** (em vez de Normais independentes)

**Antes (v1):**
```python
voto_lula = np.random.normal(35, 2)
voto_flavio = np.random.normal(29, 2)
# ... normaliza depois
```

**Agora (v2):**
```python
proporcoes = np.random.dirichlet([35, 29, 21, 15])
# Já garante que soma = 100%
```

**Por que é melhor:**
- ✅ Garante matematicamente que os votos sempre somam exatamente 100%
- ✅ Respeita a constraint natural de uma eleição (simplex)
- ✅ Mesma metodologia usada no modelo húngaro que nos inspirou

---

### 2. **Incerteza Temporal** (efeito "funil")

**Antes (v1):**
```python
DESVIO = 2.0  # sempre fixo
```

**Agora (v2):**
```python
dias_restantes = (DATA_ELEICAO - DATA_ATUAL).days
DESVIO = DESVIO_BASE × √(dias_restantes / 30)
```

**Exemplo prático:**
| Distância da eleição | Desvio padrão |
|---|---|
| 240 dias (8 meses) | 5.66% |
| 120 dias (4 meses) | 4.00% |
| 30 dias (1 mês) | 2.00% |
| 7 dias (1 semana) | 0.96% |

**Por que é melhor:**
- ✅ Reflete a realidade: quanto mais longe a eleição, maior a incerteza
- ✅ Previsões para o futuro distante são naturalmente mais conservadoras
- ✅ À medida que a eleição se aproxima, as estimativas convergem

---

## Compatibilidade

Os outputs são compatíveis:
- ✅ Mesmo formato de CSV
- ✅ Mesmas colunas e estrutura
- ✅ Gráfico com layout idêntico

**Diferenças nos nomes de arquivo:**
- `resultados_1turno_v2.csv` (antes: `resultados_1turno.csv`)
- `resultados_2turno_v2.csv` (antes: `resultados_2turno.csv`)
- `simulacao_eleicoes_brasil_2026_v2.png` (antes: `simulacao_eleicoes_brasil_2026.png`)

---

## Como usar

Execute a v2:
```bash
python src/simulation_v2.py
```

A v1 continua disponível:
```bash
python src/simulation.py
```

---

## Resultados esperados

Os resultados da v2 serão **ligeiramente diferentes** da v1 devido a:
1. Dirichlet produz distribuições mais realistas
2. Incerteza temporal maior (eleição ainda está longe)

**Espere:**
- Intervalos de confiança mais largos
- Probabilidades menos "certeiras"
- Mais cenários de disputa apertada no 2º turno

Isso é **honesto estatisticamente** — estamos 8 meses antes da eleição!

---

## Créditos

Metodologia inspirada no modelo **Chronicler-v2** (Krónikás-v2) desenvolvido por Viktor Tisza para as eleições húngaras de 2026.

📎 [Metodologia original](https://www.szazkilencvenkilenc.hu/methodology-v2/)

---

## Versão 2.1 — Leitura automática do CSV

### 3. **Dados via CSV** (novo!)

**Antes (v2.0):**
```python
VOTOS_MEDIA = np.array([35.0, 29.0, 21.0, 15.0])
DESVIO = 2.0
# Valores fixos no código
```

**Agora (v2.1):**
```python
CANDIDATOS, VOTOS_MEDIA, DESVIO_BASE = carregar_pesquisas()
# Lê automaticamente de data/pesquisas.csv
```

**Por que é melhor:**
- ✅ Atualizar pesquisas = só editar o CSV, não precisa mexer no código Python
- ✅ Mais fácil manter histórico de pesquisas
- ✅ Facilita colaboração (outras pessoas podem atualizar sem saber programar)
- ✅ Dados separados da lógica do modelo

**Como usar:**
1. Edite `data/pesquisas.csv` com os novos valores
2. Rode `python src/simulation_v2.py`
3. Pronto!

📖 Veja o guia completo em [ATUALIZANDO_PESQUISAS.md](ATUALIZANDO_PESQUISAS.md)

