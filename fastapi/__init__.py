from __future__ import annotations

import cgi
import inspect
import io
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs

from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass
class UploadFile:
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"

    def read(self) -> bytes:
        return self.content


@dataclass
class Request:
    method: str
    path: str
    headers: dict
    query_params: dict
    form_data: dict
    files: dict
    app: "FastAPI"


class _Route:
    def __init__(self, method: str, path: str, endpoint):
        self.method = method.upper()
        self.path = path
        self.endpoint = endpoint
        self.parts = [part for part in path.strip("/").split("/") if part]

    def match(self, method: str, path: str):
        if method.upper() != self.method:
            return None
        target_parts = [part for part in path.strip("/").split("/") if part]
        if len(target_parts) != len(self.parts):
            if not self.parts and not target_parts:
                return {}
            return None
        params = {}
        for route_part, target_part in zip(self.parts, target_parts):
            if route_part.startswith("{") and route_part.endswith("}"):
                params[route_part[1:-1]] = target_part
                continue
            if route_part != target_part:
                return None
        return params


class FastAPI:
    def __init__(self, title: str = "App"):
        self.title = title
        self.routes: list[_Route] = []
        self.before_request_hooks = []
        self.after_response_hooks = []

    def add_before_request_hook(self, hook):
        self.before_request_hooks.append(hook)

    def add_after_response_hook(self, hook):
        self.after_response_hooks.append(hook)

    def add_api_route(self, path: str, endpoint, methods: list[str]):
        for method in methods:
            self.routes.append(_Route(method, path, endpoint))

    def get(self, path: str):
        def decorator(endpoint):
            self.add_api_route(path, endpoint, ["GET"])
            return endpoint

        return decorator

    def post(self, path: str):
        def decorator(endpoint):
            self.add_api_route(path, endpoint, ["POST"])
            return endpoint

        return decorator

    def _find_route(self, method: str, path: str):
        for route in self.routes:
            params = route.match(method, path)
            if params is not None:
                return route, params
        return None, None

    def _invoke(self, endpoint, request: Request, path_params: dict):
        signature = inspect.signature(endpoint)
        kwargs = {}
        for name in signature.parameters:
            if name == "request":
                kwargs[name] = request
            elif name in path_params:
                kwargs[name] = path_params[name]
        return endpoint(**kwargs)

    def handle_request(
        self,
        method: str,
        path: str,
        headers: dict | None = None,
        form_data: dict | None = None,
        files: dict | None = None,
        body: bytes | None = None,
    ):
        headers = headers or {}
        query_params = {}
        if "?" in path:
            path, query_string = path.split("?", 1)
            query_params = {key: values[-1] for key, values in parse_qs(query_string).items()}
        route, path_params = self._find_route(method, path)
        if route is None:
            return PlainTextResponse("Not Found", status_code=404)
        request = Request(
            method=method.upper(),
            path=path,
            headers=headers,
            query_params=query_params,
            form_data=form_data or {},
            files=files or {},
            app=self,
        )
        for hook in self.before_request_hooks:
            hook_response = hook(request)
            if isinstance(hook_response, Response):
                for after_hook in self.after_response_hooks:
                    hook_response = after_hook(request, hook_response)
                return hook_response
        try:
            result = self._invoke(route.endpoint, request, path_params or {})
        except HTTPException as exc:
            response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        except Exception as exc:
            response = PlainTextResponse(f"Internal Server Error\n{exc}", status_code=500)
        else:
            if isinstance(result, Response):
                response = result
            elif isinstance(result, dict):
                response = JSONResponse(result)
            elif isinstance(result, str):
                response = HTMLResponse(result)
            else:
                response = PlainTextResponse(str(result))

        for hook in self.after_response_hooks:
            response = hook(request, response)
        return response

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")
        query_string = environ.get("QUERY_STRING", "")
        if query_string:
            path = f"{path}?{query_string}"
        headers = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").title()
                headers[header_name] = value

        form_data = {}
        files = {}
        content_type = environ.get("CONTENT_TYPE", "")
        if method.upper() == "POST":
            if "multipart/form-data" in content_type:
                field_storage = cgi.FieldStorage(fp=environ["wsgi.input"], environ=environ, keep_blank_values=True)
                if field_storage.list:
                    for item in field_storage.list:
                        if item.filename:
                            files[item.name] = UploadFile(
                                filename=item.filename,
                                content=item.file.read(),
                                content_type=item.type or "application/octet-stream",
                            )
                        else:
                            form_data[item.name] = item.value
            else:
                size = int(environ.get("CONTENT_LENGTH", "0") or "0")
                body = environ["wsgi.input"].read(size) if size else b""
                parsed = parse_qs(body.decode("utf-8", errors="ignore"))
                form_data = {key: values[-1] for key, values in parsed.items()}

        response = self.handle_request(method, path, headers=headers, form_data=form_data, files=files)
        status_text = {
            200: "200 OK",
            201: "201 Created",
            202: "202 Accepted",
            302: "302 Found",
            303: "303 See Other",
            400: "400 Bad Request",
            403: "403 Forbidden",
            404: "404 Not Found",
            415: "415 Unsupported Media Type",
            422: "422 Unprocessable Entity",
            500: "500 Internal Server Error",
        }.get(response.status_code, f"{response.status_code} OK")
        response_headers = [("Content-Type", getattr(response, "media_type", "text/plain; charset=utf-8"))]
        for key, value in response.headers.items():
            response_headers.append((key, value))
        start_response(status_text, response_headers)
        return [response.body]


__all__ = [
    "FastAPI",
    "HTTPException",
    "HTMLResponse",
    "JSONResponse",
    "PlainTextResponse",
    "RedirectResponse",
    "Request",
    "Response",
    "UploadFile",
]
