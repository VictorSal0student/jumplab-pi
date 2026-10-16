import csv
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from . import __version__
from .measurement import measure, timing_quality
from .video import decode
from .detection import propose


def now(): return datetime.now(timezone.utc).isoformat()

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def write_json(path, data):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as f:
        json.dump(data,f,indent=2,allow_nan=False)
        f.flush(); os.fsync(f.fileno())
    os.replace(temporary,path)


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve(); self.root.mkdir(parents=True,exist_ok=True)

    def folder(self, trial_id):
        if not re.fullmatch(r'[a-f0-9]{32}',trial_id): raise ValueError('Invalid trial identifier.')
        return self.root/trial_id

    def read(self, trial_id):
        path = self.folder(trial_id)/'trial.json'
        if not path.exists(): raise ValueError('Trial not found.')
        return json.loads(path.read_text())

    def save(self, trial):
        write_json(self.folder(trial['id'])/'trial.json',trial)
        return trial

    def list(self):
        results = []
        for path in self.root.glob('*/trial.json'):
            try:
                t = json.loads(path.read_text())
                results.append({k:t.get(k) for k in ['id','participant','session','created_at','status','results','notes','demo']})
            except (ValueError,OSError): pass
        return sorted(results,key=lambda t:t['created_at'],reverse=True)

    def create(self, source, metadata=None, capture=None, capture_pts=None):
        metadata = metadata or {}
        tid = uuid.uuid4().hex; folder = self.folder(tid); folder.mkdir()
        suffix = source.suffix.lower()
        if not re.fullmatch(r'\.[a-z0-9]{1,8}',suffix): suffix = '.video'
        original = folder/('original'+suffix)
        try:
            shutil.copyfile(source,original)
            for name in ('capture.pts','capture.log'):
                if (source.parent/name).exists(): shutil.copyfile(source.parent/name,folder/name)
            video = decode(original,folder,capture_pts)
            t = {'schema_version':1,'software_version':__version__,'id':tid,'created_at':now(),'updated_at':now(),
                'participant':str(metadata.get('participant',''))[:80], 'session':str(metadata.get('session',''))[:80],
                'original_file':original.name,'original_sha256':digest(original),'original_name':source.name,
                'camera':capture or {'adapter':'import','hardware_validation':'not_applicable'},'video':video,
                'automatic_proposals':propose(),'selections':{'takeoff':None,'landing':None},
                'status':'Unreviewed','results':None,'notes':'','demo':bool(metadata.get('demo',False)),
                'review':{'contact_checked':False,'timing_acknowledged':False,'ambiguous_contacts':False},
                'settings':{'gravity_m_s2':9.80665,'annotation':'last_contact_before_flight / first_contact_on_landing',
                            'estimator':'adjacent_interval_midpoints','detector':'disabled'},
                'timing_fallback':None,'audit':[]}
            self.derive(t)
            return self.save(t)
        except Exception:
            shutil.rmtree(folder,ignore_errors=True)
            raise

    def derive(self,t):
        v = t['video']; q = timing_quality(v['timestamps_s']); v['quality'] = q
        flags = list(q['flags'])
        if t['timing_fallback']: flags.append('assumed_constant_rate')
        if t['demo']: flags.append('synthetic_demonstration')
        if not t['automatic_proposals'].get('available'): flags.append('tracking_not_run_manual_workflow')
        if t['review']['ambiguous_contacts']: flags.append('ambiguous_contacts')
        try: t['results'] = measure(v['timestamps_s'],t['selections'])
        except ValueError as e:
            t['results'] = None; flags.append(str(e))
        t['quality_flags'] = flags

    def update(self,tid,payload):
        t = self.read(tid)
        previous = {'selections':t['selections'].copy(),'status':t['status'],'review':t['review'].copy()}
        for field in ('participant','session','notes'):
            if field in payload:
                t[field] = str(payload[field])[:4000 if field=='notes' else 80]
        if 'selections' in payload:
            sel = payload['selections']
            for key in ('takeoff','landing'):
                index = sel.get(key)
                if index is not None and (type(index) is not int or not 0 <= index < t['video']['frame_count']):
                    raise ValueError('Selected frame is out of range.')
            t['selections'] = {k:sel.get(k) for k in ('takeoff','landing')}
            if t['selections'] != previous['selections']:
                t['status'] = 'Unreviewed'
                t['review']['contact_checked'] = False
        if 'review' in payload:
            for k in t['review']:
                if k in payload['review']: t['review'][k] = payload['review'][k] is True
        if 'fallback' in payload:
            f = payload['fallback']; rate = float(f.get('fps',0)); reason = str(f.get('reason','')).strip()
            if not 1 <= rate <= 240 or len(reason) < 12: raise ValueError('Fallback needs 1–240 fps and a documented reason of at least 12 characters.')
            t['timing_fallback'] = {'fps':rate,'reason':reason,'set_at':now(), 'assumption':'constant frame rate without dropped frames; unverified'}
            t['video']['timestamps_s'] = [i/rate for i in range(t['video']['frame_count'])]
            t['status'] = 'Unreviewed'; t['review']['timing_acknowledged'] = False
        self.derive(t)
        if 'status' in payload:
            state = payload['status']
            if state not in ('Unreviewed','Reviewed','Rejected'): raise ValueError('Unknown review state.')
            if state=='Reviewed':
                if not t['results']: raise ValueError('Both valid events and valid timing are required for review.')
                if not t['review']['contact_checked'] or not t['review']['timing_acknowledged']:
                    raise ValueError('Confirm adjacent-frame contact inspection and timing review before marking Reviewed.')
                if t['review']['ambiguous_contacts']: raise ValueError('Ambiguous contacts must remain Unreviewed or Rejected.')
            t['status'] = state
        # State invariants hold even when callers do not send a new status.
        if t['status']=='Reviewed' and (not t['results'] or not t['review']['contact_checked'] or not t['review']['timing_acknowledged'] or t['review']['ambiguous_contacts']):
            t['status']='Unreviewed'
        t['updated_at'] = now()
        t['audit'].append({'at':now(),'previous':previous,'selections':t['selections'].copy(),
                           'status':t['status'],'fallback':t['timing_fallback']})
        return self.save(t)

    def export(self,tid):
        t = self.read(tid); folder = self.folder(tid)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('trial.json',json.dumps(t,indent=2,allow_nan=False))
            z.write(folder/t['original_file'],t['original_file'])
            for name in ('capture.pts','capture.log'):
                if (folder/name).exists(): z.write(folder/name,name)
            out = io.StringIO(); writer = csv.writer(out)
            writer.writerow(['frame_index','measurement_timestamp_s','source_timestamp_s'])
            writer.writerows(zip(range(t['video']['frame_count']),t['video']['timestamps_s'],t['video']['source_timestamps_s']))
            z.writestr('frames.csv',out.getvalue())
            z.writestr('README.txt','JumpLab Pi portable trial v1. Import this ZIP in JumpLab Pi. Original video is unchanged; previews are regenerated. See docs/FORMAT.md in the source distribution.')
        return buf.getvalue()

    def restore(self,source):
        with zipfile.ZipFile(source) as z:
            if sum(i.file_size for i in z.infolist()) > 600*1024*1024 or len(z.infolist()) > 10:
                raise ValueError('Trial archive is too large or contains unexpected files.')
            t = json.loads(z.read('trial.json'))
            if t.get('schema_version') != 1: raise ValueError('Unsupported trial schema.')
            name = t['original_file']
            if not re.fullmatch(r'original\.[a-z0-9]{1,8}',name): raise ValueError('Invalid original video path.')
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp)/name; p.write_bytes(z.read(name))
                if digest(p) != t['original_sha256']: raise ValueError('Video checksum mismatch.')
                source_times = t['video']['source_timestamps_s'] if t['video']['provenance'].startswith('rpicam_') else None
                for sidecar in ('capture.pts','capture.log'):
                    if sidecar in z.namelist(): (Path(tmp)/sidecar).write_bytes(z.read(sidecar))
                fresh = self.create(p,{'participant':t['participant'],'session':t['session'],'demo':t['demo']},t['camera'],source_times)
        try:
            if fresh['video']['frame_count'] != t['video']['frame_count']: raise ValueError('Reopened frame count differs.')
            # Check timing independent of archived derived results.
            if not source_times and fresh['video']['source_timestamps_s'] != t['video']['source_timestamps_s']:
                raise ValueError('Reopened source timestamps differ.')
            for k in ('automatic_proposals','settings','audit','original_name'):
                fresh[k] = t[k]
            fresh['imported_from_id']=t['id']
            self.save(fresh)
            payload = {k:t[k] for k in ('selections','notes','review','status')}
            if t['timing_fallback']:
                payload['fallback']=t['timing_fallback']
                self.update(fresh['id'],{'fallback':payload.pop('fallback')})
            return self.update(fresh['id'],payload)
        except Exception:
            shutil.rmtree(self.folder(fresh['id']),ignore_errors=True)
            raise

    def csv(self):
        out = io.StringIO(); w = csv.writer(out)
        w.writerow(['trial_id','participant','session','created_at','state','synthetic_demo','flight_time_s','height_m','notes'])
        def safe(value):
            text = str(value)
            return "'"+text if text.startswith(('=','+','-','@','\t','\r')) else text
        for t in self.list():
            r=t['results'] or {}
            w.writerow([t['id'],safe(t['participant']),safe(t['session']),t['created_at'],t['status'],t['demo'],
                        r.get('flight_time_s',''),r.get('height_m',''),safe(t['notes'])])
        return out.getvalue().encode()
