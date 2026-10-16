"""Local invitation layout. Text and logos are composed, never regenerated."""
from pathlib import Path
import math
import re

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps

FONTS = Path(__file__).parent / 'fonts'
PALETTES = {
    'Mitternacht & Gold': ('#111F31', '#C5A46C', '#F6EEE0'),
    'Botanisch & Creme': ('#F3F0E7', '#52715A', '#233D30'),
    'Modern & Koralle': ('#F4EDE4', '#C86651', '#243347'),
}
FORMATS = {'A5 Hochformat': (148, 210), 'A6 Hochformat': (105, 148), 'Quadratisch': (148, 148)}


def color(value, default):
    if not value.strip():
        return ImageColor.getrgb(default)
    if not re.fullmatch(r'#[0-9A-Fa-f]{6}', value.strip()):
        raise ValueError('Farben bitte als Hex-Code angeben, zum Beispiel #C5A46C, oder leer lassen.')
    return ImageColor.getrgb(value.strip())


def font(size, serif=False):
    return ImageFont.truetype(str(FONTS / ('cormorantgaramond.ttf' if serif else 'manrope.ttf')), max(10, int(size)))


def wrapped(draw, text, face, width):
    lines = []
    for paragraph in text.split('\n'):
        line = ''
        for word in paragraph.split():
            candidate = f'{line} {word}'.strip()
            if line and draw.textlength(candidate, font=face) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


def text_block(draw, text, box, size, fill, serif=False, tracking=0):
    if not text.strip():
        return
    left, top, right, bottom = box
    for pixels in range(int(size), max(10, int(size * 0.5)) - 1, -1):
        face = font(pixels, serif)
        lines = wrapped(draw, text, face, right - left)
        step = pixels * 1.2
        widths = [draw.textlength(line, font=face) + tracking * max(0, len(line) - 1) for line in lines]
        if len(lines) * step <= bottom - top and max(widths, default=0) <= right - left:
            break
    else:
        raise ValueError('Ein Text ist zu lang für das gewählte Format. Bitte kürzen oder Zeilenumbrüche ergänzen.')
    y = top + ((bottom - top) - len(lines) * step) / 2
    for line, width in zip(lines, widths):
        x = (left + right - width) / 2
        if tracking:
            for letter in line:
                draw.text((x, y), letter, font=face, fill=fill, anchor='lt')
                x += draw.textlength(letter, font=face) + tracking
        else:
            draw.text((x, y), line, font=face, fill=fill, anchor='lt')
        y += step


def leaf(draw, start, tip, thickness, fill):
    x, y = start
    dx, dy = tip[0] - x, tip[1] - y
    length = math.hypot(dx, dy)
    if not length:
        return
    normal = (-dy / length, dx / length)
    sides = []
    for sign in (1, -1):
        points = []
        for i in range(17):
            t = i / 16
            bend = math.sin(math.pi * t) * thickness * sign
            points.append((x + dx * t + normal[0] * bend, y + dy * t + normal[1] * bend))
        sides.extend(points if sign == 1 else reversed(points))
    draw.polygon(sides, fill=fill)


