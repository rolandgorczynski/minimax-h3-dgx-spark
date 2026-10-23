"""Comic scene validation, optional dialogue, odd-sized grids and exact lettering."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from PIL import Image

SOURCE = Path(__file__).resolve().parents[1]/'extensions/dgx-comics/design.py'
spec = importlib.util.spec_from_file_location('comic_design', SOURCE)
design = importlib.util.module_from_spec(spec)
spec.loader.exec_module(design)


class ComicTests(unittest.TestCase):
    def test_only_visible_scenes_are_used_and_missing_scenes_fail(self):
        scenes = json.dumps([{'story': 'Sysop prüft Backups.', 'dialog': 'Zażółć gęślą jaźń.'},
                             {'story': 'Ausgeblendete Szene', 'dialog': ''}])
        self.assertEqual(len(design.parse_scenes(scenes, 1)), 1)
        with self.assertRaises(ValueError):
            design.parse_scenes(scenes, 3)
        with self.assertRaisesRegex(ValueError, 'Kachel 1'):
            design.parse_scenes('[{"story": ""}]', 1)
        for count in (0, 13):
            with self.assertRaises(ValueError):
                design.parse_scenes(scenes, count)

    def test_grid_dimensions_and_empty_last_cell(self):
        tiles = [design.panel(Image.new('RGB', (1024, 704), 'red'), '', i+1) for i in range(3)]
        image = design.assemble(tiles, 2, '', '')
        self.assertEqual(image.size, (1588, 1441))
        self.assertEqual(image.getpixel((1200, 1000)), (255, 255, 255))
        self.assertEqual(design.assemble(tiles[:1], 4, '', '').size, (808, 757))
        with self.assertRaises(ValueError):
            design.assemble(tiles, 0)

    def test_dialogue_is_optional_and_overflow_fails(self):
        art = Image.new('RGB', (1024, 704), 'red')
        with_dialogue = design.panel(art, 'Grüße aus Łódź!', 1)
        without_dialogue = design.panel(art, '', 1)
        self.assertEqual(with_dialogue.size, (768, 672))
        self.assertEqual(with_dialogue.getpixel((300, 50)), (255, 255, 255))
        self.assertEqual(without_dialogue.getpixel((300, 50)), (255, 0, 0))
        with self.assertRaisesRegex(ValueError, 'zu lang'):
            design.panel(art, 'W'*500, 1)

    def test_panel_character_states_survive_scene_parsing(self):
        scene={'story':'Eine Person sitzt am Fenster.','dialog':'','characters':['a'*32],'character_states':{'a'*32:'Kinnlanger Bob.'}}
        self.assertEqual(design.parse_scenes(json.dumps([scene]),1)[0]['character_states'],scene['character_states'])
        with self.assertRaises(ValueError):design.parse_scenes(json.dumps([{**scene,'character_states':{'falsch':'Bob'}}]),1)

    def test_multiple_bubbles_have_separate_speakers_and_movable_tails(self):
        art=Image.new('RGB',(1024,704),'#224466')
        bubbles=design.validate_bubbles([
            {'speaker':'a'*32,'text':'Nein! Nein!','expression':'shout'},
            {'speaker':'Verbrecher','text':'Halt die Klappe, Idiot!'}])
        with patch.object(design,'lettering',wraps=design.lettering) as draw:
            image=design.panel(art,'Erzählertext.',1,bubbles,{'a'*32:'Markus'})
            texts=[call.args[1] for call in draw.call_args_list]
            self.assertIn('Markus',texts)
            self.assertIn('Verbrecher',texts)
            self.assertIn('Nein! Nein!',texts)
            self.assertIn('Halt die Klappe, Idiot!',texts)
        moved=[{**bubbles[0],'tip_x':.1,'tip_y':.8},bubbles[1]]
        edited=design.panel(art,'Erzählertext.',1,moved,{'a'*32:'Markus'})
        self.assertNotEqual(image.tobytes(),edited.tobytes())
        scenes=design.parse_scenes(json.dumps([{'story':'Markus wartet.','dialog':'','bubbles':bubbles}]),1)
        self.assertEqual(scenes[0]['bubbles'],bubbles)

    def test_speech_and_narration_enforce_readable_font_minima(self):
        art=Image.new('RGB',(1024,704),'#224466')
        with patch.object(design,'lettering',wraps=design.lettering) as draw:
            design.panel(art,'Ein neuer Morgen.',1,[{'speaker':'a'*32,'text':'Guten Morgen!'}],{'a'*32:'Ria'})
            calls={call.args[1]:call.kwargs for call in draw.call_args_list}
            self.assertEqual(calls['Ein neuer Morgen.']['minimum'],24)
            self.assertEqual(calls['Guten Morgen!']['minimum'],22)
            self.assertEqual(calls['Ria']['minimum'],16)
        with patch.object(design,'lettering',wraps=design.lettering) as draw:
            design.panel(art,'',1,[{'speaker':'a'*32,'text':'Psst.','expression':'whisper'}],{'a'*32:'Ria'})
            self.assertEqual(next(call.kwargs['minimum'] for call in draw.call_args_list if call.args[1]=='Psst.'),20)
        with self.assertRaisesRegex(ValueError,'zu lang'):
            design.panel(art,'',1,[{'speaker':'a'*32,'text':'Dieser Text passt niemals in diese kleine Sprechblase. '*6}],{'a'*32:'Ria'})

    def test_invalid_bubbles_and_overflow_fail_before_generation(self):
        for bubble in [{'speaker':''},{'speaker':'Markus','x':float('nan')},
                       {'speaker':'Markus','x':.9,'w':.4}, {'speaker':'Markus','expression':'invalid'}]:
            with self.assertRaises(ValueError):design.validate_bubbles([bubble])
        with self.assertRaises(ValueError):design.validate_bubbles([{'speaker':'Markus'}]*7)
        with self.assertRaisesRegex(ValueError,'zu lang'):
            design.panel(Image.new('RGB',(1024,704)),'',1,[{'speaker':'Markus','text':'W'*400}])
