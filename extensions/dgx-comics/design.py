"""Numbered comic grids and exact dialogue, independent of image generation."""
import json
import math
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

FONT = Path(__file__).parent.parent/'dgx-invitations/fonts/manrope.ttf'


def parse_scenes(serialized, count):
    if not 1 <= count <= 12:
        raise ValueError('Bitte 1 bis 12 Kacheln auswählen.')
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
        if len(scene['story']) > 4000 or len(scene.get('dialog', '')) > 400:
            raise ValueError(f'Kachel {i+1}: Szene maximal 4000, Dialog maximal 400 Zeichen.')
        item = {'story': scene['story'].strip(), 'dialog': scene.get('dialog', '').strip()}
        if 'characters' in scene:
            ids = scene['characters']
            if not isinstance(ids, list) or len(ids)>8 or any(not isinstance(x,str) or not re.fullmatch(r'[a-f0-9]{32}',x) for x in ids):
                raise ValueError(f'Kachel {i+1}: Ungültige Figuren-Zuordnung.')
            item['characters'] = ids
        if 'bubbles' in scene:
            item['bubbles'] = validate_bubbles(scene['bubbles'])
        result.append(item)
    return result


def validate_bubbles(value):
    if not isinstance(value, list) or len(value)>6:
        raise ValueError('Maximal sechs Sprechblasen pro Kachel.')
    result=[]
    for i,bubble in enumerate(value):
        if not isinstance(bubble,dict):
            raise ValueError('Ungültige Sprechblase.')
        speaker=bubble.get('speaker','')
        text=bubble.get('text','')
        expression=bubble.get('expression','normal')
        if not isinstance(speaker,str) or not speaker.strip() or len(speaker)>100:
            raise ValueError('Jede Sprechblase braucht einen Sprecher (maximal 100 Zeichen).')
        if not isinstance(text,str) or len(text)>400:
            raise ValueError('Sprechblasentext maximal 400 Zeichen.')
        if expression not in ('normal','shout','whisper'):
            raise ValueError('Ungültiger Sprechblasen-Ausdruck.')
        b={'speaker':speaker.strip(),'text':text.strip(),'expression':expression}
        defaults={'x':.08+(i%2)*.46,'y':.23+(i//2)*.24,'w':.38,'h':.18,
                  'tip_x':.25+(i%2)*.5,'tip_y':min(.96,.48+(i//2)*.22)}
        for key,default in defaults.items():
            v=bubble.get(key,default)
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1:
                raise ValueError('Sprechblasenpositionen müssen zwischen 0 und 1 liegen.')
            b[key]=v
        if b['w']<.15 or b['h']<.08 or b['x']+b['w']>.995 or b['y']+b['h']>.995:
            raise ValueError('Die Sprechblase muss innerhalb der Kachel liegen und groß genug sein.')
        show=bubble.get('show_name',True)
        if not isinstance(show,bool): raise ValueError('Ungültige Sprecheranzeige.')
        b['show_name']=show
        result.append(b)
    return result


def _speech(draw, bubble, names):
    x,y,w,h=[bubble[key]*scale for key,scale in [('x',768),('y',672),('w',768),('h',672)]]
    tx,ty=bubble['tip_x']*768,bubble['tip_y']*672
    cx,cy=x+w/2,y+h/2
    dx,dy=tx-cx,ty-cy
    if abs(dx)/(w/2)>abs(dy)/(h/2):
        edge=x+w if dx>=0 else x
        base=[(edge,cy-12),(edge,cy+12)]
    else:
        edge=y+h if dy>=0 else y
        base=[(cx-12,edge),(cx+12,edge)]
    # Draw the tail first, then the body to keep the join clean.
    draw.polygon([*base,(tx,ty)],fill='white',outline='black',width=3)
    if bubble['expression']=='shout':
        points=[]
        for i in range(32):
            angle=i*math.pi/16
            radius=1 if i%2==0 else .9
            points.append((cx+math.cos(angle)*w/2*radius,cy+math.sin(angle)*h/2*radius))
        draw.polygon(points,fill='white',outline='black',width=3)
        inset_x,inset_y=w*.18,h*.22
    else:
        draw.rounded_rectangle((x,y,x+w,y+h),radius=min(25,h/3),fill='white',outline='black',width=3)
        inset_x,inset_y=14,10
    top=y+inset_y
    if bubble['show_name']:
        speaker=names.get(bubble['speaker'],bubble['speaker'])
        lettering(draw,speaker,(x+inset_x,top,x+w-inset_x,top+22),size=16,minimum=12)
        top+=24
    size=28 if bubble['expression']=='shout' else 24
    if bubble['expression']=='whisper':size=20
    lettering(draw,bubble['text'],(x+inset_x,top,x+w-inset_x,y+h-inset_y),size=size,minimum=14)


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


def panel(image, dialogue, number, bubbles=None, speaker_names=None):
    # Keep legacy single-bubble layouts; new scenes use a narrator band and positioned speech.
    width, height = 768, 672
    band = 150 if dialogue else 0
    tile = Image.new('RGB', (width, height), 'white')
    art = ImageOps.fit(image.convert('RGB'), (width-8, height-band-8), Image.Resampling.LANCZOS)
    tile.paste(art, (4, band+4))
    draw = ImageDraw.Draw(tile)
    if dialogue and bubbles is not None:
        draw.rectangle((65,10,width-15,band-20),fill='white',outline='black',width=3)
        lettering(draw,dialogue,(80,20,width-30,band-30))
    elif dialogue:
        draw.rounded_rectangle((65, 10, width-15, band-20), radius=35, fill='white', outline='black', width=3)
        draw.polygon([(width-165, band-21), (width-120, band-21), (width-125, band+8)], fill='white', outline='black', width=3)
        draw.line((width-161, band-21, width-125, band-21), fill='white', width=5)
        lettering(draw, dialogue, (85, 20, width-35, band-30))
    if bubbles is not None:
        for bubble in validate_bubbles(bubbles):
            _speech(draw,bubble,speaker_names or {})
    draw.ellipse((12, 12, 55, 55), fill='white', outline='black', width=3)
    lettering(draw, str(number), (15, 15, 52, 52), size=26)
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
        page.paste(tile, (x, y))
    if signature.strip():
        lettering(draw, signature, (margin, height-55, width-margin, height-10), 27)
    return page
