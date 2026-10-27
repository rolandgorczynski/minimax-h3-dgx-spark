"""Figuren neu gestalten: Identität bewahren, lokale Arbeit getrennt speichern."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'automation/comics'))
import character_profiles as profiles
from storage import Store
from app import Service,Handler,ThreadingHTTPServer
spec=importlib.util.spec_from_file_location('profiles_native',ROOT/'extensions/dgx-comics/characters.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)


def profile():
    return {'id':'a'*32,'name':'Ria','description':'19 Jahre, kurze braune Haare.',
            'outfit':'Blauer Mantel','backstory':'Wuchs in einer Hafenstadt auf.',
            'personality':'Neugierig und geduldig.','motivation':'Ihre Schwester finden.',
            'alignment':'neutral_good','aliases':['Ria Sommer'],'variants':{},'references':[]}


class ProfileTests(unittest.TestCase):
    def test_optional_alignment_and_legacy_edits_preserve_biography(self):
        with tempfile.TemporaryDirectory() as root:
            lib=native.CharacterLibrary(root);saved=lib.save(profile())
            self.assertEqual(saved['backstory'],profile()['backstory'])
            legacy={k:v for k,v in saved.items() if k not in ('backstory','personality','motivation','alignment')}
            legacy['name']='Ria Sommer';new=lib.save(legacy)
            self.assertEqual(new['alignment'],'neutral_good');self.assertEqual(new['backstory'],saved['backstory'])
            cleared=lib.save({**new,'alignment':''});self.assertEqual(cleared['alignment'],'')
            self.assertNotIn('alignment',profiles.narrative(cleared))
            with self.assertRaises(ValueError):lib.save({**cleared,'alignment':'unbekannt'})
            for key in profiles.ALIGNMENTS:self.assertEqual(native.validate_character({**profile(),'alignment':key})['alignment'],key)
            with self.assertRaises(ValueError):lib.save({**cleared,'version':saved['version']})

    def test_regeneration_changes_only_appearance_alignment_and_image(self):
        for determine in (True,False):
            with self.subTest(determine=determine),tempfile.TemporaryDirectory() as root:
                store=Store(root);original=profile();original['inline_references']=['altes-bild']
                work=profiles.enqueue(store,{'profile':original,'style':'Großstadt-Noir (düster)','determine_alignment':determine})
                class FakeEngine:
                    def __init__(self):self.store=store
                    def json_call(self,ident,step,prompt,validator,**kwargs):
                        return validator({'description':'19 Jahre, lockige schwarze Haare und Sommersprossen.','alignment':'chaotic_good','id':'b'*32,'name':'Unzulässiger Ersatz','backstory':'Unzulässige neue Biografie'})
                    def portrait(self,ident,c,index,style):
                        self.asserted=(c['id'],c['name'],style);return 'bmV1ZXMtYmlsZA=='
                engine=FakeEngine();result=profiles.regenerate(engine,work['id'])
                updated=json.loads((store.directory(work['id'])/'character-result.json').read_text())
                for key in original:
                    if key not in ('description','alignment','inline_references','references'):self.assertEqual(updated[key],original[key])
                self.assertNotEqual(updated['description'],original['description'])
                self.assertEqual(updated['alignment'],'chaotic_good' if determine else '')
                self.assertEqual(updated['inline_references'],['bmV1ZXMtYmlsZA=='])
                self.assertEqual(result['status'],'completed');self.assertTrue(store.get(work['id'])['character_mode'])
                self.assertEqual(original['inline_references'],['altes-bild'])
                self.assertFalse((store.directory(work['id'])/'comic.png').exists())

    def test_first_portrait_preserves_every_profile_field_without_text_model(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);original=profile()
            work=profiles.enqueue(store,{'profile':original,'style':'Großstadt-Noir (düster)','portrait_only':True})
            class FakeEngine:
                def __init__(self):self.store=store
                def json_call(self,*args,**kwargs):raise AssertionError('Keine neue Beschreibung erfinden.')
                def portrait(self,ident,c,index,style):
                    self.seen=copy.deepcopy(c);return 'bmV1ZXMtYmlsZA=='
            engine=FakeEngine();profiles.regenerate(engine,work['id'])
            result=json.loads((store.directory(work['id'])/'character-result.json').read_text())
            for key in original:self.assertEqual(result[key],original[key])
            self.assertEqual(engine.seen,original)
            self.assertEqual(result['inline_references'],['bmV1ZXMtYmlsZA=='])
            self.assertFalse((store.directory(work['id'])/'comic.png').exists())

    def test_authenticated_proxy_and_separate_regeneration_status(self):
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'DATA_DIR':root,'WORKFLOW_TEMPLATE':str(ROOT/'examples/comics/workflows/04_Comic_Automat_9B.json'),'LLM_BACKEND':'comfyui','API_TOKEN':'test'}):
            service=Service();calls=[]
            def remote(method,path,data=None):
                calls.append((method,path,copy.deepcopy(data)))
                if method=='GET' and path=='/dgx-comics/characters':return {'characters':[profile()]}
                if method=='GET':return b'png-bytes'
                if method=='POST':return {**data,'version':2}
                return {'deleted':profile()['id']}
            service.client.request=remote
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.service=service
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def call(path,method='GET',data=None,auth=True):
                req=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Authorization':'Bearer test'} if auth else {})
                try:
                    with urllib.request.urlopen(req) as r:return r.status,json.load(r)
                except urllib.error.HTTPError as exc:return exc.code,json.load(exc)
            try:
                self.assertEqual(call('/characters',auth=False)[0],401)
                self.assertEqual(call('/characters/regenerate','POST',{},auth=False)[0],401)
                self.assertEqual(call('/characters')[1]['characters'][0]['name'],'Ria')
                self.assertEqual(call('/characters','POST',profile())[1]['version'],2)
                self.assertEqual(call('/characters','POST',{**profile(),'alignment':False})[0],400)
                self.assertEqual(call('/characters/regenerate','POST',{'profile':profile(),'style':'Großstadt-Noir (düster)','determine_alignment':True})[0],202)
                job=store_job=service.store.list()[0]
                self.assertEqual(call('/jobs')[1]['jobs'],[])
                self.assertEqual(call('/characters/regenerations/'+job['id'])[1]['status'],'queued')
                self.assertEqual(call('/characters/'+'a'*32,'DELETE',{'version':1})[0],200)
                self.assertEqual(calls[-1][0],'DELETE')
                self.assertFalse(any(p=='/prompt' for _,p,_ in calls))
            finally:server.shutdown();server.server_close();thread.join()
