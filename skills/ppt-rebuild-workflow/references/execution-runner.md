# 公共执行入口

`scripts/rebuild_workflow.py` 管理路由、执行记录、实际文件绑定和报告，不识别图片、不决定布局、不调用生图接口，也不替代 Presentations。每个独立交付件一个 run-dir；普通多页 PPT 共用一个，十个独立测试用例才建十个。证据目录放 work/。

## 开始与来源

按 task-input-template 填实际需求。用户定稿按对象放入 `userCopy`，例如：

```json
{"userCopy":[{"id":"title-01","page":1,"text":"用户提供的新标题","source":"本次用户消息","pptxShapeName":"title-01"}]}
```

仅背景资料不放入 userCopy；长文件先读取一次，把实际采用的定稿和文件定位记在这里。userCopy 为空时使用通常的内容来源流程。

```powershell
python scripts/rebuild_workflow.py init task-input.json --run-dir work/rebuild
python scripts/rebuild_workflow.py preflight work/rebuild
```

init 在构建前保存路由、定稿及需求哈希；后续检查其未被改写。E 同时备份源 PPTX。需求变更时建立新 run-dir，旧证据保留；不要修改旧快照绕过路由。

从 load_workspace_dependencies 和实际安装的 Presentations 获取 `runtime.nodeExecutable`、`pythonExecutable`、`nodeModules`、`presentationSkillDir`，使用绝对路径。preflight 同时检查独立启动与 **Node 启动 Python** 的实际嵌套路径，避免 finalizer 才遇到 EPERM。它不安装运行时、不更改权限；未配置项显示 INCOMPLETE。若子进程受限，按当前权限规则解决实际阻碍，不循环运行同一命令。

## 资产与文字

```powershell
python scripts/rebuild_workflow.py assets work/rebuild asset-manifest.json
python scripts/rebuild_workflow.py bind-copy work/rebuild extraction-observed.json --output extraction.json
```

assets 每批追加后审计整份已知资产表，返回 1 的 MANUAL_CUTOUT_REQUIRED 表示需交接，不阻塞无关页面。EMPTY、UNREADABLE 或 required 策略失败标 BLOCKED。详细结果为 asset-audit.json，包含源路径、实际哈希和下一步。

bind-copy 只更新抽取中与 userCopy ID 对应的文字字段，保留几何；其他页未匹配的 ID 不改。layout 的 sourceExtractionId 与原生文本框 name 建立映射，或在 userCopy 指明 pptxShapeName。相同 ID 的一段多色文字优先用一个文本框的 runs。报告阶段会从最终 PPTX 包读取实际文字，发现丢字或错写即 FAIL，不能用截图文字覆盖定稿。

## 构建与渲染

生图等待期间搭建文字、图表和已就绪页，按页面依赖推进。当前平台允许时少量并行独立生图或构建，最终组装仍由一个写入者完成，不让多个任务同时写同一 PPTX/报告。

由 Presentations 写 builder。可将 [rebuild-runtime.mjs](../assets/runtime/rebuild-runtime.mjs) **复制到任务 build 目录**，按当前 Presentations implementation 创建该目录的 node_modules 链接，然后从 builder 导入 `finalizeAndRender`。不能直接从 skill 安装目录导入带 bare imports 的副本。

适配器接受绝对路径 workspaceDir、candidatePath、finalPath、renderDir、presentationSkillDir、pythonExecutable，及真实 expectedSlideSizeEmu、requirements、fontPolicy。每版使用新 finalPath 和空 renderDir，避免覆盖旧证据。调用当前 finalizer，原生表格声明自动同步到 layoutArgs，再从最终实际 PPTX 导入并渲染，写 render-receipt.json 的 PPTX/各 PNG 哈希。它不覆盖源稿，不替代运行时标记，不自动安装依赖。Presentations 版本改变时核对当前 API；兼容性失败如实记录。

```powershell
python scripts/rebuild_workflow.py run work/rebuild --stage build --pages 1 2 --revision 0 --cwd . --render-receipt work/render/render-receipt.json -- node build.mjs
```

