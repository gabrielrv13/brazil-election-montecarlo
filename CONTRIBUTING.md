# 🤝 Guia de Contribuição

Obrigado por considerar contribuir com o **brazil-election-montecarlo**!

---

## 🎯 Como Contribuir

### 1. Issues e Melhorias

Antes de começar a codar, veja o [ROADMAP.md](ROADMAP.md) para melhorias planejadas.

Se encontrou um bug ou tem uma ideia nova:
1. Verifique se já existe uma issue sobre o tema
2. Se não, [abra uma nova issue](https://github.com/seu-usuario/brazil-election-montecarlo/issues/new)
3. Descreva claramente o problema ou melhoria

---

### 2. Workflow de Desenvolvimento

#### Passo 1: Fork e Clone
```bash
# Fork no GitHub primeiro, depois:
git clone https://github.com/seu-usuario/brazil-election-montecarlo.git
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
pip install -r requirements.txt
```

#### Passo 4: Faça suas Mudanças
- Mantenha o código limpo e documentado
- Siga o estilo PEP 8
- Adicione docstrings nas funções
- Teste suas mudanças

#### Passo 5: Teste
```bash
# Rode a simulação para verificar que funciona
python src/simulation_v2.py

# Se criou novos scripts, teste também
python src/seu_novo_script.py
```

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

## 🐛 Reportando Bugs

Ao reportar um bug, inclua:

1. **Versão do Python:** `python --version`
2. **Sistema operacional:** Windows/Linux/macOS
3. **Descrição clara:** O que você esperava vs o que aconteceu
4. **Passos para reproduzir:**
   ```
   1. Execute `python src/simulation_v2.py`
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

- Abra uma [issue com label "question"](https://github.com/seu-usuario/brazil-election-montecarlo/issues)
- Ou envie um e-mail para: [seu-email@exemplo.com]

---

**Obrigado por contribuir! 🎉**
