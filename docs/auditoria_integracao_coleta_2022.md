# Auditoria de integração da coleta documental de 2022

Revisão em 31/10/2026, sem ampliar a coleta. Resultado: nenhuma divergência material identificada. Corrigidos somente acentos corrompidos em notas auxiliares e títulos do relatório; nenhum dado factual ou critério foi alterado.

- Relatório, sete CSVs, matriz, inventário e diagnósticos consistentes: 24 levantamentos, 27 cenários, 291 respostas, 48 fontes e 2.191 evidências.
- Inventário: 658 códigos distintos; 24 com resultados ao menos parcialmente transcritos, 634 sem resultados recuperados nesta entrega. Esses 634 não são declarados pesquisas nacionais executadas ou divulgadas: abrangência, execução e publicação continuam pendentes de verificação individual.
- Reproduzidos os 12 artefatos do catálogo em diretório temporário, com SHA-256 idênticos. O CLI retornou 1 pelas pendências esperadas, com saída JSON igual ao diagnóstico preservado.
- Conferidas todas as 15 linhas de cobertura do relatório contra os CSVs e os cortes 04/07, 03/08, 02/09, 18/09 e 25/09 de 2022 do protocolo. Janelas inclusivas de 14, 28 e 42 dias preservadas.
- Todos os 24 levantamentos e 27 cenários em quarentena; zero elegíveis; CSVs de snapshots e vínculos somente com cabeçalhos. Nenhum backtesting executado nesta auditoria.
- Conferidos os 281 arquivos de preservacao.json, sem ausências ou mudanças de hash.
- Conferidas as cópias originais contra seus hashes. Os 85 arquivos documentais são fontes preservadas, derivados de texto identificáveis e atributos de preservação; não há download órfão. Maior arquivo: 3.171.871 bytes. Não foi baixado o ZIP completo de questionários.
- Verificação de padrões de chaves privadas e tokens de credenciais não encontrou segredos no conjunto selecionado. Caches e temporários foram excluídos da seleção explícita de arquivos.
- Testes desta auditoria: 77 específicos passaram com MPLBACKEND=Agg. A suíte completa da entrega anterior passou com 724 testes, 14 avisos e cobertura de 90,81%; não foi repetida porque houve apenas correções tipográficas e este registro de auditoria.
- git diff --check e git diff --cached --check sem erros antes do commit.

## Hashes da reprodução

| Artefato | SHA-256 original e reproduzido |
|---|---|
| cenarios.csv | `e92e1130146f4067bb0cb9db06fa81595bed793853f9d4fd5c4735badc52a9e4` |
| cobertura_documental.csv | `5ce5a17b8314bda8c8df7c1df2aa28e71ebeac565a8b07abbf67713a8f5b9fed` |
| diagnostico_validacao.json | `5466060261128e25c07d8ea8ea0849763c1722f6c1aba546c03deae8efe33641` |
| evidencias.csv | `8cc8ede4f2826c550a6609fcaba3744354db84fb8c1aa3523c060093effb3527` |
| fontes.csv | `be1954e35d3bbb13ed481b88d9c037e59bdad807f50b939afb7e2c62d3298d2c` |
| inventario_registros.csv | `ec5fa52d5c7a1c468ada69a68892420f4952fe5e3205e047eedfd07f8254ce91` |
| matriz_documental.csv | `6b86b1742414a208e98d04c03578283bd027339c27040e8484b0d1d89dd566d6` |
| pesquisas.csv | `384b29177e240cf4f0c22bb9d87739c1d4cb8ad7051836f20b4cdbef94efbda5` |
| resultados.csv | `9aba101d99d51bcddabb3acce981f2c49f6be4b041f70b6af2050134e40a414d` |
| resumo.json | `fe3612b4b27bc5d62ee8ba5fa9cee9695800f4a23d4e47a322bbcf9ed4d85e29` |
| snapshot_pesquisas.csv | `1fd506b6f63f0bb6f5ee6863ee4b764f9cec220a2d427d3321c581db19504e7f` |
| snapshots.csv | `dac14bf82737d45ebb59b39cc04b8eb7e9d3f2779713f3628e360c3099c04530` |

