"""Numbered comic grids and exact dialogue, independent of image generation."""
import json
import math
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

FONT = Path(__file__).parent.parent/'dgx-invitations/fonts/manrope.ttf'


def clean_text(value):
    if not isinstance(value,str):return value
    value=value.replace('\r\n','\n').replace('\r','\n').replace('\u200b','').replace('\ufeff','')
    value='\n'.join(re.sub(r'[^\S\n]+',' ',line).strip() for line in value.split('\n'))
    return re.sub(r'\n{3,}','\n\n',value).strip()


def validate_character_states(value):
    if not isinstance(value,dict) or len(value)>8 or any(not isinstance(key,str) or not re.fullmatch(r'[a-f0-9]{32}',key) or not isinstance(state,str) or not state.strip() or len(state)>1000 for key,state in value.items()):
        raise ValueError('Ungültiger Figuren-Zustand je Kachel.')
    return value


def parse_scenes(serialized, count):
    if type(count) is not int or count<1:
        raise ValueError('Bitte eine positive Kachelanzahl auswählen.')
    try:
        scenes = json.loads(serialized)
    except (ValueError, TypeError) as exc:
        raise ValueError('Die Szenen müssen als Liste gespeichert sein.') from exc
    if not isinstance(scenes, list) or len(scenes) < count:
        raise ValueError('Für jede Kachel eine Szene eingeben.')
    result = []
    for i, scene in enumerate(scenes[:count]):
        if not isinstance(scene, dict) or not isinstance(scene.get('story'), str) or not scene['story'].strip():
            raise ValueError(f'Kachel {i+1}: Die Szenenbeschreibung fehlt.')
        if not isinstance(scene.get('dialog', ''), str):
            raise ValueError(f'Kachel {i+1}: Der Dialog muss Text sein.')
        dialogue=clean_text(scene.get('dialog',''))
        if len(scene['story']) > 4000 or len(dialogue) > 400:
            raise ValueError(f'Kachel {i+1}: Szene maximal 4000, Dialog maximal 400 Zeichen.')
        item = {'story': scene['story'].strip(), 'dialog': dialogue}
        if 'characters' in scene:
            ids = scene['characters']
            if not isinstance(ids, list) or len(ids)>8 or any(not isinstance(x,str) or not re.fullmatch(r'[a-f0-9]{32}',x) for x in ids):
                raise ValueError(f'Kachel {i+1}: Ungültige Figuren-Zuordnung.')
            item['characters'] = ids
        if 'bubbles' in scene:
            item['bubbles'] = validate_bubbles(scene['bubbles'])
        if 'character_states' in scene:item['character_states']=validate_character_states(scene['character_states'])
        if 'lettering_draft' in scene:
            if type(scene['lettering_draft']) is not bool:raise ValueError('Ungültige Entwurfsmarkierung.')
            item['lettering_draft']=scene['lettering_draft']
        if 'canvas_size' in scene:item['canvas_size']=list(validate_canvas_size(scene['canvas_size']))
        if 'render_size' in scene:
            dims=scene['render_size']
            item['render_size']=list(validate_render_size(dims))
        result.append(item)
    return result


BUBBLE_STYLES={'rounded':'Abgerundet','oval':'Oval','box':'Eckig','thought':'Gedankenwolke','burst':'Gezackt','dashed':'Gestrichelt','auto':'Nach Sprechweise'}

