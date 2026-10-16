"""Layout contracts: print dimensions, user text, and validation."""
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'extensions/dgx-invitations/design.py'
spec = importlib.util.spec_from_file_location('invitation_design', SOURCE)
design = importlib.util.module_from_spec(spec)
spec.loader.exec_module(design)


class InvitationTests(unittest.TestCase):
    def values(self):
        return dict(veranstaltung='ZAŻÓŁĆ\nGĘŚLĄ', veranstalter='Prüfung · Łódź',
                    einladungstext='Für Freunde und Gäste', datum='5. Dezember 2026',
                    uhrzeit='18:30 Uhr', ort='Berlin', rueckmeldung='Bis bald!')

    def test_all_styles_have_print_dimensions(self):
        for style in design.PALETTES:
            with self.subTest(style=style):
                image = design.render_card(**self.values(), stil=style)
                self.assertEqual(image.size, (1748, 2480))
                self.assertEqual(image.mode, 'RGB')

    def test_long_text_is_rejected_instead_of_clipped(self):
        values = self.values()
        values['veranstaltung'] = 'W' * 250
        with self.assertRaisesRegex(ValueError, 'zu lang'):
            design.render_card(**values)

    def test_invalid_color_and_empty_title_explain_error(self):
        with self.assertRaisesRegex(ValueError, 'Hex-Code'):
            design.render_card(**self.values(), akzentfarbe='gold')
        values = self.values()
        values['veranstaltung'] = ' '
        with self.assertRaisesRegex(ValueError, 'Veranstaltungstitel'):
            design.render_card(**values)
