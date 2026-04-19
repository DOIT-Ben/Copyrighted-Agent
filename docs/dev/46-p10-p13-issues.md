# P10-P13 问题与修复

## Issue 1

- 现象：指定某个测试文件执行时，自定义 pytest runner 仍会跑全量。
- 影响：所谓“局部回归”实际上会把历史问题一并带出来。
- 修复：
  - 本轮把新增测试都按“全量执行也必须稳定”来写。
  - 避免使用 `pytest.raises(match=...)`、`exc_info.value` 等这个轻量 runner 不兼容的能力。

## Issue 2

- 现象：Windows 下 `clear_database()` 直接删 `soft_review.db` 会偶发 `WinError 32`。
- 影响：持久化测试在本地运行中的真实服务存在时不稳定。
- 修复：
  - 保留“先删文件”的快路径。
  - 若文件被占用，则回退到表级 `DELETE` 清空。
- 结果：全量回归恢复稳定。

## Issue 3

- 现象：`external_http` skeleton 缺少清晰的 request/response 版本和错误分类。
- 影响：后续接真实 provider 时难以判断是调用失败、响应格式错误还是业务缺字段。
- 修复：
  - 固化请求/响应版本号。
  - 固化缺 `summary`、HTTP 错误、请求失败、无效 JSON 的错误码。
  - 在 service 层对外部异常做归一化记录。

## Issue 4

- 现象：runtime cleanup 如果没有强约束，很容易误删调查中的文件。
- 影响：运维脚本本身会成为新的风险源。
- 修复：
  - 默认 dry-run。
  - 只允许扫描 `submissions / uploads / logs`。
  - active log 明确跳过。
  - SQLite 改为人工备份策略，不允许脚本自动删除。
  - apply 前做 allowed roots 校验。

## Issue 5

- 现象：legacy `.doc` 即便都落在 `low_quality`，也不利于后续运营复盘。
- 影响：无法区分“还有救的碎片”与“基本纯噪声”。
- 修复：
  - 引入 `legacy_doc_bucket` 与 `review_reason_code`。
  - 让报告、Submission 页面、`input_runner` 都能看到同一套分类。
