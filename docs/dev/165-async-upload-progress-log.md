# 165 异步上传与真实进度反馈日志

日期：2026-04-24

## 背景

首页“开始分析”此前只有前端即时提示，但上传流程仍是同步表单提交。用户虽然能看到按钮 loading，却无法获得真实处理状态。

## 本次处理

1. 新增异步提交入口：`POST /api/submissions/async`
2. 上传后立即返回：
   - `job_id`
   - `submission_id`
   - `status_url`
   - `redirect_url`
3. 首页导入表单接入异步提交能力，并保留原有 `/upload` 作为无脚本兜底。
4. 前端提交反馈层改为轮询 `job` 状态：
   - 文件已接收
   - 正在登记批次
   - 正在解压文件
   - 正在解析材料
   - 正在整理项目
   - 正在生成审查结果 / 脱敏交付 / 批次报告
   - 结果已生成
5. 为 `Job` 模型补充：
   - `stage`
   - `detail`
6. 在提交失败时，前端会恢复按钮可用状态并显示错误提示。

## 涉及文件

- `app/core/domain/models.py`
- `app/core/pipelines/submission_pipeline.py`
- `app/api/main.py`
- `app/web/page_home.py`
- `app/web/view_helpers.py`
- `app/web/static/styles.css`
- `tests/integration/test_web_mvp_contracts.py`

## 验证

- 首页 HTML 包含 `data-async-upload-url="/api/submissions/async"`
- 异步上传接口返回 `202`
- 轮询 `status_url` 可得到完成态 `job`
- 集成测试覆盖异步提交流程与 job 完成态

## 当前结果

用户点击“开始分析”后，前端不再只是展示假进度，而是跟随真实 job 状态推进，并在处理完成后自动跳转到对应批次详情页。
