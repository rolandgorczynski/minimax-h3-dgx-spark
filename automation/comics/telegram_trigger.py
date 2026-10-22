"""Optional, allowlisted Telegram polling; no public webhook or remote models."""
import json
import logging
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request
import uuid

from engine import STYLES, TERMINAL, validate_request

LOG=logging.getLogger('comic-telegram')
ALIASES=dict(zip(('klassisch','noir','ligne','manga','aquarell'),STYLES))
HELP=('Sende ein Thema als Nachricht oder:\n/comic 12 noir Eine geheimnisvolle Nacht im Archiv\n'
      'Ohne Thema erfinde ich selbst eine Geschichte.\n'
      'Stile: noir, klassisch, ligne, manga, aquarell. Kacheln: 1–12.\n'
      '/status zeigt deinen letzten Auftrag. Alle Geschichten sind auf Deutsch.')


def parse_message(text):
    text=text.strip()
    if not text:raise ValueError('Bitte ein Thema oder /comic senden.')
    if text.startswith('/'):
        parts=text.split(maxsplit=1);command=parts[0];text=parts[1] if len(parts)>1 else ''
        if command.split('@')[0].lower()!='/comic':raise ValueError('Unbekannter Befehl. '+HELP)
        text=text.strip()
    result={};parts=text.split(maxsplit=1);first=parts[0] if parts else '';rest=parts[1] if len(parts)>1 else ''
    if first.isdigit():result['kacheln']=int(first);text=rest.strip()
    parts=text.split(maxsplit=1);first=parts[0] if parts else '';rest=parts[1] if len(parts)>1 else ''
    if first.lower() in ALIASES:result['stil']=ALIASES[first.lower()];text=rest.strip()
    result['thema']=text
    return result


class TelegramError(RuntimeError):
    def __init__(self,message,retry_after=30):super().__init__(message);self.retry_after=retry_after


