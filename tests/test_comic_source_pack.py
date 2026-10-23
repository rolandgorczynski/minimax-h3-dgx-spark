"""Quellenpaket: zehn saubere Einträge und ergänzender Import ohne Datenverlust."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'automation/comics'))
from storage import Store
from source_generator import clean_source,BUILTINS
spec=importlib.util.spec_from_file_location('source_import',ROOT/'scripts/import_comic_sources.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class SourcePackTests(unittest.TestCase):
    def test_ten_distinct_sources_with_rights_and_grounded_adaptation(self):
        pack=module.read_pack(ROOT/'examples/comics/sources/germanische-heldensagen-10.json')
        self.assertEqual(len(pack['sources']),10)
        for source in pack['sources']:
            clean=clean_source(source)
            self.assertTrue(clean['url'].startswith('https://'))
            self.assertIn('Gemeinfreier',clean['rights'])
            for section in ('STOFF UND HERKUNFT:','HANDLUNGSGRUNDLAGE','SCHWERPUNKT DER COMIC-ADAPTION:','ABGRENZUNG:'):self.assertIn(section,clean['text'])
        self.assertEqual(len({s['title'] for s in pack['sources']}),10)

    def test_import_preserves_custom_sources_and_user_edits_on_repeat(self):
        pack=module.read_pack(ROOT/'examples/comics/sources/germanische-heldensagen-10.json')
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);existing=BUILTINS+[{'id':'meine-quelle','title':'Meine eigene Vorlage'}]
            store.integration_set('source-catalog',existing)
            def run(apply):
                output=io.StringIO()
                with patch('storage.Store',lambda path:store),patch('sys.stdin',io.StringIO(json.dumps({'pack':pack,'apply':apply}))),contextlib.redirect_stdout(output):exec(module.IMPORT_CODE,{})
                return json.loads(output.getvalue())
            preview=run(False);self.assertEqual(preview['neu'],10);self.assertEqual(store.integration_get('source-catalog'),existing)
            first=run(True);self.assertEqual(first['gesamt'],14);self.assertTrue(Path(first['sicherung']).is_file())
            saved=store.integration_get('source-catalog');saved[-1]['text']='Meine Änderung bleibt bestehen.';store.integration_set('source-catalog',saved)
            second=run(True);self.assertEqual(second['neu'],0);self.assertEqual(second['unveraendert'],10)
            self.assertEqual(store.integration_get('source-catalog'),saved);self.assertEqual(store.list(),[])

    def test_pack_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'bad.json';path.write_text(json.dumps({'schema_version':1,'id':'probe','title':'Probe','sources':[{'id':'gleich'},{'id':'gleich'}]}))
            with self.assertRaises(ValueError):module.read_pack(path)
