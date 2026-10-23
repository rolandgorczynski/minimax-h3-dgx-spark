"""Gemeinsames Seitenlayout für Hostskript und redaktionelle Webausgaben."""
import base64
import io
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
from PIL.PngImagePlugin import PngInfo


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
    count_panels=len(source['scenes'])
    def read_tile(i):
        with Image.open(output/f'panels/{i+1:02}_panel.png') as im:return im.convert('RGB')
    layout_info={'narrator_badge':bool(source.get('narrator_badge')),'reproduce':'scripts/layout_editorial_comic.py','panels_per_sharing_page':4,'overview_is_preview':count_panels>12}
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
    count=(count_panels+3)//4
    for start in range(0,count_panels,4):
        group=[read_tile(i) for i in range(start,min(start+4,count_panels))]
        page=design.assemble(group,2,f'{source["title"]} · {start//4+1}/{count}',source.get('signature',''))
        path=output/f'pages/{start//4+1:02}.png';page.save(path,pnginfo=tile_metadata);pages.append(path)
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
    (output/'README.txt').write_text('Redaktioneller Comic auf Basis des bereitgestellten Artikels.\ncomic.png: alle Kacheln. pages/: Teilseiten zum Teilen. comic.pdf: mehrseitige Fassung.\nworkflow.json: in ComfyUI öffnen, Figurenreferenzen sind eingebettet.\nDas Workflow-Rendering erzeugt die Illustrationen und Texte. scripts/layout_editorial_comic.py ergänzt das Erzähler-Porträt und die Druckseiten.\nPersonen sind symbolisch dargestellt; Angaben und Zeitbezüge stammen aus dem bereitgestellten Artikel.\n',encoding='utf-8')
    return {'panels':count_panels,'pages':len(pages)}
