"""Einzelbildkorrektur darf genau eine Zeichnung ersetzen und keine Dialoge ändern."""
import base64
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_comic_lettering import fixture
import panel_correction
from lettering import manifest
from editorial import export
from engine import Engine
from stories import Stories,Conflict


def setup(root):
    store,parent=fixture(root);path=store.directory(parent['id']);
    from lettering import DESIGN
    for i in range(2):
        DESIGN.panel(Image.new('RGB',(1024,704),'#334455'),'',i+1,[{'speaker':'b'*32,'text':'Hallo!'}]).save(path/f'panels/{i+1:02}_panel.png')
    cast=json.loads((path/'characters.json').read_text());cast[0]['inline_references']=[base64.b64encode((path/'panels/01_art.png').read_bytes()).decode()];store.write(parent['id'],'characters.json',cast);store.stage(parent['id'],'finished',status='needs_review',artifacts=export(store,parent['id']));return store,store.get(parent['id'])


class PanelCorrectionTests(unittest.TestCase):
    def test_exactly_one_panel_is_generated_and_other_files_are_identical(self):
        with tempfile.TemporaryDirectory() as root:
            store,parent=setup(root);info=manifest(store,parent);original={str(p.relative_to(store.directory(parent['id']))):p.read_bytes() for p in store.directory(parent['id']).rglob('*') if p.is_file()}
            job=panel_correction.enqueue(store,parent,{'version':info['version'],'panel':1,'correction':'Bei Ria die Haare kürzer.'})
            with self.assertRaises(Conflict):Stories(store).delete_job(parent['id'])
            picture=io.BytesIO();Image.new('RGB',(1024,704),'red').save(picture,format='PNG');generated=picture.getvalue();studio_calls=[];downloads=[]
            class Client:
                def download(self,ident,descriptor):downloads.append(descriptor);return generated
                def request(self,*args,**kwargs):raise AssertionError('Keine anderen ComfyUI-Aufträge erlauben.')
            class FakeEngine:
                validate_scenes=Engine.validate_scenes
                def __init__(self):self.store=store;self.client=Client()
                def json_call(self,ident,step,prompt,validator,images,tokens):
                    self.asserted_image=images[0];return validator({'story':'Ria mit sichtbar kürzerem Bob sitzt am Eingang.','character_states':{'b'*32:'Kinnlanger Bob.'}})
                def preflight(self,plan,cast):self.checked_count=len(plan['scenes']);return {'valid':True,'issues':[]}
                def studio(self,ident,step,doc,cast,plan,revisions,request_override):studio_calls.append((request_override,copy.deepcopy(plan)));return {'comic_panels':[{'filename':'01_panel.png','type':'temp','subfolder':'test'}]}
                def workflow(self,*args):return {'nodes':[]}
            engine=FakeEngine();result=panel_correction.run(engine,job['id']);self.assertEqual(result['status'],'needs_review')
            self.assertEqual(len(studio_calls),1);self.assertEqual(studio_calls[0][0]['kacheln'],1);self.assertEqual(len(studio_calls[0][1]['scenes']),1);self.assertEqual(engine.checked_count,1);self.assertEqual(len(downloads),1)
            out=store.directory(job['id']);self.assertEqual((out/'panels/01_art.png').read_bytes(),original['panels/01_art.png']);self.assertEqual((out/'panels/01_panel.png').read_bytes(),original['panels/01_panel.png']);self.assertEqual((out/'panels/02_art.png').read_bytes(),generated)
            source=json.loads((out/'editorial-source.json').read_text());old=json.loads(original['editorial-source.json'])
            self.assertEqual(source['scenes'][0],old['scenes'][0]);self.assertEqual(source['scenes'][1]['bubbles'],old['scenes'][1]['bubbles']);self.assertEqual(source['scenes'][1]['dialog'],old['scenes'][1]['dialog']);self.assertEqual(source['article'],old['article'])
            self.assertEqual(source['scenes'][1]['character_states']['b'*32],'Kinnlanger Bob.');self.assertTrue((out/'comic.pdf').exists());self.assertTrue((out/'comic-bundle.zip').exists())
            self.assertEqual(original,{str(p.relative_to(store.directory(parent['id']))):p.read_bytes() for p in store.directory(parent['id']).rglob('*') if p.is_file()})

    def test_single_panel_graph_keeps_full_job_request_unchanged(self):
        with tempfile.TemporaryDirectory() as root:
            store,parent=setup(root);calls=[]
            class Client:
                def run(self,job,step,graph,workflow):
                    calls.append(graph)
                    node=next(k for k,v in graph.items() if v['class_type']=='DGXComicStudio')
                    return {node:{'comic_panels':[]}}
            template=Path(__file__).resolve().parents[1]/'examples/comics/workflows/04_Comic_Automat_9B.json'
            engine=Engine(store,Client(),template,'unused','unused')
            source=json.loads((store.directory(parent['id'])/'editorial-source.json').read_text())
            engine.studio(parent['id'],'test',{'title':'Die Tür','story':source['article']},source['characters'],{'scenes':[source['scenes'][1]]},{'0':1},request_override={**parent['request'],'kacheln':1})
            fields=calls[0][engine.node]['inputs'];self.assertEqual(fields['anzahl_kacheln'],1)
            self.assertEqual(len(json.loads(fields['bearbeiteter_plan'])['scenes']),1)
            self.assertEqual(store.get(parent['id'])['request']['kacheln'],2)

    def test_invalid_requests_and_duplicate_work_do_not_start_other_panels(self):
        with tempfile.TemporaryDirectory() as root:
            store,parent=setup(root);info=manifest(store,parent);value={'version':info['version'],'panel':1,'correction':'Haare kürzer bei Ria.'}
            for change in ({'panel':2},{'correction':''},{'correction':'Bild 1 ändern'},{'style':'Manga'},{'version':'veraltet'}):
                with self.subTest(change=change),self.assertRaises(ValueError):panel_correction.enqueue(store,parent,{**value,**change})
            self.assertEqual(len(store.list()),1)
            job=panel_correction.enqueue(store,parent,value)
            with self.assertRaises(Conflict):panel_correction.enqueue(store,parent,value)
            self.assertTrue(store.get(job['id'])['panel_correction_mode']);self.assertEqual(store.get(job['id'])['corrected_panel'],2)
