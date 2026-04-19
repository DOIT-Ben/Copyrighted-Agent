from __future__ import annotations

import zipfile
from pathlib import Path

import pytest


def _write_zip(zip_path: Path, files: dict[str, str]) -> Path:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative_path, content in files.items():
            archive.writestr(relative_path, content)
    return zip_path


@pytest.fixture(autouse=True)
def reset_runtime_store():
    try:
        from app.core.services.runtime_store import store
    except Exception:
        yield
        return
    store.reset()
    yield
    store.reset()


@pytest.fixture
def api_client():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from app.api.main import create_app

    return TestClient(create_app(testing=True))


@pytest.fixture
def make_zip(tmp_path: Path):
    def _factory(zip_name: str, files: dict[str, str]) -> Path:
        return _write_zip(tmp_path / zip_name, files)

    return _factory


@pytest.fixture
def mode_a_zip_path(make_zip):
    return make_zip(
        "single_case_bundle.zip",
        {
            "信息采集表.txt": "软件名称：极光关节运动分析系统\n版本号：V1.0\n著作权人：极光医疗科技有限公司",
            "源代码.txt": "def calculate_angle(a, b, c):\n    return 90\n",
            "软著文档.txt": "极光关节运动分析系统 V1.0\n目录\n运行环境\n操作步骤\n",
            "合作协议/2501_合作协议.txt": "本协议自双方签订之日起生效。\n甲方：公司A\n乙方：公司B",
            "合作协议/2502_合作协议.txt": "本协议自双方签订之日起生效。\n甲方：公司A\n乙方：公司B",
        },
    )


@pytest.fixture
def mode_a_root_level_zip_path(make_zip):
    return make_zip(
        "single_case_root_level.zip",
        {
            "信息采集表.txt": "软件名称：极光关节运动分析系统\n版本号：V1.0",
            "代码.txt": "def calculate_angle(a, b, c):\n    return 90\n",
            "说明书.txt": "极光关节运动分析系统 V1.0\n运行环境\n操作步骤\n",
            "2501_合作协议.txt": "本协议自双方签订之日起生效。\n甲方：公司A\n乙方：公司B",
        },
    )


@pytest.fixture
def mode_b_zip_path(make_zip):
    return make_zip(
        "agreements_batch.zip",
        {
            "项目A_合作协议.txt": "项目A\n甲方：公司A\n乙方：公司B\n本协议自双方签订之日起生效。",
            "项目B_合作协议.txt": "项目B\n甲方：公司C\n乙方：公司D\n本协议自双方签订之日起生效。",
            "项目C_合作协议.txt": "项目C\n甲方：公司E\n乙方：公司F\n本协议自双方签订之日起生效。",
        },
    )


@pytest.fixture
def mode_b_ambiguous_zip_path(make_zip):
    return make_zip(
        "agreements_batch_ambiguous.zip",
        {
            "合作协议_未识别1.txt": "甲方：公司A\n乙方：公司B\n本协议自双方签订之日起生效。",
            "合作协议_未识别2.txt": "甲方：公司A\n乙方：公司B\n本协议自双方签订之日起生效。",
        },
    )


@pytest.fixture
def zip_with_zip_slip_path(make_zip):
    return make_zip(
        "zip_slip_attack.zip",
        {
            "../evil.txt": "should never be extracted outside target dir",
            "正常文件.txt": "safe content",
        },
    )


@pytest.fixture
def zip_with_executable_path(make_zip):
    return make_zip(
        "archive_with_executable.zip",
        {
            "正常文件.txt": "safe content",
            "payload.exe": "MZ-binary-placeholder",
        },
    )


@pytest.fixture
def zip_with_windows_unsafe_names_path(make_zip):
    return make_zip(
        "windows_unsafe_names.zip",
        {
            "合作协议/2501:合作协议?.txt": "本协议自双方签订之日起生效。\n甲方：公司A\n乙方：公司B",
            "信息采集表|终版.txt": "软件名称：极光关节运动分析系统\n版本号：V1.0\n著作权人：极光医疗科技有限公司",
            "说明书<最终>.txt": "极光关节运动分析系统 V1.0\n目录\n运行环境\n操作步骤\n",
        },
    )
