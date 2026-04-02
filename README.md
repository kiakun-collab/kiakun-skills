# Kiakun Skills

个人 OpenClaw/Kimi 技能库，包含各种自动化工具和助手。

## 技能列表

### 1. douyin-creator-research (抖音达人研究助手)

**状态**: ⚠️ 实验性 / 待完善  
**目标**: 自动化抖音达人筛选与研究  
**当前问题**: 抖音风控严格，CDP 连接待解决

#### 功能
- ✅ Session 管理（创建、列出、保存研究数据）
- ✅ 浏览器多模式支持（headless、xvfb、CDP）
- ✅ 搜索达人并截图
- ✅ 分析达人主页和视频
- ✅ VNC + noVNC 部署
- ⚠️ Chrome CDP 连接（待解决）

#### 目录结构
```
douyin-creator-research/
├── SKILL.md              # OpenClaw 技能文档
├── pyproject.toml        # Python 项目配置
├── LESSONS_LEARNED.md    # 踩坑记录与经验总结
├── scripts/
│   ├── cli.py           # CLI 入口
│   ├── run.sh           # 启动脚本
│   ├── session_manager.py
│   └── dy/              # 抖音模块
│       ├── browser.py   # 浏览器封装
│       ├── extractors.py # DOM 提取
│       ├── login.py     # 登录辅助
│       └── types.py     # 数据模型
└── references/          # 提示词和模板
```

#### 部署记录
- **服务器**: 腾讯云 1.12.66.113
- **环境**: Ubuntu 24.04 + XFCE + VNC
- **详细记录**: 见 LESSONS_LEARNED.md

---

## 使用方式

### 安装

```bash
cd douyin-creator-research
pip install -e .
playwright install chromium
```

### CLI 命令

```bash
# 创建研究会话
python scripts/cli.py session-create --name "测试" --game "幻塔"

# 搜索达人
python scripts/cli.py explore --keyword "开放世界手游" --session-id <id>

# 分析达人主页
python scripts/cli.py research --url "https://..." --session-id <id>
```

---

## 开发笔记

见 [LESSONS_LEARNED.md](./LESSONS_LEARNED.md)

---

## License

MIT
