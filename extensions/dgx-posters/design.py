"""Facebook poster composition: original branding and exact Polish text."""
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

FONT = Path(__file__).parent.parent / 'dgx-invitations/fonts/manrope.ttf'
NAVY = '#102742'


def text(draw, value, box, size, fill=NAVY, weight=600):
    left, top, right, bottom = box
    for pixels in range(size, 17, -1):
        font = ImageFont.truetype(str(FONT), pixels)
        font.set_variation_by_axes([weight])
        lines = []
        for paragraph in value.split('\n'):
            line = ''
            for word in paragraph.split():
                candidate = (line + ' ' + word).strip()
                if line and draw.textlength(candidate, font=font) > right-left:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
        step = int(pixels * 1.3)
        if len(lines)*step <= bottom-top and all(draw.textlength(s, font=font) <= right-left for s in lines):
            for i, line in enumerate(lines):
                draw.text((left, top+i*step), line, font=font, fill=fill, anchor='lt')
            return
    raise ValueError('Za długi tekst w polu: ' + value[:70] + '. Skróć tekst.')


def compose(organizer, title, topics, event_date, hours, place, illustration, logo=None, footer=None, crest=None):
    parsed = date.fromisoformat(event_date)
    day = ('poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota', 'niedziela')[parsed.weekday()]
    if not title.strip() or not organizer.strip() or not place.strip():
        raise ValueError('Uzupełnij tytuł, organizatora i miejsce.')
    if any(len(v) > 2500 for v in (organizer, title, topics, hours, place)):
        raise ValueError('Maksymalnie 2500 znaków w jednym polu.')
    image = Image.new('RGB', (1080, 1350), '#f8f5ee')
    draw = ImageDraw.Draw(image)
    if logo is not None:
        mark = logo.convert('RGBA')
        bounds = mark.getbbox()
        if bounds:
            mark = mark.crop(bounds)
            mark.thumbnail((185, 185), Image.Resampling.LANCZOS)
            image.paste(mark, (45+(185-mark.width)//2, 25+(185-mark.height)//2), mark)
    text(draw, organizer, (255 if logo is not None else 45, 52, 1035, 135 if crest is not None else 205), 42)
    if crest is not None:
        mark = crest.convert('RGBA')
        mark.thumbnail((300, 70), Image.Resampling.LANCZOS)
        image.paste(mark, (1035-mark.width, 145), mark)
    footer_height = 0
    if footer is not None:
        footer_height = round(footer.height * 990 / footer.width) + 30
        if footer_height > 200:
            raise ValueError('Belka jest zbyt wysoka. Użyj poziomej belki partnerów (co najmniej 6:1).')
    # Art gets a separate full-width band. Exact lettering never goes through the image model.
    art = ImageOps.fit(illustration.convert('RGB'), (1080, 390-footer_height), method=Image.Resampling.LANCZOS)
    image.paste(art, (0, 225))
    draw.rectangle((0, 615-footer_height, 1080, 627-footer_height), fill='#bf3938')
    text(draw, title, (45, 649-footer_height, 1035, 775-footer_height), 48, weight=800)
    if footer is not None:
        strip = footer.convert('RGBA').resize((990, footer_height-30), Image.Resampling.LANCZOS)
        image.paste(strip, (45, 1350-footer_height+15), strip)
    info_y = 1130-footer_height
    text(draw, topics, (45, 795-footer_height, 1035, info_y-20), 31)
    draw.rounded_rectangle((30, info_y, 1050, 1330-footer_height), radius=20, fill=NAVY)
    text(draw, parsed.strftime('%d.%m.%Y') + ' · ' + day + ' · ' + hours,
         (55, info_y+20, 1025, info_y+75), 32, '#ffffff')
    text(draw, place, (55, info_y+86, 1025, 1310-footer_height), 29, '#ffffff')
    return image
