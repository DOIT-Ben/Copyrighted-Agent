# 运维页信号层级优化构建日志

## 日期

- 2026-04-21

## 背景

- `ops` 页已经具备完整信息，但几个核心区域仍然偏“表驱动”：
  - 发布闸门
  - 模型通道就绪度
  - 启动自检
- 使用者需要先阅读整张表，才能定位当前最重要的阻塞项或告警项。

## 本轮目标

- 在不改变运维数据来源和接口契约的前提下，把关键风险前置。
- 让 `ops` 页从“表集合”进一步变成“摘要先行 + 明细托底”的运维工作台。

## 实施内容

- 在 `app/web/page_ops.py` 中新增：
  - `_status_bucket_counts()`
  - `_status_rank()`
  - `_ops_focus_cards()`
  - `_ops_check_snapshot()`
- 基于上述方法，为以下区域增加摘要层：
  - 发布闸门详情
  - 模型通道就绪度
  - 启动自检明细
- 每个区域现在包含三层：
  - 重点摘要说明
  - 检查项数量/正常/告警/阻塞汇总
  - 最高优先级的重点项卡片
  - 完整明细表保留在下方
- 在 `app/web/static/styles.css` 中新增：
  - `ops-detail-stack`
  - `ops-detail-callout`
  - `ops-detail-summary`
  - `ops-focus-grid`
  - `ops-focus-card`

## 效果

- 进入 `ops` 页后，不需要先扫完整张表。
- 当前阻塞点、重点告警、优先修复项会先被抬到上层。
- 明细表仍完整保留，便于后续追根溯源。

## 涉及文件

- `app/web/page_ops.py`
- `app/web/static/styles.css`

