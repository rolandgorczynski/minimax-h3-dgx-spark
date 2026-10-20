"""Comic scene validation, optional dialogue, odd-sized grids and exact lettering."""
import importlib.util
import json
from pathlib import Path
import unittest
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
