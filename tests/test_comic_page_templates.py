"""Seitenvorlagen: Geometrie, vollständige Exporte und Vererbung ohne Modellaufrufe."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
from lettering import LAYOUT,DESIGN
from storage import Store
from stories import Stories
from engine import validate_request
import series

class PageTemplatesTests(unittest.TestCase):
    def test_catalog_has_distinct_nonoverlapping_templates_in_reading_order(self):
        self.assertGreaterEqual(len(LAYOUT.TEMPLATES),30)
        shapes=set()
        for template in LAYOUT.TEMPLATES.values():
            slots=template['slots'];self.assertEqual(len(slots),template['count'])
            shapes.add(json.dumps(slots))
            for i,(x,y,w,h) in enumerate(slots):
                self.assertTrue(0<=x<1 and 0<=y<1 and w>0 and h>0 and x+w<=1.00001 and y+h<=1.00001)
                for a,b,c,d in slots[:i]:self.assertTrue(x>=a+c-1e-8 or a>=x+w-1e-8 or y>=b+d-1e-8 or b>=y+h-1e-8)
        self.assertGreaterEqual(len(shapes),29)

    def test_sharing_uses_complete_template_pages_in_numeric_order(self):
        from sharing import image_sources
        job={'artifacts':[{'name':n} for n in ('pages/10.png','pages/02.png','pages/01.png','panels/01_panel.png','comic.png')]}
        self.assertEqual(image_sources(job,'six_action'),['pages/01.png','pages/02.png','pages/10.png'])
        self.assertEqual(image_sources(job),['panels/01_panel.png'])

    def test_unknown_templates_are_rejected_and_old_stories_still_work(self):
        self.assertEqual(validate_request({'thema':'Test'})['thema'],'Test')
        with self.assertRaises(ValueError):validate_request({'page_template':'unbekannt'})
        with tempfile.TemporaryDirectory() as tmp:
            stories=Stories(Store(tmp))
            with self.assertRaises(ValueError):stories.save({'name':'Test','mode':'editorial','payload':{'style':'Ligne claire','page_template':'unbekannt'}})

    def test_series_inherits_template_and_keeps_parent_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            stories=Stories(Store(tmp));parent=stories.save({'name':'Das Tor','mode':'editorial','payload':{'style':'Ligne claire','page_template':'six_action','article':'Ria öffnet ein Tor.','characters':[{'id':'a'*32,'name':'Ria','description':'Junge Frau.','outfit':'Gelbe Jacke.'}],'scenes':[{'story':'Ria vor dem Tor.','dialog':'','characters':[],'bubbles':[]}]}})
            before=copy.deepcopy(parent)
            settings=series.preview(stories,{'base_kind':'story','base_id':parent['id']})['settings']
            child=series.create(stories,{**settings,'title':'Hinter dem Tor','article':'Ria geht weiter.'})
            self.assertEqual(child['payload']['page_template'],'six_action');self.assertEqual(stories.get(parent['id']),before)
            child['payload']['page_template']='hero_top';child=stories.save(child,child['id'],child['version'])
            self.assertEqual(stories.get(parent['id']),before)
            settings=series.preview(stories,{'base_kind':'story','base_id':child['id']})['settings']
            self.assertEqual(series.create(stories,{**settings,'title':'Folge drei'})['payload']['page_template'],'hero_top')

    def test_render_uses_template_for_png_pdf_all_pages_and_keeps_tiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'panels').mkdir();(root/'pages').mkdir();(root/'pages/99.png').write_bytes(b'alt')
            tile=Image.new('RGB',(180,160),'#437fb2');tile.putpixel((0,0),(255,0,0));tile.putpixel((179,159),(0,255,0))
            tile.save(root/'comic.png')
            for i in range(7):tile.save(root/f'panels/{i+1:02}_panel.png')
            before=[p.read_bytes() for p in sorted((root/'panels').glob('*'))]
            src={'title':'Sieben Momente','scenes':[{}]*7,'page_template':'hero_top'}
            result=LAYOUT.render_layout(root,src,{},DESIGN,decorate=False)
            self.assertEqual(result,{'panels':7,'pages':3});self.assertEqual(len(list((root/'pages').glob('*.png'))),3)
            with Image.open(root/'comic.png') as im,Image.open(root/'pages/01.png') as first:
                self.assertEqual(im.size,first.size);self.assertEqual(im.tobytes(),first.tobytes())
                self.assertEqual(json.loads(im.info['editorial_layout'])['page_template'],'hero_top')
                colors=im.getcolors(im.width*im.height);self.assertTrue(any(c==(255,0,0) for _,c in colors));self.assertTrue(any(c==(0,255,0) for _,c in colors))
            self.assertTrue((root/'comic.pdf').read_bytes().startswith(b'%PDF'))
            self.assertEqual([Image.open(p).getpixel((0,0)) for p in sorted((root/'panels').glob('*'))],[(255,0,0)]*7)
            # Keine Bilderzeugung, keine unvollständigen Restseiten, keine Änderung der Panel-Pixel.
            for data,path in zip(before,sorted((root/'panels').glob('*'))):
                import io
                with Image.open(io.BytesIO(data)) as old,Image.open(path) as new:self.assertEqual(old.tobytes(),new.tobytes())

if __name__=='__main__':unittest.main()
