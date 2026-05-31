# -*- coding: utf-8 -*-
"""Run the full strict clean-pairs pipeline and write the final report."""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from strict_utils import (  # noqa: E402
    PAIR_OUT,
    QA_OUT,
    RULE_OUT,
    SCAN_OUT,
    STRICT_OUT,
    ensure_dirs,
    read_jsonl,
)


SCRIPTS = [
    ("01_scan_and_classify_files.py", SCAN_OUT / "file_classification.jsonl"),
    ("02_extract_records.py", PAIR_OUT / "approval_records.jsonl"),
    ("03_match_clean_pairs.py", PAIR_OUT / "clean_pairs.jsonl"),
    ("04_generate_strict_qa.py", QA_OUT / "qa_strict_all.jsonl"),
    ("05_audit_strict_qa.py", QA_OUT / "qa_strict_high.jsonl"),
    ("06_build_experience_library_strict.py", RULE_OUT / "rules_all.json"),
]


def run_script(script_name: str) -> None:
    script = Path(__file__).resolve().parent / script_name
    print(f"\n=== running {script_name} ===", flush=True)
    subprocess.run([sys.executable, str(script)], check=True)


def run_script_if_needed(script_name: str, marker: Path) -> None:
    if marker.exists() and marker.stat().st_size > 0:
        print(f"skip {script_name}: found {marker}", flush=True)
        return
    run_script(script_name)


def count_jsonl(path: Path) -> int:
    return len(read_jsonl(path))


def count_rules(name: str) -> int:
    path = RULE_OUT / name
    if not path.exists():
        return 0
    return len(json.loads(path.read_text(encoding="utf-8")))


def count_lines_csv(path: Path) -> int:
    if not path.exists():
        return 0
    return max(0, len(path.read_text(encoding="utf-8-sig").splitlines()) - 1)


def format_counter(counter: Counter) -> str:
    if not counter:
        return "- none\n"
    return "".join(f"- {key or '未知'}: {value}\n" for key, value in sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def sample_qa_line(qa: dict) -> str:
    standards = ", ".join(s.get("standard_code", "") for s in qa.get("standards_normalized", []) if s.get("standard_code")) or "无"
    answer = qa.get("answer", "").replace("\n", " ")[:160].rstrip()
    issues = ", ".join(qa.get("quality_issues", [])) or "none"
    return (
        f"- {qa.get('qa_id', '')} | {qa.get('element', '')} | {qa.get('project_type', '')} | "
        f"standards: {standards} | issues: {issues} | {answer}\n"
    )


def write_final_report() -> None:
    classified = read_jsonl(SCAN_OUT / "file_classification.jsonl")
    clean_pairs = count_jsonl(PAIR_OUT / "clean_pairs.jsonl")
    high_qas = read_jsonl(QA_OUT / "qa_strict_high.jsonl")
    medium_qas = read_jsonl(QA_OUT / "qa_strict_medium.jsonl")
    review_qas = read_jsonl(QA_OUT / "qa_strict_review.jsonl")
    all_qas = read_jsonl(QA_OUT / "qa_strict_all.jsonl")
    downgraded = medium_qas + review_qas
    downgrade_reasons = Counter(issue for qa in downgraded for issue in qa.get("quality_issues", []))
    high_element_dist = Counter(qa.get("element", "") for qa in high_qas)
    high_project_type_dist = Counter(qa.get("project_type", "") for qa in high_qas)
    recommendation = (
        "建议进入经验库生成：仅使用 `qa_strict_high.jsonl`。"
        if high_qas and count_rules("rules_all.json") > 0
        else "不建议进入经验库生成：当前 high QA 或规则数量不足。"
    )

    counts = {
        "scanned": len(classified),
        "report": sum(1 for r in classified if r.get("detected_file_type") == "report"),
        "approval": sum(1 for r in classified if r.get("detected_file_type") == "approval"),
        "public_participation": sum(1 for r in classified if r.get("detected_file_type") == "public_participation"),
        "clean_pairs": clean_pairs,
        "candidate_pairs": count_lines_csv(PAIR_OUT / "candidate_pairs_needs_review.csv"),
        "mismatch_sample": count_lines_csv(PAIR_OUT / "mismatch_pairs.csv"),
        "qa_all": len(all_qas),
        "qa_high": len(high_qas),
        "qa_medium": len(medium_qas),
        "qa_review": len(review_qas),
        "rules_all": count_rules("rules_all.json"),
        "rules_a": count_rules("rules_A_verified.json"),
        "rules_b": count_rules("rules_B_candidate.json"),
        "rules_c": count_rules("rules_C_observation.json"),
    }

    md = [
        "# Final Strict Pipeline Report\n\n",
        "## 1. Why the old pipeline failed\n\n",
        "The old pipeline trusted sequence IDs such as P000x and file-name hints like report/approval. "
        "Those IDs were only ordinal labels, so report text, approval text, QA answers, and evidence could come from different projects.\n\n",
        "## 2. How this run avoids P000x mismatches\n\n",
        "This pipeline classifies files by body text, extracts project/company fields again, performs strict one-to-one record linkage, "
        "and generates QA only from `data/clean_pairs/`.\n\n",
        "## 3. Counts\n\n",
        f"1. scanned files: {counts['scanned']}\n",
        f"2. report files: {counts['report']}\n",
        f"3. approval files: {counts['approval']}\n",
        f"4. public_participation files: {counts['public_participation']}\n",
        f"5. clean_pairs: {counts['clean_pairs']}\n",
        f"6. candidate_pairs: {counts['candidate_pairs']}\n",
        f"7. unmatched/mismatch sampled: {counts['mismatch_sample']}\n",
        f"8. strict QA: {counts['qa_all']}\n",
        f"9. strict high QA: {counts['qa_high']}\n",
        f"10. strict medium QA: {counts['qa_medium']}\n",
        f"11. strict review QA: {counts['qa_review']}\n",
        f"12. strict experience rules from high QA: {counts['rules_all']}\n",
        f"13. A rules: {counts['rules_a']}\n",
        f"14. B rules: {counts['rules_b']}\n",
        f"15. C rules: {counts['rules_c']}\n",
        "\n## 4. High QA Element Distribution\n\n",
        format_counter(high_element_dist),
        "\n## 5. High QA Project Type Distribution\n\n",
        format_counter(high_project_type_dist),
        "\n## 6. Downgrade Reason Statistics\n\n",
        format_counter(downgrade_reasons),
        "\n## 7. Typical High QA Samples\n\n",
        "".join(sample_qa_line(qa) for qa in high_qas[:5]) or "- none\n",
        "\n## 8. Typical Downgraded Samples\n\n",
        "".join(sample_qa_line(qa) for qa in downgraded[:5]) or "- none\n",
        "\n## 9. Experience Library Recommendation\n\n",
        recommendation + "\n\n",
        "## 10. Remaining Manual Review\n\n",
        "Candidate pairs and QA outside `qa_strict_high.jsonl` remain outside the experience library and require manual review before use.\n\n",
        "## 11. Data Expansion\n\n",
        "Add more MinerU parsed reports and authoritative approval PDFs, then rerun this strict pipeline. "
        "Prefer more verified pairs over looser matching thresholds.\n",
    ]
    ensure_dirs(STRICT_OUT)
    (STRICT_OUT / "final_strict_pipeline_report.md").write_text("".join(md), encoding="utf-8")
    print(f"final_report={STRICT_OUT / 'final_strict_pipeline_report.md'}")


def main() -> None:
    for script, marker in SCRIPTS:
        run_script_if_needed(script, marker)
    write_final_report()


if __name__ == "__main__":
    main()
