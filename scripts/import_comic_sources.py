#!/usr/bin/env python3
"""Ein Quellenpaket lokal prüfen und optional ohne Duplikate ins Dashboard einspielen."""
import argparse
import json
from pathlib import Path
import subprocess

# Der Zielcontainer verwendet seinen vorhandenen Store und seine Feldvalidierung.
# Es gibt keinen Modellaufruf, keine Änderung an Workflows und keinen Webabruf.
IMPORT_CODE = r'''
import copy,json,sys
from datetime import datetime,timezone
from source_generator import BUILTINS,clean_source
from storage import Store
value=json.load(sys.stdin);pack=value['pack'];incoming=[]
for item in pack['sources']:
    incoming.append({**clean_source(item),'id':item['id']})
store=Store('/data')
with store.connect() as db:
    db.execute('BEGIN IMMEDIATE')
    row=db.execute('SELECT value FROM integration_state WHERE key=?',('source-catalog',)).fetchone()
    saved=json.loads(row['value']) if row else None
    existing=copy.deepcopy(saved if saved is not None else BUILTINS)
    known={x['id'] for x in existing};added=[x for x in incoming if x['id'] not in known]
    backup=None
    if value['apply'] and added:
        path=store.root/'catalog-backups';path.mkdir(exist_ok=True)
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup=path/('vor-'+pack['id']+'-'+stamp+'.json')
        backup.write_text(json.dumps({'saved_catalog':saved,'effective_catalog':existing},ensure_ascii=False,indent=2)+'\n')
        db.execute('INSERT INTO integration_state VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('source-catalog',json.dumps(existing+added)))
    print(json.dumps({'modus':'gespeichert' if value['apply'] else 'Vorschau','paket':pack['title'],'vorhanden':len(existing),'neu':len(added),'unveraendert':len(incoming)-len(added),'gesamt':len(existing)+len(added),'sicherung':str(backup) if backup else None},ensure_ascii=False))
'''


def read_pack(path):
    pack=json.loads(Path(path).read_text())
    if not isinstance(pack,dict) or pack.get('schema_version')!=1:raise ValueError('Quellenpaket mit schema_version 1 erforderlich.')
    if not isinstance(pack.get('id'),str) or not pack['id'] or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in pack['id']):raise ValueError('Paket-ID nur mit Kleinbuchstaben, Ziffern und Bindestrichen.')
    if not isinstance(pack.get('title'),str) or not pack['title'].strip():raise ValueError('Pakettitel fehlt.')
    sources=pack.get('sources')
    if not isinstance(sources,list) or not sources:raise ValueError('Quellenliste fehlt.')
    ids=set()
    for source in sources:
        if not isinstance(source,dict) or not isinstance(source.get('id'),str) or not source['id']:raise ValueError('Jede Quelle benötigt eine feste ID.')
        if source['id'] in ids:raise ValueError('Doppelte Quellen-ID: '+source['id'])
        ids.add(source['id'])
    return pack


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paket',type=Path)
    parser.add_argument('--container',default='comic-automation-comic-automation-1')
    parser.add_argument('--apply',action='store_true',help='Neue Einträge ergänzen; vorhandene IDs bleiben unverändert.')
    args=parser.parse_args()
    try:
        pack=read_pack(args.paket)
        result=subprocess.run(['docker','exec','-i',args.container,'python','-c',IMPORT_CODE],input=json.dumps({'pack':pack,'apply':args.apply}),text=True,capture_output=True,check=True)
        print(result.stdout.strip())
    except (OSError,ValueError,subprocess.CalledProcessError) as exc:
        parser.exit(1,'Import fehlgeschlagen: '+(exc.stderr.strip() if isinstance(exc,subprocess.CalledProcessError) else str(exc))+'\n')


if __name__=='__main__':main()
