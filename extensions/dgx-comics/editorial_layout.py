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
    tiles=[Image.open(output/f'panels/{i+1:02}_panel.png').convert('RGB') for i in range(len(source['scenes']))]
    if decorate:decorate_tiles(tiles,source,design)
    layout_info={'narrator_badge':bool(source.get('narrator_badge')),'reproduce':'scripts/layout_editorial_comic.py','panels_per_sharing_page':4}
    workflow.setdefault('extra',{})['editorial_layout']=layout_info
    for node in workflow.get('nodes',[]):
        if node.get('type')=='Note':
            node['widgets_values']=['Redaktioneller Comic: Szenen und Texte unverändert rendern. Das Exportskript scripts/layout_editorial_comic.py ergänzt das Sysop-Porträt in der Kopfleiste und die Druck-/Teilseiten. Figurenreferenzen sind eingebettet.']
            break
    (output/'workflow.json').write_text(json.dumps(workflow,ensure_ascii=False,indent=2)+'\n')
    metadata.add_text('workflow',json.dumps(workflow,ensure_ascii=False));metadata.add_text('editorial_layout',json.dumps(layout_info))
    for i,tile in enumerate(tiles):tile.save(output/f'panels/{i+1:02}_panel.png',pnginfo=metadata)
    design.assemble(tiles,min(3,len(tiles)),source['title'],source.get('signature','')).save(output/'comic.png',pnginfo=metadata)
    pages=[];(output/'pages').mkdir(exist_ok=True)
    count=(len(tiles)+3)//4
    for start in range(0,len(tiles),4):
        page=design.assemble(tiles[start:start+4],2,f'{source["title"]} · {start//4+1}/{count}',source.get('signature',''))
        page.save(output/f'pages/{start//4+1:02}.png',pnginfo=metadata);pages.append(page)
    pages[0].save(output/'comic.pdf','PDF',resolution=144,save_all=True,append_images=pages[1:])
    (output/'README.txt').write_text('Redaktioneller Comic auf Basis des bereitgestellten Artikels.\ncomic.png: alle Kacheln. pages/: Teilseiten zum Teilen. comic.pdf: mehrseitige Fassung.\nworkflow.json: in ComfyUI öffnen, Figurenreferenzen sind eingebettet.\nDas Workflow-Rendering erzeugt die Illustrationen und Texte. scripts/layout_editorial_comic.py ergänzt das Erzähler-Porträt und die Druckseiten.\nPersonen sind symbolisch dargestellt; Angaben und Zeitbezüge stammen aus dem bereitgestellten Artikel.\n',encoding='utf-8')
    return {'panels':len(tiles),'pages':len(pages)}
