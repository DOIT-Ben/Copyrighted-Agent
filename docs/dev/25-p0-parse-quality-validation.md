# P0 验证报告

## 日期

- 2026-04-19

## 自动化回归

- 命令：`py -m pytest`
- 结果：`57 passed, 0 failed`

## 真实样本验证

### 模式 A

- 命令：
  - `D:\Soft\python310\python.exe -m app.tools.input_runner --path input\软著材料 --mode single_case_package`

### 模式 A 结果

- `2501_软著材料.zip`
  - `types={'info_form': 1, 'agreement': 1, 'source_code': 1, 'software_doc': 1}`
  - `needs_review=4`
  - `low_quality=4`
- `2502_软著材料.zip`
  - `types={'unknown': 1, 'software_doc': 1, 'source_code': 1, 'info_form': 1}`
  - `needs_review=4`
  - `low_quality=4`
- `2504_软著材料.zip`
  - `types={'info_form': 1, 'agreement': 1, 'source_code': 1, 'software_doc': 1}`
  - `needs_review=3`
  - `low_quality=3`
- `2505_软著材料.zip`
  - `types={'info_form': 1, 'agreement': 1, 'source_code': 1, 'software_doc': 1}`
  - `needs_review=2`
  - `low_quality=2`
- `2508_软著材料.zip`
  - `types={'info_form': 1, 'agreement': 1, 'source_code': 1, 'software_doc': 1}`
  - `needs_review=4`
  - `low_quality=4`
- `2510_软著材料.zip`
  - `types={'agreement': 1, 'software_doc': 1, 'source_code': 1, 'info_form': 1}`
  - `needs_review=2`
  - `low_quality=2`

### 模式 A 阶段结论

- 本轮真实样本总 unknown 数为 `1`
- 对比上一轮已知状态：
  - 上一轮 unknown 总数为 `5`
  - 本轮 unknown 总数为 `1`
  - 收敛结果：`5 -> 1`

## 模式 B

- 命令：
  - `D:\Soft\python310\python.exe -m app.tools.input_runner --path input\合作协议 --mode batch_same_material`

### 模式 B 结果

- `合作协议`
  - `materials=11`
  - `cases=2`
  - `types={'agreement': 11}`
  - `needs_review=10`
  - `low_quality=10`

## 解释

- `needs_review` 与 `low_quality` 偏高，不代表分类失败。
- 这说明当前大量 `.doc` 材料虽然能凭文件名正确归类，但文本解析质量仍不足，必须进入人工复核。
- 这正是下一阶段 P1 需要接手的工作对象。

## 验证结论

- P0 已达成“unknown 可解释、真实样本大幅收敛”的目标。
- 下阶段优先级应转向：
  - 人工纠错
  - case regroup
  - 持久化 correction 记录
