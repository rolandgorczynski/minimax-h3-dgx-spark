"""Geführte Navigation und gemeinsame Buchseiten ohne LLM- oder Bilderzeugung."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_comic_books import comic
import books
import guided_reader as reader
from stories import Conflict


def fixture(folder):
    store,job=comic(folder,7);root=store.directory(job['id']);src=json.loads((root/'editorial-source.json').read_text());src['page_template']='hero_top';store.write(job['id'],'editorial-source.json',src)
    return store,job,src

class GuidedReaderTests(unittest.TestCase):
    def test_geometry_matches_pixels_and_read_order_roundtrips_without_changing_originals(self):
        with tempfile.TemporaryDirectory() as folder:
            store,job,src=fixture(folder);root=store.directory(job['id']);before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
            first=reader.manifest(store,job);self.assertEqual(len(first['pages']),3)
            saved=reader.save(store,job,{'version':first['version'],'page_order':[3,1],'panel_orders':{'1':[3,1,2]}})
            self.assertEqual(saved['settings']['page_order'],[3,1]);self.assertEqual(saved['settings']['panel_orders']['1'],[3,1,2]);self.assertEqual(len(saved['pages']),3)
            self.assertEqual([r['panel'] for r in sorted(saved['pages'][0]['regions'],key=lambda r:r['ordinal'])],[3,1,2])
            with self.assertRaises(Conflict):reader.save(store,job,{'version':first['version'],'page_order':[1]})
            for order in ([],[1,1],[0],[True]):
                with self.subTest(order=order),self.assertRaises(ValueError):reader.save(store,job,{'version':saved['version'],'page_order':order})
            with self.assertRaises(ValueError):reader.save(store,job,{'version':saved['version'],'panel_orders':{'1':[1,2,7]}})
            import io
            with Image.open(io.BytesIO(reader.image(store,job,1))) as im:
                self.assertEqual(im.size,(first['pages'][0]['width'],first['pages'][0]['height']))
                for r in first['pages'][0]['regions']:
                    x,y,w,h=r['rect'];self.assertEqual(im.getpixel((x+w//2,y+h//2)),(30+r['panel']-1,60,90))
            self.assertEqual(before,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()})
            restored=reader.save(store,job,{'version':saved['version'],'page_order':[1,2,3],'panel_orders':{'1':[1,2,3]}})
            self.assertEqual(len(restored['settings']['page_order']),3)

    def test_book_epub_print_and_kindle_package_use_the_same_selected_pages(self):
        with tempfile.TemporaryDirectory() as folder:
            store,job,src=fixture(folder);info=reader.manifest(store,job)
            reader.save(store,job,{'version':info['version'],'page_order':[3,1],'panel_orders':{'1':[3,1,2]}})
            settings=books.settings(store,job)['settings'];self.assertEqual(settings['layout_mode'],'template');settings['author']='Sysop';settings['front_text']='Ein eigenes Vorwort.';settings['back_text']='Das Ende.'
            export=books.enqueue(store,job,settings)
            # Der Export verwendet die gesicherte Auswahl, auch wenn die Leseordnung danach geändert wird.
            info=reader.manifest(store,job);reader.save(store,job,{'version':info['version'],'page_order':[2]})
            result=books.run(store,export['id']);report=result['book_report'];out=store.directory(export['id'])/'books'
            self.assertEqual(report['comic_pages'],2);self.assertEqual(report['guided_panel_count'],4);self.assertEqual(report['model_calls'],0)
            navigation=json.loads((out/'kindle-create/navigation.json').read_text())
            self.assertEqual([p['id'] for p in navigation['pages']],[3,1])
            with zipfile.ZipFile(out/'kindle-create.zip') as z:
                self.assertIn('comic-0001.png',z.namelist());self.assertIn('comic-0002.png',z.namelist());self.assertNotIn('comic-0003.png',z.namelist());self.assertEqual(len([n for n in z.namelist() if n.startswith('Buchseiten/')]),report['epub_pages'])
            with zipfile.ZipFile(out/'buchpaket.zip') as z:self.assertIn('kindle-create.zip',z.namelist())
            with zipfile.ZipFile(out/'comic.epub') as z:
                self.assertEqual(len(z.namelist()),len(set(z.namelist())))
                comic_pages=[]
                for name in z.namelist():
                    if name.endswith('.xhtml'):
                        page=ET.fromstring(z.read(name));anchors=[a for a in page.iter() if a.get('class')=='app-amzn-magnify']
                        if not anchors:continue
                        ids={node.get('id') for node in page.iter() if node.get('id')};values=[json.loads(a.get('data-app-amzn-magnify')) for a in anchors]
                        self.assertEqual([v['ordinal'] for v in values],list(range(1,len(values)+1)))
                        self.assertTrue(all(v['targetId'] in ids for v in values));comic_pages.append(values)
                self.assertEqual([[v['targetId'] for v in page] for page in comic_pages],[['panel-7'],['panel-3','panel-1','panel-2']])
                self.assertNotIn('EPUB/images/panel-00004.jpg',z.namelist())
            self.assertTrue(any('mindestens 24' in b for b in report['blockers']))
            self.assertTrue((out/'taschenbuch-inhalt-ENTWURF.pdf').exists())

    def test_adaptive_kachel_sizes_survive_epub_and_print_export(self):
        from panel_formats import apply
        from lettering import DESIGN
        with tempfile.TemporaryDirectory() as folder:
            store,job,src=fixture(folder);src['scenes']=apply(src['scenes'],'hero_top');root=store.directory(job['id'])
            for i,scene in enumerate(src['scenes']):
                raw=Image.new('RGB',tuple(scene['render_size']),'#426a8c')
                DESIGN.panel(raw,'',i+1,[],canvas_size=scene['canvas_size']).save(root/f'panels/{i+1:02}_panel.png')
            store.write(job['id'],'editorial-source.json',src)
            settings=books.settings(store,job)['settings'];settings['author']='Sysop';task=books.enqueue(store,job,settings)
            report=books.run(store,task['id'])['book_report'];out=store.directory(task['id'])/'books'
            navigation=json.loads((out/'kindle-create/navigation.json').read_text());first=navigation['pages'][0]
            self.assertTrue(first['adaptive']);self.assertEqual(first['regions'][0]['original_size'],src['scenes'][0]['canvas_size'])
            self.assertGreater(first['regions'][0]['rect'][2],first['regions'][1]['rect'][2]*1.8)
            self.assertEqual(report['guided_panel_count'],7);self.assertEqual(report['comic_pages'],3)
            with zipfile.ZipFile(out/'comic.epub') as archive:self.assertIn('EPUB/images/panel-00001.jpg',archive.namelist())

    def test_http_reader_requires_token_and_rejects_stale_saves(self):
        from app import Handler,Service
        from stories import Stories
        from unittest.mock import patch
        from http.server import ThreadingHTTPServer
        import threading,urllib.request,urllib.error
        with tempfile.TemporaryDirectory() as folder:
            store,job,src=fixture(folder)
            with patch.object(Service,'__init__',lambda self:None):service=Service()
            service.store=store;service.stories=Stories(store);service.token='test'
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.service=service
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            url='http://127.0.0.1:'+str(server.server_port)+'/jobs/'+job['id']+'/reader'
            try:
                with self.assertRaises(urllib.error.HTTPError) as denied:urllib.request.urlopen(url)
                self.assertEqual(denied.exception.code,401)
                def call(payload=None):
                    req=urllib.request.Request(url,data=json.dumps(payload).encode() if payload else None,method='PUT' if payload else 'GET',headers={'Authorization':'Bearer test','Content-Type':'application/json'})
                    with urllib.request.urlopen(req) as response:return json.load(response)
                info=call();self.assertEqual(len(info['pages']),3)
                saved=call({'version':info['version'],'page_order':[3,1]});self.assertEqual(saved['settings']['page_order'],[3,1])
                with self.assertRaises(urllib.error.HTTPError) as stale:call({'version':info['version'],'page_order':[1]})
                self.assertEqual(stale.exception.code,409)
                with urllib.request.urlopen(urllib.request.Request(url+'/pages/1.png',headers={'Authorization':'Bearer test'})) as response:self.assertTrue(response.read().startswith(b'\x89PNG'))
            finally:server.shutdown();server.server_close();thread.join()

    def test_print_still_blocks_unreadably_small_text_in_template(self):
        with tempfile.TemporaryDirectory() as folder:
            store,job,src=fixture(folder)
            for scene in src['scenes']:scene['dialog']='Ein wichtiger Erzählertext.'
            store.write(job['id'],'editorial-source.json',src);settings=books.settings(store,job)['settings'];settings['author']='Sysop'
            task=books.enqueue(store,job,settings);report=books.run(store,task['id'])['book_report']
            self.assertTrue(any('Schrift wäre kleiner als 7 Punkt' in text for text in report['blockers']))

if __name__=='__main__':unittest.main()
