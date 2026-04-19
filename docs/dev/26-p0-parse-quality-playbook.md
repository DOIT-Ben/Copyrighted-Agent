# P0 经验手册

## 适用场景

- ZIP 导入后大量中文文件名变成乱码
- `.doc` 被错误识别成 `source_code` 或其他类型
- Submission 看起来能跑通，但 `unknown` 很多，且原因不可解释

## 处理顺序

1. 先检查 ZIP 文件名是否被错误解码。
2. 修复文件名后，再看 unknown 是否已经明显下降。
3. 不要直接相信二进制 `.doc` 解析出来的文本。
4. 先做 parse quality，再决定能不能继续自动分类。
5. 对 low quality 文本，要优先进入 `needs review`，而不是强行自动判断。

## 判断原则

- 文件名可靠、文本质量低：
  - 可以保留分类
  - 但必须标记 `needs_manual_review`
- 文件名不可靠、文本质量低：
  - 应优先保持 `unknown`
  - 同时给出 `unknown_reason`
- 文件名不可靠、文本质量高：
  - 允许第二轮内容分类

## 本轮最关键的经验

- 真实世界里，很多问题不是分类器太弱，而是输入名字先坏了。
- 解析器没有“质量”概念时，系统会把噪声当信号。
- 先把失败解释清楚，再追求更高自动化，开发效率会更高。

## 对下一阶段的建议

- P1 人工纠错要直接复用本轮产出的：
  - `triage.needs_manual_review`
  - `triage.unknown_reason`
  - `parse_quality.quality_level`
  - `classification.first_pass_result`
  - `classification.second_pass_result`
- P2 SQLite 时，这些字段要原样入库，不能只保留最终分类结果。
