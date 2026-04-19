# Test Strategy

## 1. Purpose

这份文档定义这个项目在“先测试、后开发”模式下的完整测试规划。

目标不是只列几个零散用例，而是建立一套能支撑后续网站化开发的测试体系。后续开发必须围绕这些测试展开，优先让核心契约稳定，再逐层补功能。

本策略默认产品最终形态为：

- 用户上传 ZIP
- 系统自动分类材料
- 系统按软著项目归档
- 系统执行规则审查与 AI 审查
- 用户在线查看问题与报告


## 2. Testing Principles

### 2.1 Contract First

先锁定未来模块的输入输出契约，再实现功能。

契约包括：

- 领域模型字段
- 枚举值
- 服务入口签名
- 返回结果最小结构
- 关键报告的最小内容

### 2.2 Rule Engine Must Be Testable Without AI

规则引擎必须能在不访问外部模型的情况下独立运行和测试。

### 2.3 Synthetic Fixtures First, Real Corpus Second

测试数据分两类：

- 合成样本：用于稳定、快速、可复现的单元与集成测试
- 真实样本：用于解析回归、质量验证、性能验证

### 2.4 Test The Product Shape We Want

测试不应只围绕当前脚本写，而要围绕未来产品形态写：

- `Submission`
- `Case`
- `Material`
- `ReviewResult`
- `Job`
- ZIP 模式 A / B

### 2.5 Failure Should Be Actionable

测试失败后，要能直接定位到：

- 解析层
- 分类层
- 聚合层
- 规则审查层
- AI 审查层
- 报告层
- API 层


## 3. Test Levels

### 3.1 Unit Tests

覆盖：

- 领域模型
- 枚举
- 纯函数
- 文本分类
- 脱敏逻辑
- 规则审查函数
- 报告渲染函数

要求：

- 无网络
- 不依赖数据库
- 尽量不依赖真实文件系统
- 执行速度快

### 3.2 Integration Tests

覆盖：

- ZIP 导入
- 文件分类
- Case 聚合
- 解析 -> 审查 -> 报告流水线
- FastAPI 接口

要求：

- 可以使用临时目录
- 可以使用临时数据库
- 默认不访问真实外部 AI

### 3.3 End-to-End Tests

覆盖：

- 用户上传 ZIP
- 等待任务完成
- 查看分类结果
- 查看项目详情
- 查看报告
- 人工修正并重跑

要求：

- 基于真实 Web 页面或可替代的 API 旅程
- 仅覆盖关键主路径

### 3.4 Non-Functional Tests

覆盖：

- 安全
- 性能
- 稳定性
- 并发
- 可观察性
- 数据脱敏与隐私


## 4. Scope And Coverage Matrix

### 4.1 Domain Model

必须测试：

- `SubmissionMode` 至少包含两种模式
- `MaterialType` 至少包含四类材料和 `unknown`
- `Submission`、`Case`、`Material`、`ParseResult`、`ReviewResult`、`ReportArtifact`、`Job` 的核心字段齐全
- 领域模型可稳定序列化

### 4.2 ZIP Ingestion

必须测试：

- ZIP 上传成功
- 非 ZIP 上传失败
- ZIP 解压后能列出文件清单
- 支持根目录平铺结构
- 支持子目录结构
- 阻止 Zip Slip 路径穿越
- 非白名单后缀处理策略正确
- 重名文件处理策略正确

### 4.3 Material Classification

必须测试：

- 基于文件名关键词识别四类材料
- 基于文本内容纠正文件名误导
- 内容不足时返回 `unknown`
- 用户人工修正后优先使用人工结果

### 4.4 Case Mapping

Mode A 必须测试：

- 单个 ZIP 归为单个 `Case`
- 同一个 `Case` 下允许多个合作协议
- 根目录与多层目录都可正确聚合

Mode B 必须测试：

- 可批量导入单一材料类型
- 不强制错误聚合成单一 `Case`
- 可按软件名称/版本号进行候选归并
- 低置信材料可保持未归档

### 4.5 Parsing

必须测试：

- `.doc` 解析器存在且行为受控
- `.docx` 解析器存在且行为受控
- `.pdf` 解析器存在且行为受控
- 统一 `parse_material(file_path, material_type)` 入口存在
- 解析输出至少包含原始文本、清洗文本、脱敏文本、元数据
- 解析失败时返回可解释错误，而不是静默吞掉

解析回归必须覆盖：

- 中文文本
- 中英混排
- 代码片段
- 目录页
- 页眉页码
- 空文档
- 损坏文件

### 4.6 Desensitization

必须测试：

- 公司名脱敏
- 人名脱敏
- 身份证号/统一社会信用代码脱敏
- 重复脱敏幂等
- 非敏感词不误伤

### 4.7 Rule Review

必须测试：

