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
| **v2.7** | **Simulação standalone do 2º turno (simulation_2turno)** | 📋 Planejado |

---

## Issues Pendentes

### Issue #9 — Simulação Standalone do 2º Turno (v2.7)

**Motivação:**

A partir de outubro de 2026, quando os dois finalistas estiverem definidos pelo resultado do 1º turno, o modelo completo (`simulation_v2.py`) passa a ser redundante: rodar 40.000 simulações de 1º turno para chegar ao 2º não faz mais sentido. O que importa nesse momento é concentrar toda a capacidade de simulação no confronto direto, com dados de pesquisas específicas de 2º turno — que têm dinâmicas distintas das pesquisas de 1º turno (transferência de votos já realizada, indecisos menores, rejeição pode mudar).

Um script dedicado, com CSV próprio e interface mais simples, é mais adequado para esse período.

**Arquivo:** `src/simulation_2turno.py`

**CSV próprio:** `data/pesquisas_2turno.csv`

---

**Formato do CSV:**

```csv
candidato,intencao_voto_pct,rejeicao_pct,desvio_padrao_pct,instituto,data
Lula,54.0,42.0,2.0,Datafolha,2026-10-08
Lula,53.0,43.0,2.0,Quaest,2026-10-09
Lula,55.0,41.0,2.0,PoderData,2026-10-10
Flávio Bolsonaro,46.0,48.0,2.0,Datafolha,2026-10-08
Flávio Bolsonaro,47.0,47.0,2.0,Quaest,2026-10-09
Flávio Bolsonaro,45.0,49.0,2.0,PoderData,2026-10-10
```

Diferenças em relação ao `pesquisas.csv` do modelo completo:
- Apenas dois candidatos (sem "Outros", "Brancos/Nulos" — esses são tratados internamente)
- Sem coluna `indecisos_pct` (os indecisos do 2º turno já estão implícitos na diferença entre os dois candidatos para 100%)
- Agregação temporal e detecção de outliers herdadas de `carregar_pesquisas()` via import

---

**Lógica do modelo:**

No 2º turno as pesquisas já são declaradas em termos de voto válido entre os dois finalistas. A soma `A + B` não é necessariamente 100% — a diferença representa indecisos e brancos/nulos residuais. O modelo deve:

1. Ler e agregar as pesquisas (reutilizando `agregar_pesquisas_candidato` de `simulation_v2`)
2. Calcular o espaço residual: `residual = 100 - (voto_A + voto_B)`
3. Distribuir o residual entre os candidatos proporcionalmente ao espaço eleitoral disponível (mesma lógica da `distribuir_indecisos` do v2.4, sem coluna `indecisos_pct` — o residual é calculado automaticamente)
4. Aplicar teto eleitoral por rejeição
5. Simular 40.000 confrontos diretos com Dirichlet de 3 categorias: `[A, B, brancos_nulos]`
6. Projetar votos absolutos com `abstencao_2t ~ Normal(0.22, 0.03)`

```python
# Dirichlet de 3 categorias para o confronto direto
alphas = [voto_A_ajustado, voto_B_ajustado, residual_final] * fator_concentracao
proporcoes = np.random.dirichlet(alphas, size=N_SIM)

votos_A = proporcoes[:, 0] / (proporcoes[:, 0] + proporcoes[:, 1]) * 100
votos_B = proporcoes[:, 1] / (proporcoes[:, 0] + proporcoes[:, 1]) * 100
```

---

**Outputs:**

```
outputs/
├── resultados_2turno_standalone.csv   # 40.000 linhas: voto_A, voto_B, vencedor, diferenca,
│                                      #   abstencao_pct, votos_validos, votos_A_abs, votos_B_abs,
│                                      #   margem_votos
└── simulacao_2turno.png               # Visualização dedicada (ver abaixo)
```

---

**Visualização:**

Um único painel compacto com três elementos:

- **Semicírculo** (reutilizado de `graficos()` do v2.5): distribuição de cenários por margem — folgado / apertado / foto-finish.
- **Distribuição de votos válidos** para cada candidato: histograma sobreposto ou violin plot mostrando toda a distribuição de `voto_A` e `voto_B` nas 40.000 simulações.
- **Distribuição da margem em votos absolutos**: histograma de `margem_votos` com linha de mediana e IC 90%.

---

**Reutilização de código:**

`simulation_2turno.py` importa diretamente de `simulation_v2`:

```python
from simulation_v2 import (
    agregar_pesquisas_candidato,
    calcular_peso_temporal,
    detectar_outliers,
    aplicar_teto_rejeicao,
    gerar_cores,
    _hex_lighten,
    ELEITORADO,
    ABSTENCAO_2T_MU,
    ABSTENCAO_2T_SIGMA,
    N_SIM,
)
```

Isso garante que qualquer correção futura em `agregar_pesquisas_candidato` ou nas constantes de eleitorado se propague automaticamente para o script de 2º turno.

---

**Complexidade:** Baixa-média — a lógica de simulação é mais simples que o modelo completo (sem 1º turno, sem top-2 dinâmico), mas exige cuidado com a distribuição do residual e a normalização do Dirichlet de 3 categorias.

**Esforço estimado:** ~3h

**Retrocompatibilidade:** N/A — arquivo novo, não altera `simulation_v2.py`.

**Dependência:** Pode ser desenvolvido independentemente do v2.6; não tem pré-requisito de versão.

---

### Issues Descartadas / Incorporadas

| Issue original | Decisão |
|---|---|
| #2 — Suporte para 5 candidatos | Incorporado na v2.3 (geração dinâmica de cores e estrutura N candidatos) |
| #4 — Detecção de outliers | Implementado na v2.3 como Modified Z-Score (MAD-based) |
| #7 — Relatório PDF | Implementado na v2.6 via `gerar_relatorio_pdf()` |
| #8 — Dashboard Streamlit | Implementado na v2.6 em `src/dashboard.py` |

---

## Impacto por Feature Pendente

| Feature | Realismo | Complexidade | Esforço |
|---|---|---|---|
| Issue #9 — Simulação standalone 2º turno | Alto | Baixa-média | ~3h |

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
├── v2.6 ✅  Votos absolutos + PDF + Dashboard Streamlit
└── v2.7 📋  simulation_2turno — simulação standalone do 2º turno
            CSV próprio · Dirichlet 3 categorias · reutiliza simulation_v2

Outubro 2026 (pós-1º turno)
└── simulation_2turno em produção com dados reais do confronto definido
```
