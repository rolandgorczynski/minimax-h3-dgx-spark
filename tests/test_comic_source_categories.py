"""Kategorien: alte Daten erhalten, eigene Zuordnung speichern, alle Quellen erfassen."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'automation/comics'))
from source_categories import CATEGORIES,category,collection
from source_generator import BUILTINS,catalog,clean_source,save_source
from storage import Store


class SourceCategoryTests(unittest.TestCase):
    def test_classifying_old_catalog_does_not_write_or_mutate_it(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);original=copy.deepcopy(BUILTINS)
            store.integration_set('source-catalog',original)
            entries=catalog(store)
            self.assertEqual(store.integration_get('source-catalog'),original)
            self.assertTrue(all(e['category'] and e['collection'] for e in entries))
            self.assertEqual(entries[1]['category'],'Fabeln und Tiergeschichten')
            self.assertEqual(BUILTINS,original)

    def test_user_category_survives_reloads_and_other_entries_remain_identical(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);store.integration_set('source-catalog',copy.deepcopy(BUILTINS))
            entry=catalog(store)[0]
            entry.update(category='Meine poetischen Geschichten',text='Meine Textänderung.')
            saved=save_source(store,entry)
            self.assertEqual(saved['category'],'Meine poetischen Geschichten')
            self.assertEqual(catalog(Store(root))[0]['category'],saved['category'])
            self.assertEqual(store.integration_get('source-catalog')[1:],BUILTINS[1:])
            self.assertEqual(catalog(store)[0]['text'],'Meine Textänderung.')
            saved['category']=''
            self.assertEqual(save_source(store,saved)['category'],'Märchen und Verwandlungen')

    def test_all_shipped_sources_have_a_known_category_and_collection(self):
        entries=copy.deepcopy(BUILTINS)
        for path in (ROOT/'examples/comics/sources').glob('*.json'):
            entries+=json.loads(path.read_text())['sources']
        for entry in entries:
            self.assertIn(category(entry),CATEGORIES,entry['title'])
            self.assertTrue(collection(entry),entry['title'])
        self.assertEqual(category({'id':'bechstein-sagen-probe','title':'Das verlassene Haus','text':'Ein Gespenst erscheint. Das Gespenst verschwindet.'}),'Geister und Spuk')
        # Allgemeine Regiehinweise dürfen keine Kategorisierung vortäuschen.
        self.assertEqual(category({'id':'bechstein-sagen-probe','title':'Die Anhöhe','text':'HANDLUNGSGRUNDLAGE:\nEine Wiese liegt im Tal.\nSCHWERPUNKT DER COMIC-ADAPTION: Teufel Teufel Drache'}),'Regionale Sagen')

    def test_category_validation(self):
        with self.assertRaisesRegex(ValueError,'category: maximal 120'):
            clean_source({**BUILTINS[0],'category':'x'*121})
        with self.assertRaises(ValueError):clean_source({**BUILTINS[0],'category':['Spuk']})
