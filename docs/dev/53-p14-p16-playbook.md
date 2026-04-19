# P14-P16 经验手册

## 1. 联调入口不要直接连真实 provider

- 在接真实 provider 前，先跑本地 sandbox。
- 先验证：
  - 请求字段
  - desensitized 边界
  - fallback 行为
  - Authorization 头

## 2. 备份能力要先于自动清理成熟

- 只有 cleanup，没有 backup/restore，不算完整运维方案。
- 更稳的顺序是：
  - 先 backup
  - 再 cleanup
  - 最后才考虑自动 apply

## 3. restore 默认必须保守

- restore 最安全的默认动作不是“直接恢复”，而是“先给出计划”。
- 尤其在真实 runtime 已经积累大量文件时，dry-run 能明显降低误操作风险。

## 4. 大归档 CLI 输出要默认做摘要

- 大量路径清单在 Windows 终端里不但会刷屏，还容易触发编码问题。
- 对这类命令，默认摘要 + 预览前几条，比完整打印更可用。

## 5. 趋势基线一定要结构化

- 写进验证文档的数字，适合汇报。
- 写进 JSON 快照的数字，适合后续程序化比较。
- 两者都要保留，缺一不可。
