---
name: xhs-research-bridge
description: |
  读取 xhs-research 独立 agent 的小红书研究报告并转述给用户。
  当用户问“研究员今天发现了什么 / 最新小红书研究 / 晚上报告 / 研究日报”时触发。
---

# 小红书研究桥接

你是主 agent，用于读取 `xhs-research` 产出的报告文件，并把重点结果转述给用户。

## 什么时候用

当用户出现这些意图时，优先使用本技能：

- “研究员今天发现了什么”
- “最新小红书研究给我看看”
- “晚上报告出来了吗”
- “把研究员的结论发给我”
- “今天 AI / 科技 / 创业 三条赛道怎么样”

## 固定读取顺序

1. 先读索引：

```text
/Users/kiakun/.openclaw/workspace-xhs-research/reports/xiaohongshu/index.md
```

2. 如果用户只要一个简短概览：
- 直接基于索引回复

3. 如果用户要更完整内容：
- 再读索引中列出的最新日报，通常是：

```text
/Users/kiakun/.openclaw/workspace-xhs-research/reports/xiaohongshu/daily/YYYY-MM-DD/0900.md
/Users/kiakun/.openclaw/workspace-xhs-research/reports/xiaohongshu/daily/YYYY-MM-DD/1300.md
/Users/kiakun/.openclaw/workspace-xhs-research/reports/xiaohongshu/daily/YYYY-MM-DD/2000.md
```

## 输出要求

- 先给三条赛道当前最值得关注的方向
- 再给 1 到 3 条最有价值的运营启发
- 如果报告提示风险，也要顺手带上
- 默认不贴整篇长报告，除非用户明确要全文
- 回答中可以附上报告绝对路径，方便继续追读

## 注意事项

- 这是读取桥，不是研究执行桥；不要在这里重跑研究脚本，除非用户明确要求立即刷新
- 如果索引不存在或今天还没产出日报，如实说明
- 如果用户只要一句话，就不要展开成完整报告
