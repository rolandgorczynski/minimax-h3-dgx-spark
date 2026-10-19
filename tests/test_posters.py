"""Verify exact Polish text composition, optional footer and invalid inputs."""
import importlib.util
from pathlib import Path
import unittest
from PIL import Image

SOURCE = Path(__file__).resolve().parents[1]/'extensions/dgx-posters/design.py'
spec = importlib.util.spec_from_file_location('poster_design', SOURCE)
design = importlib.util.module_from_spec(spec)
spec.loader.exec_module(design)


class PosterTests(unittest.TestCase):
    def values(self):
        return dict(organizer='Rada Kobiet Gminy Mirsk', title='ZAŻÓŁĆ GĘŚLĄ JAŹŃ',
                    topics='Pierwsza pomoc\nMałgorzata Kubś i Wioleta Chylińska',
                    event_date='2026-10-26', hours='16:00–20:00', place='Mirsk · Wodna 2',
                    illustration=Image.new('RGB', (1792, 1024), 'green'))

    def test_facebook_dimensions_with_and_without_footer(self):
        for footer in (None, Image.new('RGBA', (1000, 100), 'red')):
            result = design.compose(**self.values(), footer=footer)
            self.assertEqual(result.size, (1080, 1350))
            self.assertEqual(result.mode, 'RGB')
            self.assertEqual(result.getpixel((500, 1300)), (255, 0, 0) if footer else (16, 39, 66))

    def test_invalid_date_and_overlong_text_fail(self):
        values = self.values()
        values['event_date'] = '2026-02-30'
        with self.assertRaises(ValueError):
            design.compose(**values)
        values = self.values()
        values['title'] = 'W'*200
        with self.assertRaisesRegex(ValueError, 'Za długi'):
            design.compose(**values)

    def test_date_weekday_is_calculated(self):
        captured = []
        original = design.text
        def record(draw, value, *args, **kwargs):
            captured.append(value)
            return original(draw, value, *args, **kwargs)
        design.text = record
        try:
            design.compose(**self.values())
        finally:
            design.text = original
        self.assertTrue(any('poniedziałek' in value for value in captured))

    def test_original_branding_is_placed_without_cropping(self):
        crest = Image.new('RGB', (600, 200), 'blue')
        footer = Image.new('RGB', (1200, 100), 'red')
        result = design.compose(**self.values(), crest=crest, footer=footer)
        self.assertEqual(result.getpixel((1000, 160)), (0, 0, 255))
        self.assertEqual(result.getpixel((500, 1320)), (255, 0, 0))
        plain = design.compose(**self.values())
        self.assertEqual(plain.getpixel((1000, 160)), (248, 245, 238))
        self.assertEqual(plain.getpixel((500, 1320)), (16, 39, 66))
