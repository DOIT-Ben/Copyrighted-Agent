# P3-P4 验证报告

## 日期

- 2026-04-19

## 自动化回归

- 命令：`py -m pytest`
- 结果：`67 passed, 0 failed`

## 关键回归点

- `tests/integration/test_operator_console_and_exports.py`
  - 验证 HTML operator actions
  - 验证报告下载
  - 验证材料产物下载
  - 验证 submission bundle 下载
  - 验证 app log 下载
- `tests/unit/test_app_config_contracts.py`
  - 验证安全默认配置
  - 验证环境变量覆盖
- `tests/unit/test_ai_provider_boundary_contracts.py`
  - 验证 provider enable switch
  - 验证非 mock provider 拒绝原始 payload
  - 验证非 mock provider 接受脱敏 payload

## 真实样本验证

- 命令：`py -m app.tools.input_runner --path input\软著材料 --mode single_case_package`
- 结果：
  - `2501 / 2504 / 2505 / 2508 / 2510` 均完成 4 类材料识别
  - `2502` 仍有 `1` 个 `unknown`
  - 模式 A 当前 unknown 总数仍为 `1`
  - 各包都产生 redaction 统计，说明脱敏链路仍在生效
- 命令：`py -m app.tools.input_runner --path input\合作协议 --mode batch_same_material`
- 结果：
  - `11` 份材料全部识别为 `agreement`
  - 生成 `2` 个 case 和 `1` 个 batch report

## 非 mock 边界烟测

- 命令：`$env:SOFT_REVIEW_AI_ENABLED='true'; $env:SOFT_REVIEW_AI_PROVIDER='safe_stub'; py -m app.tools.input_runner --path input\软著材料\2501_软著材料.zip --mode single_case_package`
- 结果：
  - 导入成功
  - case review 成功完成
  - 说明真实管线在非 mock 配置下仍能通过脱敏边界正常运行

## 结论

- 浏览器操作台、导出、日志与 AI 边界增强均已通过自动化回归。
- 默认本地安全行为没有被破坏。
- 当前最值得继续推进的风险点，仍然是老 `.doc` 样本的解析质量与人工复核占比。
