"""Story-plan JSON validation and preservation of user edits without model inference."""
import importlib.util
import json
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'extensions/dgx-comics/story.py'
spec = importlib.util.spec_from_file_location('comic_story', SOURCE)
story = importlib.util.module_from_spec(spec)
spec.loader.exec_module(story)


class ComicStoryTests(unittest.TestCase):
    def test_plan_parses_fences_and_thinking_but_requires_exact_count(self):
        value = '<think>Ignore this reasoning.</think>\n```json\n[{"story":"Sysop prüft ein Backup.","dialog":"Alles gut."}]\n```'
        self.assertEqual(story.read_plan(value, 1)[0]['dialog'], 'Alles gut.')
        with self.assertRaisesRegex(ValueError, 'genau 2'):
            story.read_plan(value, 2)
        with self.assertRaises(ValueError):
            story.read_plan('[{"story":""}]', 1)
        with self.assertRaises(ValueError):
            story.read_plan('[{"story":"Szene","dialog":5}]', 1)

    def test_manual_edits_bypass_language_model(self):
        scenes = [{'story': 'Sysop winkt.', 'dialog': 'Eigener Text.'}]
        fingerprint = story.source_hash('Die Geschichte', 1, 42)
        edited = json.dumps({'source_hash': fingerprint, 'scenes': scenes})
        result, returned = story.plan_story(None, 'Die Geschichte', 1, 42, edited)
        self.assertEqual(result, scenes)
        self.assertEqual(returned, fingerprint)
        self.assertNotEqual(fingerprint, story.source_hash('Neue Geschichte', 1, 42))
        self.assertNotEqual(fingerprint, story.source_hash('Die Geschichte', 2, 42))

    def test_style_is_part_of_saved_plan_identity(self):
        article = 'Ein Artikel mit offenen Fragen.'
        style = story.STYLES['Großstadt-Noir (düster)']
        fingerprint = story.source_hash(article, 1, 42, style)
        self.assertNotEqual(fingerprint, story.source_hash(article, 1, 42))
        self.assertNotEqual(fingerprint, story.source_hash(article, 1, 42, story.STYLES['Ligne claire']))
        scenes = [{'story': 'Korrigierte Szene.', 'dialog': 'Offene Frage?'}]
        edited = json.dumps({'source_hash': fingerprint, 'scenes': scenes})
        self.assertEqual(story.plan_story(None, article, 1, 42, edited, style), (scenes, fingerprint))

    def test_source_sections_cover_complete_article_in_order(self):
        article = (SOURCE.parents[2]/'examples/comics/articles/marius-dick.txt').read_text()
        sections = story.source_sections(article, 12)
        self.assertEqual(len(sections), 12)
        self.assertEqual(' '.join(' '.join(sections).split()), ' '.join(article.split()))
        self.assertIn('Familie Dick', sections[-1])
        self.assertTrue(all(part.strip() for part in sections))
        self.assertEqual(story.source_sections('Kurze Geschichte.', 12), [])

    def test_invalid_edit_is_not_silently_discarded(self):
        with self.assertRaisesRegex(ValueError, 'bearbeitete'):
            story.plan_story(None, 'Geschichte', 1, 42, '{bad json')
        with self.assertRaises(ValueError):
            story.plan_story(None, '', 1, 42)
