#!/usr/bin/env python3
"""Ein redaktionell geschriebenes Comic-Skript als neue bearbeitbare Geschichte importieren. Keine Generierung."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'automation/comics'))
from stories import validate_definition
from engine import Engine
from lettering_plan import prepare


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('definition',type=Path)
    parser.add_argument('--url',default='http://192.168.1.224:8090')
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    value=validate_definition(json.loads(args.definition.read_text()));payload=value['payload']
    if value['mode']!='editorial':raise ValueError('Ein ausgearbeitetes redaktionelles Skript erforderlich.')
    plan=payload.get('narrative_plan',{});source=payload.get('source_provenance',{})
    if plan.get('review_method')!='redaktionell':raise ValueError('Redaktionelle Sinnanalyse fehlt.')
    if len(payload['scenes'])!=plan.get('recommended_count'):raise ValueError('Szenenzahl entspricht nicht der redaktionellen Empfehlung.')
    signature=hashlib.sha256((payload['article']+'\n').encode()).hexdigest()
    if signature!=plan.get('source_sha256'):raise ValueError('Skriptgrundlage passt nicht zur Sinnanalyse.')
    if payload.get('planned_article')!=payload['article'] or payload.get('planned_count')!=len(payload['scenes']):raise ValueError('Geplanter Umfang oder Ausgangstext stimmt nicht.')
    Engine.validate_scenes(None,payload['scenes'],len(payload['scenes']),payload['characters'])
    _,report=prepare(payload['scenes'],payload['characters'])
    if report['unresolved_panels']:raise ValueError('Beschriftung vor dem Import kürzen oder aufteilen.')
    ident=payload.get('editorial_script_id')
    if not isinstance(ident,str) or not ident:raise ValueError('Stabile Skriptkennung erforderlich.')
    if not args.apply:
        print(f"Geprüft: {value['name']}, {len(payload['scenes'])} Kacheln. Ohne --apply nichts gespeichert.");return
    token=os.getenv('COMIC_STUDIO_API_TOKEN')
    if token is None:token=subprocess.check_output(['docker','exec','comic-automation-comic-automation-1','python','-c','import os;print(os.getenv("API_TOKEN",""))'],text=True).strip()
    def api(path,body=None):
        req=urllib.request.Request(args.url.rstrip('/')+path,data=None if body is None else json.dumps(body,ensure_ascii=False).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
    live=next((entry for entry in api('/sources')['sources'] if entry['id']==source.get('id')),None)
    if not live or hashlib.sha256((live['text']+'\n').encode()).hexdigest()!=signature:raise ValueError('Aktive Quelle fehlt oder wurde inzwischen geändert.')
    if live.get('narrative_plan',{}).get('recommended_count')!=len(payload['scenes']):raise ValueError('Aktuelle Umfangsempfehlung wurde geändert.')
    for item in api('/stories')['stories']:
        if item['name']!=value['name']:continue
        existing=api('/stories/'+item['id'])
        if existing['payload'].get('editorial_script_id')==ident:
            print('Bereits vorhanden, unverändert: '+existing['id']);return
    created=api('/stories',value)
    print(json.dumps({'id':created['id'],'name':created['name'],'panels':len(created['payload']['scenes']),'images_generated':False},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
