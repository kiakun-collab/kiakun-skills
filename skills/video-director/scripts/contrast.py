"""重点时刻比前半拍响多少（短时 RMS，dB）。目标 ≥ 6 dB。

用法：python contrast.py out/sfx.wav 2.5 11 20.5 ...
比较的是 [t, t+0.15] 和 [t-0.25, t-0.02] 两段。不够 6 dB 时，先降低它前面那个 swell 的 gain，再考虑加重重击本身。
"""
import sys, wave
import numpy as np

w = wave.open(sys.argv[1]); sr = w.getframerate(); sw = w.getsampwidth(); ch = w.getnchannels()
raw = np.frombuffer(w.readframes(w.getnframes()), np.uint8)
if sw == 3:   # 24-bit：补一个字节再按 int32 读
    b = raw.reshape(-1, 3); x = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
    x = np.where(x >= 1 << 23, x - (1 << 24), x).astype(float)
else:
    x = np.frombuffer(raw.tobytes(), {2: '<i2', 4: '<i4'}[sw]).astype(float)
x = x.reshape(-1, ch).mean(1)
db = lambda a, b: 20 * np.log10(np.sqrt(np.mean(x[int(a * sr):int(b * sr)] ** 2)) + 1e-9)
for t in map(float, sys.argv[2:]):
    d = db(t, t + 0.15) - db(t - 0.25, t - 0.02)
    print(f'{t:5.1f}s  hit vs previous half-beat: {d:+.1f} dB' + ('' if d >= 6 else '   <-- < 6 dB'))
