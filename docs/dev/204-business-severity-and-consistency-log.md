# 业务分级与一致性规则补强日志

日期：2026-04-25

## 本次目标

继续把结构化规则从“可配置”推进到“业务可读”：

- 新增开发完成日期一致性和申请人排序一致性的基础执行能力
- 报告页直接输出 `退回级问题 / 弱智问题 / 警告项`
- 保留细分规则命中、材料来源和证据链

## 已完成内容

### 1. 文本提取能力增强

涉及文件：

- `app/core/utils/text.py`

新增：

- `extract_date_candidates`
- `extract_party_sequence`

用于从信息采集表、合作协议等文本中提取：

- 日期候选值
- 主体顺序信号

### 2. 审查规则执行补强

涉及文件：

- `app/core/reviewers/rules/info_form.py`
- `app/core/reviewers/rules/agreement.py`
- `app/core/reviewers/rules/cross_material.py`

新增或增强：

- 信息采集表提取日期与主体顺序
- 合作协议提取日期与主体顺序
- 跨材料比对：
  - `completion_date_match`
  - `party_order_match`

目前这两项仍是第一版启发式规则，但已经能够进入项目级问题结果。

### 3. 项目报告业务分级

涉及文件：

- `app/web/page_report.py`

新增：

- `问题级别归类`

按当前 severity 映射为：

- `severe -> 退回级问题`
- `moderate -> 弱智问题`
- `minor -> 警告项`

这让页面更贴近真实审查语境，而不是只显示技术 severity。

### 4. 项目结果页继续增强

报告页现已具备：

- 先改这些地方
- 问题级别归类
- 发现了什么不足
- 怎么判定出来的
- 用了哪些审查规则

其中“发现了什么不足”会继续展示：

- 命中细分规则
- 问题描述
- 材料来源
- 证据说明
- 建议动作

## 验证

执行：

```text
py -m py_compile app\core\utils\text.py app\core\reviewers\rules\info_form.py app\core\reviewers\rules\agreement.py app\core\reviewers\rules\cross_material.py app\core\pipelines\submission_pipeline.py app\core\services\corrections.py app\web\page_report.py
py -m pytest tests\integration\test_web_mvp_contracts.py -q
```

结果：

- `7 passed`

## 当前仍未完成的点

以下仍属于后续增强项：

- 在线系统填报的真实字段比对
- 申请人排序的强规则化解析
- 日期逻辑中“早于申请时间 8 个月”这类时序判断
- 鲜章/手签/截图裁剪等偏 OCR 或图像类校验
- 退回级 / 弱智问题 / 警告项的独立策略表，而不是当前 severity 映射
