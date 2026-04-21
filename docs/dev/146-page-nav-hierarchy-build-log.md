# 页面导航层级优化构建日志

## 日期

- 2026-04-21

## 背景

- 页面顶部原先把全局入口和页内锚点都塞进同一排 `workspace-shortcuts`。
- 在详情页和运维页中，顶部胶囊数量过多，容易和主标题抢注意力。
- 报告页虽然已经把正文做成整行，但上下文信息仍然复用通用双列表现，对长路径和长值不够友好。

## 本轮目标

- 把“全局导航”和“本页导航”拆成两层，不再混在同一排。
- 保留所有页内锚点，但降低其在 Header 区域的视觉抢占。
- 优化报告页上下文字段对长值的容纳能力。

## 实施内容

- 更新 `app/web/view_helpers.py`
  - `workspace-shortcuts` 只保留全局入口
  - 新增 `_page_link_strip(page_links)`，单独渲染“本页导航”
  - `layout()` 在 Header/notice 后插入页内导航带
  - `list_pairs()` 支持传入自定义类名
- 更新 `app/web/static/styles.css`
  - 新增 `page-link-strip`、`page-link-chip`、`page-link-strip-row`
  - 为页内导航带增加独立容器和更轻的视觉权重
  - 新增 `dossier-list-single`
  - 为 `dossier-list` 内容块补充 `min-width: 0` 和长值换行能力
- 更新 `app/web/page_report.py`
  - 报告上下文改为 `dossier-list dossier-list-single`

## 效果

- 页面顶部结构更清晰：
  - 发布栏只展示全局入口
  - 页内锚点下沉为单独导航带
- 报告页元数据不再被压成双列小块，长路径与长 ID 更易读。

## 涉及文件

- `app/web/view_helpers.py`
- `app/web/static/styles.css`
- `app/web/page_report.py`

