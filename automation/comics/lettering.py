"""Sprechblasen auf vorhandenen Zeichnungen setzen: CPU, keine Modellaufrufe."""
import base64
import copy
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import uuid

from stories import Conflict


def core(name):
    root=Path('/app/comic-design')
    if not root.exists():root=Path(__file__).resolve().parents[2]/'extensions/dgx-comics'
    spec=importlib.util.spec_from_file_location('lettering_'+name,root/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


DESIGN=core('design');LAYOUT=core('editorial_layout')


def source(store,job):
    if job['status'] not in ('completed','needs_review','editing'):raise Conflict('Zuerst die Comic-Erzeugung abschließen.')
    root=store.directory(job['id']);names={a['name'] for a in job.get('artifacts',[])}
    if (root/'editorial-source.json').exists():value=json.loads((root/'editorial-source.json').read_text())
    else:
        story=json.loads((root/'story.json').read_text());plan=json.loads((root/'scenes.json').read_text())
        value={'title':story['title'],'article':story['story'],'style':job['request']['stil'],'scenes':plan['scenes'],'page_template':job['request'].get('page_template','standard')}
    value['characters']=json.loads((root/'characters.json').read_text())
    if len(value['scenes'])<1:raise ValueError('Ungültige Kachelzahl.')
    for index in range(len(value['scenes'])):
        name=f'panels/{index+1:02}_art.png'
        if name not in names or not(root/name).is_file():raise ValueError('Die unbeschriftete Originalzeichnung fehlt für Kachel '+str(index+1)+'.')
    version=hashlib.sha256(json.dumps([value,[(a['name'],a.get('sha256')) for a in job['artifacts']]],sort_keys=True).encode()).hexdigest()
    return value,version


def manifest(store,job):
    value,version=source(store,job)
    return {'job_id':job['id'],'version':version,'title':value['title'],'characters':[{'id':c['id'],'name':c['name']} for c in value['characters']],
            'panels':[{'canvas_size':s.get('canvas_size',[768,672]),'story':s['story'],'dialog':s.get('dialog',''),'bubbles':s.get('bubbles',[]),'protected_areas':s.get('protected_areas',[])} for s in value['scenes']]}


def area(value):
    if not isinstance(value,dict):raise ValueError('Ungültiger geschützter Bereich.')
    result={k:value.get(k) for k in ('x','y','w','h')}
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in result.values()):raise ValueError('Ungültige Bereichskoordinaten.')
    if result['x']<0 or result['y']<0 or result['w']<=0 or result['h']<=0 or result['x']+result['w']>1 or result['y']+result['h']>1:raise ValueError('Geschützter Bereich muss innerhalb der Kachel liegen.')
    return result


def panel(value,cast):
    if not isinstance(value,dict) or set(value)-{'dialog','bubbles','protected_areas','canvas_size'}:raise ValueError('Nur Erzählertext, Sprechblasen und geschützte Bereiche ändern.')
    if 'canvas_size' in value:DESIGN.validate_canvas_size(value['canvas_size'])
    caption=value.get('dialog','')
    if not isinstance(caption,str) or len(caption)>400:raise ValueError('Erzählertext maximal 400 Zeichen.')
    bubbles=DESIGN.validate_bubbles(value.get('bubbles',[]));known={c['id'] for c in cast}
    if any(b['speaker'] not in known for b in bubbles):raise ValueError('Sprechblase braucht eine bekannte Figur.')
    areas=value.get('protected_areas',[])
    if not isinstance(areas,list) or len(areas)>16:raise ValueError('Maximal 16 geschützte Bereiche.')
    return {'dialog':caption,'bubbles':bubbles,'protected_areas':[area(a) for a in areas]}


def intersects(a,b):
    return a['x']<b['x']+b['w']-.0001 and a['x']+a['w']>b['x']+.0001 and a['y']<b['y']+b['h']-.0001 and a['y']+a['h']>b['y']+.0001


def contains(rect,x,y):
    return rect['x']<x<rect['x']+rect['w'] and rect['y']<y<rect['y']+rect['h']


