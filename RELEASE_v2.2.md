# 🎉 Release v2.2 — Rejection Index as Electoral Ceiling

**Data:** 18 de Fevereiro de 2026  
**Versão:** 2.2.0  
**Status:** Stable for Production

---

## 🎯 Destaque Principal

### Índice de Rejeição como Teto Eleitoral

A versão 2.2 implementa a funcionalidade **#1 no ROADMAP**: o índice de rejeição como limite máximo de votos que um candidato pode receber.

**Por que isso importa:**
- Historicamente, nenhum candidato com >50% de rejeição venceu desde a redemocratização
- A rejeição funciona como um "teto" que limita o crescimento eleitoral
- Melhora drasticamente o realismo das previsões

---

## ✨ O Que Há de Novo

### 1. Teto Eleitoral Automático
```
Lula: rejeição 42% → teto de 58% dos votos válidos
Flávio: rejeição 48% → teto de 52% dos votos válidos
```

### 2. Transferência Inteligente no 2º Turno
Votos de candidatos eliminados agora migram proporcionalmente ao **espaço disponível**:
- Candidato com menos rejeição recebe mais votos
- Modelo muito mais realista

### 3. Validações Automáticas
```
❌ Flávio Bolsonaro: 53% rejeição (INVIÁVEL)
⚠️  Lula: 48% rejeição (próximo ao limite)
✅ Marina Silva: 35% rejeição (viável)
```

### 4. Visualizações Aprimoradas
- Novo gráfico de rejeição com código de cores
- Linha de teto nos gráficos de votos válidos
- Estatísticas de limitação

---

## 📊 Como Usar

### Passo 1: Atualize o CSV

Adicione a coluna `rejeicao_pct`:

```csv
candidato,intencao_voto_pct,rejeicao_pct,desvio_padrao_pct,instituto,data
Lula,35.0,42.0,2.0,Datafolha,2026-02-20
Flávio Bolsonaro,29.0,48.0,2.0,Datafolha,2026-02-20
Outros,21.0,0.0,2.0,Datafolha,2026-02-20
Brancos/Nulos,15.0,0.0,2.0,Datafolha,2026-02-20
```

**Onde conseguir dados de rejeição:**
- Datafolha, Quaest, PoderData perguntam: *"Em quem você não votaria de jeito nenhum?"*

### Passo 2: Rode a v2.2

```bash
python src/simulation_v2.2.py
```

### Passo 3: Analise os Resultados

O modelo agora mostra:
- Teto eleitoral de cada candidato
- Avisos de inviabilidade
- Quantas simulações foram limitadas pelo teto
- Transferência proporcional no 2º turno

---

## 🧪 Testado e Validado

✅ Suite de 4 testes automatizados  
✅ Todos os testes passando  
✅ 100% retrocompatível com v2.1  

Execute os testes:
```bash
python tests/test_rejeicao.py
```

---

## 📈 Impacto nos Resultados

### Exemplo com dados reais:

**Sem rejeição (v2.1):**
```
Lula: 62% no 2º turno (irealista)
Flávio: 38%
```

**Com rejeição (v2.2):**
```
Lula: 57% no 2º turno (limitado pelo teto de 58%)
Flávio: 43%
⚠️  Lula foi limitado em 3.2% das simulações
```

---

## 🔄 Retrocompatibilidade

✅ **Totalmente retrocompatível**

Se você não adicionar a coluna `rejeicao_pct`, o modelo funciona **exatamente como a v2.1** (sem teto de rejeição).

Nenhum código existente precisa ser alterado.

---

## 📦 Download

**GitHub Release:** [v2.2.0](https://github.com/gabrielrv13/brazil-election-montecarlo/releases/tag/v2.2.0)

**Arquivos principais:**
- `src/simulation_v2.2.py` - Código principal
- `tests/test_rejeicao.py` - Testes
- `CHANGELOG_v2.2.md` - Mudanças detalhadas
- `data/pesquisas.csv` - Exemplo com rejeição

---

## 🚀 Instalação

### Novo projeto:
```bash
git clone https://github.com/gabrielrv13/brazil-election-montecarlo.git
cd brazil-election-montecarlo
git checkout v2.2.0
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate no Windows
pip install -r requirements.txt
python src/simulation_v2.2.py
```

### Atualizar projeto existente:
```bash
git pull origin main
# Adicione coluna rejeicao_pct ao data/pesquisas.csv
python src/simulation_v2.2.py
```

---

## 📚 Documentação

- [CHANGELOG_v2.2.md](CHANGELOG_v2.2.md) - Mudanças técnicas completas
- [ATUALIZANDO_PESQUISAS.md](ATUALIZANDO_PESQUISAS.md#-novidade-v22-índice-de-rejeição) - Como adicionar rejeição
- [ROADMAP.md](ROADMAP.md) - Próximas funcionalidades

---

## 🤝 Contribuindo

Esta release implementou a **Issue #5** do ROADMAP. Próximas prioridades:

1. ✅ ~~Índice de rejeição~~ (concluído v2.2)
2. 🔄 Agregação automática de pesquisas (próxima)
3. 🔄 Categoria "Indecisos"
4. 🔄 5+ candidatos com cores dinâmicas

Veja [CONTRIBUTING.md](CONTRIBUTING.md) para contribuir.

---

## 🙏 Agradecimentos

- **Inspiração:** Modelo Chronicler-v2 (eleições húngaras)
- **Dados históricos:** TSE, Datafolha, Quaest
- **Comunidade:** Feedback e sugestões

---

## 📊 Estatísticas do Release

- **Linhas de código adicionadas:** ~400
- **Testes criados:** 4
- **Documentação atualizada:** 3 arquivos
- **Bugs corrigidos:** 0 (v2.1.1 já estava estável)
- **Tempo de desenvolvimento:** ~4 horas

---

## 🐛 Problemas Conhecidos

Nenhum bug conhecido nesta release.

Se encontrar algum problema, abra uma [issue no GitHub](https://github.com/gabrielrv13/brazil-election-montecarlo/issues).

---

## 📅 Próxima Release

**v2.3** está planejada para Março/2026 com:
- Agregação automática de múltiplas pesquisas
- Categoria "Indecisos"
- Melhorias de UX

---

**Versão:** 2.2.0  
**Autor:** @gabrielrv13  
**Licença:** MIT  
**Status:** ✅ Stable for Production
