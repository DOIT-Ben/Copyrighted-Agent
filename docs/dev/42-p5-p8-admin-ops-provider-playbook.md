# P5-P8 复用手册

## 1. 当真实样本还没完全稳定时，先把“错误看清楚”

- 不要一开始就只追 `unknown` 数量。
- 先拆出：
  - `unknown`
  - `needs_review`
  - `low_quality`
  - `redactions`
- 命令行工具最好直接输出聚合摘要，这样每一轮回归都能快速比较趋势。

## 2. 管理台页面不要只展示结果，要显式告诉用户“下一步该做什么”

- 模式 B 最容易让人误解。
- 对批量归档型工作流，页面必须明确表达：
  - 当前阶段的目标是什么
  - 为什么会出现散落 Case
  - 人工纠偏入口在哪里

## 3. provider 真正接入前，先把接口边界和失败策略做成独立层

- `safe_stub` 只能证明“安全边界设计没错”。
- 真要进入真实 provider 阶段，还要提前准备：
  - adapter 层
  - timeout
  - fallback
  - started / completed / failed 日志
- 而且任何非 mock provider，都必须先过脱敏校验。

## 4. 运维页不是锦上添花，而是排障速度放大器

- 当系统开始有：
  - SQLite
  - runtime 文件夹
  - 日志
  - 下载
  - provider 配置
- 就应该有一个集中页面统一展示它们。
- 否则每次排查都要在文档、终端和代码之间来回切。

## 5. 报告里要把“规则确定结论”和“AI 补充说明”分开

- 规则结果和 AI 说明混在一起时，用户会误判风险来源。
- 一旦后面接真实 provider，审计要求会更高。
- 最稳妥的做法是：
  - `rule_conclusion`
  - `ai_summary`
  - `ai_provider`
  - `ai_resolution`
  分别保留。

## 6. 推荐的交付节奏

1. 先做小批量代码改动。
2. 立刻跑自动化回归。
3. 再跑真实样本烟测。
4. 最后把计划、构建、问题、验证、手册落到 `docs/dev`。

## 7. 下一次复用时，优先沿用的最小模板

- `AppConfig`
- `run_startup_self_check`
- `Provider Adapter Skeleton`
- `Support / Ops` 页面
- `input_runner` 聚合摘要
- `docs/dev` 五件套：
  - plan
  - build-log
  - issues
  - validation
  - playbook
