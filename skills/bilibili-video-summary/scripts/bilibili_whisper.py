#!/usr/bin/env python3
"""B站音频 Whisper 转写（字幕兜底链路）。

修复：aiohttp 下载带 Referer/UA（B站 CDN 防盗链，否则 403，BUG-2/PERF-5）；先 ffmpeg 转
16kHz 单声道 wav 再转写（PERF-4）；按时长自动选模型；`--sample` 依据弹幕/pbp 峰值切片转写（T9）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bilibili_digest import extract_id, load_credential  # noqa: E402

HEADERS = {
    "Referer": "https://www.bilibili.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
}


# --- 纯函数（可单测） ---------------------------------------------------
def choose_model(duration_sec: int, override: str | None = None) -> str:
    """按时长选模型：≤15min → small（更准），>15min → base（更快）。override 优先。"""
    if override:
        return override
    return "small" if (duration_sec or 0) <= 900 else "base"


def sample_segments(peak_times, duration_sec: int, window: int = 90, n_uniform: int = 5):
    """峰值 → 切片窗口 [(start, dur)]；无峰值时在时长内均匀取 n 段。"""
    duration_sec = max(0, int(duration_sec or 0))
    if peak_times:
        segs = []
        for t in sorted(set(int(x) for x in peak_times)):
            start = max(0, t - window // 2)
            dur = window if duration_sec == 0 else min(window, max(1, duration_sec - start))
            segs.append((float(start), float(dur)))
        return segs
    if duration_sec <= window:
        return [(0.0, float(duration_sec or window))]
    step = duration_sec / (n_uniform + 1)
    out = []
    for i in range(n_uniform):
        center = step * (i + 1)
        start = max(0, center - window / 2)
        out.append((round(start, 1), float(min(window, duration_sec - start))))
    return out


# --- 网络 / ffmpeg / whisper --------------------------------------------
def has_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


async def get_audio_url(id_kind, id_value, credential=None) -> str | None:
    from bilibili_api import video

    v = (video.Video(bvid=id_value, credential=credential) if id_kind == "bvid"
         else video.Video(aid=id_value, credential=credential))
    info = await v.get_info()
    cid = info["cid"]
    duration = info.get("duration", 0)
    dl = await v.get_download_url(cid=cid)
    audio_list = (dl.get("dash", {}) or {}).get("audio", []) or []
    if not audio_list:
        return None, duration
    best = max(audio_list, key=lambda x: x.get("bandwidth", 0))
    return best.get("baseUrl") or best.get("base_url"), duration


async def download_audio(url: str, out_path: str) -> bool:
    import aiohttp

    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    print(f"下载失败 HTTP {resp.status}", file=sys.stderr)
                    return False
                with open(out_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(1 << 16):
                        f.write(chunk)
        return os.path.getsize(out_path) > 0
    except Exception as exc:
        print(f"下载异常: {exc}", file=sys.stderr)
        return False


def to_wav(src: str, dst: str, start: float | None = None, dur: float | None = None) -> bool:
    cmd = ["ffmpeg", "-y"]
    if start is not None:
        cmd += ["-ss", str(start)]
    if dur is not None:
        cmd += ["-t", str(dur)]
    cmd += ["-i", src, "-ar", "16000", "-ac", "1", "-f", "wav", dst]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return os.path.getsize(dst) > 0
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return False


def transcribe(wav_path: str, model_size: str, language: str = "zh") -> str:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(wav_path, language=language, beam_size=5)
    return "".join(seg.text for seg in segments).strip()


async def run(args) -> int:
    if not has_ffmpeg():
        print(json.dumps({"ok": False, "error": {"code": "no_ffmpeg",
              "message": "ffmpeg 未安装，无法转码/切片"}}, ensure_ascii=False))
        return 2
    id_kind, id_value = extract_id(args.url)
    credential = load_credential()
    audio_url, duration = await get_audio_url(id_kind, id_value, credential)
    if not audio_url:
        print(json.dumps({"ok": False, "error": {"code": "no_audio", "message": "无法获取音频流"}},
                         ensure_ascii=False))
        return 2

    model_size = choose_model(duration, args.whisper_model)
    with tempfile.TemporaryDirectory() as tmp:
        raw = os.path.join(tmp, "audio.m4s")
        if not await download_audio(audio_url, raw):
            print(json.dumps({"ok": False, "error": {"code": "download", "message": "音频下载失败"}},
                             ensure_ascii=False))
            return 2
        pieces = []
        if args.sample:
            peaks = json.loads(Path(args.peaks).read_text(encoding="utf-8")) if args.peaks else []
            segs = sample_segments(peaks, duration)
            for i, (start, dur) in enumerate(segs):
                wav = os.path.join(tmp, f"seg{i}.wav")
                if to_wav(raw, wav, start, dur):
                    pieces.append({"t": start, "text": transcribe(wav, model_size, args.lang)})
        else:
            wav = os.path.join(tmp, "full.wav")
            if not to_wav(raw, wav):
                print(json.dumps({"ok": False, "error": {"code": "ffmpeg", "message": "转码失败"}},
                                 ensure_ascii=False))
                return 2
            pieces.append({"t": 0.0, "text": transcribe(wav, model_size, args.lang)})

    result = {"ok": True, "model": model_size, "sampled": bool(args.sample),
              "duration_sec": duration, "segments": pieces,
              "text": "".join(p["text"] for p in pieces)}
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    print(json.dumps(result, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="B站音频 Whisper 转写")
    parser.add_argument("url")
    parser.add_argument("--whisper-model", choices=["tiny", "base", "small", "medium", "large"])
    parser.add_argument("--lang", default="zh")
    parser.add_argument("--sample", action="store_true", help="按峰值切片转写（配 --peaks）")
    parser.add_argument("--peaks", help="峰值时刻 JSON 文件（数字数组，单位秒）")
    args = parser.parse_args()
    try:
        from faster_whisper import WhisperModel  # noqa: F401
    except ImportError:
        print(json.dumps({"ok": False, "error": {"code": "no_whisper",
              "message": "faster-whisper 未安装"}}, ensure_ascii=False))
        return 2
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
