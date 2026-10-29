#!/usr/bin/env python3
"""Add the reusable Roland Gorczynski / bits.gorczynski.online image signature."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

NAME = 'Roland Gorczynski'
URL = 'bits.gorczynski.online'
FONT = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    if not a.input.is_file(): p.error(f'Input image not found: {a.input}')
    im=Image.open(a.input).convert('RGBA')
    w,h=im.size
    name_size=max(14,round(w*0.026))
    url_size=max(11,round(w*0.018))
    name_font=ImageFont.truetype(str(FONT),name_size)
    url_font=ImageFont.truetype(str(FONT),url_size)
    pad=max(8,round(w*0.015))
    gap=max(3,round(h*0.004))
    draw=ImageDraw.Draw(im,'RGBA')
    name_box=draw.textbbox((0,0),NAME,font=name_font,stroke_width=0)
    url_box=draw.textbbox((0,0),URL,font=url_font,stroke_width=0)
    tw=max(name_box[2]-name_box[0],url_box[2]-url_box[0])
    th=(name_box[3]-name_box[1])+(url_box[3]-url_box[1])+gap
    x=w-pad-tw
    y=h-pad-th
    draw.rounded_rectangle((x-pad,y-pad,x+tw+pad,y+th+pad),radius=max(5,pad//2),fill=(0,0,0,112))
    draw.text((x,y),NAME,font=name_font,fill=(255,255,255,242),stroke_width=max(1,round(w*0.0018)),stroke_fill=(0,0,0,190))
    uy=y+(name_box[3]-name_box[1])+gap
    draw.text((x,uy),URL,font=url_font,fill=(255,255,255,230),stroke_width=max(1,round(w*0.0014)),stroke_fill=(0,0,0,190))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    if a.output.suffix.lower() in {'.jpg','.jpeg'}:
        im.convert('RGB').save(a.output,quality=95,optimize=True)
    else:
        im.save(a.output)
    print(a.output)

if __name__=='__main__': main()
