# P5-P8 验证记录

## 日期

- 2026-04-19

## 自动化回归

### Full Regression

- 命令：`py -m pytest`
- 结果：`74 passed, 0 failed`

### 本轮新增 / 扩展覆盖点

- `Support / Ops` 页面可访问
- 启动自检结果结构
- `external_http` provider skeleton 的 fallback 行为
- Case report 中的 AI 分层展示
- `input_runner` 的聚合指标函数
- Submission 页新增 `Import Digest`
- Case 页新增 `AI Supplement`

## 真实样本烟测

### 模式 A

- 命令：`py -m app.tools.input_runner --path input\软著材料 --mode single_case_package`
- 结果：
  - 六个 ZIP 全部完成
  - 聚合输出：`packages=6 materials=24 cases=6 reports=6 unknown=0 needs_review=10 low_quality=10 redactions=239`
- 关键结论：
  - 模式 A `unknown` 总数已从前一轮的 `1` 收敛到 `0`
  - 本轮主要剩余压力转移到 `low_quality / needs_review`

### 模式 B

- 命令：`py -m app.tools.input_runner --path input\合作协议 --mode batch_same_material`
- 结果：
  - `materials=11`
  - `cases=10`
  - `reports=1`
  - `types={'agreement': 11}`
  - `needs_review=2`
  - `low_quality=2`
  - `redactions=149`

## 页面与运维路径确认

- `/` 首页可访问，保留上传主入口。
- `/submissions` 批次中心可访问。
- `/submissions/{id}` 可查看：
  - `Import Digest`
  - `Operator Console`
  - `Needs Review`
  - `Export Center`
  - `Artifact Browser`
- `/cases/{id}` 可查看 `AI Supplement`。
- `/ops` 可查看：
  - 启动自检
  - 当前配置
  - 日志下载入口
  - 常用验证命令

## 结论

- 本轮已完成从“解析质量收敛”到“管理台可运维化”的过渡。
- 现在系统的主要剩余工作重心不再是 `unknown`，而是：
  - legacy `.doc` 低质量文本的进一步收敛
  - 浏览器级 E2E
  - 真实 provider 的正式接入与端到端验收
