"""Sequential extraction, no browser seek. FFprobe PTS paired with decoded frames."""
import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from .measurement import timing_quality

MAX_FRAMES = 1800

def run(args, timeout=300):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise ValueError('FFmpeg/FFprobe is missing. Follow README installation instructions.')
    except subprocess.TimeoutExpired:
        raise ValueError('Video processing timed out. Try a shorter recording.')
    if p.returncode:
        raise ValueError('Video processing failed: ' + p.stderr[-1500:])
    return p


def decode(source, folder, capture_pts=None):
    start = time.monotonic()
    probe = json.loads(run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-select_streams','v:0',
        '-show_streams','-show_format','-show_frames','-show_entries',
        'frame=pts_time,best_effort_timestamp_time:stream=codec_name,width,height,time_base,avg_frame_rate,r_frame_rate:format=duration,format_name',
        '-of','json',str(source)]).stdout)
    if not probe.get('streams'): raise ValueError('No decodable video stream was found.')
    raw = probe.get('frames', [])
    if not 3 <= len(raw) <= MAX_FRAMES: raise ValueError('Use a short clip containing 3–1800 frames (one jump).')
    frames = folder / 'frames'
    if frames.exists(): shutil.rmtree(frames)
    frames.mkdir()
    # showinfo observes exactly the same sequence sent to the JPEG encoder.
    proc = run(['ffmpeg','-hide_banner','-nostdin','-v','info','-threads','1','-protocol_whitelist','file,pipe',
        '-copyts','-i',str(source),'-map','0:v:0','-an','-sn','-dn','-vf',
        "scale=w='min(960,iw)':h=-2,showinfo",'-vsync','0','-threads','1','-q:v','3',
        '-start_number','0',str(frames/'%06d.jpg')])
    observations = re.findall(r'\bn:\s*(\d+)\s+pts:\s*\S+\s+pts_time:\s*(\S+)', proc.stderr)
    images = list(frames.glob('*.jpg'))
    if len(images) != len(raw) or len(observations) != len(raw):
        raise ValueError('Decoded image/timestamp counts differ; import refused.')
    times = []
    aligned = True
    for i, (frame, (n, shown)) in enumerate(zip(raw, observations)):
        t = float(frame['pts_time']) if 'pts_time' in frame else None
        if int(n) != i: raise ValueError('Decoded frame numbering is inconsistent.')
        if t is not None and abs(t-float(shown)) > max(0.0001, abs(t)*0.00001): aligned = False
        times.append(t)
    if not aligned: raise ValueError('Decoded images and source timestamps do not correspond.')
    provenance = 'ffprobe_frame_pts_time_verified_against_ffmpeg_showinfo'
    if capture_pts is not None:
        if len(capture_pts) != len(raw): raise ValueError('Camera timestamp count differs from decoded frame count.')
        times = capture_pts
        provenance = 'rpicam_save_pts_milliseconds_in_encoded_frame_order'
    quality = timing_quality(times)
    origin = times[0] if quality['valid'] else None
    normalized = [t-origin for t in times] if quality['valid'] else times
    return {'timestamps_s': normalized, 'source_timestamps_s': times, 'time_origin_s': origin,
        'provenance': provenance, 'quality': quality, 'stream': probe['streams'][0],
        'format': probe.get('format',{}), 'frame_count': len(raw),
        'processing_seconds': round(time.monotonic()-start,3),
        'ffmpeg_version': run(['ffmpeg','-version']).stdout.splitlines()[0],
        'preview_max_width': 960}
