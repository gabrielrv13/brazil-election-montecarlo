"""Obtenção explícita e rastreável das fontes da segunda revisão documental."""
import argparse
import hashlib
import io
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'documentos/2018/qualificacao'
HERE = Path(__file__).resolve().parent
URL_ZIP = 'https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2018.zip'
SOURCES = [
    ('Q001', 'https://www1.folha.uol.com.br/poder/2018/09/bolsonaro-domina-com-folga-no-df-e-haddad-lidera-em-pe-segundo-datafolha.shtml', 'noticia', '2018-09-20'),
    ('Q002', 'https://www.suno.com.br/noticias/btg-pactual-bolsonaro-haddad/', 'noticia', '2018-09-24'),
    ('Q003', 'https://apublica.org/checagem/2018/10/truco-pesquisa-falsa-coloca-bolsonaro-com-52-e-haddad-com-48/', 'noticia', '2018-10-23'),
    ('Q004', 'https://uploads.agencialupa.org/2022/02/4261674.pdf', 'relatorio', ''),
    ('Q005', 'https://economia.uol.com.br/noticias/reuters/2018/09/20/bolsonaro-vai-a-28-haddad-a-16-e-ciro-mantem-13-diz-datafolha.htm', 'noticia', '2018-09-20'),
    ('Q006', 'https://www.infomoney.com.br/politica/bolsonaro-tem-33-dos-votos-e-haddad-vai-de-16-para-23-isolando-se-em-2o-lugar-mostra-pesquisa/', 'noticia', '2018-09-24'),
]
COMPLEMENTARY = [
    ('Q007', 'https://noticias.uol.com.br/politica/eleicoes/2018/noticias/2018/09/24/pesquisa-ibope-presidente-24-setembro-bolsonaro-haddad-ciro-alckmin-marina.htm', 'noticia', '2018-09-24'),
    ('Q008', 'https://www.gaz.com.br/ibope-bolsonaro-lidera-com-28-e-haddad-aparece-com-22/', 'noticia', '2018-09-24'),
    ('Q009', 'https://www1.folha.uol.com.br/poder/2018/09/bolsonaro-perde-para-ciro-haddad-e-alckmin-no-segundo-turno-aponta-ibope.shtml', 'noticia', ''),
]


class RemoteZip(io.RawIOBase):
    """Leia somente intervalos solicitados, sem baixar o acervo de 681 MB."""
    def __init__(self):
        self.position = 0
        response = requests.get(URL_ZIP, headers={'Range': 'bytes=0-0'}, timeout=60)
        response.raise_for_status()
        if response.status_code != 206:
            raise ValueError('Servidor não confirmou HTTP Range')
        self.size = int(response.headers['Content-Range'].split('/')[-1])

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        return self.position

    def read(self, size=-1):
        end = self.size-1 if size < 0 else min(self.size-1, self.position+size-1)
        if end < self.position:
            return b''
        response = requests.get(URL_ZIP, headers={'Range': f'bytes={self.position}-{end}'}, timeout=60)
        response.raise_for_status()
        if response.status_code != 206 or len(response.content) != end-self.position+1:
            raise ValueError('Intervalo remoto inconsistente')
        self.position = end+1
        return response.content


def save(entry, content, suffix):
    path = OUT / (entry['fonte_id'] + suffix)
    path.write_bytes(content)
    entry.update(caminho_local=path.relative_to(ROOT.parents[1]).as_posix(), sha256=hashlib.sha256(content).hexdigest(), bytes=len(content), status_acesso='lido_http_com_copia')


def download(spec):
    sid, url, kind, publication = spec
    entry = dict(fonte_id=sid, url_original=url, tipo_fonte=kind, data_publicacao_documento=publication, acessado_em_utc=datetime.now(timezone.utc).isoformat())
    try:
        response = requests.get(url, timeout=60)
        entry['status_http'] = response.status_code
        response.raise_for_status()
        if kind == 'relatorio' and not response.content.startswith(b'%PDF'):
            raise ValueError('Resposta não é PDF')
        save(entry, response.content, '.pdf' if kind == 'relatorio' else '.html')
    except (requests.RequestException, ValueError) as exc:
        entry.update(status_acesso='nao_recuperado', erro=str(exc))
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baixar', action='store_true', required=True)
    parser.add_argument('--complementares', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.complementares:
        entries = json.loads((HERE / 'acessos.json').read_text(encoding='utf-8'))
        with ThreadPoolExecutor(max_workers=3) as pool:
            entries += list(pool.map(download, COMPLEMENTARY))
        (HERE / 'acessos.json').write_text(json.dumps(entries, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(entries[-3:],ensure_ascii=False))
        return
    with ThreadPoolExecutor(max_workers=4) as pool:
        entries = list(pool.map(download, SOURCES))
    try:
        archive = zipfile.ZipFile(RemoteZip())
        for register in ('05596','02410','03512','01057','06478','03861','01669','04669','05221','09678','06630','00526','02995'):
            matches = [i for i in archive.infolist() if i.filename.startswith('BR'+register+'2018_')]
            for ordinal, info in enumerate(matches, 1):
                entry = dict(fonte_id=f'QT{register}_{ordinal}', url_original=URL_ZIP, tipo_fonte='registro_pesqele', data_publicacao_documento='', acessado_em_utc=datetime.now(timezone.utc).isoformat(), membro_zip=info.filename, registro_tse='BR-'+register+'/2018')
                try:
                    content = archive.read(info)
                    if not content.startswith(b'%PDF'):
                        raise ValueError('Membro não é PDF')
                    save(entry, content, '.pdf')
                except Exception as exc:
                    entry.update(status_acesso='nao_recuperado', erro=str(exc))
                entries.append(entry)
    except Exception as exc:
        entries.append(dict(fonte_id='QT_INDICE',url_original=URL_ZIP,status_acesso='nao_recuperado',erro=str(exc),acessado_em_utc=datetime.now(timezone.utc).isoformat()))
    (HERE / 'acessos.json').write_text(json.dumps(entries, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps([{'fonte_id':e['fonte_id'], 'status':e['status_acesso'], 'bytes':e.get('bytes')} for e in entries]))


if __name__ == '__main__':
    main()
