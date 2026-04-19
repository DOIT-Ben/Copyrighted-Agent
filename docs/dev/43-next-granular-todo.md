# 下一阶段细颗粒 Todo

## 日期

- 2026-04-19

## Completion Update 2026-04-19 Round 3

### Completed

- [x] Added provider readiness service and CLI probe
- [x] Added latest backup and latest baseline discovery helpers
- [x] Upgraded `/ops` into a status-first admin panel
- [x] Reduced real sample mode A `needs_review / low_quality` to `0 / 0`
- [x] Reduced real sample mode B `needs_review / low_quality` to `0 / 0`
- [x] Generated final baseline comparison artifacts and release closeout docs

### Recommended Next Slice

- [ ] Configure a real external provider endpoint and credential for live non-sandbox smoke
- [ ] Decide recurring baseline cadence and ownership
- [ ] Review backup retention thresholds against real runtime growth

## Completion Update 2026-04-19

### Completed

- [x] 建立 legacy `.doc` 最小真实回归语料目录
- [x] 细化 `low_quality` 原因标签并沉淀聚合指标
- [x] 增加浏览器级 E2E，覆盖上传、Submission、人工纠偏、报告、日志、`/ops`
- [x] 收敛 `external_http` request/response 契约与错误分类
- [x] 增加 provider fallback 上下文测试与 readiness 自检
- [x] 增加 `data/runtime` 清理脚本、runbook 与 `/ops` 命令入口
- [x] 明确 submissions / uploads / logs / sqlite 的保留与备份策略
- [x] 补充常见问题与经验手册

### Recommended Next Slice

- [ ] 准备真实 provider 联调沙箱与验收 checklist
- [ ] 为 runtime cleanup 补备份与恢复 SOP
- [ ] 针对 `needs_review / low_quality` 建立趋势基线

## Completion Update 2026-04-19 Round 2

### Completed

- [x] 增加真实 provider 联调沙箱与对应集成测试
- [x] 增加 runtime backup / inspect / restore 预演工具
- [x] 增加真实样本趋势基线工具与首个 baseline 产物
- [x] 把 backup / sandbox / baseline 命令加入 `/ops`

### Recommended Next Slice

- [ ] 为真实 provider 配置模板补联调 checklist 与示例环境变量
- [ ] 评估 runtime 备份归档体积控制策略
- [ ] 用 baseline JSON 做下一轮趋势对比

## P10 解析语料与质量压缩

- [ ] 为 legacy `.doc` 建立最小真实回归语料目录，按“可用文本 / 半可读碎片 / 纯噪音”分组。
- [ ] 为 `low_quality` 材料增加更细的原因标签，区分“文本太短 / 噪音过多 / OLE 可读段不足”。
- [ ] 把模式 A 和模式 B 的 `needs_review / low_quality / unknown` 聚合结果沉淀成固定模板文档。

## P11 浏览器级 E2E

- [ ] 增加浏览器级 E2E，覆盖上传、进入 Submission、人工纠偏、查看报告、下载日志。
- [ ] 增加 `/ops` 页面主链路校验。
- [ ] 增加模式 B 浏览器上传后的 Case regroup 场景验证。

## P12 真实 Provider 正式接入

- [ ] 为 `external_http` adapter 设计最小请求 / 响应契约。
- [ ] 增加“provider 不可用但 fallback 成功”的页面提示或日志提示。
- [ ] 设计 provider 结果的字段映射与异常分类。
- [ ] 为真实 provider 接入准备单独的脱敏验收 checklist。

## P13 运维清理与留存

- [ ] 增加 `data/runtime` 清理脚本或手工 runbook。
- [ ] 明确 submissions / uploads / logs / sqlite 的保留与备份策略。
- [ ] 为常见问题补支持手册：
  - 上传失败
  - 下载失败
  - SQLite 恢复失败
  - provider 连接失败
