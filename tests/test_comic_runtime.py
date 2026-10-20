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
    def test_planning_boundary_and_selective_regeneration(self):
        ref=torch.zeros((1,32,32,3)); model=object(); clip=object(); vae=object()
        scenes=[{'story':'First distinct scene','dialog':'One'},{'story':'Second distinct scene','dialog':'Two'}]
        with tempfile.TemporaryDirectory() as d, patch.object(folder_paths,'get_output_directory',return_value=d), patch.object(g,'prepare_reference',return_value={}), patch.object(g,'generate_panel',return_value=torch.zeros((1,32,32,3))) as gen:
            def run(scenes,revisions=None):
                return m.DGXSysopComic().create(ref,model,clip,vae,2,2,'','Sysop','Noir',json.dumps(scenes),'',1984,'comics/test',revisions=revisions,reuse_panels=True)
            run(scenes); assert gen.call_count==2
            result=run(scenes); assert gen.call_count==2, 'Unchanged images were regenerated'
            scenes[0]['dialog']='Edited caption';run(scenes);assert gen.call_count==2,'Caption edit generated art'
            scenes[0]['story']='Changed first scene';run(scenes);assert gen.call_count==3,'Scene edit must change only one panel'
            run(scenes,{'1':1});assert gen.call_count==4,'Variant must change only selected panel'
            assert len(result['ui']['comic_panels'])==2
            print('PASS: repeat run, caption edit, scene edit, selected variant and previews')
        wf=m.DGXComicWorkflow()
        style=m.workflow.STYLES['Großstadt-Noir (düster)']
        from comic_test_extension.story import source_hash
        saved=json.dumps({'source_hash':source_hash('Article',2,1984,style),'scenes':scenes})
        with patch.object(m.workflow,'plan_story',return_value=(scenes,'fingerprint')) as plan, patch.object(m.DGXSysopComic,'create') as render:
            wf.run(ref,model,clip,vae,'Article','Großstadt-Noir (düster)',2,'Szenen planen','',2,'',1984)
            plan.assert_called_once();render.assert_not_called()
        with patch.object(m.workflow,'plan_story') as plan, patch.object(m.DGXSysopComic,'create',return_value={'ui':{},'result':(ref,)}) as render:
            wf.run(ref,model,clip,vae,'Article','Großstadt-Noir (düster)',2,'Comic generieren','',2,'',1984,saved)
            plan.assert_not_called();render.assert_called_once()
            try:
                wf.run(ref,model,clip,vae,'Changed article','Großstadt-Noir (düster)',2,'Comic generieren','',2,'',1984,saved)
                raise AssertionError('Stale plan accepted')
            except ValueError:pass
        print('PASS: planning generates no art, rendering never replans, stale plan rejected')

if __name__ == "__main__":
    unittest.main()
