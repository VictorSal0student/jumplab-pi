"""Convenience launcher; application code remains in jumplab-pi/."""
import argparse
import shutil
import sys
import threading
import webbrowser
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Check dependencies without starting')
    args = parser.parse_args()
    missing = [name for name in ('ffmpeg', 'ffprobe') if not shutil.which(name)]
    if missing:
        print('Missing tools in PATH: ' + ', '.join(missing))
        print('Read DEMARRER_SUR_PC.md, install FFmpeg, then reopen this launcher.')
        return 1
    print('Python, FFmpeg and FFprobe found.')
    if args.check:
        return 0
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'jumplab-pi'))
    from jumplab.server import make_server
    try:
        server = make_server(Path.home() / 'JumpLabPi-data', 8765)
    except OSError as error:
        print('Cannot start the local server:', error)
        print('If another JumpLab instance is running, open http://127.0.0.1:8765.')
        return 1
    print('JumpLab Pi: http://127.0.0.1:8765')
    print('Keep this terminal open. Press Ctrl+C to stop. No Raspberry Pi is needed for import mode.')
    threading.Timer(0.8, lambda: webbrowser.open('http://127.0.0.1:8765')).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
