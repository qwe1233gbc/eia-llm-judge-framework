# -*- coding: utf-8 -*-
"""Step 6: build strict experience rules from verified QA only."""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from strict_utils import QA_OUT, RULE_OUT, ensure_dirs, read_jsonl  # noqa: E402


def rule_level(support_count: int) -> str:
    if support_count >= 3:
        return "A"
    if support_count >= 2:
        return "B"
    return "C"


def main() -> None:
    ensure_dirs(RULE_OUT)
    qas = read_jsonl(QA_OUT / "qa_strict_verified.jsonl")
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for qa in qas:
        groups[(qa.get("industry_code", ""), qa.get("element", ""), qa.get("project_type", ""))].append(qa)

    rules = []
    for idx, ((industry, element, project_type), items) in enumerate(sorted(groups.items()), start=1):
        pair_ids = sorted({q["pair_id"] for q in items})
        standards = sorted(
            {
                s.get("standard_code", "")
                for q in items
                for s in q.get("standards_normalized", [])
                if s.get("standard_code")
            }
        )
        level = rule_level(len(pair_ids))
        rules.append(
            {
                "rule_id": f"STRICT_RULE_{idx:04d}",
                "industry_code": industry,
                "industry_name": "",
                "element": element,
                "project_type": project_type,
                "rule_status": {"A": "verified", "B": "candidate", "C": "observation"}[level],
                "evidence_level": level,
                "confidence": min(1.0, len(pair_ids) / 3) if level == "A" else min(0.7, len(pair_ids) / 3),
                "trigger_condition": [f"项目属于 {industry} 行业", f"项目涉及{element}审查事项"],
                "review_checkpoints": [
                    f"是否识别并说明{element}相关污染源或管理要求",
                    "是否引用与该要素对应的有效标准",
                    "报告内容是否能支撑批复中的审批要求",
                ],
                "expected_report_content": [f"{element}来源或管理对象", "治理/处置/管理措施", "执行标准", "排放去向或管理要求"],
                "common_approval_requirement": [q.get("answer", "")[:260] for q in items[:5]],
                "common_standards": standards[:12],
                "source_pair_ids": pair_ids,
                "source_qa_ids": [q.get("qa_id", "") for q in items[:20]],
                "support_count": len(pair_ids),
                "sample_counts": {"verified": len(items)},
                "limitations": [] if level == "A" else ["样本数不足，需人工复核后再作为稳定规则使用"],
                "need_human_review": level != "A",
            }
        )

    rules_a = [r for r in rules if r["evidence_level"] == "A"]
    rules_b = [r for r in rules if r["evidence_level"] == "B"]
    rules_c = [r for r in rules if r["evidence_level"] == "C"]

    for name, data in [
        ("rules_all.json", rules),
        ("rules_A_verified.json", rules_a),
        ("rules_B_candidate.json", rules_b),
        ("rules_C_observation.json", rules_c),
    ]:
        (RULE_OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    md = ["# Strict Experience Rules by Industry\n\n"]
    for rule in rules:
        md.append(f"## {rule['rule_id']} | {rule['industry_code']} | {rule['element']}\n\n")
        md.append(f"- level: {rule['evidence_level']}\n")
        md.append(f"- support_count: {rule['support_count']}\n")
        md.append(f"- standards: {', '.join(rule['common_standards'])}\n")
        md.append("- checkpoints:\n")
        for item in rule["review_checkpoints"]:
            md.append(f"  - {item}\n")
        md.append("\n")
    (RULE_OUT / "rules_by_industry.md").write_text("".join(md), encoding="utf-8")

    with (RULE_OUT / "neo4j_triples.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["head", "relation", "tail", "evidence", "source_type"])
        for rule in rules:
            writer.writerow([rule["industry_code"], "HAS_STRICT_RULE", rule["rule_id"], ",".join(rule["source_pair_ids"]), "rule"])
            writer.writerow([rule["rule_id"], "CHECKS_ELEMENT", rule["element"], ",".join(rule["source_pair_ids"]), "rule"])
            for standard in rule["common_standards"][:5]:
                writer.writerow([rule["rule_id"], "USES_STANDARD", standard, ",".join(rule["source_pair_ids"]), "rule"])

    print(f"rules_all={len(rules)} A={len(rules_a)} B={len(rules_b)} C={len(rules_c)}")


if __name__ == "__main__":
    main()
