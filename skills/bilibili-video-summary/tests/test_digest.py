from __future__ import annotations

import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import bilibili_digest as d  # noqa: E402


# --- 标识解析（BUG-4） ---------------------------------------------------
def test_extract_bvid_from_url():
    assert d.extract_id("https://www.bilibili.com/video/BV1xx411c7mD?p=2") == ("bvid", "BV1xx411c7mD")


def test_extract_bare_bvid():
    assert d.extract_id("BV1xx411c7mD") == ("bvid", "BV1xx411c7mD")


def test_extract_av_number():
    assert d.extract_id("av170001") == ("aid", 170001)
    assert d.extract_id("https://www.bilibili.com/video/av170001") == ("aid", 170001)


def test_extract_invalid_raises():
    with pytest.raises(ValueError):
        d.extract_id("not-a-video")


# --- 弹幕聚合（T4） ------------------------------------------------------
def test_fold_repeats_collapses_runs():
    assert d.fold_repeats("哈哈哈哈") == "哈"
    assert d.fold_repeats("666666") == "6"


def test_top_words_filters_single_char_and_folds():
    words = d.top_words(["名场面", "名场面!", "哈哈哈哈", "前方高能", "666666"])
    counts = {w["word"]: w["count"] for w in words}
    assert counts["名场面"] == 2          # 标点无关，两条合并
    assert counts["前方高能"] == 1
    assert "哈" not in counts             # 折叠成单字符后被过滤
    assert "6" not in counts


def test_bucket_seconds_takes_larger():
    assert d.bucket_seconds(200) == 30      # 200/100=2 < 30 → 30
    assert d.bucket_seconds(6000) == 60     # 6000/100=60 > 30 → 60


def test_density_and_peaks():
    times = [1, 2, 3, 100, 101, 102, 103]
    buckets = d.density_buckets(times, 200, 30)
    assert buckets[0] == 3 and buckets[3] == 4
    peaks = d.find_peaks(buckets, 30, k=2)
    assert {p["count"] for p in peaks} == {3, 4}
    assert peaks[0]["t_sec"] < peaks[1]["t_sec"]  # 按时间升序


def test_peak_samples_dedup_and_cap():
    peaks = [{"t_sec": 100.0, "count": 5, "samples": []}]
    dm = [{"t": 98.0, "text": "高能"}, {"t": 99.0, "text": "高能"}, {"t": 101.0, "text": "笑死"}]
    d.peak_samples(peaks, dm, window=15.0, per_peak=8)
    assert peaks[0]["samples"] == ["高能", "笑死"]  # 相邻重复去重


# --- 价值信号（T6） -----------------------------------------------------
def test_value_signals_rates_and_hint():
    vs = d.value_signals(
        {"view": 100000, "like": 9000, "favorite": 4000, "coin": 3000, "reply": 2000, "danmaku": 6000}, 600)
    assert vs["like_rate"] == 0.09
    assert vs["fav_rate"] == 0.04
    assert vs["coin_rate"] == 0.03
    assert vs["reply_rate"] == 0.02
    assert "收藏率" in vs["hint"]


def test_value_signals_handles_zero_view():
    vs = d.value_signals({"view": 0, "like": 0, "favorite": 0, "coin": 0, "reply": 0, "danmaku": 0}, 0)
    assert vs["like_rate"] == 0.0  # 不除零崩溃


# --- 字幕正文解析（BUG-3 / T1，mock JSON） -------------------------------
def test_parse_subtitle_body_and_text():
    segs = d.parse_subtitle_body({"body": [{"from": 0, "to": 1, "content": "你好"},
                                            {"from": 1, "to": 2, "content": "世界"}]})
    assert len(segs) == 2
    assert d.subtitle_to_text(segs) == "你好世界"


def test_choose_subtitle_prefers_cc_zh():
    entry, kind = d.choose_subtitle([{"lan": "ai-zh", "subtitle_url": "//a"},
                                     {"lan": "zh-CN", "subtitle_url": "//b"}])
    assert entry["lan"] == "zh-CN" and kind == "cc"


def test_choose_subtitle_falls_back_to_ai():
    entry, kind = d.choose_subtitle([{"lan": "ai-zh", "subtitle_url": "//a"}])
    assert kind == "ai"


# --- 错误分类（BUG-7） --------------------------------------------------
def test_classify_error_by_code():
    class E(Exception):
        code = -404
    assert d.classify_error(E("稿件不可见"))["code"] == "not_found"

    class R(Exception):
        code = -412
    assert d.classify_error(R("请求被拦截"))["code"] == "rate_limited"

    class A(Exception):
        code = -101
    assert d.classify_error(A("账号未登录"))["code"] == "auth"


def test_classify_error_network_and_unknown():
    class ClientConnectionError(Exception):
        pass
    assert d.classify_error(ClientConnectionError("boom"))["code"] == "network"
    assert d.classify_error(ValueError("weird"))["code"] == "unknown"


