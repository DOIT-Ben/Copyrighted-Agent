# P10-P13 经验手册

## 1. 解析质量不要只做一个 low_quality

- 真正可运营的不是“低质量”这个结论，而是“为什么低质量”。
- 最小可用组合建议固定为：
  - `review_reason_code`
  - `review_reason_label`
  - `legacy_doc_bucket`
  - `legacy_doc_bucket_label`

## 2. 真实样本语料要最小但真实

- 不要只靠合成样本判断 `.doc` 质量。
- 从真实目录中抽出最小 corpus，按预期结果分桶，比堆一大堆样本更容易长期维护。

## 3. 页面主链路要用真实 HTTP 跑

- 当目标是“像管理系统一样的分析后台”时，只测 API 不够。
- 浏览器级 E2E 至少要覆盖：
  - 上传
  - 页面跳转
  - 表单动作
  - 下载
  - `/ops`

## 4. 接真实 provider 前，先锁契约

- 先固化 request/response 版本与字段，再谈模型接入。
- 这样后面无论接内网网关、第三方代理还是真正的大模型服务，边界都更稳。

## 5. 清理工具必须默认保守

- 默认 dry-run。
- 默认不删 active log。
- 默认不删 SQLite。
- apply 前必须校验 candidate path 只能落在允许根目录内。

## 6. Windows 下删库不是唯一清理方案

- 对 SQLite，`unlink()` 在 Windows 上不稳定并不代表“没法清理”。
- 更稳的策略是：
  - 优先删文件
  - 删除失败时回退到表级清空

## 7. 自定义测试环境要用最低兼容写法

- 如果项目不是标准 pytest，就不要默认使用高级 fixture/断言语法。
- 最稳妥的写法依然是：
  - 显式 `try/except`
  - 显式断言字符串
  - 少依赖 runner 特性
