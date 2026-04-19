# P5-P8 收敛计划

## 日期

- 2026-04-19

## 本轮目标

- 把 legacy `.doc` 收敛结果正式落盘，并确认真实样本模式 A 的 `unknown` 总数降到 `0`。
- 补齐浏览器端管理台的导入摘要、模式 B 批量导入说明、操作台预填和 `Support / Ops` 运维页。
- 在 `safe_stub` 之后加入真实 provider 的接口骨架，同时坚持“仅脱敏 payload 可进入非 mock provider”。
- 增加启动自检、配置模板、运行时保留策略说明，补强可运维性和可追溯性。
- 用自动化回归和真实样本烟测把本轮改动闭环。

## 范围

### P5 解析质量继续收敛

- 记录真实样本回归结果，明确模式 A 已无 `unknown`。
- 在命令行输入验证工具中增加聚合摘要，直接输出 `unknown / needs_review / low_quality / redactions` 总量。
- 在 Submission 页把 `quality_flags` 与 `unknown_reason` 展示得更直接。

### P6 浏览器侧体验增强

- 增加导入摘要卡。
- 增加首页运行摘要和模式 B 批量导入说明。
- 增加操作台预填、提示文本和更友好的备注占位文案。
- 增加单独的 `Support / Ops` 页面。

### P7 真实 AI Provider 接入准备

- 增加 `external_http` provider adapter skeleton。
- provider 调用必须经过脱敏校验。
- 增加 provider 调用开始 / 结束 / 失败日志。
- 在 Case 页和 Case 报告中区分“规则结论”与“AI 补充说明”。

### P8 运维与可追溯性

- 增加 `config/local.example.json`。
- 增加启动自检，覆盖：
  - 运行目录可写
  - 上传目录可写
  - SQLite 目录可写
  - 日志目录可写
  - 配置模板存在
  - AI 脱敏边界状态
- 在运维页呈现保留策略、配置和常用验证命令。

## 开发顺序

1. 先跑真实样本，确认 legacy `.doc` 收敛后的真实基线。
2. 先补后端骨架：
   - config 扩展
   - self-check
   - provider adapter
   - 路径配置化
3. 再补页面：
   - 首页导入说明
   - Submission 导入摘要卡 / review queue 增强 / operator 预填
   - Case 页规则与 AI 结果分离
   - Ops 页
4. 最后补测试和文档。

## 验收标准

- `py -m pytest` 全绿。
- `py -m app.tools.input_runner --path input\软著材料 --mode single_case_package` 输出聚合摘要，且 `unknown=0`。
- `py -m app.tools.input_runner --path input\合作协议 --mode batch_same_material` 继续稳定通过。
- `docs/dev` 中有本轮计划、构建、问题、验证和复用文档。
