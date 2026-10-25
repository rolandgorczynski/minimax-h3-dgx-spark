"""Abschluss und Lösch-Schutz nur mit kleinen Testdaten prüfen."""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
finish=load('finish','finish_docker_backup_setup.py')
cleanup=load('cleanup','cleanup_old_comic_data.py')


class FinalizationTests(unittest.TestCase):
    def test_failed_backup_blocks_all_setup_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'status.json').write_text('{"phase":"fehler","verified":false,"error":"Testfehler"}')
            with patch.object(finish.subprocess,'run') as run:
                with self.assertRaisesRegex(RuntimeError,'Testfehler'):finish.check_success({'state_root':tmp})
                run.assert_not_called()

    def test_success_requires_matching_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);state=root/'state';state.mkdir();snap=root/'snap/weekly.0';snap.mkdir(parents=True)
            (state/'status.json').write_text('{"phase":"fertig","verified":true,"started":"2026-10-25T12:33:00+01:00"}')
            frozen=snap/'localhost'/str(state).lstrip('/')/'export/dienstzustand.json';frozen.parent.mkdir(parents=True)
            frozen.write_text('{"started":"another-run"}')
            settings={'state_root':str(state),'snapshot_root':str(snap.parent),'backup_mount':'/mnt/backup','backup_uuid':'uuid'}
            with patch.object(finish.subprocess,'check_output',return_value='{"filesystems":[{"target":"/mnt/backup","uuid":"uuid"}]}'):
                with self.assertRaisesRegex(RuntimeError,'gleichen Lauf'):finish.check_success(settings)
                frozen.write_text('{"started":"2026-10-25T12:33:00+01:00"}')
                self.assertTrue(finish.check_success(settings)['verified'])