`--` 后为可执行文件与独立参数，不是 shell 字符串。使用实际 Node 绝对路径；run 注入已配置的 RUNTIME_NODE_MODULES，并将每次 stdout/stderr 写入唯一日志。必要的运行时标记按 Presentations 规定单独执行，不夹入该包装命令。

初次成功构建 revision=0；实际视觉返修递增，同一版的环境错误重试保持 revision，但每次都有独立记录。保存每版新文件。用 `--stage render/probe/operation --count N` 记录独立执行的实际渲染页次；若 build 内集成渲染，传 `--render-receipt`，脚本从本次适配器真实时间戳登记 render 子事件，无需再渲染或手工补记。build 总时长含该子事件，不把两者相加当总耗时。

外部工具可用 begin/end 包住调用，平台函数编排中获取 begin 输出后直接执行工具，结束时传实际返回状态与产物路径：

```powershell
python scripts/rebuild_workflow.py begin work/rebuild --stage imagegen --pages 1 --count 1
python scripts/rebuild_workflow.py end work/rebuild ACTUAL_EVENT_ID --exit-code 0 --artifacts work/assets/person.png
```

begin/end 只记时，不执行生图、不认定结果质量；工具失败同样 end 非零，alpha 不合格另走 assets。不要把未计时的过去阶段补写成实测。每事件独立文件支持并行；整体耗时与重叠的累计工具用时分开看。

## 一份视觉复核，自动汇总

```powershell
python scripts/rebuild_workflow.py prepare-review work/rebuild --pptx outputs/final.pptx --render-receipt work/render/render-receipt.json
```

先核对 receipt 的 PPTX、PNG 哈希及完整页序；并行运行结构/文字框审计，再创建该版本的 review-HASH.json。所有主观结论初始 PENDING/空值；查看真实最终页后填写 contentStatus、visionAuditStatus、visualFidelityStatus、editableBoundaryStatus、各类实际数量、pages 观察与触发项。同一份文件同时充当视觉审计、还原审计和 renderVerification，不复制三份结论。不要改其哈希来掩盖旧渲染。

内容 PASS：userCopy 已提供部分不再 OCR；未提供部分仍有来源。视觉 PASS 允许已记录 minor；major、遮字、明显接缝不能用 minor 隐藏。几何预警使用 qa-standards 的逐项 geometryExceptions，保留原始计数。C 再填写真实 level3Gates，并附实际移动后的必要证据；alpha 通道检查不能代替边缘复核。

使用原有 make_reference_render_comparison.py 生成配对图，填写 [evidence-input-template.json](../assets/templates/evidence-input-template.json) 的实际路径。路径相对于 evidence-input 文件；其中 reviewFile 指向上述共享复核文件。

```powershell
python scripts/rebuild_workflow.py report work/rebuild evidence-input.json
```

report 自动汇集实际页数、审计统计、版本事件、定稿检查和素材检查；运行标准验证器，生成 qa-report.json、evidence-validation.json、delivery-summary.md。未填观察、未完成事件、文案错写、过期图片、未解决 alpha 不能被报告器填成 PASS。strict 的实际测量/字体计算仍需对应脚本，自动汇总不替它们执行主观判断。

A/E 不调用 Level 2/3 验证器；evidence-input 用 modeSpecificEvidenceFile 引用各自实际检查报告，含 status 和 outputPptxSha256。A 检查一页一图、页序比例；E 检查指定对象差异、原稿/备份、前后渲染，新重构区域另按 B/C 验证。汇总器只验证文件绑定及 E 源稿未变，不伪称独立证明所有模式特有条件。

E 的 prepare-review 可只包含实际变更页；未变部分依靠专用对象/包内差异和必要的全稿扫描证明保留。B/C 最终复核仍覆盖所有交付页；局部返修可复用已证实依赖未变的其他页渲染，但不得把旧图直接换成当前哈希冒充复用证据，无法证明未变时重新渲染。

默认 standard：将成品、最终预览、简短交付说明及待抠素材放入 outputs，所有技术日志留 work。不默认打包所有中间版本/探针。benchmark 才整理完整对比与阶段计时，但不增加无目的的视觉返修。
