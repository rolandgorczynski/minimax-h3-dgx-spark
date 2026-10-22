"""ComfyUI API client: only submit our own graphs and clean our own sessions."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


class ComfyError(RuntimeError):pass


class Comfy:
    def __init__(self,url,store,timeout=3600,poll=2):
        self.url=url.rstrip('/');self.store=store;self.timeout=timeout;self.poll=poll
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(self,method,path,data=None,limit=40_000_000):
        payload=json.dumps(data).encode() if data is not None else None
        req=urllib.request.Request(self.url+path,data=payload,method=method,headers={'Content-Type':'application/json'})
        try:
            with self.opener.open(req,timeout=45) as response:
                content=response.read(limit+1)
                if len(content)>limit:raise ComfyError('ComfyUI-Antwort zu groß.')
                return json.loads(content) if 'json' in response.headers.get('Content-Type','') else content
        except urllib.error.HTTPError as exc:
            detail=exc.read(12000).decode(errors='replace')
            raise ComfyError(f'ComfyUI HTTP {exc.code}: {detail}') from exc

    def matching(self,session,step,search_history=False):
        queue=self.request('GET','/queue')
        for entry in [*queue['queue_running'],*queue['queue_pending']]:
            extra=entry[3]
            if extra.get('comic_automation_session')==session and extra.get('comic_automation_step')==step:return entry[1]
        if not search_history:return None
        history=self.request('GET','/history?max_items=20',limit=100_000_000)
        for ident,run in reversed(list(history.items())):
            extra=run['prompt'][3]
            if extra.get('comic_automation_session')==session and extra.get('comic_automation_step')==step:return ident
        return None

    def run(self,session,step,graph,workflow=None):
        result_path=self.store.directory(session)/'checkpoints'/(step+'.json')
        if result_path.exists():return json.loads(result_path.read_text())
        doc=self.store.get(session);record=doc['steps'].get(step,{})
        ident=record.get('prompt_id') or self.matching(session,step,doc.get('recovering',False))
        if not ident:
            extra={'comic_automation_session':session,'comic_automation_step':step}
            if workflow:extra['extra_pnginfo']={'workflow':workflow}
            reply=self.request('POST','/prompt',{'prompt':graph,'client_id':'comic-automation-'+session,'extra_data':extra})
            if reply.get('node_errors'):raise ComfyError(json.dumps(reply['node_errors']))
            ident=reply['prompt_id']
        doc=self.store.get(session);steps=doc['steps'];steps[step]={'prompt_id':ident,'status':'running'}
        self.store.update(session,steps=steps)
        start=time.monotonic()
        while True:
            history=self.request('GET','/history/'+urllib.parse.quote(ident,safe=''))
            if ident in history:
                run=history[ident]
                if run.get('status',{}).get('status_str')=='error':
                    errors=[data.get('exception_message','ComfyUI-Ausführung fehlgeschlagen.') for kind,data in run['status']['messages'] if kind=='execution_error']
                    raise ComfyError('; '.join(errors) or 'ComfyUI-Ausführung fehlgeschlagen.')
                if run.get('status',{}).get('completed'):
                    result=run['outputs'];self.store.write(session,'checkpoints/'+step+'.json',result)
                    doc=self.store.get(session);steps=doc['steps'];steps[step]['status']='completed';self.store.update(session,steps=steps,recovering=False)
                    return result
            if time.monotonic()-start>self.timeout:
                raise ComfyError(f'Zeitlimit für eigenen ComfyUI-Auftrag {ident}; laufende Aufgaben werden nicht abgebrochen.')
            time.sleep(self.poll)

    def download(self,session,descriptor):
        prefix='comic-automation/'+session
        folder=descriptor.get('subfolder','')
        if descriptor.get('type')!='temp' or not (folder==prefix or folder.startswith(prefix+'/')) or any(part in ('.','..') for part in folder.split('/')) or '\\' in folder or '/' in descriptor.get('filename','') or '..' in descriptor.get('filename',''):
            raise ComfyError('Unerwarteter Ausgabepfad; keine fremden Ergebnisse abrufen.')
        data=self.request('GET','/view?'+urllib.parse.urlencode(descriptor))
        if not isinstance(data,bytes) or not data.startswith(b'\x89PNG\r\n\x1a\n'):raise ComfyError('Ungültiges PNG-Ergebnis.')
        return data

    def cleanup(self,session):
        # The extension refuses cleanup while one of our tagged graphs is still queued/running.
        self.request('DELETE','/dgx-comics/automation/'+session)
        steps=self.store.get(session)['steps']
        ids=[v['prompt_id'] for v in steps.values() if v.get('prompt_id')]
        if ids:self.request('POST','/history',{'delete':ids})
        self.store.update(session,cleanup_pending=False,cleanup_error=None)
