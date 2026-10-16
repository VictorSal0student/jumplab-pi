import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from jumplab.server import make_server

class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.server=make_server(self.tmp.name,0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):self.server.shutdown();self.server.server_close();self.tmp.cleanup()
    def test_offline_assets(self):
        for name in ('/','/app.js','/style.css','/api/trials'):
            with urllib.request.urlopen(self.base+name) as r:self.assertEqual(r.status,200)
    def test_token_and_host_protection(self):
        with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(urllib.request.Request(self.base+'/api/demo',data=b'{}',method='POST'))
        with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(urllib.request.Request(self.base+'/',headers={'Host':'untrusted.test'}))
    def test_invalid_json(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(urllib.request.Request(self.base+'/api/camera',data=b'{bad',headers={'X-JumpLab-Token':self.server.app.token},method='POST'))
        self.assertEqual(ctx.exception.code,400)

if __name__=='__main__':unittest.main()
