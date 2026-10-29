"""Sysop comics with per-panel scenes and a shared local FLUX image reference."""
import json
import hashlib
import base64
import io
from pathlib import Path

import folder_paths
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import torch
import comfy.utils
from .design import assemble, assemble_preview, panel, parse_scenes
from .equipment import instruction as equipment_instruction

WEB_DIRECTORY = './web'
DEFAULT_SCENES = [
    {'story': 'Sysop sitzt im Smoking mit einer Kaffeetasse vor einem Serverrack. Er schaut zufrieden auf die grünen Statusanzeigen.', 'dialog': 'Heute läuft alles ruhig.'},
    {'story': 'Sysop sieht auf seinem Monitor ein einzelnes rotes Warnsymbol. Er hebt skeptisch eine Augenbraue.', 'dialog': 'Nur ein kleines Update.'},
    {'story': 'Sysop steht zwischen vielen losen Netzwerkkabeln im Serverraum. Die Kaffeetasse hält er noch fest.', 'dialog': 'Das stand nicht im Changelog.'},
    {'story': 'Sysop sitzt wieder entspannt am Schreibtisch. Alle Server leuchten grün. Er hebt seine Kaffeetasse.', 'dialog': 'Backup. Aus gutem Grund.'},
]


class DGXSysopComic:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'referenz': ('IMAGE',), 'model': ('MODEL',), 'clip': ('CLIP',), 'vae': ('VAE',),
            'anzahl_kacheln': ('INT', {'default': 4, 'min': 1, 'max': 9007199254740991}),
            'spalten': ('INT', {'default': 2, 'min': 1, 'max': 4}),
            'titel': ('STRING', {'default': 'Sysop · Nur ein kleines Update'}),
            'hauptfigur': ('STRING', {'default': 'Sysop: middle-aged man, shoulder-length wavy dark brown hair, full dark beard with subtle grey strands, strong eyebrows, black tuxedo jacket, white shirt and black bow tie. Match the same person and drawing style as the reference.', 'multiline': True}),
            'stil': ('STRING', {'default': 'European editorial comic illustration, confident black ink outlines, warm muted colors, expressive faces, clear visual storytelling, same character design in every panel.', 'multiline': True}),
            'szenen': ('STRING', {'default': json.dumps(DEFAULT_SCENES, ensure_ascii=False), 'multiline': True}),
            'signatur': ('STRING', {'default': 'example.com'}),
            'seed': ('INT', {'default': 1984, 'min': 0, 'max': 2147483647, 'control_after_generate': True}),
            'dateiname': ('STRING', {'default': 'comics/sysop'}),
        }, 'optional': {'szenenplan': ('STRING', {'forceInput': True})},
            'hidden': {'prompt': 'PROMPT', 'extra_pnginfo': 'EXTRA_PNGINFO'}}

    RETURN_TYPES = ('IMAGE',)
    RETURN_NAMES = ('comic',)
    FUNCTION = 'create'
    CATEGORY = 'DGX/Comics'
    OUTPUT_NODE = True
    DESCRIPTION = 'Frei wählbare Kachelanzahl. Pro Kachel Szene und Dialog eingeben. Sysop wird für jedes Bild als Referenz an das ComfyUI-Modell FLUX.2 Klein 9B übergeben. Texte werden separat gesetzt.'

    def create(self, referenz, model, clip, vae, anzahl_kacheln, spalten, titel, hauptfigur, stil, szenen,
               signatur, seed, dateiname, prompt=None, extra_pnginfo=None, szenenplan=None, revisions=None, reuse_panels=False, model_identity=None, cast=None, library_cast=False, output_directory=None, image_type='output', image_subfolder_prefix=''):
        if szenenplan is not None:
            planned = json.loads(szenenplan)
            if not isinstance(planned, list):
                raise ValueError('Der automatische Szenenplan muss eine Liste sein.')
            anzahl_kacheln = len(planned)
            szenen = szenenplan
        scenes = parse_scenes(szenen, anzahl_kacheln)
        if not 1 <= spalten <= 4 or len(titel) > 200 or len(signatur) > 200:
            raise ValueError('Bitte 1–4 Spalten wählen und Titel/Signatur auf 200 Zeichen begrenzen.')
        if len(hauptfigur)+len(stil) > 2500:
            raise ValueError('Figurenbeschreibung und Stil zusammen maximal 2500 Zeichen.')
        speaker_names = {c['id']:c['name'] for c in cast or []}
        # Check lettering for every panel before starting expensive generation.
        for i, scene in enumerate(scenes):
            panel(Image.new('RGB', (768, 512)), scene['dialog'], i+1, scene.get('bubbles'), speaker_names,canvas_size=scene.get('canvas_size'),draft=scene.get('lettering_draft',False))
        assemble_preview([Image.new('RGB', (768, 672))]*min(12,len(scenes)), spalten, titel, signatur,len(scenes))
        from .generation import prepare_reference, generate_panel
        reference_latent = None
        character_latents = {}
        output = output_directory or folder_paths.get_output_directory()
        folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(dateiname, output)
        base = f'{filename}_{counter:05}'
        # A separate run directory retains completed panels if a later request fails.
        run = Path(folder)/(base+'_panels')
        while run.exists() or (Path(folder)/(base+'.png')).exists():
            counter += 1
            base = f'{filename}_{counter:05}'
            run = Path(folder)/(base+'_panels')
        run.mkdir(exist_ok=False)
        (run/'story.json').write_text(json.dumps({'title': titel, 'character': hauptfigur,
            'style': stil, 'signature': signatur, 'seed': seed, 'columns': spalten, 'scenes': scenes, 'panel_revisions': revisions or {}, 'characters': cast or []}, ensure_ascii=False, indent=2)+'\n')
        cache = Path(output)/'comics'/'.panel-cache'
        if reuse_panels:
            cache.mkdir(parents=True, exist_ok=True)
        reference_key = hashlib.sha256(referenz.detach().cpu().contiguous().numpy().tobytes()).hexdigest() if reuse_panels and not library_cast else ''
        previews = []
        progress = comfy.utils.ProgressBar(len(scenes))
        tiles = []
        from .characters import scene_cast, character_prompt, library
        for i, scene in enumerate(scenes):
            active = scene_cast(scene, cast or [])
            references = [(c, asset) for c in active for asset in c['references']]
            inline_sources={}
            for c in active:
                for encoded in c.get('inline_references',[]):
                    data=base64.b64decode(encoded,validate=True)
                    asset=hashlib.sha256(data).hexdigest()+'.png'
                    inline_sources[(c['id'],asset)]=data
                    references.append((c,asset))
            for c, asset in references:
                if (c['id'],asset) not in inline_sources:library().reference_path(c['id'], asset)
            reference_offset = 0 if library_cast else 1
            reference_instructions = [] if library_cast else ['Reference image 1 shows Sysop.']
            reference_instructions += [f'Reference image {j+1+reference_offset} shows only the identity of {c["name"]}. Keep different people distinct.' for j,(c,asset) in enumerate(references)]
            identity_rules = (
                ([f'This panel contains exactly {len(active)} assigned subject(s), each appearing once. Follow the scene composition.',
                  'Keep each assigned person consistent with their saved profile and uploaded reference images.'] if active else
                 ['Environmental illustration or object still life. Focus exclusively on the architecture and objects described in the scene.'])
                if library_cast else
                ['Exactly one Sysop, no duplicate characters, no twins, no reflections, no split view. Other people only if the scene explicitly requests them.',
                 'Keep Sysop the same person: same face, hair and beard. Follow the selected style and scene for clothing. Change the pose, expression and setting to match the scene.', hauptfigur])
            text = '\n'.join([
                'Create one new comic panel. Preserve the scene events and composition. The selected visual style controls palette and lighting.',
                *identity_rules, stil, 'Scene: '+scene['story'],
                *([character_prompt(c,scene.get('character_states',{}).get(c['id'],'')) for c in active]),
                *reference_instructions,
                *[equipment_instruction(c) for c in active if equipment_instruction(c)],
                *(['The saved character profiles and current clothing define the assigned subjects.'] if active else []),
                'One scene only, no grid, no lettering, no words, no speech bubbles, no captions, no watermark.'])
            if scene.get('render_size'):text+='\nFrame this scene for an illustration of '+str(scene['render_size'][0])+' by '+str(scene['render_size'][1])+' pixels. Keep all assigned subjects and important objects inside the frame.'
            panel_seed = (seed+i+100003*(revisions or {}).get(str(i), 0)) % 2147483648
            cache_key = hashlib.sha256(json.dumps([text, panel_seed, reference_key, [(c['id'], asset) for c, asset in references],
                model_identity if model_identity is not None else [id(model), id(clip), id(vae)]]).encode()).hexdigest()
            cached = cache/(cache_key+'.png')
            retained = Path(output)/'retained-panels'/f'{i+1:02}_art.png' if image_type=='temp' else None
            if retained and retained.is_file() and scene.get('render_size'):
                with Image.open(retained) as check:
                    if list(check.size)!=scene['render_size']:retained=None
            if retained and retained.is_file():
                with Image.open(retained) as existing:art=existing.convert('RGB')
            elif reuse_panels and cached.exists():
                with Image.open(cached) as existing:
                    art = existing.convert('RGB')
            else:
                panel_references = []
                if not library_cast:
                    if reference_latent is None:
                        reference_latent = prepare_reference(vae, referenz)
                    panel_references.append(reference_latent)
                for c, asset in references:
                    key = (c['id'], asset)
                    if key not in character_latents:
                        source=io.BytesIO(inline_sources[key]) if key in inline_sources else library().reference_path(*key)
                        with Image.open(source) as image:
                            if image.width*image.height>25_000_000:raise ValueError('Referenzbild zu groß.')
                            pixels = torch.from_numpy(np.asarray(image.convert('RGB')).copy().astype(np.float32)/255).unsqueeze(0)
                        character_latents[key] = prepare_reference(vae, pixels)
                    panel_references.append(character_latents[key])
                pixels = generate_panel(model, clip, vae, panel_references, text, panel_seed, *scene['render_size']) if scene.get('render_size') else generate_panel(model, clip, vae, panel_references, text, panel_seed)
                art = Image.fromarray(np.clip(pixels[0].detach().cpu().numpy()*255, 0, 255).astype(np.uint8)).convert('RGB')
                if reuse_panels:
                    temporary = cached.with_suffix('.tmp.png')
                    art.save(temporary)
                    temporary.replace(cached)
            art.save(run/f'{i+1:02}_art.png')
            tile = panel(art, scene['dialog'], i+1, scene.get('bubbles'), speaker_names,canvas_size=scene.get('canvas_size'),draft=scene.get('lettering_draft',False))
            tile.save(run/f'{i+1:02}_panel.png')
            previews.append({'filename': f'{i+1:02}_panel.png',
                'subfolder': str(Path(image_subfolder_prefix)/subfolder/run.name), 'type': image_type})
            if len(tiles)<12:tiles.append(tile)
            progress.update_absolute(i+1)
        comic = assemble_preview(tiles, spalten, titel, signatur,len(scenes))
        metadata = PngInfo()
        if prompt is not None:
            metadata.add_text('prompt', json.dumps(prompt, ensure_ascii=False))
        for key, value in (extra_pnginfo or {}).items():
            metadata.add_text(key, json.dumps(value, ensure_ascii=False))
        name = base+'.png'
        comic.save(Path(folder)/name, pnginfo=metadata)
        return {'ui': {'images': [{'filename': name, 'subfolder': str(Path(image_subfolder_prefix)/subfolder) if image_subfolder_prefix else subfolder, 'type': image_type}], 'comic_panels': previews},
                'result': (torch.from_numpy(np.asarray(comic).astype(np.float32)/255).unsqueeze(0),)}


