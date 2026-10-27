"""Gespeicherte Arbeit bleibt über alle Kacheln erhalten, auch bei Textüberlauf."""
import copy
import json
import tempfile
import zipfile
import unittest
from test_comic_lettering import fixture
from editorial import export
import lettering
from stories import Conflict

class EditingStateTests(unittest.TestCase):
    def test_roundtrip_preserves_draft_without_changing_source_or_jobs(self):
        with tempfile.TemporaryDirectory() as root:
            store,job=fixture(root);info=lettering.manifest(store,job)
            path=store.directory(job['id'])/'editorial-source.json';before=path.read_bytes();jobs=store.list()
            patches=[{k:p[k] for k in ('dialog','bubbles','protected_areas')} for p in info['panels']]
            patches[0]['dialog']='W'*390
            patches[1]['bubbles'][0]['x']=.12
            value={'version':info['version'],'panels':patches,'index':1,'corrections':['','Haare kürzer.']}
            saved=lettering.editor_draft(store,job,value)
            self.assertEqual(saved,lettering.editor_draft(store,job))
            self.assertEqual(saved['draft']['index'],1)
            self.assertEqual(saved['draft']['panels'][0]['dialog'],'W'*390)
            self.assertEqual(path.read_bytes(),before);self.assertEqual(store.list(),jobs)
            artifacts=export(store,job['id']);self.assertNotIn('editing-draft.json',[a['name'] for a in artifacts])
            with zipfile.ZipFile(store.directory(job['id'])/'comic-bundle.zip') as archive:self.assertNotIn('editing-draft.json',archive.namelist())
            for patch in ({'index':-1},{'index':True},{'panels':[]},{'corrections':['x']},{'corrections':['','x'*2001]}):
                with self.subTest(patch=patch),self.assertRaises(ValueError):lettering.editor_draft(store,job,{**value,**patch})
            with self.assertRaises(Conflict):lettering.editor_draft(store,job,{**value,'version':'alt'})
            source=json.loads(path.read_text());source['article']='Geändert';store.write(job['id'],'editorial-source.json',source)
            self.assertIsNone(lettering.editor_draft(store,job)['draft'])
