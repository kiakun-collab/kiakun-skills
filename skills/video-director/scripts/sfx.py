"""Synthesize a soundtrack (music bed + sound effects) from the cue list a page exports
(render.mjs --events). Needs numpy only.

Usage: python -I sfx.py events.json out.wav

events.json = {duration, music?, events:[{t, type, ...}]}

music (optional) = {bpm, chords:["Am","F","C","G"], sections:[{from, to, style, chord?}]}
  One chord per bar, looping. Section styles, from sparse to dense:
    intro    pad + soft ticking hats, riser into the next section
    verse    kick on 1 and 3, 8th hats, bass on the root
    groove   four-on-the-floor, claps on 2 and 4, 16th hats, bass line, arpeggio
    break    drums drop out: pad + sub only (use it for a surprise / upset)
    build    kick returns, hats get denser, snare roll and riser into the next section
    tension  pulsing 16th bass, hats, sparse kick, riser at the end
    half     half-time: kick on 1, clap on 3, long bass notes
    outro    sustained pad (section `chord` overrides the loop), slow arpeggio, fade out
  Each section also has a level (default per style, override with `level`); levels
  crossfade over 0.3s so the bed has an emotional arc instead of one flat volume.
  dips (optional) = [{at, len}]: the music drops almost to silence for `len` seconds
  right before `at`, so the hit at `at` lands into silence. Use it for key moments.

Cue types (optional fields have defaults; every cue also takes `gain`):
  tick {pitch}  hero {pitch}  cluster {n}  grain {dur, density}  thud  boom
  step {n}  chord  whoosh  shuffle  slide  pair {n}  card
  swell {dur}   reverse build-up that ENDS at t (it starts at t - dur); put it on key hits
  riffle {dur, n}  n paper-card flicks spread over dur (a riffle shuffle)
  paper {dur}   long paper rustle / unfold
  string {f, dur, sustain, glide}  exact-pitch string (demo tones are evidence): integer harmonics,
                no random detune/pan; two at once beat for real. glide=[[dt, df_hz], ...]
Each hit gets a little random pitch, level and stereo spread so repeats do not sound
identical. Everything comes from fixed seeds: the same cue list gives the same file.
"""
import json
import sys
import wave

import numpy as np

SR = 48000
rng = np.random.default_rng(7)
NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def chord_notes(name):
    """'Am' -> root midi (octave 3) and triad intervals."""
    minor = name.endswith("m")
    root = NOTE[name[:-1] if minor else name] + 48
    return root, [0, 3, 7] if minor else [0, 4, 7]


# ---------------- building blocks ----------------
def env(n, attack=0.002, decay=0.08):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-t / decay)


def adsr(n, a=0.01, r=0.1):
    e = np.ones(n)
    na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return e


def add(*parts):
    """Sum (gain, signal) pairs of different lengths, zero-padding the shorter ones."""
    out = np.zeros(max(len(x) for _, x in parts))
    for g, x in parts:
        out[: len(x)] += g * x
    return out


def osc(f, dur, shape="sine", detune=0.0):
    n = int(dur * SR)
    ph = 2 * np.pi * f * (1 + detune) * np.arange(n) / SR
    if shape == "sine":
        return np.sin(ph)
    if shape == "tri":
        return (2 / np.pi) * np.arcsin(np.sin(ph))
    # band-limited saw from a handful of harmonics (warm, no aliasing)
    k = max(1, min(12, int(6000 / max(f, 1))))
    return sum(np.sin(ph * h) / h for h in range(1, k + 1)) * 0.6


def tone(f, dur, decay, shape="sine"):
    x = osc(f, dur, shape)
    return x * env(len(x), decay=decay)


