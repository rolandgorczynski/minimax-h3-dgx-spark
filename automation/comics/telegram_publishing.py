"""Explizite Kanalveröffentlichung; keine Zeitsteuerung und keine automatischen Posts."""
import io
import json
import os
import re
import tempfile
import threading
from pathlib import Path
from PIL import Image
import sharing
from telegram_trigger import BotAPI,TelegramError

KEY='telegram-publishing-channel'

class Publisher:
    def __init__(self,store,api=None):
        self.store=store;self.lock=threading.RLock()
        token=os.getenv('TELEGRAM_PUBLISH_BOT_TOKEN','')
        self.api=api or (BotAPI(token) if token else None)

    def check(self,channel):
        if not self.api:raise ValueError('Telegram-Bot-Token ist lokal noch nicht konfiguriert.')
        if not isinstance(channel,str):raise ValueError('Kanal als @Benutzername oder numerische Kanal-ID eingeben.')
        channel=channel.strip()
        if channel.startswith('https://t.me/'):channel='@'+channel.removeprefix('https://t.me/').rstrip('/')
        if not re.fullmatch(r'@[A-Za-z][A-Za-z0-9_]{4,31}|-100[0-9]+',channel):raise ValueError('Kanal als @Benutzername oder numerische Kanal-ID eingeben.')
        me=self.api.call('getMe');chat=self.api.call('getChat',{'chat_id':channel})
        if chat.get('type')!='channel':raise ValueError('Das Veröffentlichungsziel muss ein Telegram-Kanal sein.')
        member=self.api.call('getChatMember',{'chat_id':chat['id'],'user_id':me['id']})
        if member.get('status') not in ('administrator','creator') or member.get('status')!='creator' and not member.get('can_post_messages'):
            raise ValueError('Der Bot braucht im Kanal das Administratorrecht „Nachrichten veröffentlichen“.')
        return {'channel':('@'+chat['username']) if chat.get('username') else str(chat['id']),'channel_id':chat['id'],'title':chat.get('title',''),'bot_username':me.get('username','')}

    def configure(self,value):
        if not isinstance(value,dict) or set(value)!={'channel'}:raise ValueError('Kanal angeben.')
        with self.lock:
            result=self.check(value['channel']);self.store.integration_set(KEY,result)
            return self.info()

    def record_key(self,ident,channel_id):return 'telegram-publication:'+ident+':'+str(channel_id)

    def info(self,ident=None,verify=False):
        saved=self.store.integration_get(KEY) or {}
        result={'configured':bool(self.api),'target':saved,'ready':False,'publication':None}
        if saved:
            if verify:
                try:
                    current=self.check(str(saved['channel_id']))
                    if current['channel_id']!=saved['channel_id']:raise ValueError('Kanal stimmt nicht überein.')
                    result['target']=current;result['ready']=True
                except (ValueError,TelegramError) as exc:result['error']=str(exc)
            else:result['ready']=bool(self.api)
            if ident:result['publication']=self.store.integration_get(self.record_key(ident,saved['channel_id']))
        return result

    def prepare_photo(self,data):
        with Image.open(io.BytesIO(data)) as source:
            image=source.convert('RGB');width,height=image.size
            if max(width,height)/min(width,height)>20:raise ValueError('Comic zu lang für ein Telegram-Foto. Bitte eine Ausgabe mit einzelnen Kacheln oder Seiten verwenden.')
            if width+height<=10000 and len(data)<=9_500_000:return data,'.png'
            scale=min(1,9900/(width+height));image=image.resize((max(1,int(width*scale)),max(1,int(height*scale))))
            for quality in (95,90,85):
                buf=io.BytesIO();image.save(buf,'JPEG',quality=quality)
                if buf.tell()<=9_500_000:return buf.getvalue(),'.jpg'
        raise ValueError('Bild zu groß für Telegram. Bitte kleinere Comic-Seiten verwenden.')

    def publish(self,job,value):
        if not isinstance(value,dict) or set(value)!={'post_version','channel_id'} or type(value['channel_id']) is not int:raise ValueError('Beitragsversion und Kanal-ID angeben.')
        with self.lock:
            target=self.store.integration_get(KEY)
            if not target or target['channel_id']!=value['channel_id']:raise ValueError('Veröffentlichungsziel geändert. Teilen-Dialog neu öffnen.')
            key=self.record_key(job['id'],target['channel_id']);old=self.store.integration_get(key)
            if old:
                if old['status']=='sent':return old
                raise ValueError('Für diese Ausgabe besteht bereits ein Versandversuch. Bitte zuerst den Kanal prüfen; ein erneuter Versand wird zum Schutz vor Doppelposts nicht automatisch gestartet.')
            target=self.check(str(target['channel_id']))
            info=sharing.manifest(self.store,job)
            if type(value['post_version']) is not int or info['post_version']!=value['post_version']:raise ValueError('Beitragstext inzwischen geändert. Teilen-Dialog neu öffnen.')
            text=info['text']
            units=len(text.encode('utf-16-le'))//2
            if units>4096:raise ValueError('Telegram-Begleittext maximal 4096 Zeichen. Bitte kürzen.')
            # Alle Bilder prüfen, bevor die erste Nachricht versendet wird.
            with tempfile.TemporaryDirectory(prefix='comic-telegram-') as directory:
                paths=[]
                for i in range(len(info['images'])):
                    data,suffix=self.prepare_photo(sharing.image(self.store,job,i));path=Path(directory)/(str(i)+suffix);path.write_bytes(data);paths.append(path)
                if not paths:raise ValueError('Keine Comic-Bilder vorhanden.')
                record={'status':'sending','channel_id':target['channel_id'],'channel':target['channel'],'message_ids':[],'url':'','post_version':info['post_version'],'image_count':len(paths)}
                # Prozessübergreifende Reservierung bleibt auch nach einem Neustart erhalten.
                with self.store.connect() as db:
                    inserted=db.execute('INSERT OR IGNORE INTO integration_state (key,value) VALUES (?,?)',(key,json.dumps(record))).rowcount
                if not inserted:raise ValueError('Dieser Comic wird bereits veröffentlicht. Kanal prüfen.')
                def remember(messages):
                    if isinstance(messages,dict):messages=[messages]
                    record['message_ids'].extend(m['message_id'] for m in messages)
                    if record['message_ids']:
                        prefix='https://t.me/'+target['channel'][1:] if target['channel'].startswith('@') else 'https://t.me/c/'+str(target['channel_id'])[4:]
                        record['url']=prefix+'/'+str(record['message_ids'][0])
                    self.store.integration_set(key,record)
                try:
                    long_text=units>1024
                    if long_text:remember(self.api.call('sendMessage',{'chat_id':target['channel_id'],'text':text}))
                    for offset in range(0,len(paths),10):
                        batch=paths[offset:offset+10];caption=(info['title'] if long_text else text) if offset==0 else ''
                        if len(batch)==1:
                            remember(self.api.call('sendPhoto',{'chat_id':target['channel_id'],'caption':caption},files={'photo':batch[0]}))
                        else:
                            media=[{'type':'photo','media':'attach://image'+str(i),**({'caption':caption} if i==0 and caption else {})} for i in range(len(batch))]
                            remember(self.api.call('sendMediaGroup',{'chat_id':target['channel_id'],'media':json.dumps(media,ensure_ascii=False)},files={'image'+str(i):path for i,path in enumerate(batch)}))
                    record['status']='sent';self.store.integration_set(key,record);return record
                except Exception:
                    record['status']='uncertain';record['error']='Versand nicht vollständig bestätigt. Vor einem erneuten Versand den Kanal prüfen.';self.store.integration_set(key,record)
                    raise TelegramError(record['error']) from None
