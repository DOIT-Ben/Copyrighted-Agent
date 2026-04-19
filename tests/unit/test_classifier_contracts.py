from __future__ import annotations

import pytest

from tests.helpers.contracts import get_material_type, require_symbol


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.classifier
@pytest.mark.parametrize(
    ("file_name", "content", "expected_type"),
    [
        ("信息采集表.doc", "", "info_form"),
        ("代码.doc", "", "source_code"),
        ("软著文档.doc", "", "software_doc"),
        ("2510_合作协议.doc", "", "agreement"),
    ],
)
def test_classifier_can_use_filename_keywords(file_name, content, expected_type):
    classify_material = require_symbol("app.core.services.material_classifier", "classify_material")
    result = classify_material(file_name=file_name, content=content, directory_hint="")
    assert get_material_type(result) == expected_type


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.classifier
@pytest.mark.parametrize(
    ("file_name", "content", "expected_type"),
    [
        ("unknown_1.txt", "软件名称：极光关节运动分析系统\n著作权人：极光医疗", "info_form"),
        ("unknown_2.txt", "def calculate_angle(a, b, c):\n    return 90\n", "source_code"),
        ("unknown_3.txt", "目录\n运行环境\n操作步骤\n界面截图", "software_doc"),
        ("unknown_4.txt", "甲方：公司A\n乙方：公司B\n本协议自双方签订之日起生效。", "agreement"),
    ],
)
def test_classifier_can_use_content_when_filename_is_not_enough(file_name, content, expected_type):
    classify_material = require_symbol("app.core.services.material_classifier", "classify_material")
    result = classify_material(file_name=file_name, content=content, directory_hint="")
    assert get_material_type(result) == expected_type


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.classifier
def test_classifier_returns_unknown_for_irrelevant_content():
    classify_material = require_symbol("app.core.services.material_classifier", "classify_material")
    result = classify_material(
        file_name="random_notes.txt",
        content="this is just a note without recognizable software copyright signals",
        directory_hint="",
    )
    assert get_material_type(result) == "unknown"

