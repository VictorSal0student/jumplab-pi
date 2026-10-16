import copy
import io
import json
import math
import tempfile
import unittest
import zipfile
from pathlib import Path
from jumplab.measurement import G, measure, timing_quality
from jumplab.storage import Store
from jumplab.video import decode, run

SAMPLE=Path(__file__).resolve().parents[1]/'samples/synthetic-jump.mp4'

class MeasurementTests(unittest.TestCase):
    def test_known_height_and_intervals(self):
        r=measure([i/100 for i in range(100)],{'takeoff':10,'landing':61})
        self.assertAlmostEqual(r['flight_time_s'],.5)
        self.assertAlmostEqual(r['height_m'],.3064578125)
        self.assertAlmostEqual(r['flight_time_bounds_s'][0],.49)
        self.assertAlmostEqual(r['flight_time_bounds_s'][1],.51)
    def test_invalid_order_boundaries(self):
        for a,b in [(3,2),(1,1),(1,2),(-1,4),(4,8),(None,4),(True,4)]:
            with self.subTest(a=a,b=b),self.assertRaises(ValueError): measure([i/30 for i in range(6)],{'takeoff':a,'landing':b})
    def test_invalid_timing(self):
        for times in ([0,None,.2],[0,.1,.1],[0,.2,.1],[0,float('nan'),.3],[0,float('inf'),1],[]):
            with self.subTest(times=times):
                self.assertFalse(timing_quality(times)['valid'])
                with self.assertRaises(ValueError): measure(times,{'takeoff':0,'landing':2})
    def test_vfr_and_gaps(self):
        times=[0,.01,.02,.12,.13,.14]
        q=timing_quality(times)
        self.assertEqual(q['gap_indices'],[2]);self.assertIn('variable_frame_intervals',q['flags'])
        r=measure(times,{'takeoff':1,'landing':4})
        self.assertAlmostEqual(r['flight_time_s'],.11)

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=Store(self.root/'trials')
        self.trial=self.store.create(SAMPLE,{'participant':'P01','session':'test','demo':True})
    def tearDown(self): self.tmp.cleanup()
    def test_decode_identity_and_timestamps(self):
        t=self.trial; self.assertEqual(t['video']['frame_count'],90)
        self.assertEqual(len(list((self.store.folder(t['id'])/'frames').glob('*.jpg'))),90)
        self.assertAlmostEqual(t['video']['timestamps_s'][45],1.5)
        # Sequential decode of exactly frame 45 must match the cached displayed image.
        expected=self.root/'expected.jpg'
        run(['ffmpeg','-v','error','-i',str(SAMPLE),'-vf',"select=eq(n\\,45)",'-vsync','0','-frames:v','1','-q:v','3','-threads','1',str(expected)])
        self.assertEqual(expected.read_bytes(),(self.store.folder(t['id'])/'frames/000045.jpg').read_bytes())
    def test_review_and_proposal_preservation(self):
        tid=self.trial['id'];original={'available':True,'events':{'takeoff':28,'landing':46},'method':'test fixture only'}
        self.trial['automatic_proposals']=copy.deepcopy(original);self.store.save(self.trial)
        t=self.store.update(tid,{'selections':{'takeoff':29,'landing':45}})
        self.assertEqual(t['automatic_proposals'],original)
        with self.assertRaises(ValueError): self.store.update(tid,{'status':'Reviewed'})
        t=self.store.update(tid,{'review':{'contact_checked':True,'timing_acknowledged':True},'status':'Reviewed'})
        self.assertEqual(t['status'],'Reviewed')
        t=self.store.update(tid,{'selections':{'takeoff':28,'landing':45}})
        self.assertEqual(t['status'],'Unreviewed');self.assertEqual(t['automatic_proposals'],original)
    def test_ambiguous_rejected(self):
        t=self.store.update(self.trial['id'],{'selections':{'takeoff':29,'landing':45},'review':{'contact_checked':True,'timing_acknowledged':True,'ambiguous_contacts':True},'status':'Rejected'})
        self.assertEqual(t['status'],'Rejected')
        with self.assertRaises(ValueError):self.store.update(t['id'],{'status':'Reviewed'})
    def test_save_export_reopen(self):
        t=self.store.update(self.trial['id'],{'selections':{'takeoff':29,'landing':45},'notes':'visible feet','review':{'contact_checked':True,'timing_acknowledged':True},'status':'Reviewed'})
        reopened=Store(self.root/'trials').read(t['id']);self.assertEqual(t,reopened)
        archive=self.root/'trial.zip';archive.write_bytes(self.store.export(t['id']))
        restored=self.store.restore(archive)
        for key in ('results','selections','automatic_proposals','notes','status','original_sha256'):self.assertEqual(t[key],restored[key])
        self.assertNotEqual(restored['id'],t['id'])
    def test_missing_timing_fallback_preserves_source(self):
        t=self.trial;t['video']['timestamps_s']=[None]*90;t['video']['source_timestamps_s']=[None]*90
        self.store.save(t)
        t=self.store.update(t['id'],{'selections':{'takeoff':29,'landing':45}});self.assertIsNone(t['results'])
        with self.assertRaises(ValueError):self.store.update(t['id'],{'fallback':{'fps':30,'reason':'guess'}})
        t=self.store.update(t['id'],{'fallback':{'fps':30,'reason':'External verified nominal rate; no dropped frames assumed'}})
        self.assertIsNotNone(t['results']);self.assertEqual(t['video']['source_timestamps_s'],[None]*90)
        self.assertIn('assumed_constant_rate',t['quality_flags'])
    def test_failed_import_leaves_existing_trial(self):
        p=self.root/'broken.mp4';p.write_text('not video')
        with self.assertRaises(ValueError):self.store.create(p)
        self.assertEqual(len(self.store.list()),1)
        self.assertEqual(self.store.read(self.trial['id'])['id'],self.trial['id'])
    def test_csv_unavailable_not_zero_and_formula_escape(self):
        self.store.update(self.trial['id'],{'notes':'=1+1'})
        data=self.store.csv().decode();self.assertIn("'=1+1",data);self.assertIn(',,,',data)
    def test_archive_tamper(self):
        t=self.trial;t['original_sha256']='bad'
        path=self.root/'tampered.zip'
        with zipfile.ZipFile(path,'w') as z:
            z.writestr('trial.json',json.dumps(t));z.write(SAMPLE,t['original_file'])
        with self.assertRaises(ValueError):self.store.restore(path)

