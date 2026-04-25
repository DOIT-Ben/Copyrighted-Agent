# 180 全站极简化收口记录

## 时间
- 2026-04-24

## 目标
- 继续降低全站提示噪音
- 删除不必要的说明性文案与装饰信息
- 统一首页、批次页、报告页、规则页、运维页的简约观感

## 本次修改
- 共享层 `app/web/view_helpers.py`
- 样式层 `app/web/static/styles.css`
- 报告页 `app/web/page_report.py`
- 审查配置组件 `app/web/review_profile_widgets.py`

## 具体动作
- 保留共享页头主标题和状态区，弱化页头提示性内容
- 通过共享样式隐藏全站次要说明元素：
  - 页头标签
  - 页头副标题
  - 表单 hint
  - summary tile 的补充说明
  - 折叠区 small 提示
  - 维度选择说明小字
  - prompt 维度卡片小字
  - helper chip 行
- 侧边栏只强调品牌与主导航，其余流程型说明区通过样式层隐藏
- 整体缩小阴影、悬浮动效、图标体积与卡片留白，减少“管理台噪声感”
- 报告页工具条改为仅保留导出动作：
  - 保存 MD
  - 保存 PDF
- 审查配置组件去掉维度描述行，保留更直接的选择结构

## 验证
- `D:\Soft\python310\python.exe -m py_compile app\web\view_helpers.py app\web\page_home.py app\web\page_submission.py app\web\page_case.py app\web\page_report.py app\web\page_review_rule.py app\web\page_ops.py app\web\review_profile_widgets.py app\web\prompt_views.py`
- `D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q`
- 结果：`6/6 passed`

## 备注
- 本轮以“减法”为主，没有新增业务入口
- 页面现有能力保持不变，重点是统一简约感与可扫读性
