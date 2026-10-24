"""Lesbare Blasen automatisch einpassen und übervolle Entwürfe editierbar liefern."""
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
from lettering_plan import prepare,accept_preflight,record
import lettering
import sharing
import books
from test_comic_lettering import fixture


class DraftTests(unittest.TestCase):
    def test_realistic_wide_panel_fits_without_rewriting(self):
        ident='b'*32
        scene={'story':'Vater und Sohn umarmen sich.','dialog':'Eine lange Trennung findet ihr Ende in einer emotionalen Wiedervereinigung…','canvas_size':[1088,672],
               'bubbles':[{'speaker':ident,'text':'Ich habe dich so oft in meinen Gedanken gesehen…','x':.08,'y':.321455938697318,'w':.38,'h':.1586206896551724,'tip_x':.25,'tip_y':.5417624521072797}]}
        before=copy.deepcopy(scene)
        result,report=prepare([scene],[{'id':ident,'name':'Alebrand'}])
        self.assertEqual(scene,before)
        self.assertFalse(report['unresolved_panels'])
        self.assertEqual(result[0]['bubbles'][0]['text'],scene['bubbles'][0]['text'])
        self.assertTrue(report['adjustments'])
        lettering.DESIGN.panel(Image.new('RGB',(1088,672)),result[0]['dialog'],1,result[0]['bubbles'],{ident:'Alebrand'},canvas_size=[1088,672])

    def test_overflow_is_visible_draft_and_full_caption_stays_editable(self):
        scene={'story':'Eine Tür.','dialog':'W'*390,'bubbles':[]}
        scenes,report=prepare([scene],[])
        self.assertEqual(report['unresolved_panels'],[1])
        self.assertEqual(scenes[0]['dialog'],scene['dialog'])
        image=Image.new('RGB',(768,672))
        with self.assertRaises(ValueError):lettering.DESIGN.panel(image,scene['dialog'],1,[])
        draft=lettering.DESIGN.panel(image,scene['dialog'],1,[],draft=True)
        self.assertEqual(draft.size,(768,672))
        self.assertEqual(draft.getpixel((10,640)),(255,223,138))
        with tempfile.TemporaryDirectory() as root:
            store,job=fixture(root);path=store.directory(job['id'])/'editorial-source.json';source=json.loads(path.read_text());source['scenes'][0].update(scenes[0]);store.write(job['id'],'editorial-source.json',source)
            record(store,job['id'],report);job=store.get(job['id'])
            with self.assertRaisesRegex(ValueError,'Entwurf'):sharing.image_sources(job)
            with self.assertRaisesRegex(Exception,'Entwurf'):books.source(store,job)
            info=lettering.manifest(store,job);patches=[{k:v for k,v in p.items() if k!='story'} for p in info['panels']]
            preview=lettering.preview(store,job,{'version':info['version'],'panel':0,'layout':patches[0]})
            self.assertFalse(preview['valid']);self.assertTrue(preview['background']);self.assertEqual(preview['layout']['dialog'],scene['dialog'])
            patches[0]['dialog']='Eine Tür öffnet sich.'
            corrected=lettering.enqueue(store,job,{'version':info['version'],'panels':patches})
            self.assertFalse(corrected['lettering_unresolved'])
            saved=json.loads((store.directory(corrected['id'])/'editorial-source.json').read_text())
            self.assertNotIn('lettering_draft',saved['scenes'][0])
            self.assertEqual((store.directory(job['id'])/'panels/01_art.png').read_bytes(),(store.directory(corrected['id'])/'panels/01_art.png').read_bytes())
            rendered=lettering.render(store,corrected['id']);self.assertEqual(rendered['status'],'needs_review')

    def test_structural_errors_are_not_accepted_as_drafts(self):
        with self.assertRaisesRegex(ValueError,'ungültig'):
            accept_preflight([{}],{'issues':[{'panel':1,'message':'Unbekannte Figur'}]},{'unresolved_panels':[],'warnings':[]})

    def test_whitespace_cleaning_preserves_words_paragraphs_and_emoji(self):
        self.assertEqual(lettering.DESIGN.clean_text('  Hallo   Welt!\r\n\r\n\r\n 👩\u200d🔬\u200b  '),'Hallo Welt!\n\n👩\u200d🔬')
        scene={'story':'Eine Tür.','dialog':'Hallo'+(' '*500)+'Welt!','bubbles':[]}
        result,_=prepare([scene],[]);self.assertEqual(result[0]['dialog'],'Hallo Welt!');self.assertEqual(scene['dialog'],'Hallo'+(' '*500)+'Welt!')

if __name__=='__main__':unittest.main()
