"""EPUB und KDP-Druckdateien aus fertigen Comic-Kacheln, ohne Modellaufrufe."""
import copy
import datetime
import hashlib
import html
import io
import json
import math
from pathlib import Path
import re
import uuid
import zipfile
import xml.etree.ElementTree as ET

from stories import Conflict

TRIMS={'6x9':(6.,9.),'8.5x11':(8.5,11.)}
INKS={'premium':(24,828,.002347),'standard':(72,600,.002252),'black':(24,828,.002252)}
TEXT_LIMITS={'title':200,'subtitle':300,'author':200,'publisher':200,'isbn':30,'imprint':12000,'front_heading':200,'front_text':100000,'back_heading':200,'back_text':100000,'blurb':2000}
SOURCES={'druck':'https://kdp.amazon.com/en_US/help/topic/G201857950','raender':'https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6','umschlag':'https://kdp.amazon.com/en_US/help/topic/G201953020','epub':'https://kdp.amazon.com/en_US/help/topic/G9GSTY4LTRT39D4Z','inhalt':'https://kdp.amazon.com/en_US/help/topic/G200672390'}


def defaults(title=''):
    return {**{k:'' for k in TEXT_LIMITS},'title':title,'front_heading':'Vorwort','back_heading':'Nachwort','trim':'6x9','ink':'premium','panels_per_page':1,'cover_panel':0}


def validate(value,required=False):
    if not isinstance(value,dict) or set(value)-set(defaults()):raise ValueError('Unbekannte Buchangaben.')
    result=defaults();result.update(value)
    for key,limit in TEXT_LIMITS.items():
        text=result[key]
        if not isinstance(text,str) or len(text)>limit or any(ord(c)<32 and c not in '\n\r\t' for c in text):raise ValueError(f'{key}: ungültiger Text oder mehr als {limit} Zeichen.')
        result[key]=text.strip()
    if required and (not result['title'] or not result['author']):raise ValueError('Buchtitel und Autor bitte ausfüllen.')
    if result['trim'] not in TRIMS or result['ink'] not in INKS:raise ValueError('Buchformat und Druckfarbe auswählen.')
    if type(result['panels_per_page']) is not int or result['panels_per_page'] not in (1,2,4):raise ValueError('1, 2 oder 4 Kacheln pro Druckseite wählen.')
    if type(result['cover_panel']) is not int or result['cover_panel']<0:raise ValueError('Vorhandenes Titelbild wählen.')
    isbn=re.sub(r'[\s-]','',result['isbn'])
    if isbn and (not re.fullmatch(r'\d{13}',isbn) or not isbn.startswith(('978','979')) or sum(int(n)*(1 if i%2==0 else 3) for i,n in enumerate(isbn))%10):raise ValueError('Gültige ISBN-13 eingeben oder das Feld leer lassen.')
    result['isbn']=isbn;return result


def source(store,parent):
    if parent['status'] not in ('completed','needs_review'):raise Conflict('Zuerst eine fertige Comic-Ausgabe wählen.')
    root=store.directory(parent['id'])
    if (root/'editorial-source.json').exists():data=json.loads((root/'editorial-source.json').read_text())
    else:
        story=json.loads((root/'story.json').read_text());plan=json.loads((root/'scenes.json').read_text());data={'title':story['title'],'scenes':plan['scenes']}
    scenes=data.get('scenes',[])
    if not isinstance(scenes,list) or not scenes:raise ValueError('Comic-Kacheln fehlen.')
    listed={a['name'] for a in parent.get('artifacts',[])}
    for i in range(len(scenes)):
        if f'panels/{i+1:02}_panel.png' not in listed or not(root/f'panels/{i+1:02}_panel.png').is_file():raise ValueError('Unvollständiger Comic: Kachel '+str(i+1)+' fehlt.')
    cast=json.loads((root/'characters.json').read_text()) if (root/'characters.json').exists() else []
    return {'book_author':data.get('book_author',''),'title':data.get('title',parent.get('story_title','Comic')),'narrator_badge':bool(data.get('narrator_badge')),'scenes':scenes,'characters':[{'id':c['id'],'name':c['name']} for c in cast]}


