"""Bewertung verbessert dieselbe Ausgabe; Stil darf wechseln, Anzahl und Identitäten bleiben fest."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'automation/comics'))
from storage import Store
from stories import Stories,Conflict
from engine import Engine,validate_request
from improvement import revise,remove_duplicates
from feedback import CRITERIA,validate_feedback


class FakeEngine:
    validate_scenes=Engine.validate_scenes
    def __init__(self,store):self.store=store
    def json_call(self,job,step,prompt,validator,**kwargs):
        return validator({'changes':[{'panel':2,'story':'Anna hält den getrennten Zopf. Sichtbarer kurzer Bob.','character_states':{'a'*32:'Kinnlanger Bob, Gesicht wie in der Referenz.'},'reason':'Der abgeschnittene Zopf muss sichtbar getrennt sein.'}]})
    def preflight(self,*args):return {'valid':True,'issues':[]}


class ImprovementTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.store=Store(self.temp.name);self.stories=Stories(self.store)
        self.parent=uuid.uuid4().hex
        req=validate_request({'kacheln':2,'stil':'Warme Alltagsillustration','seed':42,'max_korrekturrunden':0})
        self.store.create(self.parent,req,initial_status='editing')
        self.source={'title':'HG1','article':'Anna sagt: „Hallo!“ Ein Zopf wird abgeschnitten.','style':req['stil'],'seed':42,
            'characters':[{'id':'a'*32,'name':'Anna','aliases':[],'description':'Gleiches Gesicht.','outfit':'Umhang','references':[]}],
            'scenes':[{'story':'Anna sitzt im Stuhl.','dialog':'Hallo!','characters':['a'*32],'bubbles':[{'speaker':'a'*32,'text':'Hallo!'}]},
                      {'story':'Anna steht auf.','dialog':'Der Schnitt ist fertig.','characters':['a'*32],'bubbles':[]}]}
        self.store.write(self.parent,'editorial-source.json',self.source);self.store.write(self.parent,'characters.json',self.source['characters']);self.store.write(self.parent,'story.json',{'title':'HG1','story':self.source['article']})
        self.store.stage(self.parent,'finished',status='needs_review')
        self.store.save_feedback(self.parent,{'bewertungen':{k:3 for k in CRITERIA},'kommentar':'Bild 2: der abgeschnittene Zopf muss getrennt sein.'})

    def test_same_story_fixed_count_reference_and_original_untouched(self):
        before=(self.store.directory(self.parent)/'editorial-source.json').read_bytes()
        job=self.stories.improve(self.parent,'Warme Alltagsillustration')
        snapshot=json.loads((self.store.directory(job['id'])/'improvement-input.json').read_text())
        source,report=revise(FakeEngine(self.store),job['id'],snapshot)
        self.assertEqual(source['article'],self.source['article']);self.assertEqual(source['title'],'HG1')
        self.assertEqual(source['characters'],self.source['characters']);self.assertEqual(len(source['scenes']),2)
        self.assertEqual(source['scenes'][0]['dialog'],'');self.assertEqual(source['scenes'][0]['bubbles'],self.source['scenes'][0]['bubbles'])
        self.assertEqual(report['retained_art_panels'],[1]);self.assertEqual(report['rerendered_panels'],[2]);self.assertEqual(report['duplicate_captions_removed'],[1])
        self.assertEqual((self.store.directory(self.parent)/'editorial-source.json').read_bytes(),before)
        with self.assertRaises(Conflict):self.stories.delete_job(self.parent)
        with self.assertRaises(Conflict):self.stories.improve(self.parent)

    def test_style_override_regenerates_all_without_count_override(self):
        job=self.stories.improve(self.parent,'Holzschnitt / Linolschnitt');self.assertEqual(job['request']['kacheln'],2)
        self.assertEqual(job['request']['stil'],'Holzschnitt / Linolschnitt')
        snapshot=json.loads((self.store.directory(job['id'])/'improvement-input.json').read_text())
        _,report=revise(FakeEngine(self.store),job['id'],snapshot)
        self.assertEqual(report['rerendered_panels'],[1,2]);self.assertEqual(report['retained_art_panels'],[])

    def test_comment_only_can_be_saved_used_and_aggregated_without_zero_scores(self):
        value=validate_feedback({'kommentar':'Nur die Sprechblasen korrigieren.'})
        self.store.save_feedback(self.parent,value)
        prefs=self.store.preferences()
        self.assertEqual(prefs['average_ratings'],{})
        self.assertEqual(prefs['rated_examples'][0]['kommentar'],value['kommentar'])
        job=self.stories.improve(self.parent)
        snapshot=json.loads((self.store.directory(job['id'])/'improvement-input.json').read_text())
        self.assertEqual(snapshot['feedback']['bewertungen'],{})
        self.assertEqual(snapshot['feedback']['kommentar'],value['kommentar'])
        self.store.save_feedback(self.parent,validate_feedback({'bewertungen':{'figuren':4}}))
        self.assertEqual(self.store.preferences()['average_ratings'],{'figuren':4.0})
        with self.assertRaises(ValueError):validate_feedback({'kommentar':'   '})

    def test_missing_feedback_is_rejected(self):
        with self.store.connect() as db:
            d=self.store.get(self.parent);d.pop('feedback');db.execute('UPDATE jobs SET doc=? WHERE id=?',(json.dumps(d),self.parent))
        with self.assertRaisesRegex(ValueError,'Bewertung'):self.stories.improve(self.parent)

    def test_semantic_caption_is_not_removed_just_because_a_word_repeats(self):
        source=copy.deepcopy(self.source);source['scenes'][0]['dialog']='Anna sagt freundlich Hallo.'
        self.assertEqual(remove_duplicates(source),[])


if __name__=='__main__':unittest.main()
