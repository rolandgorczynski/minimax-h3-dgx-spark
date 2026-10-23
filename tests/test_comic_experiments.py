"""Experimentzweig: aktuelle Fassung übernehmen und ausschließlich eigene Dateien ändern."""
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import urllib.request
import urllib.error
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
import experiments
from storage import Store
from engine import Engine,validate_request
from stories import Stories,Conflict
from editorial import export

WHO='a'*32

def fixture(root,count=2):
    store=Store(root);ident='b'*32;store.create(ident,validate_request({'kacheln':count,'stil':'Ligne claire'}));im=io.BytesIO();Image.new('RGB',(320,280),'#345678').save(im,format='PNG');png=im.getvalue()
    cast=[{'id':WHO,'name':'Ria','description':'Junge Frau, schwarze Haare.','outfit':'Gelbe Jacke.','alignment':'neutral_good','inline_references':[base64.b64encode(png).decode()]}]
    scenes=[{'heading':'Original '+str(i+1),'story':'Ria wartet vor dem Eingang '+str(i+1)+'.','dialog':'Mein korrigierter Erzählertext.','characters':[WHO],'character_states':{},'protected_areas':[{'x':.2,'y':.2,'w':.1,'h':.1}],'bubbles':[{'speaker':WHO,'text':'Meine bearbeitete Sprechblase.','expression':'normal','bubble_style':'thought','x':.1,'y':.3,'w':.4,'h':.2,'tip_x':.3,'tip_y':.8}]} for i in range(count)]
    source={'title':'Meine bearbeitete Geschichte','article':'Ria wartet. Sie öffnet am Ende die Tür.','style':'Ligne claire','seed':1,'characters':cast,'scenes':scenes,'series':{'id':'c'*32,'name':'Reihe','episode':2,'initial_states':{WHO:'Gelbe Jacke.'}}}
    store.write(ident,'editorial-source.json',source);store.write(ident,'characters.json',cast)
    for i in range(count):
        store.write(ident,f'panels/{i+1:02}_art.png',png);store.write(ident,f'panels/{i+1:02}_panel.png',png)
    store.update(ident,status='needs_review',story_title=source['title'],feedback={'kommentar':'Bestehendes Feedback','bewertungen':{}},artifacts=export(store,ident),story_id='d'*32)
    return store,store.get(ident)


def settings(store,parent,**changes):
    info=experiments.options(store,parent);return {'version':info['version'],**info['settings'],**changes}


class FakeEngine:
    def __init__(self,store,fail_review=False):self.store=store;self.calls=[];self.sizes=[];self.fail_review=fail_review
    def json_call(self,ident,step,prompt,validator,tokens,images=None):
        self.calls.append(step)
        if step.startswith('experiment-direction-'):
            if step.endswith('vision'):assert images and images[0].startswith(b'\xff\xd8')
            return validator({'core':'Eine Tür und eine Entscheidung.','emotion':'Ria überwindet ihre Angst.','turning_point':'Ria entscheidet sich zu handeln.','visual_rhythm':'Erst Stille, dann eine dynamische Bewegung.','ending':'Ria öffnet wie zuvor die Tür.'})
        if 'review' in step:return validator({'approved':not self.fail_review,'issues':['Unklarer Handlungsanschluss.'] if self.fail_review else []})
        start,end,count=map(int,re.search(r'für Position (\d+) bis (\d+) von insgesamt (\d+)',prompt).groups());self.sizes.append(end-start+1)
        return validator([{'heading':'Neue Szene '+str(i),'story':'Tiefe Froschperspektive: Ria hält inne und entscheidet sich, die schwere Tür aufzustoßen.','dialog':'Ein Moment verändert alles.','characters':[WHO],'bubbles':[{'speaker':WHO,'text':'Ich entscheide mich jetzt.','expression':'shout','bubble_style':'burst'}],'character_states':{},'reason':'Aus passivem Warten wird eine sichtbare Entscheidung.'} for i in range(start,end+1)])
    def require_german(self,ident,step,value,validator,tokens):return validator(value)
    def preflight(self,*args):return {'valid':True,'issues':[]}


