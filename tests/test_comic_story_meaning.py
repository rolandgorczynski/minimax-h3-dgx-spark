"""Pointe, feste Kachelzahl, Quellenbindung und Schlussprüfung ohne echte Modelle."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
import story_meaning as meaning
from storage import Store

PLAN={'central_question':'Was kostet ein gebrochenes Versprechen?','meaning_type':'Lehre','evidence':[{'event':'Die Stadt zahlt nicht.','meaning':'Ein Vertrauensbruch kann größere Verluste auslösen.'}],'core':'Der gebrochene Handel kostet mehr als die Bezahlung.','causal_chain':['Die Stadt braucht Hilfe.','Der Rattenfänger entfernt die Ratten.','Die Stadt verweigert die Bezahlung.','Der Rattenfänger führt die Kinder fort.'],'ending':'Die Stadt verliert ihre Kinder.','recommended_count':8,'reason':'Vier Ursachen und Folgen benötigen Aufbau und Konsequenz.','series_reason':'Zwei Folgen können Hilfe und Konsequenz als zusammenhängenden Lernbogen zeigen.'}

class Fake:
    def __init__(self,store):self.store=store;self.calls=[];self.approved=True
    def json_call(self,job,step,prompt,validator,tokens):
        step=step.replace('-v4','')
        self.calls.append((step,prompt))
        return validator(copy.deepcopy(PLAN) if step=='story-meaning' else {'approved':True,'issues':[]} if 'source-' in step else {'approved':self.approved,'issues':[] if self.approved else ['Die verweigerte Bezahlung fehlt.']})
    def require_german(self,job,step,value,validator,tokens):return validator(value)

class MeaningTests(unittest.TestCase):
    def test_fixed_count_and_original_preserved_and_cache_bound_to_text(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);job=meaning.enqueue(store,{'text':'Die Stadt verweigert die Bezahlung.','count':3});engine=Fake(store)
            result=meaning.plan(engine,job['id'],'Die Stadt verweigert die Bezahlung.',3)
            self.assertEqual(result['fixed_count'],3);self.assertEqual(result['recommended_count'],8)
            self.assertEqual(store.get(job['id'])['request']['kacheln'],3)
            self.assertEqual(result['panels_per_episode'],6)
            meaning.plan(engine,job['id'],'Die Stadt verweigert die Bezahlung.',3,cached=result)
            self.assertEqual(len(engine.calls),2)
            meaning.plan(engine,job['id'],'Anderer Text.',3,cached=result)
            self.assertEqual(len(engine.calls),4)
            self.assertIn('keine Moral',engine.calls[0][1]);self.assertIn('nicht automatisch gerechtfertigt',engine.calls[0][1])

    def test_loss_of_pointe_blocks_success_and_keeps_report(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);job=meaning.enqueue(store,{'text':'Ratten, Handel, Vertragsbruch, Kinder.','count':6});engine=Fake(store);engine.approved=False
            with self.assertRaisesRegex(ValueError,'verweigerte Bezahlung'):
                meaning.review(engine,job['id'],'Ratten, Handel, Vertragsbruch, Kinder.',PLAN,[{'story':'Ratten verschwinden.'}])
            report=json.loads((store.directory(job['id'])/'narrative-review.json').read_text());self.assertFalse(report['approved'])

    def test_invalid_recommendation_or_series_is_rejected(self):
        for key,value in [('recommended_count',True),('recommended_count',0),('recommended_count',121),('series_reason',''),('causal_chain',[]),('core','')]:
            invalid={**PLAN,key:value}
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):meaning.validate(invalid)

    def test_analysis_only_job_never_requests_images(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);job=meaning.enqueue(store,{'text':'Die Stadt bricht den Handel.','count':12})
            engine=Fake(store);result=meaning.run(engine,job['id'])
            self.assertTrue(job['narrative_mode']);self.assertEqual(result['artifacts'],[])
            self.assertEqual([step for step,prompt in engine.calls],['story-meaning','story-meaning-source-review'])
            self.assertEqual(result['narrative_plan']['fixed_count'],12)

class GroundingTests(unittest.TestCase):
    def test_unproven_details_are_revised_before_caching(self):
        class Revising(Fake):
            def json_call(self,job,step,prompt,validator,tokens):
                step=step.replace('-v4','')
                self.calls.append((step,prompt))
                if step=='story-meaning-source-review':return validator({'approved':False,'issues':['Ein zusätzliches Motiv ist nicht belegt.']})
                if step=='story-meaning-source-final-review':return validator({'approved':True,'issues':[]})
                return validator(copy.deepcopy(PLAN))
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);job=meaning.enqueue(store,{'text':'Der Handel wird gebrochen.'});engine=Revising(store)
            result=meaning.plan(engine,job['id'],'Der Handel wird gebrochen.',12)
            self.assertEqual(result['analysis_version'],meaning.ANALYSIS_VERSION)
            self.assertTrue((store.directory(job['id'])/'narrative-source-first-review.json').exists())
            self.assertEqual([s for s,p in engine.calls],['story-meaning','story-meaning-source-review','story-meaning-source-revision','story-meaning-source-final-review'])
            self.assertIsNotNone(meaning.cached_plan(store,'Der Handel wird gebrochen.'))

    def test_unresolved_source_error_is_not_cached(self):
        class Rejecting(Fake):
            def json_call(self,job,step,prompt,validator,tokens):
                step=step.replace('-v4','')
                if 'review' in step:return validator({'approved':False,'issues':['Der Schluss wird erfunden.']})
                return validator(copy.deepcopy(PLAN))
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);job=meaning.enqueue(store,{'text':'Offener Schluss.'})
            with self.assertRaisesRegex(ValueError,'Schluss wird erfunden'):
                meaning.plan(Rejecting(store),job['id'],'Offener Schluss.',12)
            self.assertIsNone(meaning.cached_plan(store,'Offener Schluss.'))


class LibraryMeaningTests(unittest.TestCase):
    def setup_library(self,store):
        from source_generator import BUILTINS
        from stories import Stories
        source=copy.deepcopy(BUILTINS[0]);source['text']='Ein Handel wird gebrochen.'
        store.integration_set('source-catalog',[source]);stories=Stories(store)
        story=stories.save({'name':'Probe','mode':'editorial','payload':{'style':'Klassischer Comic','article':'Eine Stadt verliert die Kinder.','panel_count':4,'scenes':[]}})
        return stories,source,story

    def test_restart_cache_new_entries_and_changed_text(self):
        from stories import Stories
        from source_generator import catalog,save_source
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);stories,source,story=self.setup_library(store);engine=Fake(store)
            meaning.configure_library(store,stories,{'action':'start'})
            self.assertEqual(meaning.library_status(store,stories)['pending'],2)
            self.assertTrue(meaning.process_library_next(engine,stories))
            self.assertEqual(meaning.library_status(store,stories)['completed'],1)
            self.assertIn('narrative_plan',catalog(store)[0])
            self.assertEqual(store.integration_get('source-catalog'),[source])
            # Neustart: vorhandenen Cache fortsetzen, keine Analyse wiederholen.
            store=Store(root);stories=Stories(store);engine=Fake(store)
            self.assertTrue(meaning.process_library_next(engine,stories))
            self.assertEqual(meaning.library_status(store,stories)['completed'],2)
            self.assertFalse(meaning.process_library_next(engine,stories))
            self.assertEqual(stories.get(story['id'],with_meaning=False),story)
            self.assertIn('narrative_plan',stories.get(story['id'])['payload'])
            self.assertEqual(stories.get(story['id'])['version'],1)
            save_source(store,{**source,'text':'Geänderter Handel mit anderem Schluss.'})
            self.assertNotIn('narrative_plan',catalog(store)[0])
            self.assertEqual(meaning.library_status(store,stories)['pending'],1)
            self.assertTrue(meaning.process_library_next(engine,stories))
            self.assertEqual(meaning.library_status(store,stories)['pending'],0)
            self.assertEqual(len(engine.calls),4)

    def test_pause_and_individual_failure_do_not_destroy_progress(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);stories,source,story=self.setup_library(store);engine=Fake(store)
            meaning.configure_library(store,stories,{'action':'start'})
            engine.json_call=lambda *args,**kwargs:(_ for _ in ()).throw(ValueError('Ungültige Antwort.'))
            self.assertTrue(meaning.process_library_next(engine,stories))
            self.assertEqual(meaning.library_status(store,stories)['failed'],1)
            meaning.configure_library(store,stories,{'action':'pause'})
            self.assertFalse(meaning.process_library_next(engine,stories))
            meaning.configure_library(store,stories,{'action':'start'})
            self.assertTrue(meaning.process_library_next(Fake(store),stories))
            self.assertEqual(meaning.library_status(store,stories)['failed'],0)
            self.assertEqual(meaning.library_status(store,stories)['completed'],1)

    def test_editorial_import_checks_text_evidence_and_preserves_story(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);stories,source,story=self.setup_library(store)
            entry={'kind':'source','id':source['id'],'source_sha256':meaning.fingerprint(source['text']+'\n'),'plan':{**copy.deepcopy(PLAN),'evidence':[{'event':'Ein Handel wird gebrochen.','meaning':'Vertrauen wird verletzt.'}]}}
            bad=copy.deepcopy(entry);bad['source_sha256']='falsch'
            with self.assertRaisesRegex(ValueError,'Textgrundlage'):meaning.import_curated(store,stories,{'entries':[entry,bad]})
            self.assertEqual(meaning.current_cache(store),{})
            bad=copy.deepcopy(entry);bad['plan']['evidence'][0]['event']='Erfundene Handlung.'
            with self.assertRaisesRegex(ValueError,'Textausschnitt'):meaning.import_curated(store,stories,{'entries':[bad]})
            result=meaning.import_curated(store,stories,{'entries':[entry]})
            self.assertEqual(result['completed'],1);self.assertTrue(result['editorial_active'])
            self.assertEqual(meaning.cached_plan(store,source['text'])['review_method'],'redaktionell')
            self.assertEqual(stories.get(story['id'],with_meaning=False),story)

    def test_hidden_analysis_jobs_do_not_hide_older_comics(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root)
            req={'kacheln':1}
            store.create('old-comic',req,initial_status='editing');store.update('old-comic',status='completed')
            for i in range(105):
                ident='analysis-'+str(i);store.create(ident,req,initial_status='editing');store.update(ident,status='completed',narrative_mode=True)
            self.assertEqual([job['id'] for job in store.list(public_only=True)],['old-comic'])


if __name__=='__main__':unittest.main()
