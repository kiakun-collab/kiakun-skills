# 玩家互动合同模板

## 完整合同

```md
## 玩家互动合同（完整）
- 玩家当前阶段：<玩家此刻已经知道什么、还缺什么>
- 玩家目标：<玩家想完成的经营动作、挑战动作或理解动作>
- 入口：<玩家从哪里发现并进入>
- 第一眼信息：<玩家进入后最先看到的状态、目标和限制>
- 主操作：<玩家最自然会点击、选择、拖动或确认什么>
- 可选操作：<玩家还能做什么，但不能抢走主线>
- 成功反馈：<玩家如何知道事情成功了>
- 阻断原因：<失败、拒绝、缺资源、未解锁时玩家看到的原因>
- 恢复路径：<玩家下一步如何补救>
- 下一步：<成功或失败后界面把玩家带向哪里>
- 不展示信息：<不得展示内部 id、debug 字段、runner 名、内部枚举、状态码或字段名>
- 证据层级：logic_runner / ui_contract / interactive_mcp / visible_capture / manual_canary
- 证据说明（可选）：<runner、fixture、截图、MCP、加速、bridge helper、fallback 或 mixed evidence 等支撑与限制>
- not_proven：<本次不能宣称的玩家体验、自然链路或挑战结果>
```

自然通关限制：只有任务明确要求、同一玩家可见窗口、无 fixture、无 direct manager/API、无加速、无桥接支撑时，才能在 `证据层级` 填写 `natural UI-only`。否则不要在合同里使用该字面量。

## 短合同

```md
## 玩家互动合同（短）
- 玩家目标：<玩家想完成的经营动作、挑战动作或理解动作>
- 入口：<玩家从哪里发现并进入>
- 主操作：<玩家最自然会点击、选择、拖动或确认什么>
- 成功反馈：<玩家如何知道事情成功了>
- 阻断原因：<失败、拒绝、缺资源、未解锁时玩家看到的原因>
- 恢复路径：<玩家下一步如何补救>
- 不展示信息：<不得展示内部 id、debug 字段、runner 名、内部枚举、状态码或字段名>
- 证据层级：logic_runner / ui_contract / interactive_mcp / visible_capture / manual_canary
- 证据说明（可选）：<runner、fixture、截图、MCP、加速、bridge helper、fallback 或 mixed evidence 等支撑与限制>
- not_proven：<本次不能宣称的玩家体验、自然链路或挑战结果>
```

证据口径优先以当前项目的 `docs/agent_guides/player_interaction_contract.md` 和 `docs/agent_guides/evidence_levels_and_claims.md` 为准；项目未提供时，使用本 skill 的 `references/player_interaction_contract.md`。
