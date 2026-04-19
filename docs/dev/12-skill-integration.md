# UI Skill Integration

## Purpose

把用户提供的 `ui-ux-pro-max-skill` 从“项目里的参考资料”变成“本地可复用技能”。

## Source And Installed Paths

- 原始来源：`D:\Code\软著智能体\ui-ux-pro-max-skill`
- 技能库目录：`C:\Users\DOIT\.codex\skills\ui-ux-pro-max`

## What Was Added

- 复制 `scripts/` 到技能目录
- 复制 `data/` 到技能目录
- 新建 `SKILL.md`
- 新建 `agents/openai.yaml`

## What This Skill Is Used For

- 页面视觉方向选择
- 色彩、排版、间距系统设计
- 管理台 / 审查台 / Landing 页结构决策
- UI 可访问性与体验审查

## Recommended Usage

### 1. 先生成设计系统

```bash
py C:\Users\DOIT\.codex\skills\ui-ux-pro-max\scripts\search.py "document review accessibility enterprise dashboard trust" --design-system -p "Soft Copyright Review Desk" -f markdown
```

### 2. 再补局部检索

```bash
py C:\Users\DOIT\.codex\skills\ui-ux-pro-max\scripts\search.py "accessible enterprise" --domain style
py C:\Users\DOIT\.codex\skills\ui-ux-pro-max\scripts\search.py "trust document blue" --domain color
py C:\Users\DOIT\.codex\skills\ui-ux-pro-max\scripts\search.py "readable professional" --domain typography
py C:\Users\DOIT\.codex\skills\ui-ux-pro-max\scripts\search.py "focus states keyboard navigation" --domain ux
```

## Validation Status

- 技能目录结构已建立完成
- 检索脚本已成功执行
- `quick_validate.py` 未执行成功

原因：

- 当前环境缺少 `yaml` 依赖，运行系统校验脚本时报错 `ModuleNotFoundError: No module named 'yaml'`

## Project-Level Design Conclusion

对本项目，建议后续网站化设计继续遵循：

- 高可读、高对比、低噪音
- 以审查工作流为中心，而不是营销感首页
- 轻量动效，只服务于状态变化和层级引导
- 可访问性优先
