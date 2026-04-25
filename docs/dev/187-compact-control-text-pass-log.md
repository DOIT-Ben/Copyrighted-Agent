# 187 控件文字与标题紧凑化记录

## 时间
- 2026-04-25

## 目标
- 继续收短全站按钮、下载入口和折叠标题的视觉占用
- 避免长文案把按钮、卡片和折叠标题撑宽
- 保持功能不变，只收敛展示层

## 本次调整
- 更新 `app/web/static/styles.css`
- 按钮统一增加：
  - `max-width`
  - `overflow: hidden`
  - `text-overflow: ellipsis`
  - `white-space: nowrap`
- `button-compact` 限制最大宽度为 `10rem`
- `download-chip` 限制最大宽度为 `10rem`
- 折叠区标题单行显示，超出后省略
- 摘要卡主值最多显示两行，避免高度失控
- 动作组间距从 `0.65rem` 收到 `0.5rem`

## 结果
- 长按钮不再明显撑开布局
- 下载按钮更紧凑
- 折叠区标题更规整
- 摘要卡高度更稳定

## 验证
- `D:\Soft\python310\python.exe -m py_compile app\web\page_ops.py app\web\view_helpers.py app\web\page_home.py app\web\page_submission.py app\web\page_case.py app\web\page_report.py app\web\page_review_rule.py app\web\review_profile_widgets.py app\web\prompt_views.py`
- `D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q`
- 结果：`6/6 passed`