def validate_bubbles(value):
    if not isinstance(value, list) or len(value)>6:
        raise ValueError('Maximal sechs Sprechblasen pro Kachel.')
    result=[]
    for i,bubble in enumerate(value):
        if not isinstance(bubble,dict):
            raise ValueError('Ungültige Sprechblase.')
        speaker=bubble.get('speaker','')
        text=clean_text(bubble.get('text',''))
        expression=bubble.get('expression','normal')
        if not isinstance(speaker,str) or not speaker.strip() or len(speaker)>100:
            raise ValueError('Jede Sprechblase braucht einen Sprecher (maximal 100 Zeichen).')
        if not isinstance(text,str) or len(text)>400:
            raise ValueError('Sprechblasentext maximal 400 Zeichen.')
        if expression not in ('normal','shout','whisper'):
            raise ValueError('Ungültiger Sprechblasen-Ausdruck.')
        style=bubble.get('bubble_style','rounded')
        if not isinstance(style,str) or style not in BUBBLE_STYLES:raise ValueError('Unbekannter Sprechblasenstil.')
        b={'speaker':speaker.strip(),'text':text.strip(),'expression':expression,'bubble_style':style}
        defaults={'x':.08+(i%2)*.46,'y':.23+(i//2)*.24,'w':.38,'h':.18,
                  'tip_x':.25+(i%2)*.5,'tip_y':min(.96,.48+(i//2)*.22)}
        for key,default in defaults.items():
            v=bubble.get(key,default)
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1:
                raise ValueError('Sprechblasenpositionen müssen zwischen 0 und 1 liegen.')
            b[key]=v
        if b['w']<.15 or b['h']<.08 or b['x']+b['w']>.995 or b['y']+b['h']>.995:
            raise ValueError('Die Sprechblase muss innerhalb der Kachel liegen und groß genug sein.')
        show=bubble.get('show_name',False)
        if not isinstance(show,bool): raise ValueError('Ungültige Sprecheranzeige.')
        b['show_name']=False
        result.append(b)
    return result


def validate_canvas_size(value):
    if not isinstance(value,(list,tuple)) or len(value)!=2 or any(type(n) is not int or n%16 for n in value) or not 384<=value[0]<=2304 or not 320<=value[1]<=3072:raise ValueError('Ungültiges Kachelformat: Breite 384–2304, Höhe 320–3072, jeweils durch 16 teilbar.')
    return tuple(value)


def validate_render_size(value):
    if not isinstance(value,(list,tuple)) or len(value)!=2 or any(type(n) is not int or n%16 or not 128<=n<=2304 for n in value) or value[0]*value[1]>2359296:raise ValueError('Ungültiges Illustrationsformat.')
    return tuple(value)


def caption_band(dialogue,size):
    return min(round(150*size[0]/768),round(size[1]*.38)) if dialogue else 0


def art_render_size(canvas_size,dialogue):
    width,height=validate_canvas_size(canvas_size);ratio=(width-8)/(height-caption_band(dialogue,(width,height))-8)
    budget=720896*min(2.5,max(1,width/768*height/672))
    w=round(math.sqrt(budget*ratio)/16)*16;h=round(w/ratio/16)*16
    scale=min(1,2304/max(w,h));w=max(128,round(w*scale/16)*16);h=max(128,round(h*scale/16)*16)
    return [w,h]


def _speech(draw, bubble, names, canvas_size=(768,672)):
    width,height=canvas_size;scale=width/768
    x,y,w,h=[bubble[key]*scale for key,scale in [('x',width),('y',height),('w',width),('h',height)]]
    tx,ty=bubble['tip_x']*width,bubble['tip_y']*height
    cx,cy=x+w/2,y+h/2
    dx,dy=tx-cx,ty-cy
    if abs(dx)/(w/2)>abs(dy)/(h/2):
        edge=x+w if dx>=0 else x
        base=[(edge,cy-12),(edge,cy+12)]
    else:
        edge=y+h if dy>=0 else y
        base=[(cx-12,edge),(cx+12,edge)]
    style=bubble.get('bubble_style','rounded')
    if style=='auto':style='burst' if bubble['expression']=='shout' else 'dashed' if bubble['expression']=='whisper' else 'rounded'
    if style=='thought':
        # Gedanken werden durch kleine Blasen statt eines Sprechschweifs verbunden.
        distance=math.hypot(dx,dy) or 1
        edge_scale=min(w/(2*abs(dx)) if dx else 1,h/(2*abs(dy)) if dy else 1,1)
        ex,ey=cx+dx*edge_scale,cy+dy*edge_scale
        for t,r in ((.25,9),(.60,6),(.9,3)):
            px,py=ex+(tx-ex)*t,ey+(ty-ey)*t
            draw.ellipse((px-r,py-r,px+r,py+r),fill='white',outline='black',width=2)
    else:draw.polygon([*base,(tx,ty)],fill='white',outline='black',width=3)
    if style in ('burst','thought'):
        count=64 if style=='burst' else 96;points=[]
        for i in range(count):
            angle=i*2*math.pi/count
            radius=(1 if i%2==0 else .9) if style=='burst' else 1+.055*math.sin(angle*12)
            points.append((cx+math.cos(angle)*w/2*radius/(1.055 if style=='thought' else 1),cy+math.sin(angle)*h/2*radius/(1.055 if style=='thought' else 1)))
        draw.polygon(points,fill='white',outline='black',width=3)
        inset_x,inset_y=(w*.18,h*.22) if style=='burst' else (w*.16,h*.20)
    elif style in ('oval','dashed'):
        draw.ellipse((x,y,x+w,y+h),fill='white',outline='black' if style=='oval' else None,width=3)
        if style=='dashed':
            for angle in range(0,360,20):draw.arc((x,y,x+w,y+h),angle,angle+11,fill='black',width=3)
        inset_x,inset_y=w*.15,h*.17
    else:
        draw.rounded_rectangle((x,y,x+w,y+h),radius=0 if style=='box' else min(25,h/3),fill='white',outline='black',width=3)
        inset_x,inset_y=14,10
    top=y+inset_y
    size=round((28 if bubble['expression']=='shout' else 24)*scale)
    if bubble['expression']=='whisper':size=round(20*scale)
    lettering(draw,bubble['text'],(x+inset_x,top,x+w-inset_x,y+h-inset_y),size=size,minimum=round((20 if bubble['expression']=='whisper' else 22)*scale))


def lettering(draw, value, bounds, size=30, minimum=18):
    left, top, right, bottom = bounds
    for pixels in range(size, minimum-1, -1):
        face = ImageFont.truetype(str(FONT), pixels)
        face.set_variation_by_axes([750])
        lines = []
        for paragraph in value.split('\n'):
            line = ''
            for word in paragraph.split():
                candidate = (line+' '+word).strip()
                if line and draw.textlength(candidate, font=face) > right-left:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
        step = math.ceil(pixels*1.25)
        if len(lines)*step <= bottom-top and all(draw.textlength(v, font=face) <= right-left for v in lines):
            y = top+(bottom-top-len(lines)*step)/2
            for line in lines:
                x = left+(right-left-draw.textlength(line, font=face))/2
                draw.text((x, y), line, font=face, fill='#121212', anchor='lt')
                y += step
            return
    raise ValueError('Der Text ist zu lang für die Sprechblase. Bitte kürzen.')


def panel(image, dialogue, number, bubbles=None, speaker_names=None, canvas_size=None,draft=False):
    # Keep legacy single-bubble layouts; new scenes use a narrator band and positioned speech.
    width,height=validate_canvas_size(canvas_size) if canvas_size else (768,672)
    scale=width/768
    band=caption_band(dialogue,(width,height)) if canvas_size else (150 if dialogue else 0)
    tile = Image.new('RGB', (width, height), 'white')
    art = ImageOps.fit(image.convert('RGB'), (width-8, height-band-8), Image.Resampling.LANCZOS)
    tile.paste(art, (4, band+4))
    draw = ImageDraw.Draw(tile)
    badge_font=ImageFont.truetype(str(FONT),26);badge_font.set_variation_by_axes([750])
    badge_width=max(43,math.ceil(draw.textlength(str(number),font=badge_font))+14)
    caption_left=max(65,12+badge_width+10)
    if dialogue and bubbles is not None:
        draw.rectangle((caption_left,10,width-15,band-20),fill='white',outline='black',width=3)
        try:lettering(draw,clean_text(dialogue),(caption_left+15,20,width-30,band-30),size=round(30*scale),minimum=round(24*scale))
        except ValueError:
            if not draft:raise
            lettering(draw,'TEXT PRÜFEN',(caption_left+15,20,width-30,band-30),size=24,minimum=18)
    elif dialogue:
        draw.rounded_rectangle((caption_left, 10, width-15, band-20), radius=35, fill='white', outline='black', width=3)
        draw.polygon([(width-165, band-21), (width-120, band-21), (width-125, band+8)], fill='white', outline='black', width=3)
        draw.line((width-161, band-21, width-125, band-21), fill='white', width=5)
        try:lettering(draw,clean_text(dialogue),(caption_left+20,20,width-35,band-30))
        except ValueError:
            if not draft:raise
            lettering(draw,'TEXT PRÜFEN',(caption_left+20,20,width-35,band-30),size=24,minimum=18)
    if bubbles is not None:
        for bubble in validate_bubbles(bubbles):
            try:_speech(draw,bubble,speaker_names or {},(width,height))
            except ValueError:
                if not draft:raise
    draw.rounded_rectangle((12,12,12+badge_width,55),radius=21,fill='white',outline='black',width=3)
    lettering(draw,str(number),(15,15,9+badge_width,52),size=26,minimum=26)
    if draft:
        draw.rectangle((4,height-52,width-4,height-4),fill='#ffdf8a',outline='#a56500',width=2)
        lettering(draw,'ENTWURF – Text bearbeiten',(12,height-48,width-12,height-8),size=24,minimum=18)
    draw.rectangle((1, 1, width-2, height-2), outline='black', width=4)
    return tile


def assemble(tiles, columns, title='', signature='sysop1984.substack.com'):
    if not 1 <= columns <= 4 or not tiles:
        raise ValueError('Bitte 1 bis 4 Spalten und mindestens eine Kachel verwenden.')
    columns = min(columns, len(tiles))
    rows = math.ceil(len(tiles)/columns)
    margin, gap = 20, 12
    top = 90 if title.strip() else 20
    width = columns*768+(columns-1)*gap+2*margin
    height = rows*672+(rows-1)*gap+top+65
    page = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(page)
    if title.strip():
        lettering(draw, title, (margin, 15, width-margin, 75), 42)
    for i, tile in enumerate(tiles):
        x = margin+(i%columns)*(768+gap)
        y = top+(i//columns)*(672+gap)
        if tile.size!=(768,672):
            fitted=ImageOps.contain(tile,(768,672),Image.Resampling.LANCZOS);page.paste(fitted,(x+(768-fitted.width)//2,y+(672-fitted.height)//2))
        else:page.paste(tile, (x, y))
    if signature.strip():
        lettering(draw, signature, (margin, height-55, width-margin, height-10), 27)
    return page


def assemble_preview(tiles,columns,title='',signature='',total_count=None):
    total=total_count if total_count is not None else len(tiles)
    label=title if total<=12 else title+' · Vorschau 1–12 von '+str(total)
    return assemble(tiles[:12],columns,label,signature)
