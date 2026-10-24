"""Quellenskripte ohne echte Modelle und ohne Bilderzeugung prüfen."""
import copy
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import urllib.request
import urllib.error
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
import source_generator as sources
from storage import Store
from stories import Stories, Conflict
STYLE='Ligne claire'


def example():
    text=(Path(__file__).resolve().parents[1]/'docs/Comic_Story_Eingabeformat.md').read_text()
    return text.split('```text')[2].split('```')[0].strip()


class FakeEngine:
    def __init__(self,store):self.store=store;self.sizes=[];self.reviewed=[];self.languages=[]
    def json_call(self,ident,step,prompt,validator,tokens):
        if '-continuity-events-' in step:return validator({'events':[]})
        if step=='source-outline':return validator({'characters':[{'name':'Ria','description':'Junge Frau mit kurzen schwarzen Haaren.','outfit':'Gelber Mantel.','backstory':'Sie sucht einen neuen Weg.'}],'arc':'Anfang, Reise, Heimkehr.','mood':'Warm und ruhig.'})
        if step.startswith('source-review'):
            if 'TEXTGRUNDLAGE:' not in prompt:raise AssertionError('Die Logikprüfung braucht die Originalgrundlage, nicht nur den erzeugten Bogen.')
            self.reviewed.append(step);return validator({'approved':True,'issues':[]})
        start,end,total=map(int,re.search(r'für Kachel (\d+) bis (\d+) von insgesamt (\d+)',prompt).groups())
        people=json.JSONDecoder().raw_decode(prompt.split('FIGUREN: ')[1])[0];who=people[0]['id'];self.sizes.append(end-start+1)
        return validator([{'heading':'Schritt '+str(i),'setting':'Am Fluss, morgens.','story':'Ria geht am Fluss entlang.','dialog':'','characters':[who],'bubbles':[{'speaker':who,'text':'Ich gehe weiter.','expression':'normal'}],'continuity':'keine','character_states':{who:'Gelber Mantel.'}} for i in range(start,end+1)])
    def require_german(self,ident,step,value,validator,tokens):self.languages.append(step);return validator(value)
    def preflight(self,plan,cast):return {'valid':True,'issues':[]}


