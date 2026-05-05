# 软著智能体

软著智能体是一个面向软件著作权材料整理、脱敏、审查、分组、报告生成和运维排查的本地 Web 管理系统。

当前正式产品形态是 `app/` 下的 Web MVP，而不是旧 CLI 工具集合。项目优先使用 `uv` 管理虚拟环境和依赖。

## 能做什么

- 导入软著 ZIP 材料包。
- 支持单案完整材料包和批量同类材料两种模式。
- 自动解析 DOC/DOCX/PDF/TXT/MD。
- 自动识别材料类型：信息采集表、源代码、软件说明文档、协议/权属材料等。
- 执行规则审查、整包全局审查、跨材料一致性检查和在线填报信息检查。
- 生成材料报告、项目报告、整包全局报告和导出包。
- 支持先脱敏后继续审查的人工流程。
- 支持 AI 审查补充，但默认只发送脱敏后的安全载荷。
- 提供批次台账、案件详情、报告阅读器、人工干预台、导出中心和运维页。

## 技术形态

- 后端：本地 FastAPI 风格接口。
- 前端：服务端渲染的管理后台页面。
- 存储：本地 SQLite 和运行目录。
- 环境：`uv` + `.venv`。
- 测试：单元、集成、E2E 和非功能契约测试。
- CI：GitHub Actions 自动运行编译和全量测试。

## 快速开始

### 1. 安装依赖

如果机器上已经有 `uv`：

```powershell
uv sync --dev
```

如果没有 `uv`，可以先安装：

```powershell
py -m pip install uv
uv sync --dev
```

也可以直接使用项目脚本，它会自动寻找可用的 `uv`：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\ensure_uv.ps1 -Dev
```

### 2. Mock 模式启动

Mock 模式不调用外部模型，适合本地开发和演示：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_uv_web.ps1 -Mock
```

默认访问地址：

```text
http://127.0.0.1:8000
```

### 3. 真实模型模式启动

先准备 API Key 环境变量：

```powershell
$env:MINIMAX_API_KEY="你的真实密钥"
```

启动模型桥接服务：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_real_bridge.ps1
```

再启动 Web：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_uv_web.ps1 -Port 18080
```

访问地址：

```text
http://127.0.0.1:18080
```

## 常用命令

运行全量测试：

```powershell
.venv\Scripts\pytest.exe -q
```

编译检查：

```powershell
.venv\Scripts\python.exe -m compileall app
```

查看本地服务状态：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\show_stack_status.ps1
```

执行真实链路验证：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_real_validation.ps1
```

## 关键页面

- `/`：导入控制台。
- `/submissions`：批次台账。
- `/submissions/{id}`：批次详情和整包全局审查。
- `/submissions/{id}/materials`：材料矩阵和脱敏产物。
- `/submissions/{id}/operator`：人工干预台。
- `/submissions/{id}/exports`：导出中心。
- `/cases/{id}`：项目风险分析。
- `/reports/{id}`：报告阅读器。
- `/ops`：运维和健康检查。

## 目录结构

```text
app/                    正式应用代码
app/api/                HTTP 路由和本地服务入口
app/core/               领域模型、解析、审查、服务和流水线
app/web/                服务端渲染页面和前端静态资源
app/tools/              运维、验证、备份和探针工具
config/                 本地配置和示例配置
docs/                   项目说明、运行手册和历史开发记录
scripts/                一键启动和验证脚本
tests/                  自动化测试
cli.py, src/            legacy CLI 代码，仅保留作迁移参考
```

更详细说明见：

- `docs/PROJECT_STRUCTURE.md`
- `docs/ENCODING.md`
- `docs/LEGACY.md`

## 配置说明

默认读取：

- `config/local.json`
- `SOFT_REVIEW_*` 环境变量覆盖

示例配置：

- `config/local.example.json`
- `config/local.minimax_bridge.example.json`

不要把真实 API Key 写入配置文件，统一使用环境变量。

## 测试和 CI

本地全量测试：

```powershell
.venv\Scripts\pytest.exe -q
```

GitHub Actions 会在 `main` 的 push 和 pull request 上自动执行：

- `uv sync --dev`
- `python -m compileall app`
- `pytest -q`

## 编码和文案约定

项目包含中文文案，统一按 UTF-8 处理。Windows PowerShell 有时会把正常 UTF-8 预览成乱码，不要仅凭终端显示就重写文件。

编辑前请阅读：

- `docs/ENCODING.md`
- `app/web/README.md`

## Legacy 说明

`cli.py` 和 `src/` 是旧 CLI 阶段代码。新功能应放在 `app/`、`app/tools/` 或 `scripts/` 中。

迁移策略见：

- `docs/LEGACY.md`

## 注意事项

- 不提交 `input/`、`output/`、`data/runtime/`、`tmp_runtime/` 等本地运行数据。
- 不提交真实 API Key。
- 默认只向外部模型发送脱敏后的安全载荷。
- 提交前请运行全量测试。
