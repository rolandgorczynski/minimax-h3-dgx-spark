#!/usr/bin/env python3
"""Redaktionelle Comics mit Erzählerporträt, Teilseiten und PDF exportieren."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import urllib.request


ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('comic_editorial_design',ROOT/'extensions/dgx-comics/design.py')
design=importlib.util.module_from_spec(spec);spec.loader.exec_module(design)
spec=importlib.util.spec_from_file_location('comic_editorial_layout',ROOT/'extensions/dgx-comics/editorial_layout.py')
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)


def layout(job,base,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    headers={}
    if os.getenv('COMIC_AUTOMATION_API_TOKEN'):headers['Authorization']='Bearer '+os.environ['COMIC_AUTOMATION_API_TOKEN']
    def get(path):
        with urllib.request.urlopen(urllib.request.Request(base.rstrip('/')+path,headers=headers),timeout=45) as response:return response.read()
    status=json.loads(get('/jobs/'+job))
    for artifact in status['artifacts']:
        name=artifact['name']
        if name.endswith('.zip'):continue
        target=(output/name).resolve()
        if not target.is_relative_to(output.resolve()):raise ValueError('Ungültiger Artefaktpfad.')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(get(artifact['url']))
    source=json.loads((output/'editorial-source.json').read_text())
    workflow=json.loads((output/'workflow.json').read_text())
    result=renderer.render_layout(output,source,workflow,design)
    print(json.dumps({'directory':str(output),'panels':result['panels'],'pages':result['pages']},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--job',required=True);parser.add_argument('--base-url',default='http://192.168.1.224:8090');parser.add_argument('--output',required=True)
    args=parser.parse_args();layout(args.job,args.base_url,args.output)
