"""Render an editor-authored storyboard verbatim with workflow 04; no LLM writing."""
import argparse
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import uuid
import zipfile

from comfy import Comfy
from engine import Engine,ID,validate_request
from storage import Store


def export(store,job):
    root=store.directory(job);bundle=root/'comic-bundle.zip';temporary=bundle.with_suffix('.tmp')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob('*')):
            if path.is_file() and path.suffix not in ('.zip','.tmp') and 'checkpoints' not in path.parts:archive.write(path,path.relative_to(root))
    temporary.replace(bundle)
    artifacts=[{'name':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                'url':f'/jobs/{job}/artifacts/{p.relative_to(root)}'} for p in sorted(root.rglob('*')) if p.is_file() and p.suffix!='.tmp' and 'checkpoints' not in p.parts]
    return artifacts


def render(store,client,template,payload,job,worker=False,review_engine=None):
    req=validate_request({'kacheln':len(payload['scenes']),'stil':payload.get('style','Großstadt-Noir (düster)'),
        'seed':payload.get('seed',1984),'max_korrekturrunden':0,'figuren_ids':payload.get('library_ids',[]),'signatur':payload.get('signature','')})
    previous=store.get(job)
    if not previous:store.create(job,req,initial_status='editing')
    elif previous['request']!=req:raise ValueError('Vorhandener Redaktionsauftrag hat andere Grundeinstellungen.')
    elif previous['status']!='editing' and not (worker and previous['status']=='running' and previous.get('editorial_mode')):raise ValueError('Abgeschlossener Auftrag wird nicht überschrieben. Neue Auftrags-ID verwenden.')
    engine=Engine(store,client,template,'unused','unused')
    doc={'title':payload['title'],'story':payload['article'],'characters':payload.get('characters',[])}
    if not isinstance(doc['title'],str) or not doc['title'].strip() or len(doc['title'])>200 or not isinstance(doc['story'],str) or not doc['story'].strip() or len(doc['story'])>16000:raise ValueError('Titel oder Artikel ungültig.')
    store.stage(job,'editorial_preflight',editorial_mode=True,editorial_notes=payload.get('notes',[]))
    cast=engine.existing_cast(req['figuren_ids'])+copy.deepcopy(payload.get('characters',[]))
    if not 1<=len(cast)<=8 or any(not ID.fullmatch(c.get('id','')) for c in cast) or len({c['id'] for c in cast})!=len(cast):raise ValueError('Eindeutige Figuren-IDs erforderlich.')
    for c in cast:
        if c['id'] in payload.get('outfits',{}):c['story_outfit']=payload['outfits'][c['id']]
    # Keep already-generated private portrait references across editorial revisions.
    saved=store.directory(job)/'characters.json'
    if saved.exists():
        old={c['id']:c for c in json.loads(saved.read_text())}
        for c in cast:
            if c['id'] in old and old[c['id']].get('inline_references'):c['inline_references']=old[c['id']]['inline_references']
    overrides=payload.get('reference_overrides',{})
    if not isinstance(overrides,dict) or set(overrides)-{c['id'] for c in cast}:raise ValueError('Unbekannte Figurenreferenz.')
    for c in cast:
        if c['id'] in overrides:
            images=overrides[c['id']]
            if not isinstance(images,list) or not 1<=len(images)<=2 or any(not isinstance(image,str) or len(image)>8_000_000 or not base64.b64decode(image,validate=True).startswith(b'\x89PNG\r\n\x1a\n') for image in images):raise ValueError('Ungültige eingebettete Porträtreferenz.')
            c['inline_references']=images;c['references']=[]
    from panel_formats import apply
    payload=copy.deepcopy(payload)
    keep_legacy=bool(previous and previous.get('improvement_mode') and not any(s.get('canvas_size') for s in payload['scenes']))
    scenes=engine.validate_scenes(payload['scenes'] if keep_legacy else apply(payload['scenes'],payload.get('page_template','standard')),req['kacheln'],cast)
    from lettering_plan import prepare,accept_preflight,record
    scenes,lettering_report=prepare(scenes,cast)
    payload['scenes']=scenes
    plan={'source_hash':hashlib.sha256(json.dumps([doc['story'].strip(),req['kacheln'],req['seed']],ensure_ascii=False).encode()).hexdigest(),'scenes':scenes}
    revisions=payload.get('revisions',{})
    if not isinstance(revisions,dict) or any(not str(k).isdigit() or not 0<=int(k)<req['kacheln'] or type(v) is not int or v<0 for k,v in revisions.items()):raise ValueError('Ungültige Kachelrevisionen.')
    fit=engine.preflight(plan,cast)
    accept_preflight(scenes,fit,lettering_report)
    record(store,job,lettering_report)
    store.write(job,'story.json',doc);store.write(job,'scenes.json',plan);store.write(job,'editorial-source.json',payload)
    store.stage(job,'editorial_characters')
    needed={ident for scene in scenes for ident in scene['characters']}
    needed.update(bubble['speaker'] for scene in scenes for bubble in scene['bubbles'])
    for index,c in enumerate(cast):
        if c['id'] in needed and not c.get('inline_references'):c['inline_references']=[engine.portrait(job,c,index,req['stil'])]
    store.write(job,'characters.json',cast)
    digest=hashlib.sha256(json.dumps([doc,plan,revisions,cast,engine.loaders],sort_keys=True).encode()).hexdigest()[:16]
    store.stage(job,'editorial_rendering')
    output=engine.studio(job,'editor-render-'+digest,doc,cast,plan,revisions)
    if len(output.get('images',[]))!=1 or len(output.get('comic_panels',[]))!=req['kacheln']:raise ValueError('Unvollständige Comicausgabe.')
    store.write(job,'comic.png',client.download(job,output['images'][0]))
    for index,panel in enumerate(output['comic_panels']):
        store.write(job,f'panels/{index+1:02}_panel.png',client.download(job,panel))
        store.write(job,f'panels/{index+1:02}_art.png',client.download(job,{**panel,'filename':panel['filename'].replace('_panel.png','_art.png')}))
    store.write(job,'workflow.json',engine.workflow(req,doc,cast,plan,revisions))
    if worker and not output.get('local_layout') and payload.get('page_template','standard')=='standard':
        # Same layout code as the host export; the helper only writes into this session.
        layout_source={k:v for k,v in payload.items() if k not in ('characters','article','notes','outfits')}
        layout=client.request('POST','/dgx-comics/automation/layout',{'session':job,'source':layout_source,
            'workflow':engine.workflow(req,doc,cast,plan,revisions),'image':output['images'][0],'panels':output['comic_panels']})
        for artifact in layout['files']:
            path=Path(artifact['name'])
            if path.is_absolute() or '..' in path.parts:raise ValueError('Ungültiger Layoutpfad.')
            kind={'.png':'png','.pdf':'pdf','.json':'json','.txt':'text'}.get(path.suffix)
            if not kind:raise ValueError('Unbekanntes Layoutformat.')
            store.write(job,str(path),client.download(job,artifact['image'],kind=kind))
    if worker and (output.get('local_layout') or payload.get('page_template','standard')!='standard'):
        from lettering import LAYOUT,DESIGN
        LAYOUT.render_layout(store.directory(job),payload,engine.workflow(req,doc,cast,plan,revisions),DESIGN)
    if review_engine is not None:
        from equipment_review import audit
        audit(review_engine,job,cast,scenes)
    store.write(job,'report.json',{'editorial_mode':True,'text_rewritten_by_local_llm':False,'fiction':False,
        'source':'Vom Nutzer bereitgestellter Artikel','story_language':'de','lettering':fit,'lettering_layout':lettering_report,'notes':payload.get('notes',[]),'visual_review':'pending'})
    store.stage(job,'editorial_review',artifacts=export(store,job))
    return job