def band(x, lo=0.0, hi=None):
    """Brick-ish FFT band-pass with soft edges; fine for short one-shots."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if lo: m *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    if hi: m *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * m, len(x))


def noise(dur, decay, lo=0.0, hi=None):
    n = int(dur * SR)
    return band(rng.standard_normal(n), lo, hi) * env(n, decay=decay)


# ---------------- drums & instruments ----------------
def kick(v=1.0):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 28)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.16)
    return v * add((1.0, body), (0.25, noise(0.012, 0.003, 1500)))


def clap(v=1.0):
    out = np.zeros(int(0.3 * SR))
    for k, d in enumerate((0, 0.011, 0.022)):
        b = noise(0.25 if k == 2 else 0.02, 0.09 if k == 2 else 0.006, 900, 6000)
        at = int(d * SR)
        out[at:at + len(b)] += b[: len(out) - at]
    return v * 0.9 * out


def hat(v=1.0, open_=False):
    return v * 0.35 * noise(0.2 if open_ else 0.05, 0.07 if open_ else 0.014, 7000)


def snare(v=1.0):
    return v * add((0.6, noise(0.18, 0.06, 1200, 9000)), (0.4, tone(190, 0.12, 0.04)))


def bass(midi, dur, v=1.0):
    x = osc(hz(midi), dur, "saw")
    return v * 0.55 * x * adsr(len(x), 0.005, 0.05) * np.exp(-np.arange(len(x)) / SR / 0.6)


def sub(midi, dur, v=1.0):
    x = osc(hz(midi), dur, "sine")
    return v * 0.6 * x * adsr(len(x), 0.05, 0.3)


def pad(notes, dur, v=1.0):
    parts = []
    for m in notes:
        for d in (-0.004, 0.004):
            parts.append((0.12, osc(hz(m), dur, "tri", d)))
    x = add(*parts)
    return v * x * adsr(len(x), 0.35, 0.6)


def pluck(midi, v=1.0):
    return v * add((0.35, tone(hz(midi), 0.35, 0.09, "tri")), (0.12, tone(hz(midi) * 2, 0.15, 0.03)))


def riser(dur, v=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 200 * (8 ** (t / dur))
    tonal = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    nz = band(rng.standard_normal(n), 2000) * 0.5
    return v * (tonal + nz) * (t / dur) ** 2


# ---------------- sound effects (cues) ----------------
def thud():
    n = int(0.8 * SR)
    t = np.arange(n) / SR
    f = 70 * np.exp(-t * 2.5) + 42
    w = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, attack=0.003, decay=0.25)
    return add((0.9, w), (0.3, noise(0.15, 0.03, 0, 400)))


def tick(pitch=1.0):
    return add((0.5, tone(900 * pitch, 0.12, 0.025)), (0.25, tone(1800 * pitch, 0.05, 0.01)), (0.15, noise(0.02, 0.004, 3000)))


def ding(pitch=1.0):
    """钢珠撞黄铜钉：几个不成整数倍的泛音，像小铃铛，衰减很快"""
    f = 1250 * pitch
    return add((0.45, tone(f, 0.35, 0.09)), (0.22, tone(f * 2.76, 0.2, 0.04)), (0.1, tone(f * 5.4, 0.1, 0.015)),
               (0.12, noise(0.012, 0.003, 4000)))


def hero(pitch=1.0):
    return add((0.7, tone(420 * pitch, 0.3, 0.07)), (0.3, tone(840 * pitch, 0.15, 0.03)), (0.2, noise(0.03, 0.006, 2000)))


def step(n=0):
    scale = [0, 2, 4, 5, 7, 9, 11, 12]
    f = 392.0 * 2 ** (scale[min(n * 2, 7)] / 12)
    return add((0.45, tone(f, 0.6, 0.2, "tri")), (0.18, tone(f * 2, 0.25, 0.06)), (0.12, tone(f * 1.5, 0.4, 0.12, "tri")))


def chord_hit():
    return add(*[(0.2, osc(hz(m), 2.2, "tri") * env(int(2.2 * SR), 0.01, 0.8)) for m in (60, 64, 67, 72, 76)])


def whoosh():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    return 0.3 * band(rng.standard_normal(n), 400, 5000) * np.sin(np.pi * t / t[-1]) ** 3


def grain(dur=1.0, density=40):
    n = int(dur * SR)
    out = np.zeros(n + SR // 10)
    for _ in range(int(dur * density)):
        at = int(rng.uniform(0, n))
        g = 0.12 * tone(rng.uniform(1500, 3600), 0.03, 0.006)
        out[at:at + len(g)] += g * (0.5 + 0.5 * at / n)  # swells as the grid fills
    return out


def shuffle():
    return grain(0.9, 80) * 1.4


def slide():
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    f = 700 * np.exp(-t * 1.8)
    return 0.4 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, attack=0.01, decay=0.4)


def cluster(n=16):
    out = np.zeros(int(0.45 * SR))
    for _ in range(n):
        at = int(rng.uniform(0, 0.22) * SR)
        g = 0.5 * tick(rng.uniform(0.8, 1.25))
        out[at:at + len(g)] += g[: len(out) - at]
    return out


def pair(n=8):
    out = np.zeros(int(0.6 * SR))
    for k in range(n):
        at = int(k * 0.4 / max(n, 1) * SR)
        g = 0.3 * tone(1200 + 90 * k, 0.06, 0.012, "tri")
        out[at:at + len(g)] += g
    return out


def card():
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    return 0.45 * band(rng.standard_normal(n), 2500) * np.exp(-t / 0.04) * np.minimum(1, t / 0.01)


def swell(dur=0.8):
    n = int(dur * SR)
    t = np.arange(n) / SR
    shape = (t / dur) ** 3
    nz = band(rng.standard_normal(n), 300, 9000) * 0.5
    f = 180 * (4 ** (t / dur))
    tonal = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.2
    x = (nz + tonal) * shape
    x[-int(0.004 * SR):] *= np.linspace(1, 0, int(0.004 * SR))
    return x


def riffle(dur=0.4, n=26):
    out = np.zeros(int((dur + 0.1) * SR))
    for k in range(n):
        u = k / max(n - 1, 1)
        at = int((u + rng.uniform(-0.3, 0.3) / n) * dur * SR)
        at = min(max(at, 0), len(out) - 1)
        nn = int(0.012 * SR)
        g = band(rng.standard_normal(nn), 1800, 7500) * np.exp(-np.arange(nn) / SR / 0.003) * rng.uniform(0.25, 0.45)
        out[at:at + len(g)] += g[: len(out) - at]
    return out


def paper(dur=1.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    crackle = np.zeros(n)
    for _ in range(int(dur * 120)):
        at = int(rng.uniform(0, n - 600))
        crackle[at:at + 600] += band(rng.standard_normal(600), 2500) * np.exp(-np.arange(600) / SR / 0.002) * 0.3
    body = band(rng.standard_normal(n), 300, 4000) * 0.25
    return (crackle + body) * np.sin(np.pi * t / dur) ** 1.5


def boom():
    return add((1.0, thud()), (0.6, tick(1.6)), (0.5, noise(0.6, 0.25, 3000)))


# ---- 叠在 AI 配乐上的环境/冲击音效（夏の残響）----
def launch(dur=1.1):
    """烟火升空的哨音：音高上滑 + 气流噪声，结尾留给 burst"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 900 + 1700 * (t / dur) ** 0.7
    wh = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.18 * np.sin(np.pi * np.minimum(t / dur, 1)) ** 0.5
    air = band(rng.standard_normal(n), 1500, 7000) * 0.12 * (t / dur)
    return wh + air


