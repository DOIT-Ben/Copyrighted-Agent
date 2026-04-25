from __future__ import annotations

from app.core.domain.enums import MaterialType
from app.core.services.review_profile import normalize_review_profile


def _to_dict(item) -> dict:
    if hasattr(item, "to_dict"):
        return item.to_dict()
    return dict(item or {})


def _collect_issue_descriptions(materials: list[dict], material_type: str) -> list[str]:
    descriptions: list[str] = []
    for material in materials:
        if material.get("material_type") != material_type:
            continue
        for issue in material.get("issues", []) or []:
            description = str(issue.get("desc", "") or issue.get("message", "") or issue.get("detail", "") or "").strip()
            if description:
                descriptions.append(description)
    return descriptions


def _material_names(materials: list[dict], material_type: str) -> list[str]:
    names: list[str] = []
    for material in materials:
        if material.get("material_type") != material_type:
            continue
        name = str(material.get("original_filename", "") or material.get("id", "") or "").strip()
        if name:
            names.append(name)
    return names


def _format_scope(names: list[str], fallback: str) -> str:
    if not names:
        return fallback
    if len(names) == 1:
        return names[0]
    return f"{names[0]} 等 {len(names)} 份材料"


def _dimension(key: str, title: str, status: str, tone: str, scope: str, summary: str, findings: list[str]) -> dict:
    return {
        "key": key,
        "title": title,
        "status": status,
        "tone": tone,
        "scope": scope,
        "summary": summary,
        "findings": findings,
    }


