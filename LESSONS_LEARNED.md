# 抖音自动化研究踩坑记录与经验总结

> 项目：douyin-creator-research  
> 时间：2026-04-02  
> 结论：抖音风控过于严格，短期内无法实现稳定的完全自动化

---

## 一、项目目标

开发一个基于 OpenClaw 的抖音达人研究助手，实现：
1. 自动搜索抖音达人
2. 截图达人主页和视频
3. LLM 分析截图生成达人报告

---

## 二、尝试过的方案

### 方案 1：Playwright Headless（失败）

**实现**：使用 Playwright 启动 headless Chromium

**结果**：❌ 立即触发滑块验证码

**原因**：
- Headless 浏览器有明显特征（`navigator.webdriver = true`）
- 抖音风控系统能检测无头环境
- 请求被识别为自动化工具

---

### 方案 2：xvfb-run + 真实 Chrome（失败）

**实现**：使用 xvfb-run 在虚拟显示中运行真实 Google Chrome

**结果**：❌ 仍然触发滑块验证码

**原因**：
- Chrome 在 xvfb 虚拟显示中仍有可检测特征
- 缺少真实鼠标/键盘事件
- WebGL、字体、时区等指纹特征不一致

---

### 方案 3：VNC + 人工登录 + CDP 自动化（部分成功）

**实现**：
1. 部署 VNC 服务器（端口 5901）
2. noVNC 提供浏览器访问（端口 6080）
3. 人工在 VNC 中完成滑块验证并登录
4. Chrome 开启远程调试端口（9222）
5. Playwright 通过 CDP 连接已登录的 Chrome

**结果**：⚠️ Chrome 远程调试端口无法正确监听

**问题**：
- Chrome 启动时 `--remote-debugging-port=9222` 参数无效
- 可能原因：
  - VNC 环境中的 DISPLAY 变量问题
  - Chrome 权限问题（root 用户运行限制）
  - Chrome 安全策略阻止远程调试

---

## 三、技术架构（已实现部分）

```
kiakun-skills/
└── douyin-creator-research/
    ├── SKILL.md                    # 技能文档
    ├── pyproject.toml              # Python 依赖
    ├── scripts/
    │   ├── cli.py                  # CLI 入口
    │   ├── session_manager.py      # 会话管理
    │   └── dy/
    │       ├── __init__.py
    │       ├── browser.py          # 浏览器封装（支持 CDP）
    │       ├── extractors.py       # DOM 数据提取
    │       ├── login.py            # 登录辅助
    │       └── types.py            # Pydantic 模型
    ├── references/
    │   ├── prompts.md              # LLM 提示词模板
    │   └── report-template.md      # 报告格式规范
    └── templates/                   # Jinja2 模板（占位）
```

### 核心功能（已实现）

| 功能 | 状态 | 说明 |
|:---|:---|:---|
| Session 管理 | ✅ | 创建、列出、保存研究会话 |
| 浏览器连接 | ✅ | 支持 headless、xvfb、CDP 三种模式 |
| 搜索功能 | ✅ | 关键词搜索、截图、提取达人列表 |
| 达人分析 | ✅ | 主页截图、视频截图、元数据提取 |
| VNC 部署 | ✅ | XFCE + TigerVNC + noVNC |
| Chrome 启动 | ✅ | 带远程调试参数的 Chrome |

---

## 四、核心代码亮点

### 1. 浏览器封装（支持多模式）

```python
class DouyinBrowser:
    def __init__(self, headless=False, connect_cdp=None):
        self.connect_cdp = connect_cdp  # CDP 连接地址
        
    def connect(self):
        if self.connect_cdp:
            # 连接到已有 Chrome（方案3）
            self.browser = self.playwright.chromium.connect_over_cdp(self.connect_cdp)
        else:
            # 启动新 Chrome（方案1/2）
            self.browser = self.playwright.chromium.launch_persistent_context(...)
```

### 2. 安全约束（硬编码）

```python
MAX_PAGES_PER_SESSION = 30    # 单 session 最多访问 30 页
MIN_INTERVAL_SECONDS = 5.0    # 操作间隔至少 5 秒
```

