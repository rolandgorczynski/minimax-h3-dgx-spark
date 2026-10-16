"""Download workflow models on the ComfyUI host, not in the browser."""
import asyncio
import hashlib
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

import aiohttp
from aiohttp import web
import folder_paths
from server import PromptServer

WEB_DIRECTORY = './web'
NODE_CLASS_MAPPINGS = {}
MODEL_SUFFIXES = {'.safetensors', '.sft', '.ckpt', '.pt', '.pth', '.bin', '.gguf', '.onnx'}
JOBS = {}
LOCK = asyncio.Lock()
TASKS = set()


def allowed_url(url, redirect=False):
    if not isinstance(url, str):
        raise ValueError("Invalid model URL.")
    parsed = urlsplit(url)
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('Only HTTPS model downloads from supported sources are allowed.')
    initial = host in {'huggingface.co', 'hf.co', 'github.com', 'civitai.com', 'civitai.red'}
    cdn = redirect and (host in {'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}
                       or host.endswith(('.hf.co', '.huggingface.co', '.xethub.hf.co', '.r2.cloudflarestorage.com', '.civitai.com', '.civitai.red')))
    if not initial and not cdn:
        raise ValueError(f'Unsupported download host: {host}')
    if host == 'github.com' and '/releases/download/' not in parsed.path:
        raise ValueError('GitHub URLs must point to a release asset.')
    return url


def destination(model):
    category = model.get('directory', '')
    category = {'unet': 'diffusion_models', 'clip': 'text_encoders'}.get(category, category)
    name = model.get('name', '')
    root = Path(folder_paths.models_dir).resolve()
    if category not in folder_paths.folder_names_and_paths or category in {'custom_nodes', 'configs', 'datasets', 'diffusers'}:
        raise ValueError('Unknown model folder; download location cannot be determined.')
    if not isinstance(name, str) or not name or '\\' in name or any(c in name for c in '\r\n\x00'):
        raise ValueError('Invalid model filename.')
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts or relative.suffix.lower() not in MODEL_SUFFIXES:
        raise ValueError('Invalid model filename or extension.')
    target = (root / category / relative).resolve()
    if not target.is_relative_to(root) or not target.is_relative_to((root / category).resolve()):
        raise ValueError('Model path escapes the model directory.')
    allowed_url(model.get('url', ''))
    return target


async def fetch_file(job, target):
    partial = target.with_name(target.name + '.dgx-part')
    marker = target.with_name(target.name + '.dgx-source')
    url = job['_url']
    # A partial file belongs to one source URL; never resume data from another.
    source_id = hashlib.sha256(url.encode()).hexdigest()
    if partial.exists() and (not marker.exists() or marker.read_text() != source_id):
        raise ValueError('Partial download belongs to another URL; remove its .dgx-part file first.')
    target.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(source_id)
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {'Accept-Encoding': 'identity'}
    if offset:
        headers['Range'] = f'bytes={offset}-'
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=120)
    async with aiohttp.ClientSession(timeout=timeout, auto_decompress=False) as session:
        current = url
        for _ in range(10):
            allowed_url(current, redirect=current != url)
            request_headers = dict(headers)
            if urlsplit(current).hostname in {'huggingface.co', 'hf.co'} and os.environ.get('HF_TOKEN'):
                request_headers['Authorization'] = 'Bearer ' + os.environ['HF_TOKEN']
            response = await session.get(current, headers=request_headers, allow_redirects=False)
            if response.status in {301, 302, 303, 307, 308}:
                from urllib.parse import urljoin
                location = response.headers.get('Location')
                response.release()
                if not location:
                    raise ValueError('Download redirect has no destination.')
                current = urljoin(current, location)
                continue
            break
        else:
            raise ValueError('Too many download redirects.')
        async with response:
            if response.status == 416:
                match = re.fullmatch(r'bytes \*/(\d+)', response.headers.get('Content-Range', ''))
                if match and int(match[1]) == offset and offset > 0:
                    job.update(downloaded=offset, total=offset)
                    os.link(partial, target)
                    partial.unlink()
                    marker.unlink(missing_ok=True)
                    folder_paths.filename_list_cache.clear()
                    return
            if response.status in {401, 403}:
                raise ValueError('Access denied. Accept the model license and configure HF_TOKEN on the DGX if required.')
            if response.status not in {200, 206}:
                raise ValueError(f'Model server returned HTTP {response.status}.')
            if any(t in response.headers.get('Content-Type', '').lower() for t in ('text/', 'json', 'xml')):
                raise ValueError('The link returned a web page instead of a model file.')
            total = None
            if response.status == 206:
                match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
                if not match or int(match[1]) != offset:
                    raise ValueError('The server returned an invalid resume range.')
                total = int(match[3])
            else:
                offset = 0  # Server ignored Range; safely restart the partial file.
                if response.content_length is not None:
                    total = response.content_length
            job.update(downloaded=offset, total=total)
            with partial.open('ab' if offset else 'wb') as output:
                async for data in response.content.iter_chunked(1024 * 1024):
                    output.write(data)
                    job['downloaded'] += len(data)
                    if total is not None and job['downloaded'] > total:
                        raise ValueError('Download exceeded the advertised file size.')
            if job['downloaded'] == 0 or (total is not None and job['downloaded'] != total):
                raise ValueError('Incomplete model download. Click download again to resume.')
    if target.exists():
        raise ValueError('A model appeared at the destination; refusing to overwrite it.')
    os.link(partial, target)
    partial.unlink()
    marker.unlink(missing_ok=True)
    folder_paths.filename_list_cache.clear()


