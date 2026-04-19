# P10-P13 验证记录

## 日期

- 2026-04-19

## 自动化回归

- 命令：`py -m pytest`
- 结果：`90 passed, 0 failed`

## Runtime Cleanup Dry Run

- 命令：`py -m app.tools.runtime_cleanup`
- 结果：
  - `candidate_count=0`
  - `skipped_count=0`
  - `sqlite_action=skip_manual_backup`
  - `sqlite_reason=sqlite_requires_manual_backup`
- 结论：
  - 当前运行时目录没有超过保留期的自动清理候选。
  - SQLite 进入人工备份策略，符合“默认不删库”的安全要求。

## 模式 A 真实样本

- 命令：`py -m app.tools.input_runner --path input\软著材料 --mode single_case_package`
- 聚合结果：
  - `packages=6`
  - `materials=24`
  - `cases=6`
  - `reports=6`
  - `unknown=0`
  - `needs_review=10`
  - `low_quality=10`
  - `redactions=239`
  - `review_reasons={'noise_too_high': 10, 'ole_readable_segments_insufficient': 1, 'clean_text_ready': 13}`
  - `legacy_doc_buckets={'binary_noise': 6, 'partial_fragments': 4, 'usable_text': 8}`
- 结论：
  - `unknown` 继续维持 `0`
  - P10 的细分标签已经能反映低质 `.doc` 的真实分布

## 模式 B 真实样本

- 命令：`py -m app.tools.input_runner --path input\合作协议 --mode batch_same_material`
- 结果：
  - `materials=11`
  - `cases=10`
  - `reports=1`
  - `types={'agreement': 11}`
  - `needs_review=2`
  - `low_quality=2`
  - `redactions=149`
  - `review_reasons={'ole_readable_segments_insufficient': 2, 'clean_text_ready': 8, 'noise_too_high': 1}`
  - `legacy_doc_buckets={'partial_fragments': 2, 'usable_text': 7}`

## 页面与运维入口

- `/ops` 页验证点：
  - `Startup Self Check`
  - `/downloads/logs/app`
  - `py -m app.tools.runtime_cleanup`
- 浏览器级 E2E 已覆盖：
  - 上传
  - HTML 更正
  - rerun review
  - report
  - logs
  - `/ops`
  - Mode B regroup

## 总结

- P10-P13 全部落地并通过验证。
- 系统当前的下一步重点不再是“把 unknown 降下来”，而是：
  - 继续压缩 `needs_review / low_quality`
  - 接真实 provider 的端到端联调
  - 让运维清理从“可观察”进一步走向“可执行 SOP”
