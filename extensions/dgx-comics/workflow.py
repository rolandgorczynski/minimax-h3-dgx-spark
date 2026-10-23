"""One editor with an explicit planning and rendering boundary."""
import json
import torch
from .story import STYLES, plan_story


class DGXComicWorkflow:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'referenz': ('IMAGE',), 'model': ('MODEL',), 'clip': ('CLIP',), 'vae': ('VAE',),
            'artikel': ('STRING', {'default': '', 'multiline': True}),
            'comic_art': (list(STYLES),),
            'anzahl_kacheln': ('INT', {'default': 12, 'min': 1, 'max': 9007199254740991}),
            'aktion': (['Szenen planen', 'Comic generieren'],),
            'titel': ('STRING', {'default': ''}),
            'spalten': ('INT', {'default': 3, 'min': 1, 'max': 4}),
            'signatur': ('STRING', {'default': 'sysop1984.substack.com'}),
            'seed': ('INT', {'default': 1984, 'min': 0, 'max': 2147483647, 'control_after_generate': False}),
            'bearbeiteter_plan': ('STRING', {'default': '', 'multiline': True}),
            'kachel_revisionen': ('STRING', {'default': '{}'}),
        }, 'optional': {'figuren': ('STRING', {'default': '[]', 'multiline': True})}, 'hidden': {'prompt': 'PROMPT', 'extra_pnginfo': 'EXTRA_PNGINFO', 'unique_id': 'UNIQUE_ID'}}

    @classmethod
    def VALIDATE_INPUTS(cls, artikel):
        if not artikel.strip():
            return 'Bitte zuerst den Originalartikel oder die Gesamtgeschichte eingeben.'
        if len(artikel)>16000:
            return 'Die Gesamtgeschichte darf maximal 16000 Zeichen enthalten.'
        return True

    RETURN_TYPES = ('IMAGE',)
    RETURN_NAMES = ('comic',)
    FUNCTION = 'run'
    CATEGORY = 'DGX/Comics'
    OUTPUT_NODE = True

    def run(self, referenz, model, clip, vae, artikel, comic_art, anzahl_kacheln,
            aktion, titel, spalten, signatur, seed, bearbeiteter_plan='',
            kachel_revisionen='{}', prompt=None, extra_pnginfo=None, unique_id=None, figuren='[]', automation_session=''):
        from . import DGXSysopComic
        from .story import source_hash, read_plan, plan_matches
        from .characters import read_cast
        cast = read_cast(figuren)
        style = STYLES[comic_art].replace('Sysop is a narrator silhouette in a dark coat.', '').replace('realistic people.', 'realistic illustration.')
        if aktion == 'Szenen planen':
            scenes, fingerprint = plan_story(clip, artikel, anzahl_kacheln, seed, bearbeiteter_plan, style, cast=cast)
            saved = json.dumps({'source_hash': fingerprint, 'scenes': scenes}, ensure_ascii=False)
            return {'ui': {'comic_plan': [saved]}, 'result': (torch.zeros((1, 1, 1, 3)),)}
        # Rendering must never silently replace edits or start a new language-model plan.
        try:
            saved = json.loads(bearbeiteter_plan)
            if not plan_matches(saved, artikel, anzahl_kacheln, seed):
                raise ValueError('outdated')
            scenes = read_plan(saved['scenes'], anzahl_kacheln)
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError('Bitte zuerst Szenen planen, prüfen und danach Comic generieren wählen.') from exc
        revisions = json.loads(kachel_revisionen)
        if not isinstance(revisions, dict) or any(not isinstance(v, int) or v < 0 for v in revisions.values()):
            raise ValueError('Ungültige Kachelrevisionen.')
        def upstream(value):
            if isinstance(value, list) and len(value) == 2 and str(value[0]) in (prompt or {}):
                node = prompt[str(value[0])]
                return [node['class_type'], {key: upstream(item) for key, item in node['inputs'].items()}, value[1]]
            return value
        inputs = (prompt or {}).get(str(unique_id), {}).get('inputs', {})
        model_identity = json.dumps([upstream(inputs[name]) for name in ('model', 'clip', 'vae')], sort_keys=True) if all(name in inputs for name in ('model', 'clip', 'vae')) else None
        temporary={}
        if automation_session:
            from .automation import session_directory
            root=session_directory(automation_session)
            root.mkdir(parents=True,exist_ok=True)
            temporary={'output_directory':str(root),'image_type':'temp','image_subfolder_prefix':f'comic-automation/{automation_session}'}
        result = DGXSysopComic().create(
            referenz, model, clip, vae, anzahl_kacheln, spalten, titel,
            '',
            style, json.dumps(scenes, ensure_ascii=False), signatur, seed, 'comic' if automation_session else 'comics/artikel',
            prompt, extra_pnginfo, revisions=revisions, reuse_panels=True, model_identity=model_identity, cast=cast, library_cast=True,**temporary)
        result['ui']['comic_plan'] = [bearbeiteter_plan]
        return result


class DGXComicStudio(DGXComicWorkflow):
    """Library-only workflow without the legacy shared Sysop image input."""
    @classmethod
    def INPUT_TYPES(cls):
        inputs=super().INPUT_TYPES()
        del inputs['required']['referenz']
        inputs['optional']['automation_session']=('STRING',{'forceInput':True})
        return inputs

    def run(self, **inputs):
        return super().run(referenz=None, **inputs)
