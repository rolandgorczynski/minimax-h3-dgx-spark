"""Buchdateien: EPUB-Struktur, eingebettete Schrift und KDP-Maße ohne Bildlauf."""
import copy
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
import books
from storage import Store
from engine import validate_request
from editorial import export


def comic(root,count):
    store=Store(root);ident='a'*32;store.create(ident,validate_request({'kacheln':count}))
    scenes=[]
    for i in range(count):
        scenes.append({'story':'Eine ruhige Szene '+str(i+1),'dialog':'','characters':[],'bubbles':[]})
        data=io.BytesIO();Image.new('RGB',(768,672),(30+i%150,60,90)).save(data,format='PNG');store.write(ident,f'panels/{i+1:02}_panel.png',data.getvalue())
    store.write(ident,'editorial-source.json',{'title':'Ein Comic','scenes':scenes});store.stage(ident,'finished',status='needs_review',artifacts=export(store,ident));return store,store.get(ident)


class BooksTests(unittest.TestCase):
    def test_kdp_epub_and_print_include_author_and_front_back_text(self):
        with tempfile.TemporaryDirectory() as root:
            store,parent=comic(root,24);settings=books.defaults('Titel & Abenteuer');settings.update(author='Änne Beispiel',front_text='Mein Vorwort mit Gefühl.',back_text='Mein Nachwort.',blurb='Ein besonderes Abenteuer.',publisher='Ein Verlag')
            before={p.name:p.read_bytes() for p in (store.directory(parent['id'])/'panels').iterdir()}
            job=books.enqueue(store,parent,settings);result=books.run(store,job['id']);report=result['book_report'];self.assertTrue(report['print_upload_ready']);self.assertEqual(report['model_calls'],0);self.assertFalse(report['kdp_acceptance_verified'])
            out=store.directory(job['id'])/'books';self.assertTrue((out/'taschenbuch-inhalt.pdf').exists());self.assertTrue((out/'taschenbuch-umschlag.pdf').exists())
            pdf=(out/'taschenbuch-inhalt.pdf').read_bytes();self.assertIn(b'/FontFile2',pdf);self.assertNotIn(b'/BaseFont /Helvetica',pdf)
            self.assertTrue(re.search(rb'/MediaBox\s*\[\s*0\s+0\s+432\s+648\s*\]',pdf))
            with zipfile.ZipFile(out/'comic.epub') as z:
                self.assertEqual(z.infolist()[0].filename,'mimetype');self.assertEqual(z.infolist()[0].compress_type,zipfile.ZIP_STORED)
                opf=z.read('EPUB/package.opf').decode();self.assertIn('Änne Beispiel',opf);self.assertIn('Titel &amp; Abenteuer',opf);self.assertIn('pre-paginated',opf);self.assertIn('book-type',opf)
                self.assertEqual(len(z.namelist()),len(set(z.namelist())));self.assertFalse(any('workflow' in n or 'characters' in n for n in z.namelist()))
                for name in z.namelist():
                    if name.endswith(('.xml','.xhtml','.opf')):ET.fromstring(z.read(name))
                self.assertEqual(len(ET.fromstring(z.read('EPUB/package.opf')).find('{http://www.idpf.org/2007/opf}spine')),report['epub_pages'])
            self.assertEqual(before,{p.name:p.read_bytes() for p in (store.directory(parent['id'])/'panels').iterdir()})
            self.assertEqual(len(store.list()),2)

    def test_source_author_is_only_an_editable_default(self):
        with tempfile.TemporaryDirectory() as root:
            store,parent=comic(root,2)
            path=store.directory(parent['id'])/'editorial-source.json';data=json.loads(path.read_text());data['book_author']='Mein Pseudonym';store.write(parent['id'],'editorial-source.json',data)
            self.assertEqual(books.settings(store,parent)['settings']['author'],'Mein Pseudonym')
            settings=books.settings(store,parent)['settings'];settings['author']='Anderer Name';books.save_settings(store,parent,settings)
            self.assertEqual(books.settings(store,parent)['settings']['author'],'Anderer Name')

    def test_short_book_is_explicit_draft_without_filling_blank_pages(self):
        with tempfile.TemporaryDirectory() as root:
            store,parent=comic(root,2);settings=books.defaults('Kurzer Comic');settings['author']='Autor'
            job=books.enqueue(store,parent,settings);result=books.run(store,job['id']);report=result['book_report'];out=store.directory(job['id'])/'books'
            self.assertFalse(report['print_upload_ready']);self.assertLess(report['pages'],24);self.assertTrue((out/'comic.epub').exists());self.assertTrue((out/'taschenbuch-inhalt-ENTWURF.pdf').exists());self.assertFalse((out/'taschenbuch-inhalt.pdf').exists())
            self.assertEqual(books.settings(store,parent)['last_export'],job['id'])

    def test_authenticated_book_settings_and_queued_export_do_not_call_models(self):
        import os,threading,urllib.request,urllib.error
        from unittest.mock import patch
        from app import Service,Handler,ThreadingHTTPServer
        template=str(Path(__file__).resolve().parents[1]/'examples/comics/workflows/04_Comic_Automat_9B.json')
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'DATA_DIR':root,'LLM_BACKEND':'comfyui','API_TOKEN':'test','WORKFLOW_TEMPLATE':template}):
            store,parent=comic(root,2);service=Service();service.client.request=lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('Kein Modellaufruf erlaubt.'))
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.service=service;thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def call(path,method='GET',data=None,auth=True):
                request=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Authorization':'Bearer test'} if auth else {})
                try:
                    with urllib.request.urlopen(request) as response:return response.status,json.load(response)
                except urllib.error.HTTPError as exc:return exc.code,json.load(exc)
            try:
                endpoint='/jobs/'+parent['id'];self.assertEqual(call(endpoint+'/book-settings',auth=False)[0],401)
                info=call(endpoint+'/book-settings')[1];self.assertEqual(info['settings']['author'],'')
                value={**info['settings'],'author':'Mein Autor','front_text':'Widmung'}
                self.assertEqual(call(endpoint+'/book-settings','PUT',value)[0],200)
                status,job=call(endpoint+'/book-export','POST',value);self.assertEqual(status,202);self.assertTrue(job['book_mode'])
                self.assertEqual(len(call('/jobs')[1]['jobs']),1)
                self.assertEqual(call(endpoint+'/book-settings')[1]['last_export'],job['id'])
                self.assertEqual(call(endpoint+'/book-export','POST',value)[0],409)
            finally:server.shutdown();server.server_close();thread.join()

    def test_no_author_no_export_and_metadata_validation(self):
        with tempfile.TemporaryDirectory() as root:
            store,parent=comic(root,1)
            with self.assertRaises(ValueError):books.enqueue(store,parent,books.defaults('Titel'))
            self.assertEqual(len(store.list()),1)
            for patch in ({'isbn':'123'},{'panels_per_page':True},{'trim':'frei'},{'author':'X\x01Y'}):
                with self.assertRaises(ValueError):books.validate({**books.defaults(),**patch})
            saved=books.save_settings(store,parent,{**books.defaults('Titel'),'author':'Mein Name','front_text':'Widmung'});self.assertEqual(books.settings(store,parent)['settings'],saved)