## Arquivos selecionados para integração

Lista completa dos 114 arquivos da coleta de 2022, incluindo este relatório. Nenhum arquivo preexistente pertence à seleção.

```text
data/historico_v2/coleta_2022/.gitattributes
data/historico_v2/coleta_2022/acessos.json
data/historico_v2/coleta_2022/acessos_questionarios.json
data/historico_v2/coleta_2022/anotacoes_fontes.json
data/historico_v2/coleta_2022/catalogo/cenarios.csv
data/historico_v2/coleta_2022/catalogo/cobertura_documental.csv
data/historico_v2/coleta_2022/catalogo/diagnostico_validacao.json
data/historico_v2/coleta_2022/catalogo/evidencias.csv
data/historico_v2/coleta_2022/catalogo/fontes.csv
data/historico_v2/coleta_2022/catalogo/inventario_registros.csv
data/historico_v2/coleta_2022/catalogo/matriz_documental.csv
data/historico_v2/coleta_2022/catalogo/pesquisas.csv
data/historico_v2/coleta_2022/catalogo/resultados.csv
data/historico_v2/coleta_2022/catalogo/resumo.json
data/historico_v2/coleta_2022/catalogo/snapshot_pesquisas.csv
data/historico_v2/coleta_2022/catalogo/snapshots.csv
data/historico_v2/coleta_2022/coletar_fontes.py
data/historico_v2/coleta_2022/conflitos.json
data/historico_v2/coleta_2022/fontes_complementares.json
data/historico_v2/coleta_2022/fontes_planejadas.json
data/historico_v2/coleta_2022/gerar_catalogo.py
data/historico_v2/coleta_2022/indice_questionarios.json
data/historico_v2/coleta_2022/preparar_transcricoes.py
data/historico_v2/coleta_2022/preservacao.json
data/historico_v2/coleta_2022/recuperar_questionarios.py
data/historico_v2/coleta_2022/transcricoes.json
data/historico_v2/documentos/2022/.gitattributes
data/historico_v2/documentos/2022/F22_CONTR.zip
data/historico_v2/documentos/2022/F22_DF0623.html
data/historico_v2/documentos/2022/F22_DF0623.txt
data/historico_v2/documentos/2022/F22_DF0624.html
data/historico_v2/documentos/2022/F22_DF0624.txt
data/historico_v2/documentos/2022/F22_DF0728.html
data/historico_v2/documentos/2022/F22_DF0728.txt
data/historico_v2/documentos/2022/F22_DF0729.html
data/historico_v2/documentos/2022/F22_DF0729.txt
data/historico_v2/documentos/2022/F22_DF0819.html
data/historico_v2/documentos/2022/F22_DF0819.txt
data/historico_v2/documentos/2022/F22_DF0901.html
data/historico_v2/documentos/2022/F22_DF0901.txt
data/historico_v2/documentos/2022/F22_DF0910.html
data/historico_v2/documentos/2022/F22_DF0910.txt
data/historico_v2/documentos/2022/F22_DF0915.html
data/historico_v2/documentos/2022/F22_DF0915.txt
data/historico_v2/documentos/2022/F22_DF0922.html
data/historico_v2/documentos/2022/F22_DF0922.txt
data/historico_v2/documentos/2022/F22_DF0923.html
data/historico_v2/documentos/2022/F22_DF0923.txt
data/historico_v2/documentos/2022/F22_DFPDF0623.pdf
data/historico_v2/documentos/2022/F22_DFPDF0623.txt
data/historico_v2/documentos/2022/F22_DFPDF0728.pdf
data/historico_v2/documentos/2022/F22_DFPDF0728.txt
data/historico_v2/documentos/2022/F22_DFPDF0818.pdf
data/historico_v2/documentos/2022/F22_DFPDF0818.txt
data/historico_v2/documentos/2022/F22_DFPDF0909.pdf
data/historico_v2/documentos/2022/F22_DFPDF0909.txt
data/historico_v2/documentos/2022/F22_DFPDF0922.pdf
data/historico_v2/documentos/2022/F22_DFPDF0922.txt
data/historico_v2/documentos/2022/F22_FSB0627.pdf
data/historico_v2/documentos/2022/F22_FSB0627.txt
data/historico_v2/documentos/2022/F22_FSB0627N.html
data/historico_v2/documentos/2022/F22_FSB0627N.txt
data/historico_v2/documentos/2022/F22_FSB0725.html
data/historico_v2/documentos/2022/F22_FSB0725.txt
data/historico_v2/documentos/2022/F22_FSB0725N.html
data/historico_v2/documentos/2022/F22_FSB0725N.txt
data/historico_v2/documentos/2022/F22_FSB0919V.html
data/historico_v2/documentos/2022/F22_FSB0919V.txt
data/historico_v2/documentos/2022/F22_IPEC0815.html
data/historico_v2/documentos/2022/F22_IPEC0815.txt
data/historico_v2/documentos/2022/F22_IPEC0829.html
data/historico_v2/documentos/2022/F22_IPEC0829.txt
data/historico_v2/documentos/2022/F22_IPEC0905N.html
data/historico_v2/documentos/2022/F22_IPEC0905N.txt
data/historico_v2/documentos/2022/F22_IPEC0912.html
data/historico_v2/documentos/2022/F22_IPEC0912.txt
data/historico_v2/documentos/2022/F22_IPEC0919.html
data/historico_v2/documentos/2022/F22_IPEC0919.txt
data/historico_v2/documentos/2022/F22_PAR0706.html
data/historico_v2/documentos/2022/F22_PAR0706.txt
data/historico_v2/documentos/2022/F22_PAR0920.html
data/historico_v2/documentos/2022/F22_PAR0920.txt
data/historico_v2/documentos/2022/F22_PD0622.html
data/historico_v2/documentos/2022/F22_PD0622.txt
data/historico_v2/documentos/2022/F22_PD0706.html
data/historico_v2/documentos/2022/F22_PD0706.txt
data/historico_v2/documentos/2022/F22_PD0804.html
data/historico_v2/documentos/2022/F22_PD0804.txt
data/historico_v2/documentos/2022/F22_PD0921.html
data/historico_v2/documentos/2022/F22_PD0921.txt
data/historico_v2/documentos/2022/F22_QT00433_1.pdf
data/historico_v2/documentos/2022/F22_QT00433_1.txt
data/historico_v2/documentos/2022/F22_QT04180_1.pdf
data/historico_v2/documentos/2022/F22_QT04180_1.txt
data/historico_v2/documentos/2022/F22_QT05022_1.pdf
data/historico_v2/documentos/2022/F22_QT05022_1.txt
data/historico_v2/documentos/2022/F22_QT09088_1.pdf
data/historico_v2/documentos/2022/F22_QT09088_1.txt
data/historico_v2/documentos/2022/F22_QUA0803.html
data/historico_v2/documentos/2022/F22_QUA0803.txt
data/historico_v2/documentos/2022/F22_QUA0803N.html
data/historico_v2/documentos/2022/F22_QUA0803N.txt
data/historico_v2/documentos/2022/F22_QUA0831.html
data/historico_v2/documentos/2022/F22_QUA0831.txt
data/historico_v2/documentos/2022/F22_QUA0921.html
data/historico_v2/documentos/2022/F22_QUA0921.txt
data/historico_v2/documentos/2022/F22_REG.zip
data/historico_v2/documentos/2022/F22_REGIONAIS.html
data/historico_v2/documentos/2022/F22_REGIONAIS.txt
data/historico_v2/documentos/2022/F22_TSE.html
data/historico_v2/documentos/2022/F22_TSE.txt
docs/auditoria_integracao_coleta_2022.md
docs/coleta_historica_2022.md
tests/test_coleta_historica_2022.py
```
