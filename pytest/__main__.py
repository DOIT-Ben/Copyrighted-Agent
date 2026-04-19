from __future__ import annotations

import importlib
import inspect
import sys
import tempfile
import traceback
from pathlib import Path

from pytest import SkipTest, XFailed


ROOT = Path.cwd()


def discover_test_modules() -> list[str]:
    modules = []
    for path in sorted((ROOT / "tests").rglob("test_*.py")):
        relative = path.relative_to(ROOT).with_suffix("")
        modules.append(".".join(relative.parts))
    return modules


def load_fixture_functions(module):
    fixtures = {}
    for name, value in vars(module).items():
        if callable(value) and getattr(value, "_pytest_fixture", False):
            fixtures[name] = value
    return fixtures


def resolve_fixture(name, fixture_pool, cache):
    if name in cache:
        return cache[name]
    if name == "tmp_path":
        value = Path(tempfile.mkdtemp(prefix="pytest-tmp-"))
        cache[name] = value
        return value
    if name not in fixture_pool:
        raise KeyError(name)
    fixture_func = fixture_pool[name]
    kwargs = {}
    for param_name in inspect.signature(fixture_func).parameters:
        kwargs[param_name] = resolve_fixture(param_name, fixture_pool, cache)
    value = fixture_func(**kwargs)
    cache[name] = value
    return value


def iter_test_functions(module):
    for name, value in sorted(vars(module).items()):
        if callable(value) and name.startswith("test_"):
            yield name, value


def iter_cases(func):
    spec = getattr(func, "_pytest_parametrize", None)
    if not spec:
        yield {}
        return
    names, values = spec
    for entry in values:
        if not isinstance(entry, tuple):
            entry = (entry,)
        yield dict(zip(names, entry))


def run_function(module, func_name, func, conftest_fixtures):
    module_fixtures = load_fixture_functions(module)
    fixture_pool = {**conftest_fixtures, **module_fixtures}
    results = {"passed": 0, "failed": 0, "skipped": 0, "xfailed": 0, "errors": []}

    for case in iter_cases(func):
        cache = {}
        kwargs = {}
        try:
            for param_name in inspect.signature(func).parameters:
                if param_name in case:
                    kwargs[param_name] = case[param_name]
                else:
                    kwargs[param_name] = resolve_fixture(param_name, fixture_pool, cache)
            func(**kwargs)
            results["passed"] += 1
            print(f"PASS {module.__name__}.{func_name} {case or ''}".rstrip())
        except SkipTest as exc:
            results["skipped"] += 1
            print(f"SKIP {module.__name__}.{func_name}: {exc}")
        except XFailed as exc:
            results["xfailed"] += 1
            print(f"XFAIL {module.__name__}.{func_name}: {exc}")
        except Exception as exc:  # pragma: no cover - test runner path
            results["failed"] += 1
            tb = traceback.format_exc()
            results["errors"].append((module.__name__, func_name, exc, tb))
            print(f"FAIL {module.__name__}.{func_name}: {exc}")
    return results


def main():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    try:
        conftest = importlib.import_module("tests.conftest")
        conftest_fixtures = load_fixture_functions(conftest)
    except Exception:
        conftest_fixtures = {}

    summary = {"passed": 0, "failed": 0, "skipped": 0, "xfailed": 0}
    errors = []

    for module_name in discover_test_modules():
        module = importlib.import_module(module_name)
        for func_name, func in iter_test_functions(module):
            result = run_function(module, func_name, func, conftest_fixtures)
            for key in summary:
                summary[key] += result[key]
            errors.extend(result["errors"])

    print("")
    print("==== Summary ====")
    print(f"passed={summary['passed']} failed={summary['failed']} skipped={summary['skipped']} xfailed={summary['xfailed']}")

    if errors:
        print("")
        print("==== Failures ====")
        for module_name, func_name, exc, tb in errors:
            print(f"{module_name}.{func_name}: {exc}")
            print(tb)

    raise SystemExit(1 if summary["failed"] else 0)


if __name__ == "__main__":
    main()

