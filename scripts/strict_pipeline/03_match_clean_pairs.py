# -*- coding: utf-8 -*-
"""Step 3: strict one-to-one report-approval record linkage."""
from __future__ import annotations

import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz

sys.path.append(str(Path(__file__).resolve().parent))
from strict_utils import (  # noqa: E402
    CLEAN_PAIRS_DIR,
    PAIR_OUT,
    clean_text,
    ensure_dirs,
    extract_pdf_text,
    normalize_for_match,
    read_jsonl,
    read_text,
    write_csv,
    write_jsonl,
)


PAIR_FIELDS = [
    "pair_id",
    "report_id",
    "approval_id",
    "report_file",
    "report_company",
    "report_project_name",
    "approval_file",
    "approval_company",
    "approval_project_name",
    "company_similarity",
    "project_name_similarity",
    "report_type_match",
    "project_type_match",
    "town_or_location_match",
    "date_order_valid",
    "match_score",
    "pair_status",
    "warnings",
]


def sim(a: str, b: str) -> float:
    aa = normalize_for_match(a)
    bb = normalize_for_match(b)
    if not aa or not bb:
        return 0.0
    if aa == bb:
        return 100.0
    return float(max(fuzz.token_sort_ratio(aa, bb), fuzz.partial_ratio(aa, bb)))


def company_block_key(company: str) -> str:
    key = normalize_for_match(company)
    for prefix in ("佛山市顺德区", "佛山市", "广东省", "广东", "顺德区"):
        key = key.replace(normalize_for_match(prefix), "")
    for suffix in ("有限公司", "有限责任公司", "公司", "厂", "经营部", "分公司"):
        key = key.replace(normalize_for_match(suffix), "")
    return key[:4]


def exact_or_empty(a: str, b: str) -> float:
    if not a or not b:
        return 50.0
    return 100.0 if str(a).strip() == str(b).strip() else 0.0


def date_order_valid(report_year: str, approval_date: str) -> float:
    if not report_year or not approval_date:
        return 50.0
    try:
        return 100.0 if int(str(report_year)[:4]) <= int(str(approval_date)[:4]) else 0.0
    except ValueError:
        return 50.0


def hard_reject(report: dict, approval: dict, c_sim: float, p_sim: float) -> list[str]:
    reasons = []
    if report.get("detected_file_type") != "report":
        reasons.append("report_detected_file_type_not_report")
    if approval.get("detected_file_type") != "approval":
        reasons.append("approval_detected_file_type_not_approval")
    if c_sim < 92:
        reasons.append("company_not_strict_match")
    if p_sim < 65:
        reasons.append("project_name_not_strict_match")
    if report.get("report_type") and approval.get("report_type_referenced"):
        if report["report_type"] != approval["report_type_referenced"]:
            reasons.append("report_type_mismatch")
    title_blob = approval.get("approval_title", "") + approval.get("evidence_text", "") + approval.get("project_name", "")
    if report.get("project_type") and report["project_type"] not in title_blob:
        reasons.append("project_type_not_found_in_approval")
    return reasons


def load_body(source_file: str) -> str:
    path = Path(source_file)
    if path.suffix.lower() == ".pdf":
        return extract_pdf_text(path, max_pages=30)
    return read_text(path)


