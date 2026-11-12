# 🤝 Guia de Contribuição

Obrigado por considerar contribuir com o **brazil-election-montecarlo**!

---

## 🎯 Como Contribuir

### 1. Issues e Melhorias

Antes de começar a codar, veja o [ROADMAP.md](ROADMAP.md) para melhorias planejadas.

Se encontrou um bug ou tem uma ideia nova:
1. Verifique se já existe uma issue sobre o tema
2. Se não, [abra uma nova issue](https://github.com/gabrielrv13/brazil-election-montecarlo/issues/new)
3. Descreva claramente o problema ou melhoria

---

### 2. Workflow de Desenvolvimento

#### Passo 1: Fork e Clone
```bash
# Fork no GitHub primeiro, depois:
git clone https://github.com/gabrielrv13/brazil-election-montecarlo.git
cd brazil-election-montecarlo
```

#### Passo 2: Crie uma Branch
```bash
# Para novas funcionalidades:
git checkout -b feature/nome-da-funcionalidade

# Para correções de bugs:
git checkout -b fix/nome-do-bug

# Para melhorias de documentação:
git checkout -b docs/descricao
```

#### Passo 3: Configure o Ambiente
```bash
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate no Windows
pip install -e ".[dev]"   # dependências + pytest, pytest-cov, pytest-mock e ruff
```

#### Passo 4: Faça suas Mudanças
- Mantenha o código limpo e documentado
- Siga o estilo PEP 8
- Adicione docstrings nas funções
- Teste suas mudanças

#### Passo 5: Teste
```bash
# Suíte de testes (cobertura mínima de 80%, sem janelas gráficas)
pytest

# Rodada rápida da simulação, sem gravar no histórico
python -m src run --n-sim 2000 --seed 1 --no-history
```

O CI (`.github/workflows/tests.yml`) roda os mesmos comandos no Ubuntu (Python 3.11 e 3.12) e no Windows (Python 3.12).

#### Passo 6: Commit
```bash
git add .
git commit -m "feat: adiciona funcionalidade X

- Implementa Y
- Corrige Z
- Atualiza documentação W"
```

**Convenção de commits:**
- `feat:` nova funcionalidade
- `fix:` correção de bug
- `docs:` mudanças na documentação
- `refactor:` refatoração de código
- `test:` adição de testes
- `chore:` mudanças em build, dependências, etc.

#### Passo 7: Push e Pull Request
```bash
git push origin feature/nome-da-funcionalidade
```

No GitHub:
1. Vá para o repositório original
2. Clique em "Compare & pull request"
3. Preencha o template (será criado automaticamente)
4. Aguarde review

---

### 3. Checklist do Pull Request

Antes de submeter, verifique:

- [ ] O código funciona e foi testado
- [ ] Adicionei docstrings nas funções novas
- [ ] Atualizei o ROADMAP.md se relevante
- [ ] Atualizei o README.md se relevante
- [ ] Segui as convenções de código Python (PEP 8)
- [ ] A mensagem do commit é clara e descritiva
- [ ] Não incluí arquivos desnecessários (outputs/, .pyc, etc.)

---

## 📝 Padrões de Código

### Python Style Guide

Seguimos [PEP 8](https://pep8.org/) com algumas preferências:

```python
# ✅ BOM
def calcular_media_ponderada(valores, pesos):
    """
    Calcula a média ponderada de uma lista de valores.
    
    Args:
        valores: Array de valores numéricos
        pesos: Array de pesos (mesma dimensão que valores)
    
    Returns:
        float: Média ponderada
    """
    return np.average(valores, weights=pesos)


# ❌ RUIM
def calc(v,p):  # sem docstring, nomes não descritivos
    return np.average(v,weights=p)
```

### Nomenclatura

- **Variáveis e funções:** `snake_case`
- **Classes:** `PascalCase`
- **Constantes:** `UPPER_SNAKE_CASE`
- **Arquivos:** `lowercase_com_underscores.py`

### Documentação

Sempre adicione docstrings em funções públicas:

```python
def funcao_exemplo(param1, param2):
    """
    Breve descrição do que a função faz.
    
    Descrição mais detalhada se necessário, explicando
    algoritmos, edge cases, etc.
    
    Args:
        param1 (tipo): Descrição do parâmetro
        param2 (tipo): Descrição do parâmetro
    
    Returns:
        tipo: Descrição do retorno
    
    Raises:
        ExcecaoX: Quando isso acontece
    
    Example:
        >>> funcao_exemplo(1, 2)
        3
    """
    pass
```

---

## 🗂️ Estrutura do Repositório

```
brazil-election-montecarlo/
├── src/
│   ├── cli.py, __main__.py       # python -m src run | runoff | backtest
│   ├── core/                     # lógica pura: config, aggregation, simulation,
│   │                             #   runoff, pipeline, events, scoring, poll_quality
│   ├── io/                       # loader, runoff, report (CSV/PDF), history, manifest, wikipedia
│   ├── viz/                      # gráficos, gráfico do 2º turno, cores, dashboard Streamlit
│   ├── calibracao.py             # avaliação de 2026 e calibração do erro comum
│   ├── backtesting.py            # backtest histórico no motor do núcleo
│   ├── simulation_2turno.py      # script do 2º turno v2.10 (compatibilidade)
│   ├── retrospectiva_1t.py       # retrospectiva do 1º turno
│   ├── publicar_2turno.py        # portão de publicação e posts
│   └── historico_v2.py           # validador do catálogo histórico auditável
├── data/
│   ├── pesquisas.csv             # pesquisas de 1º turno
│   ├── pesquisas_2turno.csv      # pesquisas de 2º turno (antes e depois do 1º turno)
│   ├── pesquisas_only_2turno.csv # pesquisas de 2º turno após o 1º turno
│   ├── historico/                # recortes legados de 2018/2022 (backtest)
│   ├── historico_v2/             # catálogo histórico auditado (em quarentena)
│   └── wikipedia/                # pesquisas 2010–2022 transcritas da Wikipédia (calibração)
├── docs/                         # metodologia, contratos, auditorias, relatório de calibração
├── reports/                      # previsões publicadas
├── tests/                        # suíte pytest (fixtures em tests/fixtures/)
├── .github/workflows/tests.yml   # CI no Windows e no Linux
└── outputs/                      # gerado pelas rodadas (CSV/PNG/PDF ignorados pelo git)
```

---

## 🔄 Atualizando as Pesquisas

```bash
# 1. Acrescente a pesquisa em data/pesquisas.csv (formato no README)
# 2. Rode; o manifesto em outputs/ registra semente, entradas e saídas
python -m src run --as-of <data da pesquisa>

# 3. Commit
git add data/pesquisas.csv
git commit -m "chore: update polls - <instituto> <data>"
```

Para publicar uma previsão de 2º turno, siga o [PUBLISHING.md](PUBLISHING.md).

---

## 🐛 Reportando Bugs

Ao reportar um bug, inclua:

1. **Versão do Python:** `python --version`
2. **Sistema operacional:** Windows/Linux/macOS
3. **Descrição clara:** O que você esperava vs o que aconteceu
4. **Passos para reproduzir:**
   ```
   1. Execute `python -m src run --seed 42`
   2. Observe o erro na linha X
   3. ...
   ```
5. **Mensagem de erro completa** (se houver)
6. **Conteúdo do CSV** (se relevante)

---

## ✨ Sugerindo Melhorias

Para sugerir melhorias:

1. Explique **por que** a melhoria é útil
2. Descreva **como** você imagina que funcionaria
3. Se possível, inclua exemplos de código ou mockups
4. Mencione se está disposto a implementar

---

## 🎓 Recursos Úteis

- [PyMC Documentation](https://www.pymc.io/)
- [NumPy User Guide](https://numpy.org/doc/stable/user/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [Metodologia Chronicler-v2](https://www.szazkilencvenkilenc.hu/methodology-v2/)

---

## 📧 Contato

Dúvidas sobre como contribuir?

- Abra uma [issue com label "question"](https://github.com/gabrielrv13/brazil-election-montecarlo/issues)
- Ou envie um e-mail para: [seu-email@exemplo.com]

---

**Obrigado por contribuir! 🎉**
