# -*- coding: utf-8 -*-
"""Step 5: strict evidence audit and high/medium/review QA partition."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parent))
from strict_utils import CLEAN_PAIRS_DIR, QA_OUT, clean_text, extract_standards, read_jsonl, read_text, write_jsonl  # noqa: E402


ELEMENT_KEYWORDS = {
    "废水": ["废水", "污水", "生活污水", "生产废水", "清洗废水", "COD", "氨氮", "水污染物"],
    "废气": ["废气", "VOCs", "非甲烷总烃", "颗粒物", "粉尘", "臭气", "排气筒", "无组织"],
    "噪声": ["噪声", "厂界", "隔声", "减振", "昼间", "夜间", "GB12348"],
    "危废": ["危险废物", "危废", "废活性炭", "废机油", "HW", "GB18597"],
}

SUPPORT_TERMS = {
    "废水": ["化粪池", "隔油", "预处理", "污水处理", "市政污水管网", "纳管", "排入", "回用", "外委", "委托", "处理厂", "不外排"],
    "废气": ["收集", "治理", "活性炭", "喷淋", "催化燃烧", "UV", "布袋除尘", "排气筒", "高空排放", "密闭"],
    "噪声": ["隔声", "减振", "消声", "厂界", "达标", "昼间", "夜间"],
    "危废": ["暂存", "规范暂存", "危废暂存", "委托", "有资质", "转移联单", "GB18597"],
}

BAD_REPORT_EVIDENCE_MARKERS = [
    "三线一单",
    "生态环境分区管控",
    "准入清单",
    "目录",
    "附件清单",
    "附图",
    "附件",
    "建设项目基本情况",
    "项目概况",
    "从生态环境保护角度可行",
    "可行性结论",
    "综合结论",
    "评价结论",
]


def text_found(needle: str, haystack: str) -> bool:
    return bool(needle and needle.strip() in haystack)


def compact(text: str) -> str:
    return "".join(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", str(text))).lower()


def project_matches(project_name: str, report: str, approval: str) -> bool:
    if not project_name:
        return True
    key = compact(project_name)
    if len(key) < 8:
        return True
    slices = [key[:18], key[-18:], key[:12]]
    return any(s and s in compact(report) and s in compact(approval) for s in slices)


def contains_any(text: str, terms: list[str]) -> bool:
    return any(term and term in text for term in terms)


def standard_codes(qa: dict[str, Any]) -> list[str]:
    return [s.get("standard_code", "") for s in qa.get("standards_normalized", []) if s.get("standard_code")]


def standards_in_text(text: str) -> set[str]:
    return {s.get("standard_code", "") for s in extract_standards(text) if s.get("standard_code")}


def element_standards(element: str, answer: str) -> list[str]:
    codes = []
    for std in extract_standards(answer):
        code = std.get("standard_code", "")
        if element == "危废" and not code.startswith("GB18597-"):
            continue
        if element == "噪声" and not (code.startswith("GB12348-") or code.startswith("GB/T3096-")):
            continue
        if code and code not in codes:
            codes.append(code)
    return codes


def canonical_answer_terms(element: str, answer: str) -> list[str]:
    if element not in ELEMENT_KEYWORDS:
        return []
    standards = element_standards(element, answer)
    terms = [term for term in ELEMENT_KEYWORDS[element] + SUPPORT_TERMS[element] if term in answer]
    return list(dict.fromkeys(standards + terms))


def qa_id_element(qa_id: str) -> str:
    return qa_id.rsplit("_", 1)[-1] if "_" in qa_id else ""


def relevant_standards_in_scope(qa: dict[str, Any], answer: str) -> bool:
    codes = standard_codes(qa)
    if not codes:
        return False
    answer_codes = standards_in_text(answer)
    return all(code in answer_codes for code in codes)


def standard_alignment(codes: list[str], answer: str, approval_ev: str, report_ev: str) -> bool:
    if not codes:
        return False
    answer_codes = standards_in_text(answer)
    approval_codes = standards_in_text(approval_ev)
    report_codes = standards_in_text(report_ev)
    return all(code in answer_codes and code in approval_codes and code in report_codes for code in codes)


def support_overlap(element: str, answer: str, report_ev: str) -> list[str]:
    terms = SUPPORT_TERMS.get(element, [])
    return [term for term in terms if term in answer and term in report_ev]


def evidence_is_specific(element: str, report_ev: str) -> bool:
    if not report_ev:
        return False
    if any(marker in report_ev for marker in BAD_REPORT_EVIDENCE_MARKERS):
        return False
    return contains_any(report_ev, ELEMENT_KEYWORDS.get(element, []))


def answer_is_trimmed(answer: str) -> bool:
    body = answer.replace("批复要求：", "")
    if len(body) > 700:
        return False
    numbered_sections = len(re.findall(r"[一二三四五六七八九十]+、", body))
    return numbered_sections <= 1


def audit_one(qa: dict[str, Any]) -> tuple[str, list[str], int, dict[str, str]]:
    issues: list[str] = []
    pair_dir = CLEAN_PAIRS_DIR / qa.get("pair_id", "")
    if not pair_dir.exists():
        issues.append("pair_id_missing")
        return "review", issues, 0, {"level": "review", "reason": ";".join(issues)}

    report = read_text(pair_dir / "report.md")
    approval = read_text(pair_dir / "approval.md")
    meta = json.loads(read_text(pair_dir / "pair_metadata.json"))

    company = qa.get("company", "")
    project_name = qa.get("project_name", "")
    element = qa.get("element", "")
    answer = qa.get("answer", "")
    approval_ev = qa.get("approval_evidence", [{}])[0].get("text", "")
    report_ev = qa.get("report_evidence", [{}])[0].get("text", "")
    codes = standard_codes(qa)
    task_domain = qa.get("benchmark_metadata", {}).get("task_domain", "")
    id_element = qa_id_element(qa.get("qa_id", ""))
    canonical_terms = canonical_answer_terms(element, answer)
    canonical_codes = element_standards(element, answer)

    if meta.get("company") and meta.get("company") != company:
        issues.append("metadata_company_mismatch")
    if company and company not in approval:
        issues.append("company_in_approval_failed")
    if company and company not in report:
        issues.append("company_in_report_failed")
    if not project_matches(project_name, report, approval):
        issues.append("project_name_match_failed")

    if not text_found(approval_ev, clean_text(approval)):
        issues.append("approval_evidence_found_failed")
    if not text_found(report_ev, clean_text(report)):
        issues.append("report_evidence_found_failed")
    if not text_found(answer.replace("批复要求：", "").strip("。")[:80], clean_text(approval)):
        issues.append("answer_supported_by_approval_failed")
    if not answer_is_trimmed(answer):
        issues.append("answer_not_trimmed_to_element")

    if not id_element or id_element != element:
        issues.append("qa_id_element_mismatch")
    if task_domain != element:
        issues.append("task_domain_element_mismatch")
    if qa.get("answer_terms", []) != canonical_terms:
        issues.append("answer_terms_not_current_answer_element")
    if codes != canonical_codes:
        issues.append("standards_not_current_answer_element")
    if element == "噪声" and any(term in qa.get("answer_terms", []) for term in ELEMENT_KEYWORDS["危废"] + SUPPORT_TERMS["危废"]):
        issues.append("noise_contains_hazard_terms")
    if element == "危废" and task_domain == "噪声":
        issues.append("hazard_metadata_noise_mismatch")

    if element not in ELEMENT_KEYWORDS:
        issues.append("unsupported_element")
    else:
        if not contains_any(answer, ELEMENT_KEYWORDS[element]):
            issues.append("answer_element_missing")
        if not contains_any(approval_ev, ELEMENT_KEYWORDS[element]):
            issues.append("approval_element_missing")
        if not contains_any(report_ev, ELEMENT_KEYWORDS[element]):
            issues.append("report_element_missing")
        if not evidence_is_specific(element, report_ev):
            issues.append("report_evidence_not_specific_or_excluded")

    if not relevant_standards_in_scope(qa, answer):
        issues.append("standards_missing_or_out_of_answer_scope")
    if not standard_alignment(codes, answer, approval_ev, report_ev):
        issues.append("same_standard_alignment_failed")

    overlap = support_overlap(element, answer, report_ev)
    if not overlap:
        issues.append("same_destination_or_measure_failed")

    if not issues:
        return (
            "high",
            issues,
            100,
            {
                "level": "high",
                "reason": "同项目、同要素、同标准、同排放去向/治理措施，且 report evidence 具体支撑 answer",
            },
        )

    medium_blockers = {
        "pair_id_missing",
        "metadata_company_mismatch",
        "company_in_approval_failed",
        "approval_evidence_found_failed",
        "answer_supported_by_approval_failed",
        "answer_not_trimmed_to_element",
        "unsupported_element",
        "qa_id_element_mismatch",
        "task_domain_element_mismatch",
        "answer_terms_not_current_answer_element",
        "standards_not_current_answer_element",
        "noise_contains_hazard_terms",
        "hazard_metadata_noise_mismatch",
    }
    if not any(issue in medium_blockers for issue in issues) and evidence_is_specific(element, report_ev):
        return (
            "medium",
            issues,
            max(60, 100 - 8 * len(issues)),
            {"level": "medium", "reason": ";".join(issues)},
        )

    return "review", issues, max(20, 100 - 10 * len(issues)), {"level": "review", "reason": ";".join(issues)}


def main() -> None:
    qas = read_jsonl(QA_OUT / "qa_strict_all.jsonl")
    high, medium, review = [], [], []
    for qa in qas:
        status, issues, score, alignment = audit_one(qa)
        qa["quality_issues"] = issues
        qa["quality_score"] = score
        qa["evidence_alignment"] = alignment
        qa["need_human_review"] = status != "high"
        if status == "high":
            high.append(qa)
        elif status == "medium":
            medium.append(qa)
        else:
            review.append(qa)

    write_jsonl(qas, QA_OUT / "qa_strict_all.jsonl")
    write_jsonl(high, QA_OUT / "qa_strict_high.jsonl")
    write_jsonl(medium, QA_OUT / "qa_strict_medium.jsonl")
    write_jsonl(review, QA_OUT / "qa_strict_review.jsonl")

    # Backward-compatible names for existing reports; only high is considered verified now.
    write_jsonl(high, QA_OUT / "qa_strict_verified.jsonl")
    write_jsonl(medium + review, QA_OUT / "qa_strict_needs_review.jsonl")
    write_jsonl([], QA_OUT / "qa_strict_rejected.jsonl")

    print(f"high={len(high)} medium={len(medium)} review={len(review)}")


if __name__ == "__main__":
    main()
