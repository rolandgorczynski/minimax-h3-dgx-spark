"""Export orchestration must not complete a job when page generation fails."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('render_editorial_script',SCRIPTS/'render_editorial_comic.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class ScriptTests(unittest.TestCase):
    def test_layout_failure_never_uploads_or_finalizes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'story.json'
            source.write_text(json.dumps({'title':'Titel','article':'Text','scenes':[{'story':'Ein Raum.'}]}))
            args=argparse.Namespace(source=source,job='a'*32,output=root/'output',container='test',base_url='http://localhost',draft=False,review='Test')
            with patch.object(m,'docker') as docker,patch.object(m,'upload') as upload,patch('layout_editorial_comic.layout',side_effect=ValueError('Layout defekt')):
                with self.assertRaisesRegex(ValueError,'Layout defekt'):m.run(args)
                self.assertEqual(docker.call_count,1)
                self.assertIn('from editorial import render',docker.call_args.args[1])
                upload.assert_not_called()
            marker=json.loads((args.output/'render-job.json').read_text())
            self.assertEqual(marker['id'],args.job)

    def test_invalid_job_cannot_reach_docker_or_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'story.json'
            source.write_text(json.dumps({'title':'Titel','article':'Text','scenes':[{}]}))
            args=argparse.Namespace(source=source,job='../outside',output=root/'output')
            with patch.object(m,'docker') as docker:
                with self.assertRaises(ValueError):m.run(args)
                docker.assert_not_called()
            self.assertFalse(args.output.exists())


if __name__=='__main__':unittest.main()
