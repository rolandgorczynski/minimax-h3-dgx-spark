"""Runtime integration checks; run inside ComfyUI for selective render verification."""
import importlib.util, sys, tempfile, json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'/opt/ComfyUI')
import unittest
try:
    import torch
    import folder_paths
except ImportError:
    raise unittest.SkipTest('Requires ComfyUI runtime with torch')
p=Path(__file__).resolve().parents[1]/'extensions/dgx-comics'
if not p.exists():
    p=Path('/opt/ComfyUI/custom_nodes/dgx-comics')
spec=importlib.util.spec_from_file_location('comic_test_extension',p/'__init__.py',submodule_search_locations=[str(p)])
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
g=__import__('comic_test_extension.generation',fromlist=['generate_panel'])
class ComicRuntimeTests(unittest.TestCase):
    def test_sampling_uses_requested_latent_and_scheduler_dimensions(self):
        from types import SimpleNamespace
        clip=SimpleNamespace(tokenize=lambda text:text,encode_from_tokens_scheduled=lambda tokens:'conditioning')
        vae=SimpleNamespace(decode=lambda samples:'decoded')
        with patch.object(g.EmptyFlux2LatentImage,'execute',return_value=({'samples':'empty'},)) as latent, patch.object(g.Flux2Scheduler,'execute',return_value=('sigmas',)) as scheduler, patch.object(g.BasicGuider,'execute',return_value=('guider',)), patch.object(g.RandomNoise,'execute',return_value=('noise',)), patch.object(g.SamplerCustomAdvanced,'execute',return_value=({'samples':'sampled'},)), patch.object(g.comfy.samplers,'sampler_object',return_value='sampler'):
            self.assertEqual(g.generate_panel(object(),clip,vae,[],'Bild',1984,1408,448),'decoded')
            latent.assert_called_with(1408,448,1);scheduler.assert_called_with(4,1408,448)
            g.generate_panel(object(),clip,vae,[],'Bild',1984)
            latent.assert_called_with(1024,704,1);scheduler.assert_called_with(4,1024,704)

    def test_canvas_dimensions_reach_sampler_and_lettered_tile(self):
        from PIL import Image
        ref=torch.zeros((1,32,32,3))
        scene={'story':'Eine breite Landschaft.','dialog':'','characters':[],'bubbles':[],'canvas_size':[1280,384],'render_size':[1536,448]}
        from comic_test_extension.story import read_plan
        self.assertEqual(read_plan([scene],1)[0]['canvas_size'],[1280,384])
        with tempfile.TemporaryDirectory() as folder, patch.object(folder_paths,'get_output_directory',return_value=folder), patch.object(g,'generate_panel',return_value=torch.zeros((1,448,1536,3))) as sample:
            m.DGXSysopComic().create(ref,object(),object(),object(),1,1,'','','Tusche',json.dumps([scene]),'',1984,'canvas-test',cast=[],library_cast=True)
            self.assertEqual(sample.call_args.args[-2:],(1536,448))
            with Image.open(next(Path(folder).rglob('01_art.png'))) as art:self.assertEqual(art.size,(1536,448))
            with Image.open(next(Path(folder).rglob('01_panel.png'))) as tile:self.assertEqual(tile.size,(1280,384))

    def test_overflow_draft_survives_native_render_and_can_be_corrected(self):
        from PIL import Image
        from comic_test_extension.story import read_plan
        scene={'story':'Eine Tür.','dialog':'W'*390,'characters':[],'bubbles':[],'lettering_draft':True,'canvas_size':[1088,672]}
        self.assertTrue(read_plan([scene],1)[0]['lettering_draft'])
        with tempfile.TemporaryDirectory() as folder, patch.object(folder_paths,'get_output_directory',return_value=folder), patch.object(g,'generate_panel',return_value=torch.zeros((1,64,64,3))) as sample:
            m.DGXSysopComic().create(torch.zeros((1,32,32,3)),object(),object(),object(),1,1,'','','Tusche',json.dumps([scene]),'',1984,'draft-test',cast=[],library_cast=True)
            self.assertEqual(sample.call_count,1)
            with Image.open(next(Path(folder).rglob('01_panel.png'))) as tile:
                self.assertEqual(tile.size,(1088,672));self.assertEqual(tile.getpixel((10,640)),(255,223,138))

    def test_planning_boundary_and_selective_regeneration(self):
        ref=torch.zeros((1,32,32,3)); model=object(); clip=object(); vae=object()
        scenes=[{'story':'First distinct scene','dialog':'One'},{'story':'Second distinct scene','dialog':'Two'}]
        with tempfile.TemporaryDirectory() as d, patch.object(folder_paths,'get_output_directory',return_value=d), patch.object(g,'prepare_reference',return_value={}), patch.object(g,'generate_panel',return_value=torch.zeros((1,32,32,3))) as gen:
            def run(scenes,revisions=None):
                return m.DGXSysopComic().create(ref,model,clip,vae,2,2,'','Sysop','Noir',json.dumps(scenes),'',1984,'comics/test',revisions=revisions,reuse_panels=True)
            run(scenes); assert gen.call_count==2
            result=run(scenes); assert gen.call_count==2, 'Unchanged images were regenerated'
            scenes[0]['dialog']='Edited caption';run(scenes);assert gen.call_count==2,'Caption edit generated art'
            scenes[0]['bubbles']=[{'speaker':'Markus','text':'Nein! Nein!'}]
            run(scenes);self.assertEqual(gen.call_count,2)
            scenes[0]['bubbles'][0]['text']='Halt!'
            scenes[0]['bubbles'][0]['tip_x']=.2
            run(scenes);self.assertEqual(gen.call_count,2)

            scenes[0]['story']='Changed first scene';run(scenes);assert gen.call_count==3,'Scene edit must change only one panel'
            run(scenes,{'1':1});assert gen.call_count==4,'Variant must change only selected panel'
            assert len(result['ui']['comic_panels'])==2
            print('PASS: repeat run, caption edit, scene edit, selected variant and previews')
        wf=m.DGXComicWorkflow()
        style=m.workflow.STYLES['Großstadt-Noir (düster)']
        from comic_test_extension.story import source_hash, read_plan
        saved=json.dumps({'source_hash':source_hash('Article',2,1984,style),'scenes':scenes})
        with patch.object(m.workflow,'plan_story',return_value=(scenes,'fingerprint')) as plan, patch.object(m.DGXSysopComic,'create') as render:
            wf.run(ref,model,clip,vae,'Article','Großstadt-Noir (düster)',2,'Szenen planen','',2,'',1984)
            plan.assert_called_once();render.assert_not_called()
        with patch.object(m.workflow,'plan_story') as plan, patch.object(m.DGXSysopComic,'create',return_value={'ui':{},'result':(ref,)}) as render:
            wf.run(ref,model,clip,vae,'Article','Großstadt-Noir (düster)',2,'Comic generieren','',2,'',1984,saved)
            plan.assert_not_called();render.assert_called_once()
            wf.run(ref,model,clip,vae,'Article','Ligne claire',2,'Comic generieren','',2,'',1984,saved)
            plan.assert_not_called()
            self.assertEqual(render.call_args.args[8], m.workflow.STYLES['Ligne claire'])
            self.assertEqual(json.loads(render.call_args.args[9]), read_plan(scenes,2))

            try:
                wf.run(ref,model,clip,vae,'Changed article','Großstadt-Noir (düster)',2,'Comic generieren','',2,'',1984,saved)
                raise AssertionError('Stale plan accepted')
            except ValueError:pass
        print('PASS: planning generates no art, rendering never replans, stale plan rejected')

    def test_single_sword_rule_reaches_actual_image_prompt(self):
        from comic_test_extension.characters import CharacterLibrary
        with tempfile.TemporaryDirectory() as folder:
            lib=CharacterLibrary(Path(folder)/'library')
            char=lib.save({'name':'Hildebrand','description':'Älterer Krieger.','outfit':'Ein Schwert am Gürtel.'})
            scene={'story':'Hildebrand zieht sein einziges Schwert. Seine Scheide ist leer, kein zweiter Griff.','dialog':'','characters':[char['id']],'bubbles':[]}
            with patch('comic_test_extension.characters.library',return_value=lib),patch.object(folder_paths,'get_output_directory',return_value=str(Path(folder)/'output')),patch.object(g,'generate_panel',return_value=torch.zeros((1,32,32,3))) as sample:
                m.DGXSysopComic().create(torch.zeros((1,32,32,3)),object(),object(),object(),1,1,'','','Tusche',json.dumps([scene]),'',1984,'sword-test',cast=[char],library_cast=True)
                prompt=sample.call_args.args[4]
                self.assertIn('exactly ONE physical sword',prompt);self.assertIn('NO SECOND HILT',prompt);self.assertIn('Current scene and explicit physical state override default outfit placement',prompt)

    def test_cast_references_and_clothing_only_affect_assigned_panel(self):
        import io
        from PIL import Image
        from comic_test_extension.characters import CharacterLibrary
        with tempfile.TemporaryDirectory() as folder:
            lib=CharacterLibrary(Path(folder)/'library')
            char=lib.save({'name':'Markus','aliases':['Marcus'],'description':'17 years, short brown hair','outfit':'Grey hoodie'})
            for slot,color in enumerate(['red','blue']):
                image=io.BytesIO();Image.new('RGB',(32,32),color).save(image,format='PNG')
                char=lib.upload(char['id'],image.getvalue(),slot)
            cast=[char]
            scenes=[{'story':'Marcus stands on stairs.','dialog':''},{'story':'An empty hospital corridor.','dialog':''}]
            ref=torch.zeros((1,32,32,3));model=object();clip=object();vae=object()
            with patch('comic_test_extension.characters.library',return_value=lib), patch.object(folder_paths,'get_output_directory',return_value=str(Path(folder)/'output')), patch.object(g,'prepare_reference',return_value={'samples':ref}), patch.object(g,'generate_panel',return_value=torch.zeros((1,32,32,3))) as gen:
                def run():
                    return m.DGXSysopComic().create(ref,model,clip,vae,2,2,'','Sysop','Noir',json.dumps(scenes),'',1984,'comics/cast-test',reuse_panels=True,cast=cast)
                run()
                self.assertEqual(len(gen.call_args_list[0].args[3]),3)
                self.assertEqual(len(gen.call_args_list[1].args[3]),1)
                self.assertIn('17 years',gen.call_args_list[0].args[4])
                self.assertNotIn('17 years',gen.call_args_list[1].args[4])
                run();self.assertEqual(gen.call_count,2)
                cast[0]['story_outfit']='Blue winter coat'
                run();self.assertEqual(gen.call_count,3)
                self.assertIn('Blue winter coat',gen.call_args.args[4])
                self.assertEqual(lib.list()[0]['outfit'],'Grey hoodie')
                scenes[0]['characters']=[]
                run();self.assertEqual(gen.call_count,4)
                self.assertEqual(len(gen.call_args.args[3]),1)

    def test_retained_art_is_not_generated_and_panel_states_reach_prompt(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'retained-panels').mkdir()
            Image.new('RGB',(1024,704),'red').save(root/'retained-panels/01_art.png')
            cast=[{'id':'a'*32,'name':'Ria','aliases':[],'description':'Gleiches Gesicht.','outfit':'Umhang','references':[]}]
            scenes=[{'story':'Ria wartet.','dialog':'','characters':['a'*32]},
                    {'story':'Ria sieht in den Spiegel.','dialog':'','characters':['a'*32],'character_states':{'a'*32:'Kinnlanger Bob.'}}]
            with patch.object(g,'generate_panel',return_value=torch.zeros((1,32,32,3))) as generate:
                result=m.DGXSysopComic().create(None,object(),object(),object(),2,2,'','', 'Noir',json.dumps(scenes),'',42,'comic',
                    cast=cast,library_cast=True,output_directory=directory,image_type='temp',image_subfolder_prefix='comic-automation/test')
            self.assertEqual(generate.call_count,1)
            self.assertIn('Kinnlanger Bob.',generate.call_args.args[4])
            self.assertIn('reference hairstyle',generate.call_args.args[4])
            exported=next(root.glob('comic_*_panels/01_art.png'))
            with Image.open(exported) as picture:self.assertEqual(picture.getpixel((20,20)),(255,0,0))

    def test_planner_receives_cast_and_preserves_reviewed_scenes(self):
        from comfy_extras.nodes_textgen import TextGenerate
        from comic_test_extension.story import plan_story, source_hash
        cast=[{'id':'a'*32,'name':'Markus','aliases':['Marcus'],'description':'17 years, green eyes','outfit':'Grey hoodie','references':[]}]
        scenes=[{'story':'Marcus stands on stairs.','dialog':'Hallo.'}]
        with patch.object(TextGenerate,'execute',return_value=[json.dumps(scenes)]) as generate:
            result,fingerprint=plan_story(None,'Markus geht heim.',1,42,cast=cast)
            self.assertIn('17 years, green eyes',generate.call_args.args[1])
            self.assertIn('Marcus',generate.call_args.args[1])
            saved=json.dumps({'source_hash':fingerprint,'scenes':result})
            generate.reset_mock()
            self.assertEqual(plan_story(None,'Markus geht heim.',1,42,saved,cast=cast)[0],result)
            generate.assert_not_called()

    def test_planning_keeps_explicit_speakers_and_exact_quotes(self):
        from comfy_extras.nodes_textgen import TextGenerate
        from comic_test_extension.story import plan_story, read_plan
        cast=[{'id':'a'*32,'name':'Markus','aliases':['Marcus'],'description':'17 Jahre','outfit':'Hoodie','references':[]}]
        article='Markus steht neben dem Eingang. Markus: "Nein ! Nein !" Verbrecher: "Halt die Klappe Idiot"'
        output=[{'story':'Markus steht links, ein Mann rechts.','dialog':'','bubbles':[]}]
        with patch.object(TextGenerate,'execute',return_value=[json.dumps(output)]):
            scenes,_=plan_story(None,article,1,42,cast=cast)
        self.assertEqual(scenes[0]['bubbles'][0]['speaker'],'a'*32)
        self.assertEqual(scenes[0]['bubbles'][0]['text'],'Nein ! Nein !')
        self.assertEqual(scenes[0]['bubbles'][1]['speaker'],'Verbrecher')
        self.assertEqual(scenes[0]['bubbles'][1]['text'],'Halt die Klappe Idiot')
        self.assertEqual(read_plan(json.dumps(scenes),1),scenes)

    def test_library_sysop_uses_only_its_own_images_and_can_be_unassigned(self):
        import io
        from PIL import Image
        from comic_test_extension.characters import CharacterLibrary
        with tempfile.TemporaryDirectory() as folder:
            lib=CharacterLibrary(Path(folder)/'library')
            sysop=lib.ensure_sysop()
            stream=io.BytesIO();Image.new('RGB',(32,32),'green').save(stream,format='PNG')
            sysop=lib.upload(sysop['id'],stream.getvalue(),0)
            sysop=lib.save({**sysop,'description':'Custom Sysop with green eyes'})
            lib.delete(sysop['id'],sysop['version'])  # Saved stories must still render their retained reference.
            ref=torch.zeros((1,32,32,3));model=object();clip=object();vae=object()
            scenes=[{'story':'Sysop wartet.','dialog':'','characters':[sysop['id']]},
                    {'story':'Ein leerer Raum.','dialog':'','characters':[]}]
            with patch('comic_test_extension.characters.library',return_value=lib), patch.object(folder_paths,'get_output_directory',return_value=str(Path(folder)/'output')), patch.object(g,'prepare_reference',return_value={'samples':ref}) as prepare, patch.object(g,'generate_panel',return_value=torch.zeros((1,32,32,3))) as generate:
                m.DGXSysopComic().create(ref,model,clip,vae,2,2,'','Legacy appearance','Noir',json.dumps(scenes),'',42,'comics/sysop-test',cast=[sysop],library_cast=True)
                self.assertEqual(prepare.call_count,1)
                self.assertEqual(len(generate.call_args_list[0].args[3]),1)
                self.assertEqual(len(generate.call_args_list[1].args[3]),0)
                self.assertIn('Custom Sysop with green eyes',generate.call_args_list[0].args[4])
                self.assertNotIn('Legacy appearance',generate.call_args_list[0].args[4])
                self.assertNotIn('Custom Sysop with green eyes',generate.call_args_list[1].args[4])
                self.assertNotIn('Sysop',generate.call_args_list[1].args[4])
                self.assertNotIn('main character',generate.call_args_list[1].args[4])
                self.assertIn('architecture and objects',generate.call_args_list[1].args[4])

    def test_planner_uses_sysop_profile_instead_of_a_fixed_appearance(self):
        from comfy_extras.nodes_textgen import TextGenerate
        from comic_test_extension.story import plan_story
        cast=[{'id':'a'*32,'name':'Sysop','aliases':[],'description':'Short red hair, green eyes','outfit':'Blue jacket','references':[]}]
        with patch.object(TextGenerate,'execute',return_value=[json.dumps([{'story':'Sysop wartet.','dialog':''}])]) as generate:
            plan_story(None,'Sysop geht heim.',1,42,cast=cast)
            prompt=generate.call_args.args[1]
            self.assertIn('Short red hair, green eyes',prompt)
            self.assertNotIn('Sysop has shoulder-length',prompt)

    def test_studio_runs_without_a_shared_reference_image(self):
        from comic_test_extension.story import source_hash
        studio=m.DGXComicStudio()
        self.assertNotIn('referenz',studio.INPUT_TYPES()['required'])
        scenes=[{'story':'Ein leerer Raum.','dialog':''}]
        args=dict(model=object(),clip=object(),vae=object(),artikel='Artikel',comic_art='Ligne claire',anzahl_kacheln=1,aktion='Szenen planen',titel='',spalten=1,signatur='',seed=42)
        fingerprint=source_hash('Artikel',1,42)
        with patch.object(m.workflow,'plan_story',return_value=(scenes,fingerprint)):
            result=studio.run(**args)
        saved=result['ui']['comic_plan'][0]
        with patch.object(m.DGXSysopComic,'create',return_value={'ui':{},'result':(torch.zeros((1,1,1,3)),)}) as render:
            studio.run(**{**args,'aktion':'Comic generieren','bearbeiteter_plan':saved})
            self.assertIsNone(render.call_args.args[0])
            self.assertTrue(render.call_args.kwargs['library_cast'])

    def test_automation_output_and_embedded_references_do_not_touch_user_data(self):
        import io,base64
        from PIL import Image
        from comic_test_extension.automation import session_directory
        ref=torch.zeros((1,32,32,3));model=object();clip=object();vae=object()
        image=io.BytesIO();Image.new('RGB',(32,32),'orange').save(image,format='PNG')
        cast=[{'id':'a'*32,'name':'Aria','aliases':[],'description':'Green eyes','outfit':'Grey jacket','references':[],
               'inline_references':[base64.b64encode(image.getvalue()).decode()]}]
        scenes=[{'story':'Aria wartet.','dialog':'Hallo.','characters':['a'*32]}]
        with tempfile.TemporaryDirectory() as folder, patch.object(folder_paths,'get_temp_directory',return_value=folder), patch.object(folder_paths,'get_output_directory',side_effect=AssertionError('User output directory accessed')), patch('comic_test_extension.characters.library',side_effect=AssertionError('Shared library accessed')), patch.object(g,'prepare_reference',return_value={'samples':ref}), patch.object(g,'generate_panel',return_value=ref) as generate:
            session='b'*32;root=session_directory(session);root.mkdir(parents=True)
            result=m.DGXSysopComic().create(None,model,clip,vae,1,1,'','', 'Noir',json.dumps(scenes),'',42,'comic',cast=cast,library_cast=True,output_directory=str(root),image_type='temp',image_subfolder_prefix='comic-automation/'+session)
            self.assertEqual(len(generate.call_args.args[3]),1)
            descriptor=result['ui']['images'][0]
            self.assertEqual(descriptor['type'],'temp')
            self.assertEqual(descriptor['subfolder'],'comic-automation/'+session)
            self.assertTrue((root/descriptor['filename']).exists())
            with self.assertRaises(ValueError):session_directory('../outside')

if __name__ == "__main__":
    unittest.main()
