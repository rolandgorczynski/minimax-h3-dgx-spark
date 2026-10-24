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
    validate_scenes=Engine.validate_scenes
    def __init__(self,store,fail_review=False):self.store=store;self.calls=[];self.sizes=[];self.fail_review=fail_review
    def json_call(self,ident,step,prompt,validator,tokens,images=None):
        self.calls.append(step)
        if step.startswith('experiment-direction-'):
            if step.endswith('vision'):assert images and images[0].startswith(b'\xff\xd8')
            slots=json.loads(prompt.split('BEATRASTER:\n')[-1]);return validator({'core':'Eine Tür und eine Entscheidung.','emotion':'Ria überwindet ihre Angst.','goal':'Ria will die Tür öffnen.','stakes':'Sie verliert die letzte Gelegenheit.','obstacle':'Die Tür ist schwer zu bewegen.','choice':'Ria riskiert ihren sicheren Rückweg.','turning_point':'Ria entscheidet sich zu handeln.','visual_rhythm':'Erst Stille, dann eine dynamische Bewegung.','continuity':'Die Tür bleibt nach dem Öffnen offen.','ending':'Ria öffnet wie zuvor die Tür.','beats':[{**slot,'event':'Ria muss an dieser Stelle eine konkrete Entscheidung treffen.','change':'Ihr Wissen über die Tür ändert sich sichtbar.'} for slot in slots]})
        if step.startswith('experiment-locked-text-alignment-'):
            original=json.JSONDecoder().raw_decode(prompt.split('KACHELN MIT FESTEN TEXTEN:')[1].lstrip())[0];numbers=json.JSONDecoder().raw_decode(prompt.split('FESTE KACHELNUMMERN:')[1].lstrip())[0]
            return validator([{'panel':number,'story':'Tiefe Froschperspektive: Ria hält inne und betrachtet die Tür.','character_states':s.get('character_states',{})} for number,s in zip(numbers,original)])
        if 'review' in step:
            panel=int(re.search(r'GEPRÜFTER ABSCHNITT (\d+)',prompt)[1]);return validator({'issues':[{'panel':panel,'kind':'sequence','message':'Der dargestellte Handlungsanschluss widerspricht der vorigen Szene.','image_quote':'Ria hält inne'}] if self.fail_review else [],'suggestions':[]})
        start,end,count=map(int,re.search(r'für Position (\d+) bis (\d+) von insgesamt (\d+)',prompt).groups());self.sizes.append(end-start+1)
        return validator([{'heading':'Neue Szene '+str(i),'story':'Tiefe Froschperspektive: Ria hält inne und entscheidet sich, die schwere Tür aufzustoßen. Bildmoment '+str(i),'dialog':'Ein Moment verändert alles.','characters':[WHO],'bubbles':[{'speaker':WHO,'text':'Ich entscheide mich jetzt.','expression':'shout','bubble_style':'burst'}],'character_states':{},'dramatic_change':'Ria verlässt ihren sicheren Standpunkt.','visual_device':'Nahaufnahme ihrer entschlossenen Hand.','reason':'Aus passivem Warten wird eine sichtbare Entscheidung.'} for i in range(start,end+1)])
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

    def test_storytelling_profiles_and_beat_ranges_are_real_planning_constraints(self):
        from narrative_profiles import beat_slots,profile_prompt
        for count in (1,2,3,4,5,6,12,13,1001):
            slots=beat_slots(count)
            self.assertEqual([i for s in slots for i in range(s['start'],s['end']+1)],list(range(1,count+1)))
        self.assertEqual(experiments.controls({'narrative_profile':'asterix','levels':dict.fromkeys(experiments.DIRECTIONS,0)})['narrative_profile'],'asterix')
        prompt=profile_prompt('batman');self.assertIn('Hinweis',prompt);self.assertNotIn('Batman',prompt)
        with self.assertRaises(ValueError):experiments.controls({'narrative_profile':'unbekannt'})
        with tempfile.TemporaryDirectory() as root:
            store,parent=fixture(root);job=experiments.enqueue(store,parent,settings(store,parent,narrative_profile='one_piece'));source,report=experiments.plan(FakeEngine(store),job['id'])
            self.assertIn('One Piece',report['narrative_profile']['label']);self.assertEqual(len(report['direction']['beats']),2)
            self.assertTrue(all(s['dramatic_change'] and s['visual_device'] for s in source['scenes']))

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
                with self.assertRaisesRegex(ValueError,'belegten Widerspruch'):experiments.run(engine,job['id'])
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

    def test_failed_experiment_retries_from_its_original_with_preserved_controls(self):
        with tempfile.TemporaryDirectory() as root:
            store,parent=fixture(root);selected=settings(store,parent,mode='staging',narrative_profile='batman',notes='Meine Regie behalten.');failed=experiments.enqueue(store,parent,selected);store.update(failed['id'],status='failed')
            info=experiments.options(store,store.get(failed['id']))
            self.assertEqual(info['parent_job'],parent['id']);self.assertEqual(info['retry_of'],failed['id']);self.assertEqual(info['settings']['notes'],'Meine Regie behalten.');self.assertEqual(info['settings']['mode'],'staging')
            self.assertEqual(info['version'],experiments.options(store,parent)['version']);self.assertEqual(store.get(parent['id']),parent)
            retry=experiments.enqueue(store,parent,{'version':info['version'],**info['settings']})
            self.assertNotEqual(retry['id'],failed['id']);self.assertEqual(retry['parent_job'],parent['id'])

    def test_stylistic_advice_and_silent_visible_figures_do_not_block(self):
        from experiment_review import validate_review
        scenes=[{'story':'Siegfried und der Lindwurm stehen in der Höhle.','dialog':'Vor ihm steht der Lindwurm.','characters':[WHO],'bubbles':[],'character_states':{}}]
        result=validate_review({'issues':[{'panel':1,'kind':'redundancy','message':'Der Erzähler benennt das sichtbare Wesen.'},{'panel':1,'kind':'missing_annotation','message':'Kleidung ist nicht eigens wiederholt.'},{'panel':1,'kind':'speaker','message':'Der Lindwurm hat keine Sprechblase.'}],'suggestions':[]},scenes,0)
        self.assertTrue(result['approved']);self.assertEqual(len(result['suggestions']),3)

    def test_locked_alignment_keeps_saved_states_even_if_model_adds_unrequested_metadata(self):
        from experiment_review import align_locked_texts
        scene={'story':'Der Kampf läuft.','dialog':'Der Gegner ist bezwungen.','characters':[WHO],'bubbles':[],'character_states':{WHO:'Gelbe Jacke.'}}
        self_test=self
        class AlignEngine:
            validate_scenes=Engine.validate_scenes
            def json_call(self,ident,step,prompt,validator,tokens):
                self_test.assertNotIn('Der Kampf läuft.',prompt)
                self_test.assertIn('Ria hat den Gegner bezwungen.',prompt)
                self_test.assertIn('genau EINEN gleichzeitigen Moment',prompt)
                return validator([{'panel':1,'story':'Ria steht vor dem besiegten Gegner.','character_states':{'Ria':{'kleidung':'Geänderte, nicht angeforderte Kleidung.'}}}])
        result=align_locked_texts(AlignEngine(),'f'*32,[scene],0,[{'id':WHO,'name':'Ria'}],[{**scene,'story':'Ria hat den Gegner bezwungen.'}])
        self.assertEqual(result[0]['character_states'],scene['character_states']);self.assertEqual(result[0]['dialog'],scene['dialog']);self.assertIn('besiegten',result[0]['story'])

    def test_actual_image_text_conflict_is_targeted_and_fixed_text_is_preserved(self):
        from experiment_review import validate_review,repair_staging
        scenes=[{'story':'Siegfried steht ruhig.','dialog':'Er wartet.','characters':[WHO],'bubbles':[]},
                {'story':'Der Lindwurm stürzt sich auf Siegfried.','dialog':'Er hat den Lindwurm bezwungen.','characters':[WHO],'bubbles':[],'character_states':{}}]
        before=copy.deepcopy(scenes)
        result=validate_review({'issues':[{'panel':5,'kind':'image_text_conflict','message':'Kampf läuft im Bild noch, der Erzähler beschreibt bereits den Sieg.','image_quote':'stürzt sich auf Siegfried','text_quote':'den Lindwurm bezwungen'}],'suggestions':['Der feste Erzählertext könnte kürzer sein.']},scenes,3)
        self.assertFalse(result['approved'])
        class RepairEngine:
            validate_scenes=Engine.validate_scenes
            def json_call(self,ident,step,prompt,validator,tokens):
                self_test.assertEqual(step,'experiment-locked-image-repair-5');self_test.assertIn('Er hat den Lindwurm bezwungen.',prompt)
                return validator({'story':'Der besiegte Lindwurm liegt reglos. Siegfried steht über ihm.','character_states':{}})
        self_test=self
        repaired=repair_staging(RepairEngine(),'f'*32,scenes,3,result['issues'],[{'id':WHO,'name':'Siegfried'}])
        self.assertEqual(repaired[0],before[0]);self.assertEqual(repaired[1]['dialog'],before[1]['dialog']);self.assertEqual(repaired[1]['bubbles'],before[1]['bubbles']);self.assertIn('reglos',repaired[1]['story']);self.assertEqual(scenes,before)
        unproven=validate_review({'issues':[{'panel':5,'kind':'image_text_conflict','message':'Erfundener Befund.','image_quote':'Nicht im Bildtext','text_quote':'den Lindwurm bezwungen'}]},scenes,3)
        self.assertTrue(unproven['approved']);self.assertIn('Unbelegter Prüfhinweis',unproven['suggestions'][0])

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
