"""Validação documental histórica, sem importar o motor estatístico."""
import argparse
import csv
import json
import re
from datetime import datetime
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'historico_v2'
SCHEMA = json.loads((ROOT / 'schema.json').read_text(encoding='utf-8'))['tabelas']
PROTOCOL = json.loads((ROOT / 'protocolo_v2.0.0.json').read_text(encoding='utf-8'))


def carregar(path):
    """Leia CSVs estritamente, preservando IDs e valores originais."""
    tables = {}
    for name, spec in SCHEMA.items():
        with (Path(path) / f'{name}.csv').open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != spec['campos']:
                raise ValueError(f'cabecalho_invalido:{name}')
            tables[name] = list(reader)
    return tables


def validar(tables):
    """Retorne diagnósticos e decisões atômicas em ordem determinística."""
    malformed = [name for name, spec in SCHEMA.items()
                 if name not in tables or any(set(r) != set(spec['campos']) or
                    any(not isinstance(v, str) for v in r.values()) for r in tables[name])]
    if malformed:
        return {'diagnosticos': [{'codigo': 'estrutura_invalida', 'tabela': name, 'chave': ''}
                                for name in sorted(malformed)], 'decisoes': []}
    tables = {name: sorted(rows, key=lambda r: tuple(r[f] for f in SCHEMA[name]['campos']))
              for name, rows in tables.items()}
    diagnostics, decisions = set(), []
    bad = set()

    def issue(code, table, row):
        key = tuple(row.get(k, '') for k in SCHEMA[table]['chave'])
        diagnostics.add((code, table, '|'.join(key)))
        if row.get('pesquisa_id'):
            bad.add((row.get('pesquisa_id'), row.get('versao_id')))

    indices = {}
    for name, spec in SCHEMA.items():
        index = {}
        for row in tables[name]:
            key = tuple(row.get(k, '') for k in spec['chave'])
            if any(not v for v in key) or key in index:
                issue('chave_invalida_ou_duplicada', name, row)
            index[key] = row
            if set(row) != set(spec['campos']) or None in row.values():
                issue('estrutura_invalida', name, row)
            for field, value in row.items():
                if (field.startswith('data_') or field == 'as_of') and value:
                    try:
                        if date.fromisoformat(value).isoformat() != value:
                            raise ValueError
                    except (ValueError, TypeError):
                        issue('data_invalida', name, row)
        indices[name] = index

    for name in ('cenarios', 'resultados', 'evidencias', 'snapshot_pesquisas'):
        for row in tables[name]:
            pkey = (row['pesquisa_id'], row['versao_id'])
            if pkey not in indices['pesquisas']:
                issue('pesquisa_inexistente', name, row)
            if name != 'cenarios' and row['cenario_id']:
                if (*pkey, row['cenario_id']) not in indices['cenarios']:
                    issue('cenario_inexistente', name, row)
            if name in ('resultados', 'evidencias') and (row['fonte_id'],) not in indices['fontes']:
                issue('fonte_inexistente', name, row)
            if name == 'snapshot_pesquisas' and (row['snapshot_id'],) not in indices['snapshots']:
                issue('snapshot_inexistente', name, row)
    for p in tables['pesquisas']:
        versions = [v for v in tables['pesquisas'] if v['pesquisa_id'] == p['pesquisa_id']]
        if any(any(v[f] != p[f] for f in ('instituto_id', 'eleicao_id', 'cargo', 'turno', 'abrangencia')) for v in versions):
            issue('identidade_entre_versoes_inconsistente', 'pesquisas', p)
        required = ('ano', 'eleicao_id', 'cargo', 'turno', 'abrangencia', 'instituto_id',
                    'instituto_original', 'data_inicio_campo', 'data_fim_campo',
                    'grupo_dependencia_id', 'metodo', 'universo')
        if any(not p[f] for f in required):
            issue('identidade_incompleta', 'pesquisas', p)
        if p['data_inicio_campo'] > p['data_fim_campo']:
            issue('campo_invertido', 'pesquisas', p)
        if (p['cargo'], p['turno'], p['abrangencia']) != ('presidente', '1', 'BR'):
            issue('escopo_invalido', 'pesquisas', p)
        if p['eleicao_id'] != f"BR-{p['ano']}-presidente-1t":
            issue('eleicao_inconsistente', 'pesquisas', p)
        for field in ('n_planejado', 'n_realizado', 'n_base_ponderada', 'margem_erro_pp', 'nivel_confianca_pct'):
            if p[field]:
                try:
                    n = Decimal(p[field])
                    if not n.is_finite() or n <= 0 or (field.endswith('_pct') and n > 100):
                        raise InvalidOperation
                except InvalidOperation:
                    issue('numero_invalido', 'pesquisas', p)
    for f in tables['fontes']:
        if f['tipo_fonte'] not in {'registro_pesqele', 'relatorio', 'noticia', 'transmissao', 'arquivo_web', 'republicacao'} or not f['titulo'] or not (f['url_original'] or f['caminho_local']):
            issue('fonte_incompleta', 'fontes', f)
        if f['data_atualizacao_documento'] and f['data_atualizacao_documento'] < f['data_publicacao_documento']:
            issue('atualizacao_antes_publicacao', 'fontes', f)
        if f['sha256'] and not re.fullmatch(r'[0-9a-f]{64}', f['sha256']):
            issue('hash_invalido', 'fontes', f)
        if f['acessado_em_utc']:
            try:
                dt = datetime.fromisoformat(f['acessado_em_utc'].replace('Z', '+00:00'))
                if dt.utcoffset() is None or dt.utcoffset().total_seconds() != 0:
                    raise ValueError
            except ValueError:
                issue('acesso_utc_invalido', 'fontes', f)
    response_types = {'candidato', 'outros', 'branco', 'nulo', 'branco_nulo', 'nenhum', 'ns_nr', 'indeciso'}
    qualifiers = {'exato', 'zero_observado', 'zero_arredondado', 'nao_pontuou', 'menor_que', 'ausente'}
    for r in tables['resultados']:
        if r['tipo_resposta'] not in response_types or r['metrica'] not in {'intencao_voto', 'rejeicao'}:
            issue('resposta_invalida', 'resultados', r)
        if bool(r['candidato_id']) != (r['tipo_resposta'] == 'candidato'):
            issue('candidato_inconsistente', 'resultados', r)
        q = r['qualificador_valor']
        if q not in qualifiers or (q == 'ausente' and r['valor_pct'] != '') or (r['valor_pct'] == '' and q not in {'ausente', 'nao_pontuou'}) or (q == 'ausente' and not r['motivo_ausencia']):
            issue('ausencia_qualificador_invalido', 'resultados', r)
        if r['valor_pct']:
            try:
                n = Decimal(r['valor_pct'])
                if not n.is_finite() or not 0 <= n <= 100 or (q in {'zero_observado', 'zero_arredondado'} and n != 0):
                    raise InvalidOperation
            except InvalidOperation:
                issue('percentual_invalido', 'resultados', r)
    for c in tables['cenarios']:
        if c['base_percentual'] not in {'totais', 'validos'} or c['tipo_pergunta'] not in {'estimulada', 'espontanea'}:
            issue('base_pergunta_invalida', 'cenarios', c)
        if c['completo'] not in {'true', 'false'} or (c['completo'] == 'false' and not c['motivo_incompletude']):
            issue('completude_invalida', 'cenarios', c)
        if any(not c[f] for f in ('numero_pergunta', 'texto_pergunta', 'lista_candidatos_id', 'base_amostral', 'tratamento_candidato_pt')):
            issue('cenario_sem_identidade', 'cenarios', c)
        rows = [r for r in tables['resultados'] if all(r[k] == c[k] for k in ('pesquisa_id', 'versao_id', 'cenario_id')) and r['metrica'] == 'intencao_voto']
        expected = c['respostas_ids'].split('|')
        if not c['respostas_ids'] or len(set(expected)) != len(expected) or set(expected) != {r['resposta_id'] for r in rows} or any(r['valor_pct'] == '' for r in rows):
            issue('cenario_incompleto', 'cenarios', c)
        if set(filter(None, c['candidatos_ids'].split('|'))) != {r['candidato_id'] for r in rows if r['tipo_resposta'] == 'candidato'}:
            issue('lista_candidatos_inconsistente', 'cenarios', c)
    for e in tables['evidencias']:
        ck = (e['pesquisa_id'], e['versao_id'], e['cenario_id'])
        target = indices['resultados'].get((*ck, e['resposta_id'], e['metrica'])) if e['resposta_id'] else indices['cenarios'].get(ck) if e['cenario_id'] else indices['pesquisas'].get(ck[:2])
        if e['resposta_id'] and target and e['fonte_id'] != target['fonte_id']:
            issue('evidencia_fonte_divergente', 'evidencias', e)
        if target is None or e['campo_comprovado'] not in target or e['valor_original'] != target.get(e['campo_comprovado']):
            issue('evidencia_sem_campo_ou_divergente', 'evidencias', e)
        if e['conflito'] not in {'true', 'false'}:
            issue('conflito_invalido', 'evidencias', e)
        if not e['pagina_trecho'] or not e['revisor'] or e['status_evidencia'] not in {'comprovado', 'incompleto', 'hipotese'}:
            issue('evidencia_incompleta', 'evidencias', e)
        p = indices['pesquisas'].get(ck[:2], {})
        if any(e[f] and e[f] < p.get('data_fim_campo', '') for f in ('data_publicacao', 'data_disponibilidade')):
            issue('divulgacao_antes_campo', 'evidencias', e)
    invalid_sources = {key for _, table, key in diagnostics if table == 'fontes'}
    for e in tables['evidencias']:
        if e['fonte_id'] in invalid_sources:
            issue('fonte_em_quarentena', 'evidencias', e)
    # Fail closed: every populated factual field needs reviewed field-level evidence.
    technical = {'pesquisa_id', 'versao_id', 'cenario_id', 'resposta_id', 'fonte_id', 'pagina_tabela', 'motivo_ausencia', 'motivo_incompletude', 'completo'}
    for name in ('pesquisas', 'cenarios', 'resultados'):
        for row in tables[name]:
            for field, value in row.items():
                if not value or field in technical:
                    continue
                if not any(all(e[k] == row.get(k, '') for k in ('pesquisa_id', 'versao_id', 'cenario_id', 'resposta_id')) and (not row.get('resposta_id') or e['metrica'] == row['metrica']) and e['campo_comprovado'] == field and e['status_evidencia'] == 'comprovado' and e['conflito'] == 'false' for e in tables['evidencias']):
                    issue('campo_sem_evidencia', name, row)
    for s in tables['snapshots']:
        official = next((x for x in PROTOCOL['snapshots'] if x['snapshot_id'] == s['snapshot_id']), None)
        if not official or any(str(official[f]) != s[f] for f in ('eleicao_id', 'data_eleicao', 'as_of', 'horizonte_dias')) or s['janela_dias'] not in {'14', '28', '42'} or s['versao_politica'] != PROTOCOL['versao_protocolo']:
            issue('snapshot_fora_protocolo', 'snapshots', s)
            continue
        candidates = []
        for c in tables['cenarios']:
            key = tuple(c[k] for k in ('pesquisa_id', 'versao_id', 'cenario_id'))
            p = indices['pesquisas'].get(key[:2], {})
            reasons = []
            if key[:2] in bad or c['completo'] != 'true': reasons.append('quarentena_documental')
            if p.get('eleicao_id') != s['eleicao_id'] or c['lista_candidatos_id'] != s['universo_candidatos'] or f"{c['tipo_pergunta']}:{c['base_percentual']}" != s['cenario_alvo'] or c['tratamento_candidato_pt'] != s['tratamento_candidato_pt']:
                reasons.append('cenario_incompativel')
            if s['snapshot_id'] == '2018_1t_T-30': reasons.append('transicao_nao_avaliavel')
            try:
                age = (date.fromisoformat(s['as_of']) - date.fromisoformat(p.get('data_fim_campo', ''))).days
                if not 0 <= age <= int(s['janela_dias']): reasons.append('fora_janela')
            except ValueError: reasons.append('data_invalida')
            ev = [e for e in tables['evidencias'] if (e['pesquisa_id'], e['versao_id']) == key[:2] and e['cenario_id'] in {'', key[2]}]
            publication = []
            for e in ev:
                source = indices['fontes'].get((e['fonte_id'],), {})
                if e['status_evidencia'] != 'comprovado' or e['conflito'] != 'false': reasons.append('evidencia_pendente')
                if e['campo_comprovado'] == 'valor_pct':
                    if source.get('tipo_fonte') == 'registro_pesqele' or e['tipo_disponibilidade'] != 'publica_historica' or not e['data_publicacao'] or not e['data_disponibilidade']:
                        reasons.append('sem_prova_divulgacao')
                    publication.append(e['data_publicacao'])
                if any(e[f] > s['as_of'] for f in ('data_publicacao', 'data_disponibilidade')): reasons.append('posterior_corte')
            if not publication: reasons.append('sem_prova_divulgacao')
            d = {'snapshot_id': s['snapshot_id'], 'pesquisa_id': key[0], 'versao_id': key[1], 'cenario_id': key[2], 'motivos': sorted(set(reasons)), 'elegivel': not reasons}
            decisions.append(d)
            if not reasons: candidates.append((d, p, max(publication)))
        # Latest known version first, then latest collection per institute.
        for dimension in ('pesquisa_id', 'instituto_id', 'grupo_dependencia_id'):
            groups = {}
            for d, p, pub in candidates:
                if d['elegivel']: groups.setdefault(p[dimension], []).append((d, p, pub))
            for group in groups.values():
                best = max((p['data_fim_campo'], pub) for _, p, pub in group)
                winners = [d for d, p, pub in group if (p['data_fim_campo'], pub) == best]
                for d, p, pub in group:
                    if len(winners) > 1 or (p['data_fim_campo'], pub) != best:
                        d['elegivel'] = False
                        d['motivos'].append('empate_quarentena' if len(winners) > 1 else 'onda_superada')
        selected = [d for d, _, _ in candidates if d['elegivel']]
        if len(selected) < 2: diagnostics.add(('base_vazia' if not selected else 'baixa_diversidade', 'snapshots', s['snapshot_id']))
    for link in tables['snapshot_pesquisas']:
        d = next((d for d in decisions if all(d[k] == link[k] for k in ('snapshot_id', 'pesquisa_id', 'versao_id', 'cenario_id'))), None)
        p = indices['pesquisas'].get((link['pesquisa_id'], link['versao_id']), {})
        if not d or link['elegivel'] != str(d['elegivel']).lower() or link['data_recencia'] != p.get('data_fim_campo') or link['grupo_dependencia_id'] != p.get('grupo_dependencia_id') or (link['fonte_temporal_id'],) not in indices['fontes'] or not link['regra_selecao'] or not link['motivo']:
            issue('vinculo_snapshot_inconsistente', 'snapshot_pesquisas', link)
    if not tables['pesquisas']: diagnostics.add(('catalogo_vazio', 'pesquisas', ''))
    return {'diagnosticos': [dict(codigo=c, tabela=t, chave=k) for c, t, k in sorted(diagnostics)], 'decisoes': sorted(decisions, key=lambda d: (d['snapshot_id'], d['pesquisa_id'], d['versao_id'], d['cenario_id']))}


def main():
    """Imprima JSON; código 1 indica pendências, inclusive catálogo vazio."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('diretorio', nargs='?', type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        report = validar(carregar(args.diretorio))
    except (OSError, ValueError) as exc:
        print(json.dumps({'erro': str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(bool(report['diagnosticos']) or any(not d['elegivel'] for d in report['decisoes']))


if __name__ == '__main__':
    raise SystemExit(main())
