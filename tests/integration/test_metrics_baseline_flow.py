from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.integration
@pytest.mark.contract
def test_metrics_baseline_can_collect_single_case_package_directory_snapshot(make_zip, tmp_path: Path):
    build_baseline_snapshot = require_symbol("app.tools.metrics_baseline", "build_baseline_snapshot")

    package_dir = tmp_path / "packages"
    package_dir.mkdir(parents=True, exist_ok=True)
    make_zip(
        str(package_dir / "2501_软著材料.zip"),
        {
            "信息采集表.txt": "软件名称：极光系统\n版本号：V1.0\n著作权人：极光医疗",
            "源代码.txt": "def calculate_angle(a, b, c):\n    return 90\n",
            "软著文档.txt": "极光系统 V1.0\n目录\n运行环境\n操作步骤",
            "合作协议.txt": "甲方：公司A\n乙方：公司B\n本协议自双方签订之日起生效。",
        },
    )
    make_zip(
        str(package_dir / "2502_软著材料.zip"),
        {
            "信息采集表.txt": "软件名称：极光系统2\n版本号：V2.0\n著作权人：极光医疗",
            "源代码.txt": "def calculate_speed(a, b):\n    return a + b\n",
            "软著文档.txt": "极光系统2 V2.0\n目录\n运行环境\n操作步骤",
            "合作协议.txt": "甲方：公司C\n乙方：公司D\n本协议自双方签订之日起生效。",
        },
    )

    snapshot = build_baseline_snapshot(
        [
            {
                "label": "fixture_mode_a",
                "path": str(package_dir),
                "mode": "single_case_package",
            }
        ]
    )

    target = snapshot["targets"][0]
    assert target["label"] == "fixture_mode_a"
    assert target["aggregate"]["materials"] == 8
    assert target["aggregate"]["cases"] == 2
    assert target["aggregate"]["reports"] == 2
