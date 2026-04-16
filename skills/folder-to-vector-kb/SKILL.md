---
name: folder-to-vector-kb
description: 把指定文件夹中的公司案例、提案、研究、复盘等文件整理成可用于向量检索的结构化知识库。
---

# folder-to-vector-kb

## 这个 skill 是干什么的

当用户希望把一个指定文件夹中的公司案例、方案、研究、复盘、会议纪要、方法论文档，整理为可用于向量检索的知识库时，使用这个 skill。

这个 skill 的目标不是先设计一套大而全的平台，而是先把 **用户手头这批文件本身** 处理干净，输出可直接做 embedding / retrieval 的结构化结果。

---

## 适用场景

适用于以下任务：
- 把某个文件夹中的 PPT / PDF / DOCX / Markdown / TXT 整理成知识库
- 识别终稿、排除过程稿、抽取高价值内容
- 对广告行业文件做语义 chunk 切分与元数据补全
- 输出 `knowledge_base.jsonl` 供向量库 ingest 使用

不适用于以下任务：
- 网站多轮搜索与网页抓取
- 实时联网 research
- 通用爬虫系统设计
- 复杂数据库平台搭建

---

## 工作原则

### 1. AI 先处理文件本身，不要先空转做系统设计
默认优先直接分析这批文件，完成入库判断、清洗、chunk 切分和元数据补全。

### 2. 不要只按文件夹机械扫描
很多真实文件不会规整地放在项目文件夹里。必须同时结合：
- 文件夹名
- 文件名中的项目名
- 文档首页标题 / 目录 / 封面中的项目名
来识别项目归属。

### 3. 终稿优先，过程稿慎入库
不要把头脑风暴稿、发散稿、占位稿、中间版本整份塞进知识库。

### 4. 语义完整优先于字数平均
不要机械按 1000 字切块。chunk 应该在语义边界处切开，并且单独拿出来也能看懂。

### 5. 输出要能直接被后续系统消费
最终输出必须稳定、结构化、字段明确，便于后续做 embedding、向量存储、检索和引用。

---

## 输入

当执行这个 skill 时，默认输入包括：

- `folder_path`：待处理文件夹路径
- `output_path`：输出 JSONL 路径
- `allowed_extensions`：允许处理的文件后缀，如 `.pptx .pdf .docx .md .txt`
- `project_name_hints`：可选，用户额外提供的项目名关键词
- `max_chunk_chars`：建议单 chunk 最大字符数，默认 1500
- `min_chunk_chars`：建议单 chunk 最小字符数，默认 100

---

## 标准工作流

## Step 1：扫描文件列表 + 项目归组 + 终稿识别

### 目标
获取指定目录下所有候选文件，并在以下两种情况下都能正确识别项目归属：
- 文件位于项目文件夹中
- 文件只是散落在公共目录中的单独文件

### 必做操作
1. 递归扫描文件夹，获取所有符合条件的文件
2. 记录：
   - `file_name`
   - `file_path`
   - `file_size`
   - `created_time`
   - `modified_time`
   - `extension`
3. 先尝试从文件夹名识别项目
4. 再从文件名中提取项目名，作为补足或修正依据
5. 如果文件夹名与文件名冲突：
   - 默认 **文件名中的项目名优先**
   - 同时标记 `needs_review = true`
6. 如果两者都不明确，再尝试从文档封面、首页标题、目录、首段中识别项目名
7. 如果仍无法识别，归入 `unclassified`
8. 在同一项目组中识别终稿：
   - 文件名含 `终稿` / `定稿` / `final` 优先
   - 修改时间更晚优先
   - 文件体积更大优先

### 项目识别优先级
1. 文件名中的项目名称
2. 当前文件夹名
3. 上级文件夹名
4. 文档首页 / 封面 / 目录中的项目名
5. `unclassified`

### Step 1 输出字段
- `project_name_candidate_from_filename`
- `project_name_candidate_from_folder`
- `resolved_project_name`
- `project_name_confidence`
- `needs_review`
- `is_final_candidate`

### 注意
不要把 Step 1 简化为“按文件夹分组”。在广告公司真实资料里，散文件、临时目录、混放目录非常常见。

