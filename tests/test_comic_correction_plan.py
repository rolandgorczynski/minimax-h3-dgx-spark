"""Präzisieren erzeugt nur einen prüfbaren Text, kein neues Comicbild."""
import json
import tempfile
import unittest
from test_comic_panel_correction import setup
from engine import Engine
from lettering import manifest
import panel_correction
from stories import Conflict

class CorrectionPlanTests(unittest.TestCase):
    def test_short_wish_produces_only_reviewable_text_and_keeps_original(self):
        with tempfile.TemporaryDirectory() as root:
            store,parent=setup(root);info=manifest(store,parent);path=store.directory(parent['id']);before={str(p.relative_to(path)):p.read_bytes() for p in path.rglob('*') if p.is_file()}
            value={'version':info['version'],'panel':0,'correction':'Ria muss hinter geschlossenen Gitterstäben sitzen.'}
            job=panel_correction.enqueue_plan(store,parent,value)
            self.assertNotIn(job['id'],[j['id'] for j in store.list(public_only=True)])
            self.assertIn(parent['id'],[j['id'] for j in store.list(public_only=True)])
            with self.assertRaises(Conflict):panel_correction.enqueue_plan(store,parent,value)
            class FakeEngine:
                validate_scenes=Engine.validate_scenes
                def __init__(self):self.store=store
                def json_call(self,ident,step,prompt,validator,images,tokens):
                    assert step=='panel-correction-instruction';assert images[0]==before['panels/01_art.png']
                    assert 'innen/außen' in prompt and 'Erhaltungsregeln' in prompt
                    return validator({'story':'Ria sitzt vollständig im verschlossenen Käfig. Stäbe vor dem Körper. Kamera unverändert.','character_states':{}})
                def studio(self,*args,**kwargs):raise AssertionError('Keine Bilder erzeugen.')
            result=panel_correction.run_plan(FakeEngine(),job['id']);self.assertEqual(result['status'],'completed')
            self.assertIn('Stäbe vor',store.get(job['id'])['correction_plan']['story'])
            self.assertEqual(before,{str(p.relative_to(path)):p.read_bytes() for p in path.rglob('*') if p.is_file()})
            self.assertFalse((store.directory(job['id'])/'panels').exists())

    def test_known_separate_sections_are_kept_in_full_and_unknown_fields_rejected(self):
        scene={'story':'Ria an der Tür.','characters':['b'*32],'bubbles':[],'dialog':''};cast=[{'id':'b'*32,'name':'Ria'}]
        value={'story':'Ria sitzt im Käfig.','character_states':{},'Zwingende Bildkomposition':'Stäbe vor Gesicht und Körper.','Kamera':'Totale.','Ausschlüsse':'Keine zweite Ria.','Beibehalten':'Farben und Kleidung.'}
        original=json.loads(json.dumps(value))
        result=panel_correction.validate_instruction(value,scene,cast,Engine)
        for key in ('Zwingende Bildkomposition','Kamera','Ausschlüsse','Beibehalten'):self.assertIn(key+': '+value[key],result['story'])
        self.assertEqual(value,original)
        with self.assertRaises(ValueError):panel_correction.validate_instruction({**value,'Andere Geschichte':'Nein'},scene,cast,Engine)