### 3. 会话数据管理

```python
# 目录结构
~/.douyin-research/sessions/
└── {session-id}/
    ├── meta.json          # 项目信息
    ├── data.jsonl         # 研究记录
    ├── search_001.png     # 搜索截图
    ├── homepage_xxx.png   # 达人主页截图
    └── video_xxx_001.png  # 视频截图
```

---

## 五、关键经验教训

### 1. 关于抖音风控

- **检测维度多**：User-Agent、WebDriver、WebGL、字体、时区、鼠标轨迹等
- **滑块验证严格**：即使通过验证，后续操作仍可能触发二次验证
- **账号风险高**：频繁自动化操作可能导致账号限制

### 2. 关于浏览器自动化

| 方案 | 复杂度 | 成功率 | 备注 |
|:---|:---|:---|:---|
| Playwright Headless | 低 | ❌ 极低 | 现代网站都能检测 |
| Playwright + stealth | 中 | ⚠️ 低 | 违反安全约束，不推荐 |
| xvfb-run + Chrome | 中 | ❌ 低 | 仍有可检测特征 |
| VNC + 人工 + CDP | 高 | ⚠️ 中 | 技术可行但流程复杂 |
| 真实物理机 | 高 | ✅ 高 | 成本最高 |

### 3. 关于技术选型

- **CDP 连接**：理论可行，但实际部署中遇到端口监听问题
- **Session 管理**：JSONL + 文件系统足够轻量，无需数据库
- **截图分析**：LLM 视觉理解能力强，截图分析效果好

---

## 六、未解决问题

1. **Chrome CDP 端口无法监听**
   - 可能原因：root 用户权限、DISPLAY 环境变量、Chrome 安全策略
   - 解决思路：尝试非 root 用户、检查 Chrome 启动日志

2. **滑块验证码绕过**
   - 当前方案：人工完成
   - 自动化方案：需接入验证码识别服务（2Captcha 等），成本和法律风险高

3. **长期稳定性**
   - 即使通过验证，抖音可能随时更新风控策略
   - 需要持续维护和更新

---

## 七、替代方案建议

### 短期（立即可用）

| 平台 | 工具 | 状态 |
|:---|:---|:---|
| 小红书 | xiaohongshu-skills | ✅ 已可用 |
| B站 | bilibili-api | ✅ 已可用 |

### 长期（抖音）

1. **方案A**：继续研究 CDP 连接问题，解决端口监听
2. **方案B**：接入验证码识别服务（需评估成本）
3. **方案C**：使用真实设备或云服务（如 BrowserStack）

---

## 八、部署记录

### 服务器配置

- **IP**: 1.12.66.113
- **系统**: Ubuntu 24.04 LTS
- **内存**: 3.6GB
- **已安装**:
  - XFCE4 桌面环境
  - TigerVNC Server (端口 5901)
  - noVNC (端口 6080)
  - Google Chrome 146.0.7680.177
  - Python 3.12 + Playwright

### 服务状态

| 服务 | 端口 | 状态 |
|:---|:---|:---|
| VNC | 5901 | ✅ 运行中 |
| noVNC | 6080 | ✅ 运行中 |
| Chrome CDP | 9222 | ❌ 未解决 |

---

## 九、代码资产

所有代码已整理为 OpenClaw Skill 格式：

```
.kimi/skills/douyin-creator-research/
├── SKILL.md              # 技能文档（150行，符合规范）
├── pyproject.toml        # Python 项目配置
├── scripts/
│   ├── cli.py           # CLI 入口（支持 session/explore/research/login）
│   ├── run.sh           # xvfb-run 包装脚本
│   └── dy/              # 抖音模块
├── references/          # 提示词和模板
└── templates/           # 报告模板
```

---

## 十、下一步行动

1. **短期内**：使用小红书/B站完成达人研究任务
2. **中期**：解决 Chrome CDP 端口问题，完成方案3
3. **长期**：评估是否需要接入验证码识别服务

---

**总结**：抖音的风控机制非常强大，远超预期。技术实现上已接近可行，但最后一公里（CDP 连接）仍需解决。建议优先使用小红书/B站等风控较松的平台。
