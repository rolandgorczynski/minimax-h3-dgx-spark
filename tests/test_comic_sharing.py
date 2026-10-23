"""Bildfreigabe verwendet bestehende Pixel und entfernt Workflow-Metadaten."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
import uuid
import zipfile
from PIL import Image
from PIL.PngImagePlugin import PngInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
from sharing import settings,save_settings,clean_png,manifest,bundle,image
from storage import Store
from engine import validate_request
from app import Service,Handler,ThreadingHTTPServer


def png():
    data=io.BytesIO();meta=PngInfo();meta.add_text('workflow','PRIVATE FIGURE REFERENCES');meta.add_text('prompt','PRIVATE ARTICLE')
    Image.new('RGB',(16,16),'red').save(data,format='PNG',pnginfo=meta);return data.getvalue()


class SharingTests(unittest.TestCase):
    def test_image_pixels_stay_exact_and_private_metadata_is_removed(self):
        original=png();result=clean_png(original)
        self.assertNotIn(b'PRIVATE',result)
        with Image.open(io.BytesIO(original)) as before,Image.open(io.BytesIO(result)) as after:
            self.assertEqual(before.tobytes(),after.tobytes());self.assertNotIn('workflow',after.info)
        with self.assertRaises(ValueError):clean_png(original[:-8])
        broken=bytearray(original);broken[22]^=1
        with self.assertRaises(ValueError):clean_png(bytes(broken))

    def test_targets_start_empty_and_are_user_configurable(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root);self.assertEqual(settings(store),{'substack_url':'','x_url':''})
            value={'substack_url':'https://substack.com/@beispiel','x_url':'https://x.com/beispiel'}
            save_settings(store,value);self.assertEqual(settings(Store(root)),value)
            for address in ['javascript:alert(1)','http://substack.com/@name','https://user:password@example.com']:
                with self.assertRaises(ValueError):save_settings(store,{**value,'substack_url':address})

    def test_authenticated_download_does_not_start_or_change_jobs(self):
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'DATA_DIR':root,'WORKFLOW_TEMPLATE':str(Path(__file__).resolve().parents[1]/'examples/comics/workflows/04_Comic_Automat_9B.json'),'LLM_BACKEND':'comfyui','API_TOKEN':'test'}):
            service=Service();ident=uuid.uuid4().hex
            service.store.create(ident,validate_request({'kacheln':1}),initial_status='editing')
            service.store.write(ident,'panels/01_panel.png',png());service.store.write(ident,'characters.json',{'secret':'KEEP PRIVATE'})
            service.store.write(ident,'story.json',{'title':'Der Comic','story':'PRIVATE ARTICLE'})
            service.store.stage(ident,'finished',status='needs_review',artifacts=[{'name':'panels/01_panel.png'}])
            before=service.store.get(ident);server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.service=service
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base='http://127.0.0.1:'+str(server.server_port)
            def call(path,auth=True,data=None):
                return urllib.request.urlopen(urllib.request.Request(base+path,data=json.dumps(data).encode() if data else None,method='PUT' if data else 'GET',headers={'Authorization':'Bearer test'} if auth else {}))
            try:
                with self.assertRaises(urllib.error.HTTPError) as missing:call('/jobs/'+ident+'/share',auth=False)
                self.assertEqual(missing.exception.code,401)
                with call('/sharing',data={'substack_url':'https://substack.com/@test','x_url':''}) as r:self.assertEqual(json.load(r)['substack_url'],'https://substack.com/@test')
                with call('/jobs/'+ident+'/share') as r:info=json.load(r)
                self.assertFalse(info['published']);self.assertEqual(len(info['images']),1)
                with call(info['download_url']) as r,zipfile.ZipFile(io.BytesIO(r.read())) as archive:
                    self.assertEqual(set(archive.namelist()),{'01.png','Beitragstext.txt','Anleitung.txt'})
                    self.assertNotIn(b'PRIVATE',archive.read('01.png'))
                with call(info['images'][0]['url']) as r:self.assertTrue(r.read().startswith(b'\x89PNG'))
                self.assertEqual(service.store.get(ident),before);self.assertEqual(len(service.store.list()),1)
            finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
