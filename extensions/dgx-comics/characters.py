"""Persistent character profiles and immutable reference images, separate from stories."""
import hashlib
import io
import json
import re
import threading
import uuid
from pathlib import Path
from PIL import Image, ImageOps

LOCK = threading.RLock()
ID = re.compile(r'^[a-f0-9]{32}$')
SYSOP_ID = uuid.uuid5(uuid.NAMESPACE_URL, 'dgx-comics/default-sysop').hex


def is_sysop(character):
    return character.get('id') == SYSOP_ID or any(name.casefold() == 'sysop' for name in [character.get('name',''), *character.get('aliases',[])])


ASSET = re.compile(r'^[a-f0-9]{64}\.png$')


def validate_character(value):
    if not isinstance(value, dict):
        raise ValueError('Eine Figur muss ein Objekt sein.')
    result = {}
    for key, limit in [('name', 100), ('description', 2500), ('outfit', 1000), ('story_outfit', 1000)]:
        text = value.get(key, '')
        if not isinstance(text, str) or len(text) > limit:
            raise ValueError(f'{key}: maximal {limit} Zeichen.')
        result[key] = text.strip()
    if not result['name'] or not result['description']:
        raise ValueError('Name und festes Aussehen bitte ausfüllen.')
    aliases = value.get('aliases', [])
    if not isinstance(aliases, list) or len(aliases) > 12 or any(not isinstance(x, str) or not x.strip() or len(x) > 100 for x in aliases):
        raise ValueError('Maximal 12 alternative Namen angeben.')
    result['aliases'] = [x.strip() for x in aliases]
    variants = value.get('variants', {})
    if not isinstance(variants, dict) or len(variants) > 12 or any(not isinstance(k, str) or not k.strip() or len(k)>100 or not isinstance(v, str) or len(v)>1000 for k,v in variants.items()):
        raise ValueError('Ungültige Kleidungsvarianten.')
    result['variants'] = variants
    ident = value.get('id', '')
    if not isinstance(ident, str) or (ident and not ID.fullmatch(ident)):
        raise ValueError('Ungültige Figuren-ID.')
    result['id'] = ident
    refs = value.get('references', [])
    if not isinstance(refs, list) or len(refs)>2 or any(not isinstance(x,str) or not ASSET.fullmatch(x) for x in refs):
        raise ValueError('Maximal zwei gültige Referenzbilder pro Figur.')
    result['references'] = refs
    inline=value.get('inline_references',[])
    if not isinstance(inline,list) or len(inline)>2 or any(not isinstance(x,str) or len(x)>8_000_000 for x in inline):
        raise ValueError('Maximal zwei eingebettete Referenzbilder pro Figur.')
    if inline:result['inline_references']=inline
    return result


def read_cast(value):
    cast = json.loads(value or '[]') if isinstance(value, str) else value
    if not isinstance(cast, list) or len(cast)>8:
        raise ValueError('Maximal acht Figuren pro Geschichte auswählen.')
    cast = [validate_character(item) for item in cast]
    if any(not c['id'] for c in cast) or len({c['id'] for c in cast}) != len(cast):
        raise ValueError('Figuren benötigen eindeutige gespeicherte IDs.')
    names = [name.casefold() for c in cast for name in [c['name'], *c['aliases']]]
    if len(names) != len(set(names)):
        raise ValueError('Namen und alternative Namen müssen innerhalb dieser Geschichte eindeutig sein.')
    return cast


def canonical_speaker(name, cast):
    for c in cast:
        if name.casefold() in [x.casefold() for x in [c['id'],c['name'],*c['aliases']]]:
            return c['id']
    return name


def explicit_speech(source):
    pattern = r'([A-ZÄÖÜ][\wÄÖÜäöüß -]{0,59}):\s*["„“»]([^"“”«»\n]{1,400})["“”«»]'
    return [{'speaker':name.strip(),'text':text.strip(),'expression':'shout' if text.count('!')>1 else 'normal'}
            for name,text in re.findall(pattern,source)]


