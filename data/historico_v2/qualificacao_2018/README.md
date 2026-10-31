# Qualificação documental, revisão de 31/10/2026

`qualificar.py --aplicar` reconstrói os cinco CSVs documentais a partir da
primeira transcrição e de decisões explícitas. Sem `--aplicar`, produz somente
artefatos de revisão nesta pasta. Não há escrita de snapshots, rede ou motor.

Arquivos de entrada:

- `decisoes.json`: decisões de leitura, instrumentos, conflitos e política conservadora de dependência.
- `acessos.json`: tentativas HTTP, membros extraídos do ZIP TSE, URLs, UTC real e hashes.
- `preservacao.json`: hashes registrados antes da qualificação, incluindo todos os módulos estatísticos rastreados e arquivos locais protegidos.
- `../coleta_2018/transcricoes.json` e acervo documental original: entrada preliminar preservada.
- `../documentos/2018/qualificacao/`: originais adicionais recuperados. PDFs têm hash e membro de origem; `.txt` são extrações auxiliares, sem autoridade sobre o original.

Saídas de revisão:

- `matriz_qualificacao.csv`: uma linha por pesquisa/versão/cenário, com respostas publicadas, pergunta aplicada, instrumento adicional, base, datas, fontes e critérios.
- `dependencias.csv`: componentes institucionais ligados por CNPJ de executor ou CPF/CNPJ de contratante. Não são certificados de independência ou sobreposição amostral.
- `historico_alteracoes.json`: conteúdo anterior e novo por campo, justificativa e evidências anteriores retiradas do catálogo ativo.
- `validacao_catalogo.json`: validador original sobre o catálogo sem snapshots.
- `validador_DATA_Nd.json`: validador original sobre cortes definidos apenas em memória.
- `diagnostico_por_corte.csv`: todos os motivos, resultado mecânico e gate documental adicional; T−30 explicitamente separado.
- `diagnostico_transicao_T30.csv`: recorte separado da transição não avaliável, nas três janelas.

IDs de grupo diferentes não comprovam independência. As relações institucionais
foram documentadas, mas a incerteza amostral entre componentes permanece e impede
liberação nesta revisão. Não use `elegivel_validador` como autorização de exportação.

O gerador original aceita `--preliminar` para obter somente a primeira entrega.
Por padrão aplica esta revisão. Os percentuais e os qualificadores originais não
foram alterados. O histórico de revisão não é uma nova versão histórica de resultado.

Para nova obtenção das mesmas fontes, `coletar_fontes.py --baixar` usa `requests`
com validação TLS e consulta por HTTP Range. `--complementares` adiciona as três
tentativas complementares ao log existente. Isso refaz acessos com datas/hashes
atuais; não é necessário para reproduzir esta revisão preservada. Questionários
não provam divulgação e documentos inacessíveis não são dependência de reprodução.

Relatório de leitura e limites: `../../../docs/qualificacao_historica_2018.md`.
