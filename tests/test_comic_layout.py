"""Ein gemeinsames Layout erhält Erzählerporträt, Teilseiten und PDF."""
import base64
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]/'extensions/dgx-comics'
def load(name):
    spec=importlib.util.spec_from_file_location('test_layout_'+name,ROOT/(name+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
layout=load('editorial_layout');design=load('design')


class LayoutTests(unittest.TestCase):
    def test_detached_narrator_reference_survives_import_and_export(self):
        avatar=io.BytesIO();Image.new('RGB',(32,32),'red').save(avatar,format='PNG')
        source={'title':'Die Geschichte','scenes':[{}]*5,'narrator_badge':True,'narrator_character_id':'a'*32,'library_ids':[],
                'reference_overrides':{'a'*32:[base64.b64encode(avatar.getvalue()).decode()]}}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'panels').mkdir()
            for i in range(5):Image.new('RGB',(768,672),'white').save(root/f'panels/{i+1:02}_panel.png')
            Image.new('RGB',(768,672),'white').save(root/'comic.png')
            result=layout.render_layout(root,source,{'nodes':[]},design)
            self.assertEqual(result,{'panels':5,'pages':2})
            self.assertTrue((root/'pages/02.png').exists());self.assertTrue((root/'comic.pdf').read_bytes().startswith(b'%PDF'))
            with Image.open(root/'panels/01_panel.png') as tile:self.assertEqual(tile.getpixel((15,70)),(255,0,0))
            self.assertTrue(json.loads((root/'workflow.json').read_text())['extra']['editorial_layout']['narrator_badge'])


if __name__=='__main__':unittest.main()
