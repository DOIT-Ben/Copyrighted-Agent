# Delivery Hardening Todo

## Date

- 2026-04-20

## Goal

- 把当前项目从“已可运行的 MVP”进一步收口到“更容易启动、验证、复用和交付”的状态。
- 不再扩张新功能边界，优先消除运行摩擦、交付摩擦和追溯摩擦。

## Execution Order

### Phase 1. Todo And Scope Freeze

- [x] 复核当前项目状态、真实 provider 状态、前端状态、docs/dev 状态
- [x] 确认本轮目标聚焦在交付加固，而不是新增业务功能
- [x] 产出本轮细粒度 todo，并锁定执行顺序

### Phase 2. Launch And Validation Tooling

- [ ] 新增本地启动脚本目录 `scripts/`
- [ ] 新增 `scripts/start_mock_web.ps1`
- [ ] 新增 `scripts/start_real_bridge.ps1`
- [ ] 新增 `scripts/start_real_web.ps1`
- [ ] 新增 `scripts/run_real_validation.ps1`
- [ ] 新增 `scripts/show_stack_status.ps1`
- [ ] 用实际命令验证脚本至少能正确输出 / 启动 / 指向当前仓库根目录

### Phase 3. Product Surface Alignment

- [ ] 更新 `/ops` 页面命令区，加入脚本入口
- [ ] 在 `/ops` 页面中补充真实 bridge / real web / validation 的可复制命令
- [ ] 检查 `/ops` 页面是否仍保留既有契约字符串
- [ ] 视需要对 `page_submission.py` 做最小维护性整理，避免后续再出现大型页面难维护问题

### Phase 4. Documentation Alignment

- [ ] 更新 `README.md`
- [ ] 更新 `docs/dev/09-runbook.md`
- [ ] 让 README / runbook / `/ops` 页面三处命令保持一致
- [ ] 明确 mock 模式与 real 模式的区别
- [ ] 明确 bridge、web、validation 的推荐执行顺序

### Phase 5. Real Validation And Regression

- [ ] 复核 `config/local.json` 与 `config/local.minimax_bridge.example.json`
- [ ] 复核 18011 bridge 端口状态
- [ ] 运行一次真实 provider 验证
- [ ] 启动并验证 Web 页面可访问
- [ ] 运行全量自动化回归
- [ ] 如发现回归问题，直接修复并重新验证

### Phase 6. Delivery Closure

- [ ] 写入本轮 build log
- [ ] 写入本轮 validation log
- [ ] 写入本轮 issues / fixes
- [ ] 新增 `.gitignore`
- [ ] 初始化 git 仓库
- [ ] 执行一次提交，保留本轮交付快照

## Acceptance Criteria

- 有一套明确的 mock / real / validation 启动命令，不再需要手工拼接
- `/ops` 页面、README、runbook 三处信息一致
- 真实 provider 验证可复现
- 全量自动化回归通过
- `docs/dev` 留下完整过程记录
- git 交付快照可用，且不会误纳入本地敏感输入与运行时垃圾
