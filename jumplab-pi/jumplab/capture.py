"""Optional Raspberry Pi CSI adapter. No simulated capture or inferred frame rate."""
import shutil
from .video import run


def status():
    binary = shutil.which('rpicam-vid') or shutil.which('libcamera-vid')
    if not binary:
        return {'available': False, 'message': 'No camera adapter • import mode', 'adapter': None}
    try:
        result = run([binary,'--list-cameras'], timeout=15)
        listing = result.stdout + result.stderr
        available = 'Available cameras' in listing and '0 :' in listing
        return {'available': available, 'message': 'CSI camera detected • capture unvalidated' if available else 'No CSI camera detected • import mode',
                'adapter': binary, 'listing': listing}
    except ValueError as e:
        return {'available': False, 'message': str(e), 'adapter': binary}


def record(folder, seconds=5):
    info = status()
    if not info['available']: raise ValueError(info['message'])
    seconds = int(seconds)
    if not 2 <= seconds <= 10: raise ValueError('Capture duration must be 2–10 seconds.')
    source, pts = folder/'original.h264', folder/'capture.pts'
    command = [info['adapter'],'--nopreview','--timeout',str(seconds*1000),
        '--width','640','--height','480','--framerate','30','--codec','h264',
        '--save-pts',str(pts),'--output',str(source)]
    result = run(command, timeout=seconds+30)
    (folder/'capture.log').write_text(result.stdout+result.stderr)
    if not pts.exists(): raise ValueError('Camera did not provide a timestamp sidecar.')
    values = [float(line)/1000 for line in pts.read_text().splitlines() if line.strip() and not line.startswith('#')]
    return source, values, {'adapter': info, 'command': command, 'requested_size': [640,480],
        'requested_fps':30, 'duration_requested_s':seconds, 'hardware_validation':'pending',
        'timestamp_semantics':'rpicam --save-pts; exposure/contact correspondence requires hardware validation'}
