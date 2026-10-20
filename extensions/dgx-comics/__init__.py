"""Sysop comics with per-panel scenes and a shared local FLUX image reference."""
import json
import hashlib
from pathlib import Path

import folder_paths
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import torch
import comfy.utils
from .design import assemble, panel, parse_scenes

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
            'anzahl_kacheln': ('INT', {'default': 4, 'min': 1, 'max': 12}),
            'spalten': ('INT', {'default': 2, 'min': 1, 'max': 4}),
            'titel': ('STRING', {'default': 'Sysop · Nur ein kleines Update'}),
            'hauptfigur': ('STRING', {'default': 'Sysop: middle-aged man, shoulder-length wavy dark brown hair, full dark beard with subtle grey strands, strong eyebrows, black tuxedo jacket, white shirt and black bow tie. Match the same person and drawing style as the reference.', 'multiline': True}),
            'stil': ('STRING', {'default': 'European editorial comic illustration, confident black ink outlines, warm muted colors, expressive faces, clear visual storytelling, same character design in every panel.', 'multiline': True}),
            'szenen': ('STRING', {'default': json.dumps(DEFAULT_SCENES, ensure_ascii=False), 'multiline': True}),
            'signatur': ('STRING', {'default': 'sysop1984.substack.com'}),
            'seed': ('INT', {'default': 1984, 'min': 0, 'max': 2147483647, 'control_after_generate': True}),
            'dateiname': ('STRING', {'default': 'comics/sysop'}),
        }, 'optional': {'szenenplan': ('STRING', {'forceInput': True})},
            'hidden': {'prompt': 'PROMPT', 'extra_pnginfo': 'EXTRA_PNGINFO'}}

    RETURN_TYPES = ('IMAGE',)
    RETURN_NAMES = ('comic',)
    FUNCTION = 'create'
    CATEGORY = 'DGX/Comics'
    OUTPUT_NODE = True
    DESCRIPTION = '1–12 Kacheln. Pro Kachel Szene und Dialog eingeben. Sysop wird für jedes Bild als Referenz an das ComfyUI-Modell FLUX.2 Klein 9B übergeben. Texte werden separat gesetzt.'

    def create(self, referenz, model, clip, vae, anzahl_kacheln, spalten, titel, hauptfigur, stil, szenen,
               signatur, seed, dateiname, prompt=None, extra_pnginfo=None, szenenplan=None, revisions=None, reuse_panels=False, model_identity=None):
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
        # Check lettering for every panel before starting expensive generation.
        for i, scene in enumerate(scenes):
            panel(Image.new('RGB', (768, 512)), scene['dialog'], i+1)
        assemble([Image.new('RGB', (768, 672))]*len(scenes), spalten, titel, signatur)
        from .generation import prepare_reference, generate_panel
        reference_latent = None
        output = folder_paths.get_output_directory()
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
            'style': stil, 'signature': signatur, 'seed': seed, 'columns': spalten, 'scenes': scenes, 'panel_revisions': revisions or {}}, ensure_ascii=False, indent=2)+'\n')
        cache = Path(output)/'comics'/'.panel-cache'
        if reuse_panels:
            cache.mkdir(parents=True, exist_ok=True)
        reference_key = hashlib.sha256(referenz.detach().cpu().contiguous().numpy().tobytes()).hexdigest() if reuse_panels else ''
        previews = []
        progress = comfy.utils.ProgressBar(len(scenes))
        tiles = []
        for i, scene in enumerate(scenes):
            text = '\n'.join([
                'Create one new comic panel. Use the reference only for the identity of the main character. The selected visual style overrides the reference style.',
                'Exactly one Sysop, no duplicate characters, no twins, no reflections, no split view. Other people only if the scene explicitly requests them.',
                'Keep Sysop the same person: same face, hair and beard. Follow the selected style and scene for clothing. Change the pose, expression and setting to match the scene.',
                hauptfigur, stil, 'Scene: '+scene['story'],
                'One scene only, no grid, no lettering, no words, no speech bubbles, no captions, no watermark.'])
            panel_seed = (seed+i+100003*(revisions or {}).get(str(i), 0)) % 2147483648
            cache_key = hashlib.sha256(json.dumps([text, panel_seed, reference_key,
                model_identity if model_identity is not None else [id(model), id(clip), id(vae)]]).encode()).hexdigest()
            cached = cache/(cache_key+'.png')
            if reuse_panels and cached.exists():
                with Image.open(cached) as existing:
                    art = existing.convert('RGB')
            else:
                if reference_latent is None:
                    reference_latent = prepare_reference(vae, referenz)
                pixels = generate_panel(model, clip, vae, reference_latent, text, panel_seed)
                art = Image.fromarray(np.clip(pixels[0].detach().cpu().numpy()*255, 0, 255).astype(np.uint8)).convert('RGB')
                if reuse_panels:
                    temporary = cached.with_suffix('.tmp.png')
                    art.save(temporary)
                    temporary.replace(cached)
            art.save(run/f'{i+1:02}_art.png')
            tile = panel(art, scene['dialog'], i+1)
            tile.save(run/f'{i+1:02}_panel.png')
            previews.append({'filename': f'{i+1:02}_panel.png',
                'subfolder': str(Path(subfolder)/run.name), 'type': 'output'})
            tiles.append(tile)
            progress.update_absolute(i+1)
        comic = assemble(tiles, spalten, titel, signatur)
        metadata = PngInfo()
        if prompt is not None:
            metadata.add_text('prompt', json.dumps(prompt, ensure_ascii=False))
        for key, value in (extra_pnginfo or {}).items():
            metadata.add_text(key, json.dumps(value, ensure_ascii=False))
        name = base+'.png'
        comic.save(Path(folder)/name, pnginfo=metadata)
        return {'ui': {'images': [{'filename': name, 'subfolder': subfolder, 'type': 'output'}], 'comic_panels': previews},
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
            'anzahl_kacheln': ('INT', {'default': 4, 'min': 1, 'max': 12}),
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