class ExperimentTests(unittest.TestCase):
    def test_branch_snapshots_latest_edits_and_original_is_untouched(self):
        with tempfile.TemporaryDirectory() as root:
            store,parent=fixture(root);before=copy.deepcopy(parent);files={str(p):p.read_bytes() for p in store.directory(parent['id']).rglob('*') if p.is_file()}
            job=experiments.enqueue(store,parent,settings(store,parent,notes='Mehr Konflikt und weniger Erklärung.'));snapshot=json.loads((store.directory(job['id'])/'experiment-input.json').read_text())
            self.assertEqual(snapshot['source']['scenes'][0]['bubbles'][0]['text'],'Meine bearbeitete Sprechblase.')
            self.assertNotIn('story_id',job);self.assertEqual(job['based_on_story_id'],parent['story_id']);self.assertNotEqual(job['id'],parent['id'])
            source,report=experiments.plan(FakeEngine(store),job['id']);self.assertEqual(source['characters'],snapshot['source']['characters']);self.assertEqual(len(source['scenes']),2);self.assertTrue(report['experimental'])
            self.assertNotIn('series',source);self.assertEqual(source['based_on_series']['name'],'Reihe');self.assertNotEqual(source['scenes'][0]['bubbles'][0]['x'],snapshot['source']['scenes'][0]['bubbles'][0]['x']);self.assertNotIn('protected_areas',source['scenes'][0])
            self.assertEqual(store.get(parent['id']),before);self.assertEqual(files,{str(p):p.read_bytes() for p in store.directory(parent['id']).rglob('*') if p.is_file()})
            self.assertEqual(snapshot['original_art_sha256'][0],hashlib.sha256((store.directory(job['id'])/'checkpoints/experiment-originals/01_art.png').read_bytes()).hexdigest())

    def test_staging_keeps_dialogues_and_speakers_but_resets_coordinates(self):
        with tempfile.TemporaryDirectory() as root:
            store,parent=fixture(root);job=experiments.enqueue(store,parent,settings(store,parent,mode='staging',keep_ending=False));source,report=experiments.plan(FakeEngine(store),job['id'])
            original=json.loads((store.directory(parent['id'])/'editorial-source.json').read_text())
            self.assertTrue(report['controls']['keep_ending'])
            for before,after in zip(original['scenes'],source['scenes']):
                self.assertEqual(before['dialog'],after['dialog']);self.assertEqual(before['bubbles'][0]['text'],after['bubbles'][0]['text']);self.assertEqual(before['bubbles'][0]['speaker'],after['bubbles'][0]['speaker']);self.assertEqual(after['bubbles'][0]['bubble_style'],'thought');self.assertNotEqual(after['bubbles'][0]['x'],before['bubbles'][0]['x'])

    def test_large_experiments_use_bounded_chunks(self):
        with tempfile.TemporaryDirectory() as root:
            store,parent=fixture(root,13);job=experiments.enqueue(store,parent,settings(store,parent));engine=FakeEngine(store);source,report=experiments.plan(engine,job['id']);self.assertEqual(engine.sizes,[6,6,1]);self.assertEqual(len(source['scenes']),13)

    def test_invalid_controls_stale_version_and_parallel_duplicate_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            store,parent=fixture(root)
            with self.assertRaises(Conflict):experiments.enqueue(store,parent,settings(store,parent,version='veraltet'))
            with self.assertRaises(ValueError):experiments.controls({'levels':{**experiments.DEFAULTS,'anger':4}})
            with self.assertRaises(ValueError):experiments.controls({'count':99})
            with self.assertRaises(ValueError):experiments.controls({'levels':dict.fromkeys(experiments.DIRECTIONS,0),'notes':''})
            experiments.enqueue(store,parent,settings(store,parent))
            with self.assertRaises(Conflict):experiments.enqueue(store,parent,settings(store,parent))

    def test_rejected_review_blocks_rendering(self):
        with tempfile.TemporaryDirectory() as root:
            store,parent=fixture(root);job=experiments.enqueue(store,parent,settings(store,parent));engine=FakeEngine(store,True)
            with patch('editorial.render') as render:
                with self.assertRaisesRegex(ValueError,'dramaturgische Korrektur'):experiments.run(engine,job['id'])
                render.assert_not_called()

    def test_complete_branch_export_uses_only_own_job_and_preserves_parent(self):
        with tempfile.TemporaryDirectory() as root:
            store,parent=fixture(root);before=copy.deepcopy(parent);job=experiments.enqueue(store,parent,settings(store,parent));store.update(job['id'],status='running')
            png=(store.directory(parent['id'])/'panels/01_art.png').read_bytes();sessions=[]
            class Client:
                def request(self,method,path,data=None):
                    if path.endswith('check-plan'):return {'valid':True,'issues':[]}
                    raise AssertionError('Unerwarteter externer Aufruf: '+path)
                def run(self,ident,step,graph,workflow):
                    sessions.append(ident);node=next(k for k,v in graph.items() if v['class_type']=='DGXComicStudio');count=graph[node]['inputs']['anzahl_kacheln']
                    return {node:{'images':[{'filename':'comic.png'}],'comic_panels':[{'filename':f'{i+1:02}_panel.png'} for i in range(count)],'local_layout':True}}
                def download(self,*args):return png
            engine=FakeEngine(store);engine.client=Client()
            template=Path(__file__).resolve().parents[1]/'examples/comics/workflows/04_Comic_Automat_9B.json'
            with patch.dict('os.environ',{'WORKFLOW_TEMPLATE':str(template)}):result=experiments.run(engine,job['id'])
            self.assertEqual(result['status'],'needs_review');self.assertEqual(sessions,[job['id']]);self.assertTrue((store.directory(job['id'])/'comic-bundle.zip').is_file())
            report=json.loads((store.directory(job['id'])/'report.json').read_text());self.assertTrue(report['experimental']);self.assertTrue(report['fiction']);self.assertTrue(report['text_rewritten_by_local_llm'])
            self.assertEqual(store.get(parent['id']),before)
            self.assertTrue(any(a['name']=='experiment-report.json' for a in result['artifacts']))

    def test_authenticated_api_only_enqueues_a_new_branch(self):
        from app import Service,Handler
        with tempfile.TemporaryDirectory() as root:
            store,parent=fixture(root)
            with patch.object(Service,'__init__',lambda self:None):service=Service()
            service.store=store;service.stories=Stories(store);service.token='test';server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.service=service;thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def call(path,method='GET',data=None,auth=True):
                request=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Authorization':'Bearer test'} if auth else {})
                try:
                    with urllib.request.urlopen(request) as response:return response.status,json.load(response)
                except urllib.error.HTTPError as exc:return exc.code,json.load(exc)
            try:
                path='/jobs/'+parent['id'];self.assertEqual(call(path+'/experiment-options',auth=False)[0],401)
                code,info=call(path+'/experiment-options');self.assertEqual(code,200);self.assertEqual(info['count'],2)
                code,job=call(path+'/experiment','POST',{'version':info['version'],**info['settings']});self.assertEqual(code,202);self.assertTrue(job['experiment_mode'])
                self.assertEqual(store.get(parent['id']),parent);self.assertEqual(len(store.list()),2)
            finally:server.shutdown();server.server_close();thread.join()
