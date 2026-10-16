"""Development-only synthetic frame sequence. Requires Pillow, never a human validation."""
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont
root=Path(__file__).resolve().parents[1]
font=ImageFont.load_default()
with tempfile.TemporaryDirectory() as temp:
    for i in range(90):
        im=Image.new('RGB',(640,480),'#e7ebe3'); d=ImageDraw.Draw(im)
        for x in range(0,640,40): d.line((x,0,x,480),fill='#dde3d9')
        for y in range(0,480,40): d.line((0,y,640,y),fill='#dde3d9')
        # Frames 0..29 contact; 30..44 flight; 45 onward contact.
        offset=0 if i<30 or i>=45 else int(15+105*(1-((i-37)/8)**2))
        foot=390-offset
        d.rectangle((0,391,640,480),fill='#cdd8c8'); d.line((0,391,640,391),fill='#688373',width=3)
        d.ellipse((295,foot-210,345,foot-160),fill='#215e56')
        d.line((320,foot-155,320,foot-80),fill='#215e56',width=24)
        d.line((320,foot-140,270,foot-90),fill='#215e56',width=13)
        d.line((320,foot-140,370,foot-90),fill='#215e56',width=13)
        d.line((314,foot-80,300,foot-10),fill='#215e56',width=17)
        d.line((326,foot-80,344,foot-10),fill='#215e56',width=17)
        d.rectangle((284,foot-10,310,foot),fill='#25463e'); d.rectangle((336,foot-10,366,foot),fill='#25463e')
        d.text((22,42),'SYNTHETIC / NOT A HUMAN RECORDING',fill='#36544a',font=font)
        d.text((22,61),f'DECODED FRAME {i:03d}   |   {i/30:.4f} s',fill='#36544a',font=font)
        d.text((22,438),'Practice only: last contact 29 / first landing 45',fill='#36544a',font=font)
        im.save(Path(temp)/f'{i:06d}.png')
    subprocess.run(['ffmpeg','-y','-v','error','-framerate','30','-i',str(Path(temp)/'%06d.png'),'-c:v','libx264','-threads','1','-pix_fmt','yuv420p',str(root/'samples/synthetic-jump.mp4')],check=True)
