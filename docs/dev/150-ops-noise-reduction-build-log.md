# 150 Ops Noise Reduction Build Log

- Date: 2026-04-21
- Scope: `ops` 页面信息层级压缩、命令工作台重组、探针概览可用性提升

## Goals

- 删除顶部重复表达同一状态的冗余层，避免 KPI、状态卡、摘要块、表格四层重复。
- 让命令区先给出环境上下文，再给操作入口，减少“先点命令后找状态”的跳跃。
- 让探针概览展示可执行信息，尤其是“最近失败原因”，不再回退为文件名。

## Changes

- 在 `app/web/page_ops.py` 中新增顶部优先级横幅与 `signal-ribbon` 总览层。
- 保留 KPI 层，但把原 `ops-status-card` 顶部卡组压缩为一条风险横幅加四张紧凑信号卡。
- 将发布闸门常见英文缺口文案本地化：
  - `Complete the missing requirements: API key env.`
  - `external_http is partially configured: API key env.`
  - `Live external_http probe skipped because provider=mock.`
- 将命令区改为 `ops-workbench`：
  - 顶部先给“当前 provider / 阶段 / endpoint / model / 脱敏边界 / 探针 JSON / 日志”上下文
  - 下方再给启动、验证、维护三组命令
- 将探针概览改为：
  - 最新探针
  - HTTP
  - 最近成功
  - 请求审计
  - 最近失败说明
  - 批次 / 项目 / 材料计数
- 在 `app/web/static/styles.css` 中补充：
  - `signal-ribbon`
  - `ops-workbench`
  - `ops-context-grid`
  - `probe-observatory`
  - 对上述新块的移动端单列回落规则

## Notes

- `/static/styles.css` 可以直接反映最新文件内容，但 8000 端口上的既有受管进程会继续持有旧版 Python 模块。
- 为验证最新 `ops` HTML，额外在 `http://127.0.0.1:18080/ops` 启动了当前仓库代码实例。
