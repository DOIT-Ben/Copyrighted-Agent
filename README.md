# 软著智能体

一个面向软著材料整理、脱敏、审查、分组、报告生成和运营排查的本地管理系统。

当前仓库已经不是单纯的 CLI 工具集合，而是一个可运行、可测试、可追溯的 Web MVP。它支持：

- ZIP 导入，两种模式：
  - 模式 A：同一个软著的完整材料包
  - 模式 B：不同软著的同类材料批量归档
- 本地脱敏与隐私清单输出
- 材料分类、文档解析、规则审查、AI 补充说明
- Submission / Case / Report / Ops 四类后台页面
- 导出报告、导出 submission bundle、导出脱敏产物
- provider probe、release gate、rolling baseline、runtime backup / cleanup

## 当前形态

- 后端：本地 FastAPI 风格接口
- 前端：服务端渲染的管理系统界面
- 运行态：`data/runtime/`
- 测试：内置 `pytest` 兼容层 + 单元 / 集成 / E2E 契约测试
- 文档：`docs/dev/`

## 快速启动

### 1. Mock 模式启动后台

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_mock_web.ps1
```

默认地址：

```text
http://127.0.0.1:8000
```

### 2. 真实模型桥接启动

先准备环境变量：

```powershell
$env:MINIMAX_API_KEY='你的真实密钥'
```

再启动 bridge：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_real_bridge.ps1
```

默认地址：

```text
http://127.0.0.1:18011/review
```

### 3. 真实模式启动后台

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_real_web.ps1 -Port 18080
```

默认地址：

```text
http://127.0.0.1:18080
```

### 4. 查看当前本地栈状态

```powershell
powershell -ExecutionPolicy Bypass -File scripts\show_stack_status.ps1
```

### 5. 执行真实链路验证

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_real_validation.ps1
```

验证产物会写入：

```text
docs/dev/real-provider-validation-latest.json
docs/dev/real-provider-validation-latest.md
docs/dev/history/
```

## 当前默认配置

本地运行配置读取：

- `config/local.json`
- `SOFT_REVIEW_*` 环境变量覆盖

MiniMax bridge 示例配置：

- `config/local.minimax_bridge.example.json`

Mock 安全默认配置示例：

- `config/local.example.json`

## 常用命令

运行全量回归：

```powershell
py -m pytest
```

直接启动 Web：

```powershell
py -m app.api.main
```

直接启动 bridge：

```powershell
py -m app.tools.minimax_bridge --port 18011 --upstream-base-url https://api.minimaxi.com/v1 --upstream-model MiniMax-M2.7-highspeed --upstream-api-key-env MINIMAX_API_KEY
```

## 关键页面

- `/`：Control Center / Import Console
- `/submissions`：Batch Registry
- `/submissions/{id}`：Submission 详情、Operator Console、Export Center
- `/cases/{id}`：Case 风险分析面板
- `/reports/{id}`：Report Reader
- `/ops`：Support / Ops

## 目录

```text
app/                    应用代码
config/                 本地配置与 example 模板
data/runtime/           运行时数据
docs/dev/               规划、日志、验证、经验手册
input/                  本地测试材料
scripts/                启动与验证脚本
tests/                  自动化测试
```

## 进一步阅读

- `docs/dev/09-runbook.md`
- `docs/dev/10-test-matrix.md`
- `docs/dev/07-playbook.md`
- `docs/dev/106-real-provider-acceptance-checklist.md`

## 注意事项

- 不要把真实 API key 写入仓库文件，统一使用环境变量。
- 不要把 `input/`、`output/`、`data/runtime/` 里的本地数据直接纳入版本管理。
- 本项目默认只向外部模型发送脱敏后的 `llm_safe` 载荷。
