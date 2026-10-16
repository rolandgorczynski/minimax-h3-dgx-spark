"""Reusable local invitation cards with original logo and exact editable text."""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import torch
import folder_paths

from .design import FORMATS, PALETTES, render_card

WEB_DIRECTORY = './web'
DEFAULTS = {
    'veranstaltung': 'WINTER\nABEND',
    'veranstalter': 'Nordlicht Atelier',
    'einladungstext': 'Ein Abend für gute Gespräche,\nfeine Klänge und neue Begegnungen.',
    'datum': 'Samstag, 5. Dezember 2026',
    'uhrzeit': 'ab 18:30 Uhr',
    'ort': 'Atelier am Fluss\nUferstraße 12 · 10115 Berlin',
    'rueckmeldung': 'Rückmeldung bis 25. November\nhallo@nordlicht.example',
    'stil': 'Mitternacht & Gold',
    'format': 'A5 Hochformat',
    'akzentfarbe': '',
    'hintergrundfarbe': '',
    'hintergrund_staerke': 0.25,
    'dateiname': 'einladungen/nordlicht',
}


def pil_image(tensor):
    return Image.fromarray(np.clip(tensor[0].detach().cpu().numpy() * 255, 0, 255).astype(np.uint8))


class DGXInvitation:
    @classmethod
    def INPUT_TYPES(cls):
        required = {}
        for key in ('veranstaltung', 'veranstalter', 'einladungstext', 'datum', 'uhrzeit', 'ort', 'rueckmeldung'):
            required[key] = ('STRING', {'default': DEFAULTS[key], 'multiline': key in {'veranstaltung', 'einladungstext', 'ort', 'rueckmeldung'}})
        required.update({
            'stil': (list(PALETTES),),
            'format': (list(FORMATS),),
            'akzentfarbe': ('STRING', {'default': '', 'tooltip': 'Leer = Stilfarbe. Eigene Farbe als #RRGGBB, zum Beispiel #C5A46C.'}),
            'hintergrundfarbe': ('STRING', {'default': '', 'tooltip': 'Leer = Stilfarbe. Eigene Farbe als #RRGGBB.'}),
            'hintergrund_staerke': ('FLOAT', {'default': 0.25, 'min': 0, 'max': 1, 'step': 0.05, 'tooltip': 'Wird nur verwendet, wenn ein eigenes Hintergrundbild angeschlossen ist.'}),
            'dateiname': ('STRING', {'default': DEFAULTS['dateiname']}),
        })
        return {'required': required,
                'optional': {'logo': ('IMAGE',), 'logo_maske': ('MASK',), 'bildhintergrund': ('IMAGE',)},
                'hidden': {'prompt': 'PROMPT', 'extra_pnginfo': 'EXTRA_PNGINFO'}}

    RETURN_TYPES = ('IMAGE',)
    RETURN_NAMES = ('vorschau',)
    FUNCTION = 'create'
    CATEGORY = 'DGX/Einladungen'
    OUTPUT_NODE = True
    DESCRIPTION = 'Einladung mit austauschbarem Logo und exaktem Text. Speichert Druck-PNG, PDF, WhatsApp-PNG und die Textvorlage lokal. Keine Modell-Downloads nötig.'

    def create(self, logo=None, logo_maske=None, bildhintergrund=None, prompt=None, extra_pnginfo=None, **values):
        prefix = values.pop('dateiname')
        mark = pil_image(logo).convert('RGBA') if logo is not None else None
        if mark is not None and logo_maske is not None:
            alpha = Image.fromarray(np.clip((1-logo_maske[0].detach().cpu().numpy()) * 255, 0, 255).astype(np.uint8))
            if alpha.size != mark.size:
                alpha = alpha.resize(mark.size, Image.Resampling.LANCZOS)
            mark.putalpha(alpha)
        background = pil_image(bildhintergrund) if bildhintergrund is not None else None
        image = render_card(**values, logo=mark, background=background)
        output = folder_paths.get_output_directory()
        folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(prefix, output, *image.size)
        base = f'{filename}_{counter:05}_'
        metadata = PngInfo()
        if prompt is not None:
            metadata.add_text('prompt', json.dumps(prompt, ensure_ascii=False))
        for key, value in (extra_pnginfo or {}).items():
            metadata.add_text(key, json.dumps(value, ensure_ascii=False))
        names = {'Druck-PNG · 300 dpi': base+'druck.png', 'PDF zum Drucken': base+'druck.pdf',
                 'WhatsApp-PNG': base+'mobil.png', 'Textvorlage (JSON)': base+'vorlage.json'}
        image.save(Path(folder)/names['Druck-PNG · 300 dpi'], pnginfo=metadata, dpi=(300, 300))
        image.save(Path(folder)/names['PDF zum Drucken'], 'PDF', resolution=300.0, quality=95)
        mobile = image.copy()
        mobile.thumbnail((1080, 1920), Image.Resampling.LANCZOS)
        mobile.save(Path(folder)/names['WhatsApp-PNG'], pnginfo=metadata)
        (Path(folder)/names['Textvorlage (JSON)']).write_text(json.dumps(values | {'dateiname': prefix}, ensure_ascii=False, indent=2)+'\n')
        files = [dict(label=label, filename=name, subfolder=subfolder, type='output') for label, name in names.items()]
        preview = dict(filename=names['WhatsApp-PNG'], subfolder=subfolder, type='output')
        return {'ui': {'images': [preview], 'invitation_files': files},
                'result': (torch.from_numpy(np.array(image).astype(np.float32)/255.0).unsqueeze(0),)}


NODE_CLASS_MAPPINGS = {'DGXInvitation': DGXInvitation}
NODE_DISPLAY_NAME_MAPPINGS = {'DGXInvitation': 'Einladung gestalten · Logo & Text'}
