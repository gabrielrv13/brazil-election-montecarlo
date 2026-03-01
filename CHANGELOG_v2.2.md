# Changelog v2.2

## [2.2.0] - 2026-02-18

### 🎯 Feature Principal: Índice de Rejeição

A versão 2.2 introduz o **índice de rejeição como teto eleitoral**, a melhoria mais importante desde o lançamento do projeto.

#### O Que Mudou

**Regra Histórica Implementada:**  
Nenhum candidato com >50% de rejeição venceu uma eleição presidencial brasileira desde a redemocratização (dados TSE 2014-2022).

### ✨ Novas Funcionalidades

#### 1. Teto Eleitoral por Rejeição
- Candidatos não podem ultrapassar `(100 - rejeição)%` dos votos válidos
- Exemplo: Candidato com 42% rejeição → teto de 58%
- Aplicado tanto no 1º quanto no 2º turno

#### 2. Transferência Proporcional (2º Turno)
- **ANTES:** Votos de candidatos eliminados se distribuíam em proporções fixas (40%/35%/25%)
- **AGORA:** Distribuição proporcional ao **espaço disponível** de cada candidato
- Candidato com menos rejeição recebe mais votos transferidos

**Exemplo:**
```
Lula: rejeição 42% → espaço 58%
Flávio: rejeição 48% → espaço 52%

Transferência de "Outros":
- 52.7% → Lula (58/110)
- 47.3% → Flávio (52/110)
- ~20% → Brancos/Nulos
```

#### 3. Validações e Avisos
- Alerta automático para candidatos com >50% rejeição (eleitoralmente inviáveis)
- Aviso para candidatos entre 45-50% rejeição (próximos ao limite crítico)
- Estatísticas de quantas simulações foram limitadas pelo teto

#### 4. Visualizações Aprimoradas
- Novo gráfico: "Índice de Rejeição" com código de cores
  - 🟢 Verde: <45% (viável)
  - 🟠 Laranja: 45-50% (alerta)
  - 🔴 Vermelho: >50% (inviável)
- Linha de teto de rejeição nos gráficos de votos válidos

### 📊 Dados Necessários

Nova coluna no CSV: `rejeicao_pct`

```csv
candidato,intencao_voto_pct,rejeicao_pct,desvio_padrao_pct,instituto,data
Lula,35.0,42.0,2.0,Datafolha,2026-02-20
Flávio Bolsonaro,29.0,48.0,2.0,Datafolha,2026-02-20
```

**Nota:** A coluna é **opcional**. Se não fornecida, o modelo roda sem teto de rejeição (comportamento v2.1).

### 🧪 Testes

Adicionada suite de testes automatizados:
- ✅ `test_teto_eleitoral()` - Verifica aplicação do teto
- ✅ `test_inviabilidade_eleitoral()` - Identifica candidatos inviáveis
- ✅ `test_transferencia_proporcional()` - Valida cálculo de transferência
- ✅ `test_retrocompatibilidade()` - Garante funcionamento sem rejeição

Execute: `python tests/test_rejeicao.py`

### 📝 Documentação Atualizada

- `ATUALIZANDO_PESQUISAS.md` - Seção sobre como adicionar rejeição
- `README.md` - Exemplos de uso com rejeição
- Comentários detalhados no código

### 🔧 Melhorias Técnicas

- Função `aplicar_teto_rejeicao()` modular e testável
- Função `validar_viabilidade()` com análise pré-simulação
- Estatísticas de limitação por candidato
- Código de cores automático baseado em níveis de rejeição

### 📈 Impacto nos Resultados

Com os dados de exemplo (Lula 42% rej, Flávio 48% rej):
- Lula: limitado em ~2-5% das simulações
- Flávio: limitado em ~8-12% das simulações
- Transferência no 2º turno favorece quem tem menos rejeição

### 🔄 Retrocompatibilidade

✅ **100% retrocompatível** com v2.1:
- CSV sem coluna `rejeicao_pct` funciona normalmente
- Nenhum código existente precisa ser alterado
- Outputs têm mesmo formato

### 🐛 Bugs Corrigidos

Nenhum bug conhecido da v2.1.1.

### 📦 Arquivos Novos/Modificados

**Novos:**
- `src/simulation_v2.2.py` - Versão com rejeição
- `tests/test_rejeicao.py` - Suite de testes
- `CHANGELOG_v2.2.md` - Este arquivo
- `data/pesquisas_v2.2.csv` - Exemplo com rejeição

**Modificados:**
- `ATUALIZANDO_PESQUISAS.md` - Seção sobre rejeição
- `data/pesquisas.csv` - Adicionada coluna rejeição

### 🎓 Referências

Dados históricos de rejeição:
- TSE - Resultados oficiais 2014-2022
- Datafolha - Pesquisas de rejeição
- Análise: "Por que a rejeição é mais importante que a intenção de voto" (Poder360)

### 🚀 Próximos Passos (v2.3)

Conforme ROADMAP.md:
1. Agregação automática de múltiplas pesquisas
2. Categoria "Indecisos"
3. 2º turno baseado nos mais votados do 1º turno
4. Detecção de outliers

---

**Versão:** 2.2.0  
**Data:** 2026-02-18  
**Autor:** @gabrielrv13  
**Status:** ✅ Stable
