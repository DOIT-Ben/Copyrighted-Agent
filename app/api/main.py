from __future__ import annotations

from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, make_server

from fastapi import FastAPI

from app.api.routes import register_routes
from app.api.security import configure_security
from app.api.startup import prepare_runtime
from app.core.services.app_config import load_app_config


def create_app(testing: bool = False):
    prepare_runtime(testing=testing)
    app = FastAPI(title="软著分析平台")
    configure_security(app, testing=testing)

    register_routes(app)

    return app


class _ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def main():
    app = create_app()
    config = load_app_config()
    host = config.host
    port = config.port
    with make_server(host, port, app, server_class=_ThreadingWSGIServer) as server:
        print(f"软著分析平台运行中: http://{host}:{port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
