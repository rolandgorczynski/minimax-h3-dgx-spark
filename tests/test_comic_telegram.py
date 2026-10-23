"""Telegram trigger ownership, deduplication and durable delivery; no real messages."""
import io
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'automation/comics'))
from storage import Store
from telegram_trigger import TelegramTrigger,TelegramError,BotAPI,parse_message
from engine import validate_request


class FakeAPI:
    def __init__(self):self.calls=[];self.updates=[];self.webhook='';self.fail=False
    def call(self,method,data=None,file=None):
        self.calls.append((method,data,file))
        if method=='getMe':return {'id':42,'username':'ComicBot'}
        if method=='getWebhookInfo':return {'url':self.webhook}
        if method=='getUpdates':return self.updates[-1:] if data.get('offset')==-1 else [u for u in self.updates if u['update_id']>=data.get('offset',0)]
        if self.fail:raise TelegramError('Temporary delivery error',30)
        return {'message_id':999}


def message(number=1,chat=123,text='/comic 4 noir Ein verlorener Schlüssel'):
    return {'update_id':number,'message':{'message_id':number,'chat':{'id':chat},'from':{'id':chat,'is_bot':False},'text':text}}


class TelegramTests(unittest.TestCase):
    def make(self,root,api):return TelegramTrigger(Store(root),threading.Event(),allowed='123',api=api)

    def test_parser_and_fixed_german_policy(self):
        self.assertEqual(parse_message('/comic\n4 manga Ein alter Brief'),{'kacheln':4,'stil':'Manga Schwarzweiß','thema':'Ein alter Brief'})
        self.assertEqual(validate_request(parse_message('/comic'))['sprache'],'de')
        self.assertEqual(parse_message('Ein Hausmeister entdeckt einen Raum')['thema'],'Ein Hausmeister entdeckt einen Raum')
        with self.assertRaises(ValueError):validate_request(parse_message('/comic 0 noir'))

    def test_initial_backlog_is_skipped_and_cursor_survives_restart(self):
        with tempfile.TemporaryDirectory() as root:
            api=FakeAPI();api.updates=[message(50)]
            trigger=self.make(root,api);trigger.initialize();trigger.poll_once()
            self.assertEqual(trigger.store.list(),[])
            api.updates.append(message(51));trigger.poll_once()
            self.assertEqual(len(trigger.store.list()),1)
            self.assertEqual(Store(root).integration_get('telegram-offset:42'),52)
            restarted=self.make(root,api);restarted.initialize();restarted.poll_once()
            self.assertEqual(len(restarted.store.list()),1)
            self.assertEqual(sum(method=='getUpdates' and data.get('offset')==-1 for method,data,_ in api.calls),1)

    def test_foreign_chats_bots_and_other_bot_commands_are_ignored(self):
        with tempfile.TemporaryDirectory() as root:
            api=FakeAPI();trigger=self.make(root,api);trigger.initialize();api.calls=[]
            trigger.handle(message(chat=456));trigger.handle(message(text='/comic@OtherBot 4 noir'))
            update=message();update['message']['from']['is_bot']=True;trigger.handle(update)
            trigger.handle({'channel_post':message()['message']})
            self.assertEqual(trigger.store.list(),[]);self.assertEqual(api.calls,[])

    def test_deduplication_result_delivery_and_restart(self):
        with tempfile.TemporaryDirectory() as root:
            api=FakeAPI();trigger=self.make(root,api);trigger.initialize()
            trigger.handle(message());trigger.handle(message());self.assertEqual(len(trigger.store.list()),1)
            ident=trigger.store.list()[0]['id'];trigger.deliver();trigger.deliver()
            self.assertEqual(sum(method=='sendMessage' for method,_,_ in api.calls),1)
            trigger.store.write(ident,'comic.png',b'png-test');trigger.store.update(ident,status='needs_review',artifacts=[{'name':'comic.png'}])
            trigger.deliver();self.make(root,api).initialize()
            trigger.deliver()
            documents=[(data,file) for method,data,file in api.calls if method=='sendDocument']
            self.assertEqual(len(documents),1);self.assertEqual(documents[0][0]['chat_id'],123)
            self.assertIn('offene Punkte',documents[0][0]['caption'])

    def test_delivery_retry_and_missing_credentials_do_not_start_jobs(self):
        with tempfile.TemporaryDirectory() as root:
            api=FakeAPI();trigger=self.make(root,api);trigger.initialize();trigger.handle(message());api.fail=True
            trigger.deliver();binding=trigger.store.telegram_pending(42)[0]
            self.assertFalse(binding['ack_sent']);self.assertGreater(binding['retry_at'],0)
            api.fail=False
            with patch('telegram_trigger.time.time',return_value=binding['retry_at']+1):trigger.deliver()
            self.assertTrue(trigger.store.telegram_pending(42)[0]['ack_sent'])
            disabled=TelegramTrigger(trigger.store,threading.Event());self.assertFalse(disabled.initialize())
            self.assertEqual(disabled.info()['status'],'disabled')
            api.calls=[]
            unlisted=TelegramTrigger(trigger.store,threading.Event(),api=api)
            self.assertFalse(unlisted.initialize());self.assertEqual(api.calls,[])

    def test_existing_webhook_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as root:
            api=FakeAPI();api.webhook='https://existing.example/webhook';trigger=self.make(root,api)
            with self.assertRaises(TelegramError):trigger.initialize()
            self.assertEqual([method for method,_,_ in api.calls],['getMe','getWebhookInfo'])

    def test_bot_token_is_redacted_in_network_errors(self):
        token='123:'+('x'*30);api=BotAPI(token)
        error=urllib.error.HTTPError('https://api.telegram.org/bot'+token+'/getMe',401,'Unauthorized',{},io.BytesIO(json.dumps({'description':'Invalid token '+token}).encode()))
        with patch.object(api.opener,'open',side_effect=error):
            with self.assertRaises(TelegramError) as caught:api.call('getMe')
            self.assertNotIn(token,str(caught.exception));self.assertNotIn('https://',str(caught.exception))

    def test_setup_keeps_credentials_private_and_does_not_overwrite(self):
        script=Path(__file__).resolve().parents[1]/'scripts/setup_comic_telegram.py'
        spec=importlib.util.spec_from_file_location('comic_telegram_setup',script);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as root:
            module.ROOT=Path(root);folder=module.ROOT/'automation/comics';folder.mkdir(parents=True)
            api=FakeAPI();api.updates=[message()];token='123:'+('x'*30);output=io.StringIO()
            with patch.object(module,'BotAPI',return_value=api),patch.object(module.getpass,'getpass',return_value=token),patch('builtins.input',side_effect=['','123']),patch('sys.stdout',output):module.main()
            target=folder/'.env.telegram'
            self.assertEqual(target.stat().st_mode&0o777,0o600)
            self.assertIn(token,target.read_text());self.assertNotIn(token,output.getvalue())
            before=target.read_text()
            with self.assertRaises(ValueError):module.main()
            self.assertEqual(target.read_text(),before)
