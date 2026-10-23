"""HTTP-Verwaltung mit Versionskonflikt, Löschschutz und Authentifizierung."""
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

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from app import Service,Handler,ThreadingHTTPServer
from test_comic_stories import definition


class StoriesHTTPTests(unittest.TestCase):
    def test_authenticated_crud_and_generation_snapshot(self):
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'DATA_DIR':root,'WORKFLOW_TEMPLATE':str(Path(__file__).resolve().parents[1]/'examples/comics/workflows/04_Comic_Automat_9B.json'),'LLM_BACKEND':'comfyui','API_TOKEN':'test'}):
            service=Service();cleaned=[];service.cleanup=cleaned.append
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.service=service
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base='http://127.0.0.1:'+str(server.server_port)
            def call(path,method='GET',data=None,auth=True):
                req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,method=method,headers={'Authorization':'Bearer test'} if auth else {})
                try:
                    with urllib.request.urlopen(req) as r:return r.status,json.load(r)
                except urllib.error.HTTPError as exc:return exc.code,json.load(exc)
            try:
                self.assertEqual(call('/stories',auth=False)[0],401)
                self.assertEqual(len(call('/styles')[1]['styles']),11)
                status,story=call('/stories','POST',definition());self.assertEqual(status,201)
                ident=story['id'];updated={**definition(),'version':1,'name':'Bearbeitet'}
                self.assertEqual(call('/stories/'+ident,'PATCH',updated)[0],200)
                self.assertEqual(call('/stories/'+ident,'PATCH',updated)[0],409)
                self.assertEqual(call('/stories/'+ident+'/generate','POST',{'version':1})[0],409)
                status,job=call('/stories/'+ident+'/generate','POST',{'version':2});self.assertEqual(status,202)
                self.assertEqual(call('/stories/'+ident,'DELETE',{'version':2})[0],409)
                self.assertEqual(call('/jobs/'+job['id'],'DELETE',{})[0],409)
                service.store.stage(job['id'],'finished',status='needs_review')
                service.store.write(job['id'],'story.json',{'title':'HG1','story':'Ein Text.'})
                source=json.loads((service.store.directory(job['id'])/'editorial-source.json').read_text())
                service.store.write(job['id'],'characters.json',source['characters'])
                from feedback import CRITERIA
                self.assertEqual(call('/jobs/'+job['id']+'/feedback','POST',{'bewertungen':{key:3 for key in CRITERIA},'kommentar':'Bitte Bild 1 verbessern.'})[0],200)
                self.assertEqual(call('/jobs/'+job['id']+'/improve','POST',{'stil':'Retro-Zeitungscomic','kacheln':9})[0],400)
                code,improved=call('/jobs/'+job['id']+'/improve','POST',{'stil':'Retro-Zeitungscomic'})
                self.assertEqual(code,202);self.assertEqual(improved['request']['kacheln'],job['request']['kacheln'])
                self.assertEqual(improved['request']['stil'],'Retro-Zeitungscomic')
                self.assertEqual(call('/jobs/'+job['id'],'DELETE',{})[0],409)
                service.store.stage(improved['id'],'finished',status='needs_review')
                self.assertEqual(call('/stories/'+ident,'DELETE',{'version':2})[0],200)
                self.assertEqual(call('/stories/'+ident)[0],404)
                self.assertEqual(call('/jobs/'+job['id'])[0],404)
                self.assertIn(job['id'],cleaned)
            finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
