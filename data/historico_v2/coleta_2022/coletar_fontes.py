"""Obtenção de fontes de 2022 com log de tentativas; nunca escreve o catálogo."""
import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DOCS = HERE.parent / 'documentos/2022'


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[]
        self.hidden=0

    def handle_starttag(self, tag, attrs):
        if tag in {'script','style'}:
            self.hidden+=1
        if tag in {'p','div','li','br','h1','h2','h3','tr'}:
            self.parts.append('\n')

    def handle_endtag(self,tag):
        if tag in {'script','style'}:
            self.hidden=max(0,self.hidden-1)

    def handle_data(self,text):
        if not self.hidden:
            self.parts.append(text)


def download(spec):
    entry=dict(spec,acessado_em_utc=datetime.now(timezone.utc).isoformat())
    try:
        response=requests.get(spec['url_original'],timeout=75)
        entry['status_http']=response.status_code
        entry['url_final']=response.url
        response.raise_for_status()
        suffix='.zip' if response.content.startswith(b'PK') else '.pdf' if response.content.startswith(b'%PDF') else '.html'
        if spec['tipo_fonte']=='registro_pesqele' and spec['url_original'].endswith('.zip') and suffix!='.zip':
            raise ValueError('Resposta não é ZIP')
        path=DOCS/(spec['fonte_id']+suffix)
        path.write_bytes(response.content)
        entry.update(caminho_local=path.relative_to(REPO).as_posix(),sha256=hashlib.sha256(response.content).hexdigest(),bytes=len(response.content),status_acesso='lido_http_com_copia')
        if suffix=='.html':
            parser=Text()
            parser.feed(response.content.decode('utf-8',errors='replace'))
            lines=[' '.join(x.split()) for x in ''.join(parser.parts).splitlines()]
            path.with_suffix('.txt').write_text('\n'.join(x for x in lines if x)+'\n',encoding='utf-8')
    except (requests.RequestException,ValueError) as exc:
        entry.update(status_acesso='nao_recuperado',erro=str(exc))
    return entry


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baixar',action='store_true',required=True)
    args=parser.parse_args()
    DOCS.mkdir(parents=True,exist_ok=True)
    specs=json.loads((HERE/'fontes_planejadas.json').read_text(encoding='utf-8'))
    path=HERE/'acessos.json'
    previous=json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    existing={x['fonte_id'] for x in previous}
    with ThreadPoolExecutor(max_workers=5) as pool:
        entries=list(pool.map(download,[s for s in specs if s['fonte_id'] not in existing]))
    path.write_text(json.dumps(previous+entries,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{'fonte_id':e['fonte_id'],'status':e['status_acesso'],'bytes':e.get('bytes')} for e in entries]))


if __name__=='__main__':
    main()