def settings(store,parent):
    data=store.integration_get('book-'+parent['id']) or {};src=source(store,parent)
    initial=defaults(src['title']);initial['author']=src.get('book_author','')
    return {'settings':data.get('settings',initial),'panel_count':len(src['scenes']),'last_export':data.get('last_export')}


def save_settings(store,parent,value):
    src=source(store,parent);clean=validate(value)
    if clean['cover_panel']>=len(src['scenes']):raise ValueError('Titelbild existiert nicht.')
    previous=store.integration_get('book-'+parent['id']) or {}
    store.integration_set('book-'+parent['id'],{**previous,'settings':clean});return clean


def enqueue(store,parent,value):
    src=source(store,parent);clean=validate(value,True)
    if clean['cover_panel']>=len(src['scenes']):raise ValueError('Titelbild existiert nicht.')
    if any(j.get('book_mode') and j.get('parent_job')==parent['id'] and j['status'] in ('queued','running') for j in store.list()):raise Conflict('Der Buch-Export für diesen Comic läuft bereits.')
    ident=uuid.uuid4().hex;store.create(ident,copy.deepcopy(parent['request']),initial_status='editing')
    try:
        root=store.directory(parent['id'])
        for i in range(len(src['scenes'])):store.write(ident,f'checkpoints/book-panels/{i+1:02}.png',(root/f'panels/{i+1:02}_panel.png').read_bytes())
        cover_art=root/f'panels/{clean["cover_panel"]+1:02}_art.png'
        store.write(ident,'checkpoints/book-cover.png',(cover_art if cover_art.is_file() else root/f'panels/{clean["cover_panel"]+1:02}_panel.png').read_bytes())
        store.write(ident,'checkpoints/book-input.json',{'source':src,'settings':clean})
        store.update(ident,book_mode=True,parent_job=parent['id'],story_title=clean['title'],story_id=parent.get('story_id'),story_version=parent.get('story_version'))
        store.integration_set('book-'+parent['id'],{'settings':clean,'last_export':ident})
        store.stage(ident,'queued',status='queued')
    except Exception:
        store.stage(ident,'failed',status='failed',error='Buchdaten konnten nicht gesichert werden.');raise
    return store.get(ident)


def resources():
    from lettering import DESIGN
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    font_path=DESIGN.FONT
    try:
        from fontTools.ttLib import TTFont as VariableFont
        from fontTools.varLib.instancer import instantiateVariableFont
        target=Path('/tmp/comic-book-regular.ttf')
        if not target.exists():
            face=VariableFont(str(font_path));instantiateVariableFont(face,{'wght':450},inplace=True)
            for ident,text in ((1,'ComicBookText'),(2,'Regular'),(3,'ComicBookText-Regular'),(4,'ComicBookText Regular'),(6,'ComicBookText-Regular')):face['name'].setName(text,ident,3,1,0x409)
            temporary=target.with_suffix('.tmp.ttf');face.save(temporary);temporary.replace(target)
        font_path=target
    except ImportError:pass
    if 'ComicBook' not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont('ComicBook',str(font_path)))
    return font_path


def wrapped(draw,text,font,width):
    result=[]
    for paragraph in text.split('\n'):
        line=''
        for word in paragraph.split():
            while draw.textlength(word,font=font)>width:
                if line:result.append(line);line=''
                cut=1
                while cut<len(word) and draw.textlength(word[:cut+1],font=font)<=width:cut+=1
                result.append(word[:cut]);word=word[cut:]
            candidate=(line+' '+word).strip()
            if line and draw.textlength(candidate,font=font)>width:result.append(line);line=word
            else:line=candidate
        result.append(line)
    return result


def text_images(heading,text,font_path):
    from PIL import Image,ImageDraw,ImageFont
    width,height=1600,2560;font=ImageFont.truetype(str(font_path),44);title=ImageFont.truetype(str(font_path),70)
    image=Image.new('RGB',(width,height),'white');draw=ImageDraw.Draw(image);y=160
    for line in wrapped(draw,heading,title,1320):draw.text((140,y),line,font=title,fill='#172535');y+=92
    y+=60
    for line in wrapped(draw,text,font,1320):
        if y+65>height-160:
            yield image
            image=Image.new('RGB',(width,height),'white');draw=ImageDraw.Draw(image);y=160
        draw.text((140,y),line,font=font,fill='#172535');y+=62
    yield image


