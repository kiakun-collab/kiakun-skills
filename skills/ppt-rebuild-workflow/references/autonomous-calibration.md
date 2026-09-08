# 按需计算校准

仅 strict 或 [adaptive-verification.md](adaptive-verification.md) 的具体触发项出现时加载：

抽取测量 → 初版布局 → 保存并渲染 → 计算误差 → 定向修正 → 重渲染。

无需构建前通过依赖最终渲染的校准。临时校准页只用于变换诊断。

## 坐标

extract_reference_measurements.py 指定实际画布，保留唯一 coordinateTransform；随后对真实渲染运行 calibrate_reference_render.py。

只用稳定面板、图片区、长边，不用字形碎片凑 3 个锚点。不足为 INCONCLUSIVE，超容差 FAIL；自动标注图重合不能冒充 PPT 校准。默认容差 max(6 px, 长边 0.5%)，特殊精度按任务记录。

自动候选若是贯穿整页的窄条或全部挤在同一局部，应舍弃该组候选，选取有明确视觉语义且分布合理的边界。明确的真实分隔线可以保留；不要仅凭长宽比删除所有长线。计算 PASS 只证明所选锚点的匹配，不证明整页。

balanced/fast 仅触发页，strict 全页。无足够锚点的简洁页可记录直接 bbox 与渲染验证，但不能声称严格计算校准通过。

## 字体

初版直接用目标/可用字体；换行、替换、字高/基线漂移、裁切触发对应样式 2–4 个候选。strict 覆盖主要样式。

用户正文/标题替换了原图文字时，优先使用用户文案验证当前布局；不要求与旧文案的行数和字形宽度相同。候选相对最低分不等于绝对达标，所有候选都明显不合适时记录未解决，不追加无收益的穷举。

同轮候选尽量排在一个探针 deck 一次渲染，用 renderCrop 分别测量。纯文字/统一对比背景隔离字形，避免底纹被当成字。使用真实文案、相同文本框和最终渲染器；不穷举字体×字号×行距，每轮先改最可能出错的一项。

score_typography_candidates.py 排除裁切和错行，选有效最低误差。字形 bbox/基线是像素代理，不证明文案或全部字体观感，仍看最终页。

## 证据

targeted 的 triggeredChecks 写 kind、reason、evidenceFile，指向对应脚本 PASS 结果。strict 保存全页 coordinateCalibration 与 typographyCalibrationFiles。仅依赖完全相同才复用探针，返修上限跟随 executionProfile，不因 INCONCLUSIVE 自动生图或降级编辑要求。
