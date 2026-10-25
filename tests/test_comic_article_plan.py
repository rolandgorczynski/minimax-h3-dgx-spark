"""Artikelplanung muss Original und Titel erhalten und vor der Bilderzeugung stoppen."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
from storage import Store
from stories import Stories,Conflict
from article_plan import prepare
from engine import Engine


class FakeEngine:
    def __init__(self,store):self.store=store;self.calls=[]
    validate_scenes=Engine.validate_scenes
    def json_call(self,job,step,prompt,validator,tokens):
        self.calls.append(step)
        if '-continuity-events-' in step:return validator({'events':[]})
        if step=='article-people':return validator({'characters':[{'name':'Ria','description':'Erwachsene Person, braune Augen. Frisur ändert sich je Szene.','outfit':'Friseurumhang'}]})
        import json
        people=json.loads(prompt.split('FIGUREN:\n')[1].split('\nDIALOGLISTE:')[0])
        return validator([{'story':'Ria sitzt vor dem Spiegel.','dialog':'Bereit?','characters':[people[0]['id']],'quote_ids':['q001'],'bubbles':[{'speaker':people[0]['id'],'text':'Erfundenes Zitat'}]}, {'story':'Ria sieht zum Spiegel.','dialog':'Die Veränderung beginnt.','characters':[people[0]['id']],'quote_ids':[]}])
    def preflight(self,*args):return {'valid':True,'issues':[]}


class ArticlePlanTests(unittest.TestCase):
    def test_automatic_mode_creates_editable_script_before_any_images(self):
        class Writer(FakeEngine):
            def existing_cast(self,ids):return []
            def require_german(self,job,step,value,validator,tokens):return validator(value)
            def json_call(self,job,step,prompt,validator,tokens):
                if step=='automatic-script-story':
                    self.calls.append(step);return validator({'story':'Ria: „Bereit?“ Ria nickt.'})
                return super().json_call(job,step,prompt,validator,tokens)
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);stories=Stories(store)
            story=stories.save({'name':'Neue Geschichte','mode':'automatic','payload':{'thema':'Ein Spiegel','kacheln':2}})
            job=stories.plan(story['id'],1);engine=Writer(store)
            result=prepare(engine,stories,job['id']);saved=stories.get(story['id'])
            self.assertEqual(saved['mode'],'editorial');self.assertTrue(saved['payload']['visual_style_pending'])
            self.assertEqual(len(saved['payload']['scenes']),2);self.assertEqual(result['artifacts'],[])
            self.assertEqual(engine.calls[0],'automatic-script-story')
            with self.assertRaisesRegex(ValueError,'Bildstil'):stories.enqueue(story['id'],saved['version'])

    def test_layout_issue_keeps_editable_draft_without_rendering(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);stories=Stories(store)
            story=stories.save({'name':'HG1','mode':'editorial','payload':{'article':'Ria: „Bereit?“ Ria nickt.','style':'Warme Alltagsillustration','panel_count':2,'scenes':[]}})
            job=stories.plan(story['id'],1);engine=FakeEngine(store)
            engine.preflight=lambda *args:{'valid':False,'issues':[{'panel':1,'message':'Text zu lang.'}]}
            result=prepare(engine,stories,job['id'])
            self.assertEqual(result['planning_issues'][0]['panel'],1)
            self.assertEqual(len(stories.get(story['id'])['payload']['scenes']),2)
            self.assertEqual(engine.calls,['article-people','article-scenes','article-scenes-fit','article-continuity-events-1'])

    def test_prepare_without_rewriting_or_rendering(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);stories=Stories(store)
            story=stories.save({'name':'HG1','mode':'editorial','payload':{'article':'Ria: „Bereit?“ Ria nickt.','style':'Warme Alltagsillustration','panel_count':2,'scenes':[]}})
            job=stories.plan(story['id'],1)
            with self.assertRaises(Conflict):stories.plan(story['id'],1)
            store.claim();engine=FakeEngine(store);result=prepare(engine,stories,job['id'])
            saved=stories.get(story['id']);self.assertEqual(saved['name'],'HG1');self.assertEqual(saved['payload']['article'],story['payload']['article'])
            self.assertEqual(len(saved['payload']['scenes']),2)
            self.assertEqual(saved['payload']['scenes'][1]['bubbles'],[])
            self.assertEqual(saved['payload']['scenes'][0]['bubbles'][0]['expression'],'normal')
            self.assertEqual(saved['payload']['scenes'][0]['bubbles'][0]['text'],'Bereit?')
            self.assertEqual(saved['payload']['scenes'][0]['dialog'],'')
            self.assertEqual(saved['payload']['dialogue_ledger'][0]['speaker'],saved['payload']['characters'][0]['id'])
            self.assertEqual(saved['payload']['planned_article'],story['payload']['article'])
            self.assertEqual(result['status'],'completed');self.assertEqual(engine.calls,['article-people','article-scenes','article-continuity-events-1'])

    def test_late_result_cannot_overwrite_user_edit(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);stories=Stories(store)
            story=stories.save({'name':'HG1','mode':'editorial','payload':{'article':'Ria: „Bereit?“ Ria nickt.','style':'Warme Alltagsillustration','panel_count':2,'scenes':[]}})
            job=stories.plan(story['id'],1)
            stories.save({**story,'name':'Mein neuer Titel'},story['id'],1)
            with self.assertRaises(Conflict):prepare(FakeEngine(store),stories,job['id'])
            self.assertEqual(stories.get(story['id'])['name'],'Mein neuer Titel')


if __name__=='__main__':unittest.main()
