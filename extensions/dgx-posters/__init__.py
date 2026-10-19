"""Local FLUX 9B art and deterministic Polish Facebook poster layout."""
import base64
from io import BytesIO
import json
from pathlib import Path
import urllib.error
import urllib.request

import folder_paths
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import torch
from .design import compose

WEB_DIRECTORY = './web'


class DGXPoster:
    @classmethod
    def INPUT_TYPES(cls):
        fields = {
            'organizator': 'Rada Kobiet Gminy Mirsk',
            'tytul': 'UMIEĆ POMÓC. BYĆ GOTOWYM.',
            'tematy': 'Umieć pomóc – praktyczne warsztaty pierwszej pomocy\nProwadzą: Małgorzata Kubś i Wioleta Chylińska\n\nRodzina gotowa na kryzys – dom, zapasy i plecak ewakuacyjny\nProwadzi: Iwona Szkudlatek',
            'data': '2026-10-26',
            'godziny': '16:00–20:00',
            'miejsce': 'Sala gimnastyczna · Zespół Szkolno-Przedszkolny w Mirsku\nul. Wodna 2, Mirsk',
            'opis_ilustracji': 'Fotografia redakcyjna: apteczka i fantom do nauki pierwszej pomocy po lewej, plecak ewakuacyjny, woda, konserwy, latarka i radio po prawej. W tle góry i las. Bez napisów, bez ludzi.',
        }
        required = {k: ('STRING', {'default': v, 'multiline': k not in ('data', 'godziny')}) for k, v in fields.items()}
        required.update({'generuj_obraz': ('BOOLEAN', {'default': True}),
                         'ziarno': ('INT', {'default': 42, 'min': 0, 'max': 2147483647, 'control_after_generate': True}),
                         'nazwa_pliku': ('STRING', {'default': 'plakaty/mirsk'})})
        return {'required': required, 'optional': {'logo': ('IMAGE',), 'maska_logo': ('MASK',),
                'belka': ('IMAGE',), 'maska_belki': ('MASK',), 'wlasna_ilustracja': ('IMAGE',),
                'herb': ('IMAGE',), 'maska_herbu': ('MASK',),
                'pokaz_belke': ('BOOLEAN', {'default': True}),
                'pokaz_herb': ('BOOLEAN', {'default': True}),
                'opis_z_obrazu': ('STRING', {'forceInput': True})},
                'hidden': {'prompt': 'PROMPT', 'extra_pnginfo': 'EXTRA_PNGINFO'}}

    RETURN_TYPES = ('IMAGE',)
    RETURN_NAMES = ('plakat',)
    FUNCTION = 'create'
    CATEGORY = 'DGX/Plakaty'
    OUTPUT_NODE = True
    DESCRIPTION = 'Plakat Facebook 1080×1350. FLUX 9B tworzy ilustrację lokalnie; napisy i logo nakładane są osobno. Belka opcjonalna. Data: RRRR-MM-DD.'

    @staticmethod
    def pil(tensor, mask=None):
        if tensor is None:
            return None
        image = Image.fromarray(np.clip(tensor[0].detach().cpu().numpy()*255, 0, 255).astype(np.uint8)).convert('RGBA')
        if mask is not None:
            alpha = Image.fromarray(np.clip((1-mask[0].detach().cpu().numpy())*255, 0, 255).astype(np.uint8))
            image.putalpha(alpha.resize(image.size))
        return image

    def create(self, organizator, tytul, tematy, data, godziny, miejsce, opis_ilustracji,
               generuj_obraz, ziarno, nazwa_pliku, logo=None, maska_logo=None, belka=None,
               maska_belki=None, wlasna_ilustracja=None, prompt=None, extra_pnginfo=None,
               herb=None, maska_herbu=None, pokaz_belke=True, pokaz_herb=True, opis_z_obrazu=None):
        if opis_z_obrazu is not None:
            opis_ilustracji = opis_z_obrazu
        art = self.pil(wlasna_ilustracja)
        if generuj_obraz:
            config_path = Path(folder_paths.get_user_directory()) / 'default/dgx-posters.json'
            if not config_path.is_file():
                raise ValueError('Brak konfiguracji lokalnego FLUX. Zobacz examples/posters/README.md.')
            config = json.loads(config_path.read_text())
            payload = {'model': 'flux.2-klein-9b', 'prompt': opis_ilustracji + '\nEditorial photograph, no text, no letters, no logos, wide composition.',
                       'size': '1792x1024', 'n': 1, 'seed': ziarno, 'response_format': 'b64_json'}
            request = urllib.request.Request(config['url'].rstrip('/')+'/images/generations',
                      data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json',
                      'Authorization': 'Bearer '+config['api_key']})
            try:
                with urllib.request.urlopen(request, timeout=600) as response:
                    result = json.load(response)
                art = Image.open(BytesIO(base64.b64decode(result['data'][0]['b64_json']))).convert('RGB')
            except (urllib.error.URLError, KeyError, ValueError) as exc:
                raise RuntimeError('Nie udało się wygenerować ilustracji. Sprawdź lokalny FLUX 9B lub podłącz własny obraz.') from exc
        if art is None:
            raise ValueError('Włącz generowanie obrazu lub podłącz własną ilustrację.')
        image = compose(organizator, tytul, tematy, data, godziny, miejsce, art,
                        self.pil(logo, maska_logo), self.pil(belka, maska_belki) if pokaz_belke else None,
                        self.pil(herb, maska_herbu) if pokaz_herb else None)
        folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(nazwa_pliku, folder_paths.get_output_directory(), *image.size)
        filename = f'{filename}_{counter:05}.png'
        metadata = PngInfo()
        if prompt is not None:
            metadata.add_text('prompt', json.dumps(prompt, ensure_ascii=False))
        for key, value in (extra_pnginfo or {}).items():
            metadata.add_text(key, json.dumps(value, ensure_ascii=False))
        image.save(Path(folder)/filename, pnginfo=metadata)
        return {'ui': {'images': [{'filename': filename, 'subfolder': subfolder, 'type': 'output'}]},
                'result': (torch.from_numpy(np.asarray(image).astype(np.float32)/255).unsqueeze(0),)}


