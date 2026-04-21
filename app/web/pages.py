from __future__ import annotations

from app.web.page_case import render_case_detail
from app.web.page_home import render_home_page
from app.web.page_ops import render_ops_page
from app.web.page_report import render_report_page
from app.web.page_submission import (
    render_submission_detail,
    render_submissions_index,
)
from app.web.view_helpers import render_stylesheet


__all__ = [
    "render_case_detail",
    "render_home_page",
    "render_ops_page",
    "render_report_page",
    "render_stylesheet",
    "render_submission_detail",
    "render_submissions_index",
]
