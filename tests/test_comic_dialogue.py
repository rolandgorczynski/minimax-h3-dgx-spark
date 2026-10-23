"""Originalgespräche: stabile Sprecher, vollständige Übernahme, getrennte Erzählung."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
import dialogue
from storage import Store

CAST=[{'id':'a'*32,'name':'Ich','aliases':['Markus']},{'id':'b'*32,'name':'Ria','aliases':[]}]


class DialogueTests(unittest.TestCase):
    def test_direct_speech_prefix_suffix_and_unambiguous_speakers(self):
        article='„Bereit?“, fragte ich. Ria: „Ja.“\nRia fragte schüchtern: „Was kommt jetzt?“\n„Ein neuer Schnitt“, entgegnete Markus.'
        items=dialogue.quotes(article,CAST)
        self.assertEqual([q['speaker'] for q in items],['a'*32,'b'*32,'b'*32,'a'*32])
        self.assertTrue(all(q['kind']=='spoken' for q in items))
        self.assertEqual([q['text'] for q in items],['Bereit?','Ja.','Was kommt jetzt?','Ein neuer Schnitt'])

    def test_ambiguous_quotes_are_analyzed_with_context_not_invented(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);job='c'*32
            class Engine:
                def __init__(self):self.store=store
                def json_call(self,ident,step,prompt,validator,tokens):
                    self.prompt=prompt;self.step=step
                    return validator({'quotes':[{'id':'q002','kind':'spoken','speaker':'b'*32,'reason':'Die Antwort folgt auf die Frage an Ria.'},{'id':'q003','kind':'term','speaker':'','reason':'Ein zitierter Begriff, kein gesprochenes Gespräch.'}]})
            engine=Engine();items=dialogue.collect(engine,job,'„Bereit?“, fragte ich. „Ja.“ Ihre Stimme war leise. Auf der Akte steht „abgelehnt“.',CAST)
            self.assertEqual(engine.step,'article-dialogue');self.assertEqual(items[1]['speaker'],'b'*32);self.assertEqual(items[2]['kind'],'term')
            self.assertTrue((store.directory(job)/'dialogue-ledger.json').is_file())

    def test_speaker_lines_without_quotation_marks(self):
        items=dialogue.quotes('Markus: Nein! Nein!\nRia: Mach weiter!\nMarkus: „Okay.“',CAST)
        self.assertEqual([q['text'] for q in items],['Nein! Nein!','Mach weiter!','Okay.'])
        self.assertEqual([q['id'] for q in items],['q001','q002','q003'])
        self.assertEqual([q['speaker'] for q in items],['a'*32,'b'*32,'a'*32])

    def test_uncertain_alternatives_stay_open(self):
        items=dialogue.quotes('Ria sagte etwas wie „Oh!“ oder „Uh!“.',CAST)
        self.assertTrue(all(q['kind']=='uncertain' for q in items))

    def test_scene_assignment_cannot_lose_reorder_duplicate_or_rewrite_quotes(self):
        ledger=dialogue.quotes('Markus: „Nein! Nein!“ Ria: „Mach weiter!“',CAST)
        scenes=[{'story':'Markus und Ria sprechen.','dialog':'Nein! Nein!','characters':[], 'quote_ids':['q001','q002'],'bubbles':[{'speaker':'b'*32,'text':'Modell hat Text erfunden'}]}]
        result=dialogue.apply(scenes,ledger,CAST)
        self.assertEqual([b['text'] for b in result[0]['bubbles']],['Nein! Nein!','Mach weiter!'])
        self.assertEqual([b['speaker'] for b in result[0]['bubbles']],['a'*32,'b'*32]);self.assertEqual(result[0]['dialog'],'')
        self.assertEqual(result[0]['characters'],['a'*32,'b'*32])
        for ids in (['q001'],['q002','q001'],['q001','q001','q002'],['q001','q999']):
            with self.subTest(ids=ids),self.assertRaises(ValueError):dialogue.apply([{**scenes[0],'quote_ids':ids}],ledger,CAST)
        self.assertEqual(scenes[0]['bubbles'][0]['text'],'Modell hat Text erfunden')

    def test_split_speech_keeps_the_same_speaker_side(self):
        ledger=dialogue.quotes('Ria: „Was kommt jetzt?“ Markus: „Ich werde die Ansätze ganz kurz ausrasieren, das macht den Schnitt noch etwas schicker.“',CAST)
        scene=dialogue.apply([{'story':'Ria links, Markus rechts.','quote_ids':['q001','q002']}],ledger,CAST)[0]
        self.assertEqual(len(scene['bubbles']),3)
        self.assertEqual(scene['bubbles'][1]['tip_x'],scene['bubbles'][2]['tip_x'])
        self.assertEqual(scene['bubbles'][1]['x'],scene['bubbles'][2]['x'])
        self.assertGreater(scene['bubbles'][2]['y'],scene['bubbles'][1]['y'])

    def test_long_original_is_split_without_paraphrase_and_caption_preserves_action(self):
        text='Ich werde die Ansätze ganz kurz ausrasieren, das macht den Schnitt noch etwas schicker.'
        parts=dialogue.fragments(text)
        self.assertGreater(len(parts),1);self.assertEqual(' '.join(parts),text);self.assertTrue(all(len(p)<=64 for p in parts))
        self.assertEqual(dialogue.clean_caption('Ria sagt: „Mach weiter!“',[{'text':'Mach weiter!'}],CAST),'')
        self.assertEqual(dialogue.clean_caption('„Mach weiter!“ Ria sieht zum Spiegel.',[{'text':'Mach weiter!'}],CAST),'Ria sieht zum Spiegel.')
        self.assertEqual(dialogue.clean_caption(text,[{'text':p} for p in parts],CAST),'')

class LockedSourceSectionsTests(unittest.TestCase):
    def test_invalid_model_ids_and_omitted_final_dialogue_are_not_authoritative(self):
        text='Markus: „Bereit?“\n\nRia: „Ja.“\n\nDie Schere schneidet den Zopf ab.\n\nRia sagt etwas wie „Oh!“ oder „Uh!“.\n\nMarkus: „Wir sind fertig.“\n\nRia: „Danke!“'
        ledger=dialogue.quotes(text,CAST);sections=dialogue.sections(text,ledger,4)
        wrong=[{'story':'Eine Bildbeschreibung.','characters':[], 'dialog':'Markus: Bereit?','quote_ids':['q999','q003']} for _ in range(4)]
        result=dialogue.apply_sections(wrong,ledger,CAST,sections)
        actual=[b['text'] for s in result for b in s['bubbles']]
        self.assertEqual(actual,['Bereit?','Ja.','Wir sind fertig.','Danke!'])
        self.assertEqual(result[-1]['bubbles'][-1]['text'],'Danke!')
        self.assertEqual(sections[0]['start'],0);self.assertEqual(sections[-1]['end'],len(text))
        self.assertTrue(all(a['end']==b['start'] for a,b in zip(sections,sections[1:])))
        self.assertTrue(all(s['dialog']=='' for s in result))
        self.assertEqual(wrong[0]['quote_ids'],['q999','q003'])
        for section in sections:
            for q in ledger:self.assertFalse(q['start']<section['end']<q['end'])
