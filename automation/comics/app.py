"""Small local HTTP API and one durable worker; standard library only."""
import hmac
import json
import logging
import mimetypes
import os
from pathlib import Path
import signal
import threading
import time
from urllib.parse import unquote, urlsplit
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from storage import Store
from comfy import Comfy
from engine import Engine, ID, TERMINAL, validate_request
from feedback import CRITERIA, validate_feedback
from local_llm import LocalOllama
from telegram_trigger import TelegramTrigger

LOG=logging.getLogger('comic-automation')


class Service:
    def __init__(self):
        self.store=Store(os.getenv('DATA_DIR','/data'))
        self.client=Comfy(os.getenv('COMFYUI_URL','http://comfyui:8188'),self.store,int(os.getenv('COMFYUI_PROMPT_TIMEOUT','3600')))
        self.engine=Engine(self.store,self.client,os.getenv('WORKFLOW_TEMPLATE','/app/workflow_template.json'),
                           os.getenv('TEXT_MODEL','qwen3vl_8b_fp8_scaled.safetensors'),os.getenv('VISION_MODEL','qwen3vl_8b_fp8_scaled.safetensors'))
        backend=os.getenv('LLM_BACKEND','comfyui')
        if backend not in ('comfyui','ollama'):raise ValueError('Nur lokale Backends comfyui und ollama sind erlaubt.')
        if backend=='ollama':
            self.engine.llm=LocalOllama(os.getenv('OLLAMA_URL','http://host.docker.internal:11434'),self.store,
                os.getenv('OLLAMA_TEXT_MODEL','gemma3:27b'),os.getenv('OLLAMA_CRITIC_MODEL','qwen3.6:35b-a3b'),
                os.getenv('OLLAMA_VISION_MODEL','qwen3.6:35b-a3b'))
        self.stop=threading.Event();self.token=os.getenv('API_TOKEN','')
        try:self.telegram=TelegramTrigger(self.store,self.stop,os.getenv('TELEGRAM_BOT_TOKEN',''),os.getenv('TELEGRAM_ALLOWED_CHAT_IDS',''),os.getenv('COMIC_PUBLIC_URL','http://192.168.1.224:8090'))
        except ValueError:
            self.telegram=TelegramTrigger(self.store,self.stop);self.telegram.status='invalid_configuration';self.telegram.error='Bot-Token-Format oder Chat-ID-Liste ungültig.'

    def capabilities(self):
        data=self.client.request('GET','/object_info')
        needed={'DGXComicStudio','DGXComicAssistant','DGXComicPortrait'}
        missing=needed-set(data)
        if missing:raise RuntimeError('ComfyUI-Erweiterung fehlt: '+', '.join(sorted(missing)))
        available=data['CLIPLoader']['input']['required']['clip_name'][0]
        for model in (() if self.engine.llm else (self.engine.text_model,self.engine.vision_model)):
            if model not in available:raise RuntimeError('Lokales Modell fehlt: '+model)
        for loader in self.engine.loaders.values():
            node=loader['class_type'];key={'UNETLoader':'unet_name','CLIPLoader':'clip_name','VAELoader':'vae_name'}[node]
            model=loader['inputs'][key]
            if model not in data[node]['input']['required'][key][0]:raise RuntimeError('Lokales Workflow-Modell fehlt: '+model)
        return {'ready':True,'local_only':True,'story_language':'de','german_required':True,'language_models':self.engine.llm.ready() if self.engine.llm else {
            'backend':'comfyui','text_model':self.engine.text_model,'vision_model':self.engine.vision_model},'workflow':'04_Comic_Automat_9B'}

    def cleanup(self,job):
        try:self.client.cleanup(job)
        except Exception as exc:
            LOG.warning('Cleanup pending for %s: %s',job,str(exc)[:200])
            self.store.update(job,cleanup_pending=True,cleanup_error=str(exc)[:1000])

    def worker(self):
        self.store.recover()
        while not self.stop.is_set():
            job=self.store.claim()
            if not job:
                for item in self.store.list():
                    if item['status'] in TERMINAL and item.get('cleanup_pending'):self.cleanup(item['id'])
                self.stop.wait(3);continue
            ident=job['id'];LOG.info('Starting %s',ident)
            try:
                self.capabilities()
                result=self.engine.execute(ident)
                # Artifacts were copied and hashed before remote cleanup.
                self.store.stage(ident,'finished',**result,cleanup_pending=True)
            except Exception as exc:
                LOG.exception('Job %s failed',ident)
                self.store.stage(ident,'failed',status='failed',error=str(exc)[:5000],cleanup_pending=True)
            finally:self.cleanup(ident)