def cover(settings,image,font_path,size=(1600,2560)):
    from PIL import Image,ImageDraw,ImageFont,ImageOps
    w,h=size;page=Image.new('RGB',size,'#172535');draw=ImageDraw.Draw(page);margin=round(w*.085);y=round(h*.065)
    title=ImageFont.truetype(str(font_path),round(w*.065))
    for line in wrapped(draw,settings['title'],title,w-2*margin):draw.text((margin,y),line,font=title,fill='white');y+=round(w*.085)
    if settings['subtitle']:
        font=ImageFont.truetype(str(font_path),round(w*.030))
        for line in wrapped(draw,settings['subtitle'],font,w-2*margin):draw.text((margin,y),line,font=font,fill='#d5dfea');y+=round(w*.043)
    top=max(y+int(w*.05),int(h*.25));bottom=int(h*.79)
    if top>=bottom:raise ValueError('Titel und Untertitel sind für den Umschlag zu lang.')
    picture=ImageOps.contain(image.convert('RGB'),(w-2*margin,bottom-top),Image.Resampling.LANCZOS);page.paste(picture,((w-picture.width)//2,top+(bottom-top-picture.height)//2))
    font=ImageFont.truetype(str(font_path),round(w*.040));y=int(h*.86)
    for line in wrapped(draw,settings['author'],font,w-2*margin):draw.text((margin,y),line,font=font,fill='white');y+=round(w*.06)
    if y>h-margin:raise ValueError('Autorenname passt nicht auf den Umschlag.')
    return page


def epub(path,settings,src,panels,font_path,cover_image):
    from PIL import Image,ImageOps
    esc=lambda t:html.escape(str(t),quote=True)
    identifier='urn:uuid:'+str(uuid.uuid4());items=[];spine=[];nav=[];index=0
    css='html,body{margin:0;padding:0;width:1600px;height:2560px;overflow:hidden}img.page{position:absolute;width:1600px;height:2560px;left:0;top:0}.tap{position:absolute;left:0;top:0;width:1600px;height:2560px}.tap a{display:block;width:100%;height:100%}.target-mag-parent{display:none;position:absolute;left:0;top:0;width:1600px;height:2560px;overflow:hidden}.target-mag{position:absolute;left:-400px;top:-640px;width:2400px;height:3840px}.target-mag img{width:2400px;height:3840px}'
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED)
        z.writestr('META-INF/container.xml','<?xml version="1.0" encoding="UTF-8"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        z.writestr('EPUB/style.css',css)
        def add(image,label,alt='',is_cover=False,magnify=False):
            nonlocal index
            index+=1;stem=f'page-{index:05}';buffer=io.BytesIO();image.convert('RGB').save(buffer,format='JPEG',quality=94,subsampling=0,dpi=(300,300));z.writestr('EPUB/images/'+stem+'.jpg',buffer.getvalue(),compress_type=zipfile.ZIP_DEFLATED)
            zoom='<div class="tap"><a class="app-amzn-magnify" data-app-amzn-magnify=\'{"targetId":"zoom","ordinal":1}\'></a></div><div id="zoom" class="target-mag-parent"><div class="target-mag"><img src="../images/'+stem+'.jpg" alt="'+esc(alt)+'"/></div></div>' if magnify else ''
            page='<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="de"><head><title>'+esc(label)+'</title><meta name="viewport" content="width=1600,height=2560"/><link rel="stylesheet" type="text/css" href="../style.css"/></head><body><img class="page" src="../images/'+stem+'.jpg" alt="'+esc(alt or label)+'"/>'+zoom+'</body></html>'
            z.writestr('EPUB/pages/'+stem+'.xhtml',page,compress_type=zipfile.ZIP_DEFLATED)
            items.extend([f'<item id="i{index}" href="images/{stem}.jpg" media-type="image/jpeg"'+(' properties="cover-image"' if is_cover else '')+'/>',f'<item id="p{index}" href="pages/{stem}.xhtml" media-type="application/xhtml+xml"/>']);spine.append(f'<itemref idref="p{index}" properties="rendition:page-spread-center"/>');nav.append((stem,label));return stem
        cover_stem=add(cover_image,settings['title'],settings['title']+' – '+settings['author'],True)
        for heading,text in [(settings['title'],settings['subtitle']+'\n\n'+settings['author']),('Impressum',settings['imprint']),(settings['front_heading'],settings['front_text'])]:
            if text.strip():
                for image in text_images(heading,text,font_path):add(image,heading or 'Buchanfang',text[:1000])
        first_content=None
        names={c['id']:c['name'] for c in src.get('characters',[])}
        for i,file in enumerate(panels):
            with Image.open(file) as im:picture=ImageOps.contain(im.convert('RGB'),(1480,2320),Image.Resampling.LANCZOS)
            page=Image.new('RGB',(1600,2560),'white');page.paste(picture,((1600-picture.width)//2,(2560-picture.height)//2))
            scene=src['scenes'][i];alt=scene.get('dialog','')+' '+ ' '.join(names.get(b['speaker'],'Figur')+': '+b['text'] for b in scene.get('bubbles',[]))
            stem=add(page,'Kachel '+str(i+1),alt.strip() or scene.get('story','Comic-Kachel'),magnify=True)
            if first_content is None:first_content=stem
        if settings['back_text']:
            for image in text_images(settings['back_heading'],settings['back_text'],font_path):add(image,settings['back_heading'] or 'Buchende',settings['back_text'][:1000])
        navigation='<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="de"><head><title>Inhalt</title></head><body><nav epub:type="toc"><h1>Inhalt</h1><ol>'+''.join('<li><a href="pages/'+stem+'.xhtml">'+esc(label)+'</a></li>' for stem,label in nav)+'</ol></nav><nav epub:type="landmarks" hidden="hidden"><ol><li><a epub:type="cover" href="pages/'+cover_stem+'.xhtml">Umschlag</a></li><li><a epub:type="bodymatter" href="pages/'+first_content+'.xhtml">Comic</a></li></ol></nav></body></html>'
        z.writestr('EPUB/nav.xhtml',navigation,compress_type=zipfile.ZIP_DEFLATED)
        modified=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        opf='<?xml version="1.0" encoding="UTF-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id" xml:lang="de"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="book-id">'+identifier+'</dc:identifier><dc:title>'+esc(settings['title'])+'</dc:title><dc:creator>'+esc(settings['author'])+'</dc:creator><dc:language>de</dc:language><meta property="dcterms:modified">'+modified+'</meta><meta property="rendition:layout">pre-paginated</meta><meta property="rendition:orientation">auto</meta><meta property="rendition:spread">none</meta><meta name="fixed-layout" content="true"/><meta name="original-resolution" content="1600x2560"/><meta name="book-type" content="comic"/><meta name="RegionMagnification" content="true"/><meta name="primary-writing-mode" content="horizontal-lr"/></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="css" href="style.css" media-type="text/css"/>'+''.join(items)+'</manifest><spine page-progression-direction="ltr">'+''.join(spine)+'</spine></package>'
        if settings['publisher']:opf=opf.replace('<dc:language>','<dc:publisher>'+esc(settings['publisher'])+'</dc:publisher><dc:language>')
        z.writestr('EPUB/package.opf',opf,compress_type=zipfile.ZIP_DEFLATED)
    validate_epub(path)
    return index


def validate_epub(path):
    import posixpath
    with zipfile.ZipFile(path) as z:
        if z.infolist()[0].filename!='mimetype' or z.infolist()[0].compress_type!=zipfile.ZIP_STORED or z.read('mimetype')!=b'application/epub+zip':raise ValueError('Ungültiger EPUB-Container.')
        for name in z.namelist():
            if name.endswith(('.opf','.xhtml','.xml')):
                root=ET.fromstring(z.read(name))
                for element in root.iter():
                    for key in ('src','href'):
                        link=element.get(key)
                        if link and not link.startswith(('http:','https:','#')):
                            target=posixpath.normpath(posixpath.join(posixpath.dirname(name),link.split('#')[0]))
                            if target not in z.namelist():raise ValueError('EPUB-Datei fehlt: '+target)


def print_pdf(path,settings,src,panels,font_path,_pages_hint=None):
    from PIL import Image,ImageOps
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.colors import CMYKColor
    from reportlab.platypus import Paragraph
    from reportlab.lib.utils import ImageReader
    w,h=[n*72 for n in TRIMS[settings['trim']]];count=0;total_hint=_pages_hint or math.ceil(len(panels)/settings['panels_per_page'])+10
    inside=max(.5,.375 if total_hint<=150 else .5 if total_hint<=300 else .625 if total_hint<=500 else .75 if total_hint<=700 else .875)*72
    outside=36;top=36;bottom=36;content_w=w-inside-outside;content_h=h-top-bottom
    c=Canvas(str(path),pagesize=(w,h),pageCompression=1,initialFontName='ComicBook');c.setTitle(settings['title']);c.setAuthor(settings['author']);warnings=[];blockers=[];min_effective=10000
    style=ParagraphStyle('Buchtext',fontName='ComicBook',fontSize=11,leading=16,textColor=CMYKColor(0,0,0,1),spaceAfter=10)
    def left():return inside if (count+1)%2 else outside
    def finish():
        nonlocal count
        count+=1;c.setFont('ComicBook',9);c.setFillColorCMYK(0,0,0,1);c.drawCentredString(w/2,20,str(count));c.showPage()
    def text_pages(heading,text):
        y=h-top;x=left()
        if heading:
            p=Paragraph(html.escape(heading),ParagraphStyle('Titel',parent=style,fontSize=21,leading=28,spaceAfter=18));pw,ph=p.wrap(content_w,content_h)
            if ph>content_h:raise ValueError('Überschrift zu lang.')
            p.drawOn(c,x,y-ph);y-=ph+18
        for chunk in text.split('\n\n'):
            p=Paragraph(html.escape(chunk).replace('\n','<br/>'),style)
            todo=[p]
            while todo:
                p=todo.pop(0);pw,ph=p.wrap(content_w,y-bottom)
                if ph<=y-bottom:p.drawOn(c,x,y-ph);y-=ph+10
                else:
                    split=p.split(content_w,y-bottom)
                    if split:
                        first=split.pop(0);pw,ph=first.wrap(content_w,y-bottom);first.drawOn(c,x,y-ph);todo=split+todo
                    finish();y=h-top;x=left()
        finish()
    text_pages(settings['title'],settings['subtitle']+'\n\n'+settings['author'])
    if settings['imprint'] or settings['isbn']:text_pages('Impressum',settings['imprint']+('\n\nISBN '+settings['isbn'] if settings['isbn'] else ''))
    if settings['front_text']:text_pages(settings['front_heading'],settings['front_text'])
    per=settings['panels_per_page'];columns=2 if per==4 else 1;rows=2 if per in (2,4) else 1;gap=12
    for start in range(0,len(panels),per):
        x0=left();cell_w=(content_w-gap*(columns-1))/columns;cell_h=(content_h-gap*(rows-1))/rows
        for slot,file in enumerate(panels[start:start+per]):
            with Image.open(file) as im:original=im.convert('RGB')
            scale=min(cell_w/original.width,cell_h/original.height);dw,dh=original.width*scale,original.height*scale;dpi=72/scale;min_effective=min(min_effective,dpi)
            scene=src['scenes'][start+slot];smallest=min([20 if b.get('expression')=='whisper' else 22 for b in scene.get('bubbles',[])]+([24] if scene.get('dialog') else [100]))
            if src.get('narrator_badge'):smallest=min(smallest,11)
            if any(b.get('show_name') is True for b in scene.get('bubbles',[])):smallest=min(smallest,16)
            if smallest*scale<7:blockers.append('Kachel '+str(start+slot+1)+': Schrift wäre kleiner als 7 Punkt. Weniger Kacheln pro Druckseite oder ein größeres Format wählen.')
            target=(max(1,round(dw/72*300)),max(1,round(dh/72*300)));pixels=original.resize(target,Image.Resampling.LANCZOS).convert('L' if settings['ink']=='black' else 'CMYK')
            buffer=io.BytesIO();pixels.save(buffer,format='JPEG',quality=95,dpi=(300,300));buffer.seek(0)
            col=slot%columns;row=slot//columns;x=x0+col*(cell_w+gap)+(cell_w-dw)/2;y=h-top-row*(cell_h+gap)-(cell_h+dh)/2
            c.drawImage(ImageReader(buffer),x,y,width=dw,height=dh)
        finish()
    if settings['back_text']:text_pages(settings['back_heading'],settings['back_text'])
    if count%2:finish()
    c.save()
    actual_inside=max(.5,.375 if count<=150 else .5 if count<=300 else .625 if count<=500 else .75 if count<=700 else .875)*72
    if actual_inside>inside:return print_pdf(path,settings,src,panels,font_path,_pages_hint=count)
    minimum,maximum,factor=INKS[settings['ink']]
    if settings['trim']=='8.5x11' and settings['ink']!='standard':maximum=590
    if count<minimum:blockers.append(f'{count} Druckseiten: Für diese Druckart sind mindestens {minimum} Seiten erforderlich. Keine künstliche Auffüllung mit Leerseiten erfolgt.')
    if count>maximum:blockers.append(f'{count} Druckseiten: KDP erlaubt für diese Auswahl höchstens {maximum} Seiten pro Band.')
    if min_effective<300:warnings.append(f'Die Originalkacheln erreichen im gewählten Layout rechnerisch nur {min_effective:.0f} ppi. Der Export ist auf 300 dpi aufbereitet; neue Bilddetails entstehen durch Skalierung nicht. Druckprobe prüfen.')
    return {'pages':count,'width_inches':w/72,'height_inches':h/72,'minimum_pages':minimum,'maximum_pages':maximum,'spine_inches':count*factor,'blockers':list(dict.fromkeys(blockers)),'warnings':warnings,'effective_source_ppi':round(min_effective),'output_dpi':300,'interior_bleed':False,'inside_margin_inches':inside/72}


def cover_pdf(path,settings,front,font_path,report):
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.colors import CMYKColor
    from reportlab.platypus import Paragraph
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase.pdfmetrics import stringWidth
    width,height=TRIMS[settings['trim']];bleed=.125;spine=report['spine_inches'];full_w=(2*width+spine+2*bleed)*72;full_h=(height+2*bleed)*72
    c=Canvas(str(path),pagesize=(full_w,full_h),pageCompression=1,initialFontName='ComicBook');c.setFillColorCMYK(.7,.5,.25,.7);c.rect(0,0,full_w,full_h,fill=1,stroke=0)
    buffer=io.BytesIO();front.convert('CMYK').save(buffer,format='JPEG',quality=95,dpi=(300,300));buffer.seek(0);c.drawImage(ImageReader(buffer),(bleed+width+spine)*72,bleed*72,width=width*72,height=height*72)
    style=ParagraphStyle('Rueckseite',fontName='ComicBook',fontSize=11,leading=16,textColor=CMYKColor(0,0,0,0))
    p=Paragraph(html.escape(settings['blurb']).replace('\n','<br/>'),style);pw,ph=p.wrap((width-1)*72,(height-2)*72)
    if ph>(height-2)*72:raise ValueError('Klappentext passt nicht auf die Rückseite.')
    p.drawOn(c,(bleed+.5)*72,(bleed+height-.5)*72-ph)
    # Freier Bereich für den automatisch von KDP gesetzten Barcode, ohne Platzhaltertext.
    c.setFillColorCMYK(0,0,0,0);c.rect((bleed+width-2.35)*72,(bleed+.3)*72,2.1*72,1.2*72,fill=1,stroke=0)
    if report['pages']>=80 and spine*72>=10:
        title=settings['title'];size=8
        if stringWidth(title,'ComicBook',size)<(height-1)*72:
            c.saveState();c.translate((bleed+width+spine/2)*72,(bleed+.5)*72);c.rotate(90);c.setFont('ComicBook',size);c.setFillColorCMYK(0,0,0,0);c.drawString(0,-size/3,title);c.restoreState()
    c.showPage();c.save();return {'width_inches':full_w/72,'height_inches':full_h/72,'bleed_inches':bleed,'barcode_space_reserved':True}


def run(store,ident):
    from PIL import Image
    root=store.directory(ident);data=json.loads((root/'checkpoints/book-input.json').read_text());settings=validate(data['settings'],True);src=data['source'];out=root/'books';out.mkdir(exist_ok=True);font=resources();panels=[root/f'checkpoints/book-panels/{i+1:02}.png' for i in range(len(src['scenes']))]
    store.stage(ident,'book_epub')
    with Image.open(root/'checkpoints/book-cover.png') as im:cover_art=im.convert('RGB')
    ebook_cover=cover(settings,cover_art,font);ebook_cover.save(out/'ebook-cover.jpg',quality=95,subsampling=0,dpi=(300,300))
    epub_pages=epub(out/'comic.epub',settings,src,panels,font,ebook_cover)
    store.stage(ident,'book_print')
    report=print_pdf(out/'taschenbuch-inhalt.pdf',settings,src,panels,font)
    front=cover(settings,cover_art,font,tuple(round(n*300) for n in TRIMS[settings['trim']]))
    report['cover']=cover_pdf(out/'taschenbuch-umschlag.pdf',settings,front,font,report)
    for filename in ('taschenbuch-inhalt.pdf','taschenbuch-umschlag.pdf'):
        if (out/filename).stat().st_size>650*1024*1024:report['blockers'].append(filename+': größer als das KDP-Dateilimit von 650 MB.')
    report.update({'title':settings['title'],'author':settings['author'],'panel_count':len(panels),'epub_pages':epub_pages,'epub_structure_valid':True,'kdp_acceptance_verified':False,'print_upload_ready':not report['blockers'],'sources':SOURCES,'model_calls':0,'original_comic_unchanged':True,'kdp_rules_checked':'2026-10-23'})
    if report['blockers']:
        (out/'taschenbuch-inhalt.pdf').rename(out/'taschenbuch-inhalt-ENTWURF.pdf');(out/'taschenbuch-umschlag.pdf').rename(out/'taschenbuch-umschlag-ENTWURF.pdf')
    (out/'buchpruefung.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    notes=('Buchdateien für Amazon KDP\n\nEPUB: comic.epub als Kindle-eBook-Manuskript und ebook-cover.jpg als Titelbild verwenden. EPUB-Struktur geprüft; vor Veröffentlichung in Kindle Previewer und im KDP-Vorschautool kontrollieren.\n\nTaschenbuch: Buchformat '+settings['trim']+', '+settings['ink']+', weißes Papier, Buchblock OHNE Beschnitt. Manuskript und vollständigen Umschlag separat hochladen. Umschlag enthält 0,125 Zoll Beschnitt. Die gewählte Papier-/Farbart und Seitenzahl müssen in KDP übereinstimmen.\n\nAutor: '+settings['author']+'\nTitel: '+settings['title']+'\nDruckseiten: '+str(report['pages'])+'\n\n'+('\n'.join(report['blockers']) if report['blockers'] else 'Die eingebauten technischen Druckprüfungen sind bestanden. Das ist keine Zusage einer Annahme durch Amazon.')+'\n\n'+'\n'.join(report['warnings'])+'\n\nWenn keine eigene ISBN vorliegt, diese bei KDP festlegen; es wurde keine ISBN erfunden. KDP kann den Barcode in der freigehaltenen Fläche platzieren. Die erforderlichen Angaben zu KI-generierten Bildern, Rechten, Inhalt und Veröffentlichung im KDP-Formular selbst machen. Kein Upload und keine Veröffentlichung wurden ausgeführt.\n\nQuellen:\n'+'\n'.join(SOURCES.values())+'\n')
    (out/'KDP-Anleitung.txt').write_text(notes)
    with zipfile.ZipFile(out/'buchpaket.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(out.iterdir()):
            if path.suffix!='.zip':archive.write(path,path.name)
    artifacts=[{'name':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'url':f'/jobs/{ident}/artifacts/{p.relative_to(root)}'} for p in sorted(out.iterdir()) if p.is_file()]
    return {'status':'needs_review','artifacts':artifacts,'book_report':report,'warnings':report['blockers']+report['warnings']}
