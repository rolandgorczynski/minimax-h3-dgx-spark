import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import fcntl

spec=importlib.util.spec_from_file_location('update',Path(__file__).resolve().parents[1]/'scripts/update_docker_rsnapshot.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class UpdateTests(unittest.TestCase):
    def test_etc_replaces_children_and_preserves_other_sources(self):
        data={'additional_sources':['/usr/local/bin/ollama','/etc/systemd/system/ollama.service'],
              'optional_sources':['/etc/systemd/system/ollama.service.d','/other']}
        updated=m.add_etc(data)
        self.assertEqual(updated['additional_sources'],['/usr/local/bin/ollama','/etc'])
        self.assertEqual(updated['optional_sources'],['/other'])
        self.assertEqual(m.add_etc(updated),updated)

    def test_removes_content_comparison_flags(self):
        text=m.no_content_checks('rsync_short_args\t-aHAXc\nrsync_long_args\t--delete --checksum -c\n')
        self.assertEqual(text,'rsync_short_args\t-aHAX\nrsync_long_args\t--delete\n')

    def test_update_respects_lock_and_preserves_backup_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);state=root/'state';state.mkdir();project=root/'project';(project/'scripts').mkdir(parents=True)
            (project/'scripts/docker_rsnapshot_weekly.py').write_text('print("new")\n')
            (project/'scripts/docker_rsnapshot_checksums.sh').write_text('#!/bin/sh\nexit 0\n')
            config=root/'config.json';base=root/'base.conf';base.write_text('rsync_long_args\t--delete --checksum\n')
            config.write_text(json.dumps({'state_root':str(state),'base_config':str(base),'additional_sources':['/etc/systemd/unit']}))
            installed=root/'installed';installed.write_text('old\n');checker=root/'checker'
            (state/'status.json').write_text('{"phase":"fehler"}')
            before=config.read_text()
            with patch.object(m,'PROJECT',project),patch.object(m,'CONFIG',config),patch.object(m,'WRAPPER',installed),patch.object(m,'CHECKER',checker),patch.object(m.os,'geteuid',return_value=0),patch.object(m.os,'chown'):
                with (state/'lock').open('a') as lock:
                    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    with self.assertRaisesRegex(SystemExit,'läuft noch'):m.main()
                self.assertEqual(config.read_text(),before);self.assertEqual(installed.read_text(),'old\n')
                m.main()
            self.assertEqual(installed.read_text(),'print("new")\n')
            self.assertTrue(checker.is_file())
            self.assertEqual(json.loads(config.read_text())['additional_sources'],['/etc'])
            self.assertNotIn('--checksum',base.read_text())
            self.assertEqual((state/'status.json').read_text(),'{"phase":"fehler"}')
            self.assertEqual(len(list((state/'updates').glob('*/*'))),3)


if __name__=='__main__':unittest.main()
