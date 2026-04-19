from __future__ import annotations

import importlib


class SkipTest(Exception):
    pass


class XFailed(Exception):
    pass


class RaisesContext:
    def __init__(self, expected_exception):
        self.expected_exception = expected_exception
        self.caught = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            raise AssertionError(f"Expected exception {self.expected_exception!r} was not raised")
        if not issubclass(exc_type, self.expected_exception):
            return False
        self.caught = exc
        return True


def raises(expected_exception):
    return RaisesContext(expected_exception)


def fixture(func=None, **_kwargs):
    def decorator(target):
        target._pytest_fixture = True
        return target

    if func is not None:
        return decorator(func)
    return decorator


def importorskip(module_name: str):
    try:
        return importlib.import_module(module_name)
    except Exception as exc:
        raise SkipTest(f"Skipped because {module_name} could not be imported: {exc}")


def skip(reason: str = ""):
    raise SkipTest(reason)


def xfail(reason: str = ""):
    raise XFailed(reason)


def fail(message: str = ""):
    raise AssertionError(message)


class _MarkNamespace:
    def __getattr__(self, name):
        if name == "parametrize":
            return self.parametrize

        def decorator(target):
            marks = getattr(target, "_pytest_marks", [])
            marks.append(name)
            target._pytest_marks = marks
            return target

        return decorator

    def parametrize(self, arg_names, arg_values):
        if isinstance(arg_names, str):
            names = [name.strip() for name in arg_names.split(",") if name.strip()]
        else:
            names = list(arg_names)

        def decorator(target):
            target._pytest_parametrize = (names, list(arg_values))
            return target

        return decorator


mark = _MarkNamespace()