---

## Step 2：AI 直接读取 + 数据验证

### 目标
AI 直接读取每个文件内容，判断是否适合进入知识库，并识别损坏模式。

### 必做判断
对每个文件都要明确给出：
- `入库判断`：`yes` / `partial` / `no`
- `入库原因`
- `doc_type`

### 文档语义类型
可使用以下类型：
- `brief`
- `proposal`
- `case_study`
- `research`
- `methodology`
- `meeting_notes`
- `creative_material`
- `process_draft`
- `other`

### 数据验证规则
优先识别以下损坏模式：
- Python 错误日志：如 `Traceback (most recent call last):`
- 编码损坏：如 `锟斤拷`、`烫烫烫`、`屯屯屯`
- 控制字符污染：如 `\x01`、`\x08`、`\x1a`
- 空格拆分内容：如 `h t t p s : / / ...`
- 严重低中文占比：中文比例低于 30%

### 过程稿识别标准
以下内容不能整份入库，通常只允许 `partial` 或 `no`：
- 头脑风暴稿
- 半成品 PPT
- 多方向发散稿
- 临时资料拼接稿
- 对话型过程讨论稿
- 标有 `V1`、`草案`、`旧版` 的中间版本

---

## Step 3：深度清洗

### 目标
移除技术性噪音，保留纯净且可检索的正文内容。

### P0 必须处理
- Python 日志头部 / Traceback
- HTML / XML 注释
- HTML 注释空格拆分变体
- 控制字符

### P1 强烈建议
- Markdown 图片语法
- Markdown 图片空格拆分变体
- 空格拆分 URL
- 图片文件名引用，如 `VGr5.jpg`
- 可读字符比例低于 40% 的乱码行

### P2 可选处理
- 3 个以上连续换行压缩为 2 个
- 多个连续空格压缩为 1 个
- 中文标点后多余空格清理

### 清洗原则
- 不要误删正文语义
- 保留有意义的英文、数字、术语、品牌名、KOL 名称、平台名
- 保留中英混合专业表达

---

## Step 4：语义 chunk 切分

### 目标
按语义边界切块，使每个 chunk 都具备独立价值。

### 规则
- 不按固定字数机械切块
- 优先在章节、主题、段落边界切分
- 一个 chunk 尽量只表达一个核心观点 / 策略 / 方法 / 结论
- 单独拿出 chunk 时，仍能基本看懂

### 建议长度
- 简短洞察：100-300 字
- 标准内容：300-800 字
- 复杂内容：800-1500 字

### 广告行业常见 chunk 类型
按需要从以下类型中选择最合适的：
- `client_brief`
- `project_brief`
- `proposal`
- `market_research`
- `consumer_insight`
- `audience_analysis`
- `competitive_analysis`
- `brand_strategy`
- `communication_strategy`
- `media_strategy`
- `positioning`
- `messaging`
- `campaign_strategy`
- `creative_brief`
- `creative_concept`
- `creative_derivation`
- `creative_execution`
- `copywriting`
- `slogan`
- `visual_creative`
- `video_creative`
- `event_creative`
- `content_strategy`
- `content_topic`
- `social_content`
- `kol_strategy`
- `kol_selection`
- `kol_brief`
- `kol_performance`
- `media_plan`
- `placement_monitoring`
- `performance_data`
- `data_analysis`
- `campaign_review`
- `optimization`
- `best_practice`
- `methodology`
- `glossary`
- `other`

---

## Step 5：补全元数据

### 目标
让每个文档、每个 chunk 都具备可检索、可筛选、可引用的元数据。

### 文档级字段
必须尽量补全以下字段：
- `doc_id`
- `file_name`
- `file_path`
- `file_size`
- `project_name_candidate_from_filename`
- `project_name_candidate_from_folder`
- `resolved_project_name`
- `project_name_confidence`
- `needs_review`
- `project_name`
- `client_name`
- `brand_name`
- `industry`
- `project_year`
- `doc_type`
- `入库判断`
- `入库原因`

