from __future__ import annotations

from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.core.services.app_config import AppConfig, load_app_config
from app.core.services.runtime_store import store
from app.web.page_review_rule import render_global_rule_detail_page, render_review_rule_detail_page
from app.web.page_submission import (
    render_submission_exports_page,
    render_submission_materials_page,
    render_submission_operator_page,
)
from app.web.pages import (
    render_case_detail,
    render_home_page,
    render_ops_page,
    render_report_page,
    render_submission_detail,
    render_submissions_index,
)


OpsReportBuilder = Callable[[AppConfig], dict]
SubmissionContextLoader = Callable[[str], tuple[dict, list[dict], list[dict], list[dict], list[dict]]]
SubmissionNoticeBuilder = Callable[[str], dict | None]


def register_page_routes(
    app: FastAPI,
    *,
    build_ops_report: OpsReportBuilder,
    submission_context: SubmissionContextLoader,
    submission_notice_payload: SubmissionNoticeBuilder,
) -> None:
    @app.get("/")
    def home(request: Request):
        del request
        return HTMLResponse(render_home_page())

    @app.get("/submissions")
    def submission_index(request: Request):
        return HTMLResponse(render_submissions_index(dict(request.query_params or {})))

    @app.get("/ops")
    def ops_page(request: Request):
        config = load_app_config()
        return HTMLResponse(render_ops_page(config.to_dict(), build_ops_report(config), dict(request.query_params or {})))

    @app.get("/submissions/{submission_id}")
    def submission_detail(request: Request, submission_id: str):
        submission, materials, cases, reports, parse_results = submission_context(submission_id)
        notice = submission_notice_payload(request.query_params.get("notice", ""))
        return HTMLResponse(render_submission_detail(submission, materials, cases, reports, parse_results, notice=notice))

    @app.get("/submissions/{submission_id}/materials")
    def submission_materials_page(request: Request, submission_id: str):
        del request
        submission, materials, cases, reports, parse_results = submission_context(submission_id)
        return HTMLResponse(render_submission_materials_page(submission, materials, cases, reports, parse_results))

    @app.get("/submissions/{submission_id}/operator")
    def submission_operator_page(request: Request, submission_id: str):
        del request
        submission, materials, cases, reports, parse_results = submission_context(submission_id)
        return HTMLResponse(render_submission_operator_page(submission, materials, cases, reports, parse_results))

    @app.get("/submissions/{submission_id}/exports")
    def submission_exports_page(request: Request, submission_id: str):
        del request
        submission, materials, cases, reports, parse_results = submission_context(submission_id)
        return HTMLResponse(render_submission_exports_page(submission, materials, cases, reports, parse_results))

    @app.get("/submissions/{submission_id}/review-rules/{dimension_key}")
    def submission_review_rule_page(request: Request, submission_id: str, dimension_key: str):
        selected_case_id = str(request.query_params.get("case_id", "") or "").strip()
        submission, materials, cases, reports, parse_results = submission_context(submission_id)
        del materials, reports, parse_results
        try:
            return HTMLResponse(
                render_review_rule_detail_page(
                    submission,
                    cases,
                    dimension_key,
                    selected_case_id=selected_case_id,
                )
            )
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/global-rules/{dimension_key}")
    def global_rule_detail(request: Request, dimension_key: str):
        del request
        return HTMLResponse(render_global_rule_detail_page(dimension_key))

    @app.get("/cases/{case_id}")
    def case_detail(request: Request, case_id: str):
        del request
        case = store.cases.get(case_id)
        if not case:
            raise HTTPException(404, "未找到项目")
        materials = [store.materials[item_id].to_dict() for item_id in case.material_ids if item_id in store.materials]
        report = store.report_artifacts.get(case.report_id)
        review_result = store.review_results.get(case.review_result_id)
        return HTMLResponse(
            render_case_detail(
                case.to_dict(),
                materials,
                report.to_dict() if report else None,
                review_result.to_dict() if review_result else None,
            )
        )

    @app.get("/reports/{report_id}")
    def report_page(request: Request, report_id: str):
        del request
        report = store.report_artifacts.get(report_id)
        if not report:
            raise HTTPException(404, "未找到报告")
        return HTMLResponse(render_report_page(report.to_dict()))
