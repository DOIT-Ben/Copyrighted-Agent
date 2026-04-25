# 结构化审查规则改造日志

日期：2026-04-25

## 本次目标

将原本按维度维护的一段式审查规则，升级为：

- 维度下带有细分规则项
- 规则项可按当前批次单独编辑
- 导入前即可修改
- 修改结果进入当前批次配置与 LLM prompt 快照

## 规则模型调整

涉及文件：

- `app/core/services/review_rulebook.py`
- `app/core/services/review_profile.py`
- `app/core/reviewers/ai/prompt_builder.py`

本次为每个维度增加了 `rules` 结构，规则项包含：

- `key`
- `title`
- `category`
- `severity`
- `prompt_hint`
- `enabled`

并按照软著业务场景完成第一版分类拆解，覆盖：

- 基础信息完整性
- 材料完整性
- 跨材料一致性
- 源码可审查性
- 说明文档规范
- 协议与权属规范
- AI 补充研判

细分规则中已纳入：

- 软件全称一致性
- 版本号一致性
- 开发完成日期一致性
- 申请人排序一致性
- 协议代称体系
- 源码脱敏
- 文档必备章节
- 页眉页脚
- 敏感信息
- 退回级 / 弱智问题 / 警告项等输出结构要求

## 前端改造

涉及文件：

- `app/web/review_profile_widgets.py`
- `app/web/page_review_rule.py`
- `app/web/static/styles.css`

本次前端支持：

- 导入页按维度展开细分规则
- 每条规则可单独启用/停用
- 可编辑规则名、严重级别、检查说明
- 保留维度级的目标、检查点摘要、LLM 关注点
- 规则详情页支持完整编辑与保存后重跑

## 流转链路

涉及文件：

- `app/api/main.py`
- `app/core/services/corrections.py`

本次已确保：

- 导入页提交的细分规则可保存到 `review_profile.dimension_rulebook`
- 批次规则详情页修改后可保存
- 保存结果可进入重跑审查链路
- `prompt_snapshot.active_dimensions` 会带上结构化规则项

## 验证

执行：

```text
py -m py_compile app\core\services\review_rulebook.py app\core\services\review_profile.py app\core\reviewers\ai\prompt_builder.py app\web\review_profile_widgets.py app\web\page_review_rule.py app\api\main.py app\core\services\corrections.py
py -m pytest tests\integration\test_web_mvp_contracts.py -q
```

结果：

- `7 passed`

## 后续建议

当前这次完成的是“结构化规则配置层”，还没有把所有细分规则都落成独立的硬编码执行器。

下一步可以继续做两件事：

1. 将高优先级子规则落成真正的规则执行器
   - 如排序一致性
   - 文档必备章节
   - 敏感词全量排查
   - 源码格式规范

2. 报告页按细分规则命中结果直接展示
   - 哪条规则命中
   - 命中证据
   - 归属退回级 / 弱智问题 / 警告项