def burst():
    """烟火炸开：低频闷响 + 拖尾的噼啪声"""
    n = int(2.2 * SR)
    out = np.zeros(n)
    b = boom()
    out[:len(b)] += 0.8 * b[:n]
    for _ in range(90):
        at = int(rng.uniform(0.05, 1.9) * SR)
        c = noise(0.012, 0.003, 2500) * rng.uniform(0.1, 0.35) * np.exp(-at / SR / 1.2)
        out[at:at + len(c)] += c[: n - at]
    return out


def train(dur=1.4):
    """电车呼啸而过：带通噪声音量起伏 + 轨道接缝的咔哒声"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    body = band(rng.standard_normal(n), 120, 2500) * np.sin(np.pi * t / dur) ** 2 * 0.5
    for k in range(6):
        at = int((0.15 + k * dur / 7) * SR)
        c = noise(0.04, 0.01, 200, 1800) * 0.5
        body[at:at + len(c)] += c[: n - at]
    return body


def splash():
    return add((0.5, noise(0.5, 0.12, 800, 9000)), (0.25, noise(0.15, 0.04, 200, 1500)))


def shimmer(dur=1.2):
    """闪光/光效扫过：几个高音铃音快速上行"""
    out = np.zeros(int(dur * SR))
    for k, m in enumerate((84, 88, 91, 96, 100)):
        x = tone(hz(m), dur - k * 0.06, 0.35, "tri") * 0.12
        at = int(k * 0.06 * SR)
        out[at:at + len(x)] += x[: len(out) - at]
    return out


def brush(dur=0.22):
    """毛笔落纸：一下短促的带通噪声"唰"，起音快、尾巴略带纸面摩擦"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    sh = band(rng.standard_normal(n), 1200, 7000) * np.minimum(1, t / 0.01) * np.exp(-t / (dur * 0.35))
    rub = band(rng.standard_normal(n), 300, 1500) * 0.3 * np.exp(-t / (dur * 0.6))
    return 0.5 * (sh + rub)