def copy_pair(pair: dict, report: dict, approval: dict) -> None:
    pair_dir = CLEAN_PAIRS_DIR / pair["pair_id"]
    ensure_dirs(pair_dir)
    report_text = clean_text(load_body(report["source_file"]))
    approval_text = clean_text(load_body(approval["source_file"]))
    (pair_dir / "report.md").write_text(report_text, encoding="utf-8")
    (pair_dir / "approval.md").write_text(approval_text, encoding="utf-8")
    if Path(approval["source_file"]).suffix.lower() == ".pdf":
        try:
            shutil.copy2(approval["source_file"], pair_dir / "approval.pdf")
        except OSError:
            pass
    metadata = {
        "pair_id": pair["pair_id"],
        "match_score": pair["match_score"],
        "company": report.get("company", ""),
        "project_name": report.get("project_name", ""),
        "industry_code": report.get("industry_code", ""),
        "industry_name": report.get("industry_name", ""),
        "project_type": report.get("project_type", ""),
        "report_type": report.get("report_type", ""),
        "report_file_original": report.get("source_file", ""),
        "approval_file_original": approval.get("source_file", ""),
        "approval_doc_no": approval.get("approval_doc_no", ""),
        "approval_date": approval.get("approval_date", ""),
        "match_basis": [
            f"company_similarity={pair['company_similarity']}",
            f"project_name_similarity={pair['project_name_similarity']}",
            f"match_score={pair['match_score']}",
        ],
        "warnings": pair.get("warnings", "").split(";") if pair.get("warnings") else [],
    }
    (pair_dir / "pair_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    ensure_dirs(PAIR_OUT, CLEAN_PAIRS_DIR)
    reports = read_jsonl(PAIR_OUT / "report_records.jsonl")
    approvals = read_jsonl(PAIR_OUT / "approval_records.jsonl")
    approvals_by_idx = {i: row for i, row in enumerate(approvals)}
    blocks: dict[str, list[int]] = defaultdict(list)
    for ai, approval in approvals_by_idx.items():
        key = company_block_key(approval.get("company", ""))
        if key:
            blocks[key].append(ai)

    candidates = []
    for ri, report in enumerate(reports, start=1):
        if not report.get("company") or not report.get("project_name"):
            continue
        if ri % 100 == 0:
            print(f"matching reports {ri}/{len(reports)} candidates={len(candidates)}", flush=True)
        key = company_block_key(report.get("company", ""))
        search_indices = blocks.get(key, [])
        if not search_indices:
            search_indices = list(approvals_by_idx)
        for ai in search_indices:
            approval = approvals_by_idx[ai]
            if not approval.get("company") or not approval.get("project_name"):
                continue
            c_sim = sim(report.get("company", ""), approval.get("company", ""))
            if c_sim < 70:
                continue
            p_sim = sim(report.get("project_name", ""), approval.get("project_name", ""))
            if p_sim < 45:
                continue
            rt = exact_or_empty(report.get("report_type", ""), approval.get("report_type_referenced", ""))
            approval_blob = approval.get("approval_title", "") + approval.get("evidence_text", "") + approval.get("project_name", "")
            pt = 100.0 if report.get("project_type") and report["project_type"] in approval_blob else 50.0
            town = 100.0 if report.get("town") and report.get("town") in approval.get("evidence_text", "") else 50.0
            date = date_order_valid(report.get("year", ""), approval.get("approval_date", ""))
            score = c_sim * 0.40 + p_sim * 0.35 + rt * 0.10 + pt * 0.05 + town * 0.05 + date * 0.05
            rejects = hard_reject(report, approval, c_sim, p_sim)
            candidates.append((score, report, approval, ai, c_sim, p_sim, rt, pt, town, date, rejects))

    candidates.sort(key=lambda x: x[0], reverse=True)
    used_reports: set[str] = set()
    used_approvals: set[str] = set()
    clean_pairs = []
    review_pairs = []
    mismatches = []

    for score, report, approval, _ai, c_sim, p_sim, rt, pt, town, date, rejects in candidates:
        if report["report_id"] in used_reports or approval["approval_id"] in used_approvals:
            continue
        pair_status = "mismatch"
        if score >= 90 and not rejects:
            pair_status = "clean"
        elif score >= 80:
            pair_status = "candidate_pair_needs_review"
        row = {
            "pair_id": f"pair_{len(clean_pairs) + len(review_pairs) + len(mismatches) + 1:05d}",
            "report_id": report["report_id"],
            "approval_id": approval["approval_id"],
            "report_file": report["source_file"],
            "report_company": report.get("company", ""),
            "report_project_name": report.get("project_name", ""),
            "approval_file": approval["source_file"],
            "approval_company": approval.get("company", ""),
            "approval_project_name": approval.get("project_name", ""),
            "company_similarity": round(c_sim, 1),
            "project_name_similarity": round(p_sim, 1),
            "report_type_match": round(rt, 1),
            "project_type_match": round(pt, 1),
            "town_or_location_match": round(town, 1),
            "date_order_valid": round(date, 1),
            "match_score": round(score, 1),
            "pair_status": pair_status,
            "warnings": ";".join(rejects),
        }
        if pair_status == "clean":
            used_reports.add(report["report_id"])
            used_approvals.add(approval["approval_id"])
            row["pair_id"] = f"pair_{len(clean_pairs) + 1:05d}"
            clean_pairs.append(row)
            copy_pair(row, report, approval)
        elif pair_status == "candidate_pair_needs_review":
            review_pairs.append(row)
        else:
            mismatches.append(row)

    clean_report_ids = {p["report_id"] for p in clean_pairs}
    clean_approval_ids = {p["approval_id"] for p in clean_pairs}
    unmatched_reports = [r for r in reports if r["report_id"] not in clean_report_ids]
    unmatched_approvals = [a for a in approvals if a["approval_id"] not in clean_approval_ids]

    write_csv(clean_pairs, PAIR_OUT / "clean_pairs.csv", PAIR_FIELDS)
    write_jsonl(clean_pairs, PAIR_OUT / "clean_pairs.jsonl")
    write_csv(review_pairs, PAIR_OUT / "candidate_pairs_needs_review.csv", PAIR_FIELDS)
    write_csv(mismatches[:1000], PAIR_OUT / "mismatch_pairs.csv", PAIR_FIELDS)
    write_csv(unmatched_reports, PAIR_OUT / "unmatched_reports.csv")
    write_csv(unmatched_approvals, PAIR_OUT / "unmatched_approvals.csv")

    report = [
        "# Strict Pair Cleaning Report\n\n",
        f"- reports: {len(reports)}\n",
        f"- approvals: {len(approvals)}\n",
        f"- clean_pairs: {len(clean_pairs)}\n",
        f"- candidate_pairs_needs_review: {len(review_pairs)}\n",
        f"- mismatches_sampled: {len(mismatches[:1000])}\n",
        f"- unmatched_reports: {len(unmatched_reports)}\n",
        f"- unmatched_approvals: {len(unmatched_approvals)}\n",
        "\nClean pairs require score >= 90 and strict company/project/type checks.\n",
    ]
    (PAIR_OUT / "pair_cleaning_report.md").write_text("".join(report), encoding="utf-8")
    print(f"clean_pairs={len(clean_pairs)} candidate_pairs={len(review_pairs)} mismatches={len(mismatches)}")


if __name__ == "__main__":
    main()
