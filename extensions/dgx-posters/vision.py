"""Bounded URL image loading and offline image captioning for poster references."""
from io import BytesIO
import ipaddress
import re
from pathlib import Path
import socket
import threading
from urllib.parse import urlsplit, urlunsplit
import urllib.request

from PIL import Image, ImageOps

MODEL_ID = 'HuggingFaceTB/SmolVLM-500M-Instruct'
MODEL_REVISION = 'a7da5b986cb59b408707209984f360a5f4ad7e47'
MAX_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 20_000_000
_LOCK = threading.Lock()


def normalize_url(url):
    parts = urlsplit(url.strip())
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise ValueError('Podaj link HTTP/HTTPS do obrazka, bez loginu i hasła.')
    if parts.hostname.lower() == 'github.com':
        path = parts.path.split('/')
        if len(path) >= 6 and path[3] == 'blob':
            parts = parts._replace(netloc='raw.githubusercontent.com', path='/'.join(path[:3]+path[4:]), query='')
    return urlunsplit(parts._replace(fragment=''))


def validate_url(url):
    parts = urlsplit(normalize_url(url))
    # Only ComfyUI's read-only image endpoint is permitted on this trusted LAN host.
    if parts.hostname in ('192.168.1.224', '127.0.0.1', 'localhost') and parts.port == 8188 and parts.path == '/view':
        return urlunsplit(parts)
    addresses = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == 'https' else 80), type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError('Link musi wskazywać publiczny obrazek lub endpoint /view lokalnego ComfyUI.')
    return urlunsplit(parts)


class CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, validate_url(newurl))


def load_url(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), CheckedRedirect())
    request = urllib.request.Request(validate_url(url), headers={'User-Agent': 'DGX-Poster/1.0', 'Accept': 'image/*'})
    with opener.open(request, timeout=30) as response:
        if int(response.headers.get('Content-Length', 0)) > MAX_BYTES:
            raise ValueError('Obrazek przekracza 20 MB.')
        data = response.read(MAX_BYTES+1)
    if len(data) > MAX_BYTES:
        raise ValueError('Obrazek przekracza 20 MB.')
    try:
        image = Image.open(BytesIO(data))
        if image.width * image.height > MAX_PIXELS:
            raise ValueError('Obrazek przekracza 20 megapikseli.')
        image = ImageOps.exif_transpose(image).convert('RGB')
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        return image
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError('Link nie zwrócił obrazka. Użyj bezpośredniego JPG, PNG lub WebP; strony i posty wymagające logowania nie działają.') from exc


def clean_caption(value):
    # Small VLMs sometimes append OCR despite the instruction; omit labelled OCR sections.
    return '\n'.join(line for line in value.splitlines()
                     if not re.match(r'^\s*(text|logo|logos|lettering|sponsors?|event information)\s*:', line, re.I)).strip()


def caption(image, model_path, instruction, max_tokens):
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor
    if not (Path(model_path)/'model.safetensors').is_file():
        raise ValueError('Brak lokalnego modelu vision. Uruchom scripts/download_poster_vision.sh.')
    # Release the model after each caption so FLUX/video generation can use the memory.
    with _LOCK:
        processor = AutoProcessor.from_pretrained(model_path, local_files_only=True)
        model = AutoModelForImageTextToText.from_pretrained(model_path, local_files_only=True,
                    dtype=torch.float32, attn_implementation='eager').to('cpu').eval()
        messages = [{'role': 'user', 'content': [{'type': 'image'}, {'type': 'text', 'text': instruction}]}]
        prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
        inputs = processor(text=prompt, images=[image], return_tensors='pt')
        with torch.inference_mode():
            generated = model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False)
        result = clean_caption(processor.batch_decode(generated[:, inputs['input_ids'].shape[1]:], skip_special_tokens=True)[0])
        del model, processor
    if not result:
        raise ValueError('Model vision zwrócił pusty opis.')
    return result
