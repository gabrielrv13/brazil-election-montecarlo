"""Recupere somente membros identificados do acervo oficial, por HTTP Range."""
import argparse
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone

import requests

from coletar_fontes import DOCS, HERE, REPO

URL='https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2022.zip'


class RemoteZip(io.RawIOBase):
    def __init__(self):
        self.position=0
        r=requests.get(URL,headers={'Range':'bytes=0-0'},timeout=60)
        r.raise_for_status()
        if r.status_code!=206:
            raise ValueError('Servidor não confirmou HTTP Range')
        self.size=int(r.headers['Content-Range'].split('/')[-1])

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self,offset,whence=0):
        self.position=offset if whence==0 else self.position+offset if whence==1 else self.size+offset
        return self.position

    def read(self,size=-1):
        end=self.size-1 if size<0 else min(self.size-1,self.position+size-1)
        if end<self.position:
            return b''
        r=requests.get(URL,headers={'Range':f'bytes={self.position}-{end}'},timeout=60)
        r.raise_for_status()
        if r.status_code!=206 or len(r.content)!=end-self.position+1:
            raise ValueError('Intervalo recebido inconsistente')
        self.position=end+1
        return r.content


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baixar',action='store_true',required=True)
    parser.parse_args()
    entries=[]
    try:
        remote=RemoteZip()
        archive=zipfile.ZipFile(remote)
        names=archive.namelist()
        (HERE/'indice_questionarios.json').write_text(json.dumps(dict(url=URL,bytes_zip=remote.size,membros=names),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        for code in ('09088','00433','04180','05022'):
            for ordinal,name in enumerate([n for n in names if n.startswith('BR'+code+'2022_')],1):
                item=dict(fonte_id='F22_QT'+code+'_'+str(ordinal),url_original=URL,tipo_fonte='registro_pesqele',titulo='Questionário oficial BR-'+code+'/2022',membro_zip=name,acessado_em_utc=datetime.now(timezone.utc).isoformat())
                try:
                    content=archive.read(name)
                    if not content.startswith(b'%PDF'):
                        raise ValueError('Membro não é PDF')
                    path=DOCS/(item['fonte_id']+'.pdf')
                    path.write_bytes(content)
                    item.update(caminho_local=path.relative_to(REPO).as_posix(),sha256=hashlib.sha256(content).hexdigest(),bytes=len(content),status_acesso='lido_http_range_com_copia')
                except Exception as exc:
                    item.update(status_acesso='nao_recuperado',erro=str(exc))
                entries.append(item)
    except Exception as exc:
        entries.append(dict(fonte_id='F22_QT_INDICE',url_original=URL,tipo_fonte='registro_pesqele',titulo='Tentativa de acesso ao índice de questionários 2022',status_acesso='nao_recuperado',erro=str(exc),acessado_em_utc=datetime.now(timezone.utc).isoformat()))
    (HERE/'acessos_questionarios.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{'fonte_id':e['fonte_id'],'status':e['status_acesso']} for e in entries]))


if __name__=='__main__':
    main()