NODE_CLASS_MAPPINGS = {'DGXSysopComic': DGXSysopComic}
NODE_DISPLAY_NAME_MAPPINGS = {'DGXSysopComic': 'Sysop Comic · Kacheln & Geschichten'}


class DGXComicStory:
    @classmethod
    def INPUT_TYPES(cls):
        from .story import STYLES
        return {'required': {
            'clip': ('CLIP',),
            'gesamtgeschichte': ('STRING', {'default': 'Sysop genießt einen ruhigen Tag im Serverraum. Er installiert ein vermeintlich kleines Update. Plötzlich funktioniert das Netzwerk nicht mehr und er steht im Kabelchaos. Zum Glück hat er ein Backup. Nach der Wiederherstellung läuft alles wieder und Sysop hebt erleichtert seine Kaffeetasse. Die Pointe: Backup. Aus gutem Grund.', 'multiline': True}),
            'anzahl_kacheln': ('INT', {'default': 4, 'min': 1, 'max': 9007199254740991}),
            'seed': ('INT', {'default': 1984, 'min': 0, 'max': 2147483647, 'control_after_generate': True}),
            'bearbeiteter_plan': ('STRING', {'default': '', 'multiline': True}),
        }, 'optional': {'comic_art': (list(STYLES),)}}

    RETURN_TYPES = ('STRING', 'STRING')
    RETURN_NAMES = ('szenenplan', 'bildstil')
    FUNCTION = 'plan'
    CATEGORY = 'DGX/Comics'
    OUTPUT_NODE = True
    DESCRIPTION = 'Gesamtgeschichte lokal mit vorhandenem Qwen3 8B in Szenen und Sprechblasen aufteilen. Die erzeugten Szenen bleiben bearbeitbar.'

    def plan(self, clip, gesamtgeschichte, anzahl_kacheln, seed, bearbeiteter_plan='', comic_art='Klassischer Comic'):
        from .story import plan_story, STYLES
        style = STYLES[comic_art]
        scenes, fingerprint = plan_story(clip, gesamtgeschichte, anzahl_kacheln, seed, bearbeiteter_plan, style)
        value = json.dumps({'source_hash': fingerprint, 'scenes': scenes}, ensure_ascii=False)
        return {'ui': {'comic_plan': [value]}, 'result': (json.dumps(scenes, ensure_ascii=False), style)}


NODE_CLASS_MAPPINGS['DGXComicStory'] = DGXComicStory
NODE_DISPLAY_NAME_MAPPINGS['DGXComicStory'] = 'Gesamtgeschichte → Kacheln · Qwen3 8B'

from .workflow import DGXComicWorkflow
NODE_CLASS_MAPPINGS["DGXComicWorkflow"] = DGXComicWorkflow
NODE_DISPLAY_NAME_MAPPINGS["DGXComicWorkflow"] = "Artikel → Szenen prüfen → Comic"

from .characters import register_routes
register_routes()

from .speech_routes import register_speech_routes
register_speech_routes()

from .workflow import DGXComicStudio
NODE_CLASS_MAPPINGS["DGXComicStudio"] = DGXComicStudio
NODE_DISPLAY_NAME_MAPPINGS["DGXComicStudio"] = "Comic-Studio · Figuren, Szenen & Sprechblasen"

from .automation import DGXComicAssistant, DGXComicPortrait, register_automation_routes
NODE_CLASS_MAPPINGS.update({"DGXComicAssistant":DGXComicAssistant,"DGXComicPortrait":DGXComicPortrait})
register_automation_routes()
