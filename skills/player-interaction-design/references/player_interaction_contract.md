# 玩家互动合同

## 触发条件

涉及玩家可见 UI、玩法互动、引导、挑战链路、失败恢复或体验验收时，使用本合同。完整证据口径仍以 `docs/agent_guides/evidence_levels_and_claims.md` 为准。

## 合同粒度

写完整合同：

- 新入口、新面板、新弹窗、新挑战、新失败恢复、新结算反馈。
- 改变玩家目标、操作顺序、状态门槛、解锁路径或跨日链路。
- 需要声明“玩家能看见、点到、读懂、体验可理解”。

写短合同：

- 改动范围只涉及已有流程内的文案、标签、颜色或布局。
- 不新增入口、弹窗、状态门槛、主操作或恢复路径。

如有疑问，默认写完整合同。

## 结构化字段规则

- `证据层级` 只能填写枚举值：`logic_runner`、`ui_contract`、`interactive_mcp`、`visible_capture`、`manual_canary`，以及任务明确要求时的 `natural UI-only`。
- `证据层级` 不写解释句，不写 runner 类型，不写 fixture、加速、direct manager/API、bridge helper、fallback 或 mixed evidence。
- runner、fixture、加速、bridge helper、fallback 等支撑方式写在 `证据说明`、验收要求或 `not_proven`。
- 没有声明自然通关时，不要在 `not_proven` 里写字面量 `natural UI-only`；写“自然 UI 多日链”或“自然通关”即可。

## 完整合同字段

```md
## 玩家互动合同（完整）
- 玩家当前阶段：说明玩家此刻已经知道什么、还缺什么。
- 玩家目标：说明玩家想完成的经营动作、挑战动作或理解动作。
- 入口：说明玩家从哪里发现并进入。
- 第一眼信息：说明玩家进入后最先看到的状态、目标和限制。
- 主操作：说明玩家最自然会点击、选择、拖动或确认什么。
- 可选操作：说明玩家还能做什么，但不能抢走主线。
- 成功反馈：说明玩家如何知道事情成功了。
- 阻断原因：说明失败、拒绝、缺资源、未解锁时玩家看到的原因。
- 恢复路径：说明玩家下一步如何补救。
- 下一步：说明成功或失败后界面把玩家带向哪里。
- 不展示信息：说明不得展示内部 id、debug 字段、runner 名、内部枚举、状态码或字段名。
- 证据层级：logic_runner / ui_contract / interactive_mcp / visible_capture / manual_canary 中实际证明的一项或多项。
- 证据说明（可选）：说明 runner、fixture、截图、MCP、加速、bridge helper、fallback 或 mixed evidence 等支撑与限制。
- not_proven：说明本次不能宣称的玩家体验、自然链路或挑战结果。
```

仅在任务明确要求且满足全部无辅助条件时，才可在 `证据层级` 额外填写 `natural UI-only`；同时必须在 `not_proven` 或证据说明里写清限制。

## 短合同字段

```md
## 玩家互动合同（短）
- 玩家目标：说明玩家想完成的经营动作、挑战动作或理解动作。
- 入口：说明玩家从哪里发现并进入。
- 主操作：说明玩家最自然会点击、选择、拖动或确认什么。
- 成功反馈：说明玩家如何知道事情成功了。
- 阻断原因：说明失败、拒绝、缺资源、未解锁时玩家看到的原因。
- 恢复路径：说明玩家下一步如何补救。
- 不展示信息：说明不得展示内部 id、debug 字段、runner 名、内部枚举、状态码或字段名。
- 证据层级：logic_runner / ui_contract / interactive_mcp / visible_capture / manual_canary 中实际证明的一项或多项。
- 证据说明（可选）：说明 runner、fixture、截图、MCP、加速、bridge helper、fallback 或 mixed evidence 等支撑与限制。
- not_proven：说明本次不能宣称的玩家体验、自然链路或挑战结果。
```

## 证据层级选择表

| 想声明 | 最低前置条件 | 不能声明 |
| --- | --- | --- |
| `logic_runner` 代码合同通过 | focused/headless runner、规则、状态、存档、结算数据或 manager/API 合同通过。 | 玩家看见、点到、读懂或体验顺畅。 |
| `ui_contract` UI 合同通过 | UI runner 或界面合同验证入口、按钮、文案、禁用原因、禁显内部字段。 | 真实玩家体验顺畅或自然完成。 |
| `interactive_mcp` 可交互验证通过 | interactive MCP、Playtest Bridge 或玩家等价输入路径通过，并披露工具支撑。 | 无支撑自然通关或人工体验确认。 |
| `visible_capture` 可见状态验证通过 | visible capture、可见窗口截图或协议认可的可见状态，并披露 fixture、fallback、加速和工具支撑。 | 玩家自然点击完成或完整自然链。 |
| `manual_canary` 体验可理解 | 人工 feel review 或 manual canary 已观察理解成本、点击路径、节奏、挫败感、信息过载和下一步清晰度。 | 完整自然通关，除非另有自然链证据。 |
| `natural UI-only` 自然通关 | 任务明确要求；同一玩家可见窗口；无 fixture；无 direct manager/API；无加速；无桥接支撑。 | 由 runner、混合支撑、fixture、fallback、bridge helper 或局部前缀外推完整通关。 |

## 选择规则

- 有任何 fixture、加速、direct manager/API、bridge helper、fallback 或 mixed evidence，只能写对应支撑层级。
- 没有 visible capture 或交互证据，不能写“玩家看见/点到”。
- 没有 manual feel review，不能写“体验可理解”。
- 没有明确自然链任务要求，不追求也不声明 `natural UI-only`。
- 出现 `natural UI-only` 时，必须同时说明任务明确要求、无 fixture、无 direct manager/API、无加速、无桥接支撑。