class BotAPI:
    def __init__(self,token):
        if not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]{20,}',token):raise ValueError('Ungültiges Bot-Token-Format.')
        self.token=token
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def call(self,method,data=None,file=None):
        if method not in ('getMe','getWebhookInfo','getUpdates','sendMessage','sendDocument'):raise ValueError('Telegram-Methode nicht erlaubt.')
        data=data or {};headers={}
        if file:
            path=Path(file)
            if path.stat().st_size>49_000_000:raise TelegramError('Comic zu groß für Telegram; bitte in der Oberfläche herunterladen.',3600)
            boundary='comic-'+uuid.uuid4().hex;parts=[]
            for key,value in data.items():parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
            parts.extend([f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="comic.png"\r\nContent-Type: image/png\r\n\r\n'.encode(),path.read_bytes(),f'\r\n--{boundary}--\r\n'.encode()])
            payload=b''.join(parts);headers['Content-Type']='multipart/form-data; boundary='+boundary
        else:payload=json.dumps(data).encode();headers['Content-Type']='application/json'
        request=urllib.request.Request('https://api.telegram.org/bot'+self.token+'/'+method,data=payload,headers=headers)
        try:
            with self.opener.open(request,timeout=45) as response:value=json.loads(response.read(5_000_000))
        except urllib.error.HTTPError as exc:
            try:value=json.loads(exc.read(10000))
            except (ValueError,UnicodeError):value={}
            description=str(value.get('description','Telegram HTTP '+str(exc.code))).replace(self.token,'[redacted]')[:300]
            raise TelegramError(description,max(10,min(3600,int(value.get('parameters',{}).get('retry_after',30))))) from None
        except Exception:
            # Never expose urllib's URL: it contains the token.
            raise TelegramError('Telegram nicht erreichbar oder ungültige Antwort.') from None
        if not value.get('ok'):raise TelegramError('Telegram hat die Anfrage abgelehnt.')
        return value['result']


class TelegramTrigger:
    def __init__(self,store,stop,token='',allowed='',public_url='http://192.168.1.224:8090',api=None):
        self.store=store;self.stop=stop;self.allowed={int(x.strip()) for x in allowed.split(',') if x.strip()}
        self.api=api or (BotAPI(token) if token else None);self.public_url=public_url.rstrip('/')
        self.bot_id=None;self.username='';self.status='disabled';self.error=None
        if token or api:
            self.status='configured' if self.allowed else 'missing_chat_allowlist'

    def info(self):return {'status':self.status,'configured':bool(self.api),'allowed_chats':len(self.allowed),'bot_username':self.username or None,'error':self.error}

    def initialize(self):
        if not self.api or not self.allowed:return False
        me=self.api.call('getMe');self.bot_id=me['id'];self.username=me['username']
        if self.api.call('getWebhookInfo').get('url'):
            raise TelegramError('Bot verwendet bereits einen Webhook. Bitte einen eigenen Comic-Bot verwenden; der Webhook wird nicht verändert.',300)
        key='telegram-offset:'+str(self.bot_id)
        if self.store.integration_get(key) is None:
            # First activation discards old backlog; later restarts resume the saved cursor.
            old=self.api.call('getUpdates',{'offset':-1,'timeout':0,'allowed_updates':['message']})
            self.store.integration_set(key,max((u['update_id']+1 for u in old),default=0))
        self.status='polling';self.error=None;return True

    def handle(self,update):
        message=update.get('message')
        if not message:return
        chat=message.get('chat',{}).get('id')
        if chat not in self.allowed or message.get('from',{}).get('is_bot'):return
        text=message.get('text','').strip()
        if not text:return
        head=text.split()[0]
        if head.startswith('/') and '@' in head and head.split('@',1)[1].casefold()!=self.username.casefold():return
        command=head.split('@',1)[0].casefold()
        if command in ('/start','/help','/hilfe'):
            self.api.call('sendMessage',{'chat_id':chat,'text':HELP});return
        if command=='/status':
            job=self.store.telegram_latest(self.bot_id,chat)
            self.api.call('sendMessage',{'chat_id':chat,'text':f'Auftrag {job["id"]}: {job["status"]} · {job["stage"]}\n{self.public_url}' if job else 'Noch kein Comic-Auftrag in diesem Chat.'});return
        try:
            ident=uuid.uuid5(uuid.NAMESPACE_URL,f'comic-telegram:{self.bot_id}:{chat}:{message["message_id"]}').hex
            request=validate_request({**parse_message(text),'seed':int(ident[:8],16)%2147483648})
            self.store.create(ident,request)
            self.store.telegram_attach(self.bot_id,chat,ident)
        except (ValueError,OverflowError) as exc:
            self.api.call('sendMessage',{'chat_id':chat,'text':str(exc)[:3500]})

    def poll_once(self):
        key='telegram-offset:'+str(self.bot_id);offset=self.store.integration_get(key)
        for update in self.api.call('getUpdates',{'offset':offset,'timeout':15,'limit':20,'allowed_updates':['message']}):
            self.handle(update)
            self.store.integration_set(key,update['update_id']+1)

    def deliver(self):
        for binding in self.store.telegram_pending(self.bot_id):
            chat=binding['chat_id'];ident=binding['job_id']
            if chat not in self.allowed or binding['retry_at']>time.time():continue
            job=self.store.get(ident)
            if not job:continue
            try:
                if not binding['ack_sent']:
                    self.api.call('sendMessage',{'chat_id':chat,'text':f'Comic-Auftrag angenommen: {ident}\n{job["request"]["kacheln"]} Kacheln · Deutsch\n{self.public_url}'})
                    self.store.telegram_update(ident,ack_sent=1)
                if job['status'] not in TERMINAL:continue
                label={'completed':'Comic fertig.','needs_review':'Comic erstellt; automatische Prüfung meldet noch offene Punkte.','failed':'Comic-Auftrag fehlgeschlagen.'}[job['status']]
                text=label+'\nAuftrag: '+ident+'\n'+self.public_url
                if job['status']=='failed':text+='\n'+str(job.get('error',''))[:1200]
                if any(a['name']=='comic.png' for a in job.get('artifacts',[])):
                    self.api.call('sendDocument',{'chat_id':chat,'caption':text},file=self.store.directory(ident)/'comic.png')
                else:self.api.call('sendMessage',{'chat_id':chat,'text':text})
                self.store.telegram_update(ident,result_sent=1,retry_at=0)
            except TelegramError as exc:
                self.store.telegram_update(ident,retry_at=time.time()+exc.retry_after)
                self.error=str(exc)

    def worker(self):
        if not self.api or not self.allowed:return
        while not self.stop.is_set():
            try:
                if self.status!='polling' and not self.initialize():return
                self.error=None;self.deliver();self.poll_once()
            except Exception as exc:
                self.status='retrying';self.error=str(exc) if isinstance(exc,TelegramError) else 'Interner Telegram-Fehler; Verbindung wird erneut versucht.'
                LOG.warning('%s',self.error)
                self.stop.wait(exc.retry_after if isinstance(exc,TelegramError) else 30)