NODE_CLASS_MAPPINGS = {'DGXPoster': DGXPoster}
NODE_DISPLAY_NAME_MAPPINGS = {'DGXPoster': 'Plakat na Facebooka · FLUX 9B · PL'}


class DGXImageURL:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'link': ('STRING', {'default': 'http://192.168.1.224:8188/view?filename=rkgm-reference.png&type=input', 'multiline': True})}}

    RETURN_TYPES = ('IMAGE',)
    RETURN_NAMES = ('obraz',)
    FUNCTION = 'load'
    CATEGORY = 'DGX/Plakaty'

    def load(self, link):
        from .vision import load_url
        image = load_url(link)
        return (torch.from_numpy(np.asarray(image).astype(np.float32)/255).unsqueeze(0),)


class DGXDescribeImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'obraz': ('IMAGE',),
                'instrukcja': ('STRING', {'default': 'Describe the photographic scene and visible objects in English for an image generation prompt. Include colors, background and visual style. Ignore all text, logos, sponsor strips and event information. Do not transcribe any lettering. Describe only what is visible.', 'multiline': True}),
                'maks_tokenow': ('INT', {'default': 180, 'min': 32, 'max': 384})},
                'optional': {'poprawiony_opis': ('STRING', {'default': '', 'multiline': True})}}

    RETURN_TYPES = ('STRING',)
    RETURN_NAMES = ('opis_ilustracji',)
    FUNCTION = 'describe'
    CATEGORY = 'DGX/Plakaty'
    OUTPUT_NODE = True
    DESCRIPTION = 'Lokalny SmolVLM opisuje obraz po angielsku dla FLUX. Poprawiony opis zastępuje wynik modelu; pusty uruchamia vision.'

    def describe(self, obraz, instrukcja, maks_tokenow, poprawiony_opis=''):
        from .vision import caption
        description = poprawiony_opis.strip()
        if not description:
            model_path = Path(folder_paths.models_dir)/'vision/SmolVLM-500M-Instruct'
            description = caption(DGXPoster.pil(obraz).convert('RGB'), model_path, instrukcja, maks_tokenow)
        return {'ui': {'text': [description]}, 'result': (description,)}


NODE_CLASS_MAPPINGS.update({'DGXImageURL': DGXImageURL, 'DGXDescribeImage': DGXDescribeImage})
NODE_DISPLAY_NAME_MAPPINGS.update({'DGXImageURL': 'Obraz z linku · JPG/PNG/WebP',
                                  'DGXDescribeImage': 'Vision · opisz obraz lokalnie'})
