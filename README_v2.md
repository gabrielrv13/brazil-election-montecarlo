# 🆕 Versão 2.0 — Guia Rápido

## O que mudou

Esta versão implementa **duas melhorias metodológicas** inspiradas no modelo húngaro [Chronicler-v2](https://www.szazkilencvenkilenc.hu/methodology-v2/):

### 1️⃣ Distribuição Dirichlet
Garante matematicamente que os votos sempre somem 100%, respeitando a constraint natural de uma eleição.

### 2️⃣ Incerteza Temporal
O desvio padrão aumenta conforme a distância da eleição. Quanto mais longe o dia da votação, maior a incerteza — refletindo a realidade de previsões eleitorais.

---

## Como testar

### Opção A — Rodar só a v2
```bash
cd C:\Users\Usuário\Desktop\brazil-election-montecarlo
venv\Scripts\activate
python src/simulation_v2.py
```

### Opção B — Comparar v1 vs v2
```bash
python src/comparar_v1_v2.py
```
Este script roda as duas versões e mostra uma tabela comparando os resultados lado a lado.

---

## Diferenças esperadas nos resultados

| Métrica | v1 | v2 |
|---|---|---|
| Desvio padrão | Fixo 2% | ~5.66% (hoje está 8 meses antes) |
| Intervalos de confiança | Mais estreitos | Mais largos |
| Probabilidades | Mais "certeiras" | Mais conservadoras |

**Isso não é um bug** — a v2 é mais **honesta estatisticamente**. Estamos muito longe da eleição, então é natural que a incerteza seja maior!

---

## Arquivos gerados

### v1 (original)
- `outputs/simulacao_eleicoes_brasil_2026.png`
- `outputs/resultados_1turno.csv`
- `outputs/resultados_2turno.csv`

### v2 (nova)
- `outputs/simulacao_eleicoes_brasil_2026_v2.png`
- `outputs/resultados_1turno_v2.csv`
- `outputs/resultados_2turno_v2.csv`

---

## Exemplo de saída

```
📅 Dias até a eleição: 228
📊 Desvio padrão ajustado: 5.51% (base: 2.0%)

[1/4] Construindo modelo Bayesiano com PyMC (Dirichlet)...
[2/4] Simulando 1º turno (40.000 iterações) — Dirichlet...
[3/4] Simulando 2º turno (Lula vs Flávio) — Dirichlet...
[4/4] Gerando visualizações...

✅ Concluído!
```

À medida que o tempo passa e a eleição se aproxima, rode o script novamente — o desvio vai diminuir automaticamente!

---

## Preciso atualizar o GitHub?

Sim! Depois de testar localmente:

```powershell
deactivate
git add .
git commit -m "feat: add v2 with Dirichlet distribution and temporal uncertainty"
git push
```

---

## Dúvidas?

Leia o [CHANGELOG_v2.md](CHANGELOG_v2.md) para detalhes técnicos completos sobre as mudanças.