- 合作协议用词问题
- 日期和签署逻辑问题
- 版本号不一致
- 软件名称不一致
- 代码乱码比例
- 信息采集表字段提取
- 跨材料一致性检查
- 严重/中度/轻微问题分级

### 4.8 AI Review

必须测试：

- AI 审查服务存在 mock provider
- AI 输入结构化、可替换
- AI 输出具备结构化字段
- AI 失败时不阻断规则引擎主流程
- AI 结果可与规则结果合并

### 4.9 Report Generation

必须测试：

- 单材料报告生成
- 项目综合报告生成
- 批次汇总报告生成
- Markdown 内容包含核心摘要
- 结构化 JSON 报告可导出

### 4.10 API

必须测试：

- ZIP 上传接口
- 查询 Submission 接口
- 查询材料列表接口
- 触发审查接口
- 查询 Job 状态接口
- 查询/下载报告接口
- 参数校验
- 错误码语义

### 4.11 Web UI

必须测试：

- 上传 ZIP
- 选择导入模式
- 查看自动分类结果
- 修改分类
- 查看项目详情
- 查看问题详情
- 重新触发审查

### 4.12 Security

必须测试：

- Zip Slip 防护
- 非法路径写入防护
- 不允许执行型文件混入解析目录
- 日志中不泄露原始敏感信息
- 错误响应不暴露内部路径

### 4.13 Performance

必须测试：

- 单项目 ZIP 导入时延
- 批量同类材料 ZIP 导入时延
- 大批量文件下任务队列吞吐
- 报告生成耗时
- 同时多个提交的稳定性

### 4.14 Reliability And Operations

必须测试：

- Job 状态迁移正确
- 失败任务有错误信息
- 重试机制不会产生重复副作用
- 相同 ZIP 反复提交时行为可解释
- 清理中间文件的策略正确


## 5. Priority Levels

### P0

必须在第一阶段就写并长期维护：

- 领域模型
- ZIP 导入
- 分类
- Case 聚合
- 规则审查
- 报告生成
- 核心 API
- 安全基础项

### P1

第二阶段补齐：

- AI mock provider
- AI 结果结构化
- Web 主路径
- 任务状态
- 真实样本解析回归

### P2

后续增强：

- 浏览器兼容
- 批量操作体验
- 性能阈值回归
- 运行指标采集


## 6. Test Data Strategy

### 6.1 Synthetic Fixtures

默认使用轻量、可读、可版本管理的合成样本：

- `信息采集表.txt`
- `源代码.txt`
- `软著文档.txt`
- `合作协议.txt`
- 含中文文件名的 ZIP
- 含多层目录的 ZIP
- 含异常路径的恶意 ZIP

用途：

- 单元测试
- 集成测试
- API 测试

### 6.2 Real Corpus

单独维护一小组真实材料，仅用于：

- `.doc` / `.docx` / `.pdf` 解析回归
- 乱码率校验
- 报告质量比对
- 性能基线

要求：

- 去敏
- 不直接提交大量原始真实材料到仓库
- 用专门目录或私有样本存储管理


## 7. Environments

### 7.1 Local

用途：

- 开发时快速回归
- 运行 unit + 部分 integration

### 7.2 CI

用途：

- PR 阶段自动执行

建议至少分两档：

- 快速档：unit + contract + 核心 integration
- 完整档：快速档 + API + 安全 + 部分性能冒烟

### 7.3 Pre-Release

用途：

- 真实部署形态验证
- E2E
- 真实样本回归
- 并发与任务系统验证


## 8. Exit Criteria

进入开发阶段前，至少要满足：

- 测试目录结构建立完成
- 契约测试文件建立完成
- ZIP 模式 A / B 的合成样本夹具存在
- 关键服务的测试入口约定清楚

进入 MVP 交付前，至少要满足：

- 所有 P0 测试通过
- 安全基础项通过
- 单项目 ZIP 主路径通过
- 项目级报告生成通过

进入网站第一版上线前，至少要满足：

- Mode A 主路径 E2E 通过
- 关键 API 测试通过
- 任务状态和失败处理可观测
- 日志与报告不泄露敏感信息


## 9. Mapping To Current Repo

当前仓库要先建立如下测试骨架：

- `tests/unit/`
- `tests/integration/`
- `tests/non_functional/`
- `tests/helpers/`
- `pytest.ini`

第一批要写的测试文件：

- 领域模型契约
- 解析器契约
- 分类契约
- 规则审查契约
- AI 审查契约
- 报告契约
- Mode A 集成契约
- Mode B 集成契约
- API 契约
- 安全契约


## 10. One Sentence Summary

开发必须围绕测试推进：先锁契约和主路径，再写实现；先保证规则引擎和 ZIP 导入稳定，再逐步扩展到 Web、AI 和性能。

