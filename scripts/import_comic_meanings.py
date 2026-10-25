#!/usr/bin/env python3
"""Redaktionelle Sinnanalysen prüfen und optional ins Comic-Studio übernehmen."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import urllib.request


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--url',default='http://192.168.1.224:8090')
    args=parser.parse_args();value=json.loads(args.manifest.read_text())
    if not isinstance(value,dict) or not isinstance(value.get('entries'),list) or not 1<=len(value['entries'])<=100:raise ValueError('Manifest braucht 1–100 Einträge.')
    if not args.apply:
        print(str(len(value['entries']))+' redaktionelle Einträge vorbereitet. Ohne --apply nichts gespeichert.');return
    token=os.getenv('COMIC_STUDIO_API_TOKEN')
    if token is None:token=subprocess.check_output(['docker','exec','comic-automation-comic-automation-1','python','-c','import os;print(os.getenv("API_TOKEN",""))'],text=True).strip()
    request=urllib.request.Request(args.url.rstrip('/')+'/narrative-library/import',data=json.dumps(value,ensure_ascii=False).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=60) as response:result=json.load(response)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