def build_case_review_dimensions(
    case,
    materials,
    cross_material_issues: list[dict] | None = None,
    ai_resolution: str = "",
    review_profile: dict | None = None,
) -> list[dict]:
    case_data = _to_dict(case)
    material_dicts = [_to_dict(item) for item in materials]
    cross_material_issues = list(cross_material_issues or [])

    info_forms = _material_names(material_dicts, MaterialType.INFO_FORM.value)
    source_codes = _material_names(material_dicts, MaterialType.SOURCE_CODE.value)
    software_docs = _material_names(material_dicts, MaterialType.SOFTWARE_DOC.value)
    agreements = _material_names(material_dicts, MaterialType.AGREEMENT.value)
    unknown_count = sum(1 for item in material_dicts if item.get("material_type") == MaterialType.UNKNOWN.value)

    info_issues = _collect_issue_descriptions(material_dicts, MaterialType.INFO_FORM.value)
    source_issues = _collect_issue_descriptions(material_dicts, MaterialType.SOURCE_CODE.value)
    document_issues = _collect_issue_descriptions(material_dicts, MaterialType.SOFTWARE_DOC.value)
    agreement_issues = _collect_issue_descriptions(material_dicts, MaterialType.AGREEMENT.value)
    consistency_issues = [
        str(item.get("desc", "") or item.get("message", "") or item.get("detail", "") or "").strip()
        for item in cross_material_issues
        if str(item.get("desc", "") or item.get("message", "") or item.get("detail", "") or "").strip()
    ]

    missing_identity_fields: list[str] = []
    if not str(case_data.get("software_name", "") or "").strip():
        missing_identity_fields.append("软件名称")
    if not str(case_data.get("version", "") or "").strip():
        missing_identity_fields.append("版本号")
    if not str(case_data.get("company_name", "") or "").strip():
        missing_identity_fields.append("申请主体")

    identity_findings = [
        f"软件名称：{case_data.get('software_name', '') or '未识别'}",
        f"版本号：{case_data.get('version', '') or '未识别'}",
        f"申请主体：{case_data.get('company_name', '') or '未识别'}",
    ] + info_issues
    if not info_forms:
        identity_status = "缺少主索引"
        identity_tone = "danger"
        identity_summary = "没有发现信息采集表，基础字段只能依赖其他材料推断，可信度会下降。"
    elif missing_identity_fields or info_issues:
        identity_status = "需要复核"
        identity_tone = "warning"
        identity_summary = (
            f"基础字段已进入审查，但仍需补齐或核对：{'、'.join(missing_identity_fields)}。"
            if missing_identity_fields
            else "基础字段已经抽取，但仍有字段完整性问题需要复核。"
        )
    else:
        identity_status = "已通过"
        identity_tone = "success"
        identity_summary = "软件名称、版本号和申请主体已经形成可用主索引。"

    required_missing: list[str] = []
    if not info_forms:
        required_missing.append("信息采集表")
    if not source_codes:
        required_missing.append("源代码")
    if not software_docs:
        required_missing.append("说明文档")
    completeness_findings = [
        f"信息采集表：{len(info_forms)} 份",
        f"源代码：{len(source_codes)} 份",
        f"说明文档：{len(software_docs)} 份",
        f"协议材料：{len(agreements)} 份",
        f"未知类型材料：{unknown_count} 份",
    ]
    if required_missing:
        completeness_status = "材料不足"
        completeness_tone = "danger"
        completeness_summary = f"核心审查材料还不完整，当前缺少：{'、'.join(required_missing)}。"
    elif unknown_count > 0:
        completeness_status = "待整理"
        completeness_tone = "warning"
        completeness_summary = "核心材料已齐，但仍有未归类材料，建议先完成人工归档。"
    else:
        completeness_status = "已覆盖"
        completeness_tone = "success"
        completeness_summary = "核心材料组合完整，可以支撑基础规则审查和跨材料核对。"

    if consistency_issues:
        consistency_status = "存在冲突"
        consistency_tone = "warning"
        consistency_summary = "跨材料核对发现名称、版本或描述口径存在冲突，需要统一。"
    else:
        consistency_status = "口径一致"
        consistency_tone = "success"
        consistency_summary = "主要材料之间没有发现显著的名称或版本冲突。"
    consistency_findings = consistency_issues or ["软件名称和版本描述在主要材料间未发现明显冲突。"]

    if not source_codes:
        source_status = "未覆盖"
        source_tone = "danger"
        source_summary = "没有发现源代码材料，无法完成源码可读性与核心逻辑维度的审查。"
    elif source_issues:
        source_status = "需要复核"
        source_tone = "warning"
        source_summary = "源码维度已进入审查，但发现乱码、关键逻辑缺失等风险信号。"
    else:
        source_status = "已通过"
        source_tone = "success"
        source_summary = "源码文本可读，未看到明显的乱码或核心逻辑缺失信号。"
    source_findings = source_issues or ["未识别到明显的源码乱码风险或核心逻辑缺失信号。"]

    if not software_docs:
        document_status = "未覆盖"
        document_tone = "danger"
        document_summary = "没有发现说明文档，文档规范和版本描述维度无法完成审查。"
    elif document_issues:
        document_status = "需要复核"
        document_tone = "warning"
        document_summary = "说明文档维度已进入审查，但文档内部存在版本或命名规范问题。"
    else:
        document_status = "已通过"
        document_tone = "success"
        document_summary = "说明文档维度未发现明显的版本冲突或命名异常。"
    document_findings = document_issues or ["未识别到明显的文档版本冲突或命名不规范信号。"]

    if not agreements:
        agreement_status = "未提供"
        agreement_tone = "neutral"
        agreement_summary = "当前没有协议或权属类材料，这个维度不参与主结论。"
    elif agreement_issues:
        agreement_status = "需要复核"
        agreement_tone = "warning"
        agreement_summary = "协议文本维度发现日期、用词或签署口径问题，建议人工复核。"
    else:
        agreement_status = "已通过"
        agreement_tone = "success"
        agreement_summary = "协议或权属类材料未发现明显的用词与日期异常。"
    agreement_findings = agreement_issues or ["当前协议文本维度未识别到明显异常。"] if agreements else ["本批次未提供协议或权属类材料。"]

    ai_status = "已补充" if ai_resolution and ai_resolution not in {"not_run", "explicit_mock"} else "规则为主"
    ai_tone = "success" if ai_status == "已补充" else "neutral"
    ai_summary = (
        "AI 已对规则结果做补充归纳，可作为人工复核的辅助参考。"
        if ai_status == "已补充"
        else "当前主要依据规则引擎结果，AI 只提供有限补充或未实际介入。"
    )

    dimensions = [
        _dimension(
            "identity",
            "基础信息完整性",
            identity_status,
            identity_tone,
            _format_scope(info_forms, "信息采集表 / 基础字段"),
            identity_summary,
            identity_findings,
        ),
        _dimension(
            "completeness",
            "材料完整性",
            completeness_status,
            completeness_tone,
            "材料组合覆盖",
            completeness_summary,
            completeness_findings,
        ),
        _dimension(
            "consistency",
            "跨材料一致性",
            consistency_status,
            consistency_tone,
            "信息采集表 / 源代码 / 说明文档",
            consistency_summary,
            consistency_findings,
        ),
        _dimension(
            "source_code",
            "源码可审查性",
            source_status,
            source_tone,
            _format_scope(source_codes, "源代码材料"),
            source_summary,
            source_findings,
        ),
        _dimension(
            "software_doc",
            "说明文档规范",
            document_status,
            document_tone,
            _format_scope(software_docs, "说明文档材料"),
            document_summary,
            document_findings,
        ),
        _dimension(
            "agreement",
            "协议文本规范",
            agreement_status,
            agreement_tone,
            _format_scope(agreements, "协议 / 权属材料"),
            agreement_summary,
            agreement_findings,
        ),
        _dimension(
            "ai",
            "AI 补充研判",
            ai_status,
            ai_tone,
            "规则结论归纳",
            ai_summary,
            [f"AI 执行状态：{ai_resolution or 'not_run'}"],
        ),
    ]
    enabled_dimensions = set(normalize_review_profile(review_profile).get("enabled_dimensions", []))
    return [item for item in dimensions if item.get("key") in enabled_dimensions]


__all__ = ["build_case_review_dimensions"]
