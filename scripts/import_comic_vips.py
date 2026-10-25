#!/usr/bin/env python3
"""Vorbereitete VIP-Profile und lizenzierte Referenzbilder in die Figurenbibliothek übernehmen."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[1]


def profile(entry):
    fields=('name','description','outfit','backstory','personality','motivation','alignment','aliases','variants')
    result={key:entry[key] for key in fields}
    result['id']=uuid.uuid5(uuid.NAMESPACE_URL,'https://comic-studio.local/vip/'+entry['name']).hex
    result['references']=[];result['version']=0
    ref=entry['reference']
    result['backstory']+='\n\nBiografische Quellen: '+', '.join(entry['biography_sources'])
    result['backstory']+='\nBildvorlage: '+ref['artist']+'. '+ref['source_url']
    if ref.get('attribution'):result['backstory']+='\nNamensnennung: '+ref['attribution']
    if ref.get('reference_date'):result['backstory']+='\nDatum der Bildvorlage: '+ref['reference_date']
    result['backstory']+='\nBildlizenz: '+ref['license']+(' ('+ref['license_url']+')' if ref['license_url'] else ' laut Wikimedia Commons')
    result['backstory']+='\nBildaufbereitung: '+ref['changes']
    if len(result['backstory'])>2500:raise ValueError('Vorgeschichte einschließlich Bildnachweis zu lang: '+entry['name'])
    return result


def request(base,path,token='',data=None,content_type='application/json'):
    headers={}
    if token:headers['Authorization']='Bearer '+token
    if data is not None:headers['Content-Type']=content_type
    req=urllib.request.Request(base.rstrip('/')+path,headers=headers,data=data,method='POST' if data is not None else 'GET')
    try:
        with urllib.request.urlopen(req,timeout=60) as response:return json.load(response)
    except urllib.error.HTTPError as error:
        # Zugangsdaten und Request-Bodies nicht protokollieren.
        raise RuntimeError('Bibliotheksanfrage fehlgeschlagen, HTTP '+str(error.code)) from None


def upload(comfy,ident,pixels):
    boundary='ComicVip'+uuid.uuid4().hex
    body=('--'+boundary+'\r\nContent-Disposition: form-data; name="image"; filename="reference.png"\r\nContent-Type: image/png\r\n\r\n').encode()+pixels+('\r\n--'+boundary+'--\r\n').encode()
    return request(comfy,'/dgx-comics/characters/'+ident+'/references/0',data=body,content_type='multipart/form-data; boundary='+boundary)


def load_image(root,entry):
    filename=entry['reference']['filename'];path=root/filename
    if Path(filename).name!=filename or path.is_symlink() or path.resolve().parent!=root.resolve():
        raise ValueError('Ungültiger Referenzpfad.')
    pixels=path.read_bytes()
    if not pixels.startswith(b'\x89PNG\r\n\x1a\n') or len(pixels)>12*1024*1024:
        raise ValueError('Gültiges PNG mit maximal 12 MB erforderlich: '+filename)
    if hashlib.sha256(pixels).hexdigest()!=entry['reference']['sha256']:
        raise ValueError('Referenzbild entspricht nicht dem dokumentierten Bild: '+filename)
    return pixels


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=ROOT/'examples/comics/vip-profiles.json')
    parser.add_argument('--references-dir',type=Path,required=True)
    parser.add_argument('--studio-url',default='http://192.168.1.224:8090')
    parser.add_argument('--comfy-url',default='http://192.168.1.224:8188')
    parser.add_argument('--apply',action='store_true',help='Profile tatsächlich anlegen; ohne diesen Schalter nur prüfen.')
    args=parser.parse_args()
    token=os.getenv('COMIC_STUDIO_API_TOKEN')
    if token is None:
        token=subprocess.check_output(['docker','exec','comic-automation-comic-automation-1','python','-c','import os;print(os.getenv("API_TOKEN",""))'],text=True).strip()
    entries=json.loads(args.manifest.read_text())['characters']
    before=request(args.studio_url,'/characters',token)['characters']
    names={c['name'].casefold():c for c in before};ids={c['id']:c for c in before}
    hashes={c['id']:hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest() for c in before}
    prepared=[];skipped=[]
    for entry in entries:
        value=profile(entry)
        if value['id'] in ids or value['name'].casefold() in names:
            skipped.append(entry['name']);continue
        prepared.append((value,load_image(args.references_dir,entry)))
    print('Vorbereitet: '+str(len(prepared))+'. Bereits vorhanden und unverändert: '+str(len(skipped))+'.',flush=True)
    if not args.apply:
        print('Nur Prüfung. Keine Profile oder Bilder gespeichert.');return
    report={'created':[],'skipped':skipped,'previous_count':len(before),'complete':False}
    report_path=args.references_dir/'import-result.json'
    def save():
        temporary=report_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');temporary.replace(report_path)
    save()
    try:
        for value,pixels in prepared:
            saved=request(args.studio_url,'/characters',token,json.dumps(value,ensure_ascii=False).encode())
            report['created'].append({'name':saved['name'],'id':saved['id'],'reference_saved':False});save()
            updated=upload(args.comfy_url,saved['id'],pixels)
            if not updated.get('references'):raise RuntimeError('Referenzbild wurde nicht gespeichert: '+value['name'])
            report['created'][-1].update(reference_saved=True,references=updated['references']);save()
            print('Angelegt mit Referenzbild: '+value['name'],flush=True)
            time.sleep(.25)
        after=request(args.studio_url,'/characters',token)['characters'];by_id={c['id']:c for c in after}
        for ident,digest in hashes.items():
            if ident not in by_id or hashlib.sha256(json.dumps(by_id[ident],sort_keys=True).encode()).hexdigest()!=digest:
                raise RuntimeError('Eine zuvor vorhandene Figur wurde zwischenzeitlich geändert. Importbericht prüfen.')
        report.update(complete=True,after_count=len(after),previous_characters_unchanged=True);save()
        print('FERTIG: '+str(len(prepared))+' neue Figuren. Bestehende Figuren unverändert. Keine Modell- oder Comic-Aufträge gestartet.')
    except BaseException as error:
        report['error']=str(error);save();raise


if __name__=='__main__':main()
