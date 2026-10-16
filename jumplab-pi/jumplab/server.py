"""Loopback-only, single-user offline HTTP application."""
import argparse
import json
import mimetypes
import secrets
import shutil
import tempfile
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
from . import __version__, capture
from .storage import Store

STATIC = Path(__file__).parent/'static'
SAMPLE = Path(__file__).resolve().parent.parent/'samples'/'synthetic-jump.mp4'
MAX_UPLOAD = 256*1024*1024


class Application:
    def __init__(self,root):
        self.store=Store(root); self.token=secrets.token_urlsafe(32)
        self.lock=threading.Lock(); self.job=None; self.camera={'available':False,'message':'Camera not checked • import ready'}

    def start_job(self,work):
        if not self.lock.acquire(blocking=False): raise ValueError('Another capture/import is running. Wait for it to finish.')
        job={'id':secrets.token_hex(8),'state':'running','message':'Processing locally…'}; self.job=job
        def worker():
            try:
                trial=work(); job.update(state='done',trial_id=trial['id'],message='Ready for frame inspection')
            except Exception as e:
                job.update(state='error',message=str(e)); traceback.print_exc()
            finally: self.lock.release()
        threading.Thread(target=worker,daemon=True).start()
        return job.copy()


def make_server(root,port=8765):
    app=Application(root)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send(self,status,body,kind='application/json',download=None):
            if kind=='application/json': body=json.dumps(body,allow_nan=False).encode()
            if isinstance(body,str): body=body.encode()
            self.send_response(status); self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' blob:; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            if download: self.send_header('Content-Disposition','attachment; filename="'+download+'"')
            self.end_headers(); self.wfile.write(body)
        def guard(self,write=False):
            port=self.server.server_port
            host=self.headers.get('Host','')
            if host not in (f'127.0.0.1:{port}',f'localhost:{port}'):
                raise ValueError('This application only accepts local browser requests.')
            if write and (self.headers.get('X-JumpLab-Token')!=app.token or self.headers.get('Origin',f'http://{host}')!=f'http://{host}'):
                raise ValueError('Invalid local request token. Reload JumpLab Pi.')
        def do_GET(self):
            try:
                self.guard(); path=urlparse(self.path).path; parts=path.strip('/').split('/')
                if path=='/api/config': return self.send(200,{'version':__version__,'token':app.token,'camera':app.camera})
                if path=='/api/job': return self.send(200,app.job)
                if path=='/api/trials': return self.send(200,app.store.list())
                if path=='/api/history.csv': return self.send(200,app.store.csv(),'text/csv','jumplab-history.csv')
                if len(parts)>=3 and parts[:2]==['api','trials']:
                    t=app.store.read(parts[2])
                    if len(parts)==3: return self.send(200,t)
                    if len(parts)==4 and parts[3]=='export': return self.send(200,app.store.export(t['id']),'application/zip',t['id']+'.zip')
                    if len(parts)==5 and parts[3]=='frames':
                        index=int(parts[4])
                        if not 0<=index<t['video']['frame_count']: raise ValueError('Frame index out of bounds.')
                        return self.send(200,(app.store.folder(t['id'])/'frames'/f'{index:06d}.jpg').read_bytes(),'image/jpeg')
                if path=='/': path='/index.html'
                if path in ('/index.html','/app.js','/style.css'):
                    p=STATIC/path[1:]
                    return self.send(200,p.read_bytes(),mimetypes.guess_type(p.name)[0])
                self.send(404,{'error':'Not found'})
            except (ValueError,KeyError,FileNotFoundError) as e: self.send(400,{'error':str(e)})
        def do_POST(self):
            tmp=None
            try:
                self.guard(True); path=urlparse(self.path).path
                length=int(self.headers.get('Content-Length','0'))
                if length<0 or length>MAX_UPLOAD: raise ValueError('Maximum upload size is 256 MiB.')
                if path=='/api/import':
                    if app.lock.locked(): raise ValueError('Another import/capture is running.')
                    name=Path(unquote(self.headers.get('X-Filename','video.mp4'))).name
                    tmp=tempfile.TemporaryDirectory(); p=Path(tmp.name)/name
                    remaining=length
                    with p.open('wb') as f:
                        while remaining:
                            block=self.rfile.read(min(1024*1024,remaining))
                            if not block: raise ValueError('Upload ended before all bytes arrived.')
                            f.write(block); remaining-=len(block)
                    metadata=json.loads(unquote(self.headers.get('X-Metadata','{}')))
                    owned=tmp
                    def work():
                        try: return app.store.restore(p) if p.suffix.lower()=='.zip' else app.store.create(p,metadata)
                        finally: owned.cleanup()
                    job=app.start_job(work); tmp=None
                    return self.send(202,job)
                if length>16384: raise ValueError('JSON request too large.')
                payload=json.loads(self.rfile.read(length) or b'{}')
                if path=='/api/camera':
                    app.camera=capture.status(); return self.send(200,app.camera)
                if path=='/api/demo':
                    if not SAMPLE.exists(): raise ValueError('Bundled sample is missing.')
                    return self.send(202,app.start_job(lambda:app.store.create(SAMPLE,{'participant':'DEMO','session':'Synthetic example','demo':True})))
                if path=='/api/record':
                    def work():
                        with tempfile.TemporaryDirectory() as temp:
                            p,pts,meta=capture.record(Path(temp),payload.get('seconds',5))
                            return app.store.create(p,payload,meta,pts)
                    return self.send(202,app.start_job(work))
                if path.startswith('/api/trials/') and len(path.split('/'))==4:
                    if app.lock.locked(): raise ValueError('Wait for processing to finish before editing.')
                    with app.lock: trial=app.store.update(path.rsplit('/',1)[-1],payload)
                    return self.send(200,trial)
                self.send(404,{'error':'Not found'})
            except (ValueError,KeyError,OSError,TypeError) as e:
                self.send(400,{'error':str(e)})
            finally:
                if tmp: tmp.cleanup()
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.app=app
    return server


def main():
    p=argparse.ArgumentParser(); p.add_argument('--data',default=str(Path.home()/'JumpLabPi-data')); p.add_argument('--port',type=int,default=8765)
    args=p.parse_args(); server=make_server(args.data,args.port)
    print(f'JumpLab Pi {__version__} • http://127.0.0.1:{server.server_port} • data: {server.app.store.root}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
