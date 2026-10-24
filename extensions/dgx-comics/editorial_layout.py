"""Gemeinsames Seitenlayout für Hostskript und redaktionelle Webausgaben."""
import base64
import io
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
from PIL.PngImagePlugin import PngInfo


def _rows(rows):
    total=sum(height for height,widths in rows);y=0;slots=[]
    for height,widths in rows:
        x=0;den=sum(widths)
        for width in widths:
            slots.append([x/den,y/total,width/den,height/total]);x+=width
        y+=height
    return slots


# Leserichtung: zeilenweise links nach rechts. Rechtecke bleiben überschneidungsfrei.
_LAYOUT_ROWS=[
 ('single','Ganzseite','Einzelbilder',[(1,[1])]),
 ('duo_horizontal','Zwei nebeneinander','Klassisch',[(1,[1,1])]),
 ('duo_vertical','Zwei übereinander','Filmisch',[(1,[1]),(1,[1])]),
 ('triple_strip','Drei als Zeitungsstrip','Zeitungscomic',[(1,[1,1,1])]),
 ('triple_vertical','Drei breite Einstellungen','Filmisch',[(1,[1]),(1,[1]),(1,[1])]),
 ('hero_top','Großer Auftakt','Dramatisch',[(2,[1]),(1,[1,1])]),
 ('hero_bottom','Großes Finale','Dramatisch',[(1,[1,1]),(2,[1])]),
 ('four_grid','Vier gleich große Kacheln','Klassisch',[(1,[1,1]),(1,[1,1])]),
 ('four_strips','Vier filmische Streifen','Filmisch',[(1,[1]),(1,[1]),(1,[1]),(1,[1])]),
 ('four_top','Panorama und drei Details','Dramatisch',[(2,[1]),(1,[1,1,1])]),
 ('four_bottom','Drei Details und Panorama','Dramatisch',[(1,[1,1,1]),(2,[1])]),
 ('four_alternate','Wechselnde Gewichte','Dynamisch',[(1,[2,1]),(1,[1,2])]),
 ('five_focus','Fünf mit zentralem Panorama','Dramatisch',[(1,[1,1]),(2,[1]),(1,[1,1])]),
 ('five_open','Fünf mit großem Auftakt','Dramatisch',[(2,[1]),(1,[1,1]),(1,[1,1])]),
 ('five_close','Fünf mit großem Finale','Dramatisch',[(1,[1,1]),(1,[1,1]),(2,[1])]),
 ('five_rhythm','Zwei, drei – schneller Rhythmus','Dynamisch',[(1,[1,1]),(1,[1,1,1])]),
 ('six_classic','Sechs – klassisches Album','Klassisch',[(1,[1,1]),(1,[1,1]),(1,[1,1])]),
 ('six_landscape','Sechs – Querformat','Klassisch',[(1,[1,1,1]),(1,[1,1,1])]),
 ('six_action','Sechs – wechselnde Akzente','Dynamisch',[(1,[2,1]),(1,[1,2]),(1,[2,1])]),
 ('six_open','Panorama, Details, Dreierfolge','Dynamisch',[(2,[1]),(1,[1,1]),(1,[1,1,1])]),
 ('six_close','Dreierfolge, Details, Finale','Dynamisch',[(1,[1,1,1]),(1,[1,1]),(2,[1])]),
 ('seven_open','Sieben mit großem Auftakt','Album',[(2,[1]),(1,[1,1,1]),(1,[1,1,1])]),
 ('seven_close','Sieben mit großem Finale','Album',[(1,[1,1,1]),(1,[1,1,1]),(2,[1])]),
 ('seven_middle','Sieben mit ruhiger Mitte','Album',[(1,[1,1,1]),(2,[1]),(1,[1,1,1])]),
 ('eight_classic','Acht – europäisches Album','Album',[(1,[1,1]),(1,[1,1]),(1,[1,1]),(1,[1,1])]),
 ('eight_rhythm','Acht – verdichtete Handlung','Album',[(1,[1,1,1]),(1,[1,1]),(1,[1,1,1])]),
 ('nine_grid','Neun – regelmäßiges Raster','Album',[(1,[1,1,1]),(1,[1,1,1]),(1,[1,1,1])]),
 ('nine_rhythm','Neun – wechselnder Takt','Album',[(1,[2,1]),(1,[1,1,1]),(1,[1,2]),(1,[1,1])]),
 ('scroll_short','Scrollcomic – kurze Folge','Webcomic',[(1,[1])]*4),
 ('scroll_long','Scrollcomic – lange Folge','Webcomic',[(1,[1])]*6),
 ('cinema_pause','Filmisch mit langer Ruhe','Filmisch',[(1,[1]),(2,[1]),(1,[1])]),
 ('cinema_finale','Filmisch mit Schlussbild','Filmisch',[(1,[1]),(1,[1]),(2,[1])]),
]
TEMPLATES={'standard':{'id':'standard','name':'Bisheriges Layout','category':'Klassisch','slots':_rows([(1,[1,1]),(1,[1,1])]),'count':4}}
for _id,_name,_category,_spec in _LAYOUT_ROWS:
    _slots=_rows(_spec)
    TEMPLATES[_id]={'id':_id,'name':_name,'category':_category,'slots':_slots,'count':len(_slots)}


