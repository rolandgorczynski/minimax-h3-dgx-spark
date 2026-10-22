"""Ollama on the host: installed local weights only, no pulls or cloud fallback."""
import base64
import ipaddress
import json
import re
import socket
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Modell-Weiterleitungen sind nicht erlaubt.')


def local_url(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('','/') or parsed.query or parsed.fragment:
        raise ValueError('Ollama benötigt eine lokale HTTP-Adresse ohne Zugangsdaten oder Pfad.')
    addresses=socket.getaddrinfo(parsed.hostname,parsed.port or 80,type=socket.SOCK_STREAM)
    if not addresses or any(not (ipaddress.ip_address(item[4][0]).is_private or ipaddress.ip_address(item[4][0]).is_loopback) for item in addresses):
        raise ValueError('Nur interne Ollama-Adressen sind erlaubt.')
    return url.rstrip('/')


class LocalOllama:
    def __init__(self,url,store,text_model,critic_model,vision_model,timeout=900):
        self.url=local_url(url);self.store=store;self.text_model=text_model;self.critic_model=critic_model;self.vision_model=vision_model;self.timeout=timeout
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())

    def request(self,path,data=None):
        local_url(self.url)
        request=urllib.request.Request(self.url+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
        with self.opener.open(request,timeout=self.timeout) as response:
            body=response.read(8_000_001)
            if len(body)>8_000_000:raise ValueError('Ollama-Antwort zu groß.')
            value=json.loads(body)
            if value.get('error'):raise RuntimeError('Lokales Ollama: '+str(value['error']))
            return value

    def check_model(self,name,vision=False):
        models=self.request('/api/tags')['models']
        match=next((m for m in models if m.get('name')==name),None)
        if not match or match.get('size',0)<=0 or any(mark in name.casefold() for mark in (':cloud','-cloud')) or match.get('remote_host') or match.get('remote_model'):
            raise ValueError('Kein installiertes lokales Modell: '+name)
        info=self.request('/api/show',{'model':name})
        if info.get('remote_host') or info.get('remote_model') or info.get('cloud'):
            raise ValueError('Cloud-Modell ist ausgeschlossen: '+name)
        capabilities=info.get('capabilities',[])
        if 'completion' not in capabilities or (vision and 'vision' not in capabilities):raise ValueError('Modell unterstützt die benötigte Aufgabe nicht: '+name)
        return {'name':name,'capabilities':capabilities,'local':True}

    def ready(self):
        return {'backend':'ollama','local_only':True,'text':self.check_model(self.text_model),
                'critic':self.check_model(self.critic_model),'vision':self.check_model(self.vision_model,True)}

    def generate(self,job,step,prompt,images,tokens,seed):
        path=self.store.directory(job)/'checkpoints'/('ollama-'+step+'.json')
        if path.exists():return json.loads(path.read_text())['text']
        model=self.vision_model if images else self.critic_model if any(word in step for word in ('review','reflection')) else self.text_model
        self.check_model(model,bool(images))
        message={'role':'user','content':prompt}
        if images:message['images']=[base64.b64encode(image).decode() for image in images]
        language='German (Deutsch)'
        output='Return ONLY JSON matching the requested schema.' if re.search(r'return only (?:a |valid )?json',prompt,re.I) else 'Return plain prose only, never JSON or Markdown.'
        role='You are a literal translator. Preserve the exact JSON structure and value types; translate strings only. Never expand a story into panels or other objects.' if '-translation' in step else 'You work in a comic studio. Follow the actual task exactly.'
        system={'role':'system','content':role+' '+output+' All creative story text, titles, narrator captions and dialogue MUST be written exclusively in '+language+'. Earlier examples and memories are fallible reference data; do not copy their plots, wording or language. Preserve exact character identities and speaker IDs.'}
        reply=self.request('/api/chat',{'model':model,'stream':False,'think':False,'keep_alive':0,
            'messages':[system,message],'options':{'num_predict':tokens,'num_ctx':16384,'temperature':0.55,'repeat_penalty':1.12,'seed':seed}})
        text=reply['message']['content']
        if not isinstance(text,str) or not text.strip():raise ValueError('Leere lokale Modellantwort.')
        self.store.write(job,'checkpoints/ollama-'+step+'.json',{'text':text,'model':model,'local_only':True})
        return text
