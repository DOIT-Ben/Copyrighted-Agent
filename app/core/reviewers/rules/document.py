from __future__ import annotations

import re

from app.core.reviewers.rules.sensitive_terms import scan_sensitive_terms
from app.core.utils.text import extract_software_name, extract_version


def _contains_any(text: str, keywords: list[str]) -> bool:
    content = str(text or "")
    return any(keyword in content for keyword in keywords)


def _detect_page_markers(text: str) -> list[int]:
    markers = re.findall(r"第\s*(\d+)\s*页", str(text or ""), flags=re.IGNORECASE)
    return [int(item) for item in markers if str(item).isdigit()]


def _extract_feature_terms(text: str) -> list[str]:
    patterns = [
        r"([一-龥A-Za-z]{2,12}功能)",
        r"([一-龥A-Za-z]{2,12}模块)",
        r"([一-龥A-Za-z]{2,12}(?:管理|分析|查询|导出|统计|审核|采集|监控|登录))",
    ]
    found: list[str] = []
    for pattern in patterns:
        for item in re.findall(pattern, str(text or "")):
            term = str(item).strip()
            if 2 <= len(term) <= 12 and term not in found:
                found.append(term)
    return found[:8]


def review_document_text(text: str) -> dict:
    issues: list[dict] = []
    software_name = extract_software_name(text)
    version = extract_version(text)
    metadata = {
        "software_name": software_name,
        "version": version,
        "feature_terms": _extract_feature_terms(text),
    }

    v1 = len(re.findall(r"\b[Vv]1\.0\b", text))
    v2 = len(re.findall(r"\b[Vv]2\.0\b", text))
    if v1 and v2:
        issues.append(
            {
                "severity": "severe",
                "category": "文档版本号",
                "rule_key": "doc_terms_consistent",
                "desc": f"说明文档中同时出现 V1.0({v1}) 和 V2.0({v2})，版本描述前后不一致。",
            }
        )

    if "Media Pipe" in text:
        issues.append(
            {
                "severity": "minor",
                "category": "术语统一",
                "rule_key": "doc_terms_consistent",
                "desc": '发现“Media Pipe”写法，建议统一为“MediaPipe”。',
            }
        )

    has_environment = ("运行环境" in text) or ("环境要求" in text)
    has_install = ("安装说明" in text) or ("初始化步骤" in text)
    if not has_environment or not has_install:
        missing = []
        if not has_environment:
            missing.append("运行环境")
        if not has_install:
            missing.append("安装说明/初始化步骤")
        issues.append(
            {
                "severity": "severe",
                "category": "必备章节",
                "rule_key": "doc_required_sections",
                "desc": f"说明文档缺少必备章节：{'、'.join(missing)}。",
            }
        )
    else:
        has_hardware = _contains_any(text, ["处理器", "CPU", "内存", "硬盘", "存储", "磁盘"])
        has_software_env = _contains_any(text, ["操作系统", "Windows", "Linux", "数据库", "运行时", "依赖环境", "Python", "JDK", ".NET"])
        if not has_hardware or not has_software_env:
            missing = []
            if not has_hardware:
                missing.append("硬件要求")
            if not has_software_env:
                missing.append("软件环境要求")
            issues.append(
                {
                    "severity": "severe",
                    "category": "运行环境",
                    "rule_key": "doc_required_sections",
                    "desc": f"运行环境章节信息不完整，缺少：{'、'.join(missing)}。",
                    "suggest": "在运行环境章节中分别补充硬件要求和软件环境要求。",
                }
            )

    mixed_terms = [term for term in ["系统", "平台", "APP", "小程序"] if term in text]
    if len(mixed_terms) > 1:
        issues.append(
            {
                "severity": "moderate",
                "category": "术语统一",
                "rule_key": "doc_terms_consistent",
                "desc": f"说明文档中存在多种软件形态称呼：{'、'.join(mixed_terms)}，建议统一口径。",
                "suggest": "全文统一为一种对外表述，例如统一使用“系统”或“平台”。",
            }
        )

    page_numbers = _detect_page_markers(text)
    if page_numbers:
        total_pages = max(page_numbers)
        if total_pages < 10:
            issues.append(
                {
                    "severity": "moderate",
                    "category": "页数审查",
                    "rule_key": "doc_page_count",
                    "desc": f"说明文档页数偏少，当前只识别到约 {total_pages} 页，低于常见提交底线。",
                    "suggest": "补充功能说明、运行环境、安装说明等内容，使文档页数至少达到基本审查要求。",
                }
            )
        elif total_pages > 60:
            issues.append(
                {
                    "severity": "moderate",
                    "category": "页数审查",
                    "rule_key": "doc_page_count",
                    "desc": f"说明文档页数偏多，当前识别到约 {total_pages} 页，可能需要精简重点内容。",
                    "suggest": "压缩冗余截图和重复说明，保留核心章节与必要证据。",
                }
            )

    page_markers = len(re.findall(r"(第\s*\d+\s*页)|(\bpage\s*\d+\b)", text, flags=re.IGNORECASE))
    if page_markers == 0:
        issues.append(
            {
                "severity": "moderate",
                "category": "页眉页脚",
                "rule_key": "doc_header_footer_valid",
                "desc": "未识别到稳定的页码信号，请人工确认页脚是否带有连续页码。",
            }
        )
    if software_name and version:
        header_signal = f"{software_name} {version}"
        if header_signal not in text and f"{software_name}{version}" not in text:
            issues.append(
                {
                    "severity": "moderate",
                    "category": "页眉页脚",
                    "rule_key": "doc_header_footer_valid",
                    "desc": "未识别到“软件全称 + 版本号”的稳定页眉信号，请检查页眉格式是否规范。",
                    "suggest": "将页眉统一设置为“软件全称 + 版本号”，并保持全文一致。",
                }
            )

    screenshot_signals = ["截图", "界面", "页面", "登录页", "首页", "列表页"]
    if _contains_any(text, screenshot_signals):
        has_real_capture_hint = _contains_any(text, ["图1", "图2", "如下图", "界面截图", "运行截图"])
        has_status_bar_hint = _contains_any(text, ["电池", "信号", "时间", "状态栏", "导航条", "返回键", "Home键"])
        if not has_real_capture_hint:
            issues.append(
                {
                    "severity": "minor",
                    "category": "截图规范",
                    "rule_key": "doc_ui_screenshots_valid",
                    "desc": "文档提到了界面或页面展示，但未识别到明确的真实截图标注信号。",
                    "suggest": "补充带编号的真实系统截图，并在正文中明确引用。",
                }
            )
        if has_status_bar_hint:
            issues.append(
                {
                    "severity": "minor",
                    "category": "截图规范",
                    "rule_key": "doc_ui_screenshots_valid",
                    "desc": "截图描述中出现状态栏或导航条信号，建议检查是否裁掉无关顶部/底部栏位。",
                    "suggest": "裁掉手机状态栏、底部导航条和无关系统图标，保留核心业务界面。",
                }
            )

    if len(text.strip()) < 1800:
        issues.append(
            {
                "severity": "minor",
                "category": "文字质量",
                "rule_key": "doc_text_quality",
                "desc": "说明文档内容偏少，可能存在草稿感或信息覆盖不足的问题。",
            }
        )

    issues.extend(
        scan_sensitive_terms(
            text,
            rule_key="doc_sensitive_terms",
            category="敏感词排查",
            severity="moderate",
        )
    )

    return {"issues": issues, "metadata": metadata}