def validate_template(value):
    if not isinstance(value,str) or value not in TEMPLATES:raise ValueError('Unbekannte Comic-Seitenvorlage.')
    return value


def assemble_template(tiles,template,title,signature,design):
    import math
    template=TEMPLATES[validate_template(template)];slots=template['slots']
    if not tiles or len(tiles)>len(slots):raise ValueError('Ungültige Kachelanzahl für die Seitenvorlage.')
    # Fertig beschriftete Kacheln niemals beschneiden oder kleiner als das Original setzen.
    width=max(1560,max(math.ceil((tile.width+24)/slot[2]) for tile,slot in zip(tiles,slots)))
    content_h=max(1400,max(math.ceil((tile.height+24)/slot[3]) for tile,slot in zip(tiles,slots)))
    page=Image.new('RGB',(width+40,content_h+155),'white');draw=ImageDraw.Draw(page)
    design.lettering(draw,title,(20,15,width+20,75),42)
    for tile,(x,y,w,h) in zip(tiles,slots):
        box=(20+round(x*width)+6,90+round(y*content_h)+6,20+round((x+w)*width)-6,90+round((y+h)*content_h)-6)
        fitted=ImageOps.contain(tile,(box[2]-box[0]-4,box[3]-box[1]-4),Image.Resampling.LANCZOS)
        page.paste(fitted,(box[0]+(box[2]-box[0]-fitted.width)//2,box[1]+(box[3]-box[1]-fitted.height)//2))
        draw.rectangle(box,outline='#172535',width=2)
    if signature:design.lettering(draw,signature,(20,content_h+102,width+20,content_h+145),27)
    return page


def decorate_tiles(tiles,source,design):
    if source.get('narrator_badge'):
        ident=source.get('narrator_character_id') or next(iter(source.get('library_ids',[])),None)
        if not ident or not source.get('reference_overrides',{}).get(ident):raise ValueError('Referenzbild für das Erzählerporträt fehlt.')
        avatar=Image.open(io.BytesIO(base64.b64decode(source['reference_overrides'][ident][0]))).convert('RGB')
        avatar=ImageOps.fit(avatar,(48,48),Image.Resampling.LANCZOS)
        font=ImageFont.truetype(str(design.FONT),11);font.set_variation_by_axes([750])
        for tile in tiles:
            tile.paste(avatar,(10,66));draw=ImageDraw.Draw(tile)
            draw.rectangle((9,65,58,114),outline='#172535',width=1)
            draw.text((12,119),'SYSOP',font=font,fill='#172535')


def render_layout(output,source,workflow,design,decorate=True):
    output=Path(output)
    metadata=PngInfo()
    with Image.open(output/'comic.png') as original:
        for key,value in original.info.items():
            if isinstance(value,str):metadata.add_text(key,value)
    template=validate_template(source.get('page_template','standard'));per_page=TEMPLATES[template]['count']
    count_panels=len(source['scenes'])
    def read_tile(i):
        with Image.open(output/f'panels/{i+1:02}_panel.png') as im:return im.convert('RGB')
    layout_info={'narrator_badge':bool(source.get('narrator_badge')),'reproduce':'scripts/layout_editorial_comic.py','page_template':template,'panels_per_sharing_page':per_page,'overview_is_preview':count_panels>(12 if template=='standard' else per_page)}
    workflow.setdefault('extra',{})['editorial_layout']=layout_info
    for node in workflow.get('nodes',[]):
        if node.get('type')=='Note':
            node['widgets_values']=['Redaktioneller Comic: Szenen und Texte unverändert rendern. Das Exportskript scripts/layout_editorial_comic.py ergänzt das Sysop-Porträt in der Kopfleiste und die Druck-/Teilseiten. Figurenreferenzen sind eingebettet.']
            break
    (output/'workflow.json').write_text(json.dumps(workflow,ensure_ascii=False,indent=2)+'\n')
    metadata.add_text('workflow',json.dumps(workflow,ensure_ascii=False));metadata.add_text('editorial_layout',json.dumps(layout_info))
    tile_metadata=metadata
    if count_panels>12:
        tile_metadata=PngInfo();tile_metadata.add_text('editorial_layout',json.dumps(layout_info))
    for i in range(count_panels):
        tile=read_tile(i)
        if decorate:decorate_tiles([tile],source,design)
        tile.save(output/f'panels/{i+1:02}_panel.png',pnginfo=tile_metadata)
    preview=[read_tile(i) for i in range(min(12,count_panels))]
    design.assemble_preview(preview,min(3,count_panels),source['title'],source.get('signature',''),count_panels).save(output/'comic.png',pnginfo=metadata)
    del preview
    pages=[];(output/'pages').mkdir(exist_ok=True)
    for stale in (output/'pages').glob('*.png'):
        if stale.stem.isdecimal():stale.unlink()
    count=(count_panels+per_page-1)//per_page
    for start in range(0,count_panels,per_page):
        group=[read_tile(i) for i in range(start,min(start+per_page,count_panels))]
        title=f'{source["title"]} · {start//per_page+1}/{count}'
        page=design.assemble(group,2,title,source.get('signature','')) if template=='standard' else assemble_template(group,template,title,source.get('signature',''),design)
        if start==0 and template!='standard':page.save(output/'comic.png',pnginfo=metadata)
        path=output/f'pages/{start//per_page+1:02}.png';page.save(path,pnginfo=tile_metadata);pages.append(path)
    try:
        from reportlab.pdfgen.canvas import Canvas
        pdf=Canvas(str(output/'comic.pdf'))
        for path in pages:
            with Image.open(path) as im:w,h=im.size
            pdf.setPageSize((w/2,h/2));pdf.drawImage(str(path),0,0,width=w/2,height=h/2);pdf.showPage()
        pdf.save()
    except ImportError:
        opened=[Image.open(path) for path in pages]
        try:opened[0].save(output/'comic.pdf','PDF',resolution=144,save_all=True,append_images=opened[1:])
        finally:
            for im in opened:im.close()
    (output/'README.txt').write_text('Redaktioneller Comic auf Basis des bereitgestellten Artikels.\ncomic.png: Übersicht bzw. erste Vorlagenseite. pages/: vollständige Teilseiten zum Teilen. comic.pdf: mehrseitige Fassung.\nworkflow.json: in ComfyUI öffnen, Figurenreferenzen sind eingebettet.\nDas Workflow-Rendering erzeugt die Illustrationen und Texte. scripts/layout_editorial_comic.py ergänzt das Erzähler-Porträt und die Druckseiten.\nPersonen sind symbolisch dargestellt; Angaben und Zeitbezüge stammen aus dem bereitgestellten Artikel.\n',encoding='utf-8')
    return {'panels':count_panels,'pages':len(pages)}