class CleanupTests(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        home=root/'home';new=home/'models/ollama';new.mkdir(parents=True);(new/'model').write_text('Modell')
        old=root/'old-models';old.mkdir();(old/'model').write_text('Modell')
        data=home/'docker-data/comic';data.mkdir(parents=True);(data/'jobs.sqlite3').write_text('DB')
        state=root/'state';state.mkdir();(state/'export').mkdir();(state/'export/cache').write_text('behalten')
        current={'phase':'fertig','verified':True,'started':'2026-10-25T12:33:00+01:00'}
        (state/'status.json').write_text(json.dumps(current))
        snap=root/'snap/weekly.0';saved=snap/'localhost'/str(state).lstrip('/')/'export/dienstzustand.json';saved.parent.mkdir(parents=True)
        saved.write_text(json.dumps({'started':current['started'],'sources':[str(home)]}))
        for p in (new,data):(snap/'localhost'/str(p).lstrip('/')).mkdir(parents=True)
        migration=root/'migration.json';migration.write_text(json.dumps({'phase':'fertig','finished':'2026-10-25T12:19:00+01:00','source':str(old),'target':str(new)}))
        settings={'state_root':str(state),'snapshot_root':str(snap.parent),'backup_mount':'/mnt/backup','backup_uuid':'uuid'}
        config=root/'settings.json';config.write_text(json.dumps(settings))
        container={'Name':'/comic','Id':'cid','State':{'Running':False},'Mounts':[{'Type':'bind','Source':str(data),'Destination':'/data'}]}
        volumes=[{'Name':'old-comic','Driver':'local','Options':{}}]
        def command(args):
            if args[0]=='findmnt':return '{"filesystems":[{"target":"/mnt/backup","uuid":"uuid"}]}'
            if args[:3]==['docker','ps','-aq']:return 'cid\n'
            if args[:2]==['docker','inspect']:return json.dumps([container])
            if args[:3]==['docker','volume','ls']:return 'old-comic\n'
            if args[:3]==['docker','volume','inspect']:return json.dumps(volumes)
            if args[0]=='systemctl' and 'ActiveState' in args:return 'inactive\n'
            if args[0]=='systemctl':return 'OLLAMA_MODELS='+str(new)+'\n'
            raise AssertionError('Unerwarteter Befehl: '+repr(args))
        stack=contextlib.ExitStack();self.addCleanup(stack.close)
        patches={'CONFIG':config,'OLD_MODELS':old,'NEW_MODELS':new,'MIGRATION':migration,
                 'VOLUMES':{'old-comic':(str(data),'/data','comic')},'OLD_RULE':root/'sudo-rule','OLD_HELPER':root/'sudo-helper'}
        for key,value in patches.items():stack.enter_context(patch.object(cleanup,key,value))
        stack.enter_context(patch.object(cleanup,'command',side_effect=command))
        stack.enter_context(patch.object(cleanup.os,'geteuid',return_value=0))
        stack.enter_context(patch.object(cleanup.os,'sync'))
        return root,settings,container,volumes

    def test_default_only_plans_and_keeps_all_data(self):
        root,settings,c,volumes=self.fixture()
        with patch.object(sys,'argv',['cleanup']),patch.object(cleanup.subprocess,'run') as run:
            cleanup.main();run.assert_not_called()
        self.assertTrue(cleanup.OLD_MODELS.is_dir());self.assertTrue(cleanup.NEW_MODELS.is_dir())
        self.assertFalse((Path(settings['state_root'])/'bereinigung.json').exists())

    def test_no_cleanup_without_successful_backup(self):
        root,settings,c,volumes=self.fixture()
        (Path(settings['state_root'])/'status.json').write_text('{"phase":"fehler","verified":false}')
        with self.assertRaisesRegex(RuntimeError,'bestätigter'):cleanup.prerequisites(settings,[c],volumes)
        self.assertTrue(cleanup.OLD_MODELS.exists())

    def test_missing_new_data_in_snapshot_blocks_cleanup(self):
        root,settings,c,volumes=self.fixture()
        backed=Path(settings['snapshot_root'])/'weekly.0/localhost'/str(cleanup.NEW_MODELS).lstrip('/')
        backed.rmdir()
        with self.assertRaisesRegex(RuntimeError,'nicht im Snapshot'):cleanup.prerequisites(settings,[c],volumes)

    def test_any_old_volume_reference_blocks_cleanup(self):
        root,settings,c,volumes=self.fixture()
        other={'Name':'/other','State':{'Running':False},'Mounts':[{'Name':'old-comic','Type':'volume','Source':'/var/lib/docker/volumes/old-comic/_data'}]}
        with self.assertRaisesRegex(RuntimeError,'referenziert'):cleanup.prerequisites(settings,[c,other],volumes)

    def test_old_model_bind_blocks_cleanup_even_if_container_stopped(self):
        root,settings,c,volumes=self.fixture()
        other={'Name':'/other','State':{'Running':False},'Mounts':[{'Type':'bind','Source':str(cleanup.OLD_MODELS)}]}
        with self.assertRaisesRegex(RuntimeError,'Modellpfad'):cleanup.prerequisites(settings,[c,other],volumes)

    def test_explicit_cleanup_keeps_new_data_snapshots_and_export_cache(self):
        root,settings,c,volumes=self.fixture()
        with patch.object(sys,'argv',['cleanup','--delete']),patch.object(cleanup.subprocess,'run') as run:
            cleanup.main()
            run.assert_called_once_with(['docker','volume','rm','old-comic'],check=True)
        self.assertFalse(cleanup.OLD_MODELS.exists())
        self.assertTrue((cleanup.NEW_MODELS/'model').is_file())
        self.assertTrue((Path(settings['snapshot_root'])/'weekly.0').is_dir())
        self.assertTrue((Path(settings['state_root'])/'export/cache').is_file())
        self.assertEqual(json.loads((Path(settings['state_root'])/'bereinigung.json').read_text())['phase'],'fertig')


if __name__=='__main__':unittest.main()
