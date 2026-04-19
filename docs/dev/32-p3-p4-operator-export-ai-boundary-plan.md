# P3-P4 浏览器操作台、导出、日志与 AI 边界计划

## 日期

- 2026-04-19

## 本轮目标

- 补齐浏览器端最小可用操作台，让人工纠偏动作可以直接在管理台中完成。
- 增加报告、材料产物、提交包、应用日志下载能力，形成可追溯导出链路。
- 将上传、纠偏、下载事件写入结构化日志，便于后续排障和复盘。
- 把 AI provider 选择改为配置驱动，并强制非 mock provider 只能接收脱敏 payload。

## 本轮范围

- `Operator Console` 浏览器操作表单
- `Export Center` 与 `Artifact Browser`
- `app_logging.py` 结构化日志
- `exports.py` 下载与打包服务
- `AppConfig` 配置读取
- `safe_stub` 非 mock provider 预备适配层
- 非 mock provider 的脱敏强校验

## 不在本轮处理

- 真实外部模型供应商联网接入
- 浏览器级 E2E 自动化
- 老 `.doc` 深度提取能力升级

## Done 标准

- Submission 详情页可直接执行常见 operator 动作。
- 报告、材料产物、submission bundle、app log 都可下载。
- 上传、纠偏、下载都有结构化日志。
- 默认配置仍保持 `mock`，不改变当前 MVP 的本地安全行为。
- 当配置切到非 mock provider 时，未经脱敏的 payload 会被显式拒绝。
- 全量回归和真实样本验证通过。