def ornaments(image, accent, style):
    w, h = image.size
    layer = Image.new('RGBA', image.size)
    d = ImageDraw.Draw(layer)
    if style == 'Modern & Koralle':
        d.ellipse((w * .65, -w * .2, w * 1.3, w * .45), fill=(*accent, 36))
        d.ellipse((-w * .3, h - w * .4, w * .45, h + w * .35), fill=(*accent, 23))
    elif style == 'Botanisch & Creme':
        for flip in (False, True):
            points = [(w * (.035 + .22 * t), h * (.7 + .27 * t)) for t in np.linspace(0, 1, 30)]
            if flip:
                points = [(w - x, h - y) for x, y in points]
            d.line(points, fill=(*accent, 75), width=max(1, w // 1000))
            for i in range(2, 27, 3):
                x, y = points[i]
                direction = -1 if i % 2 else 1
                leaf(d, (x, y), (x + direction * w * .075, y - h * .035), w * .015, (*accent, 24))
    else:
        for offset in range(3):
            radius = w * (.3 + offset * .022)
            center = (w * 1.04, h * .18)
            d.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), outline=(*accent, 20), width=max(1, w // 1100))
        for x, y, radius in [(.12, .77, .003), (.87, .6, .002), (.82, .29, .003), (.17, .39, .002)]:
            px, py, r = x * w, y * h, radius * w
            d.line((px-r, py, px+r, py), fill=(*accent, 100), width=1)
            d.line((px, py-r, px, py+r), fill=(*accent, 100), width=1)
    inset_x, inset_y = w * .057, h * .04
    d.rectangle((inset_x, inset_y, w-inset_x, h-inset_y), outline=(*accent, 120), width=max(1, w // 1100))
    for x, sx in [(inset_x, 1), (w-inset_x, -1)]:
        for y, sy in [(inset_y, 1), (h-inset_y, -1)]:
            length = w * .065
            d.line((x, y+sy*length, x, y, x+sx*length, y), fill=(*accent, 240), width=max(2, w // 650))
    return Image.alpha_composite(image.convert('RGBA'), layer).convert('RGB')


def demo_logo(size=640, accent='#C5A46C'):
    logo = Image.new('RGBA', (size, size))
    d = ImageDraw.Draw(logo)
    s = size / 640
    d.ellipse((70*s, 70*s, 570*s, 570*s), outline=accent, width=max(1, round(3*s)))
    d.ellipse((85*s, 85*s, 555*s, 555*s), outline=accent, width=max(1, round(s)))
    d.line([(210*s, 445*s), (210*s, 200*s), (430*s, 440*s), (430*s, 195*s)], fill=accent, width=max(1, round(11*s)))
    d.line([(150*s, 180*s), (150*s, 150*s), (180*s, 150*s)], fill=accent, width=max(1, round(3*s)))
    return logo


def render_card(veranstaltung, veranstalter, einladungstext, datum, uhrzeit, ort, rueckmeldung,
                stil='Mitternacht & Gold', format='A5 Hochformat', akzentfarbe='', hintergrundfarbe='',
                logo=None, background=None, hintergrund_staerke=0.25):
    if stil not in PALETTES or format not in FORMATS:
        raise ValueError('Unbekannter Stil oder unbekanntes Format.')
    values = [veranstaltung, veranstalter, einladungstext, datum, uhrzeit, ort, rueckmeldung]
    if any(len(value) > 2000 for value in values):
        raise ValueError('Bitte höchstens 2000 Zeichen pro Textfeld verwenden.')
    if not veranstaltung.strip():
        raise ValueError('Bitte einen Veranstaltungstitel eingeben.')
    bg, accent, foreground = PALETTES[stil]
    bg, accent = color(hintergrundfarbe, bg), color(akzentfarbe, accent)
    foreground = ImageColor.getrgb(foreground)
    if hintergrundfarbe.strip():
        luminance = sum(c * weight for c, weight in zip(bg, (.2126, .7152, .0722))) / 255
        foreground = ImageColor.getrgb('#233347' if luminance > .55 else '#F6EEE0')
    width_mm, height_mm = FORMATS[format]
    w, h = round(width_mm / 25.4 * 300), round(height_mm / 25.4 * 300)
    image = Image.new('RGB', (w, h), bg)
    if background is not None:
        fitted = ImageOps.fit(background.convert('RGB'), (w, h), method=Image.Resampling.LANCZOS)
        image = Image.blend(image, fitted, max(0, min(1, hintergrund_staerke)))
    image = ornaments(image, accent, stil)
    d = ImageDraw.Draw(image)
    if logo is None:
        logo = demo_logo()
    logo = logo.convert('RGBA')
    # Transparent padding is ignored; the actual brand mark is placed unchanged.
    bounds = logo.getbbox()
    if bounds:
        logo = logo.crop(bounds)
        logo.thumbnail((round(w * .28), round(h * .115)), Image.Resampling.LANCZOS)
        image.paste(logo, (round((w-logo.width)/2), round(h*.145-logo.height/2)), logo)
    def block(text, top, bottom, size, fill=foreground, serif=False, tracking=0):
        text_block(d, text, (w*.15, h*top, w*.85, h*bottom), h*size, fill, serif, tracking)
    block(veranstalter.upper(), .222, .248, .013, accent, tracking=w*.0016)
    block('EINLADUNG', .273, .295, .011, accent, tracking=w*.003)
    block(veranstaltung.upper(), .315, .535, .103, foreground, serif=True)
    block(einladungstext, .557, .625, .0155)
    d.line((w*.44, h*.652, w*.56, h*.652), fill=accent, width=max(1, w//800))
    block(datum, .678, .708, .0175)
    block(uhrzeit, .718, .747, .0155, accent)
    block(ort, .775, .838, .0155)
    block(rueckmeldung, .88, .935, .0115)
    return image
