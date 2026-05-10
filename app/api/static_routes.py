from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import Response

from app.web.pages import render_app_script, render_stylesheet


def register_static_routes(app: FastAPI) -> None:
    @app.get("/static/styles.css")
    def styles(request: Request):
        del request
        response = Response(render_stylesheet(), status_code=200, headers={"Cache-Control": "public, max-age=86400"})
        response.media_type = "text/css; charset=utf-8"
        return response

    @app.get("/static/app.js")
    def app_js(request: Request):
        del request
        response = Response(render_app_script(), status_code=200, headers={"Cache-Control": "public, max-age=86400"})
        response.media_type = "application/javascript; charset=utf-8"
        return response
