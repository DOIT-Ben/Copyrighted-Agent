# 结构化规则执行接入日志

日期：2026-04-25

## 本次目标

在“结构化规则配置层”基础上，继续推进到“结果可见层”，让报告页能够直接显示：

- 命中了哪条细分规则
- 为什么命中
- 命中的是哪份材料

同时把单材料规则命中并入项目报告，不再只显示跨材料一致性问题。

## 已完成内容

### 1. 规则命中字段补充

已为以下规则执行器补充 `rule_key`：

- `cross_material.py`
- `agreement.py`
- `document.py`
- `source_code.py`
- `info_form.py`

目前已开始接入的可执行规则包括：

- 软件全称一致性
- 版本号一致性
- 信息采集表软件名称缺失
- 信息采集表版本号缺失
- 信息采集表申请主体缺失
- 协议错别字
- 协议日期不一致
- 协议不规范代称
- 协议电子章/扫描件信号
- 文档必备章节缺失
- 文档术语不一致
- 文档版本号混用
- 文档页码信号缺失
- 文档内容过少
- 源码乱码
- 源码格式不规范
- 源码敏感信息未脱敏
- 源码关键逻辑展示不足
- 源码注释比例异常

### 2. 项目报告问题汇总增强

涉及文件：

- `app/core/pipelines/submission_pipeline.py`
- `app/core/services/corrections.py`

新增了项目级问题汇总逻辑：

- 原来仅纳入跨材料一致性问题
- 现在会把单材料问题也一起汇总到项目级 `issues_json`
- 并保留：
  - `material_id`
  - `material_name`
  - `material_type`

这样报告页就能告诉用户：

- 问题是什么
- 来自哪份材料
- 属于哪一类审查规则

### 3. 报告页命中细分规则展示

涉及文件：

- `app/web/page_report.py`

本次增强后，`发现了什么不足` 区域不再只展示大维度：

- 会优先显示命中的细分规则标题
- 会显示材料来源
- 会将细分规则命中和当前 prompt snapshot 中的规则项对应起来

同时补强了人话诊断映射，例如：

- 合作协议顺序和信息采集表顺序不一致
- 说明文档缺少必备章节
- 源码中仍有敏感信息未脱敏
- 源码格式不符合提交规范

## 当前状态说明

当前系统已经进入：

- 规则可分类配置
- 规则可按批次编辑
- 部分高优先级规则已有真实执行器
- 报告页可显示细分规则命中

但还没有做到：

- 所有细分规则都变成独立执行器
- 所有问题都严格映射到“退回级 / 弱智问题 / 警告项”
- 设计文档页数、截图裁剪、在线填报等复杂项的强规则化执行

## 验证

执行：

```text
py -m py_compile app\core\reviewers\rules\cross_material.py app\core\reviewers\rules\agreement.py app\core\reviewers\rules\document.py app\core\reviewers\rules\source_code.py app\core\reviewers\rules\info_form.py app\core\pipelines\submission_pipeline.py app\core\services\corrections.py app\web\page_report.py
py -m pytest tests\integration\test_web_mvp_contracts.py -q
```

结果：

- `7 passed`

## 下一步建议

建议继续按优先级补执行器：

1. 排序一致性
2. 开发完成日期一致性
3. 在线填报信息核验
4. 敏感词全量排查
5. 退回级 / 弱智问题 / 警告项的正式分级策略
