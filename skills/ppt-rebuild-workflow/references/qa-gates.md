# QA 门禁入口（兼容旧链接）

当前门禁以 [qa-standards.md](qa-standards.md) 为准；检查范围见 [adaptive-verification.md](adaptive-verification.md)，文字来源优先级见 [text-recovery.md](text-recovery.md)。

- 用户提供的标题和正文在指定范围内作为定稿，不再与截图旧字反复核对；仍检查最终 PPTX 的原生文字、完整性和可读性。
- 默认 balanced 按风险触发坐标和字体校准；strict/full 保留完整计算证据。触发计算校准时，锚点不足或结果 INCONCLUSIVE 不能声明校准通过。
- B/C 不再一律要求先建纯图片基线 deck；是否生成由当前任务与 QA 策略决定。始终检查最终渲染与参考图的还原度及文字可读性。
- 素材必须检查实际透明通道；人工抠图交接不能标成 Level 3 全部通过。

旧版本的强制基线、无条件全量校准及笼统禁用文字诊断规则已被上述文档替代。
