#!/usr/bin/env python3
"""
B站视频Whisper转写脚本
从B站获取音频并用Whisper转写为文字
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Try to import faster-whisper
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("Warning: faster-whisper not installed. Run: pip install faster-whisper", file=sys.stderr)

sys.path.insert(0, str(Path(__file__).parent.parent))
from bilibili_summary import video, Credential, load_cookie_credential, extract_bvid


def install_ffmpeg():
    """检查ffmpeg是否安装"""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def download_audio(audio_url: str, output_path: str) -> bool:
    """下载音频"""
    try:
        result = subprocess.run(
            ["curl", "-L", "-o", output_path, audio_url],
            capture_output=True,
            timeout=120
        )
        return result.returncode == 0
    except Exception as e:
        print(f"下载失败: {e}", file=sys.stderr)
        return False


async def get_audio_url(bvid: str, credential=None) -> str:
    """获取音频URL"""
    v = video.Video(bvid=bvid, credential=credential)
    info = await v.get_info()
    cid = info["cid"]
    
    download_url = await v.get_download_url(cid=cid)
    dash = download_url.get("dash", {})
    
    audio_list = dash.get("audio", [])
    if not audio_list:
        return None
    
    best_audio = max(audio_list, key=lambda x: x.get("bandwidth", 0))
    return best_audio.get("baseUrl", "")


def transcribe_audio(audio_path: str, model_size: str = "base", language: str = "zh") -> str:
    """转写音频"""
    if not WHISPER_AVAILABLE:
        return "Error: faster-whisper not installed"
    
    print(f"加载Whisper模型: {model_size}...", file=sys.stderr)
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    
    print("正在转写（这可能需要几分钟）...", file=sys.stderr)
    segments, info = model.transcribe(audio_path, language=language, beam_size=5)
    
    print(f"语言: {info.language}, 时长: {info.duration}s", file=sys.stderr)
    
    result = []
    for segment in segments:
        result.append(f"[{segment.start:.1f}s -> {segment.end:.1f}s] {segment.text}")
    
    return "\n".join(result)


async def main():
    parser = argparse.ArgumentParser(description="B站视频Whisper转写")
    parser.add_argument("url", help="B站视频URL或BV号")
    parser.add_argument("--model", default="base", choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper模型大小 (default: base)")
    parser.add_argument("--lang", default="zh", help="语言代码 (default: zh)")
    parser.add_argument("--keep-audio", action="store_true", help="保留音频文件")
    args = parser.parse_args()
    
    if not WHISPER_AVAILABLE:
        print("Error: faster-whisper not installed", file=sys.stderr)
        sys.exit(1)
    
    if not install_ffmpeg():
        print("Error: ffmpeg not installed. Please install ffmpeg first.", file=sys.stderr)
        sys.exit(1)
    
    bvid = extract_bvid(args.url)
    print(f"正在处理视频: {bvid}", file=sys.stderr)
    
    credential = load_cookie_credential()
    
    # 获取音频URL
    print("获取音频URL...", file=sys.stderr)
    audio_url = await get_audio_url(bvid, credential)
    if not audio_url:
        print("Error: 无法获取音频URL", file=sys.stderr)
        sys.exit(1)
    
    # 下载音频
    with tempfile.NamedTemporaryFile(suffix=".m4s", delete=False) as f:
        audio_path = f.name
    
    print(f"下载音频到 {audio_path}...", file=sys.stderr)
    if not download_audio(audio_url, audio_path):
        print("Error: 下载失败", file=sys.stderr)
        os.unlink(audio_path)
        sys.exit(1)
    
    # 转写
    try:
        print("开始转写...", file=sys.stderr)
        transcript = transcribe_audio(audio_path, args.model, args.lang)
        print(transcript)
    finally:
        if not args.keep_audio:
            os.unlink(audio_path)
            print(f"已删除临时音频: {audio_path}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
