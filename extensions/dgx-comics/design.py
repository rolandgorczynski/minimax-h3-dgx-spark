"""Numbered comic grids and exact dialogue, independent of image generation."""
import json
import math
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
        result.append({'story': scene['story'].strip(), 'dialog': scene.get('dialog', '').strip()})
    return result


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


def panel(image, dialogue, number):
    # Speech has its own band so lettering never covers the character's face.
    width, height = 768, 672
    band = 150 if dialogue else 0
    tile = Image.new('RGB', (width, height), 'white')
    art = ImageOps.fit(image.convert('RGB'), (width-8, height-band-8), Image.Resampling.LANCZOS)
    tile.paste(art, (4, band+4))
    draw = ImageDraw.Draw(tile)
    if dialogue:
        draw.rounded_rectangle((65, 10, width-15, band-20), radius=35, fill='white', outline='black', width=3)
        draw.polygon([(width-165, band-21), (width-120, band-21), (width-125, band+8)], fill='white', outline='black', width=3)
        draw.line((width-161, band-21, width-125, band-21), fill='white', width=5)
        lettering(draw, dialogue, (85, 20, width-35, band-30))
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
