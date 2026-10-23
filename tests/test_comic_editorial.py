"""An authored article and scene plan go directly to workflow 04, without an LLM."""
import json
import base64
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from storage import Store
from editorial import render,finalize
from test_comic_automation import FakeComfy,TEMPLATE


class EditorialTests(unittest.TestCase):
    def test_locked_storyboard_export_and_editing_does_not_enter_worker_queue(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);ident=uuid.uuid4().hex;client=FakeComfy(ident)
            original=client.run;render_steps=[]
            def run(job,step,graph,workflow=None):
                if step.startswith('editor-render-'):
                    render_steps.append(step);return original(job,'render-0',graph,workflow)
                return original(job,step,graph,workflow)
            client.run=run;client.cleanup=lambda job:client.calls.append(('cleanup',job))
            cast=[{'id':uuid.uuid4().hex,'name':name,'description':'Kurzes braunes Haar, erwachsene Person.','outfit':'Graue Jacke.','aliases':[],'variants':{},'references':[]} for name in ['Anna','Bram']]
            scenes=[{'story':c['name']+' steht am Fenster.','dialog':'Ein ruhiger Morgen.','characters':[c['id']],'bubbles':[]} for c in cast]
            cast.append({'id':uuid.uuid4().hex,'name':'Unbenutzt','description':'Kurzes Haar.','outfit':'Jacke.','aliases':[],'variants':{},'references':[]})
            payload={'title':'Ein fester Plan','article':'Ein Artikel. Sein Wortlaut bleibt exakt erhalten.','seed':42,'characters':cast,'scenes':scenes}
            render(store,client,TEMPLATE,payload,ident)
            self.assertEqual(sum(step.startswith('portrait-') for _,step in client.calls),2,'Keine Porträts für unbenutzte Figuren rendern')
            self.assertIsNone(store.claim());store.recover();self.assertEqual(store.get(ident)['status'],'editing')
            self.assertEqual(json.loads((store.directory(ident)/'story.json').read_text())['story'],payload['article'])
            self.assertEqual(json.loads((store.directory(ident)/'scenes.json').read_text())['scenes'],scenes)
            self.assertFalse(any(step in ('story-prose','character-draft','scene-plan','self-reflection') for _,step in client.calls))
            reference=base64.b64encode(b'\x89PNG\r\n\x1a\nreference-for-test').decode()
            payload['reference_overrides']={cast[0]['id']:[reference]}
            render(store,client,TEMPLATE,payload,ident)
            self.assertNotEqual(render_steps[0],render_steps[1],'A changed reference must not return an old full-comic checkpoint')
            saved_cast=json.loads((store.directory(ident)/'characters.json').read_text())
            self.assertEqual(saved_cast[0]['inline_references'],[reference])
            finalize(store,client,ident,'Kacheln redaktionell geprüft.')
            self.assertEqual(store.get(ident)['status'],'completed')
            self.assertEqual(client.calls[-1],('cleanup',ident))
            self.assertIn('workflow.json',{a['name'] for a in store.get(ident)['artifacts']})
            with self.assertRaises(ValueError):render(store,client,TEMPLATE,payload,ident)