def finalize(store,client,job,review):
    doc=store.get(job)
    if not doc or doc['status']!='editing':raise ValueError('Kein offener Redaktionsauftrag.')
    if not any(a['name']=='comic.png' for a in doc['artifacts']):raise ValueError('Comic fehlt.')
    report_path=store.directory(job)/'report.json';report=json.loads(report_path.read_text())
    if doc.get('equipment_unresolved'):raise ValueError('Zusätzliche Schwerter erkannt. Erst die Bilder korrigieren.')
    if doc.get('lettering_unresolved'):raise ValueError('Entwurf: Zuerst die Beschriftung korrigieren.')
    report['visual_review']=review;store.write(job,'report.json',report)
    store.stage(job,'finished',status='completed',artifacts=export(store,job),cleanup_pending=True)
    client.cleanup(job)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('source',nargs='?');parser.add_argument('--job');parser.add_argument('--finalize',action='store_true');parser.add_argument('--review',default='Redaktionell geprüft.')
    args=parser.parse_args();job=args.job or uuid.uuid4().hex
    if not ID.fullmatch(job):raise ValueError('Ungültige Auftrags-ID.')
    store=Store(os.getenv('DATA_DIR','/data'));client=Comfy(os.getenv('COMFYUI_URL','http://comfyui:8188'),store)
    if args.finalize:finalize(store,client,job,args.review)
    else:
        if not args.source:parser.error('Storyboard-JSON erforderlich.')
        template=os.getenv('WORKFLOW_TEMPLATE','/app/workflow_template.json')
        reviewer=Engine(store,client,template,os.getenv('TEXT_MODEL','qwen3vl_8b_fp8_scaled.safetensors'),os.getenv('VISION_MODEL','qwen3vl_8b_fp8_scaled.safetensors'))
        backend=os.getenv('LLM_BACKEND','comfyui')
        if backend not in ('comfyui','ollama'):raise ValueError('Nur lokale Modelle erlaubt.')
        if backend=='ollama':
            from local_llm import LocalOllama
            reviewer.llm=LocalOllama(os.getenv('OLLAMA_URL','http://host.docker.internal:11434'),store,os.getenv('OLLAMA_TEXT_MODEL','gemma3:27b'),os.getenv('OLLAMA_CRITIC_MODEL','qwen3.6:35b-a3b'),os.getenv('OLLAMA_VISION_MODEL','qwen3.6:35b-a3b'))
        render(store,client,template,json.loads(Path(args.source).read_text()),job,review_engine=reviewer)
    print(json.dumps({'id':job,'status':store.get(job)['status']},ensure_ascii=False))


if __name__=='__main__':main()
