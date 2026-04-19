# UI Notes

## Reference Source

本轮 UI 设计参考了本地 `ui-ux-pro-max-skill` 中的以下方向：

- Accessibility first
- Mobile-first responsive layout
- Semantic tokens for color and spacing
- Clear information hierarchy
- Minimal but expressive interaction feedback

补充说明：

- 原始参考目录：`D:\Code\软著智能体\ui-ux-pro-max-skill`
- 已整理到本地技能库：`C:\Users\DOIT\.codex\skills\ui-ux-pro-max`


## MVP Visual Direction

产品气质：

- 专业
- 清晰
- 审慎
- 低浮夸
- 强信息密度但不拥挤

页面风格：

- 柔和暖灰底色
- 深色主文本
- 青绿色与墨蓝色作为功能强调色
- 层级通过间距、边框、阴影、微弱渐变建立
- 上传区、统计卡、问题列表有明显层次差异

## Website Direction For Next Iteration

使用 skill 检索后，下一阶段网站化建议收敛到：

- 风格：`Accessible & Ethical` + `Trust & Authority`
- 用途：面向审查、合规、报告型工作台
- 色彩：浅底高对比，海军蓝 / 文档灰 / 扫描蓝作为主轴
- 字体：`Lexend` + `Source Sans 3`
- 动效：仅保留状态反馈、聚焦、载入过渡，不做花哨演出

## Page-Level Guidance

- 首页：强调两种导入模式的区别、输入说明和主 CTA
- Submission 页面：强调材料清单、分类结果、报告入口
- Case 页面：强调综合结论、跨材料问题、问题优先级
- Report 页面：强调可读性与导出感，而不是卡片堆砌

## This Round UI Refactor

本轮已经实际落地以下调整：

- 首页从“普通上传页”改成“审查工作台首页”
- 上传区与流程区并列，减少空泛介绍
- Submission 页面改为报告区 + 材料区 + 项目区的工作台布局
- Case 页面强化综合结论和跨材料问题阅读体验
- Report 页面改为更接近正式报告阅读器的样式
- 统一顶部品牌区、状态胶囊、摘要卡和焦点态

## Implemented Tokens

- 标题字体：`Lexend`
- 正文字体：`Source Sans 3`
- 主色：`#2563EB`
- 深色骨架：`#1E293B`
- 背景：`#F8FAFC` / `#EDF2F7`
- 强调目标：可信、清晰、非模板化、可访问

## Admin Console Refactor

用户进一步明确后，前端方向已经从“审查台首页”彻底切换成“后台分析系统”：

- 使用 `Data-Dense Dashboard` 作为新的视觉和结构主轴
- 采用左侧导航 + 顶部分析栏 + 中间内容工作区
- 首页改为控制台，不再像官网 Landing Page
- Submission / Case 使用 KPI 卡、数据表、分布面板、风险队列
- Report 改为后台阅读器视图

## New Design Tokens

- 标题字体：`Fira Code`
- 正文字体：`Fira Sans`
- 主色：`#1E40AF`
- 次色：`#3B82F6`
- 强调色：`#D97706`
- 背景：`#F3F7FC`

## New Anti-Patterns

- 不再使用官网 Hero 式布局作为主要框架
- 不再使用偏品牌展示的首页信息架构
- 不再把核心数据放在卡片文案里而缺少表格和分析区

## Anti-Patterns

- 不要做“泛后台模板风”
- 不要使用 AI 紫粉渐变
- 不要为了酷炫牺牲可读性
- 不要在审查主路径里加入高噪音动效
