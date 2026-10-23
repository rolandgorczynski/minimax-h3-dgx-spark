"""Isolated HTTP jobs, durable state, bounded loops and export ownership."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'automation/comics'))
from storage import Store
from engine import Engine,validate_request
from comfy import Comfy,ComfyError
from app import Service,Handler,ThreadingHTTPServer
from feedback import CRITERIA,validate_feedback
from learning import evidence,validate_lessons
from local_llm import LocalOllama,local_url

TEMPLATE=ROOT/'examples/comics/workflows/04_Comic_Automat_9B.json'


class FakeComfy:
    def __init__(self,job,visual_fail=False):self.job=job;self.visual_fail=visual_fail;self.calls=[];self.prompts=[]
    def request(self,method,path,data=None):
        self.calls.append((method,path))
        if path.endswith('check-plan'):return {'valid':True,'issues':[]}
        raise AssertionError('Unexpected remote mutation/request: '+path)
    def run(self,job,step,graph,workflow=None):
        self.calls.append(('run',step))
        if '91' in graph:self.prompts.append(graph['91']['inputs']['auftrag'])
        image=lambda name:{'filename':name,'subfolder':'comic-automation/'+job,'type':'temp'}
        if step.startswith('portrait-'):return {'80':{'images':[image(step+'.png')]}}
        if step=='scene-plan':
            prompt=graph['91']['inputs']['auftrag'];people=json.loads(prompt.split('CAST:',1)[1].split('\nSTORY:',1)[0])
            scenes=[{'story':c['name']+' wartet am Eingang.','dialog':'Ein ruhiger Morgen.','characters':[c['id']],'bubbles':[]} for c in people]
            return {'91':{'assistant_text':[json.dumps(scenes)]}}
        if step.startswith('render-'):return {'5':{'images':[image('comic.png')],'comic_panels':[image('01_panel.png'),image('02_panel.png')]}}
        if step=='story-prose':return {'91':{'assistant_text':[json.dumps({'story':'Aria sucht einen Brief. Bram findet ihn im Archiv.'})]}}
        if step=='character-draft':value={'title':'Archiv','story':'Aria sucht einen Brief. Bram findet ihn im Archiv.','characters':[{'name':n,'description':'Short brown hair and green eyes.','outfit':'Grey jacket'} for n in ['Aria','Bram']]}
        elif step=='self-reflection':
            facts=json.JSONDecoder().raw_decode(graph['91']['inputs']['auftrag'].split('EVIDENCE:\n',1)[1])[0]
            value={'lessons':[{'rule':'Keep each character clearly visible in the composition.','evidence_ref':facts['findings'][0]['id']}]}
        else:value={'approved':not (self.visual_fail and step.startswith('visual-')),'issues':['Person nicht deutlich genug.'] if self.visual_fail and step.startswith('visual-') else [],'revised_scene':'Die Person steht deutlich sichtbar am Eingang.'}
        return {'91':{'assistant_text':[json.dumps(value)]}}
    def download(self,job,descriptor):return b'fake-image-for-orchestration-tests'


class AutomationTests(unittest.TestCase):
    def test_request_validation_and_durable_idempotency(self):
        for value in ({'kacheln':True},{'kacheln':0},{'max_korrekturrunden':99},{'stil':'invalid'},{'shell':'rm -rf'},{'sprache':'en'}):
            with self.assertRaises(ValueError):validate_request(value)
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);ident=uuid.uuid4().hex;req=validate_request({'seed':42})
            self.assertTrue(store.create(ident,req)[1]);self.assertFalse(store.create(ident,req)[1])
            with self.assertRaises(ValueError):store.create(ident,{**req,'seed':43})
            self.assertEqual(store.claim()['status'],'running')
            store.recover();self.assertEqual(Store(root).get(ident)['status'],'queued')

    def run_engine(self,root,fail,budget):
        store=Store(root);ident=uuid.uuid4().hex
        store.create(ident,validate_request({'kacheln':2,'seed':42,'max_korrekturrunden':budget}))
        client=FakeComfy(ident,fail)
        engine=Engine(store,client,TEMPLATE,'text','vision')
        result=engine.execute(ident)
        return store,ident,client,result

    def test_full_export_is_separate_and_contains_references(self):
        before=TEMPLATE.read_bytes()
        with tempfile.TemporaryDirectory() as root:
            store,ident,client,result=self.run_engine(root,False,2)
            self.assertEqual(result['status'],'completed')
            names={a['name'] for a in result['artifacts']}
            self.assertTrue({'comic.png','workflow.json','report.json','comic-bundle.zip'}<=names)
            workflow=json.loads((store.directory(ident)/'workflow.json').read_text())
            node=next(n for n in workflow['nodes'] if n['type']=='DGXComicStudio')
            cast=json.loads(node['widgets_values'][10]);self.assertTrue(all(c['inline_references'] for c in cast))
            self.assertEqual(before,TEMPLATE.read_bytes())
            self.assertFalse(any(path in ('/userdata','/interrupt','/characters') for method,path in client.calls))

    def test_visual_retries_are_bounded_and_exhaustion_is_visible(self):
        with tempfile.TemporaryDirectory() as root:
            store,ident,client,result=self.run_engine(root,True,1)
            self.assertEqual(result['status'],'needs_review')
            self.assertEqual(result['correction_rounds_used'],1)
            self.assertEqual([step for kind,step in client.calls if kind=='run' and step.startswith('render-')],['render-0','render-1'])
            self.assertTrue(result['warnings'])

    def test_client_rejects_foreign_output(self):
        client=Comfy('http://unused',None)
        for descriptor in [{'type':'output','subfolder':'comics','filename':'user.png'},
                           {'type':'temp','subfolder':'comic-automation/aaa-other','filename':'user.png'},
                           {'type':'temp','subfolder':'comic-automation/aaa/../../other','filename':'user.png'},
                           {'type':'temp','subfolder':'comic-automation/aaa','filename':'../user.png'}]:
            with self.assertRaises(ComfyError):client.download('aaa',descriptor)

    def test_autonomous_learning_without_any_user_rating(self):
        with tempfile.TemporaryDirectory() as root:
            store,ident,client,result=self.run_engine(root,True,1)
            self.assertEqual(store.preferences()['rated_examples'],[])
            memory=Store(root).learning_memory()
            self.assertEqual(memory['analyzed_runs'],1)
            self.assertEqual(memory['rules'][0]['status'],'hypothesis')
            self.assertEqual(memory['rules'][0]['source_job'],ident)
            following=uuid.uuid4().hex;store.create(following,validate_request({'kacheln':2,'seed':43}))
            other=FakeComfy(following);Engine(store,other,TEMPLATE,'text','vision').execute(following)
            self.assertTrue(any(memory['rules'][0]['rule'] in prompt for prompt in other.prompts if 'CAST:' in prompt))
            self.assertIn('reports/self-reflection.json',{a['name'] for a in result['artifacts']})
            # Retrying the same finalization does not count an experience twice.
            store.save_experience(ident,{'lessons':memory['rules']})
            self.assertEqual(store.learning_memory()['analyzed_runs'],2)

    def test_learning_requires_evidence_and_reports_regressions(self):
        facts=evidence({'history':[
            {'area':'story','round':0,'approved':False,'issues':['Unclear ending']},
            {'area':'story','round':1,'approved':True,'issues':[]},
            {'area':'visual','round':0,'approved':False,'issues':['Face hidden']},
            {'area':'visual','round':1,'approved':False,'issues':['Face hidden','Wrong person']}]})
        lesson={'rule':'Show a clear consequence of the final action.','evidence_ref':facts['findings'][0]['id']}
        self.assertEqual(validate_lessons({'lessons':[lesson]},facts)['lessons'][0]['status'],'supported_by_model_comparison')
        self.assertEqual(facts['comparisons'][1]['outcome'],'regressed')
        with self.assertRaises(ValueError):validate_lessons({'lessons':[{**lesson,'evidence_ref':'invented'}]},facts)

    def test_reflection_failure_preserves_the_comic(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);ident=uuid.uuid4().hex;store.create(ident,validate_request({'kacheln':2,'seed':42,'max_korrekturrunden':0}))
            client=FakeComfy(ident,True);original=client.run
            def run(job,step,*args):
                if step=='self-reflection':raise RuntimeError('Local critic unavailable')
                return original(job,step,*args)
            client.run=run
            result=Engine(store,client,TEMPLATE,'text','vision').execute(ident)
            self.assertIn('comic.png',{a['name'] for a in result['artifacts']})
            self.assertEqual(store.learning_memory()['analyzed_runs'],0)
            report=json.loads((store.directory(ident)/'reports/self-reflection.json').read_text())
            self.assertEqual(report['status'],'unavailable')

    def test_worse_scene_revision_is_discarded_before_rendering(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);ident=uuid.uuid4().hex;store.create(ident,validate_request({'kacheln':2,'seed':42,'max_korrekturrunden':1}))
            client=FakeComfy(ident);original=client.run;rendered=[]
            def run(job,step,graph,workflow=None):
                if step.startswith('scene-review-'):
                    value={'approved':False,'issues':['One issue'] if step.endswith('-0') else ['One issue','New additional error']}
                    return {'91':{'assistant_text':[json.dumps(value)]}}
                if step=='scene-revision-0':
                    prompt=graph['91']['inputs']['auftrag'];scenes=json.loads(prompt.split('SCENES:',1)[1].split('\nISSUES:',1)[0])
                    scenes[0]['story']='Worse revised composition'
                    return {'91':{'assistant_text':[json.dumps(scenes)]}}
                if step.startswith('render-'):rendered.append(json.loads(graph['5']['inputs']['bearbeiteter_plan']))
                return original(job,step,graph,workflow)
            client.run=run;Engine(store,client,TEMPLATE,'text','vision').execute(ident)
            self.assertNotEqual(rendered[0]['scenes'][0]['story'],'Worse revised composition')
            report=json.loads((store.directory(ident)/'report.json').read_text())
            self.assertEqual(report['reviews']['discarded_revisions'][0]['area'],'scenes')
            self.assertEqual(report['self_learning']['comparisons'][1]['outcome'],'regressed')

    def test_german_translation_precedes_rendering_and_preserves_speakers(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);ident=uuid.uuid4().hex;store.create(ident,validate_request({'kacheln':2,'seed':42}))
            client=FakeComfy(ident);original=client.run;rendered=[];speaker=[]
            def run(job,step,graph,workflow=None):
                value=None
                if step=='story-prose':value={'story':'Aria searches for a letter. Bram finds it.'}
                elif step.startswith('german-') and '-review-' in step:value={'approved':not step.endswith('-0'),'issues':['Fremdsprachiger Text'] if step.endswith('-0') else []}
                elif step=='german-story-language-confirm-0':value={'approved':False,'issues':['Aria searches for a letter.']}
                elif step=='german-panels-language-confirm-0':value={'approved':False,'issues':['Aria finds the letter.']}
                elif step=='german-story-translation':value={'title':'Der Brief','story':'Aria sucht einen Brief. Bram findet ihn.'}
                elif step=='german-panels-translation':value=[{'dialog':'Aria findet den Brief.','bubbles':['Hier ist er!']},{'dialog':'Ein ruhiger Morgen.','bubbles':[]}]
                if value is not None:return {'91':{'assistant_text':[json.dumps(value)]}}
                result=original(job,step,graph,workflow)
                if step=='scene-plan':
                    scenes=json.loads(result['91']['assistant_text'][0]);speaker.append(scenes[0]['characters'][0])
                    scenes[0].update(dialog='Aria finds the letter.',bubbles=[{'speaker':speaker[0],'text':'Here it is!'}])
                    result['91']['assistant_text']=[json.dumps(scenes)]
                if step.startswith('render-'):rendered.append(json.loads(graph['5']['inputs']['bearbeiteter_plan']))
                return result
            client.run=run;Engine(store,client,TEMPLATE,'text','vision').execute(ident)
            doc=json.loads((store.directory(ident)/'story.json').read_text())
            self.assertEqual(doc['title'],'Der Brief');self.assertIn('sucht einen Brief',doc['story'])
            self.assertEqual(rendered[0]['scenes'][0]['bubbles'][0],{'speaker':speaker[0],'text':'Hier ist er!'})

    def test_unresolved_language_failure_blocks_all_image_generation(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);ident=uuid.uuid4().hex;store.create(ident,validate_request({'kacheln':2,'seed':42}))
            client=FakeComfy(ident);original=client.run
            def run(job,step,graph,workflow=None):
                if step=='story-prose':return {'91':{'assistant_text':[json.dumps({'story':'Still an English story.'})]}}
                if step.startswith('german-story-review'):return {'91':{'assistant_text':[json.dumps({'approved':False,'issues':['Still English']})]}}
                if step.startswith('german-story-language-confirm'):
                    return {'91':{'assistant_text':[json.dumps({'approved':False,'issues':['Still an English story.']})]}}
                if step=='german-story-translation':return {'91':{'assistant_text':[json.dumps({'title':'The Letter','story':'Still an English story.'})]}}
                return original(job,step,graph,workflow)
            client.run=run
            with self.assertRaisesRegex(ValueError,'Deutschpflicht'):Engine(store,client,TEMPLATE,'text','vision').execute(ident)
            self.assertFalse(any(step.startswith(('portrait-','render-')) for kind,step in client.calls if kind=='run'))

    def test_false_german_rejection_is_confirmed_against_only_actual_user_text(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);ident=uuid.uuid4().hex;store.create(ident,validate_request({}))
            engine=Engine(store,FakeComfy(ident),TEMPLATE,'text','vision');calls=[]
            original={'arc':'Der Lindwurm treibt sein Unwesen.','mood':'Eine nachdenkliche Stimmung.','id':'a'*32,'expression':'shout'}
            def call(job,step,prompt,validator,tokens):
                calls.append((step,prompt))
                if '-review-' in step:return validator({'approved':False,'issues':['arc: Unwesen treibt','mood: unwunderbar']})
                if '-language-confirm-' in step:return validator({'approved':True,'issues':[]})
                raise AssertionError('Keine Übersetzung deutscher Texte: '+step)
            engine.json_call=call
            self.assertIs(engine.require_german(ident,'probe',original,lambda v:v,600),original)
            self.assertEqual(len(calls),2)
            content=json.loads(calls[0][1].split('NUTZTEXTE:\n')[1])
            self.assertEqual(content,[original['arc'],original['mood']])
            report=json.loads((store.directory(ident)/'reports/probe-language-decision-0.json').read_text())
            self.assertTrue(report['confirmed']['approved'])

    def test_language_confirmation_cannot_invent_foreign_quotes(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);ident=uuid.uuid4().hex;store.create(ident,validate_request({}))
            engine=Engine(store,FakeComfy(ident),TEMPLATE,'text','vision')
            def call(job,step,prompt,validator,tokens):return validator({'approved':False,'issues':['Dieser Ausschnitt ist gar nicht vorhanden.']})
            engine.json_call=call
            with self.assertRaisesRegex(ValueError,'vorhandenen fremdsprachigen Ausschnitt'):
                engine.require_german(ident,'probe',{'story':'Das ist ein deutscher Satz.'},lambda v:v,600)

    def test_ollama_excludes_external_endpoints_and_cloud_models(self):
        with self.assertRaises(ValueError):local_url('https://8.8.8.8')
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);client=LocalOllama('http://127.0.0.1:11434',store,'local','local','local')
            def answer(path,data=None):
                if path=='/api/tags':return {'models':[{'name':'local','size':100}]}
                return {'capabilities':['completion','vision'],'remote_host':'https://ollama.com'}
            with patch.object(client,'request',side_effect=answer):
                with self.assertRaises(ValueError):client.check_model('local')
            with patch.object(client,'request',return_value={'models':[]}):
                with self.assertRaises(ValueError):client.check_model('not-installed')
            ident=uuid.uuid4().hex;store.create(ident,validate_request({'seed':42}))
            sent=[]
            def local_answer(path,data=None):
                sent.append((path,data))
                if path=='/api/tags':return {'models':[{'name':'local','size':100}]}
                if path=='/api/show':return {'capabilities':['completion','vision']}
                return {'message':{'content':'Eine lokale Geschichte.'}}
            with patch.object(client,'request',side_effect=local_answer):
                self.assertEqual(client.generate(ident,'story','Deutsch bitte',None,200,42),'Eine lokale Geschichte.')
                count=len(sent);client.generate(ident,'story','Deutsch bitte',None,200,42)
                self.assertEqual(len(sent),count)
            payload=next(data for path,data in sent if path=='/api/chat')
            self.assertEqual(payload['keep_alive'],0);self.assertFalse(payload['think'])
            self.assertFalse(any(path=='/api/pull' for path,data in sent))

    def test_optional_feedback_persists_and_guides_future_stories(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);parent=uuid.uuid4().hex
            store.create(parent,validate_request({'kacheln':2,'seed':42}))
            store.write(parent,'story.json',{'title':'Alte Geschichte','story':'Ein alter Brief wird gefunden.'})
            store.update(parent,status='completed')
            # Advancing is independent of any rating, and retry-safe.
            following,created=store.next_story(parent);self.assertTrue(created)
            self.assertFalse(store.next_story(parent)[1]);self.assertEqual(store.preferences()['rated_examples'],[])
            ratings=validate_feedback({'bewertungen':{key:2 for key in CRITERIA},'kommentar':'Mehr überraschende Enden, weniger Wortspiele.'})
            store.save_feedback(parent,ratings)
            self.assertEqual(Store(root).preferences()['rated_examples'][0]['kommentar'],ratings['kommentar'])
            client=FakeComfy(following['id']);engine=Engine(store,client,TEMPLATE,'text','vision');engine.execute(following['id'])
            self.assertTrue(any(ratings['kommentar'] in prompt and 'Alte Geschichte' in prompt for prompt in client.prompts))
            # Changing feedback affects later jobs, not the saved input of this one.
            store.save_feedback(parent,{**ratings,'kommentar':'Anderes Feedback'})
            frozen=store.get(following['id'])['editorial_preferences']['rated_examples'][0]
            self.assertEqual(frozen['kommentar'],ratings['kommentar'])
            self.assertEqual(len(store.preferences()['rated_examples']),1)
        with self.assertRaises(ValueError):validate_feedback({'bewertungen':{key:True for key in CRITERIA}})

    def test_http_put_retry_and_artifact_boundary(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ,{'DATA_DIR':root,'WORKFLOW_TEMPLATE':str(TEMPLATE),'API_TOKEN':'test-token'}):
            service=Service();server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.service=service
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            url='http://127.0.0.1:'+str(server.server_port)
            def call(path,method='GET',data=None,token='test-token'):
                request=urllib.request.Request(url+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
                with urllib.request.urlopen(request) as r:return r.status,json.load(r)
            try:
                ident=uuid.uuid4().hex
                status,job=call('/jobs/'+ident,'PUT',{'kacheln':2});self.assertEqual(status,202)
                status,retried=call('/jobs/'+ident,'PUT',{'kacheln':2});self.assertEqual(status,200)
                self.assertEqual(job['request']['seed'],retried['request']['seed'])
                _,preview=call('/jobs/'+ident+'/story');self.assertFalse(preview['available'])
                service.store.write(ident,'story.json',{'title':'Test','story':'Eine Geschichte.'})
                service.store.update(ident,status='running')
                _,preview=call('/jobs/'+ident+'/story');self.assertTrue(preview['available']);self.assertEqual(preview['story'],'Eine Geschichte.')
                _,running=call('/jobs/'+ident);self.assertTrue(running['story_available']);self.assertEqual(running['story_title'],'Test')
                self.assertEqual(running['artifacts'],[])
                with self.assertRaises(urllib.error.HTTPError) as denied:call('/jobs/'+ident+'/story',token='wrong')
                self.assertEqual(denied.exception.code,401)
                service.store.update(ident,status='completed')
                _,schema=call('/jobs/'+ident+'/feedback');self.assertTrue(schema['optional']);self.assertEqual(len(schema['criteria']),5)
                _,saved=call('/jobs/'+ident+'/feedback','POST',{'bewertungen':{key:4 for key in CRITERIA},'kommentar':'Kürzer bitte.'});self.assertTrue(saved['saved'])
                status,next_job=call('/jobs/'+ident+'/next','POST',{});self.assertEqual(status,202)
                self.assertEqual(call('/jobs/'+ident+'/next','POST',{})[1]['id'],next_job['id'])
                with self.assertRaises(urllib.error.HTTPError) as denied:call('/jobs',token='wrong')
                self.assertEqual(denied.exception.code,401)
                with self.assertRaises(urllib.error.HTTPError) as denied:call('/jobs/'+ident+'/artifacts/../../jobs.sqlite3')
                self.assertEqual(denied.exception.code,404)
            finally:server.shutdown();server.server_close();thread.join()
