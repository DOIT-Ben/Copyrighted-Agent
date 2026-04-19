# Architecture Decisions

## Decision 1: FastAPI + Jinja2 for MVP

原因：

- 当前仓库完全是 Python
- 需要快速形成可用网站
- 不希望前期被 Node 前端工程拖慢
- 后续仍可平滑迁移到 React/Next.js


## Decision 2: File-System Runtime Store Instead of Full Database

原因：

- 当前阶段重点是打通业务闭环
- 测试和 MVP 演示不依赖完整数据库
- 可以先用内存与运行目录完成状态管理

后续可演进为：

- SQLite
- PostgreSQL


## Decision 3: Rules First, AI Second

原因：

- 规则引擎更稳定
- 测试更容易覆盖
- 外部模型不应阻断主流程


## Decision 4: Submission / Case / Material As Core Entities

原因：

- 网站化后的核心对象不是文件夹，而是业务实体
- 这样更适合 API、数据库和前端状态管理


## Decision 5: UI Uses Design Tokens

原因：

- 参考 `ui-ux-pro-max-skill` 的建议
- 避免页面在后续扩展时风格漂移
- 后续迁移到组件系统更容易