def scene_cast(scene, cast):
    speakers={canonical_speaker(b['speaker'],cast) for b in scene.get('bubbles',[])}
    if 'characters' in scene:
        return [c for c in cast if c['id'] in scene['characters'] or c['id'] in speakers]
    text = scene['story']+' '+scene.get('dialog', '')
    return [c for c in cast if any(re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)', text, re.I) for name in [c['name'], *c['aliases']]) or c['id'] in speakers]


def character_prompt(c):
    outfit = c.get('story_outfit') or c['outfit']
    return f"{c['name']} (ID {c['id']}; aliases: {', '.join(c['aliases'])}): fixed identity: {c['description']}. Clothing: {outfit}. Keep face, age, hair and body consistent."


class CharacterLibrary:
    def __init__(self, root):
        self.root = Path(root)

    def ensure_sysop(self, reference=None):
        """Seed once, retaining any existing user-edited Sysop and reference files."""
        with LOCK:
            existing=next((c for c in self.list() if is_sysop(c)),None)
            if existing:
                return existing
            if any(is_sysop(json.loads(p.read_text())) for p in (self.root/'archived').glob('*.json')):
                return None
            profile=self.save({'id':SYSOP_ID,'name':'Sysop','description':
                'Middle-aged man with shoulder-length wavy dark brown hair, full dark beard with subtle grey strands and strong eyebrows.',
                'outfit':'Black tuxedo jacket, white shirt and black bow tie.',
                'variants':{'Noir':'Dunkler Mantel; als Erzähler-Silhouette im Schatten.'},'aliases':[],'references':[]})
            if reference is not None and Path(reference).is_file():
                profile=self.upload(profile['id'],Path(reference).read_bytes(),0)
            return profile

    def path(self, ident):
        if not isinstance(ident, str) or not ID.fullmatch(ident):
            raise ValueError('Ungültige Figuren-ID.')
        return self.root/(ident+'.json')

    def list(self):
        self.root.mkdir(parents=True, exist_ok=True)
        return sorted([json.loads(p.read_text()) for p in self.root.glob('*.json')], key=lambda c: c['name'].casefold())

    def save(self, value):
        c = validate_character(value)
        with LOCK:
            self.root.mkdir(parents=True, exist_ok=True)
            c['id'] = c['id'] or uuid.uuid4().hex
            path = self.path(c['id'])
            if (self.root/'archived'/path.name).exists():
                raise ValueError('Diese Figur wurde aus der Bibliothek gelöscht. Bitte eine neue Figur anlegen.')
            previous = json.loads(path.read_text()) if path.exists() else {}
            if value.get('version', 0) != previous.get('version', 0):
                raise ValueError('Die Figur wurde inzwischen geändert. Bitte Bibliothek neu laden.')
            c['version'] = previous.get('version', 0)+1
            c.pop('story_outfit', None)
            for ref in c['references']:
                self.reference_path(c['id'], ref)
            temporary = path.with_suffix('.tmp')
            temporary.write_text(json.dumps(c, ensure_ascii=False, indent=2)+'\n')
            temporary.replace(path)
            return c

    def delete(self, ident, version):
        """Remove the library entry; retain story snapshots and immutable assets."""
        with LOCK:
            path=self.path(ident)
            current=json.loads(path.read_text())
            if isinstance(version,bool) or not isinstance(version,int) or version!=current.get('version',0):
                raise ValueError('Die Figur wurde inzwischen geändert. Bitte Bibliothek neu laden.')
            archive=self.root/'archived'
            archive.mkdir(parents=True,exist_ok=True)
            path.replace(archive/path.name)
            return current

    def reference_path(self, ident, asset):
        self.path(ident)
        if not isinstance(asset, str) or not ASSET.fullmatch(asset):
            raise ValueError('Ungültiges Referenzbild.')
        path = self.root/'references'/ident/asset
        if not path.is_file():
            raise ValueError('Referenzbild fehlt. Bitte in der Figurenbibliothek erneut hochladen.')
        return path

    def upload(self, ident, data, slot):
        if slot not in (0, 1) or len(data)>12*1024*1024:
            raise ValueError('Maximal zwei Bilder mit jeweils 12 MB.')
        with LOCK:
            c = json.loads(self.path(ident).read_text())
            with Image.open(io.BytesIO(data)) as image:
                if image.width*image.height>25_000_000:
                    raise ValueError('Referenzbild maximal 25 Megapixel.')
                image = ImageOps.exif_transpose(image).convert('RGB')
                image.thumbnail((1536,1536))
                output = io.BytesIO(); image.save(output,format='PNG')
            pixels = output.getvalue()
            asset = hashlib.sha256(pixels).hexdigest()+'.png'
            folder = self.root/'references'/ident
            folder.mkdir(parents=True, exist_ok=True)
            (folder/asset).write_bytes(pixels)
            refs = c['references'][:]
            if slot>=len(refs): refs.append(asset)
            else: refs[slot]=asset
            c['references'] = refs
            return self.save(c)


def library():
    import folder_paths
    result=CharacterLibrary(Path(folder_paths.get_user_directory())/'default/dgx-comics/characters')
    result.ensure_sysop(Path(folder_paths.get_input_directory())/'sysop-reference.png')
    return result


def register_routes():
    from aiohttp import web
    from server import PromptServer
    if getattr(PromptServer, 'instance', None) is None:
        return
    routes = PromptServer.instance.routes

    @routes.get('/dgx-comics/characters')
    async def list_characters(request):
        return web.json_response({'characters': library().list()})

    @routes.post('/dgx-comics/characters')
    async def save_character(request):
        try:
            return web.json_response(library().save(await request.json()))
        except (ValueError, TypeError) as exc:
            return web.json_response({'error': str(exc)},status=400)

    @routes.delete('/dgx-comics/characters/{id}')
    async def delete_character(request):
        try:
            value=await request.json()
            if not isinstance(value,dict):
                raise ValueError('Ungültige Löschanfrage.')
            deleted=library().delete(request.match_info['id'],value.get('version'))
            return web.json_response({'deleted':deleted['id'],'name':deleted['name']})
        except FileNotFoundError:
            return web.json_response({'error':'Figur nicht gefunden.'},status=404)
        except (ValueError,TypeError) as exc:
            return web.json_response({'error':str(exc)},status=400)

    @routes.post('/dgx-comics/characters/{id}/references/{slot}')
    async def upload_reference(request):
        try:
            reader = await request.multipart()
            part = await reader.next()
            if part is None:
                raise ValueError('Bild fehlt.')
            data = bytearray()
            while True:
                chunk = await part.read_chunk()
                if not chunk: break
                data.extend(chunk)
                if len(data)>12*1024*1024: raise ValueError('Bild maximal 12 MB.')
            return web.json_response(library().upload(request.match_info['id'],data,int(request.match_info['slot'])))
        except (ValueError, TypeError, OSError) as exc:
            return web.json_response({'error': str(exc)},status=400)

    @routes.get('/dgx-comics/characters/{id}/references/{asset}')
    async def view_reference(request):
        try:
            return web.FileResponse(library().reference_path(request.match_info['id'],request.match_info['asset']))
        except ValueError as exc:
            return web.json_response({'error': str(exc)},status=404)
