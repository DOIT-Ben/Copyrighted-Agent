# 206 敏感词规则落地日志

## 本轮目标

- 把共享敏感词扫描能力补到信息采集表规则执行中。
- 让规则簿、业务分级、报告页映射保持一致。
- 增加最小回归，确保这轮规则真正可执行。

## 实施内容

- 在 `app/core/reviewers/rules/info_form.py` 中补充：
  - `info_sensitive_terms` 规则执行
  - `missing_fields_listed` 明细输出
- 在 `app/core/services/review_rulebook.py` 的 `identity` 维度下补充 `info_sensitive_terms` 默认规则项。
- 在 `app/core/services/business_review.py` 中把敏感词类问题和协议错别字问题纳入“弱智问题”显式策略。
- 在 `app/web/page_report.py` 中补充：
  - `info_sensitive_terms` 到 `identity` 维度映射
  - `missing_fields_listed` / `info_sensitive_terms` 的友好化摘要
- 在 `tests/unit/test_rule_review_contracts.py` 中新增信息采集表敏感词与缺失字段测试。

## 预期收益

- 用户在信息采集表阶段就能看到敏感词问题，而不是只在协议/说明文档/源码阶段命中。
- 结果页的“发现了什么不足”会更接近业务语言，而不是只显示底层规则名。
- 规则编辑、规则执行、报告展示三层现在对 `info_sensitive_terms` 是打通的。

## 回归计划

- `py -m py_compile app\\core\\reviewers\\rules\\sensitive_terms.py app\\core\\reviewers\\rules\\info_form.py app\\core\\services\\review_rulebook.py app\\core\\services\\business_review.py app\\web\\page_report.py app\\core\\reports\\renderers.py`
- `py -m pytest tests\\unit\\test_rule_review_contracts.py -q`
- `py -m pytest tests\\integration\\test_web_mvp_contracts.py -q`
