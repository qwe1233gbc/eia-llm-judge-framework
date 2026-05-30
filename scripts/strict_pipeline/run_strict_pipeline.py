# -*- coding: utf-8 -*-
"""Run the full strict clean-pairs pipeline and write the final report."""
from __future__ import annotations

import json
import subprocess
import sys
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
    ("05_audit_strict_qa.py", QA_OUT / "qa_strict_verified.jsonl"),
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


def write_final_report() -> None:
    classified = read_jsonl(SCAN_OUT / "file_classification.jsonl")
    clean_pairs = count_jsonl(PAIR_OUT / "clean_pairs.jsonl")
    candidate_pairs = 0
    cand_csv = PAIR_OUT / "candidate_pairs_needs_review.csv"
    if cand_csv.exists():
        candidate_pairs = max(0, len(cand_csv.read_text(encoding="utf-8-sig").splitlines()) - 1)
    mismatch = 0
    mismatch_csv = PAIR_OUT / "mismatch_pairs.csv"
    if mismatch_csv.exists():
        mismatch = max(0, len(mismatch_csv.read_text(encoding="utf-8-sig").splitlines()) - 1)

    counts = {
        "scanned": len(classified),
        "report": sum(1 for r in classified if r.get("detected_file_type") == "report"),
        "approval": sum(1 for r in classified if r.get("detected_file_type") == "approval"),
        "public_participation": sum(1 for r in classified if r.get("detected_file_type") == "public_participation"),
        "clean_pairs": clean_pairs,
        "candidate_pairs": candidate_pairs,
        "mismatch_sample": mismatch,
        "qa_all": count_jsonl(QA_OUT / "qa_strict_all.jsonl"),
        "qa_verified": count_jsonl(QA_OUT / "qa_strict_verified.jsonl"),
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
        f"9. strict verified QA: {counts['qa_verified']}\n",
        f"10. strict experience rules: {counts['rules_all']}\n",
        f"11. A rules: {counts['rules_a']}\n",
        f"12. B rules: {counts['rules_b']}\n",
        f"13. C rules: {counts['rules_c']}\n",
        "\n## 4. Remaining manual review\n\n",
        "Candidate pairs and QA with low evidence alignment remain outside verified outputs and require manual review before use.\n\n",
        "## 5. Data expansion\n\n",
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