class VariableRateDecodeTests(unittest.TestCase):
    def test_raw_video_missing_times_and_camera_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);src=p/'raw.h264'
            run(['ffmpeg','-v','error','-i',str(SAMPLE),'-c:v','copy','-bsf:v','h264_mp4toannexb',str(src)])
            raw=decode(src,p)
            self.assertFalse(raw['quality']['valid'])
            self.assertIsNone(raw['source_timestamps_s'][0])
            times=[5+i/30 for i in range(90)]
            timed=decode(src,p,capture_pts=times)
            self.assertTrue(timed['quality']['valid'])
            self.assertEqual(timed['source_timestamps_s'],times)
            self.assertAlmostEqual(timed['timestamps_s'][45],1.5)
            with self.assertRaises(ValueError):decode(src,p,capture_pts=times[:-1])

    def test_vfr_decoded_pts(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);src=p/'vfr.mkv'
            run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=160x120:rate=30:duration=1',
                 '-vf',"setpts=if(lt(N\\,15)\\,N/(30*TB)\\,(0.5+(N-15)/15)/TB)",
                 '-vsync','0','-c:v','ffv1','-threads','1',str(src)])
            t=decode(src,p)
            self.assertEqual(t['frame_count'],30)
            self.assertIn('variable_frame_intervals',t['quality']['flags'])
            self.assertAlmostEqual(t['timestamps_s'][16]-t['timestamps_s'][15],.067,places=3)
            self.assertAlmostEqual(t['timestamps_s'][1]-t['timestamps_s'][0],.033,places=3)

if __name__=='__main__':unittest.main()
