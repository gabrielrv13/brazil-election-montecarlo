# 📦 Resumo dos Arquivos de Organização

Estes arquivos foram criados para organizar o desenvolvimento futuro do projeto.

---

## 📋 Documentação Principal

### 1. **ROADMAP.md** 🗺️
**O que é:** Planejamento de todas as melhorias futuras  
**Contém:**
- Versão 2.2: Agregação de pesquisas, 5 candidatos, indecisos
- Versão 2.3: Melhorias menores
- Versão 2.4: Dashboard interativo
- Tabela de priorização

**Quando usar:** Para ver o que está planejado e escolher o que implementar

---

### 2. **CONTRIBUTING.md** 🤝
**O que é:** Guia de como contribuir com o projeto  
**Contém:**
- Workflow de desenvolvimento (fork, branch, commit, PR)
- Padrões de código (PEP 8, docstrings)
- Checklist do Pull Request
- Como reportar bugs

**Quando usar:** Antes de fazer qualquer contribuição ao projeto

---

### 3. **ISSUES_SUGERIDAS.md** 📝
**O que é:** Issues prontas para copiar e colar no GitHub  
**Contém:**
- Issue #1: Agregação automática de pesquisas
- Issue #2: Suporte para 5 candidatos
- Issue #3: Categoria "Indecisos"
- Issue #4: 2º turno baseado nos mais votados

**Quando usar:** Ao criar issues no GitHub para organizar o trabalho

---

### 4. **ATUALIZANDO_PESQUISAS.md** 📊
**O que é:** Tutorial de como atualizar o CSV com novas pesquisas  
**Contém:**
- Formato do arquivo CSV
- Exemplos práticos de atualização
- Como agregar múltiplas pesquisas manualmente
- Troubleshooting

**Quando usar:** Toda vez que sair uma nova pesquisa eleitoral

---

## 📁 Templates do GitHub

### 5. **.github/ISSUE_TEMPLATE/feature_request.md**
**O que é:** Template para sugerir novas funcionalidades  
**Quando usar:** Ao abrir uma issue de feature no GitHub

### 6. **.github/ISSUE_TEMPLATE/bug_report.md**
**O que é:** Template para reportar bugs  
**Quando usar:** Ao abrir uma issue de bug no GitHub

---

## 🎯 Fluxo de Trabalho Recomendado

### Quando uma nova pesquisa sair:
1. Edite `data/pesquisas.csv` seguindo `ATUALIZANDO_PESQUISAS.md`
2. Rode `python src/simulation_v2.py`
3. Commit: `git commit -m "chore: update polls with Datafolha YYYY-MM-DD"`

### Quando quiser implementar uma melhoria:
1. Consulte `ROADMAP.md` para ver o que está planejado
2. Leia `CONTRIBUTING.md` para entender o workflow
3. Crie uma branch: `git checkout -b feature/nome`
4. Implemente seguindo os padrões de código
5. Abra um Pull Request

### Quando encontrar um bug:
1. Vá para GitHub Issues
2. Use o template de `bug_report.md`
3. Preencha todas as seções
4. Submeta

### Para organizar o trabalho futuro:
1. Copie as issues de `ISSUES_SUGERIDAS.md`
2. Cole no GitHub Issues
3. Adicione labels e milestones
4. Atribua a pessoas ou deixe aberto para comunidade

---

## 📊 Estrutura Visual

```
brazil-election-montecarlo/
│
├── 📖 Documentação de Uso
│   ├── README.md                    # Documentação principal
│   ├── README_v2.md                  # Guia rápido v2
│   └── ATUALIZANDO_PESQUISAS.md     # Como atualizar dados
│
├── 🗺️ Planejamento
│   ├── ROADMAP.md                   # Melhorias futuras
│   ├── CHANGELOG_v2.md               # Histórico de mudanças
│   └── ISSUES_SUGERIDAS.md          # Issues prontas
│
├── 🤝 Contribuição
│   ├── CONTRIBUTING.md              # Guia de contribuição
│   ├── LICENSE                       # Licença MIT
│   └── .github/
│       └── ISSUE_TEMPLATE/          # Templates de issues
│
├── 💻 Código
│   └── src/
│       ├── simulation.py            # v1
│       ├── simulation_v2.py          # v2 atual
│       └── comparar_v1_v2.py        # Comparação
│
└── 📊 Dados
    └── data/
        ├── pesquisas.csv            # Dados atuais
        └── pesquisas_exemplo_multiplas.csv
```

---

## ✅ Próximos Passos

### 1. Organize o GitHub
- [ ] Vá para Settings → Features → marque "Issues"
- [ ] Crie as 4 issues de `ISSUES_SUGERIDAS.md`
- [ ] Adicione labels: `enhancement`, `bug`, `documentation`, `v2.2`, `v2.3`
- [ ] Crie milestones: `v2.2`, `v2.3`, `v2.4`

### 2. Documente no README principal
- [ ] Adicione badges (MIT license, Python version)
- [ ] Link para ROADMAP e CONTRIBUTING
- [ ] Seção "How to Contribute"

### 3. Configure Branch Protection (opcional)
- [ ] Settings → Branches → Add rule
- [ ] Require PR reviews before merging
- [ ] Require status checks to pass

---

**Seu projeto agora está super organizado! 🎉**
