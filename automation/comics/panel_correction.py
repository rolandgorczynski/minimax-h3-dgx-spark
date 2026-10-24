"""Eine ausgewählte Comiczeichnung korrigieren, alle anderen Dateien erhalten."""
import base64
import copy
import hashlib
import json
import os
import re
import secrets
import uuid

from engine import validate_request
from stories import Conflict
from lettering import source as original_source


def enqueue(store,parent,value):
    if not isinstance(value,dict) or set(value)-{'panel','correction','version'}:raise ValueError('Kachel und Korrekturtext senden.')
    if parent['status'] not in ('completed','needs_review'):raise Conflict('Zuerst die fertige Comic-Ausgabe auswählen.')
    source,version=original_source(store,parent)
    if value.get('version')!=version:raise Conflict('Die Ausgabe wurde geändert. Korrektur neu öffnen.')
    index=value.get('panel');text=value.get('correction')
    if type(index) is not int or not 0<=index<len(source['scenes']):raise ValueError('Eine vorhandene Kachel auswählen.')
    if not isinstance(text,str) or not text.strip() or len(text)>2000:raise ValueError('Korrektur mit 1–2000 Zeichen eingeben.')
    text=text.strip()
    mentioned={int(n) for n in re.findall(r'\b(?:Bild|Kachel|Panel)\s*(\d+)\b',text,re.I)}
    if mentioned and mentioned!={index+1}:raise ValueError('Korrekturtext nennt eine andere Kachel als die ausgewählte.')
    if any(j.get('panel_correction_mode') and j.get('parent_job')==parent['id'] and j.get('corrected_panel')==index+1 and j['status'] in ('queued','running') for j in store.list()):raise Conflict('Diese Kachel wird bereits korrigiert.')
    if source.get('narrator_badge') and source.get('library_ids'):source['narrator_character_id']=source['library_ids'][0]
    source['library_ids']=[];source['style']=parent['request']['stil'];source.setdefault('seed',parent['request']['seed']);source.setdefault('signature',parent['request']['signatur'])
    needed={i for s in source['scenes'] for i in s.get('characters',[])}|{b['speaker'] for s in source['scenes'] for b in s.get('bubbles',[])}
    if any(c['id'] in needed and not c.get('inline_references') for c in source['characters']):raise ValueError('Gespeicherte Figurenreferenzen fehlen; zuerst eine vollständige Ausgabe verwenden.')
    request=validate_request({'kacheln':len(source['scenes']),'stil':source['style'],'seed':source['seed'],'max_korrekturrunden':0,'signatur':source.get('signature','')})
    ident=uuid.uuid4().hex;store.create(ident,request,initial_status='editing');root=store.directory(parent['id'])
    try:
        for i in range(len(source['scenes'])):
            for kind in ('art','panel'):
                path=root/f'panels/{i+1:02}_{kind}.png'
                if not path.is_file():raise ValueError('Originalkachel fehlt.')
                store.write(ident,f'checkpoints/panel-originals/{i+1:02}_{kind}.png',path.read_bytes())
        store.write(ident,'panel-correction-input.json',{'source':source,'panel':index,'correction':text,'parent_job':parent['id'],'revision_increment':1+secrets.randbelow(1000000)})
        store.update(ident,panel_correction_mode=True,editorial_mode=True,parent_job=parent['id'],corrected_panel=index+1,story_id=parent.get('story_id'),story_version=parent.get('story_version'),story_title=source['title'])
        store.stage(ident,'queued',status='queued')
    except Exception:
        store.stage(ident,'failed',status='failed',error='Originalkacheln konnten nicht gesichert werden.');raise
    return store.get(ident)


