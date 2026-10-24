"""Schwerter im tatsächlichen Bild prüfen, Verwechslungen bestätigen und Befunde erhalten."""
import copy
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
from equipment_review import audit,observations
from test_comic_lettering import fixture
import lettering,sharing,books

class EquipmentReviewTests(unittest.TestCase):
    def test_excess_needs_confirmation_and_blocks_sharing_not_the_comic(self):
        with tempfile.TemporaryDirectory() as root:
            store,job=fixture(root);data,_=lettering.source(store,job);cast=copy.deepcopy(data['characters']);cast[0]['outfit']='Ein Schwert am Gürtel.';calls=[]
            class Fake:
                def __init__(self):self.store=store
                def json_call(self,job,step,prompt,validator,images,tokens):
                    calls.append((step,images));return validator({'observations':[{'character':cast[0]['id'],'swords':2,'evidence':'Eine Klinge in der Hand und ein weiterer Griff am Gürtel.'}]})
            result=audit(Fake(),job['id'],cast,data['scenes']);self.assertEqual(result['status'],'failed');self.assertEqual(len(result['issues']),2)
            self.assertEqual(len(calls),4);self.assertTrue(all(images for _,images in calls));job=store.get(job['id'])
            with self.assertRaisesRegex(ValueError,'Schwerter'):sharing.image_sources(job)
            with self.assertRaisesRegex(Exception,'Schwerter'):books.source(store,job)
            info=lettering.manifest(store,job);child=lettering.enqueue(store,job,{'version':info['version'],'panels':[{k:v for k,v in p.items() if k!='story'} for p in info['panels']]})
            self.assertTrue(child['equipment_unresolved']);self.assertTrue((store.directory(child['id'])/'equipment-report.json').exists())
            self.assertEqual(lettering.render(store,child['id'])['status'],'needs_review')

    def test_empty_scabbard_and_uncertain_count_are_not_false_extra_swords(self):
        with tempfile.TemporaryDirectory() as root:
            store,job=fixture(root);data,_=lettering.source(store,job);cast=data['characters'];cast[0]['outfit']='Ein einziges Schwert am Gürtel.'
            class Fake:
                def __init__(self):self.store=store
                def json_call(self,job,step,prompt,validator,images,tokens):
                    return validator({'observations':[{'character':cast[0]['id'],'swords':1 if step.endswith('1') else None,'evidence':'Eine Klinge, die Scheide ist leer; im zweiten Bild teilweise verdeckt.'}]})
            result=audit(Fake(),job['id'],cast,data['scenes']);self.assertEqual(result['status'],'uncertain');self.assertFalse(result['issues']);self.assertFalse(store.get(job['id'])['equipment_unresolved'])
            result=observations({'observations':[{'character':'a','swords':None,'evidence':'Verdeckt.'}]},{'a':{}});self.assertIsNone(result['a']['swords'])
            with self.assertRaises(ValueError):observations({'observations':[{'character':'a','swords':True,'evidence':'Falsch.'}]},{'a':{}})
            counted=observations([{'observations':[{'character':'a','swords':[{'location':'rechte Hand','evidence':'Gezogene Klinge.'},{'location':'Gürtel','evidence':'Zusätzlicher Griff in Scheide.'}],'evidence':'Zwei getrennte Waffen.'}]}],{'a':{}})
            self.assertEqual(counted['a']['swords'],2)

    def test_old_uncertainty_messages_become_one_notice_without_changing_report(self):
        from equipment_review import presentation,REVIEW_NOTE
        job={'equipment_review_status':'uncertain','equipment_warnings':[f'Kachel {i}: Schwertanzahl nicht eindeutig; bitte das Bild prüfen.' for i in range(1,7)],'warnings':['Storyboard bitte prüfen.']}
        original=copy.deepcopy(job);display=presentation(job)
        self.assertEqual(job,original);self.assertEqual(display['equipment_warnings'],[])
        self.assertEqual(display['equipment_review_note'],REVIEW_NOTE);self.assertEqual(len(display['warnings']),2)
        mixed={**job,'equipment_review_status':'failed','equipment_warnings':['Kachel 1: Hildebrand zeigt 2 Schwerter statt eines.',*job['equipment_warnings']]}
        self.assertEqual(presentation(mixed)['equipment_warnings'],['Kachel 1: Hildebrand zeigt 2 Schwerter statt eines.'])
        with self.assertRaisesRegex(ValueError,'Widersprüchlicher'):
            observations({'observations':[{'character':'a','swords':0,'evidence':'Die Klinge ist sichtbar, aber der Griff verdeckt.'}]},{'a':{}})
        with self.assertRaisesRegex(ValueError,'Widersprüchlicher'):
            observations({'observations':[{'character':'a','swords':None,'evidence':'Das ergibt insgesamt zwei physische Schwerter.'}]},{'a':{}})

    def test_zero_visible_swords_is_not_a_false_inventory_warning(self):
        with tempfile.TemporaryDirectory() as root:
            store,job=fixture(root);data,_=lettering.source(store,job);cast=data['characters'];cast[0]['outfit']='Ein Schwert am Gürtel.'
            class Fake:
                def __init__(self):self.store=store
                def json_call(self,job,step,prompt,validator,images,tokens):
                    self_outer.assertIn('GANZE ZAHL',prompt)
                    return validator({'observations':[{'character':cast[0]['id'],'swords':0,'evidence':'Hüfte und Hände liegen außerhalb des Bildes.'}]})
            self_outer=self;result=audit(Fake(),job['id'],cast,data['scenes'])
            self.assertEqual(result['status'],'checked');self.assertFalse(result['warnings']);self.assertFalse(result['issues'])

    def test_unconfirmed_first_count_does_not_block_and_failure_is_visible(self):
        with tempfile.TemporaryDirectory() as root:
            store,job=fixture(root);data,_=lettering.source(store,job);cast=data['characters'];cast[0]['outfit']='Ein Schwert am Gürtel.'
            class Fake:
                def __init__(self):self.store=store
                def json_call(self,job,step,prompt,validator,images,tokens):
                    if step.endswith('2'):raise RuntimeError('Test: Modell nicht erreichbar')
                    return validator({'observations':[{'character':cast[0]['id'],'swords':1 if 'confirm' in step else 2,'evidence':'Bei erneuter Prüfung ist die Scheide leer.'}]})
            result=audit(Fake(),job['id'],cast,data['scenes']);self.assertEqual(result['status'],'uncertain');self.assertEqual(len(result['warnings']),1);self.assertEqual(len(result['notes']),2);self.assertFalse(result['issues'])
