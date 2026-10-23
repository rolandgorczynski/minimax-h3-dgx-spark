"""Mauspositionierung: sichere Geometrie, exakte Vorschau, unveränderte Zeichnungen."""
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
import lettering
from storage import Store
from engine import validate_request
from editorial import export
from stories import Stories,Conflict


def fixture(root):
    store=Store(root);ident='a'*32;store.create(ident,validate_request({'kacheln':2}))
    source={'title':'Die Tür','article':'Ria: „Hallo!“','style':'Großstadt-Noir (düster)','characters':[{'id':'b'*32,'name':'Ria','description':'Braune Augen.','outfit':'Jacke','aliases':[]}],
            'scenes':[{'story':'Ria steht links.','dialog':'','characters':['b'*32],'bubbles':[{'speaker':'b'*32,'text':'Hallo!','x':.05,'y':.25,'w':.43,'h':.22,'tip_x':.25,'tip_y':.6}]} for _ in range(2)]}
    store.write(ident,'editorial-source.json',source);store.write(ident,'characters.json',source['characters']);store.write(ident,'workflow.json',{'nodes':[]});store.write(ident,'story.json',{'title':source['title'],'story':source['article']})
    for i in range(2):
        data=io.BytesIO();Image.new('RGB',(1024,704),'#334455').save(data,format='PNG');store.write(ident,f'panels/{i+1:02}_art.png',data.getvalue())
    store.stage(ident,'finished',status='needs_review',artifacts=export(store,ident))
    return store,store.get(ident)


