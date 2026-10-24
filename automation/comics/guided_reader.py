"""Geführte Leseansicht und gemeinsame Seiten für Vorschau, EPUB und Druck."""
import copy
import hashlib
import io
import json
from pathlib import Path
from PIL import Image
from stories import Conflict
from lettering import LAYOUT,DESIGN


def source(store,job):
    if job['status'] not in ('completed','needs_review'):raise Conflict('Zuerst eine fertige Comic-Ausgabe auswählen.')
    root=store.directory(job['id']);path=root/'editorial-source.json'
    if path.exists():src=json.loads(path.read_text())
    else:
        src={'title':json.loads((root/'story.json').read_text())['title'],'scenes':json.loads((root/'scenes.json').read_text())['scenes'],'page_template':job['request'].get('page_template','standard')}
    return src,[root/f'panels/{i+1:02}_panel.png' for i in range(len(src['scenes']))]


def pages_for(src,panels,settings=None):
    template=LAYOUT.validate_template(src.get('page_template','standard'));template='four_grid' if template=='standard' else template
    per=LAYOUT.TEMPLATES[template]['count'];pages=[]
    for start in range(0,len(panels),per):
        sizes=[]
        for path in panels[start:start+per]:
            with Image.open(path) as im:sizes.append(im.size)
        page={'id':start//per+1,'template':template,**LAYOUT.template_geometry(sizes,template)}
        for i,r in enumerate(page['regions']):r.update(panel=start+i+1,ordinal=i+1)
        pages.append(page)
    if settings:
        order=settings.get('page_order',[p['id'] for p in pages]);lookup={p['id']:p for p in pages}
        if not isinstance(order,list) or not order or any(type(i) is not int or i not in lookup for i in order) or len(set(order))!=len(order):raise ValueError('Mindestens eine vorhandene Seite in eindeutiger Reihenfolge auswählen.')
        panel_orders=settings.get('panel_orders',{})
        if not isinstance(panel_orders,dict) or set(panel_orders)-{str(p['id']) for p in pages}:raise ValueError('Unbekannte Seite in der Panelreihenfolge.')
        for key,order_panels in panel_orders.items():
            p=lookup[int(key)];known={r['panel'] for r in p['regions']}
            if not isinstance(order_panels,list) or any(type(i) is not int for i in order_panels) or len(order_panels)!=len(known) or set(order_panels)!=known:raise ValueError('Alle Kacheln der Seite genau einmal in Lesereihenfolge angeben.')
            for r in p['regions']:r['ordinal']=order_panels.index(r['panel'])+1
        pages=[lookup[i] for i in order]
    return pages


def render_page(src,panels,page):
    images=[]
    try:
        for r in page['regions']:
            with Image.open(panels[r['panel']-1]) as im:images.append(im.convert('RGB'))
        return LAYOUT.assemble_template(images,page['template'],src['title']+' · '+str(page['id']),src.get('signature',''),DESIGN)
    finally:
        for im in images:im.close()


def manifest(store,job):
    src,panels=source(store,job);saved=store.integration_get('reader-'+job['id']) or {};pages=pages_for(src,panels,saved)
    default=pages_for(src,panels);state={'page_order':[p['id'] for p in pages],'panel_orders':{str(p['id']):[r['panel'] for r in sorted(p['regions'],key=lambda r:r['ordinal'])] for p in default}}
    for key,order in saved.get('panel_orders',{}).items():state['panel_orders'][key]=copy.deepcopy(order)
    # Versionsprüfung schützt gespeicherte Reihenfolgen vor parallelen Änderungen.
    version=hashlib.sha256(json.dumps([src,state],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    all_geometry=pages_for(src,panels,{'panel_orders':saved.get('panel_orders',{})})
    for page in all_geometry:page['url']=f'/jobs/{job["id"]}/reader/pages/{page["id"]}.png'
    return {'job_id':job['id'],'title':src['title'],'version':version,'page_template':src.get('page_template','standard'),'pages':all_geometry,'settings':state,'all_pages':[{'id':p['id'],'panels':[r['panel'] for r in p['regions']]} for p in default]}


def save(store,job,value):
    if not isinstance(value,dict) or set(value)-{'version','page_order','panel_orders'}:raise ValueError('Nur Leseordnung und Version senden.')
    current=manifest(store,job)
    if value.get('version')!=current['version']:raise Conflict('Leseordnung wurde geändert. Vorschau neu öffnen.')
    src,panels=source(store,job);clean={k:copy.deepcopy(value.get(k,current['settings'][k])) for k in ('page_order','panel_orders')};pages_for(src,panels,clean)
    store.integration_set('reader-'+job['id'],clean);return manifest(store,job)


def image(store,job,index):
    src,panels=source(store,job);pages=pages_for(src,panels)
    page=next((p for p in pages if p['id']==index),None)
    if page is None:raise KeyError(index)
    im=render_page(src,panels,page);data=io.BytesIO();im.save(data,format='PNG');im.close();return data.getvalue()


def export_pages(folder,src,panels,settings=None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);pages=pages_for(src,panels,settings)
    for i,page in enumerate(pages):
        page['filename']=f'comic-{i+1:04}.png'
        im=render_page(src,panels,page);im.save(folder/page['filename']);im.close()
    return pages
