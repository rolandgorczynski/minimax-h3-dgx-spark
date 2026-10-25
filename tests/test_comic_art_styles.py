"""Stilbibliothek: vollständige Kataloge, echte Vorschaubilder und sichere Auslieferung."""
import io,json,sys,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import urllib.request,urllib.error
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'automation/comics'))
from art_styles import CATALOG,NAMES,BY_ID,public
from engine import validate_request
from storage import Store
from stories import Stories

class ArtStylesTests(unittest.TestCase):
    def test_catalog_contains_all_promised_directions_and_legacy_names(self):
        self.assertEqual(len(CATALOG),74);self.assertEqual(len(set(NAMES)),74);self.assertEqual(len(BY_ID),74)
        self.assertGreaterEqual(len({s['category'] for s in CATALOG}),10)
        for name in ('Großstadt-Noir (düster)','Epischer Sagencomic','Farbmanga','Mittelalterliche Buchmalerei','Nordische Saga mit Runenornamenten','Chinesische Pinselmalerei','Amerikanischer Superheldencomic','Kosmischer Horror','Glasfensteroptik','Weltraumcomic der 1950er','Stop-Motion-Puppenoptik','Plastische 3D-Animationsoptik'):self.assertIn(name,NAMES)
        for style in CATALOG:
            self.assertEqual(validate_request({'stil':style['name']})['stil'],style['name']);self.assertTrue(style['prompt'].strip());self.assertTrue(style['description'].strip())
        for name in ('Gravierte Dunkelfantasy','Slawische Volkskunst','Historischer Abenteuer-Manga','Filmischer Animationscomic','Rotoskopie','Kohlezeichnung','Schabkarton','Risografie','Isometrischer Comic','Knetfigurenoptik'):
            self.assertIn(name,NAMES)
        self.assertEqual(len({style['prompt'] for style in CATALOG}),len(CATALOG))
        self.assertTrue(all('prompt' not in style for style in public()))

    def test_every_style_has_a_real_small_decodable_preview(self):
        hashes=set();import hashlib
        for style in CATALOG:
            path=ROOT/'automation/comics/style-previews'/(style['id']+'.webp');data=path.read_bytes();hashes.add(hashlib.sha256(data).hexdigest())
            self.assertGreater(len(data),1000)
            with Image.open(io.BytesIO(data)) as image:
                self.assertEqual(image.format,'WEBP');self.assertLessEqual(max(image.size),384);self.assertGreaterEqual(image.width,200)
                self.assertTrue(any(high-low>80 for low,high in image.convert('RGB').getextrema()))
        self.assertEqual(len(hashes),74)

    def test_api_returns_categories_and_only_serves_catalog_assets(self):
        from app import Handler,Service
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(Service,'__init__',lambda self:None):service=Service()
            service.store=Store(folder);service.stories=Stories(service.store);service.token='test'
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.service=service;thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base='http://127.0.0.1:'+str(server.server_port)
            try:
                with urllib.request.urlopen(urllib.request.Request(base+'/styles',headers={'Authorization':'Bearer test'})) as response:
                    result=json.load(response);self.assertEqual(len(result['styles']),74);self.assertEqual(len(result['catalog']),74)
                with urllib.request.urlopen(base+'/style-previews/stil-01.webp') as response:self.assertEqual(response.headers.get('Content-Type'),'image/webp');self.assertTrue(response.read().startswith(b'RIFF'))
                for url in ('/style-previews/unknown.webp','/style-previews/../engine.py','/style-previews/nested/stil-01.webp'):
                    with self.subTest(url=url),self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(base+url)
            finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
