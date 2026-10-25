"""Serienfolgen übernehmen Kontext und private Figuren, ohne Originale oder Bilderläufe anzufassen."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import urllib.request
import urllib.error
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
from storage import Store
from stories import Stories,Conflict
from engine import Engine,validate_request
import series
from article_plan import prepare

STYLE='Ligne claire';FIGURE='a'*32

def original(stories):
    return stories.save({'name':'Das Tor','mode':'editorial','payload':{'article':'Ria findet ein Tor. Sie geht hindurch.','style':STYLE,'seed':42,'panel_count':2,'characters':[{'id':FIGURE,'name':'Ria','description':'Junge Frau mit schwarzen Haaren.','outfit':'Gelbe Jacke.','backstory':'Sucht ihren Bruder.','alignment':'neutral_good','references':[],'inline_references':['cHJpdmF0ZXMtYmlsZA==']}],'scenes':[{'story':'Ria steht vor einem Tor.','dialog':'','characters':[FIGURE],'bubbles':[]},{'story':'Ria geht hindurch.','dialog':'','characters':[FIGURE],'bubbles':[],'character_states':{FIGURE:'Kurze Haare, gelbe Jacke, trägt einen Schlüssel.'}}],'book_author':'Mein Pseudonym'}})

def options(stories,parent,**changes):
    return {**series.preview(stories,{'base_kind':'story','base_id':parent['id']})['settings'],**changes}

class SeriesTests(unittest.TestCase):
    def test_direct_episode_inherits_physical_states_but_new_universe_story_does_not(self):
        with tempfile.TemporaryDirectory() as root:
            stories=Stories(Store(root));parent=original(stories);parent['payload']['scenes'][-1]['continuity_state']={FIGURE:{'movement':'beritten','held':'Zügel'}}
            parent=stories.save(parent,parent['id'],parent['version'])
            direct=series.create(stories,options(stories,parent,title='Direkte Folge',mode='direct'))
            self.assertEqual(direct['payload']['series']['initial_continuity_state'][FIGURE]['movement'],'beritten')
            later=series.create(stories,options(stories,parent,title='Neue Handlung',mode='universe',episode=3))
            self.assertNotIn('initial_continuity_state',later['payload']['series'])

    def test_new_episode_keeps_id_images_and_last_state_without_mutating_original(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);stories=Stories(store);parent=original(stories);before=copy.deepcopy(parent)
            child=series.create(stories,options(stories,parent,title='Hinter dem Tor',count=25,article='Ria entdeckt hinter dem Tor eine Bibliothek.',canon='Das Tor öffnet sich nur einmal.',open_threads='Wo ist Rias Bruder?'))
            p=child['payload'];self.assertEqual(stories.get(parent['id']),before);self.assertNotEqual(child['id'],parent['id'])
            self.assertEqual(p['characters'],parent['payload']['characters']);self.assertEqual(p['series']['initial_states'][FIGURE],'Kurze Haare, gelbe Jacke, trägt einen Schlüssel.')
            self.assertEqual(p['panel_count'],25);self.assertEqual(p['style'],STYLE);self.assertEqual(p['scenes'],[]);self.assertEqual(store.list(),[])
            self.assertEqual(p['book_author'],'Mein Pseudonym');self.assertEqual(p['series']['based_on']['version'],1)
            child['payload']['series']['canon']='Neue feste Regel.';saved=stories.save(child,child['id'],child['version']);self.assertEqual(saved['payload']['series']['canon'],'Neue feste Regel.')

    def test_numbering_lineage_and_prompt_for_same_universe(self):
        with tempfile.TemporaryDirectory() as root:
            stories=Stories(Store(root));parent=original(stories);second=series.create(stories,options(stories,parent,canon='Ria kann nicht fliegen.',open_threads='Der Bruder wird gesucht.'))
            values=options(stories,second,mode='universe');self.assertEqual(values['episode'],3)
            prompt=series.preview(stories,values)['writing_prompt'];self.assertIn('Ria kann nicht fliegen.',prompt);self.assertIn('Neue Handlung im selben Universum',prompt)
            third=series.create(stories,values);self.assertEqual(third['payload']['series']['id'],parent['id']);self.assertEqual(third['payload']['series']['based_on']['id'],second['id'])
            self.assertEqual(options(stories,parent)['episode'],4)
            with self.assertRaises(Conflict):series.create(stories,{**options(stories,parent),'episode':2})
            self.assertEqual(stories.list()[0]['series']['episode'],3)

    def test_source_version_changes_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            stories=Stories(Store(root));parent=original(stories);values=options(stories,parent);stories.save(parent,parent['id'],1)
            with self.assertRaises(Conflict):series.create(stories,values)

    def test_finished_output_uses_rendered_private_references(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);stories=Stories(store);parent=original(stories);ident='b'*32;store.create(ident,validate_request({'kacheln':2,'stil':STYLE}))
            payload=copy.deepcopy(parent['payload']);payload['characters'][0]['inline_references']=['bmV1ZXMtYmlsZA=='];store.write(ident,'editorial-source.json',payload);store.write(ident,'characters.json',payload['characters']);store.update(ident,status='needs_review',story_id=parent['id'],story_title='Gezeichnetes Tor')
            preview=series.preview(stories,{'base_kind':'job','base_id':ident});child=series.create(stories,preview['settings'])
            self.assertEqual(child['payload']['characters'][0]['inline_references'],['bmV1ZXMtYmlsZA==']);self.assertEqual(child['payload']['series']['id'],parent['id'])
            self.assertTrue(any(b['kind']=='job' for b in series.bases(stories)))
            # New references also carry over from the last finished output when the saved profile is unchanged.
            p=parent['payload'];p['characters'][0].pop('inline_references');parent=stories.save(parent,parent['id'],parent['version'])
            inherited=series.snapshot(stories,'story',parent['id']);self.assertEqual(inherited['payload']['characters'][0]['inline_references'],['bmV1ZXMtYmlsZA=='])

    def test_new_scene_planning_keeps_series_context_and_identity(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);stories=Stories(store);parent=original(stories);child=series.create(stories,options(stories,parent,article='Ria geht durch einen Flur.\n\nRia findet eine Bibliothek.',count=2,canon='Das Tor öffnet sich nur einmal.'));job=stories.plan(child['id'],child['version']);prompts=[]
            class FakeEngine:
                validate_scenes=Engine.validate_scenes
                def __init__(self):self.store=store
                def require_german(self,ident,step,value,validator,tokens):return validator(value)
                def json_call(self,ident,step,prompt,validator,tokens):
                    if step=='story-meaning-v4':return validator({'central_question':'Was verändert eine neue Begegnung?','meaning_type':'Erkenntnis','core':'Neue Erfahrungen können Perspektiven verändern.','evidence':[{'event':'Ria entdeckt einen neuen Ort.','meaning':'Eine neue Erfahrung wird möglich.'}],'causal_chain':['Ria geht weiter und entdeckt einen Ort.'],'ending':'Die Entdeckung bleibt offen.','recommended_count':6,'reason':'Ein kurzer Erkenntnisschritt.','series_reason':'Eine Folge reicht.'})
                    if step.startswith('story-meaning'):return validator({'approved':True,'issues':[]})
                    if '-continuity-events-' not in step:prompts.append(prompt)
                    if '-continuity-events-' in step:return validator({'events':[]})
                    if step=='article-people':return validator({'characters':[{'name':'Ria','description':'Andere Beschreibung, darf nicht übernommen werden.','outfit':'Andere Kleidung.'}]})
                    return validator([{'story':'Ria geht durch den Flur.','dialog':'','characters':[FIGURE],'bubbles':[]},{'story':'Ria schaut in die Bibliothek.','dialog':'','characters':[FIGURE],'bubbles':[]}])
                def preflight(self,*args):return {'valid':True,'issues':[]}
            prepare(FakeEngine(),stories,job['id']);planned=stories.get(child['id'])['payload'];self.assertEqual(planned['characters'][0],parent['payload']['characters'][0])
            self.assertTrue(all('SERIENKONTEXT' in p for p in prompts));self.assertIn('Das Tor öffnet sich nur einmal.',prompts[-1]);self.assertEqual(planned['scenes'][0]['character_states'][FIGURE],parent['payload']['scenes'][-1]['character_states'][FIGURE])
            self.assertEqual(stories.get(parent['id']),parent)

    def test_api_preview_and_creation_do_not_queue_model_or_image_jobs(self):
        from app import Service,Handler
        with tempfile.TemporaryDirectory() as root:
            with patch.object(Service,'__init__',lambda self:None):service=Service()
            service.store=Store(root);service.stories=Stories(service.store);service.token='test';parent=original(service.stories)
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.service=service;thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def call(path,method='GET',data=None,auth=True):
                request=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Authorization':'Bearer test'} if auth else {})
                try:
                    with urllib.request.urlopen(request) as response:return response.status,json.load(response)
                except urllib.error.HTTPError as exc:return exc.code,json.load(exc)
            try:
                self.assertEqual(call('/series/bases',auth=False)[0],401);self.assertEqual(call('/series/bases')[1]['bases'][0]['id'],parent['id'])
                status,info=call('/series/preview','POST',{'base_kind':'story','base_id':parent['id']});self.assertEqual(status,200)
                status,child=call('/series/episodes','POST',info['settings']);self.assertEqual(status,201);self.assertEqual(child['payload']['series']['episode'],2)
                self.assertEqual(service.store.list(),[]);self.assertEqual(service.stories.get(parent['id']),parent)
                self.assertEqual(call('/series/episodes','POST',{'base_kind':'story','base_id':parent['id'],'count':0})[0],400)
            finally:server.shutdown();server.server_close();thread.join()
