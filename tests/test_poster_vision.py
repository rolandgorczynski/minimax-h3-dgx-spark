"""URL normalisation, bounded downloads and image validation without model downloads."""
import importlib.util
from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock
from PIL import Image

SOURCE = Path(__file__).resolve().parents[1]/'extensions/dgx-posters/vision.py'
spec = importlib.util.spec_from_file_location('poster_vision', SOURCE)
vision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vision)


class PosterVisionTests(unittest.TestCase):
    def test_github_blob_and_credentials(self):
        self.assertEqual(vision.normalize_url('https://github.com/user/repo/blob/main/logo.jpeg'),
                         'https://raw.githubusercontent.com/user/repo/main/logo.jpeg')
        for url in ('file:///etc/passwd', 'https://user:password@example.com/image.jpg'):
            with self.assertRaises(ValueError):
                vision.normalize_url(url)

    def test_private_addresses_and_redirects(self):
        addresses = [(2, 1, 6, '', ('169.254.169.254', 80))]
        with patch.object(vision.socket, 'getaddrinfo', return_value=addresses):
            with self.assertRaises(ValueError):
                vision.validate_url('http://metadata.example/image')
            with self.assertRaises(ValueError):
                vision.CheckedRedirect().redirect_request(None, None, 302, '', {}, 'http://metadata.example/image')
        self.assertEqual(vision.validate_url('http://192.168.1.224:8188/view?filename=test.png'),
                         'http://192.168.1.224:8188/view?filename=test.png')
        with patch.object(vision.socket, 'getaddrinfo', return_value=addresses):
            with self.assertRaises(ValueError):
                vision.validate_url('http://192.168.1.224:8188/prompt')

    def download(self, data, length=None):
        response = MagicMock()
        response.__enter__.return_value = response
        response.headers = {'Content-Length': str(length or len(data))}
        response.read.return_value = data
        opener = MagicMock()
        opener.open.return_value = response
        with patch.object(vision.urllib.request, 'build_opener', return_value=opener):
            return vision.load_url('http://127.0.0.1:8188/view?filename=test.png')

    def test_image_decoding_and_limits(self):
        data = BytesIO()
        Image.new('RGB', (30, 20), 'red').save(data, format='PNG')
        self.assertEqual(self.download(data.getvalue()).size, (30, 20))
        with self.assertRaisesRegex(ValueError, '20 MB'):
            self.download(b'', vision.MAX_BYTES+1)
        with self.assertRaisesRegex(ValueError, 'nie zwrócił obrazka'):
            self.download(b'<html>not an image</html>')

    def test_caption_discards_labelled_ocr(self):
        self.assertEqual(vision.clean_caption('Background: Green trees.\nText: RADA KOBIET\nLogo: A crest.\nForeground: A red bag.'),
                         'Background: Green trees.\nForeground: A red bag.')
