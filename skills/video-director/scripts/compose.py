"""合成成片：底层是外部渲染器的帧（例如 Blender，可以有缺帧），上层是透明的叠加层帧，再混入音轨。

用法：
  python compose.py --base render --overlay overlay --audio out/sfx.wav --out out/final.mp4 [--dur 60] [--fps 30]
                    [--crf 23] [--no-grain] [--size 1080x1920]
- 帧号都是“秒 × fps”，四位补零（0000.png）。底层缺的帧用黑帧补上（比如纸面世界期间不渲染 3D，反正会被不透明的叠加层盖住）
- 颗粒和暗角只加在底层（3D），不加在纸面和字幕上。--no-grain 用来量“只看内容”的死帧：颗粒会让冻结的画面也被判成在动
"""
import argparse, os, subprocess

ap = argparse.ArgumentParser()
ap.add_argument('--base', required=True); ap.add_argument('--overlay', required=True)
ap.add_argument('--audio'); ap.add_argument('--out', required=True)
ap.add_argument('--dur', type=float, default=60); ap.add_argument('--fps', type=int, default=30)
ap.add_argument('--crf', default='23'); ap.add_argument('--no-grain', action='store_true')
ap.add_argument('--size', default='1080x1920')
a = ap.parse_args()
W, H = a.size.split('x')
N = round(a.dur * a.fps)

filled = a.base.rstrip('/\\') + '_filled'
os.makedirs(filled, exist_ok=True)
black = os.path.join(filled, '_black.png')
if not os.path.exists(black):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', f'color=c=black:s={W}x{H}', '-frames:v', '1', black], check=True)
missing = 0
for f in range(N):
    dst = os.path.join(filled, f'{f:04d}.png')
    if os.path.exists(dst): os.remove(dst)
    src = os.path.join(a.base, f'{f:04d}.png')
    if not os.path.exists(src): src, missing = black, missing + 1
    os.link(src, dst)                     # 硬链接，不复制图片
print('base frames missing (filled black):', missing)

look = '' if a.no_grain else ',vignette=angle=PI/4.5,noise=alls=5:allf=t'
cmd = ['ffmpeg', '-y', '-loglevel', 'error',
       '-framerate', str(a.fps), '-i', os.path.join(filled, '%04d.png'),
       '-framerate', str(a.fps), '-i', os.path.join(a.overlay, '%04d.png')]
if a.audio: cmd += ['-i', a.audio]
cmd += ['-filter_complex', f'[0]scale={W}:{H}:flags=lanczos{look}[b];[b][1]overlay,format=yuv420p[v]', '-map', '[v]']
if a.audio: cmd += ['-map', '2:a', '-c:a', 'aac', '-b:a', '256k']
cmd += ['-t', str(a.dur), '-c:v', 'libx264', '-preset', 'slow', '-crf', a.crf, '-movflags', '+faststart', a.out]
subprocess.run(cmd, check=True)
print(a.out)
