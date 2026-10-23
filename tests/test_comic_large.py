"""Mehr als zwölf Kacheln: kleine Modellaufträge, vollständige Daten und Zahlensortierung."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
from engine import Engine,validate_request
from storage import Store
from comfy import Comfy
import sharing
from article_plan import prepare
from stories import Stories

ROOT=Path(__file__).resolve().parents[1]


class LargeComicTests(unittest.TestCase):
    def test_no_fixed_count_cap_and_numeric_sharing_after_99(self):
        self.assertEqual(validate_request({'kacheln':1001})['kacheln'],1001)
        for count in (0,-1,True,1.5):
            with self.assertRaises(ValueError):validate_request({'kacheln':count})
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);ident='a'*32;store.create(ident,validate_request({'kacheln':101}));store.stage(ident,'finished',status='needs_review',artifacts=[{'name':f'panels/{i:02}_panel.png'} for i in range(101,0,-1)])
            names=sharing.image_sources(store.get(ident));self.assertEqual(names[9],'panels/10_panel.png');self.assertEqual(names[99],'panels/100_panel.png')
            info=sharing.manifest(store,store.get(ident));self.assertEqual(info['images'][0]['name'],'001.png');self.assertTrue(info['images'][99]['url'].endswith('/100.png'))

    def test_large_render_only_submits_single_panel_graphs(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);ident='b'*32;store.create(ident,validate_request({'kacheln':13}));calls=[];buffer=io.BytesIO();Image.new('RGB',(1024,704),'blue').save(buffer,format='PNG');pixels=buffer.getvalue()
            class Client(Comfy):
                def run(self,job,step,graph,workflow):
                    node=next(k for k,v in graph.items() if v['class_type']=='DGXComicStudio');calls.append(graph[node]['inputs'])
                    return {node:{'comic_panels':[{'filename':'01_panel.png','subfolder':'comic-automation/'+job,'type':'temp'}]}}
                def request(self,method,path,*args,**kwargs):
                    if path.startswith('/view?'):return pixels
                    raise AssertionError(path)
            client=Client('http://localhost',store);engine=Engine(store,client,ROOT/'examples/comics/workflows/04_Comic_Automat_9B.json','unused','unused')
            scene={'story':'Ein Raum.','dialog':'','characters':[],'bubbles':[]}
            result=engine.studio(ident,'test',{'title':'Langer Comic','story':'Eine vollständige Geschichte.'},[],{'scenes':[copy.deepcopy(scene) for _ in range(13)]})
            self.assertEqual(len(calls),13);self.assertTrue(all(c['anzahl_kacheln']==1 for c in calls));self.assertEqual(len(result['comic_panels']),13)
            self.assertTrue((store.directory(ident)/'panels/13_art.png').exists());self.assertEqual(client.download(ident,result['comic_panels'][12]),(store.directory(ident)/'panels/13_panel.png').read_bytes())
            with Image.open(store.directory(ident)/'comic.png') as im:self.assertLess(im.height,4000)
            from lettering import DESIGN
            DESIGN.panel(Image.new('RGB',(1024,704),'blue'),'Ein langer Comic.',10001,[])
            engine.finish(ident,store.get(ident)['request'],{'title':'Langer Comic','story':'Eine vollständige Geschichte.'},[],{'scenes':[copy.deepcopy(scene) for _ in range(13)]},{},{},[],0)
            self.assertTrue((store.directory(ident)/'pages/04.png').exists());self.assertTrue((store.directory(ident)/'comic.pdf').exists())
            with Image.open(store.directory(ident)/'panels/13_panel.png') as im:self.assertNotIn('workflow',im.info)
            with self.assertRaises(Exception):client.download(ident,{'local_path':'../../etc/passwd'})

    def test_article_planning_works_in_small_batches(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);stories=Stories(store);story=stories.save({'mode':'editorial','name':'Lang','payload':{'style':'Großstadt-Noir (düster)','article':'\n\n'.join('Ria geht durch Raum '+str(i)+'.' for i in range(80)),'panel_count':25,'scenes':[]}});job=stories.plan(story['id'],1);sizes=[]
            class FakeEngine:
                validate_scenes=Engine.validate_scenes
                def __init__(self):self.store=store
                def json_call(self,ident,step,prompt,validator,tokens):
                    if step=='article-people':return validator({'characters':[{'name':'Ria','description':'Erwachsene Frau.','outfit':'Jacke'}]})
                    group=json.JSONDecoder().raw_decode(prompt.split('QUELLABSCHNITTE:')[1].lstrip())[0];sizes.append(len(group))
                    people=json.JSONDecoder().raw_decode(prompt.split('FIGUREN:\n')[1].lstrip())[0]
                    return validator([{'story':g['source_excerpt'],'dialog':'','characters':[people[0]['id']]} for g in group])
                def preflight(self,*args):return {'valid':True,'issues':[]}
            prepare(FakeEngine(),stories,job['id']);saved=stories.get(story['id'])['payload'];self.assertEqual(len(saved['scenes']),25);self.assertEqual(sizes,[8,8,8,1]);self.assertEqual(saved['scenes'][-1]['source_end'],len(saved['article']))
