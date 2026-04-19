from __future__ import annotations

import dataclasses
import importlib
import inspect
import json
from enum import Enum

import pytest


def require_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - helper for pre-implementation phase
        pytest.xfail(f"Contract pending: unable to import module {module_name}: {exc}")


def require_symbol(module_name: str, symbol_name: str):
    module = require_module(module_name)
    if not hasattr(module, symbol_name):  # pragma: no cover - helper for pre-implementation phase
        pytest.xfail(f"Contract pending: missing symbol {module_name}.{symbol_name}")
    return getattr(module, symbol_name)


def get_field_names(model_cls) -> set[str]:
    if hasattr(model_cls, "model_fields"):
        return set(model_cls.model_fields.keys())
    if dataclasses.is_dataclass(model_cls):
        return {field.name for field in dataclasses.fields(model_cls)}
    annotations = getattr(model_cls, "__annotations__", {})
    if annotations:
        return set(annotations.keys())
    pytest.fail(f"Unable to inspect declared fields for {model_cls!r}")


def get_signature(symbol):
    return inspect.signature(symbol)


def get_value(obj, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def get_material_type(result):
    candidate = result
    if isinstance(result, dict):
        candidate = (
            result.get("material_type")
            or result.get("type")
            or result.get("classification")
            or result.get("result")
        )
    elif hasattr(result, "material_type"):
        candidate = result.material_type
    elif hasattr(result, "type"):
        candidate = result.type
    if isinstance(candidate, Enum):
        return candidate.value
    return candidate


def get_issues(result):
    if isinstance(result, dict):
        return result.get("issues") or result.get("errors") or []
    if hasattr(result, "issues"):
        return getattr(result, "issues")
    if hasattr(result, "errors"):
        return getattr(result, "errors")
    return []


def get_metadata(result):
    if isinstance(result, dict):
        return (
            result.get("metadata")
            or result.get("info")
            or result.get("extracted_fields")
            or {}
        )
    for attr in ("metadata", "info", "extracted_fields"):
        if hasattr(result, attr):
            return getattr(result, attr)
    return {}


def renderable_text(payload) -> str:
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, (list, tuple)):
        return "\n".join(renderable_text(item) for item in payload)
    if isinstance(payload, dict):
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return str(payload)


def issues_contain(result, expected_fragment: str) -> bool:
    haystack = renderable_text(get_issues(result))
    return expected_fragment in haystack