def issues(value,canvas_size=None):
    size=DESIGN.validate_canvas_size(canvas_size) if canvas_size else (768,672)
    result=[];bubbles=value['bubbles']
    for i,b in enumerate(bubbles):
        if contains(b,b['tip_x'],b['tip_y']):result.append(f'Sprechblase {i+1}: Schweifspitze liegt in der Blase. Den gelben Punkt zur Figur ziehen.')
        if b['x']<.005 or b['y']<.005 or b['x']+b['w']>.995 or b['y']+b['h']>.995:result.append(f'Sprechblase {i+1}: mehr Abstand zum Kachelrand lassen.')
        if intersects(b,{'x':.01,'y':.01,'w':.07,'h':.085}):result.append(f'Sprechblase {i+1} verdeckt die Kachelnummer.')
        if value['dialog'] and b['y']<DESIGN.caption_band(value['dialog'],size)/size[1]+.01:result.append(f'Sprechblase {i+1} verdeckt den Erzählerkasten.')
        if any(intersects(b,a) for a in value['protected_areas']):result.append(f'Sprechblase {i+1} verdeckt einen geschützten Bereich.')
        for j,other in enumerate(bubbles[:i]):
            if intersects(b,other):result.append(f'Sprechblasen {j+1} und {i+1} überlappen.')
    return result


def art(store,job,index):
    from PIL import Image
    with Image.open(store.directory(job['id'])/f'panels/{index+1:02}_art.png') as im:
        if im.width*im.height>25_000_000:raise ValueError('Originalzeichnung zu groß.')
        return im.convert('RGB')


def encoded(image):
    out=io.BytesIO();image.save(out,format='PNG');return base64.b64encode(out.getvalue()).decode()


def preview(store,job,value):
    original,version=source(store,job)
    if value.get('version')!=version:raise Conflict('Ausgabe wurde geändert. Positionierung neu öffnen.')
    index=value.get('panel')
    if type(index) is not int or not 0<=index<len(original['scenes']):raise ValueError('Ungültige Kachel.')
    layout=value.get('layout')
    if isinstance(layout,dict) and 'canvas_size' in layout and DESIGN.validate_canvas_size(layout['canvas_size'])!=tuple(original['scenes'][index].get('canvas_size',[768,672])):raise ValueError('Das Kachelformat wird durch die Seitenvorlage festgelegt.')
    p=panel(value.get('layout'),original['characters']);image=art(store,job,index);names={c['id']:c['name'] for c in original['characters']}
    size=original['scenes'][index].get('canvas_size');background=DESIGN.panel(image,p['dialog'],index+1,[],names,canvas_size=size);problems=issues(p,size);png=None
    try:png=encoded(DESIGN.panel(image,p['dialog'],index+1,p['bubbles'],names,canvas_size=size))
    except ValueError as exc:problems.append(str(exc)+' Blase vergrößern oder den Text aufteilen.')
    return {'valid':not problems,'issues':problems,'background':encoded(background),'png':png,'layout':p}


def automatic(store,job,value):
    from PIL import ImageFilter,ImageStat
    original,version=source(store,job)
    if value.get('version')!=version:raise Conflict('Ausgabe wurde geändert. Positionierung neu öffnen.')
    index=value.get('panel')
    if type(index) is not int or not 0<=index<len(original['scenes']):raise ValueError('Ungültige Kachel.')
    p=panel(value.get('layout'),original['characters']);names={c['id']:c['name'] for c in original['characters']}
    size=original['scenes'][index].get('canvas_size');blank=DESIGN.panel(art(store,job,index),p['dialog'],index+1,[],names,canvas_size=size);edges=blank.convert('L').filter(ImageFilter.FIND_EDGES)
    placed=[];last=(-1,-1)
    for b in p['bubbles']:
        options=[];w=max(.32,min(.47,b['w']));h=max(.20,min(.28,b['h']))
        for y in (.24,.49,.72) if p['dialog'] else (.11,.37,.65):
            for x in (.02,.51):
                candidate={**b,'x':x,'y':y,'w':w,'h':h}
                if y+h>.99 or (y,x)<last or any(contains(candidate,other['tip_x'],other['tip_y']) for other in p['bubbles']) or any(intersects(candidate,a) for a in [*p['protected_areas'],*placed]):continue
                try:DESIGN.panel(blank,'',index+1,[candidate],names,canvas_size=size)
                except ValueError:continue
                score=ImageStat.Stat(edges.crop((int(x*blank.width),int(y*blank.height),int((x+w)*blank.width),int((y+h)*blank.height)))).mean[0]
                score+=abs(x+w/2-b['tip_x'])*12+y*1000
                options.append((score,candidate))
        if not options:raise ValueError('Keine passende freie Position gefunden. Blasen manuell anpassen oder geschützte Bereiche prüfen.')
        chosen=min(options,key=lambda item:item[0])[1];placed.append(chosen);last=(chosen['y'],chosen['x'])
    p['bubbles']=placed
    return preview(store,job,{'version':version,'panel':index,'layout':p})