class LetteringTests(unittest.TestCase):
    def test_preview_moves_bubbles_without_writing_or_generation(self):
        with tempfile.TemporaryDirectory() as root:
            store,job=fixture(root);manifest=lettering.manifest(store,job);before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in store.directory(job['id']).rglob('*') if p.is_file()}
            patch={k:v for k,v in manifest['panels'][0].items() if k!='story'};first=lettering.preview(store,job,{'version':manifest['version'],'panel':0,'layout':patch});self.assertTrue(first['valid'])
            patch['bubbles'][0]['x']=.5;second=lettering.preview(store,job,{'version':manifest['version'],'panel':0,'layout':patch});self.assertTrue(second['valid']);self.assertNotEqual(first['png'],second['png'])
            with Image.open(io.BytesIO(base64.b64decode(second['png']))) as image:self.assertEqual(image.size,(768,672))
            self.assertEqual(before,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in store.directory(job['id']).rglob('*') if p.is_file()});self.assertEqual(len(store.list()),1)

    def test_overlaps_caption_protection_and_small_font_block_saving(self):
        with tempfile.TemporaryDirectory() as root:
            store,job=fixture(root);info=lettering.manifest(store,job);p={k:v for k,v in info['panels'][0].items() if k!='story'}
            p['bubbles'].append(copy.deepcopy(p['bubbles'][0]));result=lettering.preview(store,job,{'version':info['version'],'panel':0,'layout':p});self.assertFalse(result['valid']);self.assertIn('überlappen',result['issues'][0])
            with self.assertRaises(ValueError):lettering.enqueue(store,job,{'version':info['version'],'panels':[p,p]})
            p['bubbles'].pop();p['protected_areas']=[{'x':.1,'y':.3,'w':.2,'h':.2}];self.assertTrue(any('geschützten' in x for x in lettering.issues(p)))
            p['protected_areas']=[];p['dialog']='Am Eingang.';p['bubbles'][0]['y']=.05;self.assertTrue(any('Erzähler' in x for x in lettering.issues(p)))
            p['dialog']='';p['bubbles'][0]['text']='Ein viel zu langer Text. '*12;result=lettering.preview(store,job,{'version':info['version'],'panel':0,'layout':p});self.assertFalse(result['valid']);self.assertIsNone(result['png'])
            with self.assertRaises(ValueError):lettering.panel({'bubbles':[{'speaker':'b'*32,'x':float('nan')} ]},[{'id':'b'*32}])
            with self.assertRaises(Conflict):lettering.preview(store,job,{'version':'veraltet','panel':0,'layout':p})

    def test_apply_creates_new_output_with_byte_identical_art_and_no_client(self):
        with tempfile.TemporaryDirectory() as root:
            store,job=fixture(root);info=lettering.manifest(store,job);patches=[{k:v for k,v in p.items() if k!='story'} for p in info['panels']];patches[0]['bubbles'][0]['x']=.5
            created=lettering.enqueue(store,job,{'version':info['version'],'panels':patches});self.assertNotEqual(created['id'],job['id']);self.assertTrue(created['lettering_mode'])
            with self.assertRaises(Conflict):Stories(store).delete_job(job['id'])
            result=lettering.render(store,created['id']);self.assertEqual(result['status'],'needs_review')
            for i in range(2):self.assertEqual((store.directory(job['id'])/f'panels/{i+1:02}_art.png').read_bytes(),(store.directory(created['id'])/f'panels/{i+1:02}_art.png').read_bytes())
            self.assertTrue((store.directory(created['id'])/'comic.pdf').exists());self.assertTrue((store.directory(created['id'])/'comic-bundle.zip').exists())
            report=json.loads((store.directory(created['id'])/'lettering-report.json').read_text());self.assertEqual(report['model_calls'],0)
            self.assertEqual(lettering.manifest(store,job)['version'],info['version'])

    def test_http_preview_requires_authentication_and_does_not_create_output(self):
        import os,threading,urllib.request,urllib.error
        from unittest.mock import patch
        from app import Service,Handler,ThreadingHTTPServer
        template=str(Path(__file__).resolve().parents[1]/'examples/comics/workflows/04_Comic_Automat_9B.json')
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'DATA_DIR':root,'LLM_BACKEND':'comfyui','WORKFLOW_TEMPLATE':template,'API_TOKEN':'test'}):
            store,job=fixture(root);service=Service()
            service.client.request=lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('Kein ComfyUI-Aufruf erlaubt.'))
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.service=service
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def call(path,method='GET',data=None,auth=True):
                req=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Authorization':'Bearer test'} if auth else {})
                try:
                    with urllib.request.urlopen(req) as r:return r.status,json.load(r)
                except urllib.error.HTTPError as exc:return exc.code,json.load(exc)
            try:
                endpoint='/jobs/'+job['id']+'/lettering'
                self.assertEqual(call(endpoint,auth=False)[0],401)
                status,info=call(endpoint);self.assertEqual(status,200)
                p={k:v for k,v in info['panels'][0].items() if k!='story'}
                status,result=call(endpoint+'/preview','POST',{'version':info['version'],'panel':0,'layout':p});self.assertEqual(status,200);self.assertTrue(result['valid'])
                self.assertEqual(len(store.list()),1)
                self.assertEqual(call(endpoint,'POST',{'version':'veraltet','panels':[p,p]})[0],409)
                self.assertEqual(len(store.list()),1)
            finally:server.shutdown();server.server_close();thread.join()

    def test_automatic_layout_keeps_protected_area_free_and_words_unchanged(self):
        with tempfile.TemporaryDirectory() as root:
            store,job=fixture(root);info=lettering.manifest(store,job);p={k:v for k,v in info['panels'][0].items() if k!='story'};p['protected_areas']=[{'x':.02,'y':.02,'w':.47,'h':.3}]
            result=lettering.automatic(store,job,{'version':info['version'],'panel':0,'layout':p});self.assertTrue(result['valid']);b=result['layout']['bubbles'][0];self.assertFalse(lettering.intersects(b,p['protected_areas'][0]));self.assertEqual(b['text'],'Hallo!');self.assertEqual(b['tip_x'],.25);self.assertFalse(lettering.contains(b,b['tip_x'],b['tip_y']))
