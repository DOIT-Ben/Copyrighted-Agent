# 业务收尾完善 TODO
## 日期

- 2026-04-21

## 目标

- 把真实 provider 验证、真实样本基线、运行时备份、交付清单汇总成统一业务收尾结论。
- 让业务、运维、操作员不再分别查多个命令和多个产物才能判断是否可交付。
- 在 `docs/dev` 内沉淀 latest + history closeout 产物，便于后续追溯。

## 颗粒化 TODO

1. 盘点现有技术闭环，确认可复用 `release_validation`、`release_gate`、基线、备份能力。
2. 定义业务收尾最小输入集合。
3. 设计业务收尾状态模型：`pass / warning / blocked`。
4. 设计业务里程碑模型：`ready_for_business_handoff / ready_for_operator_trial / blocked`。
5. 新增 `delivery_closeout` 服务，加载最新真实验证产物。
6. 在业务收尾里接入发布闸门评估。
7. 在业务收尾里接入最新真实样本基线状态。
8. 在业务收尾里接入最新运行时备份状态。
9. 在业务收尾里接入验收 checklist 状态。
10. 汇总业务侧下一步动作列表，按阻塞优先级输出。
11. 增加 latest + history JSON / Markdown 产物写入能力。
12. 新增 `app.tools.delivery_closeout` CLI。
13. 把新命令挂到 `/ops` 运维命令区。
14. 增加业务收尾单测。
15. 增加业务收尾集成测试。
16. 更新运维页契约测试。
17. 实际运行一次 closeout，生成真实收尾产物。
18. 记录开发日志、问题和验证结果到 `docs/dev`。

## 执行顺序

1. 先做服务层和状态模型。
2. 再做 CLI 和运维入口。
3. 然后补测试。
4. 再实际生成 closeout 产物。
5. 最后补文档、回归、提交 git。

## 当前状态

- 1 到 17：已完成
- 18：进行中
