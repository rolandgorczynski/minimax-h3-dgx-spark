"""Geschichtenverwaltung: Versionen, unveränderte Snapshots und begrenztes Löschen."""
import ast
import os
import threading
import urllib.request
import urllib.error
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'automation/comics'))
from storage import Store
from stories import Stories,Conflict,validate_definition
from engine import STYLES,validate_request


def definition():
    ident='a'*32
    return {'mode':'editorial','name':'Eine ruhige Geschichte','payload':{
        'article':'Anna findet einen Brief.','style':'Großstadt-Noir (düster)','seed':42,
        'characters':[{'id':ident,'name':'Anna','description':'Kurzes Haar','outfit':'Graue Jacke','aliases':[],'references':[],'inline_references':['gespeicherte-referenz']}],
        'scenes':[{'story':'Anna steht am Fenster.','dialog':'Ein Brief wartet.','characters':[ident],'bubbles':[]}],
    }}


class StoriesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(self.temp.name);self.stories=Stories(self.store)

    def test_script_availability_tracks_content_and_count_not_image_style(self):
        value=definition();value['payload'].update(planned_article=value['payload']['article'],planned_count=1,panel_count=1,visual_style_pending=True,source_provenance={'id':'quelle'})
        story=self.stories.save(value)
        summary=self.stories.list()[0]
        self.assertTrue(summary['script_ready'])
        self.assertEqual(summary['script_source_id'],'quelle')
        self.assertEqual(len(summary['script_source_sha256']),64)
        value['payload']['article']='Inzwischen geänderter Ausgangstext.'
        changed=self.stories.save(value,story['id'],story['version'])
        self.assertFalse(self.stories.list()[0]['script_ready'])
        value['payload']['planned_article']=value['payload']['article'];value['payload']['panel_count']=2
        changed=self.stories.save(value,changed['id'],changed['version'])
        self.assertFalse(self.stories.list()[0]['script_ready'])
        value['payload']['scenes']=[]
        self.stories.save(value,changed['id'],changed['version'])
        self.assertFalse(self.stories.list()[0]['script_ready'])

    def test_changed_meaning_blocks_images_until_script_is_replanned(self):
        value=definition();value['payload']['script_needs_replan']=True
        story=self.stories.save(value)
        self.assertFalse(self.stories.list()[0]['script_ready'])
        with self.assertRaisesRegex(ValueError,'Skript passt nicht'):
            self.stories.enqueue(story['id'],1)

    def test_stale_script_is_not_rendered_and_style_changes_keep_scenes(self):
        value=definition();value['payload'].update(planned_article=value['payload']['article'],planned_count=1,panel_count=1)
        story=self.stories.save(value)
        value['payload']['style']='Geisterfolklore-Manga'
        changed=self.stories.save(value,story['id'],1)
        self.assertEqual(changed['payload']['scenes'],story['payload']['scenes'])
        self.assertTrue(self.stories.enqueue(story['id'],2)['editorial_mode'])
        value['payload']['article']='Ein neuer Ausgangstext.'
        stale=self.stories.save(value,story['id'],2)
        with self.assertRaisesRegex(ValueError,'Skript passt nicht'):self.stories.enqueue(story['id'],stale['version'])

    def test_edit_version_conflict_and_small_list(self):
        original=self.stories.save(definition());changed=definition();changed['payload']['style']='Holzschnitt / Linolschnitt'
        edited=self.stories.save(changed,original['id'],1)
        self.assertEqual(edited['version'],2)
        self.assertEqual(edited['payload']['scenes'],original['payload']['scenes'])
        with self.assertRaises(Conflict):self.stories.save(changed,original['id'],1)
        self.assertNotIn('payload',self.stories.list()[0])

    def test_generation_snapshots_are_independent_and_delete_is_owned(self):
        story=self.stories.save(definition());j=self.stories.enqueue(story['id'],1)
        self.assertEqual(j['status'],'queued');self.assertTrue(j['editorial_mode'])
        saved=json.loads((self.store.directory(j['id'])/'editorial-source.json').read_text())
        self.assertEqual(saved['scenes'],story['payload']['scenes'])
        with self.assertRaises(Conflict):self.stories.delete(story['id'],1)
        with self.assertRaises(Conflict):self.stories.delete_job(j['id'])
        self.store.stage(j['id'],'finished',status='needs_review')
        self.store.write(j['id'],'characters.json',saved['characters'])
        second=self.stories.enqueue(story['id'],1)
        self.assertNotEqual(j['id'],second['id'])
        self.store.stage(second['id'],'finished',status='completed')
        outsider=uuid.uuid4().hex;self.store.create(outsider,validate_request({'seed':42}),initial_status='editing')
        self.store.write(outsider,'behalten.txt',b'Original')
        self.assertEqual(self.stories.delete(story['id'],1),2)
        self.assertIsNotNone(self.store.get(outsider));self.assertTrue((self.store.directory(outsider)/'behalten.txt').exists())
        self.assertIsNone(self.store.get(j['id']))

    def test_legacy_family_deletes_by_ancestry_not_title_and_preserves_imports(self):
        def output(parent=None,story_id=None,status='completed'):
            ident=uuid.uuid4().hex;self.store.create(ident,validate_request({'kacheln':1}),initial_status='editing')
            self.store.update(ident,parent_job=parent,story_id=story_id,status=status,story_title='Gleicher Titel')
            self.store.write(ident,'comic.png',b'behalten oder entfernen');return ident
        root=output();child=output(root);sibling=output(root);other=output()
        saved=self.stories.save(definition());imported=output(root,saved['id'])
        target=self.stories.deletion_target(child)
        self.assertEqual(target['ids'],sorted([root,child,sibling]));self.assertIsNone(target['story_id'])
        self.assertEqual(self.stories.deletion_target(imported)['story_id'],saved['id'])
        with self.assertRaises(Conflict):self.stories.delete_legacy_story(child,[child])
        self.store.update(imported,status='running')
        with self.assertRaises(Conflict):self.stories.delete_legacy_story(child,target['ids'])
        self.store.update(imported,status='completed')
        self.store.update(sibling,status='running')
        with self.assertRaises(Conflict):self.stories.delete_legacy_story(child,target['ids'])
        self.assertIsNotNone(self.store.get(root))
        self.store.update(sibling,status='completed')
        self.assertEqual(self.stories.delete_legacy_story(child,target['ids']),3)
        for ident in (root,child,sibling):
            self.assertIsNone(self.store.get(ident));self.assertFalse((self.store.root/'jobs'/ident).exists())
        self.assertIsNotNone(self.store.get(other));self.assertIsNotNone(self.store.get(imported))
        self.assertEqual(self.stories.get(saved['id'])['name'],saved['name'])

    def test_orphaned_story_links_form_one_legacy_family(self):
        missing=uuid.uuid4().hex;ids=[uuid.uuid4().hex for _ in range(2)]
        for ident in ids:
            self.store.create(ident,validate_request({'kacheln':1}),initial_status='editing')
            self.store.update(ident,story_id=missing,status='completed')
        self.assertEqual(self.stories.deletion_target(ids[0])['ids'],sorted(ids))
        self.assertEqual(self.stories.delete_legacy_story(ids[0],sorted(ids)),2)

    def test_import_keeps_reference_snapshots_and_original(self):
        ident=uuid.uuid4().hex;self.store.create(ident,validate_request({'kacheln':1,'seed':42}),initial_status='editing')
        source=definition()['payload'];source['title']='Import';source['library_ids']=['b'*32]
        self.store.write(ident,'editorial-source.json',source);self.store.write(ident,'characters.json',source['characters'])
        imported=self.stories.import_job(ident)
        self.assertEqual(imported['payload']['library_ids'],[])
        self.assertEqual(imported['payload']['characters'],source['characters'])
        self.stories.delete(imported['id'],1)
        self.assertIsNotNone(self.store.get(ident))

    def test_new_empty_draft_saves_but_does_not_render(self):
        value=definition();value['payload']['scenes']=[]
        story=self.stories.save(value)
        with self.assertRaisesRegex(ValueError,'Szenenplan'):self.stories.enqueue(story['id'],1)
        self.assertEqual(self.store.list(),[])

    def test_automatic_mode_retains_existing_pipeline(self):
        story=self.stories.save({'mode':'automatic','name':'Der Brief','payload':{'thema':'Ein verlorener Brief','stil':'Warme Alltagsillustration','kacheln':2}})
        job=self.stories.enqueue(story['id'],1)
        self.assertFalse(job['editorial_mode']);self.assertEqual(job['request']['thema'],'Ein verlorener Brief')

    def test_all_styles_match_renderer_and_request_validation(self):
        from art_styles import CATALOG
        import importlib.util
        spec=importlib.util.spec_from_file_location('style_registry_test',ROOT/'extensions/dgx-comics/story.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
        self.assertEqual(list(native.STYLES),STYLES);self.assertEqual(len(STYLES),77)
        self.assertEqual([s['name'] for s in CATALOG],STYLES)
        for style in STYLES:self.assertEqual(validate_request({'stil':style})['stil'],style)

    def test_layout_download_keeps_scope_and_format_checks(self):
        from comfy import Comfy,ComfyError
        ident='a'*32;client=Comfy('http://unused',self.store)
        descriptor={'filename':'comic.pdf','subfolder':'comic-automation/'+ident+'/web-layout','type':'temp'}
        client.request=lambda *args:b'%PDF-1.4 test'
        self.assertTrue(client.download(ident,descriptor,kind='pdf').startswith(b'%PDF'))
        with self.assertRaises(ComfyError):client.download(ident,descriptor)
        with self.assertRaises(ComfyError):client.download('b'*32,descriptor,kind='pdf')
        client.request=lambda *args:{'nodes':[]}
        self.assertEqual(json.loads(client.download(ident,{**descriptor,'filename':'workflow.json'},kind='json')),{'nodes':[]})

    def test_stale_version_never_queues_a_job(self):
        story=self.stories.save(definition())
        with self.assertRaises(Conflict):self.stories.enqueue(story['id'],0)
        self.assertEqual(self.store.list(),[])


class DismissPlanningTests(unittest.TestCase):
    def test_failed_plan_can_be_closed_without_touching_definition(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);stories=Stories(store);original=stories.save(definition())
            job=stories.plan(original['id'],original['version'])
            with self.assertRaises(Conflict):stories.dismiss_plan(job['id'])
            store.stage(job['id'],'failed',status='failed',error='Alter Modellfehler')
            stories.dismiss_plan(job['id'])
            self.assertTrue(store.get(job['id'])['planning_dismissed'])
            self.assertEqual(store.get(job['id'])['error'],'Alter Modellfehler')
            self.assertEqual(stories.get(original['id']),original)
            retry=stories.plan(original['id'],original['version'])
            self.assertNotEqual(retry['id'],job['id'])

class LegacyDeletionAPITests(unittest.TestCase):
    def test_authenticated_confirmed_deletion_keeps_other_stories(self):
        from app import Service,Handler,ThreadingHTTPServer
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'DATA_DIR':root,'WORKFLOW_TEMPLATE':str(ROOT/'examples/comics/workflows/04_Comic_Automat_9B.json'),'API_TOKEN':'test'}):
            service=Service();ids=[uuid.uuid4().hex for _ in range(3)];cleaned=[]
            for ident in ids:
                service.store.create(ident,validate_request({'kacheln':1}),initial_status='editing')
                service.store.update(ident,status='completed')
            service.store.update(ids[1],parent_job=ids[0]);service.cleanup=lambda ident:cleaned.append(ident)
            handler=type('LegacyHandler',(Handler,),{'service':service});server=ThreadingHTTPServer(('127.0.0.1',0),handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def call(method='GET',value=None,auth=True):
                req=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+'/jobs/'+ids[1]+'/story-family',method=method,data=json.dumps(value).encode() if value is not None else None,headers={'Authorization':'Bearer test'} if auth else {})
                try:
                    with urllib.request.urlopen(req) as response:return response.status,json.load(response)
                except urllib.error.HTTPError as exc:return exc.code,json.load(exc)
            try:
                self.assertEqual(call(auth=False)[0],401)
                status,target=call();self.assertEqual(status,200);self.assertEqual(target['ids'],sorted(ids[:2]))
                self.assertEqual(call('DELETE',{'ids':[ids[1]]})[0],409);self.assertEqual(cleaned,[])
                service.store.update(ids[0],status='running')
                self.assertEqual(call('DELETE',{'ids':target['ids']})[0],409);self.assertEqual(cleaned,[])
                service.store.update(ids[0],status='completed')
                self.assertEqual(call('DELETE',{'ids':target['ids']})[0],200)
                self.assertEqual(sorted(cleaned),sorted(ids[:2]));self.assertIsNotNone(service.store.get(ids[2]))
                self.assertIsNone(service.store.get(ids[0]));self.assertIsNone(service.store.get(ids[1]))
            finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