class Handler(BaseHTTPRequestHandler):
    server_version='ComicAutomation/1.0'

    @property
    def service(self):return self.server.service

    def log_message(self,fmt,*args):LOG.info('%s '+fmt,self.client_address[0],*args)

    def reply(self,status,data):
        body=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)

    def authorized(self):
        expected=self.service.token
        if expected and not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+expected):
            self.reply(401,{'error':'Bearer-Token erforderlich.'});return False
        return True

    def do_GET(self):
        path=unquote(urlsplit(self.path).path)
        if path=='/health':return self.reply(200,{'status':'ok'})
        if path=='/':
            body=Path(__file__).with_name('index.html').read_bytes()
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
        if not self.authorized():return
        if path=='/telegram':return self.reply(200,self.service.telegram.info())
        if path=='/learning':return self.reply(200,self.service.store.learning_memory())
        if path=='/ready':
            try:return self.reply(200,self.service.capabilities())
            except Exception as exc:return self.reply(503,{'ready':False,'error':str(exc)[:2000]})
        if path=='/jobs':return self.reply(200,{'jobs':[self.public(job) for job in self.service.store.list()]})
        parts=path.strip('/').split('/')
        if len(parts)>=2 and parts[0]=='jobs' and ID.fullmatch(parts[1]):
            job=self.service.store.get(parts[1])
            if not job:return self.reply(404,{'error':'Auftrag nicht gefunden.'})
            if len(parts)==2:return self.reply(200,self.public(job))
            if len(parts)==3 and parts[2]=='story':return self.reply(200,self.story_preview(job))
            if len(parts)==3 and parts[2]=='feedback':
                return self.reply(200,{'optional':True,'scale':{'min':1,'max':5},'criteria':CRITERIA,'feedback':job.get('feedback'),
                                       'note':'Bewertungen wirken auf später gestartete Geschichten; laufende Aufträge behalten ihre Vorgaben.'})
            if len(parts)>=4 and parts[2]=='artifacts':
                root=self.service.store.directory(job['id']).resolve();file=(root/('/'.join(parts[3:]))).resolve()
                # Only finalized exported files listed in the manifest are downloadable.
                names={a['name'] for a in job.get('artifacts',[])}
                if not file.is_relative_to(root) or str(file.relative_to(root)) not in names or not file.is_file():
                    return self.reply(404,{'error':'Datei nicht gefunden.'})
                self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(str(file))[0] or 'application/octet-stream')
                self.send_header('Content-Length',str(file.stat().st_size));self.end_headers()
                with file.open('rb') as source:
                    while chunk:=source.read(65536):self.wfile.write(chunk)
                return
        return self.reply(404,{'error':'Endpoint nicht gefunden.'})

    def public(self,job):
        result={k:v for k,v in job.items() if k!='steps'}
        preview=self.story_preview(job)
        result['story_available']=preview['available'];result['story_title']=preview.get('title','')
        result['status_url']='/jobs/'+job['id'];return result

    def story_preview(self,job):
        # The engine writes this atomically after its mandatory German check.
        # Only this exact document is exposed before the artifact export finishes.
        path=self.service.store.directory(job['id'])/'story.json'
        try:
            value=json.loads(path.read_text())
            if not isinstance(value,dict) or not isinstance(value.get('title'),str) or not isinstance(value.get('story'),str):raise ValueError('Ungültige Geschichte')
            return {'available':True,'title':value['title'],'story':value['story']}
        except (FileNotFoundError,ValueError,TypeError):return {'available':False}

    def do_POST(self):
        parts=unquote(urlsplit(self.path).path).strip('/').split('/')
        if len(parts)==3 and parts[0]=='jobs' and ID.fullmatch(parts[1]) and parts[2] in ('feedback','next'):
            if not self.authorized():return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<=size<=65536:raise ValueError('Maximal 64 KB senden.')
                value=json.loads(self.rfile.read(size)) if size else {}
                if parts[2]=='feedback':
                    job=self.service.store.save_feedback(parts[1],validate_feedback(value))
                    return self.reply(200,{'saved':True,'feedback':job['feedback'],'applies_to':'future_jobs'})
                if value!={}:raise ValueError('POST /next ohne Parameter verwenden.')
                job,created=self.service.store.next_story(parts[1])
                return self.reply(202 if created else 200,self.public(job))
            except KeyError:return self.reply(404,{'error':'Auftrag nicht gefunden.'})
            except OverflowError as exc:return self.reply(429,{'error':str(exc)})
            except (ValueError,TypeError) as exc:return self.reply(400,{'error':str(exc)})
        self.create(False)
    def do_PUT(self):self.create(True)

    def create(self,is_put):
        if not self.authorized():return
        parts=unquote(urlsplit(self.path).path).strip('/').split('/')
        if (is_put and (len(parts)!=2 or parts[0]!='jobs' or not ID.fullmatch(parts[1]))) or (not is_put and parts!=['jobs']):
            return self.reply(404,{'error':'POST /jobs oder PUT /jobs/<32-stellige-hex-ID> verwenden.'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=65536:raise ValueError('JSON-Body mit maximal 64 KB senden.')
            raw=json.loads(self.rfile.read(size))
            ident=parts[1] if is_put else uuid.uuid4().hex
            # A PUT retry without an explicit seed must reuse the original randomized seed.
            previous=self.service.store.get(ident)
            if previous and isinstance(raw,dict) and 'seed' not in raw:raw={**raw,'seed':previous['request']['seed']}
            request=validate_request(raw)
            job,created=self.service.store.create(ident,request)
            return self.reply(202 if created else 200,self.public(job))
        except OverflowError as exc:return self.reply(429,{'error':str(exc)})
        except (ValueError,TypeError) as exc:return self.reply(400,{'error':str(exc)})


def main():
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    service=Service();server=ThreadingHTTPServer(('0.0.0.0',int(os.getenv('PORT','8090'))),Handler);server.service=service
    worker=threading.Thread(target=service.worker,name='comic-worker',daemon=True);worker.start()
    threading.Thread(target=service.telegram.worker,name='telegram-trigger',daemon=True).start()
    def stop(*_):
        service.stop.set();threading.Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    LOG.info('Comic automation listening on %s',server.server_address)
    server.serve_forever();server.server_close()

if __name__=='__main__':main()
