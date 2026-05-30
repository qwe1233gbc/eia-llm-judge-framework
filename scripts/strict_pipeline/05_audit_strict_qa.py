# -*- coding: utf-8 -*-
"""Step 5: strict evidence audit for generated QA."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from strict_utils import CLEAN_PAIRS_DIR, QA_OUT, read_jsonl, read_text, write_jsonl  # noqa: E402


def text_found(needle: str, haystack: str) -> bool:
    if not needle:
        return False
    return needle.strip() in haystack


def audit_one(qa: dict) -> tuple[str, list[str], int, dict]:
    issues = []
    pair_dir = CLEAN_PAIRS_DIR / qa.get("pair_id", "")
    if not pair_dir.exists():
        issues.append("pair_id_missing")
        return "rejected", issues, 0, {"level": "invalid", "reason": ";".join(issues)}
    report = read_text(pair_dir / "report.md")
    approval = read_text(pair_dir / "approval.md")
    meta = json.loads(read_text(pair_dir / "pair_metadata.json"))

    company = qa.get("company", "")
    project_name = qa.get("project_name", "")
    element = qa.get("element", "")

    if company and company not in report:
        issues.append("company_in_report_failed")
    if company and company not in approval:
        issues.append("company_in_approval_failed")
    if project_name:
        project_key = project_name[: max(6, min(20, len(project_name)))]
        if project_key not in report or project_key not in approval:
            issues.append("project_name_match_failed")
    if meta.get("company") and meta.get("company") != company:
        issues.append("metadata_company_mismatch")

    approval_ev = qa.get("approval_evidence", [{}])[0].get("text", "")
    report_ev = qa.get("report_evidence", [{}])[0].get("text", "")
    answer = qa.get("answer", "")

    if not text_found(approval_ev, approval):
        issues.append("approval_evidence_found_failed")
    if not text_found(report_ev, report):
        issues.append("report_evidence_found_failed")
    if answer[:80] not in approval:
        issues.append("answer_supported_by_approval_failed")
    if element and element not in answer and element not in approval_ev:
        issues.append("element_match_failed")

    standards = qa.get("standards_normalized", [])
    if standards:
        if not any(s.get("standard_code", "") in answer for s in standards):
            issues.append("standard_match_failed")

    other_company_markers = ["有限公司", "公司", "厂"]
    if company and any(marker in approval_ev for marker in other_company_markers):
        if company not in approval_ev and len(approval_ev) > 80:
            issues.append("no_other_company_mixed_failed")

    if not issues:
        alignment = {"level": "high", "reason": "same pair, same element, evidence exists in both source files"}
        return "verified", issues, 100, alignment
    if "pair_id_missing" in issues or "company_in_report_failed" in issues or "company_in_approval_failed" in issues:
        return "rejected", issues, 0, {"level": "invalid", "reason": ";".join(issues)}
    return "needs_review", issues, max(40, 100 - 12 * len(issues)), {"level": "low", "reason": ";".join(issues)}


def main() -> None:
    qas = read_jsonl(QA_OUT / "qa_strict_all.jsonl")
    verified, needs_review, rejected = [], [], []
    for qa in qas:
        status, issues, score, alignment = audit_one(qa)
        qa["quality_issues"] = issues
        qa["quality_score"] = score
        qa["evidence_alignment"] = alignment
        qa["need_human_review"] = status != "verified"
        if status == "verified":
            verified.append(qa)
        elif status == "needs_review":
            needs_review.append(qa)
        else:
            rejected.append(qa)

    write_jsonl(qas, QA_OUT / "qa_strict_all.jsonl")
    write_jsonl(verified, QA_OUT / "qa_strict_verified.jsonl")
    write_jsonl(needs_review, QA_OUT / "qa_strict_needs_review.jsonl")
    write_jsonl(rejected, QA_OUT / "qa_strict_rejected.jsonl")
    print(f"verified={len(verified)} needs_review={len(needs_review)} rejected={len(rejected)}")


if __name__ == "__main__":
    main()
