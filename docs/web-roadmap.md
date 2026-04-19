# Web Refactor Roadmap

## 1. Goal

把当前以脚本为主的“软著材料预审工具”，重构成一个可网站化部署的“软著材料审查 Agent 平台”。

最终形态不是单次运行的 CLI，而是一个支持上传 ZIP、自动分类材料、异步审查、在线查看结果、导出报告的 Web 系统。

核心目标：

- 支持单个软著项目的一揽子材料审查
- 支持多个软著项目的同类材料批量审查
- 保留规则审查能力
- 引入 AI 作为增强审查层，而不是唯一判断来源
- 为后续前端页面、任务队列、数据库、对象存储预留清晰边界


## 2. Current State

当前仓库已经有价值的能力主要有四类：

- 文档读取与提取
- 脱敏处理
- 规则审查
- 报告生成

但它还处于“脚本原型”阶段，和网站产品之间有明显差距：

- 存在两套入口：根目录 `cli.py` 与 `src/cli.py`
- 规则和数据写死在具体项目里，缺少通用抽象
- `.doc` / `.docx` / `.pdf` 解析链路不统一
- 没有数据库、任务系统、上传流程、用户操作状态
- 没有针对 ZIP 批量导入的领域模型
- 测试、依赖、配置尚未工程化


## 3. Final Product Vision

建议把最终产品定义为：

“一个面向软著申报前质检的 Web 平台。用户上传 ZIP 包后，系统自动识别材料、按项目归档、执行规则审查与 AI 审查、输出结构化问题和报告。”

系统完成的不是“代提交”，而是“预审、归档、比对、报告”。

产品能力可分为 5 个层次：

1. 上传与归档
2. 材料识别与解析
3. 审查与一致性校验
4. 结果查看与人工复核
5. 报告导出与批量管理


## 4. ZIP Upload Modes

你提到的两种 ZIP，是整个产品设计的核心。建议把它们明确建模为两种导入模式。

### Mode A: Single Case Package

一个 ZIP 对应“同一个软著项目”的一组材料。

典型内容：

- 信息采集表
- 源代码
- 软著文档/说明书
- 合作协议

这个模式的目标是：

- 自动归为一个 `Case`
- 做跨材料一致性检查
- 产出一个项目级综合报告

建议支持的 ZIP 结构：

```text
case_bundle.zip
  信息采集表.doc
  源代码.doc
  软著文档.doc
  合作协议/
    2501_合作协议.doc
    2502_合作协议.doc
```

也要允许“文件都堆在根目录”，由系统自动识别。

### Mode B: Batch By Material Type

一个 ZIP 对应“不同软著项目，但同一种材料类型”的批量集合。

典型内容：

- 一批合作协议
- 一批源代码
- 一批说明书
- 一批信息采集表

这个模式的目标是：

- 不强求一次形成完整 `Case`
- 先对同类型材料做批量解析和单材料审查
- 后续允许再与其他批次材料合并成完整项目

建议支持的 ZIP 结构：

```text
agreements_batch.zip
  A公司_合作协议.doc
  B公司_合作协议.doc
  C公司_合作协议.pdf
```

或：

```text
source_batch.zip
  项目A_代码.doc
  项目B_代码.doc
  项目C_代码.doc
```


## 5. Domain Model

网站化之前，最重要的是先把领域模型定下来。推荐如下。

### 5.1 Submission

一次上传行为。

字段建议：

- `id`
- `mode`: `single_case_package` / `batch_same_material`
- `filename`
- `storage_path`
- `status`
- `created_at`
- `created_by`

### 5.2 Case

一个软著项目实体。

字段建议：

- `id`
- `case_name`
- `software_name`
- `version`
- `company_name`
- `status`
- `source_submission_id`
- `created_at`

说明：

- Mode A 上传后通常会直接创建一个 `Case`
- Mode B 上传后可以先只创建 `Material`，再通过后续匹配生成或绑定 `Case`

### 5.3 Material

单个材料文件。

字段建议：