### Chunk 级字段
每个 chunk 至少应包含：
- `chunk_id`
- `chunk_index`
- `chunk_title`
- `section_title`
- `chunk_type`
- `chunk_summary`
- `chunk_text`
- `why_this_chunk`
- `source_page`
- `tags`
- `brand_tone`
- `target_kpi`
- `core_message`
- `budget`
- `timeline`
- `cleaning_stats`

### 元数据补全要求
- `chunk_title` 要像知识标题，不要只是原文第一句
- `chunk_summary` 控制在约 30 字内
- `why_this_chunk` 要说明它为什么值得独立入库
- `tags` 要可检索，不要只写空泛大词

---

## Step 6：输出结构化结果

### 默认输出
至少输出以下文件：

1. `knowledge_base.jsonl`
   - 每行一个文档对象
   - 文档内包含 `chunks`

2. `ingest_report.md`
   - 记录总文件数
   - 入库数 / 部分入库数 / 不入库数
   - 待人工复核文件清单
   - 主要损坏模式统计
   - 终稿识别说明

### 推荐输出目录
```text
<root>/
├── 0-raw/
├── 1-structured/
│   ├── knowledge_base.jsonl
│   └── ingest_report.md
└── references/
```

---

## 输出 JSONL 结构要求

```json
{
  "doc_id": "uuid-xxx",
  "file_name": "项目A_终稿.pptx",
  "file_path": "F:\\知识库-比稿\\0-比稿\\项目A\\终稿.pptx",
  "file_size": 2048000,
  "project_name_candidate_from_filename": "项目A",
  "project_name_candidate_from_folder": "项目A",
  "resolved_project_name": "项目A",
  "project_name_confidence": 0.94,
  "needs_review": false,
  "project_name": "项目A",
  "client_name": "华为",
  "brand_name": "华为手机",
  "industry": "3C电子",
  "project_year": 2024,
  "doc_type": "proposal",
  "入库判断": "yes",
  "入库原因": "终稿，内容完整",
  "chunks": [
    {
      "chunk_id": "chunk-uuid-001",
      "chunk_index": 0,
      "chunk_title": "项目背景与目标",
      "section_title": "第一章 项目概述",
      "chunk_type": "project_brief",
      "chunk_summary": "项目旨在打造年轻化品牌形象",
      "chunk_text": "清洗后的纯净文本内容...",
      "why_this_chunk": "提供项目基础信息，帮助理解后续策略",
      "source_page": 1,
      "tags": ["项目背景", "目标用户", "核心挑战"],
      "brand_tone": "科技感、年轻化",
      "target_kpi": "曝光量1亿+",
      "core_message": "华为nova系列定位年轻人群",
      "budget": "500万",
      "timeline": "2024.Q1-Q2",
      "cleaning_stats": {
        "original_len": 500,
        "cleaned_len": 450,
        "retention_ratio": 0.9
      }
    }
  ]
}
```

---

## 执行检查清单

在交付结果前，逐项检查：
- 是否扫描了所有候选文件
- 是否同时使用了“文件夹 + 文件名 + 文档首页”三种项目信号
- 是否识别了终稿
- 是否剔除了明显过程稿噪音
- 是否做了深度清洗
- 是否按语义边界切块
- 是否补全了关键元数据
- 是否输出了 `knowledge_base.jsonl`
- 是否输出了 `ingest_report.md`
- 是否列出 `needs_review = true` 的文件

---

## 行为约束

### 应该做
- 直接处理用户这批文件
- 在必要时做最小脚本辅助，但脚本应服务于当前任务
- 对无法确定的项目归属给出置信度和复核标记
- 对不适合入库的文档明确拒绝整份入库

### 不应该做
- 一开始就把任务改写成大而全平台建设
- 只按文件夹名机械归组
- 只按字数切 chunk
- 把所有中间稿都塞进知识库
- 为了追求“通用性”而牺牲当前文件的实际可用性

---

## 交付风格

当用户要求实际执行任务时，优先给出：
1. 文件扫描结果摘要
2. 终稿 / 非终稿判断
3. 入库 / 不入库判断
4. 输出文件路径
5. 需要人工复核的少数问题点

避免输出空泛方法论，重点给可落地结果。
