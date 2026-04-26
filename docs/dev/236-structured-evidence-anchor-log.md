# 236 Structured Evidence Anchor Log

- 日期：2026-04-26
- 目标：把审查问题从“只描述问题”补强为“同时给出字段/章节/定位提示”，让结果页可以直接展示更稳定的回查位置。

## 本轮改动

- 在规则审查输出中新增结构化定位字段：
  - `field_label`
  - `section_label`
  - `anchor_hint`
  - `evidence_anchor`
- 覆盖的规则模块：
  - `info_form`
  - `document`
  - `source_code`
  - `agreement`
  - `online_filing`
  - `cross_material`
- 结果页更新为优先读取问题自身携带的定位字段，再回退到原有规则映射提示。

## 预期收益

- 报告里的“定位”信息更稳定，不再完全依赖 `rule_key -> 文案猜测`
- 同一条问题可以直接指向字段、章节或材料区域
- 后续如果解析层补充真实页码/区块锚点，可以直接塞进 `evidence_anchor` 继续扩展

## 回归计划

- `py -m py_compile` 检查规则模块与结果页
- `pytest` 运行单元、集成、E2E 合同回归