- `id`
- `case_id` nullable
- `submission_id`
- `material_type`
- `original_filename`
- `storage_path`
- `file_ext`
- `parse_status`
- `review_status`
- `detected_software_name`
- `detected_version`

`material_type` 建议枚举：

- `info_form`
- `source_code`
- `software_doc`
- `agreement`
- `unknown`

### 5.4 ParseResult

单个材料解析结果。

字段建议：

- `material_id`
- `raw_text_path`
- `clean_text_path`
- `desensitized_text_path`
- `metadata_json`
- `parser_name`
- `parser_version`

### 5.5 ReviewResult

单个材料或项目级审查结果。

字段建议：

- `id`
- `scope_type`: `material` / `case`
- `scope_id`
- `reviewer_type`: `rule_based` / `ai` / `hybrid`
- `severity_summary_json`
- `issues_json`
- `score`
- `conclusion`
- `created_at`

### 5.6 ReportArtifact

导出的报告文件。

字段建议：

- `id`
- `scope_type`
- `scope_id`
- `report_type`
- `file_format`
- `storage_path`
- `created_at`

### 5.7 Job

异步任务。

字段建议：

- `id`
- `job_type`
- `scope_type`
- `scope_id`
- `status`
- `progress`
- `error_message`
- `started_at`
- `finished_at`


## 6. Core Processing Pipeline

建议把整个系统处理流程拆成标准流水线，而不是让 CLI 一次性串到底。

### Step 1: Upload

用户上传 ZIP。

系统做：

- 保存原始 ZIP
- 创建 `Submission`
- 创建解压任务

### Step 2: Unpack

系统解压 ZIP 后，扫描内部文件。

系统做：

- 过滤不支持文件类型
- 记录层级结构
- 生成文件清单

### Step 3: Classification

系统对每个文件识别材料类型。

识别依据：

- 文件名关键词
- 扩展名
- 文本内容特征
- 目录位置

识别结果：

- `info_form`
- `source_code`
- `software_doc`
- `agreement`
- `unknown`

必要时允许前端人工纠正分类。

### Step 4: Case Mapping

这是两种模式最大的分叉点。

#### Mode A

系统将全部材料映射到同一个 `Case`。

#### Mode B

系统先只建立 `Material` 记录，再按以下策略尝试归并：

- 从材料中提取软件名称
- 从材料中提取版本号
- 从文件名中提取项目名
- 相似名称聚类

如果无法高置信归并，就暂时保持“未归档材料”，等待人工合并。

### Step 5: Parsing

不同材料进入不同解析器。

建议解析器拆成：

- `DocBinaryParser`
- `DocxParser`
- `PdfParser`
- `CodeMaterialParser`

输出统一结构：

- 原始文本
- 清洗文本
- 脱敏文本
- 解析元数据

### Step 6: Review

建议拆为三层：

#### Layer A: Material Rule Review

例如：

- 合作协议用词检查
- 文档版本号检查
- 代码乱码比例检查
- 信息采集表字段提取

#### Layer B: Cross Material Review

仅对完整 `Case` 执行：

- 软件名称一致性
- 版本号一致性
- 代码与文档对应性
- 信息采集表与其余材料一致性

#### Layer C: AI Review

AI 不直接取代规则，而是：

- 解释问题
- 做语义层判断
- 汇总综合结论

### Step 7: Report Generation

输出报告建议分三类：

- 单材料报告
- 项目级综合报告
- 批次汇总报告

### Step 8: Manual Review

前端应允许用户：

- 标记误判
- 修改材料类型
- 合并/拆分 Case
- 重新触发审查


## 7. Recommended Architecture

建议采用“先单体、后服务化”的路线。

第一阶段不要一上来拆微服务，先把边界拆清楚。

### 7.1 Recommended Backend Stack

基于当前仓库是 Python，后端建议继续用 Python。

推荐：

- FastAPI: Web API
- Pydantic: 入参/出参模型
- SQLAlchemy or SQLModel: ORM
- PostgreSQL: 结构化数据
- Redis: 任务队列/缓存
- Celery or Dramatiq: 后台任务
- Local FS or MinIO: 文件存储

如果前期想快速落地，可以先简化为：

