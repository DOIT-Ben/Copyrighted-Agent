# 209 页数与截图规则落地日志

## 本轮目标

- 补齐源码页数截取策略规则。
- 补齐说明文档页数区间规则。
- 补齐说明文档截图规范的基础信号检测。

## 本轮实现

- `app/core/reviewers/rules/source_code.py`
  - 通过页码信号判断源码是否疑似超过 60 页
  - 当超过 60 页但没有体现“前30页 + 后30页”时，输出 `code_page_strategy`
- `app/core/reviewers/rules/document.py`
  - 通过页码信号判断说明文档是否过少或过多，输出 `doc_page_count`
  - 检测截图相关描述是否包含真实截图标注信号
  - 检测截图描述中是否出现状态栏/导航条残留信号，输出 `doc_ui_screenshots_valid`

## 预期收益

- 用户能直接看到：
  - 源码是不是只截了前半段
  - 说明文档是不是页数太少或太多
  - 界面截图是否可能残留状态栏、导航条等无关元素

## 回归范围

- `tests/unit/test_rule_review_contracts.py`
- `tests/integration/test_web_mvp_contracts.py`
