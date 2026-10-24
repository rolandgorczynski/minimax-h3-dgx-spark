"""Modellberichte normalisieren, ohne widersprüchliche Sprachprüfungen freizugeben."""
import sys,tempfile,json
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
from engine import valid_review,Engine
from storage import Store

class LanguageReviewTests(unittest.TestCase):
    def test_actual_uppercase_issues_report_is_accepted_without_mutation(self):
        original={'approved':True,'ISSUES':[]};result=valid_review(original)
        self.assertEqual(result,{'approved':True,'issues':[]});self.assertEqual(original,{'approved':True,'ISSUES':[]})
        self.assertEqual(valid_review({'APPROVED':False,'ISSUES':['Foreign sentence.']})['issues'],['Foreign sentence.'])

    def test_ambiguous_invalid_and_contradictory_reports_still_fail(self):
        for value in ({'approved':True,'ISSUES':['Fehler']},{'approved':False,'ISSUES':[]},{'approved':'true','ISSUES':[]},{'approved':True,'issues':[],'ISSUES':['Fehler']}):
            with self.subTest(value=value),self.assertRaises(ValueError):valid_review(value)

    def test_actual_shape_does_not_start_translation_or_rewrite_scenes(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);store.create('a'*32,{'seed':1});calls=[]
            class Fake:
                require_german=Engine.require_german
                def __init__(self):self.store=store
                def json_call(self,job,step,prompt,validator,tokens):calls.append(step);return validator({'approved':True,'ISSUES':[]})
            scenes=[{'story':'Hildebrand bleibt im Sattel.','dialog':'Der Reiter antwortet.','bubbles':[]}]
            result=Fake().require_german('a'*32,'source-german-1',scenes,lambda value:value,1000)
            self.assertIs(result,scenes);self.assertEqual(calls,['source-german-1-review-0'])

if __name__=='__main__':unittest.main()
