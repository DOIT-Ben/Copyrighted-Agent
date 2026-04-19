# Comprehensive Test Matrix

## Goal

把这个项目后续所有迭代都围绕一套清晰的测试矩阵推进，而不是“想到哪测到哪”。

## Coverage Map

### 1. Upload And ZIP Ingestion

- [x] 上传 ZIP 成功
- [x] 非 ZIP 被拒绝
- [x] 模式 A 可导入
- [x] 模式 B 可导入
- [x] 根目录平铺 ZIP 可导入
- [x] Windows 非法文件名 ZIP 可导入并清洗
- [x] Zip Slip 被拦截
- [x] 可执行文件被拦截

### 2. Domain Contracts

- [x] `SubmissionMode` 枚举完整
- [x] `MaterialType` 枚举完整
- [x] `Submission / Case / Material / ParseResult / ReviewResult / ReportArtifact / Job` 最小字段完整

### 3. Classification

- [x] 文件名规则可识别四类核心材料
- [x] 内容规则可纠正文件名不明确的情况
- [x] 无法判断时回退 `unknown`

### 4. Parsing

- [x] 四类 parser 类存在
- [x] parser 暴露统一 `parse` 方法
- [x] `parse_material(file_path, material_type)` 入口存在

### 5. Rule Review

- [x] 合作协议错词检查
- [x] 文档版本号不一致检查
- [x] 源代码乱码检查
- [x] 信息采集表关键字段提取
- [x] 跨材料一致性检查

### 6. Report Generation

- [x] 材料级报告渲染
- [x] 项目级报告渲染
- [x] 批次级报告渲染

### 7. Web MVP

- [x] 首页渲染上传控件
- [x] `/upload` 提交后重定向到 Submission 页面
- [x] Submission 页面可打开
- [x] Case 页面可打开
- [x] Report 页面可打开
- [x] Submission 列表页可看到导入记录

## Manual Acceptance Checklist

### P0

- [ ] 用真实 ZIP 上传模式 A，确认页面链路完整
- [ ] 用真实 ZIP 上传模式 B，确认批次可展示
- [ ] 检查中文文件名材料不会导致 500
- [ ] 检查报告页在长文本下仍然可读

### P1

- [ ] 移动端宽度下首页无横向滚动
- [ ] 焦点态清晰可见
- [ ] 主要按钮 hover / active 状态自然
- [ ] 空状态文案清晰

### P2

- [ ] 更真实 `.doc` / `.pdf` 样本回归
- [ ] 大 ZIP 导入耗时采样
- [ ] 多次重复提交稳定性采样

## Regression Rules

每次发现线上或手工验证问题，都要问三件事：

1. 能不能先写成最小复现测试？
2. 修复后能不能留成长期回归用例？
3. 要不要把原因记入 `docs/dev/06-issues-and-fixes.md`？

## Exit Criteria

进入下一轮网站增强前，至少满足：

- 所有现有自动化测试通过
- 模式 A 主链路自动化通过
- 关键安全测试通过
- 关键问题已有文档记录和回归用例
