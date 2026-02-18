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

## Agregando múltiplas pesquisas (automático)

Agora você pode agregar pesquisas automaticamente com o script `src/agregar_pesquisas.py`.

### 1) Monte um CSV com uma linha por instituto

```csv
candidato,intencao_voto_pct,desvio_padrao_pct,instituto,data,amostra
Lula,38.0,2.0,Datafolha,2026-02-18,2000
Lula,36.0,2.0,Quaest,2026-02-19,2500
Lula,37.0,2.0,PoderData,2026-02-20,2200
Flávio Bolsonaro,27.0,2.0,Datafolha,2026-02-18,2000
...
```

### 2) Rode a agregação

```bash
python src/agregar_pesquisas.py --input data/pesquisas_exemplo_multiplas.csv --output data/pesquisas.csv
```

O script aplica:
- Média ponderada por recência (`exp(-dias/7)`)
- Desvio agregado: `sqrt(sigma_medio² + sigma_entre_institutos²)`
- Detecção de outliers por z-score (limite padrão = 2)

### 3) (Opcional) remover outliers automaticamente

```bash
python src/agregar_pesquisas.py --input data/pesquisas_exemplo_multiplas.csv --output data/pesquisas.csv --remove-outliers
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