- FastAPI
- SQLite
- 本地文件存储
- FastAPI 后台任务或轻量队列

### 7.2 Recommended Frontend Stack

有两条路线：

#### Option A: FastAPI + Jinja/HTMX

适合最短路径做内部工具。

优点：

- 开发快
- 部署简单
- 前后端不分离

缺点：

- 后期复杂交互会受限

#### Option B: Frontend SPA + FastAPI API

推荐长期路线。

建议：

- Next.js / React
- 或 Vue 3 + Vite

优点：

- 更适合上传、任务状态、结果面板、筛选管理
- 更适合后期做用户系统与权限

如果以“最终形态”考虑，我更推荐：

- FastAPI + React/Next.js


## 8. Target Repository Structure

建议逐步重构为：

```text
app/
  api/
    routers/
    schemas/
    deps/
  core/
    domain/
    services/
    pipelines/
    parsers/
    reviewers/
      rules/
      ai/
    reports/
    utils/
  infra/
    db/
    storage/
    queue/
    settings/
  workers/
  web/
tests/
docs/
scripts/
data/
```

说明：

- `app/core` 放纯业务逻辑
- `app/api` 只处理 HTTP
- `app/infra` 只处理数据库、存储、队列
- `workers` 负责异步任务入口
- `web` 作为前端工程目录，或后续独立仓库


## 9. Mapping Current Files To New Structure

可以按下面的方式搬迁当前能力。

### Keep And Refactor

- `src/pdf_extractor.py` -> `app/core/parsers/pdf_parser.py`
- `src/word_to_pdf.py` -> `app/core/parsers/word_converter.py`
- `prompts/review_prompt.py` -> `app/core/reviewers/ai/prompts.py`
- `prompts/specifications.py` -> `app/core/reviewers/rules/specs.py`

### Split Up

根目录 `cli.py` 需要拆分，不应继续保留为超大脚本。

建议拆成：

- `agreement_rules.py`
- `document_rules.py`
- `source_code_rules.py`
- `info_form_rules.py`
- `cross_material_rules.py`
- `report_builders.py`
- `desensitizers.py`
- `material_classifiers.py`

### Remove Or Downgrade

- 根目录 `cli.py` 未来只保留成调试入口
- `temp/` 迁移到 `scripts/` 或删除
- 输出产物不应长期放入仓库，应改为运行时存储


## 10. ZIP Classification Strategy

网站化后，ZIP 处理不能只靠目录名，必须支持“自动识别 + 人工修正”。

建议采用三层分类策略：

### Layer 1: Filename Rules

例如：

- 包含“信息采集表” -> `info_form`
- 包含“代码”或“源代码” -> `source_code`
- 包含“软著文档”或“说明书” -> `software_doc`
- 包含“合作协议” -> `agreement`

### Layer 2: Content Rules

解析文本后再判断：

- 包含“软件名称”“著作权人” -> `info_form`
- 大量代码符号和英文标识符 -> `source_code`
- 包含目录、章节、运行环境 -> `software_doc`
- 包含甲方乙方、签订、生效 -> `agreement`

### Layer 3: Manual Override

前端给用户一个确认表格：

- 原文件名
- 自动识别类型
- 所属项目
- 是否需要改类

这一步很重要，能显著降低误判成本。


## 11. Review Engine Design

建议明确做成“混合审查引擎”。

### Rule Based Review

优先负责：

- 明确规则
- 格式性问题
- 版本号问题
- 名称一致性问题
- 敏感词与固定措辞问题

特点：

- 稳定
- 可解释
- 成本低

### AI Review

负责：

- 语义判断
- 复杂一致性解释
- 问题归因
- 综合报告生成

特点：

- 灵活
- 易受输入质量影响
- 需要良好提示词与结构化输出约束

### Final Recommendation

推荐总策略：

```text
规则先筛查 -> AI 再解释和汇总 -> 用户确认 -> 生成正式报告
```


## 12. API Design Sketch

后端接口建议至少包括：

### Upload

- `POST /api/submissions`
- `GET /api/submissions/{id}`
- `GET /api/submissions/{id}/files`