def string(f=220.0, dur=2.0, sustain=0.0, glide=None):
    """精确音高的弦音（演示音 = 证据）：严格整数倍谐波，不加随机音高。
    sustain>0 时拨弦后保持这个比例的持续音（像弓弦），两根弦同响时拍音来自真实的泛音相消相长。
    glide=[[dt, df], ...]：相对事件开始的时间点和频率偏移（Hz），线性插值，相位按瞬时频率积分。"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    df = np.interp(t, [g[0] for g in glide], [g[1] for g in glide]) if glide else np.zeros(n)
    phase = 2 * np.pi * (np.cumsum(f + df) - (f + df[0])) / SR   # 从 0 相位起振
    out = np.zeros(n)
    for h in range(1, 9):
        if f * h > SR / 2 - 2000:
            break
        dec = sustain + (1 - sustain) * np.exp(-t / (1.6 / h ** 0.6))
        out += np.sin(h * phase) * dec / h ** 1.15
    out *= np.minimum(1, t / 0.003) * adsr(n, 0.0, min(0.12, dur / 4))
    return out * 0.32


def impact():
    """切镜重击：boom + 一层短促的白噪声闪"""
    return add((1.0, boom()), (0.5, noise(0.25, 0.06, 500, 12000)))


SFX = {
    "launch": lambda e: launch(e.get("dur", 1.1)), "burst": lambda e: burst(), "train": lambda e: train(e.get("dur", 1.4)),
    "splash": lambda e: splash(), "brush": lambda e: brush(e.get("dur", 0.22)), "shimmer": lambda e: shimmer(e.get("dur", 1.2)), "impact": lambda e: impact(),
    "tick": lambda e: tick(e.get("pitch", 1.0)), "ding": lambda e: ding(e.get("pitch", 1.0)), "hero": lambda e: hero(e.get("pitch", 1.0)),
    "cluster": lambda e: cluster(e.get("n", 16)), "grain": lambda e: grain(e.get("dur", 1.0), e.get("density", 40)),
    "thud": lambda e: thud(), "boom": lambda e: boom(), "step": lambda e: step(e.get("n", 0)),
    "chord": lambda e: chord_hit(), "whoosh": lambda e: whoosh(), "shuffle": lambda e: shuffle(),
    "slide": lambda e: slide(), "pair": lambda e: pair(e.get("n", 8)), "card": lambda e: card(),
    "swell": lambda e: swell(e.get("dur", 0.8)),
    "string": lambda e: string(e.get("f", 220.0), e.get("dur", 2.0), e.get("sustain", 0.0), e.get("glide")),
    "riffle": lambda e: riffle(e.get("dur", 0.4), e.get("n", 26)), "paper": lambda e: paper(e.get("dur", 1.2)),
}
LEVELS = {"intro": 0.55, "verse": 0.7, "groove": 0.9, "break": 0.3, "build": 0.75,
          "tension": 1.0, "half": 0.8, "outro": 0.85}


def bed_gain(music, total):
    """Per-section level with 0.3s crossfades, a ramp through `build`, and pre-hit dips."""
    g = np.ones(total)
    xf = int(0.3 * SR)
    for sec in music["sections"]:
        a, b = int(sec["from"] * SR), min(total, int(sec["to"] * SR))
        lv = sec.get("level", LEVELS.get(sec["style"], 1.0))
        seg = np.full(b - a, lv)
        if sec["style"] == "build":
            seg = np.linspace(lv * 0.6, 1.0, b - a)  # climb back after the drop
        g[a:b] = seg
    # smooth the steps between sections
    c = np.concatenate([[0], np.cumsum(g)])  # moving average via cumulative sum (linear time)
    i = np.arange(total)
    lo, hi = np.maximum(0, i - xf // 2), np.minimum(total, i + xf // 2)
    g = (c[hi] - c[lo]) / (hi - lo)
    for d in music.get("dips", []):
        a, b = int((d["at"] - d["len"]) * SR), int(d["at"] * SR)
        fall = min(int(0.05 * SR), b - a)
        g[a:a + fall] *= np.linspace(1, 0.06, fall)
        g[a + fall:b] *= 0.06
    return g


# ---------------- mixing ----------------
class Bus:
    def __init__(self, n):
        self.L, self.R = np.zeros(n), np.zeros(n)

    def put(self, sig, t, gain=1.0, pan=0.0):
        at = int(t * SR)
        if at >= len(self.L) or at < 0:
            return
        end = min(len(self.L), at + len(sig))
        s = sig[: end - at] * gain
        # short fade-out so one-shots that are cut while still ringing do not click
        f = min(len(s), int(0.006 * SR))
        if f > 1:
            s = s.copy()
            s[-f:] *= np.linspace(1, 0, f)
        self.L[at:end] += s * np.sqrt(0.5 * (1 - pan))
        self.R[at:end] += s * np.sqrt(0.5 * (1 + pan))


def reverb(L, R, secs=1.8, mix=0.25):
    n = int(secs * SR)
    t = np.arange(n) / SR
    r2 = np.random.default_rng(11)
    out = []
    for x in (L, R):
        ir = r2.standard_normal(n) * np.exp(-t / (secs / 5))
        ir = band(ir, 200, 7000)
        ir /= np.sqrt(np.sum(ir ** 2))
        size = 1 << int(np.ceil(np.log2(len(x) + n)))
        y = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
        out.append(y * mix)
    return out


def arrange(music, total, dur):
    """Render the music bed into (dry, wet) buses plus a kick-trigger list for ducking."""
    bpm = music["bpm"]
    beat = 60 / bpm
    bar = beat * 4
    chords = music.get("chords", ["Am", "F", "C", "G"])
    dry, wet = Bus(total), Bus(total)
    kicks = []
    hum = np.random.default_rng(3)
    vel = lambda base: base * hum.uniform(0.85, 1.1)

    for sec in music["sections"]:
        s0, s1, style = sec["from"], min(sec["to"], dur), sec["style"]
        first_bar, last_bar = int(np.floor(s0 / bar + 1e-6)), int(np.ceil(s1 / bar - 1e-6))
        for b in range(first_bar, last_bar):
            bt = b * bar
            name = sec.get("chord") or chords[b % len(chords)]
            root, tri = chord_notes(name)
            notes = [root + i for i in tri]
            a, z = max(bt, s0), min(bt + bar, s1)
            if z - a < 0.05:
                continue
            # pad: everywhere except the densest tension
            pad_gain = {"intro": 0.7, "verse": 0.6, "groove": 0.45, "break": 0.45, "build": 0.6,
                        "tension": 0.5, "half": 0.7, "outro": 1.0}[style]
            p = pad(notes + [root + 12], z - a + (1.2 if style == "outro" else 0.2))
            if style == "outro":
                p *= np.linspace(1, 0, len(p)) ** 1.5 if b == last_bar - 1 else 1
            wet.put(p, a, pad_gain)
            if style in ("break", "half", "outro"):
                dry.put(sub(root - 12, z - a), a, 0.3 if style == "break" else 0.5)

            for k in range(16):  # 16th-note grid
                t = bt + k * beat / 4
                if t < s0 - 1e-6 or t >= s1 - 1e-6:
                    continue
                q, on_beat = k // 4, k % 4 == 0
                prog = (t - s0) / max(s1 - s0, 1e-6)
                if style == "intro":
                    if k % 2 == 0 and t > 0.5: dry.put(hat(vel(0.35 + 0.3 * prog)), t, pan=0.3)
                elif style == "verse":
                    if on_beat and q in (0, 2): dry.put(kick(vel(0.8)), t); kicks.append(t)
                    if k % 2 == 0: dry.put(hat(vel(0.5 if k % 4 else 0.7)), t, pan=0.25)
                    if on_beat and q in (0, 2): dry.put(bass(root - 12, beat * 1.5), t, vel(0.8))
                elif style == "groove":
                    if on_beat: dry.put(kick(vel(1.0)), t); kicks.append(t)
                    if on_beat and q in (1, 3): wet.put(clap(vel(0.8)), t, 0.6); dry.put(clap(vel(0.7)), t)
                    dry.put(hat(vel(0.75 if k % 4 == 2 else 0.4), open_=k % 4 == 2), t, pan=0.3 if k % 2 else -0.15)
                    if k % 2 == 0:
                        bn = root - 12 + (12 if k % 8 == 6 else 0)
                        dry.put(bass(bn, beat * 0.45), t, vel(0.75))
                    arp = notes[[0, 1, 2, 1][k % 4]] + 12 * (1 + (k // 8) % 2)
                    wet.put(pluck(arp, vel(0.5)), t, 0.6, pan=-0.5 if k % 2 else 0.5)
                elif style == "break":
                    pass
                elif style == "build":
                    if on_beat: dry.put(kick(vel(0.6 + 0.4 * prog)), t); kicks.append(t)
                    step_ = 4 if prog < 0.35 else 2 if prog < 0.75 else 1
                    if k % step_ == 0: dry.put(hat(vel(0.35 + 0.4 * prog)), t, pan=0.25)
                    if prog > 0.8: dry.put(snare(vel(0.3 + 0.7 * (prog - 0.8) / 0.2)), t)
                    if on_beat: dry.put(bass(root - 12, beat * 0.9), t, vel(0.7))
                elif style == "tension":
                    lift = 0.8 + 0.4 * prog  # energy climbs through the section
                    dry.put(bass(root - 12, beat / 4 * 0.9), t, vel((1.4 if k % 4 else 1.9) * lift))
                    if k % 8 == 0: dry.put(sub(root - 12, beat * 1.9), t, 0.35 * lift)
                    dry.put(hat(vel((0.7 if k % 2 else 0.4) * lift)), t, pan=0.35 if k % 2 else -0.2)
                    if on_beat and q in (0, 2): dry.put(kick(vel(1.0)), t); kicks.append(t)
                    if on_beat and q == 3 and prog > 0.5: dry.put(snare(vel(0.5)), t)
                    if k % 4 == 0: wet.put(pluck(notes[q % 3] + 24, vel(0.35)), t, 0.5, pan=0.6 if q % 2 else -0.6)
                elif style == "half":
                    if on_beat and q == 0: dry.put(kick(vel(1.0)), t); kicks.append(t)
                    if on_beat and q == 2: wet.put(clap(vel(0.9)), t, 0.8); dry.put(clap(vel(0.8)), t)
                    if k % 2 == 0: dry.put(hat(vel(0.35)), t, pan=0.25)
                    if on_beat and q == 0: dry.put(bass(root - 12, bar * 0.9), t, vel(0.7))
                elif style == "outro":
                    if on_beat: wet.put(pluck(notes[[2, 1, 0, 1][q]] + 24, vel(0.45)), t, 0.7, pan=-0.3 + 0.2 * q)
        # risers into the next section
        if style in ("intro", "build", "tension"):
            rd = min(2.0 if style != "intro" else 2.5, s1 - s0)
            wet.put(riser(rd), s1 - rd, 0.35)
    return dry, wet, kicks


def main():
    src, dst = sys.argv[1], sys.argv[2]
    cue = json.load(open(src, encoding="utf-8"))
    dur = cue["duration"]
    total = int((dur + 2) * SR)

    music_dry, music_wet = Bus(total), Bus(total)
    kicks = []
    if cue.get("music"):
        music_dry, music_wet, kicks = arrange(cue["music"], total, dur)

    fx_dry, fx_wet = Bus(total), Bus(total)
    var = np.random.default_rng(21)
    unknown = set()
    for e in cue["events"]:
        if e["type"] not in SFX:
            unknown.add(e["type"])
            continue
        s = SFX[e["type"]](e)
        g = e.get("gain", 1.0) * var.uniform(0.85, 1.05)
        pan = var.uniform(-0.35, 0.35)
        if e["type"] == "string":  # 演示音是证据：电平和声像不随机
            g, pan = e.get("gain", 1.0), e.get("pan", 0.0)
        at = e["t"] - len(s) / SR if e["type"] == "swell" else e["t"]
        fx_dry.put(s, at, g, pan)
        fx_wet.put(s, at, g * 0.5, -pan)
    if unknown:
        print("unknown cue types skipped:", ", ".join(sorted(unknown)), file=sys.stderr)

    # duck the music bed under each kick and under big cue hits
    duck = np.ones(total)
    dl = int(0.18 * SR)
    shape = 1 - 0.45 * np.exp(-np.arange(dl) / SR / 0.06)
    for t in kicks + [e["t"] for e in cue["events"] if e["type"] in ("boom", "thud", "chord")]:
        at = int(t * SR)
        end = min(total, at + dl)
        duck[at:end] = np.minimum(duck[at:end], shape[: end - at])

    bed = bed_gain(cue["music"], total) if cue.get("music") else np.ones(total)
    wl, wr = reverb(music_wet.L * bed + fx_wet.L, music_wet.R * bed + fx_wet.R)
    music_gain = 0.55
    L = (music_dry.L + music_wet.L * 0.7) * music_gain * duck * bed + fx_dry.L + wl
    R = (music_dry.R + music_wet.R * 0.7) * music_gain * duck * bed + fx_dry.R + wr

    n = int(dur * SR)
    L, R = L[:n], R[:n]
    fade = int(0.03 * SR)
    for x in (L, R):
        x[:fade] *= np.linspace(0, 1, fade)
        x[-fade:] *= np.linspace(1, 0, fade)
    peak = max(np.max(np.abs(L)), np.max(np.abs(R))) or 1
    L, R = (np.tanh(x / peak * 1.4) / np.tanh(1.4) * 0.89 for x in (L, R))  # soft limiter, ~-1 dBFS
    pcm = (np.stack([L, R], axis=1) * 32767).astype("<i2")
    with wave.open(dst, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(dst)


if __name__ == "__main__":
    main()
