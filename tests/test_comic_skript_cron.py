"""Cron-Prüfung ohne Codex-Aufruf, Nachrichten oder Änderungen an der echten Crontab."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess

spec=importlib.util.spec_from_file_location('comic_skript_cron',Path(__file__).resolve().parents[1]/'scripts/comic_skript_cron.py')
cron=importlib.util.module_from_spec(spec);spec.loader.exec_module(cron)

class ScriptCronTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        for name,value in [('ROOT',self.root)]:
            p=patch.object(cron,name,value);p.start();self.addCleanup(p.stop)
        self.config={'enabled':True,'thread_id':'festes-ziel','schedule':'*/30 * * * *'}

    def test_paused_busy_unknown_and_finished_never_send(self):
        with patch.object(cron,'progress',return_value=(30,352)),patch.object(cron,'thread_status',return_value='beschäftigt'),patch.object(cron.subprocess,'run') as run:
            cron.tick(self.config,True);self.assertFalse(run.called)
        with patch.object(cron,'progress',return_value=(30,352)),patch.object(cron,'thread_status',return_value='unbekannt oder unterbrochen'),patch.object(cron.subprocess,'run') as run:
            cron.tick(self.config,True);self.assertFalse(run.called)
        with patch.object(cron,'progress',return_value=(382,0)),patch.object(cron.subprocess,'run') as run:
            cron.tick(self.config,True);self.assertFalse(run.called)
        with patch.object(cron.subprocess,'run') as run:
            cron.tick({**self.config,'enabled':False},True);self.assertFalse(run.called)

    def test_single_delivery_then_wait_until_progress(self):
        with patch.object(cron,'progress',return_value=(30,352)),patch.object(cron,'thread_status',return_value='bereit'),patch.object(cron.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'','')) as run:
            cron.tick(self.config,True);cron.tick(self.config,True)
            self.assertEqual(run.call_count,1)
            args=run.call_args.args[0]
            self.assertEqual(args[1:4],['queue','--thread','festes-ziel'])
            self.assertIn('Keine Bilder erzeugen',args[-1])
            self.assertTrue(json.loads((self.root/'status.json').read_text())['pending'])
        with patch.object(cron,'progress',return_value=(34,348)),patch.object(cron,'thread_status',return_value='bereit'),patch.object(cron.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'','')) as run:
            cron.tick(self.config,True);self.assertEqual(run.call_count,1)

    def test_failed_delivery_is_not_blindly_repeated(self):
        with patch.object(cron,'progress',return_value=(30,352)),patch.object(cron,'thread_status',return_value='bereit'),patch.object(cron.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','')) as run:
            with self.assertRaises(RuntimeError):cron.tick(self.config,True)
            cron.tick(self.config,True);self.assertEqual(run.call_count,1)

    def test_plan_never_queues_or_marks_pending(self):
        with patch.object(cron,'progress',return_value=(30,352)),patch.object(cron,'thread_status',return_value='bereit'),patch.object(cron.subprocess,'run') as run:
            cron.tick(self.config);self.assertFalse(run.called)
            self.assertFalse((self.root/'status.json').exists())

    def test_cron_keeps_unrelated_entries_and_removes_only_own(self):
        original='30 3 * * * fremder-job\n# deaktivierter-job\n*/15 * * * * alt '+cron.TAG+'\n'
        with patch.object(cron.subprocess,'run',side_effect=[subprocess.CompletedProcess([],0,original,''),subprocess.CompletedProcess([],0,'','')]) as run:
            cron.cron(self.config)
            value=run.call_args.kwargs['input']
            self.assertTrue(value.startswith('30 3 * * * fremder-job\n# deaktivierter-job\n'))
            self.assertEqual(value.count(cron.TAG),1)
            self.assertIn('*/30 * * * *',value)
