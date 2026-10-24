"""Physische Zustände müssen ohne expliziten Übergang weitergelten."""
import copy,json
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
from continuity import enforce,track
from engine import Engine,validate_request
from storage import Store

H='a'*32;A='b'*32
CAST=[{'id':H,'name':'Hildebrand','description':'Älterer Krieger.','outfit':'Brauner Mantel.'},{'id':A,'name':'Alebrand','description':'Junger Krieger.','outfit':'Grauer Mantel.'}]
SOURCE='Hildebrand kommt angeritten. Alebrand spricht mit Hildebrand. Hildebrand antwortet. Dann steigt Hildebrand vom Pferd ab.'

def scene(text,visible=None):return {'story':text,'dialog':'Ein festgeschriebener Text.','characters':visible if visible is not None else [H,A],'bubbles':[{'speaker':A,'text':'Wer bist du?'}]}

def event(panel,field,value,evidence):return {'panel':panel,'character':H,'field':field,'value':value,'evidence':evidence}

class ContinuityTests(unittest.TestCase):
    def test_state_persists_without_dismount_even_while_offscreen(self):
        scenes=[scene('Hildebrand reitet an.'),scene('Alebrand spricht.',[A]),scene('Hildebrand steht plötzlich am Boden.')]
        events,states,final=track({'events':[event(1,'movement','beritten','kommt angeritten')]},scenes,CAST,0,SOURCE,{})
        self.assertEqual([s[H]['movement'] for s in states],['beritten']*3)
        self.assertEqual(states[1][H]['movement'],'beritten')
        with self.assertRaisesRegex(ValueError,'kein Absteigen'):track({'events':[event(2,'movement','zu Fuß','Alebrand spricht mit Hildebrand')]},scenes,CAST,0,SOURCE,{H:{'movement':'beritten'}})
        with self.assertRaisesRegex(ValueError,'wörtlich'):track({'events':[event(2,'movement','zu Fuß','Hildebrand steigt ab.')]},scenes,CAST,0,SOURCE,{})
        with self.assertRaisesRegex(ValueError,'wörtlich'):track({'events':[event(2,'movement','zu Fuß','steigt Hildebrand vom Pferd ab')]},scenes,CAST,0,SOURCE,{},['kommt angeritten','Alebrand spricht mit Hildebrand','Hildebrand antwortet'])

    def test_explicit_dismount_changes_only_that_panel_and_later(self):
        scenes=[scene('Reitet.'),scene('Spricht.'),scene('Steigt ab.')]
        _,states,final=track({'events':[event(1,'movement','beritten','kommt angeritten'),event(3,'movement','zu Fuß','steigt Hildebrand vom Pferd ab')]},scenes,CAST,0,SOURCE,{})
        self.assertEqual([s[H]['movement'] for s in states],['beritten','beritten','zu Fuß'])
        self.assertEqual(final[H]['movement'],'zu Fuß')

    def test_rewrite_preserves_words_profiles_and_cross_batch_state(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);store.create('c'*32,validate_request({'kacheln':7}));scenes=[scene('Hildebrand steht neben seinem Pferd.') for _ in range(7)];before=copy.deepcopy(scenes);calls=[]
            class Fake:
                validate_scenes=Engine.validate_scenes
                def __init__(self):self.store=store
                def json_call(self,job,step,prompt,validator,tokens):
                    calls.append(step)
                    if '-events-' in step:return validator({'events':[event(1,'movement','beritten','kommt angeritten'),event(2,'movement','zu Fuß','Alebrand spricht mit Hildebrand')]} if step.endswith('-1') else {'events':[]})
                    if '-review-' in step:return validator({'issues':[]})
                    panels=json.loads(prompt.split('KACHELN:')[1])
                    return validator([{'panel':p['panel'],'story':'Hildebrand bleibt im Sattel seines Pferdes. Alebrand steht auf dem Boden und blickt zu ihm hinauf.'} for p in panels])
            fixed,report=enforce(Fake(),'c'*32,scenes,CAST,SOURCE)
            self.assertEqual(scenes,before);self.assertEqual(report['checked_panels'],7);self.assertEqual(len(report['discarded_unproven_events']),1)
            self.assertIn('script-continuity-events-7',calls)
            for a,b in zip(before,fixed):
                self.assertEqual(a['dialog'],b['dialog']);self.assertEqual(a['bubbles'],b['bubbles']);self.assertEqual(a['characters'],b['characters']);self.assertIn('beritten',b['character_states'][H]);self.assertIn('Sattel',b['story']);self.assertIn('Hildebrand: Fortbewegung: beritten',b['story'])
            self.assertEqual(fixed[-1]['continuity_state'][H]['movement'],'beritten')

    def test_unresolved_contradiction_stops_before_any_render(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);store.create('c'*32,validate_request({'kacheln':1}))
            class Fake:
                validate_scenes=Engine.validate_scenes
                def __init__(self):self.store=store
                def json_call(self,job,step,prompt,validator,tokens):
                    if '-events-' in step:return validator({'events':[event(1,'movement','beritten','kommt angeritten')]})
                    if '-review-' in step:return validator({'issues':[{'panel':1,'character':H,'field':'movement','quote':'steht neben seinem Pferd','message':'Er müsste weiterhin im Sattel sitzen.'}]})
                    return validator([{'panel':1,'story':'Hildebrand steht neben seinem Pferd.'}])
            with self.assertRaisesRegex(ValueError,'Skript-Kontinuität'):enforce(Fake(),'c'*32,[scene('Hildebrand steht neben seinem Pferd.')],CAST,SOURCE)
            self.assertEqual(json.loads((store.directory('c'*32)/'continuity-report.json').read_text())['status'],'failed')

if __name__=='__main__':unittest.main()
