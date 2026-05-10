from __future__ import annotations

from typing import Callable
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.services.app_logging import log_event
from app.core.services.corrections import (
    rerun_case_review,
    reset_submission_review_dimension_rule,
    update_submission_review_dimension_rule,
)
from app.core.services.review_profile import (
    _load_global_review_profile,
    _normalize_rulebook_meta,
    normalize_review_profile,
    parse_review_profile_form,
    save_global_review_profile,
)
from app.core.services.review_rulebook import dimension_rulebook_from_profile, parse_dimension_rule_items_from_form


SubmissionNoticeLocationBuilder = Callable[[str, str], str]


def register_rule_routes(app: FastAPI, *, submission_notice_location: Callable[..., str]) -> None:
    @app.post("/api/global-rules")
    def api_save_global_rules(request: Request):
        try:
            profile = parse_review_profile_form(request.form_data)
            save_global_review_profile(profile)
            log_event("global_review_profile_saved", {"preset_key": profile.get("preset_key"), "enabled_dimensions": profile.get("enabled_dimensions")})
            return JSONResponse({"success": True, "message": "规则配置已保存"})
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/submissions/{submission_id}/review-rules/{dimension_key}")
    def submission_review_rule_save(request: Request, submission_id: str, dimension_key: str):
        action = str(request.form_data.get("action", "save") or "save").strip()
        case_id = str(request.form_data.get("case_id", "") or "").strip()
        note = str(request.form_data.get("note", "") or "").strip()
        corrected_by = str(request.form_data.get("corrected_by", "operator_ui") or "operator_ui").strip()
        try:
            if action == "restore_default":
                result = reset_submission_review_dimension_rule(
                    submission_id,
                    dimension_key,
                    corrected_by=corrected_by,
                    note=note,
                )
            else:
                result = update_submission_review_dimension_rule(
                    submission_id,
                    dimension_key,
                    title=str(request.form_data.get("title", "") or "").strip(),
                    objective=str(request.form_data.get("objective", "") or "").strip(),
                    checkpoints=str(request.form_data.get("checkpoints", "") or "").strip(),
                    evidence_targets=str(request.form_data.get("evidence_targets", "") or "").strip(),
                    common_failures=str(request.form_data.get("common_failures", "") or "").strip(),
                    operator_notes=str(request.form_data.get("operator_notes", "") or "").strip(),
                    llm_focus=str(request.form_data.get("llm_focus", "") or "").strip(),
                    rules=parse_dimension_rule_items_from_form(request.form_data, dimension_key),
                    corrected_by=corrected_by,
                    note=note,
                )
            if action == "save_and_rerun" and case_id:
                rerun_case_review(
                    case_id,
                    corrected_by=corrected_by,
                    note=note or f"rule_update:{dimension_key}",
                    review_profile=result["review_profile"],
                )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        log_event(
            "submission_review_rule_saved_html",
            {
                "submission_id": submission_id,
                "dimension_key": dimension_key,
                "action": action,
                "case_id": case_id,
                "by": corrected_by,
            },
        )
        if action == "save_and_rerun" and case_id:
            return RedirectResponse(submission_notice_location(submission_id, "case_review_rerun", focus="review-profile"), status_code=303)
        return RedirectResponse(f"/submissions/{submission_id}/review-rules/{dimension_key}?case_id={quote(case_id)}", status_code=303)

    @app.post("/api/global-rules/{dimension_key}")
    def api_save_global_dimension_rule(request: Request, dimension_key: str):
        try:
            global_profile = _load_global_review_profile() or {}
            profile = normalize_review_profile(global_profile)
            rulebook = dimension_rulebook_from_profile(profile)
            if dimension_key not in rulebook:
                raise HTTPException(404, "维度不存在")

            rule_entry = dict(rulebook[dimension_key])
            rules = parse_dimension_rule_items_from_form(request.form_data, dimension_key)
            rule_entry["rules"] = rules

            profile["dimension_rulebook"] = {**profile.get("dimension_rulebook", {}), dimension_key: rule_entry}
            profile["rulebook_meta"] = _normalize_rulebook_meta(profile, preset_key=profile.get("preset_key", "balanced_default"))

            save_global_review_profile(profile)
            log_event("global_dimension_rule_saved", {"dimension_key": dimension_key})
            return JSONResponse({"success": True, "message": "规则已保存"})
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