class SourceTests(unittest.TestCase):
    def test_documented_format_roundtrip_and_errors(self):
        doc=sources.parse(example(),STYLE);self.assertEqual(len(doc['scenes']),2)
        self.assertEqual(doc['scenes'][1]['bubbles'][0]['expression'],'whisper')
        self.assertEqual(sources.parse(sources.emit(doc),STYLE)['scenes'],doc['scenes'])
        for text in [example().replace('KACHEL 2:','KACHEL 3:'),example().replace('Sprecher: Ria','Sprecher: Niemand'),example().replace('KACHELANZAHL: 2','KACHELANZAHL: 3'),example().replace('flüsternd','lautlos')]:
            with self.assertRaises(ValueError):sources.parse(text,STYLE)

    def test_outline_accepts_null_clothing_and_removes_voice_only_narrator(self):
        original={'characters':[{'name':'Siegfried','description':'Junger Mann.','outfit':'Tunika.'},{'name':'Lindwurm','description':'Großer Drache.','outfit':None,'backstory':None},{'name':'Erzähler','description':'Unsichtbare Stimme, die die Geschichte kommentiert.','outfit':None}],'arc':['Begegnung.','Kampf.','Ende.'],'mood':'Spannend.'}
        result=sources.check_outline(original)
        self.assertEqual([c['name'] for c in result['characters']],['Siegfried','Lindwurm'])
        self.assertEqual(result['characters'][1]['outfit'],'Keine Kleidung festgelegt.')
        self.assertEqual(result['characters'][1]['backstory'],'')
        self.assertEqual(result['arc'],'Begegnung.\nKampf.\nEnde.')
        malformed=copy.deepcopy(original);malformed['arc']=[{'unerwartet':'Kein Text'}]
        with self.assertRaisesRegex(ValueError,'Handlungsbogen fehlt'):sources.check_outline(malformed)
        self.assertEqual(len(original['characters']),3);self.assertIsNone(original['characters'][1]['outfit'])
        visible={'characters':[{'name':'Erzähler','description':'Mann im schwarzen Mantel.','outfit':'Mantel.'}],'arc':'Ein Mann betritt den Raum.','mood':''}
        self.assertEqual(len(sources.check_outline(visible)['characters']),1)
        original['characters'][0]['outfit']='x'*1001
        with self.assertRaisesRegex(ValueError,'maximal 1000'):sources.check_outline(original)

    def test_profile_type_errors_are_not_reported_as_length_errors(self):
        from character_profiles import validate
        with self.assertRaisesRegex(ValueError,'outfit: Text erwartet'):validate({'outfit':None})

    def test_post_summary_is_copyable_saved_and_adopted_without_model_calls(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);entries=sources.catalog(store)
            self.assertTrue(entries[0]['post_summary']);self.assertNotIn('kein Volltext:',entries[0]['post_summary'])
            self.assertLessEqual(len(entries[0]['post_summary']),600)
            summary='Ein persönlicher Begleittext.\n\n'+('Die Reise führt ins Unbekannte. '*22)
            saved=sources.save_source(store,{**entries[0],'post_summary':summary})
            self.assertEqual(sources.catalog(store)[0]['post_summary'],summary.strip())
            job=sources.enqueue(store,{'source_id':saved['id'],'count':2,'style':STYLE});sources.run(FakeEngine(store),job['id']);store.stage(job['id'],'finished',status='completed')
            script=(store.directory(job['id'])/'source-script.txt').read_text()
            story=sources.adopt(Stories(store),store,job['id'],{'script':script,'post_summary':'Ein Sohn begegnet seinem Vater.'})
            self.assertEqual(story['payload']['post_summary'],'Ein Sohn begegnet seinem Vater.')
            with self.assertRaisesRegex(ValueError,'Begleittext'):sources.adopt(Stories(store),store,job['id'],{'script':script,'post_summary':'x'*1201})

    def test_catalog_persists_user_sources_and_never_overwrites_defaults(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);original=copy.deepcopy(sources.BUILTINS);entry=sources.save_source(store,{'title':'Mein alter Film','kind':'Film','edition':'Konkrete Fassung','text':'Eigene Szenenzusammenfassung.','rights':'Noch zu prüfen.','territories':'Deutschland'})
            entries=sources.catalog(Store(root));self.assertEqual(len(entries),4);self.assertEqual(entries[-1]['id'],entry['id'])
            entry['text']='Überarbeitete Zusammenfassung.';sources.save_source(store,entry)
            self.assertEqual(sources.catalog(store)[-1]['text'],entry['text']);self.assertEqual(sources.BUILTINS,original)
            self.assertIn('Frankreich',sources.catalog(store)[0]['rights'])

    def test_batches_and_edited_script_adopt_directly_without_another_model_call(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);stories=Stories(store);job=sources.enqueue(store,{'source_id':'kleiner-prinz','count':13,'style':STYLE,'author':'Mein Pseudonym'});engine=FakeEngine(store)
            with self.assertRaises(Conflict):sources.adopt(stories,store,job['id'],{'script':example()})
            result=sources.run(engine,job['id']);store.stage(job['id'],'finished',**result)
            self.assertEqual(engine.sizes,[6,6,1]);self.assertEqual(len(engine.reviewed),3);self.assertEqual(len(engine.languages),4)
            script=(store.directory(job['id'])/'source-script.txt').read_text().replace('Ich gehe weiter.','Ich bleibe hier.')
            story=sources.adopt(stories,store,job['id'],{'script':script})
            self.assertEqual(len(story['payload']['scenes']),13);self.assertEqual(story['payload']['scenes'][0]['bubbles'][0]['text'],'Ich bleibe hier.')
            self.assertEqual(story['payload']['book_author'],'Mein Pseudonym');self.assertIn('Am Fluss',story['payload']['scenes'][0]['story'])
            self.assertEqual(len(store.list()),1);self.assertEqual(len(stories.list()),1)
            self.assertEqual(story['payload']['planned_article'],story['payload']['article']);self.assertEqual(story['payload']['planned_count'],13)
            known={c['id'] for c in story['payload']['characters']}
            self.assertTrue(all(set(s['character_states'])<=known for s in story['payload']['scenes']))

    def test_authenticated_api_queues_only_script_then_adopts_without_render(self):
        from app import Service,Handler
        with tempfile.TemporaryDirectory() as root:
            with patch.object(Service,'__init__',lambda self:None):service=Service()
            service.store=Store(root);service.stories=Stories(service.store);service.token='test'
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.service=service;thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def call(path,method='GET',data=None,auth=True):
                request=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Authorization':'Bearer test'} if auth else {})
                try:
                    with urllib.request.urlopen(request) as response:return response.status,json.load(response)
                except urllib.error.HTTPError as exc:return exc.code,json.load(exc)
            try:
                self.assertEqual(call('/sources',auth=False)[0],401)
                self.assertEqual(len(call('/sources')[1]['sources']),3)
                code,job=call('/source-tasks','POST',{'source_id':'bremer-stadtmusikanten','count':2,'style':STYLE});self.assertEqual(code,202)
                self.assertEqual(call('/jobs')[1]['jobs'],[]);self.assertEqual(service.stories.list(),[])
                ident=job['id'];engine=FakeEngine(service.store);result=sources.run(engine,ident);service.store.stage(ident,'finished',**result)
                code,draft=call('/source-tasks/'+ident);self.assertEqual(code,200);self.assertIn('KACHEL 2:',draft['script'])
                edited=draft['script'].replace('Ich gehe weiter.','Ich warte.');self.assertEqual(call('/source-tasks/'+ident+'/script','PUT',{'script':edited})[0],200)
                self.assertIn('Ich warte.',call('/source-tasks/'+ident)[1]['script'])
                code,story=call('/source-tasks/'+ident+'/adopt','POST',{'script':draft['script']});self.assertEqual(code,201)
                self.assertEqual(len(story['payload']['scenes']),2);self.assertEqual(len(service.store.list()),1)
                self.assertEqual(call('/source-tasks','POST',{'source_id':'missing','style':STYLE})[0],400)
                self.assertEqual(call('/source-tasks/'+ident+'/adopt','POST',{'script':'falsch'})[0],400)
            finally:server.shutdown();server.server_close();thread.join()
