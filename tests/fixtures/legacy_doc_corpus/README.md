# Legacy `.doc` Minimal Corpus

这个目录保存最小真实回归语料，只覆盖当前最关键的三类 legacy `.doc` 状态：

- `usable_text/`
  - 来自真实合作协议样本
  - 目标：验证 OLE `.doc` 里可提取出可用文本时，系统不会错误降级
- `partial_fragments/`
  - 来自真实信息采集表样本
  - 目标：验证“能读到不少字段，但控制字符 / OLE 碎片仍较重”的半可读状态
- `binary_noise/`
  - 来自真实源代码样本
  - 目标：验证高噪音 legacy `.doc` 仍会被拦在低质量门外

这些文件都来自当前仓库本地真实样本，后续如要替换，优先保证：

1. 每个分组至少保留 1 个真实样本
2. 分组含义保持稳定：`usable_text / partial_fragments / binary_noise`
3. 替换后同步更新 `tests/integration/test_legacy_doc_corpus_regression.py`
