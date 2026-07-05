from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import bilibili_whisper as w  # noqa: E402


def test_choose_model_by_duration():
    assert w.choose_model(600) == "small"      # ≤15min
    assert w.choose_model(1200) == "base"       # >15min
    assert w.choose_model(600, override="medium") == "medium"


def test_sample_segments_from_peaks_centered():
    segs = w.sample_segments([100, 500], duration_sec=600, window=90)
    assert segs[0][0] == 55.0    # 100 - 45
    assert segs[0][1] == 90.0
    # 第二个峰值靠近结尾，时长被截断到剩余
    assert segs[1][0] == 455.0 and segs[1][1] == min(90.0, 600 - 455)


def test_sample_segments_uniform_when_no_peaks():
    segs = w.sample_segments([], duration_sec=1000, window=90, n_uniform=5)
    assert len(segs) == 5
    starts = [s[0] for s in segs]
    assert starts == sorted(starts)  # 均匀递增


def test_sample_segments_short_video_single_window():
    segs = w.sample_segments([], duration_sec=60, window=90)
    assert segs == [(0.0, 60.0)]
