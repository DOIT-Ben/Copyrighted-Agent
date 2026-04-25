# 正式业务分级策略落地日志

日期：2026-04-25

## 本次目标

将报告中的 `退回级问题 / 弱智问题 / 警告项` 从简单的 severity 映射，升级为基于规则键的正式业务策略。

## 已完成内容

### 1. 新增业务分级策略模块

涉及文件：

- `app/core/services/business_review.py`

新增：

- `business_level(issue)`
- `summarize_business_levels(issues)`

当前通过规则键维护第一版业务分级策略表：

- `RETURN_LEVEL_RULES`
- `NAIVE_LEVEL_RULES`

使以下问题可以稳定归为 `退回级问题`：

- 软件名称缺失
- 申请主体缺失
- 软件名称不一致
- 版本号不一致
- 开发完成日期不一致
- 排序不一致
- 源码不可读
- 源码未脱敏
- 说明文档缺少必备章节
- 协议日期逻辑问题
- 协议签章问题

### 2. 网页报告接入正式分级

涉及文件：

- `app/web/page_report.py`

本次调整后：

- `问题级别归类` 改为使用正式业务策略表
- 顶部概览中的三个计数改为：
  - 退回级问题
  - 弱智问题
  - 警告项
- “先改这些地方” 中的问题优先级颜色也同步使用业务策略

### 3. Markdown 报告同步接入

涉及文件：

- `app/core/reports/renderers.py`

本次调整后，Markdown 项目报告也新增：

- `问题级别归类`
  - 退回级问题
  - 弱智问题
  - 警告项

并且原始问题行会同时展示：

- 业务级别
- 原始 severity

便于网页和导出结果保持一致。

## 验证

执行：

```text
py -m py_compile app\core\services\business_review.py app\web\page_report.py app\core\reports\renderers.py
py -m pytest tests\integration\test_web_mvp_contracts.py -q
```

结果：

- `7 passed`

## 当前状态

现在系统已经具备：

- 结构化规则配置
- 细分规则编辑
- 部分高优先级规则执行
- 项目报告直接展示命中细分规则
- 项目报告直接展示业务级别分组
- Markdown 导出同步显示业务级别归类

## 后续建议

下一步建议继续补三块：

1. `在线填报信息` 真实字段比对
2. `敏感词全量排查` 的规则执行器
3. `退回级 / 弱智问题 / 警告项` 政策表页面化，可在前端配置
