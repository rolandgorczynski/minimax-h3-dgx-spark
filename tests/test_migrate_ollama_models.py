"""Modellumzug nur mit Testdateien bzw. simuliertem systemd testen."""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('move',Path(__file__).resolve().parents[1]/'scripts/migrate_ollama_models.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class MigrationTests(unittest.TestCase):
    def test_not_root_does_nothing(self):
        with patch.object(m.os,'geteuid',return_value=1000),patch.object(m,'run') as run:
            with self.assertRaisesRegex(RuntimeError,'sudo'):m.preflight(False)
            run.assert_not_called()

    def test_running_container_blocks_before_stop(self):
        with patch.object(m.os,'geteuid',return_value=0),patch.object(m.shutil,'which',return_value='/tool'),patch.object(m,'run',return_value='a-running-container\n') as run:
            with self.assertRaisesRegex(RuntimeError,'laufen Docker'):m.preflight(False)
            self.assertEqual(run.call_args_list[0].args[0],['docker','ps','-q'])
            self.assertEqual(run.call_count,1)

    def test_backup_source_removed_only_when_home_covers_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)/'backup.json'
            config.write_text(json.dumps({'home':'/home/jee','additional_sources':[str(m.SOURCE),'/usr/local/bin/ollama']}))
            updated=json.loads(m.update_backup_config(config))
            self.assertEqual(updated['additional_sources'],['/usr/local/bin/ollama'])
            config.write_text('{"home":"/other"}')
            with self.assertRaises(RuntimeError):m.update_backup_config(config)

    def test_real_copy_and_verification_checks_checksums(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';target=Path(tmp)/'target';source.mkdir();target.mkdir()
            file=source/'model';file.write_text('Modell A')
            (source/'link').symlink_to('model')
            account=m.pwd.getpwuid(os.getuid()).pw_name;group=m.grp.getgrgid(os.getgid()).gr_name
            with patch.object(m,'SOURCE',source),patch.object(m,'TARGET',target):
                args=[a.replace('--chown=ollama:ollama','--chown='+account+':'+group) for a in m.copy_args()]
                subprocess.run(args,check=True,capture_output=True)
                check=[a.replace('--chown=ollama:ollama','--chown='+account+':'+group) for a in m.copy_args(True)]
                self.assertEqual(subprocess.check_output(check,text=True),'')
                stat=file.stat();file.write_text('Modell B');os.utime(file,ns=(stat.st_atime_ns,stat.st_mtime_ns))
                self.assertNotEqual(subprocess.check_output(check,text=True),'')
                self.assertEqual((target/'model').read_text(),'Modell A')
                self.assertTrue((target/'link').is_symlink())

    def scenario(self,differences=''):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        root=Path(temp.name);home=root/'home';home.mkdir();home.chmod(0o750)
        parent=home/'models';parent.mkdir();target=parent/'ollama';source=root/'old';source.mkdir()
        (source/'model').write_text('Modellinhalt')
        state=root/'state';dropin=root/'systemd'/'zz-model-path.conf';dropin.parent.mkdir()
        config=root/'config.json';config.write_text(json.dumps({'home':str(home),'additional_sources':[str(source),'/usr/local/bin/ollama']}))
        before={'User':'ollama','Group':'ollama','ActiveState':'active','UnitFileState':'enabled','ProtectHome':'no',
                'Environment':'OLLAMA_HOST=0.0.0.0:11434'}
        stopped=dict(before,ActiveState='inactive',UnitFileState='disabled')
        after=dict(stopped,SupplementaryGroups='jee',Environment=before['Environment']+' OLLAMA_MODELS='+str(target))
        # Der feste Drop-in-Pfad ist absichtlich auf das reale Ziel geschrieben; für diesen
        # Test prüft der simulierte systemd-Status den entsprechend temporären Zielpfad.
        calls=[]
        def fake_run(args,live=False):
            calls.append(args)
            if args[:2]==['docker','ps']:return ''
            if args[0]=='du':return '12\told\n'
            if args[0]=='rsync':
                if '--dry-run' in args:return differences
                shutil.copy2(source/'model',target/'model');return ''
            if args[0]=='runuser':return 'Zugriff geprüft\n'
            return ''
        stack=contextlib.ExitStack();self.addCleanup(stack.close)
        for key,value in {'HOME':home,'SOURCE':source,'TARGET':target,'STATE':state,'DROPIN':dropin,'BACKUP_CONFIGS':(config,)}.items():
            stack.enter_context(patch.object(m,key,value))
        stack.enter_context(patch.object(m,'log'))
        stack.enter_context(patch.object(m.os,'geteuid',return_value=0))
        stack.enter_context(patch.object(m.os,'chown'))
        stack.enter_context(patch.object(m.os,'sync'))
        stack.enter_context(patch.object(m.shutil,'which',return_value='/tool'))
        stack.enter_context(patch.object(m.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=os.getuid(),pw_gid=os.getgid())))
        stack.enter_context(patch.object(m.grp,'getgrnam',return_value=SimpleNamespace(gr_gid=os.getgid())))
        stack.enter_context(patch.object(m.os,'getgrouplist',return_value=[os.getgid()]))
        stack.enter_context(patch.object(m,'properties',side_effect=[before,stopped,stopped,after]))
        stack.enter_context(patch.object(m,'run',side_effect=fake_run))
        return source,target,state,dropin,config,calls

    def test_success_retains_source_stops_service_and_never_starts(self):
        source,target,state,dropin,config,calls=self.scenario()
        m.migrate()
        self.assertEqual((source/'model').read_text(),'Modellinhalt')
        self.assertEqual((target/'model').read_text(),'Modellinhalt')
        self.assertEqual(json.loads((state/'status.json').read_text())['phase'],'fertig')
        self.assertIn(['systemctl','stop','ollama.service'],calls)
        self.assertIn(['systemctl','disable','ollama.service'],calls)
        self.assertFalse(any(a[0]=='systemctl' and any(v in a for v in ('start','restart','enable')) for a in calls))
        self.assertFalse(any(a[0]=='docker' and a[1]!='ps' for a in calls))
        self.assertTrue(dropin.exists())
        self.assertEqual(json.loads(config.read_text())['additional_sources'],['/usr/local/bin/ollama'])
        self.assertTrue((state/'originale/0/pfad.json').exists())

    def test_checksum_failure_never_changes_config_or_starts(self):
        source,target,state,dropin,config,calls=self.scenario('>fc........ model\n')
        original=config.read_text()
        with self.assertRaisesRegex(RuntimeError,'weicht'):m.migrate()
        self.assertFalse(dropin.exists());self.assertEqual(config.read_text(),original)
        self.assertTrue(source.exists())
        self.assertEqual(json.loads((state/'status.json').read_text())['phase'],'fehler')
        self.assertFalse(any(a[:2] in (['systemctl','start'],['systemctl','restart']) for a in calls))

    def test_source_tree_rejects_links_back_to_old_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp);(source/'model').write_text('Modell')
            (source/'relative').symlink_to('model')
            with patch.object(m,'SOURCE',source):
                m.check_source_tree()
                (source/'absolute').symlink_to(source/'model')
                with self.assertRaisesRegex(RuntimeError,'Symlink'):m.check_source_tree()

    def test_interrupted_copy_can_resume_without_deleting_source(self):
        source,target,state,dropin,config,calls=self.scenario('>fc........ model\n')
        with self.assertRaises(RuntimeError):m.migrate()
        original_run=m.run.side_effect
        def resumed_run(args,live=False):
            if args[0]=='rsync' and '--dry-run' in args:return ''
            return original_run(args,live)
        m.run.side_effect=resumed_run
        old={'User':'ollama','Group':'ollama','ActiveState':'inactive','UnitFileState':'disabled',
             'ProtectHome':'no','Environment':'OLLAMA_HOST=0.0.0.0:11434'}
        new=dict(old,SupplementaryGroups='jee',Environment=old['Environment']+' OLLAMA_MODELS='+str(target))
        m.properties.side_effect=[old,old,old,new]
        m.migrate(resume=True)
        self.assertEqual(json.loads((state/'status.json').read_text())['phase'],'fertig')
        self.assertEqual((source/'model').read_text(),'Modellinhalt')

    def test_completed_journal_refuses_to_repeat(self):
        source,target,state,dropin,config,calls=self.scenario()
        state.mkdir();(state/'status.json').write_text('{"phase":"fertig"}')
        with self.assertRaisesRegex(RuntimeError,'bereits abgeschlossen'):m.migrate()
        self.assertFalse(any(a[:2]==['systemctl','stop'] for a in calls))


if __name__=='__main__':unittest.main()
