"""Persistent cast profiles, aliases, immutable references and per-story overrides."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image

SOURCE=Path(__file__).resolve().parents[1]/'extensions/dgx-comics/characters.py'
spec=importlib.util.spec_from_file_location('comic_characters', SOURCE)
characters=importlib.util.module_from_spec(spec);spec.loader.exec_module(characters)


class CharacterTests(unittest.TestCase):
    def profile(self):
        return {'name':'Markus','aliases':['Marcus'],'description':'17 Jahre, kurze braune Haare, schlank.',
                'outfit':'Grauer Hoodie','variants':{'Winter':'Blauer Mantel'},'references':[]}

    def test_library_survives_reload_and_story_edits_do_not_change_master(self):
        with tempfile.TemporaryDirectory() as folder:
            library=characters.CharacterLibrary(folder)
            saved=library.save(self.profile())
            cast=characters.read_cast(json.dumps([saved]))
            cast[0]['story_outfit']='Blauer Mantel'
            self.assertEqual(characters.CharacterLibrary(folder).list()[0],saved)
            self.assertIn('Blauer Mantel',characters.character_prompt(cast[0]))
            edited={**saved,'description':'17 Jahre, grüne Augen'}
            library.save(edited)
            self.assertEqual(cast[0]['description'],self.profile()['description'])
            with self.assertRaisesRegex(ValueError,'inzwischen'):
                library.save(edited)

    def test_reference_replacement_keeps_old_story_reference_available(self):
        with tempfile.TemporaryDirectory() as folder:
            library=characters.CharacterLibrary(folder);saved=library.save(self.profile())
            def png(color):
                stream=io.BytesIO();Image.new('RGB',(32,32),color).save(stream,format='PNG');return stream.getvalue()
            old=library.upload(saved['id'],png('red'),0)
            newer=library.upload(saved['id'],png('blue'),0)
            self.assertNotEqual(old['references'],newer['references'])
            self.assertTrue(library.reference_path(old['id'],old['references'][0]).exists())
            self.assertEqual(characters.CharacterLibrary(folder).list()[0],newer)
            with self.assertRaises(ValueError):library.reference_path(saved['id'],'../../secret')
            with self.assertRaises(ValueError):library.path('../bad')

    def test_aliases_match_same_character_but_not_other_names(self):
        p=self.profile();p['id']='a'*32
        cast=characters.read_cast([p])
        self.assertEqual(characters.scene_cast({'story':'Marcus steht auf der Treppe.'},cast),cast)
        self.assertEqual(characters.scene_cast({'story':'Markusson wartet.'},cast),[])
        self.assertEqual(characters.scene_cast({'story':'Markus wartet.','characters':[]},cast),[])
        self.assertEqual(characters.scene_cast({'story':'Treppe','characters':['a'*32]},cast),cast)
        with self.assertRaises(ValueError):characters.read_cast([p,p])

    def test_invalid_reference_and_incomplete_profiles_rejected(self):
        for change in [{'name':''},{'id':'../escape'},{'references':['/etc/passwd']},{'aliases':'Marcus'}]:
            with self.assertRaises(ValueError):characters.validate_character({**self.profile(),**change})

    def test_explicit_lines_keep_exact_words_and_canonical_speakers(self):
        source='Markus steht links neben dem Eingang. Markus: "Nein ! Nein !" Verbrecher: "Halt die Klappe Idiot"'
        lines=characters.explicit_speech(source)
        self.assertEqual([x['speaker'] for x in lines],['Markus','Verbrecher'])
        self.assertEqual([x['text'] for x in lines],['Nein ! Nein !','Halt die Klappe Idiot'])
        self.assertEqual(lines[0]['expression'],'shout')
        p=self.profile();p['id']='a'*32
        cast=characters.read_cast([p])
        self.assertEqual(characters.canonical_speaker('Marcus',cast),'a'*32)
        self.assertEqual(characters.scene_cast({'story':'Eingang','characters':[], 'bubbles':[{'speaker':'Marcus'}]},cast),cast)

    def test_sysop_is_seeded_once_with_reference_and_user_edits_survive(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'original.png'
            Image.new('RGB',(32,32),'red').save(source)
            lib=characters.CharacterLibrary(root/'library')
            other=lib.save(self.profile())
            sysop=lib.ensure_sysop(source)
            self.assertEqual(sysop['name'],'Sysop')
            self.assertEqual(len(sysop['references']),1)
            self.assertEqual(lib.ensure_sysop(source),sysop)
            self.assertEqual(len(lib.list()),2)
            edited=lib.save({**sysop,'description':'Mein eigener Sysop mit grünen Augen'})
            replacement=io.BytesIO();Image.new('RGB',(32,32),'blue').save(replacement,format='PNG')
            edited=lib.upload(edited['id'],replacement.getvalue(),0)
            self.assertEqual(lib.ensure_sysop(source),edited)
            self.assertTrue(lib.reference_path(sysop['id'],sysop['references'][0]).exists())
            self.assertIn(other,lib.list())

    def test_existing_sysop_alias_is_used_without_duplicate(self):
        with tempfile.TemporaryDirectory() as folder:
            lib=characters.CharacterLibrary(folder)
            original=lib.save({**self.profile(),'name':'Erzähler','aliases':['Sysop']})
            self.assertEqual(lib.ensure_sysop(),original)
            self.assertEqual(len(lib.list()),1)

    def test_delete_duplicate_keeps_other_entry_story_and_references(self):
        with tempfile.TemporaryDirectory() as folder:
            lib=characters.CharacterLibrary(folder)
            first=lib.save(self.profile());duplicate=lib.save(self.profile())
            data=io.BytesIO();Image.new('RGB',(32,32),'green').save(data,format='PNG')
            duplicate=lib.upload(duplicate['id'],data.getvalue(),0)
            snapshot=characters.read_cast([duplicate])
            lib.delete(duplicate['id'],duplicate['version'])
            self.assertEqual(lib.list(),[first])
            self.assertEqual(characters.read_cast(snapshot),snapshot)
            self.assertTrue(lib.reference_path(snapshot[0]['id'],snapshot[0]['references'][0]).exists())
            self.assertTrue((Path(folder)/'archived'/(duplicate['id']+'.json')).exists())
            with self.assertRaisesRegex(ValueError,'gelöscht'):lib.save(duplicate)
            with self.assertRaises(FileNotFoundError):lib.delete(duplicate['id'],duplicate['version'])

    def test_delete_rejects_stale_version_and_sysop_does_not_reappear(self):
        with tempfile.TemporaryDirectory() as folder:
            lib=characters.CharacterLibrary(folder)
            sysop=lib.ensure_sysop()
            edited=lib.save({**sysop,'outfit':'Blauer Mantel'})
            with self.assertRaisesRegex(ValueError,'inzwischen'):lib.delete(sysop['id'],sysop['version'])
            self.assertEqual(lib.list(),[edited])
            lib.delete(edited['id'],edited['version'])
            self.assertIsNone(lib.ensure_sysop())
            self.assertEqual(characters.CharacterLibrary(folder).list(),[])
            with self.assertRaises(ValueError):lib.delete('../bad',1)