async def download(job, target):
    async with LOCK:
        try:
            if target.exists():
                if not target.is_file() or target.stat().st_size == 0:
                    raise ValueError('Destination exists but is not a non-empty model file.')
                job.update(status='present', downloaded=target.stat().st_size, total=target.stat().st_size)
                return
            job['status'] = 'downloading'
            await fetch_file(job, target)
            job['status'] = 'complete'
        except Exception as error:
            # Never return URLs, signed query strings, or authorization headers.
            job.update(status='error', error=str(error) if isinstance(error, ValueError) else type(error).__name__ + ': download failed; retry to resume.')


def public_job(job):
    return {key: value for key, value in job.items() if not key.startswith('_')}


@PromptServer.instance.routes.get('/dgx-downloads/jobs')
async def jobs(request):
    return web.json_response([public_job(job) for job in JOBS.values()])


@PromptServer.instance.routes.post('/dgx-downloads/jobs')
async def start(request):
    if request.headers.get('X-DGX-Download') != '1' or request.content_type != 'application/json':
        raise web.HTTPForbidden(text='Use the ComfyUI download interface.')
    origin = request.headers.get('Origin')
    if origin and urlsplit(origin).netloc != request.host:
        raise web.HTTPForbidden(text='Cross-origin downloads are not allowed.')
    try:
        models = await request.json()
        if not isinstance(models, list) or not 1 <= len(models) <= 100:
            raise ValueError('Select between 1 and 100 models.')
        validated = [(model, destination(model)) for model in models if isinstance(model, dict)]
        if len(validated) != len(models):
            raise ValueError('Invalid model list.')
        sources = {}
        for model, target in validated:
            key = str(target.relative_to(Path(folder_paths.models_dir).resolve()))
            old = JOBS.get(key)
            if (target in sources and sources[target] != model['url']) or (old and old['status'] in {'queued', 'downloading'} and old['_url'] != model['url']):
                raise ValueError('Another download already targets this filename.')
            sources[target] = model['url']
        result = []
        for model, target in validated:
            key = str(target.relative_to(Path(folder_paths.models_dir).resolve()))
            old = JOBS.get(key)
            if old and old['status'] in {'queued', 'downloading'}:
                if old['_url'] != model['url']:
                    raise ValueError('Another download already targets this filename.')
                result.append(public_job(old))
                continue
            job = dict(id=key, name=model['name'], directory=model['directory'], status='queued', downloaded=0, total=None, _url=model['url'])
            JOBS[key] = job
            task = asyncio.create_task(download(job, target))
            TASKS.add(task)
            task.add_done_callback(TASKS.discard)
            result.append(public_job(job))
        return web.json_response(result, status=202)
    except (ValueError, TypeError) as error:
        return web.json_response({'error': str(error)}, status=400)
