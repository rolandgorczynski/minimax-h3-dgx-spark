"""Geschichtenverwaltung: Versionen, unveränderte Snapshots und begrenztes Löschen."""
import ast
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

if __name__=='__main__':unittest.main()
