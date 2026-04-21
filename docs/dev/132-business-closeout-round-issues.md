# 业务收尾完善问题记录
## 日期

- 2026-04-21

## 发现的问题

### 1. 技术闭环已经具备，但业务结论仍然分散

- 现象：
  - `release_validation`、`release_gate`、基线、备份、checklist 都存在，但没有统一收口。
- 风险：
  - 业务和运维需要人工拼装结论，容易漏掉阻塞项。
- 处理：
  - 新增 `delivery_closeout` 聚合服务和统一状态模型。

### 2. “真实验证通过”不等于“当前可交付”

- 现象：
  - 现有 `real-provider-validation-latest.json` 可以是 pass，但当前环境依然可能因为配置不完整被 `release_gate` 阻塞。
- 风险：
  - 容易把历史通过误当成当前环境可交付。
- 处理：
  - 业务收尾同时读取 latest validation 和当前 release gate。
  - 两者分开展示，防止误判。

### 3. 业务收尾需要给动作，不只是给状态

- 现象：
  - 单纯输出 pass/warning/blocked 还不够，业务侧仍要追问下一步做什么。
- 风险：
  - 状态知道了，但闭环仍然停在人工沟通。
- 处理：
  - `delivery_closeout` 汇总阻塞项和 warning 的推荐动作，输出 `operator_actions`。

### 4. 测试阶段发现配置对象不可变

- 现象：
  - 集成测试初版里试图直接修改 `AppConfig.ai_endpoint`，触发 `FrozenInstanceError`。
- 风险：
  - 测试会误以为业务收尾逻辑有问题，实际是配置对象使用方式错误。
- 处理：
  - 改成拿到 sandbox endpoint 后一次性构造 `AppConfig`。

## 当前残余风险

- 当前真实 closeout 仍是 `blocked`，不是代码缺陷，而是运行环境缺少 `API key env`。
- 业务收尾服务目前聚焦“当前是否可交付”，还没有纳入真实操作员签字或人工试跑反馈记录。
- 如果后续需要正式发布审计，还可以继续扩展：
  - 人工试跑记录
  - 责任人签收
  - 版本号与发布时间戳
