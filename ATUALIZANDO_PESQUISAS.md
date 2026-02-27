# 📝 Como Atualizar as Pesquisas

A versão 2.0 do modelo lê os dados automaticamente do arquivo `data/pesquisas.csv`. 

Isso significa que **você não precisa editar código Python** para atualizar as intenções de voto — basta editar o CSV!

---

## Formato do arquivo

O arquivo `data/pesquisas.csv` tem este formato:

```csv
candidato,intencao_voto_pct,desvio_padrao_pct,fonte,data
Lula,35.0,2.0,Estimativa agregada,2026-02-17
Flávio Bolsonaro,29.0,2.0,Estimativa agregada,2026-02-17
Outros,21.0,2.0,Estimativa agregada,2026-02-17
Brancos/Nulos,15.0,2.0,Estimativa agregada,2026-02-17
```

---

## Colunas obrigatórias

| Coluna | Descrição | Exemplo |
|---|---|---|
| `candidato` | Nome do candidato | `Lula` |
| `intencao_voto_pct` | Intenção de voto em % | `35.0` |
| `desvio_padrao_pct` | Margem de erro em % | `2.0` |

## Colunas opcionais (informativas)

| Coluna | Descrição | Exemplo |
|---|---|---|
| `fonte` | Instituto de pesquisa | `Datafolha` |
| `data` | Data da pesquisa | `2026-02-17` |

---

## Exemplo: Atualizar com nova pesquisa

Suponha que saiu uma nova pesquisa Datafolha em 20/02/2026:
- Lula: 38%
- Flávio Bolsonaro: 27%
- Outros: 20%
- Brancos/Nulos: 15%
- Margem de erro: 2%

### Edite o CSV:

```csv
candidato,intencao_voto_pct,desvio_padrao_pct,fonte,data
Lula,38.0,2.0,Datafolha,2026-02-20
Flávio Bolsonaro,27.0,2.0,Datafolha,2026-02-20
Outros,20.0,2.0,Datafolha,2026-02-20
Brancos/Nulos,15.0,2.0,Datafolha,2026-02-20
```

### Rode novamente:

```bash
python src/simulation_v2.py
```

**Pronto!** O modelo vai gerar novos resultados com os dados atualizados.

---

## Agregando múltiplas pesquisas

Se você quiser usar a **média de várias pesquisas**, calcule manualmente e coloque no CSV:

| Pesquisa | Lula | Flávio |
|---|---|---|
| Datafolha | 38% | 27% |
| Quaest | 36% | 28% |
| PoderData | 37% | 26% |
| **Média** | **37%** | **27%** |

Coloque a média no CSV:

```csv
candidato,intencao_voto_pct,desvio_padrao_pct,fonte,data
Lula,37.0,2.0,Agregado (Datafolha + Quaest + PoderData),2026-02-20
...
```

---

## Importante

⚠️ **Os percentuais devem somar 100%**

Se suas pesquisas não incluem brancos/nulos explicitamente, calcule:
```
Brancos/Nulos = 100 - (Lula + Flávio + Outros)
```

✅ **Ordem não importa** — o código ordena alfabeticamente automaticamente

---

## Validação automática

Se o CSV estiver mal formatado, o script vai avisar:

```
FileNotFoundError: Arquivo data/pesquisas.csv não encontrado!
ValueError: Colunas faltando no CSV: {'intencao_voto_pct'}
```

Siga a mensagem de erro e corrija! 😊

---

## 🆕 Novidade v2.2: Índice de Rejeição

A partir da versão 2.2, o modelo suporta **índice de rejeição** como teto eleitoral.

### Por que a rejeição importa?

**Regra histórica:** Nenhum candidato com >50% de rejeição venceu uma eleição presidencial brasileira desde a redemocratização.

| Ano | Candidato | Rejeição (2º turno) | Resultado |
|---|---|---|---|
| 2022 | Bolsonaro | 51% | ❌ Perdeu |
| 2022 | Lula | 49% | ✅ Venceu |
| 2018 | Bolsonaro | 46% | ✅ Venceu |
| 2014 | Dilma | 41% | ✅ Venceu |

### Como adicionar rejeição ao CSV

Adicione a coluna `rejeicao_pct`:

```csv
candidato,intencao_voto_pct,rejeicao_pct,desvio_padrao_pct,instituto,data
Lula,35.0,42.0,2.0,Datafolha,2026-02-20
Flávio Bolsonaro,29.0,48.0,2.0,Datafolha,2026-02-20
Outros,21.0,0.0,2.0,Datafolha,2026-02-20
Brancos/Nulos,15.0,0.0,2.0,Datafolha,2026-02-20
```

**Notas:**
- Use `0.0` para candidatos sem dados de rejeição (como "Outros" e "Brancos/Nulos")
- A rejeição é perguntada nas pesquisas como: *"Em quem você não votaria de jeito nenhum?"*

### O que o modelo faz com a rejeição

1. **Teto Eleitoral:** Candidato não pode ultrapassar `(100 - rejeição)%` dos votos
   - Exemplo: Lula com 42% rejeição → teto de **58%**

2. **Transferência no 2º turno:** Votos de candidatos eliminados migram proporcionalmente ao **espaço disponível**
   - Candidato com menos rejeição recebe mais votos transferidos

3. **Validações:** Avisos automáticos para candidatos com >50% de rejeição (inviáveis)

### Retrocompatibilidade

Se você **não** adicionar a coluna `rejeicao_pct`, o modelo roda normalmente **sem** o teto de rejeição (comportamento da v2.1).
