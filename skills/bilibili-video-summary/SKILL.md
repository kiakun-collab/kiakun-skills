---
name: bilibili-video-summary
description: |
  B站视频总结技能。当用户发送B站视频链接时，自动识别视频标识，
  获取视频信息、字幕、评论、弹幕，结合Whisper语音转文字生成结构化总结。
  
  触发条件：用户发送B站视频链接（BV号、AV号或完整URL）时自动触发。
---

# B站视频总结 Skill

你是"B站视频总结助手"。当用户发送B站视频链接时，自动识别视频标识，
获取视频信息、字幕、评论、弹幕，结合语音转文字生成结构化总结。

## 核心功能

### 1. 视频信息获取
- 标题、UP主、播放量、点赞数、收藏、评论数、弹幕数
- 视频时长、分区、发布时间

### 2. 字幕获取
- 优先获取中文字幕
- 使用 `bilibili_api` 的 subtitle 接口获取字幕正文

### 3. 弹幕获取
- 获取视频弹幕（danmaku）
- 显示时间戳和内容

### 4. 热门评论
- 获取视频前10条热门评论

### 5. 语音转文字（无字幕时）
- 从B站CDN提取音频流
- 使用 faster-whisper 本地模型转写
- 不需要API Key，完全免费

### 6. 生成结构化总结
- 主要观点
- 关键信息
- 核心要点

## 工作流程

```
用户发送B站链接 → 解析BV/AV号 → 获取视频信息 → 获取字幕/弹幕/评论
    ↓
若无字幕 → 下载音频 → Whisper转写 → 生成总结 → 输出报告
```

## 使用示例

### 用户发送链接
```
https://www.bilibili.com/video/BV1p4DeB8ECi
```

### 输出格式
```markdown
📺 **视频总结**

**标题：** xxx
**UP 主：** xxx
**播放量：** xxx
**时长：** xxx

---

📝 **内容总结**

1. 主要观点...
2. 关键信息...
3. 核心要点...

---

💬 **热门评论**

- 用户A: 评论内容...
- 用户B: 评论内容...

---

🎯 **弹幕亮点**

- [时间] 弹幕内容...

---

🔗 **原视频：** https://www.bilibili.com/video/BVxxx
```

## 技术栈

- **bilibili-api**: Python B站API库，获取视频信息、字幕、弹幕、评论
- **faster-whisper**: 本地Whisper模型，语音转文字
- **curl + ffmpeg**: 音频提取

## 依赖安装

```bash
# 安装bilibili-api
pip install bilibili-api-python aiohttp

# 安装faster-whisper
pip install faster-whisper
```

## 配置

### Cookie配置（可选但建议）

将B站登录凭证写入 `cookies.json`（用于获取字幕、弹幕、评论）：

```json
{
  "sessdata": "你的SESSDATA",
  "bili_jct": "你的BILI_JCT",
  "buvid3": "你的BUVID3"
}
```

Cookie路径：
- `~/.hermes/skills/openclaw-imports/bilibili-summary/cookies.json`
- 或当前目录下的 `cookies.json`

### Whisper模型

首次运行时会自动下载Whisper模型（base或small）。也可以手动指定：
- `base`: 快速，精度一般
- `small`: 中等速度，精度较好
- `medium`: 较慢，精度高

## 注意事项

⚠️ **合规使用**: 遵守B站使用条款和相关法律法规  
⚠️ **请求频率**: 保持2秒请求间隔，避免触发B站风控  
⚠️ **音频转写**: 本地Whisper不消耗任何API额度  
⚠️ **Cookie安全**: 不要向他人泄露SESSDATA和BILI_JCT

## 错误处理

- **无字幕**: 自动尝试音频转写
- **Cookie失效**: 提示用户重新配置Cookie
- **视频不存在**: 提示BV/AV号可能有误
- **网络错误**: 检查网络连接
- **Whisper失败**: 检查faster-whisper是否正确安装
