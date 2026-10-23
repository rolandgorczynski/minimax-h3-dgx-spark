"""Additive automation helpers: model calls and strictly private temporary outputs."""
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import shutil

import folder_paths
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
import torch

SESSION = re.compile(r'^[a-f0-9]{32}$')


def session_directory(session):
    if not isinstance(session,str) or not SESSION.fullmatch(session):
        raise ValueError('Ungültiger Automationsauftrag.')
    return Path(folder_paths.get_temp_directory())/'comic-automation'/session


def decode_image(encoded):
    if not isinstance(encoded,str) or len(encoded)>8_000_000:
        raise ValueError('Referenzbild zu groß.')
    data=base64.b64decode(encoded,validate=True)
    with Image.open(io.BytesIO(data)) as image:
        if image.width*image.height>25_000_000:
            raise ValueError('Referenzbild zu groß.')
        return ImageOps.exif_transpose(image).convert('RGB')


class DGXComicAssistant:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required':{'clip':('CLIP',),'auftrag':('STRING',{'multiline':True}),
            'max_tokens':('INT',{'default':2048,'min':64,'max':8192}),
            'seed':('INT',{'default':42,'min':0,'max':2147483647})},
            'optional':{'bilder':('STRING',{'default':'[]'})}}
    RETURN_TYPES=('STRING',)
    FUNCTION='execute'
    CATEGORY='DGX/Comics/Automation'
    OUTPUT_NODE=True

    def execute(self,clip,auftrag,max_tokens,seed,bilder='[]'):
        from comfy_extras.nodes_textgen import TextGenerate
        encoded=json.loads(bilder)
        if not isinstance(encoded,list) or len(encoded)>4 or len(auftrag)>60000:
            raise ValueError('Maximal vier Prüfbilder und 60000 Zeichen.')
        image=None
        if encoded:
            # Image 1 stays large enough to assess lettering. Reference views below it.
            originals=[decode_image(item) for item in encoded]
            main=ImageOps.contain(originals[0],(1000,900))
            ref_height=280 if len(originals)>1 else 0
            sheet=Image.new('RGB',(max(768,main.width),main.height+35+ref_height),'white')
            draw=ImageDraw.Draw(sheet)
            draw.text((8,8),'IMAGE 1: panel to review',fill='black')
            sheet.paste(main,(0,30))
            for i,reference in enumerate(originals[1:]):
                reference=ImageOps.contain(reference,(sheet.width//3-8,240))
                x=i*(sheet.width//3)
                draw.text((x+8,main.height+40),f'IMAGE {i+2}: reference',fill='black')
                sheet.paste(reference,(x,main.height+60))
            image=torch.from_numpy(np.asarray(sheet).copy().astype(np.float32)/255).unsqueeze(0)
        sampling={'sampling_mode':'on','temperature':0.65,'top_k':40,'top_p':0.9,
                  'min_p':0.05,'repetition_penalty':1.16,'presence_penalty':0.35,'seed':seed}
        result=TextGenerate.execute(clip,auftrag+'\n/no_think',max_tokens,sampling,image=image,thinking=False)[0]
        return {'ui':{'assistant_text':[result]},'result':(result,)}


class DGXComicPortrait:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required':{'model':('MODEL',),'clip':('CLIP',),'vae':('VAE',),
            'beschreibung':('STRING',{'multiline':True}),'stil':('STRING',),
            'session':('STRING',),'figur_id':('STRING',),
            'seed':('INT',{'default':42,'min':0,'max':2147483647})}}
    RETURN_TYPES=('IMAGE',)
    FUNCTION='execute'
    CATEGORY='DGX/Comics/Automation'
    OUTPUT_NODE=True

    def execute(self,model,clip,vae,beschreibung,stil,session,figur_id,seed):
        from .generation import generate_panel
        root=session_directory(session)
        if not SESSION.fullmatch(figur_id) or len(beschreibung)>4000 or len(stil)>2000:
            raise ValueError('Ungültiger Figurenentwurf.')
        prompt='Character reference portrait, exactly one person, face and upper body clearly visible, neutral background, no text, no labels, no panels. '+beschreibung+'\nArt style: '+stil
        pixels=generate_panel(model,clip,vae,[],prompt,seed)
        image=Image.fromarray(np.clip(pixels[0].detach().cpu().numpy()*255,0,255).astype(np.uint8))
        image.thumbnail((768,768))
        root.mkdir(parents=True,exist_ok=True)
        filename=f'character-{figur_id}.png'
        image.save(root/filename)
        return {'ui':{'images':[{'filename':filename,'subfolder':f'comic-automation/{session}','type':'temp'}]},'result':(pixels,)}


def register_automation_routes():
    from aiohttp import web
    from server import PromptServer
    if getattr(PromptServer,'instance',None) is None:
        return
    @PromptServer.instance.routes.post('/dgx-comics/automation/retain-panel')
    async def retain_panel(request):
        try:
            data=await request.json();root=session_directory(data['session']);index=data['panel']
            if type(index) is not int or index<0 or root.is_symlink():raise ValueError('Ungültige Kachel.')
            running,pending=PromptServer.instance.prompt_queue.get_current_queue()
            for entry in [*running,*pending]:
                if entry[3].get('comic_automation_session')==data['session']:raise ValueError('Auftrag wird bereits gezeichnet.')
            image=decode_image(data['png'])
            if image.size!=(1024,704):raise ValueError('Unerwartete Größe der Originalillustration.')
            target=root/'retained-panels'
            if target.is_symlink():raise ValueError('Ungültiges temporäres Verzeichnis.')
            target.mkdir(parents=True,exist_ok=True);image.save(target/f'{index+1:02}_art.png')
            return web.json_response({'retained':index+1})
        except (ValueError,KeyError,TypeError,OSError) as exc:return web.json_response({'error':str(exc)},status=400)

    @PromptServer.instance.routes.post('/dgx-comics/automation/layout')
    async def editorial_layout(request):
        from .editorial_layout import render_layout
        from . import design
        import asyncio
        try:
            data=await request.json();session=data['session'];root=session_directory(session)
            if root.is_symlink():raise ValueError('Ungültiges temporäres Verzeichnis.')
            root=root.resolve()
            source=data['source'];panels=data['panels']
            if not isinstance(panels,list) or not panels or len(source['scenes'])!=len(panels):raise ValueError('Ungültige Kachelzahl.')
            def resolve(descriptor):
                if descriptor.get('type')!='temp':raise ValueError('Nur private temporäre Bilder erlaubt.')
                file=(Path(folder_paths.get_temp_directory())/descriptor['subfolder']/descriptor['filename']).resolve()
                if not file.is_relative_to(root) or not file.is_file():raise ValueError('Bild gehört nicht zum Auftrag.')
                return file
            image=resolve(data['image']);originals=[resolve(p) for p in panels]
            target=root/'web-layout'
            if target.is_symlink():raise ValueError('Ungültiges Ausgabeverzeichnis.')
            def produce():
                target.mkdir(exist_ok=True);(target/'panels').mkdir(exist_ok=True)
                shutil.copy2(image,target/'comic.png')
                for i,file in enumerate(originals):shutil.copy2(file,target/f'panels/{i+1:02}_panel.png')
                render_layout(target,source,data['workflow'],design)
                return [{'name':str(p.relative_to(target)),'image':{'filename':p.name,'subfolder':str(p.parent.relative_to(folder_paths.get_temp_directory())),'type':'temp'}}
                        for p in sorted(target.rglob('*')) if p.is_file()]
            return web.json_response({'files':await asyncio.to_thread(produce)})
        except (ValueError,KeyError,TypeError,OSError) as exc:return web.json_response({'error':str(exc)},status=400)

    @PromptServer.instance.routes.post('/dgx-comics/automation/check-plan')
    async def preflight(request):
        from .characters import read_cast
        from .design import parse_scenes, panel
        try:
            data=await request.json();cast=read_cast(data.get('cast',[]));scenes=data['scenes']
            if not isinstance(scenes,list) or not scenes:raise ValueError('Mindestens eine Szene erforderlich.')
            issues=[];names={c['id']:c['name'] for c in cast}
            for i,scene in enumerate(scenes):
                try:
                    scene=parse_scenes(json.dumps([scene]),1)[0]
                    panel(Image.new('RGB',(768,512)),scene['dialog'],i+1,scene.get('bubbles'),names)
                except (ValueError,TypeError) as exc:issues.append({'panel':i+1,'message':str(exc)})
            return web.json_response({'valid':not issues,'issues':issues})
        except (ValueError,KeyError,TypeError) as exc:
            return web.json_response({'error':str(exc)},status=400)

    @PromptServer.instance.routes.delete('/dgx-comics/automation/{session}')
    async def cleanup(request):
        try:
            session=request.match_info['session']
            root=session_directory(session)
            # A session must not be removed while one of its own prompts is running/queued.
            running,pending=PromptServer.instance.prompt_queue.get_current_queue()
            for entry in [*running,*pending]:
                extra=entry[3] if len(entry)>3 else {}
                if extra.get('comic_automation_session')==session:
                    return web.json_response({'error':'Auftrag läuft noch.'},status=409)
            if root.is_symlink():
                raise ValueError('Ungültiges temporäres Verzeichnis.')
            if root.exists():shutil.rmtree(root)
            return web.json_response({'cleaned':session})
        except ValueError as exc:
            return web.json_response({'error':str(exc)},status=400)
