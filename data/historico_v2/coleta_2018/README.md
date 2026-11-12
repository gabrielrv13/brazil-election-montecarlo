# Evidências auxiliares da coleta de 2018

Esta pasta complementa os sete esquemas do catálogo; não altera o protocolo.

- `transcricoes.json`: transcrição manual estruturada, campos ausentes, cenários e notas de leitura.
- `inventario_registros_tse.csv`: triagem do cadastro oficial, incluindo entradas ainda sem resultados recuperados e amostras locais. Períodos declarados não são campo realizado comprovado.
- `ocorrencias_sem_resultado.csv`: ocorrências documentadas fora do inventário filtrado, sem resultados imputados.
- `conflitos.csv`: alternativas publicadas e respectivas fontes, sem resolução automática.
- `cobertura_documental.csv`: disponibilidade temporal por cenário/corte/janela; não estabelece elegibilidade.
- `diagnostico_validacao.json`: saída integral do validador independente.
- `preservacao.json`: hashes dos arquivos protegidos existentes no início da coleta.
- `consultas_web.json`: trilha de consultas de descoberta; não substitui evidências de campo.
- `gerar_catalogo.py`: reproduz os cinco CSVs documentais em destino explícito, sem rede ou simulador.
- `auditar_entrega.py`: verifica preservação e gera diagnóstico, cobertura e relatório.

As cópias de fontes e os logs de tentativa HTTP ficam em `../documentos/2018/`.
Os arquivos `.txt` são extrações auxiliares de HTML/PDF para leitura; o hash em
`fontes.csv` aponta para o documento preservado, que prevalece sobre a extração.
Os ZIPs do TSE estão completos para pesquisas/contratantes; do ZIP de questionários
foram preservados índice e três membros extraídos por HTTP Range.

Os registros ainda precisam de segunda revisão. A repetição do gerador não constitui
revisão independente. Consulte `../../../docs/coleta_historica_2018.md` para limites,
conflitos e comandos de validação.

## Reprodução após checkout

Todas as cópias apontadas por `fontes.csv:caminho_local`, os dois ZIPs pequenos
do TSE e os logs consumidos pelo gerador acompanham a entrega. Os arquivos
`S048_BR.csv`/`S049_BR.csv` e as extrações `.txt` são derivados locais redundantes
e não precisam ser versionados: o gerador lê diretamente o membro BR do ZIP.
O ZIP de questionários de aproximadamente 681 MB não é necessário: os três
PDFs usados e o índice já estão incluídos. As URLs e nomes dos membros estão
em `questionarios_acesso.json`; fontes não recuperadas mantêm URL e status,
sem que sua obtenção seja exigida para reproduzir esta transcrição preliminar.

Execute da raiz:

```powershell
.\venv\Scripts\python.exe data/historico_v2/coleta_2018/gerar_catalogo.py --destino CAMINHO_NOVO
```

`preservacao.json` registra também outputs e JSONs locais da estação de coleta,
que não acompanham o commit. Se presentes, seus hashes são conferidos; sua
ausência em checkout limpo é permitida. A auditoria exige os arquivos protegidos
do projeto em `data/` e `src/`. Não publique outputs para satisfazer essa checagem.

Documentos preservados e os cinco CSVs documentais têm conversão de finais
de linha desativada em `../.gitattributes`, para manter hashes e reprodução.
O inventário derivado remove apenas espaços finais de campos; o ZIP preserva
o texto cadastral original. Documentos originais mantêm também os espaços da
fonte, excluídos da checagem de whitespace por atributo específico desse acervo.
