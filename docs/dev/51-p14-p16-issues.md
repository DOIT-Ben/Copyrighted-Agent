# P14-P16 问题与修复

## Issue 1

- 现象：provider 契约虽然已收紧，但仍缺少“真实 HTTP 调一次”的联调入口。
- 影响：后续接企业内网网关或真实 provider 时，无法先本地演练 request/response。
- 修复：
  - 新增 `provider_sandbox`
  - 增加本地 HTTP 集成测试

## Issue 2

- 现象：runtime cleanup 只解决“删什么”，还没有解决“怎么保留和恢复”。
- 影响：运维策略不闭环。
- 修复：
  - 新增 `runtime_backup create / inspect / restore`
  - restore 默认 dry-run
  - 用 SQLite backup API 保证归档质量

## Issue 3

- 现象：真实样本结果虽然持续记录在文档里，但还没有沉淀成可复跑的结构化快照。
- 影响：后续趋势比较仍依赖人工抄数。
- 修复：
  - 新增 `metrics_baseline`
  - 输出 Markdown + JSON
  - 支持读取历史 snapshot 比较 delta

## Issue 4

- 现象：`runtime_backup inspect` 与 `restore` 在 Windows/GBK 终端下输出大清单时触发 `UnicodeEncodeError`。
- 影响：工具可用性下降，即使底层逻辑正确也无法稳定在本机执行。
- 修复：
  - 所有 CLI 输出统一走 UTF-8 buffer
  - inspect 默认输出摘要
  - restore 默认仅预览前 10 条并显示省略数量