def validate_proposal(value,before,cast,engine):
    if not isinstance(value,dict) or set(value)-{'story','character_states'}:raise ValueError('Nur Bildbeschreibung und sichtbaren Figurenzustand ändern.')
    if not isinstance(value.get('story'),str) or not value['story'].strip():raise ValueError('Konkrete Bildbeschreibung erforderlich.')
    result=copy.deepcopy(value);states=result.get('character_states',{})
    if not isinstance(states,dict):raise ValueError('Figurenzustände als Objekt mit exakten Figuren-IDs senden.')
    if set(states)-set(before.get('characters',[])):raise ValueError('Nur sichtbare Figuren dieser Kachel korrigieren; exakte Figuren-ID verwenden.')
    for ident,state in states.items():
        if isinstance(state,dict):
            # Lokale Modelle liefern oft Status/Details statt des angeforderten Klartexts.
            # Nur flache Textfelder verlustfrei verbinden; keine fremden IDs zuordnen.
            if not state or any(not isinstance(k,str) or not k.strip() or not isinstance(v,str) or not v.strip() for k,v in state.items()):
                raise ValueError('Figurenzustand als Text oder flaches Objekt mit Textfeldern senden.')
            states[ident]='; '.join(k+': '+v for k,v in state.items())
    result['character_states']=states
    candidate={**before,**result,'character_states':{**before.get('character_states',{}),**states}}
    engine.validate_scenes([candidate],1,cast)
    return result