def enqueue(store,job,value):
    original,version=source(store,job)
    if not isinstance(value,dict) or set(value)-{'version','panels'} or value.get('version')!=version:raise Conflict('Ausgabe wurde geändert. Positionierung neu öffnen.')
    patches=value.get('panels')
    if not isinstance(patches,list) or len(patches)!=len(original['scenes']):raise ValueError('Alle Kacheln mit unveränderter Anzahl senden.')
    for i,patch in enumerate(patches):
        result=preview(store,job,{'version':version,'panel':i,'layout':patch})
        if not result['valid']:raise ValueError('Kachel '+str(i+1)+': '+' '.join(result['issues']))
        original['scenes'][i].update(result['layout'])
    ident=uuid.uuid4().hex;store.create(ident,copy.deepcopy(job['request']),initial_status='editing')
    root=store.directory(ident);parent=store.directory(job['id'])
    try:
        for name in ('characters.json','workflow.json','story.json'):
            if (parent/name).exists():store.write(ident,name,(parent/name).read_bytes())
        for i in range(len(patches)):store.write(ident,f'panels/{i+1:02}_art.png',(parent/f'panels/{i+1:02}_art.png').read_bytes())
        store.write(ident,'editorial-source.json',original)
        store.update(ident,lettering_mode=True,parent_job=job['id'],editorial_mode=True,story_id=job.get('story_id'),story_version=job.get('story_version'),story_title=original['title'])
        store.stage(ident,'queued',status='queued')
    except Exception:
        store.stage(ident,'failed',status='failed',error='Beschriftung konnte nicht vorbereitet werden.');raise
    return store.get(ident)


def render(store,job):
    from PIL import Image
    from editorial import export
    root=store.directory(job);value=json.loads((root/'editorial-source.json').read_text());cast=value['characters'];names={c['id']:c['name'] for c in cast};tiles=[]
    store.stage(job,'lettering_rendering')
    for i,scene in enumerate(value['scenes']):
        p=panel({k:scene.get(k,[] if k!='dialog' else '') for k in ('dialog','bubbles','protected_areas')},cast)
        size=scene.get('canvas_size')
        if issues(p,size):raise ValueError('Kachel '+str(i+1)+': '+' '.join(issues(p,size)))
        with Image.open(root/f'panels/{i+1:02}_art.png') as image:tile=DESIGN.panel(image,p['dialog'],i+1,p['bubbles'],names,canvas_size=size)
        tile.save(root/f'panels/{i+1:02}_panel.png');
        if len(tiles)<12:tiles.append(tile)
    DESIGN.assemble_preview(tiles,min(3,len(tiles)),value['title'],value.get('signature',''),len(value['scenes'])).save(root/'comic.png')
    workflow=json.loads((root/'workflow.json').read_text()) if (root/'workflow.json').exists() else {'nodes':[]}
    # Aktualisierte Metadaten, aber keine gespeicherten ComfyUI-Workflows ändern.
    workflow.setdefault('extra',{})['lettering_only']={'parent_job':store.get(job)['parent_job'],'scenes':value['scenes']}
    for node in workflow.get('nodes',[]):
        if node.get('type')=='DGXComicStudio':
            node.setdefault('properties',{})['lettering_only_export']=True
            if len(node.get('widgets_values',[]))>=9:node['widgets_values'][8]=json.dumps({'scenes':value['scenes']},ensure_ascii=False)
    LAYOUT.render_layout(root,value,workflow,DESIGN)
    store.write(job,'README.txt',((root/'README.txt').read_text()+'\nDiese Fassung setzt ausschließlich die Beschriftung neu. Originalzeichnungen sind bytegleich übernommen. Kein Modellaufruf und keine neue Bildgenerierung.\n').encode())
    store.write(job,'scenes.json',{'scenes':value['scenes']})
    store.write(job,'lettering-report.json',{'image_generation':False,'model_calls':0,'original_art_preserved':True,'visual_review':'pending'})
    return {'status':'needs_review','artifacts':export(store,job),'warnings':['Nur Beschriftung geändert. Zeichnungen unverändert übernommen. Ergebnis vor Veröffentlichung prüfen.']}
