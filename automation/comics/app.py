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
from engine import Engine, ID, STYLES, TERMINAL, validate_request
from stories import Stories, Conflict
import sharing
from character_profiles import ALIGNMENTS, validate as validate_profile
from comfy import ComfyError
from feedback import CRITERIA, validate_feedback
from local_llm import LocalOllama
from telegram_trigger import TelegramTrigger,TelegramError
from telegram_publishing import Publisher

LOG=logging.getLogger('comic-automation')


class Service:
    def __init__(self):
        self.store=Store(os.getenv('DATA_DIR','/data'))
        self.stories=Stories(self.store)
        self.client=Comfy(os.getenv('COMFYUI_URL','http://comfyui:8188'),self.store,int(os.getenv('COMFYUI_PROMPT_TIMEOUT','3600')))
        self.engine=Engine(self.store,self.client,os.getenv('WORKFLOW_TEMPLATE','/app/workflow_template.json'),
                           os.getenv('TEXT_MODEL','qwen3vl_8b_fp8_scaled.safetensors'),os.getenv('VISION_MODEL','qwen3vl_8b_fp8_scaled.safetensors'))
        backend=os.getenv('LLM_BACKEND','comfyui')
        if backend not in ('comfyui','ollama'):raise ValueError('Nur lokale Backends comfyui und ollama sind erlaubt.')
        if backend=='ollama':
            self.engine.llm=LocalOllama(os.getenv('OLLAMA_URL','http://host.docker.internal:11434'),self.store,
                os.getenv('OLLAMA_TEXT_MODEL','gemma3:27b'),os.getenv('OLLAMA_CRITIC_MODEL','qwen3.6:35b-a3b'),
                os.getenv('OLLAMA_VISION_MODEL','qwen3.6:35b-a3b'))
        self.publisher=Publisher(self.store)
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
        if (self.store.get(job) or {}).get('book_mode') or (self.store.get(job) or {}).get('lettering_mode') or (self.store.get(job) or {}).get('narrative_mode'):
            self.store.update(job,cleanup_pending=False);return
        try:self.client.cleanup(job)
        except Exception as exc:
            LOG.warning('Cleanup pending for %s: %s',job,str(exc)[:200])
            self.store.update(job,cleanup_pending=True,cleanup_error=str(exc)[:1000])

    def worker(self):
        from story_meaning import STATE_KEY
        state=self.store.integration_get(STATE_KEY) or {}
        state.update(enabled=False,editorial_mode=True)
        self.store.integration_set(STATE_KEY,state)
        self.store.recover()
        while not self.stop.is_set():
            job=self.store.claim()
            if not job:
                try:
                    from story_meaning import process_library_next
                    if process_library_next(self.engine,self.stories):continue
                except Exception:
                    LOG.exception('Hintergrundanalyse der Erzählkerne fehlgeschlagen')
                for item in self.store.list():
                    if item['status'] in TERMINAL and item.get('cleanup_pending'):self.cleanup(item['id'])
                self.stop.wait(3);continue
            ident=job['id'];LOG.info('Starting %s',ident)
            try:
                if job.get('narrative_mode'):
                    from story_meaning import run
                    result=run(self.engine,ident)
                elif job.get('source_mode'):
                    from source_generator import run
                    result=run(self.engine,ident)
                elif job.get('book_mode'):
                    from books import run
                    result=run(self.store,ident)
                elif job.get('panel_correction_mode'):
                    from panel_correction import run
                    result=run(self.engine,ident)
                elif job.get('lettering_mode'):
                    from lettering import render
                    result=render(self.store,ident)
                elif job.get('character_mode'):
                    from character_profiles import regenerate
                    result=regenerate(self.engine,ident)
                elif job.get('experiment_mode'):
                    from experiments import run
                    result=run(self.engine,ident)
                elif job.get('improvement_mode'):
                    from improvement import improve
                    result=improve(self.engine,ident)
                elif job.get('planning_mode'):
                    from article_plan import prepare
                    result=prepare(self.engine,self.stories,ident)
                elif job.get('editorial_mode'):
                    from editorial import render
                    source=json.loads((self.store.directory(ident)/'editorial-source.json').read_text())
                    render(self.store,self.client,os.getenv('WORKFLOW_TEMPLATE','/app/workflow_template.json'),source,ident,worker=True,review_engine=self.engine)
                    result={'status':'needs_review','artifacts':self.store.get(ident)['artifacts'],
                            'warnings':self.store.get(ident).get('lettering_warnings',[])+self.store.get(ident).get('equipment_warnings',[])+['Bilder und Texte vor Veröffentlichung prüfen.']}
                else:
                    self.capabilities()
                    result=self.engine.execute(ident)
                # Artifacts were copied and hashed before remote cleanup.
                self.store.stage(ident,'finished',**result,cleanup_pending=True)
            except Exception as exc:
                LOG.exception('Job %s failed',ident)
                self.store.stage(ident,'failed',status='failed',error=str(exc)[:5000],cleanup_pending=True)
            finally:
                if not (job.get('lettering_mode') or job.get('book_mode')):self.cleanup(ident)
                else:self.store.update(ident,cleanup_pending=False)


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

    def binary(self,data,kind,filename=None):
        self.send_response(200);self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(data)))
        if filename:self.send_header('Content-Disposition','attachment; filename="'+filename+'"')
        self.end_headers();self.wfile.write(data)

    def do_GET(self):
        path=unquote(urlsplit(self.path).path)
        if path=='/health':return self.reply(200,{'status':'ok'})
        if path in ('/','/character-editor.js','/speech-editor.js','/bubble-positioner.js','/panel-correction.js','/book-export.js','/source-generator.js','/series-editor.js','/experiments.js','/page-templates.js','/guided-reader.js','/style-library.js','/telegram-publish.js','/workflow-ui.js','/story-meaning.js'):
            body=Path(__file__).with_name(path.lstrip('/') if path.endswith('.js') else 'index.html').read_bytes()
            self.send_response(200);self.send_header('Content-Type',('text/javascript' if path.endswith('.js') else 'text/html')+'; charset=utf-8')
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
        if path.startswith('/style-previews/'):
            from art_styles import BY_ID
            name=path.rsplit('/',1)[-1];ident=name.removesuffix('.webp')
            if path!='/style-previews/'+ident+'.webp' or ident not in BY_ID:return self.reply(404,{'error':'Stilvorschau nicht gefunden.'})
            asset=Path(__file__).with_name('style-previews')/name
            if not asset.is_file():return self.reply(404,{'error':'Stilvorschau noch nicht vorhanden.'})
            return self.binary(asset.read_bytes(),'image/webp')
        if not self.authorized():return
        if path=='/series/bases':
            from series import bases
            return self.reply(200,{'bases':bases(self.service.stories)})
        if path=='/narrative-library':
            from story_meaning import library_status
            return self.reply(200,library_status(self.service.store,self.service.stories))
        if path=='/sources':
            from source_generator import catalog
            entries=catalog(self.service.store)
            deferred=set(self.service.store.integration_get('source-catalog-deferred') or [])
            return self.reply(200,{'sources':[entry for entry in entries if entry['id'] not in deferred],'deferred_count':sum(entry['id'] in deferred for entry in entries)})
        if path.startswith('/source-tasks/'):
            return self.source_read(path)
        if path=='/page-templates':
            from lettering import LAYOUT
            return self.reply(200,{'templates':[{**t,'aspect_ratio':LAYOUT.template_aspect(t['id'])} for t in LAYOUT.TEMPLATES.values()]})
        if path=='/styles':
            from art_styles import public
            return self.reply(200,{'styles':STYLES,'catalog':public()})
        if path=='/sharing':return self.reply(200,sharing.settings(self.service.store))
        if path=='/characters':
            try:
                result=self.service.client.request('GET','/dgx-comics/characters')
                return self.reply(200,{**result,'alignments':ALIGNMENTS})
            except (ComfyError,OSError) as exc:return self.reply(502,{'error':str(exc)})
        if path=='/stories':return self.reply(200,{'stories':self.service.stories.list()})
        if path=='/telegram-publishing':return self.reply(200,self.service.publisher.info(verify=True))
        parts=path.strip('/').split('/')
        if len(parts)==4 and parts[0]=='jobs' and ID.fullmatch(parts[1]) and parts[2:]==['share','telegram']:
            return self.reply(200,self.service.publisher.info(parts[1],verify=True))
        if path=='/telegram':return self.reply(200,self.service.telegram.info())
        if path=='/learning':return self.reply(200,self.service.store.learning_memory())
        if path=='/ready':
            try:return self.reply(200,self.service.capabilities())
            except Exception as exc:return self.reply(503,{'ready':False,'error':str(exc)[:2000]})
        if path=='/jobs':return self.reply(200,{'jobs':[self.public(job) for job in self.service.store.list(public_only=True) if not job.get('character_mode') and not job.get('book_mode') and not job.get('source_mode') and not job.get('narrative_mode')]})
        parts=path.strip('/').split('/')
        if len(parts)==3 and parts[:2]==['characters','regenerations'] and ID.fullmatch(parts[2]):
            job=self.service.store.get(parts[2])
            if not job or not job.get('character_mode'):return self.reply(404,{'error':'Figurenauftrag nicht gefunden.'})
            result={k:job.get(k) for k in ('id','status','stage','error')}
            if job['status']=='completed':result['profile']=json.loads((self.service.store.directory(job['id'])/'character-result.json').read_text())
            return self.reply(200,result)
        if len(parts)==4 and parts[0]=='characters' and ID.fullmatch(parts[1]) and parts[2]=='references' and __import__('re').fullmatch(r'[a-f0-9]{64}\.png',parts[3]):
            try:return self.binary(self.service.client.request('GET','/dgx-comics/'+path.strip('/')),'image/png')
            except (ComfyError,OSError) as exc:return self.reply(404,{'error':str(exc)})
        if len(parts)==2 and parts[0]=='stories' and ID.fullmatch(parts[1]):
            try:return self.reply(200,self.service.stories.get(parts[1]))
            except KeyError:return self.reply(404,{'error':'Geschichte nicht gefunden.'})
        if len(parts)>=2 and parts[0]=='jobs' and ID.fullmatch(parts[1]):
            job=self.service.store.get(parts[1])
            if not job:return self.reply(404,{'error':'Auftrag nicht gefunden.'})
            if len(parts)==2:return self.reply(200,self.public(job))
            if len(parts)==3 and parts[2]=='experiment-options':
                try:
                    from experiments import options
                    return self.reply(200,options(self.service.store,job))
                except Conflict as exc:return self.reply(409,{'error':str(exc)})
                except (ValueError,KeyError,OSError) as exc:return self.reply(400,{'error':str(exc)})
            if len(parts)>=3 and parts[2]=='reader':
                try:
                    import guided_reader
                    if len(parts)==3:return self.reply(200,guided_reader.manifest(self.service.store,job))
                    if len(parts)==5 and parts[3]=='pages' and parts[4].endswith('.png'):
                        return self.binary(guided_reader.image(self.service.store,job,int(parts[4][:-4])),'image/png')
                    return self.reply(404,{'error':'Leseseite nicht gefunden.'})
                except Conflict as exc:return self.reply(409,{'error':str(exc)})
                except (ValueError,KeyError,OSError) as exc:return self.reply(400,{'error':str(exc)})
            if len(parts)==3 and parts[2]=='book-settings':
                try:
                    import books
                    return self.reply(200,books.settings(self.service.store,job))
                except Conflict as exc:return self.reply(409,{'error':str(exc)})
                except (ValueError,KeyError,OSError) as exc:return self.reply(400,{'error':str(exc)})
            if len(parts)==3 and parts[2]=='lettering':
                try:
                    import lettering
                    return self.reply(200,lettering.manifest(self.service.store,job))
                except Conflict as exc:return self.reply(409,{'error':str(exc)})
                except (ValueError,KeyError,OSError) as exc:return self.reply(400,{'error':str(exc)})
            if len(parts)>=3 and parts[2]=='share':
                try:
                    if len(parts)==3:return self.reply(200,sharing.manifest(self.service.store,job))
                    if len(parts)==4 and parts[3]=='images.zip':return self.binary(sharing.bundle(self.service.store,job),'application/zip','comic-'+job['id'][:8]+'-bilder.zip')
                    if len(parts)==5 and parts[3]=='images' and __import__('re').fullmatch(r'\d+\.png',parts[4]):
                        sharing.manifest(self.service.store,job)
                        return self.binary(sharing.image(self.service.store,job,int(parts[4][:-4])-1),'image/png')
                except (ValueError,TypeError) as exc:return self.reply(409,{'error':str(exc)})
                except (KeyError,OSError):return self.reply(404,{'error':'Bild nicht gefunden.'})
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
        result={k:v for k,v in job.items() if k not in ('steps','planning_source')}
        from equipment_review import presentation
        result.update(presentation(job))
        preview=self.story_preview(job)
        result['story_available']=preview['available'];result['story_title']=preview.get('title','') or job.get('improvement_title','') or job.get('story_title','')
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
        if urlsplit(self.path).path in ('/narrative-tasks','/narrative-library','/narrative-library/import'):
            if not self.authorized():return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=2_000_000:raise ValueError('Planungsdaten maximal 2 MB.')
                import story_meaning
                value=json.loads(self.rfile.read(size))
                if urlsplit(self.path).path=='/narrative-library/import':
                    return self.reply(200,story_meaning.import_curated(self.service.store,self.service.stories,value))
                if urlsplit(self.path).path=='/narrative-library':
                    if isinstance(value,dict) and value.get('action')=='start':raise ValueError('Neue Vorlagen und Kategorien werden redaktionell über Codex angebunden. Lokale Ersatzdeutung ist deaktiviert.')
                    return self.reply(200,story_meaning.configure_library(self.service.store,self.service.stories,value))
                return self.reply(202,self.public(story_meaning.enqueue(self.service.store,value,editorial_only=True)))
            except OverflowError as exc:return self.reply(429,{'error':str(exc)})
            except (ValueError,TypeError,OSError) as exc:return self.reply(400,{'error':str(exc)})
        if urlsplit(self.path).path.startswith('/series/'):
            return self.series_action()
        if urlsplit(self.path).path in ('/sources','/source-tasks') or urlsplit(self.path).path.startswith('/source-tasks/'):
            return self.source_action()
        parts=unquote(urlsplit(self.path).path).strip('/').split('/')
        if len(parts)==4 and parts[0]=='jobs' and ID.fullmatch(parts[1]) and parts[2:]==['share','telegram']:
            if not self.authorized():return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=4096:raise ValueError('Ungültige Veröffentlichungsdaten.')
                value=json.loads(self.rfile.read(size));job=self.service.store.get(parts[1])
                if not job:return self.reply(404,{'error':'Ausgabe nicht gefunden.'})
                with self.service.stories.lock:result=self.service.publisher.publish(job,value)
                return self.reply(200,result)
            except (ValueError,TypeError,OSError,TelegramError) as exc:return self.reply(400,{'error':str(exc)})
        if len(parts)==3 and parts[0]=='jobs' and ID.fullmatch(parts[1]) and parts[2]=='experiment':
            if not self.authorized():return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=16384:raise ValueError('Experiment-Einstellungen maximal 16 KB.')
                value=json.loads(self.rfile.read(size))
                from experiments import enqueue
                with self.service.stories.lock:
                    parent=self.service.store.get(parts[1])
                    if not parent:raise KeyError(parts[1])
                    result=enqueue(self.service.store,parent,value)
                return self.reply(202,self.public(result))
            except Conflict as exc:return self.reply(409,{'error':str(exc)})
            except KeyError:return self.reply(404,{'error':'Basis-Ausgabe nicht gefunden.'})
            except OverflowError as exc:return self.reply(429,{'error':str(exc)})
            except (ValueError,TypeError,OSError) as exc:return self.reply(400,{'error':str(exc)})
        if len(parts)==3 and parts[0]=='jobs' and ID.fullmatch(parts[1]) and parts[2]=='book-export':
            return self.book_action(parts[1],True)
        if len(parts)==3 and parts[0]=='jobs' and ID.fullmatch(parts[1]) and parts[2]=='correct-panel':
            if not self.authorized():return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=16384:raise ValueError('Korrekturanfrage maximal 16 KB.')
                import panel_correction
                value=json.loads(self.rfile.read(size))
                with self.service.stories.lock:
                    parent=self.service.store.get(parts[1])
                    if not parent:raise KeyError(parts[1])
                    job=panel_correction.enqueue(self.service.store,parent,value)
                return self.reply(202,self.public(job))
            except Conflict as exc:return self.reply(409,{'error':str(exc)})
            except KeyError:return self.reply(404,{'error':'Ausgabe nicht gefunden.'})
            except OverflowError as exc:return self.reply(429,{'error':str(exc)})
            except (ValueError,TypeError,OSError) as exc:return self.reply(400,{'error':str(exc)})
        if len(parts) in (3,4) and parts[0]=='jobs' and ID.fullmatch(parts[1]) and parts[2]=='lettering':
            if not self.authorized():return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=65536:raise ValueError('Beschriftung maximal 64 KB.')
                value=json.loads(self.rfile.read(size))
                if not isinstance(value,dict):raise ValueError('JSON-Objekt erforderlich.')
                job=self.service.store.get(parts[1])
                if not job:raise KeyError(parts[1])
                import lettering
                if len(parts)==3:
                    with self.service.stories.lock:result=lettering.enqueue(self.service.store,job,value)
                    return self.reply(202,self.public(result))
                if parts[3]=='preview':return self.reply(200,lettering.preview(self.service.store,job,value))
                if parts[3]=='automatic':return self.reply(200,lettering.automatic(self.service.store,job,value))
                return self.reply(404,{'error':'Endpunkt nicht gefunden.'})
            except Conflict as exc:return self.reply(409,{'error':str(exc)})
            except KeyError:return self.reply(404,{'error':'Ausgabe nicht gefunden.'})
            except OverflowError as exc:return self.reply(429,{'error':str(exc)})
            except (ValueError,TypeError,OSError) as exc:return self.reply(400,{'error':str(exc)})
        if parts==['characters','regenerate']:
            if not self.authorized():return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=18_000_000:raise ValueError('Figurenprofil maximal 18 MB.')
                from character_profiles import enqueue
                return self.reply(202,enqueue(self.service.store,json.loads(self.rfile.read(size))))
            except OverflowError as exc:return self.reply(429,{'error':str(exc)})
            except (ValueError,TypeError) as exc:return self.reply(400,{'error':str(exc)})
        if parts==['characters']:
            if not self.authorized():return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=18_000_000:raise ValueError('Figurenprofil maximal 18 MB.')
                value=validate_profile(json.loads(self.rfile.read(size)))
                result=self.service.client.request('POST','/dgx-comics/characters',value)
                return self.reply(200,result)
            except (ValueError,TypeError) as exc:return self.reply(400,{'error':str(exc)})
            except (ComfyError,OSError) as exc:return self.reply(409,{'error':str(exc)})
        if parts[0]=='stories':return self.story_action(parts,'POST')
        if len(parts)==3 and parts[0]=='jobs' and ID.fullmatch(parts[1]) and parts[2] in ('feedback','next','improve','dismiss-plan'):
            if not self.authorized():return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<=size<=65536:raise ValueError('Maximal 64 KB senden.')
                value=json.loads(self.rfile.read(size)) if size else {}
                if parts[2]=='dismiss-plan':
                    if value!={}:raise ValueError('Fehler ohne weitere Parameter schließen.')
                    self.service.stories.dismiss_plan(parts[1])
                    return self.reply(200,{'dismissed':True})
                if parts[2]=='feedback':
                    job=self.service.store.save_feedback(parts[1],validate_feedback(value))
                    return self.reply(200,{'saved':True,'feedback':job['feedback'],'applies_to':'future_jobs_and_explicit_improvements'})
                if parts[2]=='improve':
                    if not isinstance(value,dict) or set(value)-{'stil'}:raise ValueError('Nur stil ist änderbar; Kachelanzahl kommt aus der bewerteten Ausgabe.')
                    return self.reply(202,self.public(self.service.stories.improve(parts[1],value.get('stil'))))
                if value!={}:raise ValueError('POST /next ohne Parameter verwenden.')
                job,created=self.service.store.next_story(parts[1])
                return self.reply(202 if created else 200,self.public(job))
            except KeyError:return self.reply(404,{'error':'Auftrag nicht gefunden.'})
            except OverflowError as exc:return self.reply(429,{'error':str(exc)})
            except Conflict as exc:return self.reply(409,{'error':str(exc)})
            except (ValueError,TypeError) as exc:return self.reply(400,{'error':str(exc)})
        self.create(False)
    def do_PUT(self):
        if urlsplit(self.path).path=='/telegram-publishing':
            if not self.authorized():return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=4096:raise ValueError('Ungültige Kanaleinstellung.')
                return self.reply(200,self.service.publisher.configure(json.loads(self.rfile.read(size))))
            except (ValueError,TypeError,TelegramError) as exc:return self.reply(400,{'error':str(exc)})
        if urlsplit(self.path).path.startswith('/source-tasks/'):
            return self.source_action()
        parts=urlsplit(self.path).path.strip('/').split('/')
        if len(parts)==4 and parts[0]=='jobs' and ID.fullmatch(parts[1]) and parts[2:] == ['share','post']:
            if not self.authorized():return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=40000:raise ValueError('Beitragstext zu groß.')
                job=self.service.store.get(parts[1])
                if not job:return self.reply(404,{'error':'Ausgabe nicht gefunden.'})
                value=json.loads(self.rfile.read(size))
                with self.service.stories.lock:result=sharing.save_post(self.service.store,job,value)
                return self.reply(200,result)
            except (ValueError,TypeError,OSError) as exc:return self.reply(400,{'error':str(exc)})
        if len(parts)==3 and parts[0]=='jobs' and ID.fullmatch(parts[1]) and parts[2]=='reader':
            if not self.authorized():return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=1000000:raise ValueError('Ungültige Größe der Leseordnung.')
                job=self.service.store.get(parts[1])
                if not job:return self.reply(404,{'error':'Auftrag nicht gefunden.'})
                import guided_reader
                value=json.loads(self.rfile.read(size))
                with self.service.stories.lock:result=guided_reader.save(self.service.store,job,value)
                return self.reply(200,result)
            except Conflict as exc:return self.reply(409,{'error':str(exc)})
            except (ValueError,KeyError,OSError) as exc:return self.reply(400,{'error':str(exc)})
        if len(parts)==3 and parts[0]=='jobs' and ID.fullmatch(parts[1]) and parts[2]=='book-settings':return self.book_action(parts[1],False)
        if urlsplit(self.path).path=='/sharing':
            if not self.authorized():return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=8192:raise ValueError('Zieleinstellungen maximal 8 KB.')
                return self.reply(200,sharing.save_settings(self.service.store,json.loads(self.rfile.read(size))))
            except (ValueError,TypeError) as exc:return self.reply(400,{'error':str(exc)})
        self.create(True)

    def series_action(self):
        if not self.authorized():return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=2_000_000:raise ValueError('Serienangaben maximal 2 MB.')
            value=json.loads(self.rfile.read(size))
            if not isinstance(value,dict):raise ValueError('JSON-Objekt erforderlich.')
            import series
            with self.service.stories.lock:
                if urlsplit(self.path).path=='/series/preview':return self.reply(200,series.preview(self.service.stories,value))
                if urlsplit(self.path).path=='/series/episodes':return self.reply(201,series.create(self.service.stories,value))
            return self.reply(404,{'error':'Endpunkt nicht gefunden.'})
        except Conflict as exc:return self.reply(409,{'error':str(exc)})
        except KeyError:return self.reply(404,{'error':'Basisgeschichte oder Comic nicht gefunden.'})
        except (ValueError,TypeError,OSError) as exc:return self.reply(400,{'error':str(exc)})

    def source_read(self,path):
        parts=path.strip('/').split('/')
        if len(parts)!=2 or not ID.fullmatch(parts[1]):return self.reply(404,{'error':'Skriptauftrag nicht gefunden.'})
        job=self.service.store.get(parts[1])
        if not job or not job.get('source_mode'):return self.reply(404,{'error':'Skriptauftrag nicht gefunden.'})
        result=self.public(job)
        result['source_input']=json.loads((self.service.store.directory(job['id'])/'source-input.json').read_text())
        if job['status']=='completed':
            result['script']=(self.service.store.directory(job['id'])/'source-script.txt').read_text()
            draft=json.loads((self.service.store.directory(job['id'])/'source-draft.json').read_text())
            result['narrative_plan']=draft.get('narrative_plan')
            result['post_summary']=draft.get('post_summary',result['source_input']['source'].get('post_summary',''))
        return self.reply(200,result)

    def source_action(self):
        if not self.authorized():return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=2_000_000:raise ValueError('Daten maximal 2 MB.')
            value=json.loads(self.rfile.read(size))
            if not isinstance(value,dict):raise ValueError('JSON-Objekt erforderlich.')
            import source_generator as sources
            parts=urlsplit(self.path).path.strip('/').split('/')
            with self.service.stories.lock:
                if parts==['sources']:return self.reply(200,sources.save_source(self.service.store,value))
                if parts==['source-tasks']:return self.reply(202,self.public(sources.enqueue(self.service.store,value)))
                if len(parts)==3 and parts[0]=='source-tasks' and ID.fullmatch(parts[1]) and parts[2]=='script' and self.command=='PUT':
                    job=self.service.store.get(parts[1])
                    if not job or not job.get('source_mode'):raise KeyError(parts[1])
                    if job['status']!='completed':raise Conflict('Das Skript wird noch erstellt oder ist fehlgeschlagen.')
                    sources.parse(value.get('script'),job['request']['stil'])
                    self.service.store.write(parts[1],'source-script.txt',value['script'].encode('utf-8'))
                    return self.reply(200,{'saved':True})
                if len(parts)==3 and parts[0]=='source-tasks' and ID.fullmatch(parts[1]) and parts[2]=='adopt':
                    return self.reply(201,sources.adopt(self.service.stories,self.service.store,parts[1],value))
            return self.reply(404,{'error':'Endpunkt nicht gefunden.'})
        except Conflict as exc:return self.reply(409,{'error':str(exc)})
        except KeyError:return self.reply(404,{'error':'Quelle oder Skript nicht gefunden.'})
        except OverflowError as exc:return self.reply(429,{'error':str(exc)})
        except (ValueError,TypeError,OSError) as exc:return self.reply(400,{'error':str(exc)})

    def book_action(self,ident,generate):
        if not self.authorized():return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=2_000_000:raise ValueError('Buchangaben maximal 2 MB.')
            value=json.loads(self.rfile.read(size));import books
            with self.service.stories.lock:
                parent=self.service.store.get(ident)
                if not parent:raise KeyError(ident)
                result=books.enqueue(self.service.store,parent,value) if generate else books.save_settings(self.service.store,parent,value)
            return self.reply(202 if generate else 200,self.public(result) if generate else result)
        except Conflict as exc:return self.reply(409,{'error':str(exc)})
        except KeyError:return self.reply(404,{'error':'Comic nicht gefunden.'})
        except OverflowError as exc:return self.reply(429,{'error':str(exc)})
        except (ValueError,TypeError,OSError) as exc:return self.reply(400,{'error':str(exc)})

    def do_PATCH(self):
        self.story_action(unquote(urlsplit(self.path).path).strip('/').split('/'),'PATCH')

    def do_DELETE(self):
        parts=unquote(urlsplit(self.path).path).strip('/').split('/')
        if parts[0]=='stories':return self.story_action(parts,'DELETE')
        if not self.authorized():return
        if len(parts)==2 and parts[0]=='characters' and ID.fullmatch(parts[1]):
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=1024:raise ValueError('Versionsangabe erforderlich.')
                value=json.loads(self.rfile.read(size))
                if not isinstance(value,dict) or type(value.get('version')) is not int:raise ValueError('Versionsangabe erforderlich.')
                for entry in self.service.stories.list():
                    story=self.service.stories.get(entry['id'])
                    if parts[1] in story['payload'].get('library_ids',[])+story['payload'].get('figuren_ids',[]):
                        return self.reply(409,{'error':'Diese Figur wird in der Geschichte „'+story['name']+'“ direkt aus der Bibliothek verwendet. Zuerst dort als eigene Figurenkopie übernehmen und speichern.'})
                return self.reply(200,self.service.client.request('DELETE','/dgx-comics/characters/'+parts[1],value))
            except (ValueError,TypeError) as exc:return self.reply(400,{'error':str(exc)})
            except (ComfyError,OSError) as exc:return self.reply(409,{'error':str(exc)})
        if len(parts)==2 and parts[0]=='jobs' and ID.fullmatch(parts[1]):
            try:
                job=self.service.store.get(parts[1])
                if not job:raise KeyError(parts[1])
                if job['status'] in ('queued','running'):raise Conflict('Laufende oder wartende Ausgaben können nicht gelöscht werden.')
                self.service.cleanup(parts[1]);self.service.stories.delete_job(parts[1])
                return self.reply(200,{'deleted':True})
            except KeyError:return self.reply(404,{'error':'Ausgabe nicht gefunden.'})
            except Conflict as exc:return self.reply(409,{'error':str(exc)})
        return self.reply(404,{'error':'Endpunkt nicht gefunden.'})

    def story_action(self,parts,method):
        if not self.authorized():return
        valid=(parts==['stories'] and method=='POST') or (len(parts) in (2,3) and parts[0]=='stories' and ID.fullmatch(parts[1]))
        if not valid:return self.reply(404,{'error':'Endpunkt nicht gefunden.'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=20_000_000:raise ValueError('JSON mit maximal 20 MB senden.')
            value=json.loads(self.rfile.read(size))
            if not isinstance(value,dict):raise ValueError('JSON-Objekt erwartet.')
            if len(parts)==1:
                story=self.service.stories.import_job(value['from_job']) if 'from_job' in value else self.service.stories.save(value)
                return self.reply(201,story)
            if len(parts)==2 and method=='PATCH':return self.reply(200,self.service.stories.save(value,parts[1],value.get('version')))
            if len(parts)==3 and parts[2]=='generate' and method=='POST':
                return self.reply(202,self.public(self.service.stories.enqueue(parts[1],value.get('version'))))
            if len(parts)==3 and parts[2]=='plan' and method=='POST':
                return self.reply(202,self.public(self.service.stories.plan(parts[1],value.get('version'))))
            if len(parts)==2 and method=='DELETE':
                # Only generated outputs owned by this definition are removed; imported originals stay intact.
                with self.service.stories.lock:
                    owned=self.service.stories.outputs(parts[1])
                    if any(j['status'] in ('queued','running') for j in owned):raise Conflict('Eine Ausgabe läuft noch. Danach löschen.')
                    story=self.service.stories.get(parts[1])
                    if story['version']!=value.get('version'):raise Conflict('Geschichte wurde geändert. Bitte neu laden.')
                    for job in owned:self.service.cleanup(job['id'])
                    count=self.service.stories.delete(parts[1],value.get('version'))
                return self.reply(200,{'deleted':True,'deleted_outputs':count})
            return self.reply(404,{'error':'Endpunkt nicht gefunden.'})
        except KeyError:return self.reply(404,{'error':'Geschichte oder Ausgabe nicht gefunden.'})
        except Conflict as exc:return self.reply(409,{'error':str(exc)})
        except OverflowError as exc:return self.reply(429,{'error':str(exc)})
        except (ValueError,TypeError) as exc:return self.reply(400,{'error':str(exc)})

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
