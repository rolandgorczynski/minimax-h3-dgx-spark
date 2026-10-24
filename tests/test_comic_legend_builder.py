"""Offline-Import historischer Sagen: Vollständigkeit, Lizenz und keine Platzhalter."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('legend_builder',ROOT/'scripts/build_comic_legend_pack.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


class LegendBuilderTests(unittest.TestCase):
    def archive(self,folder,license_url='https://creativecommons.org/licenses/by/3.0/de/'):
        path=Path(folder)/'texte.zip'
        text='Ein Wanderer fand am Abend einen verborgenen Eingang. '*12
        xml=f'''<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc><titleStmt><title>12. Der verborgene Eingang</title></titleStmt><publicationStmt><idno type="TextGridUri">textgrid:probe.0</idno><availability><ref target="{license_url}"/></availability></publicationStmt></fileDesc></teiHeader><text><body><div><head>12. Der verborgene Eingang</head><p>{text}<note>EDITORISCHE NOTIZ</note> Er kehrte vor Tagesanbruch zurück.</p></div></body></text></TEI>'''
        with zipfile.ZipFile(path,'w') as z:z.writestr('probe.xml',xml)
        return path

    def test_complete_story_and_provenance_without_editorial_note(self):
        with tempfile.TemporaryDirectory() as folder:
            path=self.archive(folder)
            first,report=builder.build(path,[],4)
            self.assertEqual(first,builder.build(path,[],4)[0])
            self.assertEqual(report['added'],1)
            source=first['sources'][0]
            self.assertEqual(source['id'],'bechstein-sagen-probe-0')
            self.assertIn('Er kehrte vor Tagesanbruch zurück.',source['text'])
            self.assertNotIn('EDITORISCHE NOTIZ',source['text'])
            self.assertIn('TextGrid',source['rights'])
            self.assertEqual(len(report['archive_sha256']),64)

    def test_missing_stories_never_filled_with_placeholders(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'nicht mit Platzhaltern'):
                builder.build(self.archive(folder),[],5)

    def test_unreviewed_transcription_license_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'Transkriptionslizenz'):
                builder.collect(self.archive(folder,'https://example.invalid/nicht-kommerziell'))

    def test_shipped_catalog_has_exactly_one_thousand_distinct_entries(self):
        sources=[]
        for p in (ROOT/'examples/comics/sources').glob('*.json'):
            sources.extend(json.loads(p.read_text())['sources'])
        self.assertEqual(len(sources)+3,1000)
        self.assertEqual(len({x['id'] for x in sources}),len(sources))
        titles=[builder.normalized(x['title']) for x in sources]
        self.assertEqual(len(set(titles)),len(titles))
        new=json.loads((ROOT/'examples/comics/sources/bechstein-sagen-bis-1000.json').read_text())['sources']
        self.assertEqual(len(new),927)
        for source in new:
            self.assertLessEqual(len(source['text']),16000)
            self.assertLessEqual(len(source['post_summary']),1200)
            self.assertLessEqual(len(source['title']),200)
            self.assertIn('HISTORISCHER ORIGINALTEXT',source['text'])
