# P14-P16 验证记录

## 日期

- 2026-04-19

## 自动化回归

- 命令：`py -m pytest`
- 结果：`101 passed, 0 failed`

## Provider Sandbox

- 验证方式：集成测试 `tests/integration/test_provider_sandbox_flow.py`
- 结果：
  - safe payload 可走通 `external_http`
  - `http_error` 模式可回退到 `mock`

## Runtime Backup

### Create

- 命令：`py -m app.tools.runtime_backup create --output data\backups\runtime_backup_20260419_2219.zip`
- 结果：
  - 生成成功
  - `file_count=18011`
  - `size_bytes=424308251`

### Inspect

- 命令：`py -m app.tools.runtime_backup inspect --archive data\backups\runtime_backup_20260419_2219.zip`
- 结果：
  - `format_version=soft_review.runtime_backup.v1`
  - `entry_count=18011`
  - `sqlite_snapshot_mode=sqlite_backup_api`

### Restore Dry Run

- 命令：`py -m app.tools.runtime_backup restore --archive data\backups\runtime_backup_20260419_2219.zip --target data\restore_preview\runtime_backup_20260419_2219`
- 结果：
  - dry-run 成功
  - `entry_count=18011`
  - 未直接写入活跃 runtime

## Metrics Baseline

- 命令：`py -m app.tools.metrics_baseline --markdown-path docs\dev\54-real-sample-baseline.md --json-path docs\dev\55-real-sample-baseline.json`
- 结果：
  - Markdown 与 JSON 产物生成成功
  - 模式 A：
    - `materials=24`
    - `cases=6`
    - `reports=6`
    - `unknown=0`
    - `needs_review=10`
    - `low_quality=10`
    - `redactions=239`
  - 模式 B：
    - `materials=11`
    - `cases=10`
    - `reports=1`
    - `unknown=0`
    - `needs_review=2`
    - `low_quality=2`
    - `redactions=149`

## 结论

- P14-P16 已完成。
- 现在项目已经具备：
  - provider 本地联调沙箱
  - runtime 备份/恢复预演能力
  - 真实样本趋势基线能力