def run(engine,ident):
    store=engine.store;root=store.directory(ident);snapshot=json.loads((root/'panel-correction-input.json').read_text());source=copy.deepcopy(snapshot['source']);index=snapshot['panel'];scene=source['scenes'][index];before=copy.deepcopy(scene);cast=source['characters']
    store.stage(ident,'panel_correction_planning')
    def validate(value):return validate_proposal(value,before,cast,engine)
    proposal=engine.json_call(ident,'panel-correction-plan',
        'Korrigiere ausschließlich die Bildkomposition der ausgewählten Comic-Kachel anhand des Nutzerwunsches und des vorhandenen Bildes. '
        'Keine neue Geschichte, keine Änderungen an anderen Kacheln, keine neuen Figuren. Gesicht und Identität bleiben erhalten. '
        'Erzählertext, Sprechblasen, Sprecher, Blasenstile und Kachelanzahl dürfen nicht verändert werden. '
        'Bei kürzeren Haaren oder anderer Kleidung den neuen konkreten sichtbaren Zustand in character_states für die richtige Figuren-ID festhalten. '
        'Dieser Zustand gilt nur für die ausgewählte Kachel und ändert die Figurenbibliothek nicht. '
        'Die vorhandene Szene beibehalten und nur die ausdrücklich verlangte Änderung deutlich in die Bildbeschreibung einarbeiten. '
        'character_states ist eine Zuordnung exakter sichtbarer Figuren-IDs zu je EINEM deutschen Text mit maximal 1000 Zeichen. '
        'Keine Namen als Schlüssel und keine verschachtelten Objekte verwenden. Bereits vorhandene Zustände erhalten. '
        'Return ONLY JSON {"story":"vollständige korrigierte Bildbeschreibung auf Deutsch","character_states":{"exakte Figuren-ID":"konkreter sichtbarer Zustand als Text"}}. Ohne Zustandsänderung character_states leer lassen. '
        '\nKACHEL:'+str(index+1)+'\nKORREKTUR:'+snapshot['correction']+
        '\nFIGUREN:'+json.dumps([{k:c.get(k,'') for k in ('id','name','description','outfit')} for c in cast],ensure_ascii=False)+
        '\nAKTUELLE SZENE:'+json.dumps(before,ensure_ascii=False),validate,
        images=[(root/f'checkpoints/panel-originals/{index+1:02}_art.png').read_bytes()],tokens=1400)
    scene['story']=proposal['story'];scene['character_states']={**before.get('character_states',{}),**proposal.get('character_states',{})}
    revisions=source.setdefault('revisions',{});revisions[str(index)]=revisions.get(str(index),0)+snapshot['revision_increment']
    from editorial import export
    from lettering import LAYOUT,DESIGN
    from PIL import Image
    fit=engine.preflight({'scenes':[scene]},cast)
    if not fit['valid']:raise ValueError('Beschriftung der ausgewählten Kachel passt nicht: '+json.dumps(fit['issues'],ensure_ascii=False))
    store.stage(ident,'panel_correction_rendering')
    # Der Graph enthält genau EINE Kachel. Es gibt keine übrigen Bilder zum Neuzeichnen.
    request=store.get(ident)['request'];single={**request,'kacheln':1,'seed':(request['seed']+index)%2147483648}
    plan={'source_hash':hashlib.sha256(json.dumps([source['article'].strip(),1,single['seed']],ensure_ascii=False).encode()).hexdigest(),'scenes':[scene]}
    doc={'title':source['title'],'story':source['article']}
    output=engine.studio(ident,'panel-correction-render',doc,cast,plan,{'0':revisions[str(index)]},request_override=single)
    if len(output.get('comic_panels',[]))!=1:raise ValueError('Genau eine korrigierte Zeichnung erwartet.')
    descriptor=output['comic_panels'][0]
    raw=engine.client.download(ident,{**descriptor,'filename':descriptor['filename'].replace('_panel.png','_art.png')})
    store.write(ident,f'panels/{index+1:02}_art.png',raw)
    import io
    with Image.open(io.BytesIO(raw)) as image:tile=DESIGN.panel(image,scene.get('dialog',''),index+1,scene.get('bubbles',[]),{c['id']:c['name'] for c in cast},canvas_size=scene.get('canvas_size'))
    LAYOUT.decorate_tiles([tile],source,DESIGN);tile.save(root/f'panels/{index+1:02}_panel.png')
    for i in range(len(source['scenes'])):
        if i==index:continue
        for kind in ('art','panel'):store.write(ident,f'panels/{i+1:02}_{kind}.png',(root/f'checkpoints/panel-originals/{i+1:02}_{kind}.png').read_bytes())
    store.write(ident,'story.json',{'title':source['title'],'story':source['article']})
    store.write(ident,'characters.json',cast);store.write(ident,'editorial-source.json',source)
    full_plan={'source_hash':hashlib.sha256(json.dumps([source['article'].strip(),len(source['scenes']),request['seed']],ensure_ascii=False).encode()).hexdigest(),'scenes':source['scenes']}
    store.write(ident,'scenes.json',full_plan)
    workflow=engine.workflow(request,doc,cast,full_plan,revisions)
    tiles=[]
    for i in range(min(12,len(source['scenes']))):
        with Image.open(root/f'panels/{i+1:02}_panel.png') as image:tiles.append(image.convert('RGB'))
    DESIGN.assemble_preview(tiles,min(3,len(tiles)),source['title'],source.get('signature',''),len(source['scenes'])).save(root/'comic.png')
    LAYOUT.render_layout(root,source,workflow,DESIGN,decorate=False)
    # Auch die PNG-Dateien der unberührten Kacheln bytegleich erhalten.
    for i in range(len(source['scenes'])):
        if i!=index:store.write(ident,f'panels/{i+1:02}_panel.png',(root/f'checkpoints/panel-originals/{i+1:02}_panel.png').read_bytes())
    store.write(ident,'panel-correction-report.json',{'parent_job':snapshot['parent_job'],'correction':snapshot['correction'],'rerendered_panels':[index+1],
        'retained_art_panels':[i+1 for i in range(len(source['scenes'])) if i!=index],'other_panel_files_identical':True,'before':before,'after':scene,'visual_review':'pending'})
    from equipment_review import audit
    audit(engine,ident,cast,source['scenes'])
    return {'status':'needs_review','artifacts':export(store,ident),'warnings':store.get(ident).get('equipment_warnings',[])+[f'Nur Kachel {index+1} neu gezeichnet. Andere Kacheln unverändert übernommen. Korrektur und Blasenpositionen bitte prüfen.']}
