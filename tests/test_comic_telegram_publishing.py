"""Kanalversand ausschließlich gegen eine Attrappe, ohne echte Telegram-Nachrichten."""
import io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
from storage import Store
from telegram_publishing import Publisher
from telegram_trigger import TelegramError

class API:
    def __init__(self):self.calls=[];self.counter=100;self.fail_album=0;self.albums=0;self.permission=True
    def call(self,method,data=None,files=None):
        self.calls.append((method,data,files))
        if method=='getMe':return {'id':42,'username':'comic_bot'}
        if method=='getChat':return {'id':-10012345,'username':'test_channel','title':'Testkanal','type':'channel'}
        if method=='getChatMember':return {'status':'administrator','can_post_messages':self.permission}
        if method=='sendMediaGroup':
            self.albums+=1
            if self.fail_album==self.albums:raise TelegramError('Netzwerkfehler')
            count=len(json.loads(data['media']))
            assert 2<=count<=10 and len(files)==count
            for path in files.values():assert Path(path).read_bytes().startswith(b'\x89PNG')
        else:count=1
        result=[]
        for _ in range(count):self.counter+=1;result.append({'message_id':self.counter})
        return result if method=='sendMediaGroup' else result[0]

class PublishingTests(unittest.TestCase):
    def fixture(self,root,count=12,text='Titel\n\nEin Geist im Wald.'):
        store=Store(root);api=API();pub=Publisher(store,api);pub.configure({'channel':'@test_channel'})
        job={'id':'a'*32,'status':'completed'}
        image=io.BytesIO();Image.new('RGB',(64,64),'white').save(image,'PNG')
        manifest={'post_version':0,'text':text,'title':'Titel','images':[{}]*count}
        return store,api,pub,job,manifest,image.getvalue()
    def publish(self,pub,job):return pub.publish(job,{'channel_id':-10012345,'post_version':0})
    def test_albums_order_caption_and_duplicate_click(self):
        with tempfile.TemporaryDirectory() as root:
            store,api,pub,job,manifest,data=self.fixture(root)
            with patch('sharing.manifest',return_value=manifest),patch('sharing.image',return_value=data):
                result=self.publish(pub,job);self.assertEqual(result['status'],'sent');self.assertEqual(len(result['message_ids']),12)
                self.assertEqual(result['url'],'https://t.me/test_channel/101')
                albums=[c for c in api.calls if c[0]=='sendMediaGroup'];self.assertEqual([len(json.loads(c[1]['media'])) for c in albums],[10,2])
                self.assertEqual(json.loads(albums[0][1]['media'])[0]['caption'],manifest['text'])
                before=len(api.calls);self.assertEqual(self.publish(pub,job),result);self.assertEqual(len(api.calls),before)
    def test_long_text_and_single_remaining_image(self):
        with tempfile.TemporaryDirectory() as root:
            store,api,pub,job,manifest,data=self.fixture(root,11,'Langer Text. '*100)
            with patch('sharing.manifest',return_value=manifest),patch('sharing.image',return_value=data):self.publish(pub,job)
            sent=[c for c in api.calls if c[0].startswith('send')]
            self.assertEqual([c[0] for c in sent],['sendMessage','sendMediaGroup','sendPhoto'])
            self.assertEqual(sent[0][1]['text'],manifest['text']);self.assertEqual(sent[2][1]['caption'],'')
    def test_partial_delivery_blocks_retry_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as root:
            store,api,pub,job,manifest,data=self.fixture(root);api.fail_album=2
            with patch('sharing.manifest',return_value=manifest),patch('sharing.image',return_value=data):
                with self.assertRaises(TelegramError):self.publish(pub,job)
                record=pub.info(job['id'])['publication'];self.assertEqual(record['status'],'uncertain');self.assertEqual(len(record['message_ids']),10)
                other=Publisher(store,api);before=len(api.calls)
                with self.assertRaises(ValueError):self.publish(other,job)
                self.assertEqual(len(api.calls),before)
    def test_permissions_version_and_image_errors_send_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            store,api,pub,job,manifest,data=self.fixture(root)
            with patch('sharing.manifest',return_value=manifest),patch('sharing.image',side_effect=ValueError('Beschädigtes Bild')):
                with self.assertRaises(ValueError):self.publish(pub,job)
            api.permission=False
            with self.assertRaises(ValueError):self.publish(pub,job)
            api.permission=True;manifest['post_version']=1
            with patch('sharing.manifest',return_value=manifest):
                with self.assertRaises(ValueError):self.publish(pub,job)
            self.assertFalse(any(c[0].startswith('send') for c in api.calls));self.assertIsNone(pub.info(job['id'])['publication'])
    def test_only_explicit_rate_limit_is_retried(self):
        with tempfile.TemporaryDirectory() as root:
            store,api,pub,job,manifest,data=self.fixture(root)
            with patch.object(api,'call',side_effect=[TelegramError('Ratenlimit',10,http_status=429),{'message_id':1}]) as call,patch('telegram_publishing.time.sleep') as sleep:
                self.assertEqual(pub.send('sendMessage',{'text':'Test'}),{'message_id':1})
                self.assertEqual(call.call_count,2);sleep.assert_called_once_with(10)
            with patch.object(api,'call',side_effect=TelegramError('Unklare Antwort')) as call:
                with self.assertRaises(TelegramError):pub.send('sendMessage',{'text':'Test'})
                self.assertEqual(call.call_count,1)

    def test_album_transport_uploads_separate_named_files(self):
        from telegram_trigger import BotAPI
        from types import SimpleNamespace
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return b'{"ok":true,"result":[{"message_id":1},{"message_id":2}]}'
        with tempfile.TemporaryDirectory() as root:
            files={}
            for i in range(2):
                path=Path(root)/(str(i)+'.png');path.write_bytes(b'image'+str(i).encode());files['image'+str(i)]=path
            api=BotAPI('123:'+('x'*25));requests=[]
            api.opener=SimpleNamespace(open=lambda request,**kwargs:(requests.append(request) or Response()))
            result=api.call('sendMediaGroup',{'chat_id':-10012345,'media':'[]'},files=files)
            self.assertEqual(len(result),2)
            payload=requests[0].data
            self.assertIn(b'name="image0"',payload);self.assertIn(b'name="image1"',payload)
            self.assertIn(b'image0',payload);self.assertIn(b'image1',payload)
            self.assertNotIn(b'allow_paid_broadcast',payload)

    def test_http_requires_authentication_and_get_never_publishes(self):
        import threading,urllib.request,urllib.error
        from app import Handler,Service,ThreadingHTTPServer
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as root:
            store,api,pub,job,manifest,data=self.fixture(root)
            store.create(job['id'],{});store.stage(job['id'],'finished',status='completed')
            with patch.object(Service,'__init__',lambda self:None):service=Service()
            service.store=store;service.publisher=pub;service.token='test';service.stories=SimpleNamespace(lock=threading.RLock())
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.service=service
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base='http://127.0.0.1:'+str(server.server_port);route='/jobs/'+job['id']+'/share/telegram'
            try:
                for method,path in [('GET','/telegram-publishing'),('PUT','/telegram-publishing'),('POST',route)]:
                    request=urllib.request.Request(base+path,method=method,data=b'{}' if method!='GET' else None)
                    with self.assertRaises(urllib.error.HTTPError) as exc:urllib.request.urlopen(request)
                    self.assertEqual(exc.exception.code,401)
                request=urllib.request.Request(base+route,headers={'Authorization':'Bearer test'})
                with urllib.request.urlopen(request) as response:self.assertTrue(json.load(response)['ready'])
                self.assertFalse(any(c[0].startswith('send') for c in api.calls))
                payload=json.dumps({'channel_id':-10012345,'post_version':0}).encode()
                request=urllib.request.Request(base+route,method='POST',data=payload,headers={'Authorization':'Bearer test'})
                with patch('sharing.manifest',return_value=manifest),patch('sharing.image',return_value=data):
                    with urllib.request.urlopen(request) as response:self.assertEqual(json.load(response)['status'],'sent')
            finally:server.shutdown();server.server_close();thread.join()

    def test_existing_pixels_kept_and_extreme_ratio_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            store,api,pub,job,manifest,data=self.fixture(root)
            self.assertEqual(pub.prepare_photo(data),(data,'.png'))
            image=io.BytesIO();Image.new('RGB',(1024,20)).save(image,'PNG')
            with self.assertRaises(ValueError):pub.prepare_photo(image.getvalue())

if __name__=='__main__':unittest.main()
