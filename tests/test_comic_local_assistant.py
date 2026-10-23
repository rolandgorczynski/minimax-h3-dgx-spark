"""Quellenbelege müssen aus dem Original kommen; lokale Prüfer dürfen nichts ändern."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from comic_local_assistant import prepare,check,paragraphs,validate_schema,FACT_SCHEMA


class Fake:
    def __init__(self,value):self.value=value
    def ask(self,*args,**kwargs):return self.value,{'modell':'test'}


class LocalTests(unittest.TestCase):
    def test_only_original_paragraphs_are_used_as_evidence(self):
        article='  Marius ist 22.\n\nDie Ursache ist unbekannt.\n'
        result=prepare(article,Fake({'belege':[{'thema':'Alter','absatz':1},{'thema':'Erfunden','absatz':99}], 'offene_fragen':[]}))
        self.assertEqual(len(result['belege']),1)
        for item in result['belege']:
            self.assertEqual(article[item['start']:item['ende']],item['textstelle'])
        self.assertEqual(len(result['verworfene_belege']),1)

    def test_text_check_never_changes_story_or_approves_it(self):
        data={'article':'Marius ist 22.','characters':[], 'scenes':[{'story':'Ein leerer Raum.','dialog':'Marius ist 45.','characters':[],'bubbles':[]}]}
        original=copy.deepcopy(data)
        result=check(data,Fake({'hinweise':[{'kachel':1,'beobachtung':'Falsches Alter.','absatz':1},{'kachel':1,'beobachtung':'Ohne Beleg.','absatz':4}]}),text_review=True)
        self.assertEqual(data,original)
        self.assertFalse(result['automatische_freigabe'])
        self.assertEqual(result['text_hinweise'][0]['textstelle'],'Marius ist 22.')
        self.assertEqual(len(result['hinweise_ohne_gueltigen_beleg']),1)

    def test_unknown_speaker_fails_before_model_call(self):
        data={'article':'Ein Text.','characters':[], 'scenes':[{'story':'Ein Raum.','characters':[],'bubbles':[{'speaker':'falsch','text':'Hallo.'}]}]}
        with self.assertRaisesRegex(ValueError,'Figuren-ID'):check(data,Fake(None))

    def test_invalid_structured_answers_are_not_accepted(self):
        with self.assertRaises(ValueError):validate_schema({'belege':[]},FACT_SCHEMA)
        with self.assertRaises(ValueError):paragraphs('')

    def test_default_formal_check_does_not_call_text_model(self):
        class Forbidden:
            def ask(self,*args,**kwargs):raise AssertionError('Kein semantischer Textvergleich im Standardablauf')
        data={'article':'Ein Text.','characters':[], 'scenes':[{'story':'Ein leerer Raum.','characters':[],'bubbles':[]}]}
        report=check(data,Forbidden())
        self.assertEqual(report['text_hinweise'],[])
        self.assertFalse(report['automatische_freigabe'])


if __name__=='__main__':unittest.main()
