# B站视频总结 Skill

获取B站视频信息、字幕、评论、弹幕，并支持 Whisper 语音转文字。

## 功能

- ✅ 获取视频信息（标题、UP主、播放量、点赞等）
- ✅ 获取字幕（中文字幕优先）
- ✅ 获取弹幕
- ✅ 获取热门评论
- ✅ Whisper 语音转文字（无字幕时）
- ✅ 结构化总结输出

## 安装

```bash
# 安装依赖
pip install bilibili-api-python aiohttp faster-whisper

# 或使用 requirements.txt
pip install -r requirements.txt
```

## 配置

### Cookie 配置（可选）

将 B站登录凭证写入 `cookies.json`，用于获取字幕、弹幕、评论：

```json
{
  "sessdata": "你的SESSDATA",
  "bili_jct": "你的BILI_JCT",
  "buvid3": "你的BUVID3"
}
```

Cookie 文件路径（按顺序查找）：
1. 当前目录下的 `cookies.json`
2. `~/.hermes/skills/openclaw-imports/bilibili-summary/cookies.json`

### Whisper 模型

首次运行时会自动下载 Whisper 模型。可选模型：

| 模型 | 速度 | 精度 | 内存需求 |
|------|------|------|----------|
| tiny | 最快 | 较低 | ~1GB |
| base | 快 | 一般 | ~1GB |
| small | 中等 | 较好 | ~2GB |
| medium | 较慢 | 好 | ~5GB |

## 使用

### 视频信息 + 字幕 + 弹幕 + 评论

```bash
python scripts/bilibili_summary.py "https://www.bilibili.com/video/BV1p4DeB8ECi"
```

### Whisper 转写（无字幕时）

```bash
python scripts/bilibili_whisper.py "https://www.bilibili.com/video/BV1p4DeB8ECi"
```

### 指定 Whisper 模型

```bash
python scripts/bilibili_whisper.py "BV号" --model small --lang zh
```

## 工作流程

```
用户发送B站链接
    ↓
解析BV/AV号
    ↓
获取视频信息、字幕、弹幕、评论
    ↓
若无字幕 → 下载音频 → Whisper转写
    ↓
生成结构化总结
    ↓
输出报告
```

## 技术栈

- **bilibili-api**: B站API Python库
- **faster-whisper**: 本地Whisper模型，CPU推理，免费
- **curl + ffmpeg**: 音频提取

## 注意事项

- 遵守B站使用条款和相关法律法规
- 请求频率保持2秒间隔，避免触发风控
- Whisper 完全本地运行，不消耗任何API额度
- 不要向他人泄露 SESSDATA 和 BILI_JCT
