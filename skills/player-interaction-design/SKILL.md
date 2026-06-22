---
name: player-interaction-design
description: Use when 处理玩家可见的游戏 UI、玩法互动、引导、失败恢复、挑战链路或体验验收。
---

# 玩家互动设计

## 边界

本 skill 只触发玩家互动设计流程，不重复 `AGENTS.md`、任务包或项目 guide。

优先级：

1. 用户本轮指令
2. 具体任务包
3. `AGENTS.md`
4. 相关 `docs/agent_guides/**`
5. 本 skill

如果冲突，按更高优先级执行，并说明冲突点。

## 必读

优先读取当前项目内的同名规则；如果项目未提供对应文件，读取本 skill 打包资源：

- 玩家互动合同：`references/player_interaction_contract.md`
- 合同模板：`assets/templates/player_interaction_contract.md`
- 合同校验脚本：`scripts/validate_player_interaction_contract.py`

涉及玩法、UI、GDD、文案、引导、失败恢复或结算复盘，先读：
`docs/agent_guides/player_experience_first.md`；若项目没有该文件，则按本 skill 的玩家互动合同执行。

涉及玩家互动合同，读：
`docs/agent_guides/player_interaction_contract.md`；若项目没有该文件，读本 skill 的 `references/player_interaction_contract.md`。

涉及证据、截图、Playtest Bridge、visible-window 或体验结论，读：
`docs/agent_guides/evidence_levels_and_claims.md`；若项目没有该文件，至少按本 skill 的证据层级选择表收口。

## 合同粒度

写完整合同：

- 新入口、新面板、新弹窗、新挑战、新失败恢复、新结算反馈。
- 改变玩家目标、操作顺序、状态门槛、解锁路径或跨日链路。
- 需要声明“玩家能看见、点到、读懂、体验可理解”。

写短合同：

- 改动范围只涉及已有流程内的文案、标签、颜色或布局。
- 不新增入口、弹窗、状态门槛、主操作或恢复路径。

如有疑问，默认写完整合同。宁可多写，不漏失败恢复路径。

## 执行要求

实现、拆任务包或写验收前，先写玩家互动合同。

证据层级必须使用项目既有口径，并按 `player_interaction_contract.md` 的前置条件选择。只跑 headless/focused runner 时，不得声称玩家真实体验通过或自然通关。

`证据层级` 是结构化字段，只填写 `logic_runner`、`ui_contract`、`interactive_mcp`、`visible_capture`、`manual_canary` 或明确被任务要求的 `natural UI-only`。runner、fixture、加速、bridge helper、fallback 等支撑说明写到 `证据说明`、验收要求或 `not_proven`，不要塞进 `证据层级`。

写完合同或任务包后，运行：

```sh
python3 scripts/qa/validate_player_interaction_contract.py --mode auto <markdown...>
```

如果项目没有该脚本，改用本 skill 打包脚本：

```sh
python3 <skill-dir>/scripts/validate_player_interaction_contract.py --mode auto <markdown...>
```

常见误区见 `docs/agent_guides/player_experience_first.md`。

## 反例

- 不要在 `证据层级` 写“目标最低为 ui_contract，可选补 visible_capture”。应写 `ui_contract / visible_capture`。
- 不要把 focused runner、fixture scene、direct manager/API 写成证据层级。它们是支撑方式或限制。
- 不要在未声明自然通关时使用字面量 `natural UI-only`；否定时写“自然 UI 多日链”或“自然通关”。
