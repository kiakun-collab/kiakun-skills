# AI 配乐 + sfx.py 音效 → 成片音轨。
# 1) 在重点时刻前半拍把配乐压低（成品歌曲本身很满，不压就没有"空出来再砸下去"的对比）
# 2) 音效按 -9 dB 叠上去
# 3) 整体增益 + 限幅器到 −14 LUFS（不用 loudnorm 动态模式，保留起伏），给 AAC 留余量
# 用法：python tools/mixdown.py music.wav sfx.wav out.wav --dips 38.10,45.44,61.55 [--gain 0.9]
import argparse, subprocess, re

ap = argparse.ArgumentParser()
ap.add_argument('music'); ap.add_argument('sfx'); ap.add_argument('out')
ap.add_argument('--dips', default='', help='逗号分隔的重击时间；之前 dip_len 秒内配乐压低')
ap.add_argument('--dip-len', type=float, default=0.19)
ap.add_argument('--dip-db', type=float, default=-14)
ap.add_argument('--sfx-db', type=float, default=-9)
ap.add_argument('--target', type=float, default=-14)
ap.add_argument('--limit', type=float, default=0.70)
a = ap.parse_args()

def loud(path):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', path, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    i = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', r)[-1]); p = float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', r)[-1])
    return i, p

dips = [float(x) for x in a.dips.split(',') if x]
# 包络：dip 前沿 40ms 渐入，重击处 10ms 恢复
g = 10 ** (a.dip_db / 20)
expr = '1'
for t in dips:
    s, e = t - a.dip_len, t
    expr = f"({expr})*if(between(t,{s - .04:.3f},{s:.3f}),1-(1-{g:.4f})*(t-{s - .04:.3f})/0.04," \
           f"if(between(t,{s:.3f},{e - .01:.3f}),{g:.4f},if(between(t,{e - .01:.3f},{e:.3f}),{g:.4f}+(1-{g:.4f})*(t-{e - .01:.3f})/0.01,1)))"
raw = a.out.replace('.wav', '_raw.wav')
fc = (f"[0]aresample=48000,volume='{expr}':eval=frame[m];[1]aresample=48000,volume={a.sfx_db}dB[s];"
      f"[m][s]amix=inputs=2:normalize=0:duration=first[o]")
subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', a.music, '-i', a.sfx,
                '-filter_complex', fc, '-map', '[o]', '-c:a', 'pcm_s24le', raw], check=True)

gain = 0.0
for _ in range(4):   # 限幅器会吃掉一部分响度，迭代补回
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', raw, '-af',
                    f'volume={gain}dB,aresample=192000,alimiter=limit={a.limit}:attack=1:release=60:level=disabled,aresample=48000',
                    '-c:a', 'pcm_s24le', a.out], check=True)
    i, p = loud(a.out)
    print(f'gain {gain:+.2f} dB → {i} LUFS, peak {p} dBFS')
    if abs(i - a.target) < 0.15: break
    gain += a.target - i
