"""Gere inventários e cobertura documental, sem selecionar pesquisas para simulação."""
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
OUT = ROOT / 'coleta_2018'


def read(name):
    with (ROOT / (name + '.csv')).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def write(name, rows):
    with (OUT / name).open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    preserved = json.loads((OUT / 'preservacao.json').read_text(encoding='utf-8'))
    absent_local = [p for p in preserved if not (REPO / p).exists() and not p.startswith(('data/', 'src/'))]
    changed = [p for p, h in preserved.items() if p not in absent_local and hashlib.sha256((REPO / p).read_bytes()).hexdigest() != h]
    if changed:
        raise ValueError('Arquivos protegidos alterados: ' + repr(changed))
    run = subprocess.run([sys.executable, '-m', 'src.historico_v2'], cwd=REPO, capture_output=True, encoding='utf-8')
    if run.returncode not in (0, 1):
        raise RuntimeError(run.stderr or run.stdout)
    report = json.loads(run.stdout)
    (OUT / 'diagnostico_validacao.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    waves = json.loads((OUT / 'transcricoes.json').read_text(encoding='utf-8'))['levantamentos']
    coverage = []
    for cutoff in ('2018-09-07', '2018-09-23', '2018-09-30'):
        for window in (14, 28, 42):
            for w in waves:
                for s in w['cenarios']:
                    end, publication = w['fim'], s.get('publicacao', '')
                    reason = 'campo_realizado_ausente' if not end else 'publicacao_ausente' if not publication else 'publicacao_posterior' if publication > cutoff else 'fora_janela' if not 0 <= (date.fromisoformat(cutoff)-date.fromisoformat(end)).days <= window else 'cobertura_temporal_documentada'
                    coverage.append(dict(corte=cutoff, janela_dias=window, pesquisa_id='BR-'+w['registro']+'-2018', cenario_id=s['id'], fim_campo=end, publicacao=publication, fonte_resultado=s['fonte_id'], cobertura_temporal=reason, elegibilidade='nao_estabelecida_quarentena', avaliacao_principal='nao_avaliavel' if cutoff == '2018-09-07' else 'nao_materializada'))
    write('cobertura_documental.csv', coverage)
    conflicts = [
        dict(pesquisa_id='BR-06919-2018', campo='valor_pct:bn', valor='12', fonte_id='S055', localizacao='p. 8, tabela atual; branco/nulo/nenhum', tratamento='transcrito_com_conflito'),
        dict(pesquisa_id='BR-06919-2018', campo='valor_pct:bn', valor='11', fonte_id='S002', localizacao='Corpo: brancos/nulos/nenhum', tratamento='alternativa_preservada_sem_resolucao'),
        dict(pesquisa_id='BR-03861-2018', campo='valor_pct:amoedo', valor='3', fonte_id='S033', localizacao='p. 13, rodada atual', tratamento='transcrito_com_conflito'),
        dict(pesquisa_id='BR-03861-2018', campo='valor_pct:amoedo', valor='4', fonte_id='S066', localizacao='Texto: Amoedo', tratamento='alternativa_preservada_sem_resolucao'),
        dict(pesquisa_id='BR-08687-2018', campo='n_realizado', valor='9000', fonte_id='S005', localizacao='Corpo: 9000 eleitores em 343 municipios', tratamento='transcrito_pendente_relatorio_original'),
        dict(pesquisa_id='BR-08687-2018', campo='n_realizado', valor='9072', fonte_id='S006', localizacao='Corpo: amostra', tratamento='divergencia_jornalistica;9072_e_planejado_no_TSE'),
    ]
    write('conflitos.csv', conflicts)
    write('ocorrencias_sem_resultado.csv', [dict(registro_tse='BR-02553/2018', instituto='Datafolha', status='cancelamento_documentado', fonte_id='S043', localizacao='Texto: cancelamento do registro; campo previsto 04 a 06/09', motivo='Não consta do inventário filtrado do ZIP consultado. Cancelamento comprovado por notícia, sem aplicação comprovada ou resultados imputados.')])
    with (OUT / 'inventario_registros_tse.csv').open(encoding='utf-8', newline='') as f:
        registry = list(csv.DictReader(f))
    summary = Counter(d['codigo'] for d in report['diagnosticos'])
    lines = ['# Coleta documental de pesquisas presidenciais de 2018', '',
        'Primeira entrega, coletada em 30/10/2026. Referências: [plano](plano_reconstrucao_historica.md), [infraestrutura v2](historico_v2.md) e [protocolo congelado](../data/historico_v2/protocolo_v2.0.0.json). Não houve simulação, backtesting, alteração do protocolo ou seleção orientada por resultados eleitorais.', '',
        '## Estado da entrega', '',
        'Foram transcritos 27 levantamentos, 38 cenários e 382 respostas, com 67 fontes catalogadas e 2.960 vínculos de evidência. O catálogo inclui transcrições parciais: quantidade não significa elegibilidade. Todos os levantamentos permanecem em quarentena: grupos de dependência não foram arbitrados e a segunda revisão está pendente. Os dois CSVs de snapshots continuam somente com cabeçalhos. T−30 permanece não avaliável no protocolo principal.', '',
        '## Levantamento sistemático e limites', '',
        'Consultou-se o acervo aberto oficial do TSE, incluindo ZIPs de pesquisas e contratantes e o índice do ZIP de questionários. O membro BR contém 714 linhas e 657 códigos distintos. O inventário de triagem inclui 277 variantes de 274 códigos com cargo Presidente e fim declarado entre 27/07 e 30/09/2018. Inclui pesquisas locais que perguntaram sobre presidente: não é um censo de pesquisas nacionais publicadas. A classificação territorial das entradas restantes ainda exige leitura documental. Datas declaradas no registro não substituem campo efetivamente realizado.', '',
        'O acesso direto ao PesqEle retornou 403. Os ZIPs oficiais permitiram recuperar os cadastros e os três questionários de F01–F03. O ZIP completo de questionários não foi baixado: índice e membros foram recuperados por HTTP Range. Há colisões de códigos entre CNPJs no próprio arquivo do TSE; a identificação usa também CNPJ, período e amostra. BR-02039/2018 foi vinculado ao CNPJ 29550908000150, DataPoder360, e não à entrada de abril de outra empresa.', '',
        'A Wikipédia de 2018 e a lista da Gazeta foram usadas como índices para descobrir referências; não comprovam os percentuais transcritos. A Wikipédia de 2022 foi catalogada apenas como referência futura indicada pelo usuário. O arquivo CESOP 4405 refere-se a São Paulo e foi descartado como evidência de pesquisa nacional. BR-02553/2018 teve cancelamento documentado em S043: registro sem aplicação não gera resultado.', '',
        'Há tentativas sem recuperação integral: relatórios CNT/MDA (falha TLS), Lupa/Datafolha F03 (403/limite de tamanho), relatório XP (falha TLS), páginas R7 e Istoé (404), imagens/gráficos XP não transcritos. Esses casos permanecem no inventário de fontes; nada foi completado a partir de lembrança ou inferência. A coleta ainda não é exaustiva: o cadastro bruto reduz a invisibilidade das lacunas, mas não resolve cobertura nacional, execução ou publicação.', '',
        '## Cobertura por corte', '',
        'Contagens abaixo exigem fim de campo realizado conhecido e publicação documentada até o corte, com idade inclusiva de 0 a N dias. Não aplicam compatibilidade, completude, instituto ou dependência e **não são contagens de pesquisas elegíveis**. Um levantamento pode aparecer em vários cortes sem ser duplicado no catálogo.', '',
        '| Corte | Janela | Levantamentos com cobertura temporal | Cenários |', '|---|---:|---:|---:|']
    for cutoff in ('2018-09-07', '2018-09-23', '2018-09-30'):
        for window in (14, 28, 42):
            selected = [r for r in coverage if r['corte']==cutoff and r['janela_dias']==window and r['cobertura_temporal']=='cobertura_temporal_documentada']
            lines.append(f"| {cutoff} | {window} | {len({r['pesquisa_id'] for r in selected})} | {len(selected)} |")
    lines += ['', 'A janela principal é de 28 dias; 14 e 42 são sensibilidades congeladas. Publicação posterior, campo desconhecido e fora da janela constam individualmente em `cobertura_documental.csv`. Não se inferiu divulgação a partir de cadastro ou data prevista.', '',
        '## Inventário de transcrições', '', '| Registro | Instituto na fonte | Campo realizado | Publicação dos cenários | Fontes de resultados | Cenários |', '|---|---|---|---|---|---:|']
    for w in waves:
        lines.append(f"| BR-{w['registro']}/2018 | {w['marca_fonte']} | {w['inicio'] or 'não comprovado'} a {w['fim'] or 'não comprovado'} | {', '.join(sorted({s.get('publicacao','ausente') for s in w['cenarios']}))} | {', '.join(sorted({s['fonte_id'] for s in w['cenarios']}))} | {len(w['cenarios'])} |")
    lines += ['', '## F01–F03, conflitos e decisões de transcrição', '',
        '- **F01, BR-05003/2018:** campo realizado de 01–03/09, notícia publicada em 05/09. O registro previa período mais amplo e divulgação em 04/09. O questionário contém alternativas com Lula e Haddad; somente o cenário aplicado com Haddad tem resultados transcritos. Não foram inventados resultados do formulário com Lula. Falta conferir relatório original e categorias residuais.',
        '- **F02, BR-06919/2018:** campo de 18–19/09, divulgação em 20/09, 8.601 entrevistas realizadas versus 8.596 planejadas no cadastro. Relatório p. 8 apresenta 12% para branco/nulo/nenhum; texto do instituto informa 11%. Foi transcrito 12 com conflito explícito, mantendo 11 no inventário de conflitos. Não há resolução automática.',
        '- **F03, BR-08687/2018:** campo de 26–28/09, divulgação em 28/09. Registro planejava 9.072 entrevistas; notícia contemporânea informa 9.000 realizadas em 343 municípios. Outra notícia usa 9.072. A distinção planejado/realizado não elimina a divergência jornalística: falta o relatório original. Não se declarou a amostra definitivamente resolvida.',
        '- **FSB BR-03861/2018:** Amoêdo 3% no relatório original, p. 13, versus 4% em notícia. Valor 3 mantido com conflito; alternativa preservada.',
        '- **CNT/MDA BR-09086/2018:** os 17,3% de Haddad na pergunta de transferência referem-se aos eleitores de Lula, não à amostra nacional. Cenário separado, base amostral explicitada e base percentual vazia: o esquema atual não representa essa base condicional. Diagnóstico esperado; não houve conversão para percentual nacional.',
        '- **Vox Populi:** cenário com Lula separado do cenário com Haddad explicitamente apoiado por Lula. Sem misturar perguntas ou completar nomes ausentes com zero.', '',
        'Ausência de valor é ausência; zero impresso é `zero_arredondado`, não zero exato observado; “menos de 1%” é valor-limite 1 com `menor_que`. `exato` nos números não nulos identifica a transcrição literal do valor publicado, sem desfazer arredondamento. A troca de vírgula decimal por ponto é apenas representação. Categorias agregadas de brancos/nulos/indecisos permanecem agregadas. Nome original e identificador normalizado são campos distintos.', '',
        '## Fontes e rastreabilidade', '',
        'O catálogo completo está em `fontes.csv`: URL, tipo, status de acesso, caminho preservado e SHA-256 quando há cópia. `evidencias.csv` vincula fonte e localização aos campos; `transcricoes.json` preserva decisões e motivos de incompletude. Há notícias acessadas apenas pela ferramenta web, sem cópia HTTP: o status explicita essa limitação. Conteúdo recuperado em 2026 pode ter sido alterado desde 2018; datas históricas não equivalem à verificação de uma captura arquivada contemporânea. Cadastros e questionários não comprovam publicação de resultados.', '',
        'Relatórios recuperados incluem Datafolha de 13–14 e 18–19/09; Paraná de agosto e duas rodadas de setembro; FSB de 03, 17 e 24/09; Vox Populi; CNI/Ibope. O relatório FSB de 01/10 está preservado como tentativa de pesquisa, mas excluído das transcrições dos cortes por publicação posterior. Questionários oficiais de F01–F03 foram extraídos, com leitura das páginas relevantes. Logs HTTP, índice de questionários e consultas web ficam nos diretórios auxiliares.', '',
        'O inventário TSE preserva nome jurídico presente na exportação atual; o catálogo usa a marca contemporânea indicada na fonte. Não se assumiu que alterações cadastrais posteriores descrevem a marca histórica. Contratantes e metodologia declarada provêm do cadastro, sem afirmar execução integral do plano.', '',
        '## Validação e reprodução', '',
        'A partir da raiz, usando o Python do ambiente do projeto:', '', '```powershell', '.\\venv\\Scripts\\python.exe -m src.historico_v2', '.\\venv\\Scripts\\python.exe data/historico_v2/coleta_2018/auditar_entrega.py', '$env:MPLBACKEND="Agg"', '.\\venv\\Scripts\\python.exe -m pytest tests/test_historico_v2.py tests/test_coleta_historica_2018.py --no-cov -q', '```', '',
        'O validador retorna **1**, por pendências documentais esperadas; isso não significa catálogo aprovado. O relatório integral está em `diagnostico_validacao.json`. Não há decisões de snapshots, pois não foram materializados. Diagnósticos atuais:', '', '| Código | Quantidade |', '|---|---:|']
    lines += [f'| {k} | {v} |' for k,v in sorted(summary.items())]
    lines += ['', '`identidade_incompleta` inclui grupos de dependência ainda vazios; `cenario_sem_identidade` e `cenario_incompleto` sinalizam instrumento/lista/categorias não integralmente comprovados; `campo_sem_evidencia` inclui os dois percentuais em conflito; `base_pergunta_invalida` conserva a pergunta condicional sem forçar base incorreta. Os testes distinguem essas pendências de erros de chave, referência e tipos. O validador continua independente do motor.', '',
        'Para reproduzir os cinco CSVs documentais em **outro diretório**, executar `gerar_catalogo.py --destino CAMINHO`. O gerador usa apenas cópias locais e transcrições; não busca rede, não escreve snapshots e não importa o simulador. `auditar_entrega.py` verifica os hashes protegidos, gera cobertura, conflitos, diagnóstico e este relatório. A versão de coleta é documental_01; segunda revisão humana não foi simulada.', '',
        '## Trabalho pendente para a coleta histórica', '',
        'Conferir abrangência de todas as entradas candidatas do TSE; recuperar fontes originais e capturas contemporâneas ausentes; transcrever gráficos ainda não lidos; conferir pergunta literal, listas completas e respostas residuais; resolver conflitos com evidência adicional; estudar dependência, republicações e amostras sobrepostas; registrar segunda revisão. Só então propor elegibilidade e materialização de snapshots conforme protocolo. T−30 exige decisão metodológica explícita posterior. A coleta de 2022 permanece fora desta entrega.', '',
        f'Preservação conferida por SHA-256 para {len(preserved)-len(absent_local)} arquivos previamente existentes registrados em `preservacao.json`, incluindo protocolo, oito legados, validador e arquivos locais ali inventariados. Arquivos locais ausentes em uma cópia limpa não são exigidos; arquivos protegidos sob data/ e src/ continuam obrigatórios. O motor não integra o diff. Esta entrega é documental preliminar, sem aprovação para simulação.', '']
    (REPO / 'docs/coleta_historica_2018.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'codigo_validador':run.returncode,'diagnosticos':dict(summary),'preservados':len(preserved),'registros_variantes':len(registry),'registros_codigos':len({r['registro_tse'] for r in registry})},ensure_ascii=False))


if __name__ == '__main__':
    main()
