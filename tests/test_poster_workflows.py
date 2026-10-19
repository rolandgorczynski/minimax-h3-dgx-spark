"""Workflow contract: local model nodes, retained upload and valid links."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PosterWorkflowTests(unittest.TestCase):
    def test_templates_connect_local_models(self):
        for path in (ROOT/'examples/posters/workflows').glob('*.json'):
            with self.subTest(workflow=path.name):
                workflow = json.loads(path.read_text())
                nodes = {n['id']: n for n in workflow['nodes']}
                poster = next(n for n in nodes.values() if n['type'] == 'DGXPoster')
                links = {link[0]: link for link in workflow['links']}
                for field, node_type in [('model', 'UNETLoader'), ('clip', 'CLIPLoader'), ('vae', 'VAELoader')]:
                    port = next(i for i in poster['inputs'] if i['name'] == field)
                    link = links[port['link']]
                    self.assertEqual(nodes[link[1]]['type'], node_type)
                    self.assertEqual(poster['inputs'][link[4]]['name'], field)
                self.assertNotIn('DGXImageURL', [n['type'] for n in nodes.values()])
                if path.name.startswith('03_'):
                    self.assertEqual(nodes[6]['type'], 'LoadImage')
                    self.assertEqual(nodes[7]['type'], 'DGXDescribeImage')
