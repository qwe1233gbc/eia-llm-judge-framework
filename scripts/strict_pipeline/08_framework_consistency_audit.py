# -*- coding: utf-8 -*-
"""Audit framework consistency across strict pipeline code, data, outputs, and docs.

This script is read-only with respect to strict QA and experience-library inputs: it
does not regenerate QA, pairs, or rules. It only writes audit artifacts under
outputs/framework_audit/.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CLEAN_PAIRS_DIR = REPO_ROOT / "data" / "clean_pairs"
QA_DIR = REPO_ROOT / "data" / "qa_strict"
STRICT_OUT = REPO_ROOT / "outputs" / "strict_pipeline"
RULE_OUT = REPO_ROOT / "outputs" / "experience_library_strict"
APPROVAL_ISSUE_OUT = REPO_ROOT / "outputs" / "approval_issue_analysis"
AUDIT_OUT = REPO_ROOT / "outputs" / "framework_audit"
README = REPO_ROOT / "README.md"
DOCS_DIR = REPO_ROOT / "docs"


def load_generator_module():
    path = REPO_ROOT / "scripts" / "strict_pipeline" / "04_generate_strict_qa.py"
    spec = importlib.util.spec_from_file_location("strict_qa_generator", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


GEN = load_generator_module()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def read_json(path: Path) -> Any:
    return json.loads(read_text(path))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in read_text(path).splitlines() if line.strip()]


def write_csv(rows: list[dict[str, Any]], path: Path, fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def count_jsonl(path: Path) -> int:
    return len(read_jsonl(path))


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def standards_in_text(text: str) -> list[str]:
    return [s["standard_code"] for s in GEN.extract_standards(text)]


def qa_blob(qa: dict[str, Any]) -> str:
    parts = [
        qa.get("qa_id", ""),
        qa.get("element", ""),
        qa.get("question", ""),
        qa.get("answer", ""),
        qa.get("benchmark_metadata", {}).get("task_domain", ""),
        " ".join(qa.get("answer_terms", [])),
        " ".join(s.get("standard_code", "") for s in qa.get("standards_normalized", [])),
    ]
    parts.extend(ev.get("text", "") for ev in qa.get("approval_evidence", []) + qa.get("report_evidence", []))
    return " ".join(str(part) for part in parts)


def check_clean_pairs() -> tuple[list[dict[str, Any]], dict[str, int]]:
    errors: list[dict[str, Any]] = []
    pair_dirs = sorted(CLEAN_PAIRS_DIR.glob("pair_*"))
    report_sources: defaultdict[str, list[str]] = defaultdict(list)
    approval_sources: defaultdict[str, list[str]] = defaultdict(list)

    for pair_dir in pair_dirs:
        pair_id = pair_dir.name
        required_files = ["report.md", "approval.md", "pair_metadata.json"]
        for name in required_files:
            if not (pair_dir / name).exists() or (pair_dir / name).stat().st_size == 0:
                errors.append({"pair_id": pair_id, "error_type": "missing_or_empty_file", "field": name, "detail": str(pair_dir / name)})

        meta_path = pair_dir / "pair_metadata.json"
        if not meta_path.exists():
            continue
        try:
            meta = read_json(meta_path)
        except Exception as exc:
            errors.append({"pair_id": pair_id, "error_type": "metadata_parse_error", "field": "pair_metadata.json", "detail": str(exc)})
            continue

        for field in ["company", "project_name", "report_source", "approval_source"]:
            if not str(meta.get(field, "")).strip():
                errors.append({"pair_id": pair_id, "error_type": "metadata_required_field_empty", "field": field, "detail": "required by framework audit"})

        report_source = str(meta.get("report_source") or meta.get("report_file_original") or "").strip()
        approval_source = str(meta.get("approval_source") or meta.get("approval_file_original") or "").strip()
        if report_source:
            report_sources[report_source].append(pair_id)
        if approval_source:
            approval_sources[approval_source].append(pair_id)

    for source, pair_ids in report_sources.items():
        if len(pair_ids) > 1:
            errors.append({"pair_id": ";".join(pair_ids), "error_type": "duplicate_report_source", "field": "report_source", "detail": source})
    for source, pair_ids in approval_sources.items():
        if len(pair_ids) > 1:
            errors.append({"pair_id": ";".join(pair_ids), "error_type": "duplicate_approval_source", "field": "approval_source", "detail": source})

    return errors, {"clean_pairs": len(pair_dirs)}


def qa_id_element(qa_id: str) -> str:
    return qa_id.rsplit("_", 1)[-1] if "_" in qa_id else ""


def check_qa_high() -> tuple[list[dict[str, Any]], dict[str, int]]:
    errors: list[dict[str, Any]] = []
    qas = read_jsonl(QA_DIR / "qa_strict_high.jsonl")
    old_refs = ["qa_v3", "qa_v4"]
    water_bad = ["GB12348", "GB/T3096", "GB18597", "GB31572", "GB14554", "GB41616", "DB44/27", "DB44/2367", "DB44/815"]

    for qa in qas:
        qa_id = qa.get("qa_id", "")
        pair_id = qa.get("pair_id", "")
        element = qa.get("element", "")
        task_domain = qa.get("benchmark_metadata", {}).get("task_domain", "")
        answer = qa.get("answer", "")
        blob = qa_blob(qa)
        blob_compact = compact(blob)
        pair_dir = CLEAN_PAIRS_DIR / pair_id
        report = clean_text(read_text(pair_dir / "report.md"))
        approval = clean_text(read_text(pair_dir / "approval.md"))

        def add(error_type: str, detail: str = "") -> None:
            errors.append({"qa_id": qa_id, "pair_id": pair_id, "element": element, "error_type": error_type, "detail": detail})

        if qa_id_element(qa_id) != element:
            add("qa_id_element_mismatch", f"qa_id_element={qa_id_element(qa_id)}")
        if task_domain != element:
            add("task_domain_element_mismatch", f"task_domain={task_domain}")

        if element not in GEN.ELEMENTS:
            add("unknown_element", element)
            continue
        expected_terms = GEN.answer_terms(element, answer)
        if qa.get("answer_terms", []) != expected_terms:
            add("answer_terms_not_current_answer_element", f"actual={qa.get('answer_terms', [])}; expected={expected_terms}")

        expected_standards = [s["standard_code"] for s in GEN.element_standards(element, answer)]
        actual_standards = [s.get("standard_code", "") for s in qa.get("standards_normalized", []) if s.get("standard_code")]
        if actual_standards != expected_standards:
            add("standards_not_current_answer_element", f"actual={actual_standards}; expected={expected_standards}")

        if element == "废水" and any(marker in blob_compact for marker in water_bad):
            add("wastewater_contains_cross_element_standard")
        if element == "噪声" and any(marker in blob_compact for marker in ["DB44/26", "污水", "危废", "危险废物", "GB18597"]):
            add("noise_contains_forbidden_water_or_hazard_marker")
        if element == "危废" and any(marker in blob_compact for marker in ["GB12348", "厂界噪声", "环境噪声"]):
            add("hazard_contains_forbidden_noise_marker")

        for ev in qa.get("approval_evidence", []):
            ev_text = clean_text(ev.get("text", ""))
            if not ev_text or ev_text not in approval:
                add("approval_evidence_not_found", ev_text[:120])
        for ev in qa.get("report_evidence", []):
            ev_text = clean_text(ev.get("text", ""))
            if not ev_text or ev_text not in report:
                add("report_evidence_not_found", ev_text[:120])

        if any(ref in blob for ref in old_refs):
            add("references_old_qa_dataset", "qa_v3/qa_v4 reference found")

    return errors, {"qa_strict_high": len(qas)}


def check_experience_library() -> tuple[list[dict[str, Any]], dict[str, int]]:
    errors: list[dict[str, Any]] = []
    high_ids = {row.get("qa_id", "") for row in read_jsonl(QA_DIR / "qa_strict_high.jsonl")}
    rules = read_json(RULE_OUT / "rules_all.json") if (RULE_OUT / "rules_all.json").exists() else []
    rules_a = read_json(RULE_OUT / "rules_A_verified.json") if (RULE_OUT / "rules_A_verified.json").exists() else []
    rules_md = read_text(RULE_OUT / "rules_by_industry.md")

    for rule in rules:
        for qa_id in rule.get("source_qa_ids", []):
            if qa_id not in high_ids:
                errors.append({"rule_id": rule.get("rule_id", ""), "error_type": "source_qa_id_not_in_qa_strict_high", "field": "source_qa_ids", "detail": qa_id})
    for rule in rules_a:
        if not str(rule.get("industry_code", "")).strip():
            errors.append({"rule_id": rule.get("rule_id", ""), "error_type": "A_rule_empty_industry_code", "field": "industry_code", "detail": "A-level rule has empty industry_code"})
    if not rules_md.strip() or "STRICT_RULE_" not in rules_md:
        errors.append({"rule_id": "", "error_type": "rules_by_industry_not_readable", "field": "rules_by_industry.md", "detail": "empty or no rule markers"})

    script = read_text(REPO_ROOT / "scripts" / "strict_pipeline" / "06_build_experience_library_strict.py")
    if 'qa_strict_high.jsonl' not in script:
        errors.append({"rule_id": "", "error_type": "builder_not_using_qa_strict_high", "field": "06_build_experience_library_strict.py", "detail": "qa_strict_high.jsonl not referenced"})

    return errors, {"experience_rules_all": len(rules), "A_rules": len(rules_a)}


def parse_report_counts() -> dict[str, int]:
    report = read_text(STRICT_OUT / "final_strict_pipeline_report.md")
    patterns = {
        "clean_pairs": r"clean_pairs:\s*(\d+)",
        "qa_strict_all": r"strict QA:\s*(\d+)",
        "qa_strict_high": r"strict high QA:\s*(\d+)",
        "qa_strict_medium": r"strict medium QA:\s*(\d+)",
        "qa_strict_review": r"strict review QA:\s*(\d+)",
        "experience_rules_all": r"strict experience rules from high QA:\s*(\d+)",
        "A_rules": r"A rules:\s*(\d+)",
    }
    counts = {}
    for key, pattern in patterns.items():
        m = re.search(pattern, report)
        if m:
            counts[key] = int(m.group(1))
    return counts


def check_report_and_readme(actual_counts: dict[str, int]) -> tuple[list[dict[str, Any]], bool, bool]:
    errors: list[dict[str, Any]] = []
    report_counts = parse_report_counts()
    for key, actual in actual_counts.items():
        if key in report_counts and report_counts[key] != actual:
            errors.append({"artifact": "final_strict_pipeline_report.md", "error_type": "report_count_mismatch", "field": key, "actual": actual, "reported": report_counts[key]})

    readme = read_text(README)
    readme_outdated = "Strict Clean-Pairs Pipeline" not in readme or "qa_v4" not in readme or "历史版本" not in readme
    docs_need_strict = not any("strict" in p.name.lower() and "pipeline" in read_text(p) for p in DOCS_DIR.rglob("*.md"))
    if readme_outdated:
        errors.append({"artifact": "README.md", "error_type": "README_outdated", "field": "Strict Clean-Pairs Pipeline", "actual": 0, "reported": 1})
    if docs_need_strict:
        errors.append({"artifact": "docs/", "error_type": "docs_missing_strict_pipeline_data_notes", "field": "strict_pipeline", "actual": 0, "reported": 1})
    return errors, readme_outdated, docs_need_strict


def check_scripts() -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    gen_script = read_text(REPO_ROOT / "scripts" / "strict_pipeline" / "04_generate_strict_qa.py")
    if "CLEAN_PAIRS_DIR" not in gen_script or "load_pair_text(pair_dir)" not in gen_script:
        errors.append({"artifact": "04_generate_strict_qa.py", "error_type": "qa_generator_not_clearly_clean_pairs_only", "detail": "missing CLEAN_PAIRS_DIR or load_pair_text(pair_dir)"})
    if "qa_v3" in gen_script or "qa_v4" in gen_script:
        errors.append({"artifact": "04_generate_strict_qa.py", "error_type": "qa_generator_references_old_qa", "detail": "qa_v3/qa_v4 reference found"})
    return errors


def make_readme_suggestion(readme_outdated: bool, docs_need_strict: bool, problem_counts: dict[str, int]) -> str:
    lines = [
        "# README / Docs Update Suggestion\n\n",
        f"- README_outdated: {readme_outdated}\n",
        f"- docs_need_strict_pipeline_notes: {docs_need_strict}\n",
        "\n## Suggested README section\n\n",
        "Add or keep a `## Strict Clean-Pairs Pipeline` section that explains:\n\n",
        "- The legacy `qa_v3/qa_v4` datasets are historical versions.\n",
        "- The current mainline uses `data/clean_pairs` as the trusted data entry point.\n",
        "- `qa_strict_high` is the high-confidence benchmark candidate set.\n",
        "- `qa_strict_medium` is a manual-review candidate set.\n",
        "- `qa_strict_review` contains downgraded or unresolved samples.\n",
        "- `outputs/experience_library_strict` must be generated only from `qa_strict_high`.\n",
        "\n## Current audit warning counts\n\n",
    ]
    for key, value in problem_counts.items():
        lines.append(f"- {key}: {value}\n")
    return "".join(lines)


def write_report(summary: dict[str, int], problem_counts: dict[str, int], readme_outdated: bool) -> None:
    lines = [
        "# Framework Consistency Report\n\n",
        "This audit reads existing strict pipeline artifacts only. It does not regenerate QA, clean pairs, or experience rules.\n\n",
        "## Counts\n\n",
    ]
    for key in [
        "clean_pairs",
        "qa_strict_all",
        "qa_strict_high",
        "qa_strict_medium",
        "qa_strict_review",
        "experience_rules_all",
        "A_rules",
    ]:
        lines.append(f"- {key}: {summary.get(key, 0)}\n")
    lines.extend(
        [
            "\n## Error Counts\n\n",
            f"- clean_pair_errors: {problem_counts.get('clean_pair_errors', 0)}\n",
            f"- qa_high_field_errors: {problem_counts.get('qa_high_field_errors', 0)}\n",
            f"- experience_library_errors: {problem_counts.get('experience_library_errors', 0)}\n",
            f"- report_count_mismatch: {problem_counts.get('report_count_mismatch', 0)}\n",
            f"- README_outdated: {readme_outdated}\n",
            "\n## Key Findings\n\n",
        ]
    )
    if problem_counts.get("qa_high_field_errors", 0):
        lines.append("- Some `qa_strict_high` samples still fail field/evidence/element checks. Recommendation: downgrade inconsistent samples to `qa_strict_review`, regenerate the high/medium/review partitions, rebuild the high-only experience library, and update the final report.\n")
    else:
        lines.append("- `qa_strict_high` passes the implemented field, element, standard, and evidence-location checks.\n")
    if problem_counts.get("clean_pair_errors", 0):
        lines.append("- `clean_pairs` has metadata or uniqueness issues. Pay special attention to source field naming and duplicate report/approval sources.\n")
    if problem_counts.get("experience_library_errors", 0):
        lines.append("- `experience_library_strict` has source or A-level rule consistency issues. Do not treat these rules as final until fixed.\n")
    if readme_outdated:
        lines.append("- `README.md` still needs strict pipeline orientation or legacy-version clarification.\n")
    lines.append("\n## Outputs\n\nSee `outputs/framework_audit/*.csv` for row-level details.\n")
    (AUDIT_OUT / "framework_consistency_report.md").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    AUDIT_OUT.mkdir(parents=True, exist_ok=True)

    clean_errors, clean_counts = check_clean_pairs()
    qa_errors, qa_counts = check_qa_high()
    exp_errors, exp_counts = check_experience_library()

    actual_counts = {
        **clean_counts,
        "qa_strict_all": count_jsonl(QA_DIR / "qa_strict_all.jsonl"),
        **qa_counts,
        "qa_strict_medium": count_jsonl(QA_DIR / "qa_strict_medium.jsonl"),
        "qa_strict_review": count_jsonl(QA_DIR / "qa_strict_review.jsonl"),
        **exp_counts,
    }
    report_readme_errors, readme_outdated, docs_need_strict = check_report_and_readme(actual_counts)
    script_errors = check_scripts()

    report_count_mismatch = sum(1 for row in report_readme_errors if row.get("error_type") == "report_count_mismatch")
    problem_counts = {
        "clean_pair_errors": len(clean_errors),
        "qa_high_field_errors": len(qa_errors),
        "experience_library_errors": len(exp_errors),
        "report_count_mismatch": report_count_mismatch,
        "README_outdated": int(readme_outdated),
        "docs_need_strict_pipeline_notes": int(docs_need_strict),
        "script_errors": len(script_errors),
    }

    write_csv(clean_errors, AUDIT_OUT / "clean_pair_errors.csv", ["pair_id", "error_type", "field", "detail"])
    write_csv(qa_errors, AUDIT_OUT / "qa_strict_high_field_errors.csv", ["qa_id", "pair_id", "element", "error_type", "detail"])
    write_csv(exp_errors, AUDIT_OUT / "experience_library_errors.csv", ["rule_id", "error_type", "field", "detail"])

    summary_rows = []
    for key, value in {**actual_counts, **problem_counts}.items():
        is_problem_metric = key.endswith("errors") or key.endswith("mismatch") or key in {"README_outdated", "docs_need_strict_pipeline_notes"}
        status = "error" if is_problem_metric and value else ("ok" if is_problem_metric else "info")
        summary_rows.append({"check_name": key, "value": value, "status": status})
    for row in report_readme_errors:
        summary_rows.append({"check_name": row.get("error_type", ""), "value": 1, "status": "error"})
    for row in script_errors:
        summary_rows.append({"check_name": row.get("error_type", ""), "value": 1, "status": "error"})
    write_csv(summary_rows, AUDIT_OUT / "framework_consistency_summary.csv", ["check_name", "value", "status"])

    (AUDIT_OUT / "readme_update_suggestion.md").write_text(
        make_readme_suggestion(readme_outdated, docs_need_strict, problem_counts), encoding="utf-8"
    )
    write_report(actual_counts, problem_counts, readme_outdated)

    print("Framework consistency audit finished.")
    print()
    print(f"clean_pairs: {actual_counts['clean_pairs']}")
    print(f"qa_strict_all: {actual_counts['qa_strict_all']}")
    print(f"qa_strict_high: {actual_counts['qa_strict_high']}")
    print(f"qa_strict_medium: {actual_counts['qa_strict_medium']}")
    print(f"qa_strict_review: {actual_counts['qa_strict_review']}")
    print(f"experience_rules_all: {actual_counts['experience_rules_all']}")
    print(f"A_rules: {actual_counts['A_rules']}")
    print()
    print("errors:")
    print(f"- clean_pair_errors: {problem_counts['clean_pair_errors']}")
    print(f"- qa_high_field_errors: {problem_counts['qa_high_field_errors']}")
    print(f"- experience_library_errors: {problem_counts['experience_library_errors']}")
    print(f"- report_count_mismatch: {problem_counts['report_count_mismatch']}")
    print(f"- README_outdated: {bool(problem_counts['README_outdated'])}")
    print()
    print("outputs:")
    print("outputs/framework_audit/")


if __name__ == "__main__":
    main()