# --- transcript 预算（PERF-3） ------------------------------------------
def test_transcript_budget_modes():
    assert d.enforce_transcript_budget("x" * 100, "none") == ("", False)
    head, trunc = d.enforce_transcript_budget("x" * 10000, "full")
    assert len(head) == d.TRANSCRIPT_HEAD_CHARS and trunc is True
    assert d.enforce_transcript_budget("short", "full") == ("short", False)


# --- 热评组装（T5） -----------------------------------------------------
def test_build_hot_comments_pinned_dedup_up_replied():
    up_mid = 999
    raw = [{
        "top_replies": [{"rpid": 1}],
        "replies": [
            {"rpid": 1, "member": {"uname": "A"}, "content": {"message": "置顶评论"}, "like": 500,
             "rcount": 3, "replies": [{"member": {"mid": 999}}]},
            {"rpid": 2, "member": {"uname": "B"}, "content": {"message": "普通评论"}, "like": 100, "rcount": 0},
            {"rpid": 2, "member": {"uname": "B"}, "content": {"message": "dup"}, "like": 100},  # 去重
        ],
    }]
    comments, top3 = d.build_hot_comments(raw, up_mid)
    assert len(comments) == 2
    first = comments[0]
    assert first["is_pinned"] is True and first["up_replied"] is True and first["text"] == "置顶评论"
    assert 1 in top3


# --- 组装冒烟（≤15KB，全字段） ------------------------------------------
def _fake_material():
    class DM:
        def __init__(self, t, text):
            self.dm_time, self.text = t, text
    return {
        "info": {"bvid": "BV1", "aid": 1, "title": "标题", "desc": "简介", "duration": 600,
                 "pubdate": 1700000000, "tname": "科技", "cid": 10,
                 "stat": {"view": 100000, "like": 9000, "coin": 3000, "favorite": 4000,
                          "reply": 2000, "danmaku": 3, "share": 100},
                 "owner": {"mid": 999, "name": "UP"}, "pages": [{"cid": 10, "page": 1}]},
        "aid": 1, "cid": 10, "total_pages": 1, "current_page": 1,
        "danmakus": [DM(1.0, "高能"), DM(2.0, "哈哈哈"), DM(3.0, "名场面")],
        "ai_conclusion": {"model_result": {"result_type": 1, "summary": "官方小结",
                                           "outline": [{"title": "章节1", "timestamp": 0}]}},
        "pbp": {"data": {"step_sec": 1}}, "comments_raw": [], "transcript_text": "字幕正文",
        "subtitle_type": "cc", "segments": [{"from": 0, "to": 1, "content": "字幕正文"}],
        "requests_made": 6,
    }


def test_cache_key_separates_auth_and_anon():
    # 匿名降级结果与登录结果分开缓存，互不覆盖（审阅#2）
    auth = d.cache_path("bvid", "BV1", 1, True)
    anon = d.cache_path("bvid", "BV1", 1, False)
    assert auth != anon
    assert auth.name.endswith("_auth.json") and anon.name.endswith("_anon.json")


def test_parse_uploader_profile_defensive():
    assert d.parse_uploader_profile(None) == (None, None)
    prof, err = d.parse_uploader_profile({
        "info": {"sign": "签名", "official": {"title": "知名UP主"}},
        "rel": {"follower": 12345},
        "vids": {"list": {"vlist": [{"title": "视频1", "play": 999, "created": 1700000000}]}},
        "errors": [],
    })
    assert err is None
    assert prof["followers"] == 12345 and prof["official"] == "知名UP主"
    assert prof["recent_videos"][0]["title"] == "视频1"


def test_parse_uploader_profile_surfaces_error_on_total_failure():
    # 全部子接口失败 → (None, 错误串)，可区分"UP无数据"与"接口失败"（审阅#1）
    prof, err = d.parse_uploader_profile({"info": None, "rel": None, "vids": None,
                                          "errors": ["vids: wbi 风控", "rel: timeout"]})
    assert prof is None
    assert "wbi" in err


def test_parse_uploader_profile_partial_success():
    # get_videos 失败但 info/rel 成功 → 仍返回画像 + 记录错误
    prof, err = d.parse_uploader_profile({
        "info": {"sign": "s"}, "rel": {"follower": 100}, "vids": None, "errors": ["vids: 风控"]})
    assert prof["followers"] == 100 and prof["recent_videos"] == []
    assert "风控" in err


def test_assemble_produces_full_contract_under_15kb():
    import json

    class Args:
        transcript = "full"
        skip_comments = False
    payload = d.assemble(_fake_material(), Args())
    for key in ("ok", "video", "uploader", "uploader_profile", "uploader_profile_error",
                "stats", "value_signals", "transcript", "auxiliary", "danmaku_analysis",
                "hot_comments", "meta"):
        assert key in payload
    assert payload["transcript"]["source"] == "subtitle"
    assert payload["auxiliary"]["ai_conclusion"]["source"] == "bilibili_official_ai"
    assert payload["danmaku_analysis"]["total"] == 3
    size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    assert size <= 15 * 1024
