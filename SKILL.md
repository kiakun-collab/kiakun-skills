---
name: douyin-creator-research
description: |
  抖音达人研究助手（方案A：人工过验证 + 自动化接管）。
  使用方式：
  (1) 在 VNC 中启动带远程调试的 Chrome，
  (2) 人工完成滑块验证并登录抖音，
  (3) 自动化脚本通过 CDP 连接到已登录的 Chrome，执行搜索和截图。
  触发条件：用户需要筛选抖音达人、研究达人内容风格、输出达人候选池或营销方案时。
---

# 抖音达人研究助手（方案A）

> **方案A：人工过验证 + 自动化接管**
> 
> 由于抖音风控严格，采用半自动化方式：
> - 人工在 VNC 中完成滑块验证和登录
> - 自动化脚本接管已登录的浏览器执行研究任务

## 服务器信息

- **VNC 访问**: `http://1.12.66.113:6080/vnc.html`
- **VNC 密码**: `douyin123`
- **CDP 端口**: `9222`（Chrome 远程调试）

## 使用流程

### 第一步：在 VNC 中启动 Chrome

在 OpenClaw 中执行：
```bash
/root/.openclaw/skills/douyin-creator-research/scripts/run.sh start-chrome
```

或在 VNC 终端中手动执行：
```bash
/usr/bin/google-chrome --remote-debugging-port=9222
```

### 第二步：人工完成验证和登录

1. 访问 `http://1.12.66.113:6080/vnc.html`，输入密码 `douyin123`
2. 在 VNC 桌面中，Chrome 应该已经启动
3. 访问 https://www.douyin.com/
4. **完成滑块验证码**（手动拖动）
5. **登录抖音**（手机号 15014077447，或扫码登录）
6. **保持 Chrome 打开，不要关闭**

### 第三步：创建研究会话

```bash
/root/.openclaw/skills/douyin-creator-research/scripts/run.sh session-create \
  --name "幻塔达人研究" \
  --game "幻塔"
```

### 第四步：自动化搜索达人

```bash
/root/.openclaw/skills/douyin-creator-research/scripts/run.sh explore \
  --keyword "开放世界手游" \
  --session-id <上一步返回的ID> \
  --cdp http://localhost:9222
```

### 第五步：自动化分析达人主页

```bash
/root/.openclaw/skills/douyin-creator-research/scripts/run.sh research \
  --url "https://www.douyin.com/user/xxx" \
  --session-id <ID> \
  --cdp http://localhost:9222
```

## CLI 命令参考

| 命令 | 说明 |
|:---|:---|
| `session-create` | 创建研究会话 |
| `session-list` | 列出所有会话 |
| `start-chrome` | 启动带远程调试的 Chrome（VNC 环境） |
| `explore` | 搜索达人（支持 `--cdp` 连接已有浏览器） |
| `research` | 分析达人主页（支持 `--cdp` 连接已有浏览器） |

## 工作原理

1. **VNC 环境**: 提供真实图形界面，通过滑块验证
2. **Chrome DevTools Protocol (CDP)**: Playwright 通过 9222 端口连接到已打开的 Chrome
3. **复用登录态**: 自动化脚本使用已登录的浏览器会话，无需再次验证

## 注意事项

- **必须保持 VNC 中的 Chrome 打开**，否则 CDP 连接会断开
- 如果 Chrome 意外关闭，需要重新执行 `start-chrome` 并重新登录
- 截图和数据保存在 `/root/.douyin-research/sessions/<session-id>/`
