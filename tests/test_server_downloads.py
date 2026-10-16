import asyncio
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

PLUGIN = Path(os.environ.get('DGX_PLUGIN_FILE', Path(__file__).resolve().parents[1] / 'extensions/dgx-server-downloads/__init__.py'))
folders = types.SimpleNamespace(models_dir='', folder_names_and_paths={'vae': None, 'loras': None, 'custom_nodes': None, 'configs': None}, filename_list_cache={})
routes = web.RouteTableDef()
server = types.SimpleNamespace(PromptServer=types.SimpleNamespace(instance=types.SimpleNamespace(routes=routes)))
with patch.dict(sys.modules, {'folder_paths': folders, 'server': server}):
    spec = importlib.util.spec_from_file_location('dgx_downloads_tested', PLUGIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


class Downloads(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        folders.models_dir = self.temp.name
        module.JOBS.clear()
        module.LOCK = asyncio.Lock()
        self.target = Path(self.temp.name) / 'vae/model.safetensors'
        self.data = b'local test model bytes' * 100
        self.ranges = []
        self.ignore_range = False
        self.interrupt = False
        self.html = False

        async def remote(request):
            header = request.headers.get('Range')
            self.ranges.append(header)
            offset = int(header[6:-1]) if header and not self.ignore_range else 0
            if offset >= len(self.data):
                return web.Response(status=416, headers={'Content-Range': f'bytes */{len(self.data)}'})
            body = self.data[offset:]
            if self.interrupt:
                self.interrupt = False
                response = web.StreamResponse(headers={'Content-Length': str(len(body)), 'Content-Type': 'application/octet-stream'})
                await response.prepare(request)
                await response.write(body[:100])
                await asyncio.sleep(0.02)
                request.transport.close()
                return response
            headers = {'Content-Type': 'text/html' if self.html else 'application/octet-stream'}
            if offset:
                headers['Content-Range'] = f'bytes {offset}-{len(self.data)-1}/{len(self.data)}'
            return web.Response(body=body, status=206 if offset else 200, headers=headers)

        app = web.Application()
        app.router.add_get('/model', remote)
        self.remote = TestServer(app)
        await self.remote.start_server()
        self.url = str(self.remote.make_url('/model'))
        app = web.Application()
        app.add_routes(routes)
        self.client = TestClient(TestServer(app))
        await self.client.start_server()

    async def asyncTearDown(self):
        for task in list(module.TASKS):
            task.cancel()
        await asyncio.gather(*module.TASKS, return_exceptions=True)
        await self.client.close()
        await self.remote.close()
        self.temp.cleanup()

    def job(self):
        return {'_url': self.url, 'status': 'queued', 'downloaded': 0, 'total': None}

    def partial(self, content):
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.with_name(self.target.name + '.dgx-part').write_bytes(content)
        self.target.with_name(self.target.name + '.dgx-source').write_text(hashlib.sha256(self.url.encode()).hexdigest())

    async def test_download_is_written_to_model_folder(self):
        job = self.job()
        with patch.object(module, 'allowed_url'):
            await module.download(job, self.target)
        self.assertEqual(job['status'], 'complete')
        self.assertEqual(self.target.read_bytes(), self.data)
        self.assertNotIn('_url', module.public_job(job))

    async def test_existing_model_is_not_overwritten(self):
        self.target.parent.mkdir()
        self.target.write_bytes(b'existing model')
        job = self.job()
        await module.download(job, self.target)
        self.assertEqual(job['status'], 'present')
        self.assertEqual(self.target.read_bytes(), b'existing model')
        self.assertEqual(self.ranges, [])

    async def test_resume_uses_range_and_produces_exact_file(self):
        self.partial(self.data[:100])
        job = self.job()
        with patch.object(module, 'allowed_url'):
            await module.download(job, self.target)
        self.assertEqual(self.ranges, ['bytes=100-'])
        self.assertEqual(self.target.read_bytes(), self.data)
        self.assertEqual(job['downloaded'], len(self.data))

    async def test_finished_partial_is_published_after_restart(self):
        self.partial(self.data)
        job = self.job()
        with patch.object(module, 'allowed_url'):
            await module.download(job, self.target)
        self.assertEqual(job['status'], 'complete')
        self.assertEqual(self.target.read_bytes(), self.data)

    async def test_ignored_range_restarts_instead_of_appending(self):
        self.partial(self.data[:100])
        self.ignore_range = True
        with patch.object(module, 'allowed_url'):
            await module.download(self.job(), self.target)
        self.assertEqual(self.target.read_bytes(), self.data)

    async def test_interrupted_download_is_not_published_and_can_resume(self):
        self.interrupt = True
        job = self.job()
        with patch.object(module, 'allowed_url'):
            await module.download(job, self.target)
            self.assertEqual(job['status'], 'error')
            self.assertFalse(self.target.exists())
            await module.download(job, self.target)
        self.assertEqual(job['status'], 'complete')
        self.assertEqual(self.target.read_bytes(), self.data)
        self.assertEqual(self.ranges[1], 'bytes=100-')

    async def test_html_error_is_not_saved_as_model(self):
        self.html = True
        job = self.job()
        with patch.object(module, 'allowed_url'):
            await module.download(job, self.target)
        self.assertEqual(job['status'], 'error')
        self.assertFalse(self.target.exists())

    async def test_paths_and_download_sources_are_restricted(self):
        valid = {'name': 'model.safetensors', 'directory': 'vae', 'url': 'https://huggingface.co/org/repo/resolve/main/model.safetensors'}
        self.assertEqual(module.destination(valid), self.target)
        for changes in [{'name': '../escape.safetensors'}, {'name': '/tmp/escape.pt'}, {'directory': 'custom_nodes'}, {'directory': 'configs'}, {'name': 'code.py'}, {'url': 'http://127.0.0.1/model.pt'}, {'url': 'https://attacker.example/model.pt'}, {'url': 'https://huggingface.co.attacker.example/a.pt'}, {'url': 'https://github.com/org/repo/blob/main/code.py'}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                module.destination(valid | changes)
        outside = Path(self.temp.name).parent
        (Path(self.temp.name) / 'loras').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            module.destination(valid | {'directory': 'loras'})

    async def test_batch_is_serialized_and_duplicate_requests_are_reused(self):
        release = asyncio.Event()
        started = asyncio.Event()
        calls = []

        async def fetch(job, target):
            calls.append(job['name'])
            started.set()
            await release.wait()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self.data)

        first = {'name': 'first.safetensors', 'directory': 'vae', 'url': 'https://huggingface.co/org/repo/resolve/main/first.safetensors'}
        second = first | {'name': 'second.safetensors'}
        headers = {'X-DGX-Download': '1'}
        with patch.object(module, 'fetch_file', side_effect=fetch):
            response = await self.client.post('/dgx-downloads/jobs', json=[first, second], headers=headers)
            self.assertEqual(response.status, 202)
            await asyncio.wait_for(started.wait(), 1)
            response = await self.client.post('/dgx-downloads/jobs', json=[first], headers=headers)
            self.assertEqual(response.status, 202)
            self.assertEqual(len(module.TASKS), 2)
            self.assertEqual(calls, ['first.safetensors'])
            release.set()
            await asyncio.wait_for(asyncio.gather(*module.TASKS), 1)
        self.assertEqual(calls, ['first.safetensors', 'second.safetensors'])
        response = await self.client.get('/dgx-downloads/jobs')
        jobs = await response.json()
        self.assertTrue(all(j['status'] == 'complete' and '_url' not in j for j in jobs))

    async def test_conflicting_batch_is_rejected_before_starting_downloads(self):
        first = {'name': 'first.safetensors', 'directory': 'vae', 'url': 'https://huggingface.co/org/repo/resolve/main/first.safetensors'}
        second = first | {'url': 'https://huggingface.co/other/repo/resolve/main/first.safetensors'}
        response = await self.client.post('/dgx-downloads/jobs', json=[first, second], headers={'X-DGX-Download': '1'})
        self.assertEqual(response.status, 400)
        self.assertEqual(module.JOBS, {})

    async def test_post_requires_json_header_and_same_origin(self):
        response = await self.client.post('/dgx-downloads/jobs', json=[])
        self.assertEqual(response.status, 403)
        response = await self.client.post('/dgx-downloads/jobs', json=[], headers={'X-DGX-Download': '1', 'Origin': 'https://attacker.example'})
        self.assertEqual(response.status, 403)
        response = await self.client.post('/dgx-downloads/jobs', json=[{'name': '../escape.pt', 'directory': 'vae', 'url': self.url}], headers={'X-DGX-Download': '1'})
        self.assertEqual(response.status, 400)
        self.assertEqual(module.JOBS, {})


if __name__ == '__main__':
    unittest.main()
