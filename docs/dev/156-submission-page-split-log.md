# 批次详情拆页开发日志

日期：2026-04-21

## 目标

- 批次详情页进一步简化。
- 不再把 `导入摘要`、`产物浏览`、`人工干预台`、`导出中心` 全部堆在一个页面。
- 保留现有集成测试要求的关键入口文字。

## 本次调整

- 将批次页面拆成以下结构：
  - `/submissions/{id}`：批次总览页
  - `/submissions/{id}/materials`：产物浏览页
  - `/submissions/{id}/operator`：人工干预台
  - `/submissions/{id}/exports`：导出中心
- 主批次页只保留：
  - 导入摘要
  - 待复核队列
  - 去往三个子页面的导航入口
- 重内容迁移如下：
  - 材料矩阵、项目分组、材料产物 -> `materials`
  - 更正材料、项目编排、重跑审查、更正审计 -> `operator`
  - 报告、批次包、日志 -> `exports`

## 涉及文件

- `app/web/page_submission.py`
- `app/web/pages.py`
- `app/api/main.py`

## 兼容性处理

- `/submissions/{id}` 仍保留以下关键文字，避免破坏契约测试：
  - `导入摘要`
  - `人工干预台`
  - `导出中心`
  - `产物浏览`

## 验证

执行：

```powershell
py -3 -m py_compile app\web\page_submission.py app\web\pages.py app\api\main.py
py -3 -m pytest tests\integration\test_operator_console_and_exports.py tests\integration\test_web_mvp_contracts.py
```

结果：

- `py_compile` 通过
- `7/7 passed`

在线验证：

- `/submissions/{id}` 返回 `200`
- `/submissions/{id}/materials` 返回 `200`
- `/submissions/{id}/operator` 返回 `200`
- `/submissions/{id}/exports` 返回 `200`

## 结果

- 批次页面的信息架构从“单页堆叠”改为“总览 + 子页”。
- 主页面视觉负担明显下降。
- 人工操作、导出、材料核查都拥有独立空间，后续继续精修会更容易。
