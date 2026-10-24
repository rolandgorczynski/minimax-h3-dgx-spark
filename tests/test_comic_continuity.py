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

    def test_drawing_a_single_sword_empties_scabbard_until_resheathed(self):
        from continuity import EQUIPMENT,state_text
        cast=copy.deepcopy(CAST);cast[0]['outfit']='Ein schweres Schwert hängt an seinem Gürtel.'
        source='Hildebrand zieht sein Schwert. Alebrand spricht. Hildebrand steckt sein Schwert in die Scheide.'
        scenes=[scene('Zieht.'),scene('Antwortet.'),scene('Steckt ein.')]
        initial=EQUIPMENT.initial(cast);self.assertEqual(initial[H]['sword_position'],'in der Scheide')
        _,states,final=track({'events':[event(1,'sword_position','gezogen','zieht sein Schwert'),event(3,'sword_position','in der Scheide','steckt sein Schwert in die Scheide')]},scenes,cast,0,source,initial)
        self.assertEqual([s[H]['sword_position'] for s in states],['gezogen','gezogen','in der Scheide'])
        self.assertIn('leer',state_text(states[1][H]));self.assertIn('ohne zweiten Schwertgriff',state_text(states[1][H]))
        self.assertIn('Kein zusätzliches Schwert in den Händen',state_text(final[H]))
        self.assertIn('NO SECOND HILT',EQUIPMENT.instruction(cast[0]))
        for outfit in ('Zwei Schwerter hängen am Gürtel.','Kein Schwert.','Mantel.','Ein Schild und zwei Schwerter.'):
            self.assertFalse(EQUIPMENT.single_sword({'outfit':outfit}),outfit)
        with self.assertRaisesRegex(ValueError,'Quellenbeleg'):
            track({'events':[event(2,'sword_position','in der Scheide','Alebrand spricht')]},scenes,cast,0,source,initial)
        with self.assertRaisesRegex(ValueError,'Schwertzustand'):
            track({'events':[event(1,'sword_position','in der Hand und Scheide','zieht sein Schwert')]},scenes,cast,0,source,initial)

    def test_sword_state_is_written_explicitly_into_every_image_description(self):
        from continuity import EQUIPMENT
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);store.create('c'*32,validate_request({'kacheln':2}));cast=copy.deepcopy(CAST);cast[0]['outfit']='Ein Schwert am Gürtel.'
            class Fake:
                validate_scenes=Engine.validate_scenes
                def __init__(self):self.store=store
                def json_call(self,job,step,prompt,validator,tokens):
                    if '-events-' in step:return validator({'events':[event(1,'sword_position','gezogen','Hildebrand zieht sein Schwert')]})
                    if '-review-' in step:return validator({'issues':[]})
                    return validator([{'panel':1,'story':'Hildebrand hält sein einziges gezogenes Schwert. Seine Scheide ist leer.'},{'panel':2,'story':'Hildebrand spricht und hält dasselbe Schwert, die Scheide bleibt leer.'}])
            fixed,report=enforce(Fake(),'c'*32,[scene('Zieht.'),scene('Spricht.')],cast,'Hildebrand zieht sein Schwert. Er spricht.')
            for panel in fixed:
                self.assertEqual(panel['continuity_state'][H]['sword_position'],'gezogen')
                self.assertIn('ohne zweiten Schwertgriff',panel['story'])
                self.assertIn('ohne zweiten Schwertgriff',panel['character_states'][H])
            self.assertEqual(report['final_state'][H]['sword_position'],'gezogen')

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
