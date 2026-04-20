from __future__ import annotations

import importlib
import inspect
import os
import sys
import tempfile
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from pytest import SkipTest, XFailed


ROOT = Path.cwd()


def discover_test_modules(path_filters: list[str] | None = None) -> list[str]:
    modules = []
    for path in sorted((ROOT / "tests").rglob("test_*.py")):
        relative = path.relative_to(ROOT).with_suffix("")
        module_name = ".".join(relative.parts)
        if _matches_module_filter(module_name, path_filters or []):
            modules.append(module_name)
    return modules


def _matches_module_filter(module_name: str, path_filters: list[str]) -> bool:
    if not path_filters:
        return True
    module_path = str(Path(*module_name.split(".")).with_suffix(".py")).replace("\\", "/").lower()
    for raw_filter in path_filters:
        normalized = str(raw_filter or "").replace("\\", "/").strip().lower().lstrip("./")
        if not normalized:
            continue
        if normalized.startswith("tests/"):
            if module_path.endswith(normalized):
                return True
            continue
        if normalized.endswith(".py"):
            if module_path.endswith(normalized):
                return True
            continue
        if normalized in module_name.lower():
            return True
    return False


@dataclass
class FixtureDef:
    func: object
    autouse: bool = False


def load_fixture_functions(module):
    fixtures = {}
    autouse = []
    for name, value in vars(module).items():
        if callable(value) and getattr(value, "_pytest_fixture", False):
            fixture_kwargs = dict(getattr(value, "_pytest_fixture_kwargs", {}) or {})
            fixture_def = FixtureDef(func=value, autouse=bool(fixture_kwargs.get("autouse", False)))
            fixtures[name] = fixture_def
            if fixture_def.autouse:
                autouse.append(name)
    return fixtures, autouse


class MonkeyPatch:
    def __init__(self):
        self._undo = []

    def setenv(self, name, value):
        existed = name in os.environ
        previous = os.environ.get(name)
        os.environ[name] = str(value)

        def _restore():
            if existed:
                os.environ[name] = previous if previous is not None else ""
            else:
                os.environ.pop(name, None)

        self._undo.append(_restore)

    def delenv(self, name, raising=True):
        existed = name in os.environ
        if not existed:
            if raising:
                raise KeyError(name)
            return
        previous = os.environ.get(name)
        os.environ.pop(name, None)

        def _restore():
            if previous is not None:
                os.environ[name] = previous

        self._undo.append(_restore)

    def undo(self):
        while self._undo:
            self._undo.pop()()


class RequestNode:
    def __init__(self, module, func):
        self._module = module
        self._func = func

    def get_closest_marker(self, name):
        module_marks = getattr(self._module, "pytestmark", [])
        if not isinstance(module_marks, list):
            module_marks = [module_marks]
        for mark in list(getattr(self._func, "_pytest_marks", [])) + list(module_marks):
            mark_name = getattr(mark, "name", mark)
            if mark_name == name:
                return SimpleNamespace(name=name)
        return None


class FixtureRequest:
    def __init__(self, module, func):
        self.node = RequestNode(module, func)


def _finish_generator(generator):
    try:
        next(generator)
    except StopIteration:
        return
    raise RuntimeError("Fixture generator yielded more than once")


def resolve_fixture(name, fixture_pool, cache, teardown_stack, request_context):
    if name in cache:
        return cache[name]
    if name == "tmp_path":
        value = Path(tempfile.mkdtemp(prefix="pytest-tmp-"))
        cache[name] = value
        return value
    if name == "monkeypatch":
        value = MonkeyPatch()
        teardown_stack.append(value.undo)
        cache[name] = value
        return value
    if name == "request":
        value = FixtureRequest(request_context["module"], request_context["func"])
        cache[name] = value
        return value
    if name not in fixture_pool:
        raise KeyError(name)
    fixture_def = fixture_pool[name]
    fixture_func = fixture_def.func
    kwargs = {}
    for param_name in inspect.signature(fixture_func).parameters:
        kwargs[param_name] = resolve_fixture(param_name, fixture_pool, cache, teardown_stack, request_context)
    value = fixture_func(**kwargs)
    if inspect.isgenerator(value):
        generator = value
        value = next(generator)
        teardown_stack.append(lambda gen=generator: _finish_generator(gen))
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


def run_function(module, func_name, func, conftest_fixtures, conftest_autouse, *, keyword: str = ""):
    module_fixtures, module_autouse = load_fixture_functions(module)
    fixture_pool = {**conftest_fixtures, **module_fixtures}
    autouse_fixtures = []
    for name in list(conftest_autouse) + list(module_autouse):
        if name not in autouse_fixtures:
            autouse_fixtures.append(name)
    results = {"passed": 0, "failed": 0, "skipped": 0, "xfailed": 0, "errors": []}

    if keyword and keyword.lower() not in f"{module.__name__}.{func_name}".lower():
        return results

    for case in iter_cases(func):
        cache = {}
        kwargs = {}
        teardown_stack = []
        request_context = {"module": module, "func": func}
        try:
            for autouse_name in autouse_fixtures:
                resolve_fixture(autouse_name, fixture_pool, cache, teardown_stack, request_context)
            for param_name in inspect.signature(func).parameters:
                if param_name in case:
                    kwargs[param_name] = case[param_name]
                else:
                    kwargs[param_name] = resolve_fixture(param_name, fixture_pool, cache, teardown_stack, request_context)
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
        finally:
            while teardown_stack:
                try:
                    teardown_stack.pop()()
                except Exception as exc:  # pragma: no cover - teardown path
                    results["failed"] += 1
                    tb = traceback.format_exc()
                    results["errors"].append((module.__name__, f"{func_name}[teardown]", exc, tb))
                    print(f"FAIL {module.__name__}.{func_name}[teardown]: {exc}")
    return results


def _parse_cli_args(argv: list[str]) -> tuple[list[str], str]:
    path_filters: list[str] = []
    keyword = ""
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "-k" and index + 1 < len(argv):
            keyword = argv[index + 1]
            index += 2
            continue
        if arg in {"-m", "--maxfail"} and index + 1 < len(argv):
            index += 2
            continue
        if arg.startswith("-"):
            index += 1
            continue
        path_filters.append(arg)
        index += 1
    return path_filters, keyword


def main():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    path_filters, keyword = _parse_cli_args(sys.argv[1:])

    try:
        conftest = importlib.import_module("tests.conftest")
        conftest_fixtures, conftest_autouse = load_fixture_functions(conftest)
    except Exception:
        conftest_fixtures = {}
        conftest_autouse = []

    summary = {"passed": 0, "failed": 0, "skipped": 0, "xfailed": 0}
    errors = []

    for module_name in discover_test_modules(path_filters):
        module = importlib.import_module(module_name)
        for func_name, func in iter_test_functions(module):
            result = run_function(module, func_name, func, conftest_fixtures, conftest_autouse, keyword=keyword)
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
