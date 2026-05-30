# -*- coding: utf-8 -*-
"""Step 2: extract normalized report and approval records from classified files."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from strict_utils import (  # noqa: E402
    PAIR_OUT,
    SCAN_OUT,
    clean_text,
    ensure_dirs,
    extract_company,
    extract_date,
    extract_doc_no,
    extract_industry_code,
    extract_pdf_text,
    extract_project_name,
    extract_project_type,
    extract_report_type,
    extract_town,
    extract_year,
    first_match,
    read_jsonl,
    read_text,
    write_csv,
    write_jsonl,
)


REPORT_FIELDS = [
    "report_id",
    "source_file",
    "source_md",
    "detected_file_type",
    "project_name",
    "company",
    "construction_unit",
    "industry_code",
    "industry_name",
    "project_type",
    "report_type",
    "town",
    "construction_location",
    "year",
    "parse_status",
    "evidence_text",
]

APPROVAL_FIELDS = [
    "approval_id",
    "source_file",
    "source_md",
    "detected_file_type",
    "approval_title",
    "approval_doc_no",
    "approval_date",
    "project_name",
    "company",
    "report_type_referenced",
    "approval_mode",
    "approval_authority",
    "parse_status",
    "evidence_text",
]


def load_body(source_file: str) -> str:
    path = Path(source_file)
    if path.suffix.lower() == ".pdf":
        return extract_pdf_text(path, max_pages=6)
    return read_text(path)


def extract_construction_location(text: str) -> str:
    return first_match(
        [
            r"(?:建设地点|建设地址|项目地址|项目所在地)\s*[:：]\s*([^\n\r]{4,120})",
            r"选址(?:位于|为)\s*([^\n\r，。；;]{4,120})",
        ],
        text,
    )


def extract_approval_title(text: str) -> str:
    for line in text.splitlines()[:30]:
        if "关于" in line and ("批复" in line or "环境影响报告" in line):
            return line.strip()
    return first_match([r"(佛山市生态环境局关于[^\n\r]{8,160})"], text)


def extract_approval_mode(text: str) -> str:
    head = text[:8000]
    if "承诺制" in head or "告知承诺" in head:
        return "承诺制"
    if "形式审查" in head:
        return "形式审查"
    return "普通批复"


def extract_approval_authority(text: str) -> str:
    return first_match([r"((?:佛山市|[\u4e00-\u9fff]{2,8})生态环境局[\u4e00-\u9fff分局]*)"], text)


def main() -> None:
    ensure_dirs(PAIR_OUT)
    classified = read_jsonl(SCAN_OUT / "file_classification.jsonl")
    report_rows = []
    approval_rows = []

    for row in classified:
        file_type = row.get("detected_file_type")
        if file_type not in {"report", "approval"}:
            continue
        text = load_body(row["source_file"])
        compact = clean_text(text)
        if file_type == "report":
            company = extract_company(text)
            project_name = extract_project_name(text)
            report_rows.append(
                {
                    "report_id": f"R{len(report_rows) + 1:05d}",
                    "source_file": row["source_file"],
                    "source_md": row.get("source_md", ""),
                    "detected_file_type": file_type,
                    "project_name": project_name,
                    "company": company,
                    "construction_unit": company,
                    "industry_code": extract_industry_code(text),
                    "industry_name": "",
                    "project_type": extract_project_type(text),
                    "report_type": extract_report_type(text),
                    "town": extract_town(text),
                    "construction_location": extract_construction_location(text),
                    "year": extract_year(text, row["source_file"]),
                    "parse_status": row.get("parse_status", ""),
                    "evidence_text": compact[:800],
                }
            )
        elif file_type == "approval":
            title = extract_approval_title(text)
            approval_rows.append(
                {
                    "approval_id": f"A{len(approval_rows) + 1:05d}",
                    "source_file": row["source_file"],
                    "source_md": row.get("source_md", ""),
                    "detected_file_type": file_type,
                    "approval_title": title,
                    "approval_doc_no": extract_doc_no(text, row["source_file"]),
                    "approval_date": extract_date(text, row["source_file"]),
                    "project_name": extract_project_name(title + "\n" + text[:6000]),
                    "company": extract_company(title + "\n" + text[:6000]),
                    "report_type_referenced": extract_report_type(text),
                    "approval_mode": extract_approval_mode(text),
                    "approval_authority": extract_approval_authority(text),
                    "parse_status": row.get("parse_status", ""),
                    "evidence_text": compact[:800],
                }
            )

    write_csv(report_rows, PAIR_OUT / "report_records.csv", REPORT_FIELDS)
    write_jsonl(report_rows, PAIR_OUT / "report_records.jsonl")
    write_csv(approval_rows, PAIR_OUT / "approval_records.csv", APPROVAL_FIELDS)
    write_jsonl(approval_rows, PAIR_OUT / "approval_records.jsonl")
    print(f"report_records={len(report_rows)} approval_records={len(approval_rows)}")


if __name__ == "__main__":
    main()
