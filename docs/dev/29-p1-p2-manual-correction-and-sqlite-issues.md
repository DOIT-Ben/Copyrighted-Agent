# P1-P2 问题与处理

## Issue 1

- 现象：人工纠错如果只改内存，不改 report 和 review，页面会出现“改了材料，但结论没刷新”的错觉。
- 根因：纠错动作与 case 级 review/report 重建没有自动串联。

## Fix 1

- 为纠错动作统一补上：
  - case rebuild
  - review rerun
  - report rewrite

## Issue 2

- 现象：如果 correction 没有审计记录，后续很难追溯“是谁把什么改掉了”。
- 根因：原有模型只有最终状态，没有操作历史。

## Fix 2

- 引入 `Correction` 作为独立记录
- 在 submission 上挂 `correction_ids`
- 页面中增加 `Correction Audit` 面板

## Issue 3

- 现象：在并行执行两个 pytest 进程且都访问同一个 SQLite 文件时，会出现 Windows 文件占用问题。
- 根因：两个测试进程同时操作同一个 `data/runtime/soft_review.db`

## Fix 3

- 对 SQLite 相关回归改为串行执行
- 在持久化测试前后显式清理数据库文件
- 经验：带共享文件状态的测试不要并行跑

## 当前残留风险

- 纠错入口目前主要在 API，浏览器端还缺少完整操作控件
- SQLite 现阶段是 JSON-blob 方案，便于快速恢复，但后续仍建议细化 schema
