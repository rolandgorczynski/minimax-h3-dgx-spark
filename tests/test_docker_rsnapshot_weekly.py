"""Nur Testverzeichnisse und simulierte Dienste; keine produktiven Sicherungen."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('offline',Path(__file__).resolve().parents[1]/'scripts/docker_rsnapshot_weekly.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class OfflineTests(unittest.TestCase):
    def container(self, running=True):
        return {'Id':'container-id','Name':'/test','Image':'sha256:test',
                'State':{'Running':running},'Config':{'Labels':{'com.docker.compose.project.working_dir':'/home/jee/docker/test'}},
                'HostConfig':{'RestartPolicy':{'Name':'unless-stopped','MaximumRetryCount':0}},'Mounts':[]}

    def test_scope_uses_labels_and_directory_boundary(self):
        c=self.container()
        self.assertTrue(m.selected(c,'/home/jee/docker'))
        self.assertFalse(m.selected(c,'/home/jee/dock'))
        c['Config']['Labels']={}
        self.assertFalse(m.selected(c,'/home/jee/docker'))

    def test_unverified_never_starts(self):
        with patch.object(m,'command') as command:
            with self.assertRaises(RuntimeError): m.restart_services({'verified':False},lambda:None)
            command.assert_not_called()

    def test_only_previously_running_containers_restart(self):
        on=m.container_state(self.container()); off=dict(on,id='previously-off',name='off',running=False)
        state={'verified':True,'containers':[on,off],'services':[]}
        def fake(args):
            if args[:2]==['docker','inspect']:
                return json.dumps([{'State':{'Running':args[2]=='container-id'}}])
            return ''
        with patch.object(m,'command',side_effect=fake) as calls:
            m.restart_services(state,lambda:None)
            starts=[c.args[0] for c in calls.call_args_list if c.args[0][:2]==['docker','start']]
        self.assertEqual(starts,[['docker','start','container-id']])
        self.assertEqual(state['phase'],'fertig')

    def test_journal_blocks_repeated_run_before_docker_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,'status.json').write_text('{"phase":"fehler"}')
            with patch.object(m.os,'geteuid',return_value=0),patch.object(m,'plan') as plan:
                with self.assertRaisesRegex(RuntimeError,'Voriger Lauf'):
                    m.run({'state_root':tmp})
                plan.assert_not_called()

    def test_mount_uuid_mismatch_aborts(self):
        with patch.object(m,'command',return_value='{"filesystems":[{"target":"/mnt/backup","uuid":"wrong"}]}'):
            with self.assertRaises(RuntimeError):
                m.mount_check({'backup_mount':'/mnt/backup','backup_uuid':'expected','snapshot_root':'/mnt/backup/offline'})

    def test_unknown_config_hooks_are_rejected(self):
        with self.assertRaises(RuntimeError):
            m.config_text('cmd_postexec\t/bin/true\n',[],Path('/unused'))

    def test_stop_state_persisted_before_first_mutation(self):
        state={'containers':[m.container_state(self.container())],'services':[]}
        events=[]
        def fake(args):
            events.append(args)
            return '[{"State":{"Running":false}}]' if args[:2]==['docker','inspect'] else ''
        with patch.object(m,'command',side_effect=fake):
            m.stop_services(state,lambda:events.append('persist'))
        self.assertEqual(events[0],'persist')
        self.assertEqual(events[1],['docker','update','--restart=no','container-id'])

    def test_sync_error_never_restarts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'source';source.mkdir(); snap=root/'snapshot'
            base=root/'base.conf';base.write_text('snapshot_root\t'+str(snap)+'/\n')
            settings={'state_root':str(root/'state'),'snapshot_root':str(snap),'reserve_bytes':0,'base_config':str(base)}
            def fake(args):
                if args[-1]=='sync': raise RuntimeError('Testfehler beim Kopieren')
                return ''
            with patch.object(m.os,'geteuid',return_value=0),patch.object(m,'plan',return_value=([self.container()],[source],[])),patch.object(m,'stop_services'),patch.object(m,'space_check'),patch.object(m,'export_images'),patch.object(m,'export_rootfs'),patch.object(m,'command',side_effect=fake),patch.object(m,'restart_services') as restart:
                with self.assertRaisesRegex(RuntimeError,'Testfehler'): m.run(settings)
                restart.assert_not_called()
            state=json.loads((root/'state/status.json').read_text())
            self.assertEqual(state['phase'],'fehler'); self.assertFalse(state['verified'])

    def test_failed_restart_stops_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'source';source.mkdir();snap=root/'snapshot'
            base=root/'base.conf';base.write_text('snapshot_root\t'+str(snap)+'/\n')
            settings={'state_root':str(root/'state'),'snapshot_root':str(snap),'reserve_bytes':0,'base_config':str(base)}
            def broken_restart(state,persist):
                state['phase']='starten';persist();raise RuntimeError('Startfehler')
            with patch.object(m.os,'geteuid',return_value=0),patch.object(m,'plan',return_value=([self.container()],[source],[])),patch.object(m,'stop_services') as stop,patch.object(m,'space_check'),patch.object(m,'export_images'),patch.object(m,'export_rootfs'),patch.object(m,'command',return_value=''),patch.object(m,'stopped'),patch.object(m,'verify'),patch.object(m.os,'sync'),patch.object(m,'restart_services',side_effect=broken_restart):
                with self.assertRaisesRegex(RuntimeError,'Startfehler'):m.run(settings)
                self.assertEqual(stop.call_count,2)
            state=json.loads((root/'state/status.json').read_text())
            self.assertEqual(state['verification'],'metadata')
            self.assertFalse(state['checksums_verified'])

    def test_multiple_sources_and_volume_data_verify_without_false_deletions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);home=root/'home';home.mkdir();volume=root/'volume'/'_data';volume.mkdir(parents=True)
            (home/'datei').write_text('Home')
            (volume/'jobs.sqlite3').write_bytes(b'Datenbank-Testinhalt')
            (volume/'link').symlink_to('jobs.sqlite3')
            config_file=root/'service.conf';config_file.write_text('Konfiguration')
            dest=root/'destination';dest.mkdir()
            for source in (home,volume,config_file):
                subprocess.run(['rsync','-aHAXR',str(source)+('/' if source.is_dir() else ''),str(dest)+'/'],check=True,capture_output=True)
            m.verify([home,volume,config_file],dest)
            self.assertTrue((dest/str(volume).lstrip('/')/'link').is_symlink())
            (volume/'jobs.sqlite3').write_bytes(b'Andere Daten')
            with self.assertRaisesRegex(RuntimeError,'weicht'):
                m.verify([volume],dest)

    def test_regular_config_removes_all_checksum_flags(self):
        base='snapshot_root\t/snap/\nrsync_short_args\t-aHAXc\nrsync_long_args\t--delete --relative --checksum -c\n'
        text=m.config_text(base,[],Path('/snap'))
        self.assertNotIn('--checksum',text)
        self.assertIn('rsync_short_args\t-aHAX\n',text)
        self.assertNotIn(' -c',text)

    def test_metadata_check_skips_contents_but_detects_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir();dest=root/'dest';dest.mkdir()
            file=source/'text';file.write_text('Inhalt A')
            subprocess.run(['rsync','-aHAXR',str(source)+'/',str(dest)+'/'],check=True,capture_output=True)
            stat=file.stat();file.write_text('Inhalt B');m.os.utime(file,ns=(stat.st_atime_ns,stat.st_mtime_ns))
            m.verify([source],dest,checksums=False)
            with self.assertRaises(RuntimeError):m.verify([source],dest,checksums=True)
            file.chmod((file.stat().st_mode & 0o777)^0o100)
            with self.assertRaises(RuntimeError):m.verify([source],dest,checksums=False)

    def verify_fixture(self,tmp):
        root=Path(tmp);state=root/'state';state.mkdir();snapshot=root/'snapshots/weekly.0'
        recorded=state/'export/dienstzustand.json'
        dest=snapshot/'localhost'/str(recorded).lstrip('/')
        dest.parent.mkdir(parents=True)
        source=root/'source';source.mkdir()
        original={'sources':[str(source)],'containers':[m.container_state(self.container(False))],'services':[]}
        dest.write_text(json.dumps(original))
        settings={'state_root':str(state),'snapshot_root':str(snapshot.parent)}
        return state,source,settings

    def test_manual_job_uses_snapshot_sources_and_separate_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            state,source,settings=self.verify_fixture(tmp)
            (state/'status.json').write_text('{"phase":"fehler"}')
            before=(state/'status.json').read_text()
            with patch.object(m.os,'geteuid',return_value=0),patch.object(m,'mount_check'),patch.object(m,'plan',return_value=([self.container(False)],[],[])),patch.object(m,'inspect_containers',return_value=[self.container(False)]),patch.object(m,'stopped') as stopped,patch.object(m,'verify') as verify,patch.object(m,'command') as command:
                m.verify_snapshot(settings)
                verify.assert_called_once_with([source],Path(settings['snapshot_root'])/'weekly.0/localhost',checksums=True,ignore_paths=m.verification_ignores(settings))
                self.assertEqual(stopped.call_count,4)
                command.assert_not_called()
            self.assertEqual((state/'status.json').read_text(),before)
            result=json.loads((state/'checksums-status.json').read_text())
            self.assertTrue(result['checksums_verified'])

    def test_manual_job_refuses_running_services_without_stopping_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            state,source,settings=self.verify_fixture(tmp)
            with patch.object(m.os,'geteuid',return_value=0),patch.object(m,'mount_check'),patch.object(m,'plan',return_value=([self.container()],[],[])),patch.object(m,'inspect_containers',return_value=[self.container()]),patch.object(m,'stopped',side_effect=RuntimeError('Container läuft')),patch.object(m,'verify') as verify,patch.object(m,'stop_services') as stop,patch.object(m,'restart_services') as start:
                with self.assertRaisesRegex(RuntimeError,'läuft'):m.verify_snapshot(settings)
                verify.assert_not_called();stop.assert_not_called();start.assert_not_called()

    def test_manual_job_rejects_unfinished_or_traversal_snapshot(self):
        with patch.object(m.os,'geteuid',return_value=0),patch.object(m,'mount_check') as mount:
            for name in ('.sync','../weekly.0','/etc','weekly.0/../.sync'):
                with self.assertRaises(RuntimeError):m.verify_snapshot({},name)
            mount.assert_not_called()

    def test_volatile_codex_and_browser_changes_do_not_block_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);home=root/'home';home.mkdir();dest=root/'dest';dest.mkdir()
            codex=home/'.codex';codex.mkdir();(codex/'state.sqlite-wal').write_text('WAL')
            cache=home/'.cache/google-chrome';cache.mkdir(parents=True);(cache/'cache').write_text('alt')
            project=home/'docker/project';project.mkdir(parents=True);(project/'datenbank').write_text('DB')
            subprocess.run(['rsync','-aHAXR',str(home)+'/',str(dest)+'/'],check=True,capture_output=True)
            (codex/'state.sqlite-wal').unlink();(codex/'new-session').write_text('Neue Sitzung')
            (cache/'cache').write_text('neuer Cache')
            ignore=m.verification_ignores({'home':str(home)})
            m.verify([home],dest,checksums=False,ignore_paths=ignore)
            m.verify([home],dest,checksums=True,ignore_paths=ignore)
            # Die ignorierten Bereiche bleiben in der Kopie, auch alte WAL-Dateien.
            self.assertTrue((dest/str(codex).lstrip('/')/'state.sqlite-wal').exists())
            # Andere Quelldaten werden weiterhin streng geprüft.
            (project/'datenbank').write_text('Geänderte DB')
            with self.assertRaises(RuntimeError):m.verify([home],dest,checksums=False,ignore_paths=ignore)

    def test_real_read_errors_are_not_ignored(self):
        with patch.object(m,'command',side_effect=RuntimeError('Permission denied')):
            with self.assertRaisesRegex(RuntimeError,'Permission denied'):
                m.verify([Path('/home/jee')],Path('/dest'),checksums=False,ignore_paths=m.verification_ignores({}))

    def test_resume_rejects_other_failure_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'status.json').write_text(json.dumps({'phase':'fehler','failed_phase':'synchronisieren','error':'Permission denied'}))
            with patch.object(m.os,'geteuid',return_value=0),patch.object(m,'plan') as plan:
                with self.assertRaisesRegex(RuntimeError,'andere Fehler'):m.run({'state_root':tmp},resume=True)
                plan.assert_not_called()

    def test_resume_archives_failure_and_really_syncs_and_checks_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);state=root/'state';state.mkdir();source=root/'source';source.mkdir();snapshot=root/'snapshot'
            base=root/'base.conf';base.write_text('snapshot_root\t'+str(snapshot)+'/\n')
            original=m.container_state(self.container(False))
            old={'phase':'fehler','failed_phase':'pruefen','error':'Sicherung weicht von Quelle ab: /home/jee',
                 'started':'original-run','containers':[original],'services':[]}
            (state/'status.json').write_text(json.dumps(old))
            current=self.container(False);current['HostConfig']['RestartPolicy']={'Name':'no','MaximumRetryCount':0}
            settings={'state_root':str(state),'snapshot_root':str(snapshot),'base_config':str(base),'reserve_bytes':0}
            def restart(record,persist):
                self.assertFalse(record['containers'][0]['running'])
                self.assertEqual(record['containers'][0]['restart_policy']['Name'],'unless-stopped')
                record['phase']='fertig';persist()
            with patch.object(m.os,'geteuid',return_value=0),patch.object(m,'plan',return_value=([current],[source],[])),patch.object(m,'command',return_value='') as command,patch.object(m,'stop_services'),patch.object(m,'export_images'),patch.object(m,'export_rootfs'),patch.object(m,'space_check'),patch.object(m,'stopped'),patch.object(m,'verify') as verify,patch.object(m.os,'sync'),patch.object(m,'restart_services',side_effect=restart):
                m.run(settings,resume=True)
                verify.assert_called_once()
                self.assertFalse(verify.call_args.kwargs['checksums'])
                actions=[call.args[0][-1] for call in command.call_args_list]
                self.assertIn('sync',actions);self.assertIn('weekly',actions)
            recorded=json.loads((state/'status.json').read_text())
            self.assertEqual(recorded['phase'],'fertig');self.assertEqual(recorded['resumes_from'],'original-run')
            self.assertTrue(recorded['verified'])
            history=list((state/'fehlerhistorie').glob('*.json'))
            self.assertEqual(len(history),1);self.assertEqual(json.loads(history[0].read_text()),old)

    def test_cups_live_subscriptions_ignored_but_other_config_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);etc=root/'etc';cups=etc/'cups';cups.mkdir(parents=True);dest=root/'dest';dest.mkdir()
            first=cups/'subscriptions.conf';second=cups/'subscriptions.conf.O';printers=cups/'printers.conf'
            first.write_text('Abonnement');second.write_text('Alt');printers.write_text('Drucker')
            subprocess.run(['rsync','-aHAXR',str(etc)+'/',str(dest)+'/'],check=True,capture_output=True)
            first.write_text('Abonnement wurde vom Dienst geändert');second.unlink()
            stamp=cups.stat();m.os.utime(cups,ns=(stamp.st_atime_ns,stamp.st_mtime_ns+5_000_000_000))
            with patch.object(m,'VOLATILE_CHECK_FILES',(first,second)),patch.object(m,'VOLATILE_CHECK_DIR_TIMES',(cups,)):
                m.verify([etc],dest,checksums=False)
                self.assertTrue((dest/str(second).lstrip('/')).exists())
                printers.write_text('Wichtige geänderte Druckerkonfiguration')
                with self.assertRaisesRegex(RuntimeError,'weicht'):m.verify([etc],dest,checksums=False)

    def test_only_cups_directory_timestamp_is_nonfatal(self):
        self.assertEqual(m.essential_differences('.d..t...... /etc/cups/\n'),'')
        for difference in ('.d..tp..... /etc/cups/','.d..t...... /etc/ssh/','cd+++++++++ /etc/cups/','>f..t...... /etc/cups/printers.conf'):
            self.assertEqual(m.essential_differences(difference),difference)

    def test_browser_metrics_are_volatile_but_bookmarks_remain_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);home=root/'home';metrics=home/'.config/google-chrome/BrowserMetrics';metrics.mkdir(parents=True)
            profile=home/'.config/google-chrome/Default';profile.mkdir();bookmarks=profile/'Bookmarks';bookmarks.write_text('Meine Lesezeichen')
            metric=metrics/'BrowserMetrics.pma';metric.write_text('Messdaten');dest=root/'dest';dest.mkdir()
            subprocess.run(['rsync','-aHAXR',str(home)+'/',str(dest)+'/'],check=True,capture_output=True)
            stamp=metric.stat();m.os.utime(metric,ns=(stamp.st_atime_ns,stamp.st_mtime_ns+5_000_000_000))
            ignore=m.verification_ignores({'home':str(home)})
            m.verify([home],dest,checksums=False,ignore_paths=ignore)
            self.assertTrue((dest/str(metric).lstrip('/')).is_file())
            bookmarks.write_text('Neue wichtige Lesezeichen')
            with self.assertRaisesRegex(RuntimeError,'weicht'):m.verify([home],dest,checksums=False,ignore_paths=ignore)

    def test_parent_journal_timestamp_does_not_change_export_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);state=root/'state';export=state/'export';export.mkdir(parents=True)
            (export/'image.tar').write_text('Gesicherte Exportdatei');dest=root/'dest';dest.mkdir()
            subprocess.run(['rsync','-aHAXR',str(export)+'/',str(dest)+'/'],check=True,capture_output=True)
            stamp=state.stat();(state/'status.json').write_text('Neuer Status')
            m.os.utime(state,ns=(stamp.st_atime_ns,stamp.st_mtime_ns+5_000_000_000))
            m.verify([export],dest,checksums=False)
            m.verify([export],dest,checksums=True)
            # Der tatsächliche Quellordner und sein Inhalt bleiben geprüft.
            stamp=export.stat();m.os.utime(export,ns=(stamp.st_atime_ns,stamp.st_mtime_ns+5_000_000_000))
            with self.assertRaises(RuntimeError):m.verify([export],dest,checksums=False)
            m.os.utime(export,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
            (export/'image.tar').write_text('Falscher Exportinhalt')
            with self.assertRaises(RuntimeError):m.verify([export],dest,checksums=True)

    def test_real_rsnapshot_delta_and_checksum_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'source';source.mkdir();snapshot=root/'snapshots';snapshot.mkdir()
            file=source/'text.txt';file.write_text('Hallo Welt\n')
            (source/'bleibt.txt').write_text('Unverändert\n')
            config=root/'rsnapshot.conf'
            base=('config_version\t1.2\nsnapshot_root\t'+str(snapshot)+'/\n'
                  'no_create_root\t1\ncmd_cp\t/bin/cp\ncmd_rm\t/bin/rm\ncmd_rsync\t/usr/bin/rsync\n'
                  'lockfile\t'+str(root/'lock')+'\nlogfile\t'+str(root/'log')+'\n'
                  'sync_first\t1\nretain\tweekly\t2\nrsync_short_args\t-aHAX\n'
                  'rsync_long_args\t--delete --numeric-ids --relative --delete-excluded --checksum\n')
            config.write_text(m.config_text(base,[source],snapshot))
            for action in ('configtest','sync'):
                subprocess.run(['rsnapshot','-c',str(config),action],check=True,capture_output=True)
            m.verify([source],snapshot/'.sync/localhost')
            # Gleiche Länge und Zeitstempel: nur der Prüfsummenvergleich erkennt die Änderung.
            stat=file.stat();file.write_text('Hallo Mars\n');m.os.utime(file,ns=(stat.st_atime_ns,stat.st_mtime_ns))
            with self.assertRaises(RuntimeError):m.verify([source],snapshot/'.sync/localhost')
            file.write_text('Hallo Welt\n');m.os.utime(file,ns=(stat.st_atime_ns,stat.st_mtime_ns))
            subprocess.run(['rsnapshot','-c',str(config),'weekly'],check=True,capture_output=True)
            subprocess.run(['rsnapshot','-c',str(config),'sync'],check=True,capture_output=True)
            m.verify([source],snapshot/'.sync/localhost')
            subprocess.run(['rsnapshot','-c',str(config),'weekly'],check=True,capture_output=True)
            relative=Path('localhost')/str(source).lstrip('/')/'bleibt.txt'
            self.assertEqual((snapshot/'weekly.0'/relative).stat().st_ino,(snapshot/'weekly.1'/relative).stat().st_ino)


if __name__=='__main__':unittest.main()
