"""CPU-only lettering preview; never calls an image model."""
import io
import json
from pathlib import Path
from PIL import Image


def register_speech_routes():
    from aiohttp import web
    from server import PromptServer
    import folder_paths
    from .design import parse_scenes, panel
    if getattr(PromptServer,'instance',None) is None:
        return

    @PromptServer.instance.routes.post('/dgx-comics/lettering-preview')
    async def preview(request):
        try:
            data=await request.json()
            scene=parse_scenes(json.dumps([data['scene']]),1)[0]
            names=data.get('names',{})
            if not isinstance(names,dict) or len(names)>8 or any(not isinstance(k,str) or not isinstance(v,str) or len(v)>100 for k,v in names.items()):
                raise ValueError('Ungültige Sprechernamen.')
            number=data.get('number',1)
            if isinstance(number,bool) or not isinstance(number,int) or number<1:
                raise ValueError('Ungültige Kachelnummer.')
            art=data.get('art')
            image=Image.new('RGB',(1024,704),'#75808b')
            if art:
                if not isinstance(art,dict) or art.get('type')!='output':
                    raise ValueError('Nur erzeugte Illustrationen verwenden.')
                root=Path(folder_paths.get_output_directory()).resolve()
                filename=art.get('filename','')
                subfolder=art.get('subfolder','')
                if not isinstance(filename,str) or not isinstance(subfolder,str):
                    raise ValueError('Ungültiger Bildpfad.')
                path=(root/subfolder/filename).resolve()
                if not path.is_relative_to(root) or path.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):
                    raise ValueError('Ungültiger Bildpfad.')
                with Image.open(path) as original:
                    if original.width*original.height>25_000_000:
                        raise ValueError('Vorschaubild zu groß.')
                    image=original.convert('RGB')
            result=panel(image,scene['dialog'],number,scene.get('bubbles'),names)
            buffer=io.BytesIO();result.save(buffer,format='PNG')
            return web.Response(body=buffer.getvalue(),content_type='image/png',headers={'Cache-Control':'no-store'})
        except (ValueError,KeyError,TypeError,OSError) as exc:
            return web.json_response({'error':str(exc)},status=400)