### Classification

- `POST /api/submissions/{id}/classify`
- `PATCH /api/materials/{id}`

### Case Management

- `GET /api/cases`
- `GET /api/cases/{id}`
- `POST /api/cases/{id}/merge-materials`

### Review

- `POST /api/cases/{id}/review`
- `POST /api/materials/{id}/review`
- `GET /api/jobs/{id}`

### Reports

- `GET /api/reports/{id}`
- `POST /api/cases/{id}/reports`
- `POST /api/submissions/{id}/batch-report`


## 13. UI Design Sketch

前端建议至少有这些页面：

### 1. Upload Page

支持：

- 选择 ZIP
- 选择导入模式
- 查看上传说明

### 2. Submission Detail Page

显示：

- ZIP 文件信息
- 解压后的文件列表
- 自动分类结果
- 分类修正入口

### 3. Case Detail Page

显示：

- 项目基本信息
- 四类材料卡片
- 审查状态
- 问题清单
- 综合报告

### 4. Batch Review Page

适合 Mode B：

- 同类型材料列表
- 批量问题统计
- 可按文件筛选

### 5. Review Issue Page

显示：

- 严重/中度/轻微问题
- 规则来源
- AI 解释
- 是否误报


## 14. Suggested Milestones

建议分四期做，不要一步到位。

### Phase 1: Core Refactor

目标：

- 把当前脚本逻辑抽成可复用 Python 包
- 不做 Web，只保留 CLI 作为调试入口

交付：

- 统一解析接口
- 统一审查接口
- 统一报告接口

### Phase 2: ZIP Ingestion + Case Model

目标：

- 支持 ZIP 上传、解压、分类、建档

交付：

- Submission 模型
- Case 模型
- Material 模型
- ZIP 模式 A / B 基础支持

### Phase 3: Web API + Basic UI

目标：

- 做出可用的网站雏形

交付：

- 上传页面
- 任务状态页面
- 项目详情页面
- 报告查看页面

### Phase 4: AI Enhancement + Manual Review

目标：

- 用 AI 做补充解释与综合结论
- 支持人工纠正分类和误判

交付：

- AI 审查任务
- 人工复核 UI
- 重新审查机制


## 15. First Practical Refactor Tasks

如果下一步开始动代码，建议按这个顺序做：

1. 抽离根目录 `cli.py` 的规则函数，建立 `app/core/reviewers/rules/`
2. 建立统一 `MaterialType` 枚举和 `Case/Material` 数据模型
3. 建立统一解析接口：`parse_material(file_path, material_type)`
4. 建立 ZIP 解压与文件识别服务
5. 建立项目级聚合服务：`build_case_from_submission()`
6. 建立报告服务：单材料报告、项目报告、批次报告
7. 再接 FastAPI
8. 最后做前端


## 16. Key Design Decisions

以下决策建议尽早定下来。

### Decision A: Web First, CLI Second

后续以 Web API 为主，CLI 只用于测试与开发调试。

### Decision B: Case Is The Core Entity

完整软著项目应围绕 `Case` 组织，而不是围绕文件夹组织。

### Decision C: ZIP Is Only Ingestion Format

ZIP 只是导入方式，不应成为业务核心对象。

### Decision D: Rule Engine Must Be Independent

规则审查必须能脱离 AI 单独运行。

### Decision E: Human Override Is Necessary

材料分类和 Case 归并都必须允许人工修正。


## 17. Recommended Next Step In This Repo

当前仓库最合理的下一步不是直接写前端，而是先完成“核心能力收敛”。

建议马上做这三件事：

1. 建一个 `app/core`，把解析、脱敏、审查、报告代码迁进去
2. 把 ZIP 两种模式建模成 `SubmissionMode`
3. 把“材料类型识别”和“Case 聚合”做成独立服务

等这一步完成后，再接 Web 层会非常顺。


## 18. One Sentence Summary

这个项目的正确演进方向，不是把现有 CLI 硬包一层网页，而是先把它重构成“可被 Web 调用的审查引擎”，再围绕 ZIP 导入、Case 管理和异步任务做成网站。
