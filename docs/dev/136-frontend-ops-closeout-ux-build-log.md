# 运维页交付收尾可视化构建日志
## 日期

- 2026-04-21

## 本轮范围

- `/ops` 页面信息层级重组。
- `delivery_closeout` 只读加载与下载支持。
- 运维页 closeout 产物下载路由。
- 相关测试补齐。

## 实际改动

- `app/core/services/delivery_closeout.py`
  - 新增 `latest_delivery_closeout_status(...)`
  - 新增 `get_delivery_closeout_artifact_download(...)`
  - 让 closeout 能以只读方式被前端消费，而不是只能通过 CLI 写产物。
- `app/api/main.py`
  - `_build_ops_report(...)` 加入 `delivery_closeout`
  - 新增：
    - `/downloads/ops/delivery-closeout/latest-json`
    - `/downloads/ops/delivery-closeout/latest-md`
- `app/web/page_ops.py`
  - 新增业务收尾状态卡。
  - 新增业务收尾主面板。
  - 在页面快捷入口中加入“先看业务收尾”。
  - 在运维页 KPI 中加入“业务收尾”。
  - 调整运维页 KPI 栅格为 `kpi-grid-ops`。
- `app/web/static/styles.css`
  - 新增 closeout 面板相关样式：
    - `closeout-board`
    - `closeout-callout`
    - `artifact-strip`
    - `closeout-action-block`
    - `action-list`
  - 新增 `kpi-grid-ops`
  - 补 closeout 面板响应式规则。
- `tests/unit/test_delivery_closeout_contracts.py`
  - 新增 latest closeout 只读加载测试。
  - 新增下载 helper 路径防逃逸测试。
- `tests/integration/test_operator_console_and_exports.py`
  - 新增 `/ops` 页面 closeout 文案和下载链接断言。
  - 新增 closeout 下载路由断言。

## 关键设计决定

- 没有把 `delivery_closeout` 做成单独页面，而是直接上提到 `/ops`。
- 运维页优先级调整为：
  - 先看业务收尾
  - 再看发布闸门
  - 再看通道与探针
  - 最后看趋势与回滚点
- closeout 主面板不展示过多底层字段，而是优先展示结论、动作和产物。
- 只读加载优先于动态生成，避免打开页面就触发重量级流程。

## 产出效果

- 运维和业务现在能直接在 `/ops` 一眼看到当前是否可交付。
- 最新 closeout Markdown 和 JSON 可以直接从页面下载。
- 业务收尾不再只是命令行能力，而是进入了主工作台。
