# 分析 AI 成曲的 BPM、拍点、小节线、段落边界和分段响度，输出 json，供分镜和剪辑卡点。
# 用法：python tools/beats.py music.wav out/beats.json [--bpm-hint 180]
import sys, json, argparse
import numpy as np
import librosa

ap = argparse.ArgumentParser()
ap.add_argument('audio'); ap.add_argument('out')
ap.add_argument('--bpm-hint', type=float, default=None, help='预设 BPM，用来纠正半速/倍速误判')
ap.add_argument('--sections', type=int, default=8, help='段落聚类数上限')
a = ap.parse_args()

y, sr = librosa.load(a.audio, sr=22050, mono=True)
dur = len(y) / sr
hop = 512
onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
tempo, beats = librosa.beat.beat_track(onset_envelope=onset, sr=sr, hop_length=hop,
                                       start_bpm=a.bpm_hint or 120, units='frames')
tempo = float(np.atleast_1d(tempo)[0])
bt = librosa.frames_to_time(beats, sr=sr, hop_length=hop)
# 半速/倍速纠正：拍间隔中位数和提示 BPM 差一倍时插值或抽取
if a.bpm_hint:
    if tempo < a.bpm_hint * 0.7:
        bt = np.sort(np.concatenate([bt, (bt[:-1] + bt[1:]) / 2])); tempo *= 2
    elif tempo > a.bpm_hint * 1.4:
        bt = bt[::2]; tempo /= 2
ibi = float(np.median(np.diff(bt))) if len(bt) > 1 else 60 / tempo

# 小节线（4/4）：在 4 个相位里选拍点 onset 强度总和最大的那个作为强拍
strength = onset[np.clip(librosa.time_to_frames(bt, sr=sr, hop_length=hop), 0, len(onset) - 1)]
phase = int(np.argmax([strength[p::4].sum() for p in range(4)]))
downbeats = bt[phase::4]

# 段落：拍同步的色度 + MFCC 做结构分段
chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
mfcc = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop, n_mfcc=13)
feat = librosa.util.sync(np.vstack([librosa.util.normalize(chroma), librosa.util.normalize(mfcc)]),
                         beats, aggregate=np.median)
k = max(2, min(a.sections, feat.shape[1] // 8))
bounds = librosa.segment.agglomerative(feat, k)
bound_t = sorted(set([0.0] + [float(bt[min(b, len(bt) - 1)]) for b in bounds if b > 0]))
# 段落边界吸附到最近的小节线
snap = lambda t: float(downbeats[np.argmin(np.abs(downbeats - t))]) if len(downbeats) else t
bound_t = sorted(set(round(snap(t), 3) for t in bound_t))

# 每段的 RMS 响度（dBFS），用来判断安静段/高潮段
rms = librosa.feature.rms(y=y, hop_length=hop)[0]
rt = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
secs = []
edges = bound_t + [dur]
for s, e in zip(edges[:-1], edges[1:]):
    m = (rt >= s) & (rt < e)
    db = float(20 * np.log10(np.mean(rms[m]) + 1e-9)) if m.any() else -99
    secs.append({'start': round(s, 3), 'end': round(e, 3), 'bars': round((e - s) / (ibi * 4), 1),
                 'rms_db': round(db, 1)})

# 强 onset（重击候选）：onset 强度前 5% 且在拍点附近
thr = np.percentile(onset, 95)
peaks = librosa.util.peak_pick(onset, pre_max=8, post_max=8, pre_avg=16, post_avg=16, delta=0.3, wait=10)
hits = [round(float(librosa.frames_to_time(p, sr=sr, hop_length=hop)), 3) for p in peaks if onset[p] >= thr]

res = {'audio': a.audio, 'duration': round(dur, 3), 'bpm': round(60 / ibi, 2), 'beat': round(ibi, 4),
       'beats': [round(float(t), 3) for t in bt], 'downbeats': [round(float(t), 3) for t in downbeats],
       'sections': secs, 'hits': hits}
json.dump(res, open(a.out, 'w', encoding='utf-8'), indent=1)
print(f"duration {dur:.2f}s  bpm {res['bpm']}  beats {len(bt)}  first downbeat {downbeats[0]:.3f}s")
for s in secs:
    print(f"  {s['start']:7.2f} – {s['end']:7.2f}  {s['bars']:5.1f} bars  {s['rms_db']:6.1f} dB")
print('hits:', hits[:40])
