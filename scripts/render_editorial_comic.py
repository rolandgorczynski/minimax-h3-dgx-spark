#!/usr/bin/env python3
"""Ein geprüftes Storyboard lokal rendern und als Seiten, PDF und Paket exportieren."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def docker(container, code, data=None, args=()):
    return subprocess.run(
        ['docker', 'exec', '-i', '-e', 'PYTHONPATH=/app', container,
         'python', '-c', code, *args], input=data, check=True,
    )


def upload(container, job, folder):
    """Upload only this job's generated layout assets; never shared workflows."""
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w') as archive:
        names = ['comic.png', 'comic.pdf', 'pages', 'panels', 'workflow.json', 'README.txt']
        if (folder / 'local-review.json').exists(): names.append('local-review.json')
        for name in names:
            archive.add(folder / name, arcname=name)
    docker(container,
           'import sys,tarfile,json,hashlib;from pathlib import Path;'
           'root=Path(__import__("os").getenv("DATA_DIR","/data"))/"jobs"/sys.argv[1];'
           'report=root/"local-review.json";source=root/"editorial-source.json";'
           'expected=hashlib.sha256(json.dumps(json.loads(source.read_text()),sort_keys=True).encode()).hexdigest();'
           'report.unlink() if report.exists() and json.loads(report.read_text()).get("storyboard_hash")!=expected else None;'
           'tarfile.open(fileobj=sys.stdin.buffer,mode="r|").extractall(root,filter="data")',
           stream.getvalue(), (job,))


def run(args):
    # Check dependencies and input before starting an expensive render.
    from layout_editorial_comic import layout
    source = args.source.resolve()
    payload = json.loads(source.read_text(encoding='utf-8'))
    if not isinstance(payload.get('scenes'), list) or not payload['scenes']:
        raise ValueError('Storyboard benötigt mindestens eine Szene.')
    if not payload.get('title') or not payload.get('article'):
        raise ValueError('Titel und Artikel fehlen im Storyboard.')
    job = args.job or uuid.uuid4().hex
    if not re.fullmatch('[a-f0-9]{32}', job):
        raise ValueError('--job benötigt 32 kleine Hexadezimalzeichen.')
    output = (args.output or ROOT / 'diagnostics' / 'comics' / job).resolve()
    output.mkdir(parents=True, exist_ok=True)
    marker = output / 'render-job.json'
    if not marker.exists() and any(output.iterdir()):
        raise ValueError('Ausgabeverzeichnis ist nicht leer. Ein neues Verzeichnis verwenden.')
    if marker.exists() and json.loads(marker.read_text())['id'] != job:
        raise ValueError('Ausgabeverzeichnis gehört zu einem anderen Auftrag.')
    marker.write_text(json.dumps({'id': job, 'source': str(source)}, ensure_ascii=False, indent=2)+'\n')
    print(f'Auftrag: {job}\nAusgabe: {output}', flush=True)
    print(f'Vor dem Abschluss bei Abbruch mit --job {job} --output {output} fortsetzen.', flush=True)
    # Pass JSON via stdin; no user text or file paths are interpolated into shell code.
    docker(args.container,
           'import sys,json,os;from storage import Store;from comfy import Comfy;from editorial import render;'
           'store=Store(os.getenv("DATA_DIR","/data"));'
           'render(store,Comfy(os.getenv("COMFYUI_URL","http://comfyui:8188"),store),'
           'os.getenv("WORKFLOW_TEMPLATE","/app/workflow_template.json"),json.load(sys.stdin),sys.argv[1])',
           json.dumps(payload, ensure_ascii=False).encode(), (job,))
    print('Bilder fertig. Erzeuge Teilseiten und PDF …', flush=True)
    layout(job, args.base_url, output)
    local_check = getattr(args, 'local_check', False)
    if local_check:
        from comic_local_assistant import Assistant, check
        print('Prüfe Texte und Bilder lokal; der Auftrag bleibt zur Sichtprüfung offen …', flush=True)
        report = check(payload, Assistant(), output / 'panels')
        (output / 'local-review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    elif (output / 'local-review.json').exists():
        expected = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        if json.loads((output / 'local-review.json').read_text()).get('storyboard_hash') != expected:
            (output / 'local-review.json').unlink()
    upload(args.container, job, output)
    if args.draft or local_check:
        # Refresh the downloadable manifest without completing the job or deleting its cache.
        docker(args.container,
               'import os,sys;from storage import Store;from editorial import export;'
               's=Store(os.getenv("DATA_DIR","/data"));s.stage(sys.argv[1],"editorial_review",artifacts=export(s,sys.argv[1]))',
               args=(job,))
        print('Entwurf bleibt bearbeitbar; mit derselben ID erneut rendern.', flush=True)
    else:
        docker(args.container,
               'import os,sys;from storage import Store;from comfy import Comfy;from editorial import finalize;'
               's=Store(os.getenv("DATA_DIR","/data"));'
               'finalize(s,Comfy(os.getenv("COMFYUI_URL","http://comfyui:8188"),s),sys.argv[1],sys.argv[2])',
               args=(job, args.review))
    url = args.base_url.rstrip('/') + '/jobs/' + job + '/artifacts/'
    headers = {}
    if os.getenv('COMIC_AUTOMATION_API_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['COMIC_AUTOMATION_API_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(url+'comic-bundle.zip', headers=headers), timeout=120) as response:
        target = output / 'comic-bundle.zip'
        temporary = target.with_suffix('.tmp')
        with temporary.open('wb') as handle:
            import shutil
            shutil.copyfileobj(response, handle)
        temporary.replace(target)
    print(f'Comic: {url}comic.png\nPDF: {url}comic.pdf\nPaket: {target}', flush=True)
    return job


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Bearbeitetes Storyboard als JSON; kein Rohartikel')
    parser.add_argument('--job', help='Offenen Auftrag nach Abbruch oder für Szenenänderungen fortsetzen')
    parser.add_argument('--output', type=Path, help='Ausgabeverzeichnis (Standard: diagnostics/comics/AUFTRAG)')
    parser.add_argument('--draft', action='store_true', help='Bearbeitbar lassen und Kachelcache behalten')
    parser.add_argument('--local-check', action='store_true', help='Texte und Bilder mit lokalen Modellen vorprüfen; bleibt immer als Entwurf offen')
    parser.add_argument('--review', default='Automatisch gerendert und exportiert; keine visuelle Prüfung durch das Skript.', help='Prüfvermerk im Bericht')
    parser.add_argument('--container', default=os.getenv('COMIC_AUTOMATION_CONTAINER', 'comic-automation-comic-automation-1'))
    parser.add_argument('--base-url', default=os.getenv('COMIC_AUTOMATION_URL', 'http://192.168.1.224:8090'))
    args = parser.parse_args()
    try:
        run(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'Fehler: {exc}\n')


if __name__ == '__main__':
    main()
