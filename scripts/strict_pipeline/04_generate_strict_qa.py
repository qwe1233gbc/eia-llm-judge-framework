# -*- coding: utf-8 -*-
"""Step 4: generate QA only from strict clean pairs."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from strict_utils import (  # noqa: E402
    CLEAN_PAIRS_DIR,
    QA_OUT,
    clean_text,
    ensure_dirs,
    extract_standards,
    find_evidence,
    load_pair_text,
    write_jsonl,
)


ELEMENT_PATTERNS = {
    "废水": ["废水", "生活污水", "生产废水", "水污染物", "COD", "氨氮"],
    "废气": ["废气", "大气污染物", "VOCs", "非甲烷总烃", "颗粒物", "粉尘", "臭气"],
    "噪声": ["噪声", "厂界噪声", "工业企业厂界环境噪声"],
    "固废": ["固体废物", "一般工业固体废物", "固废"],
    "危废": ["危险废物", "危废", "废活性炭", "废机油"],
    "环境风险": ["环境风险", "风险防范", "应急预案"],
    "总量控制": ["总量控制", "总量指标", "污染物总量"],
    "排污许可": ["排污许可", "排污登记"],
    "验收": ["竣工环境保护验收", "环保验收"],
    "重大变动": ["重大变动", "重新报批"],
    "承诺制": ["承诺制", "承诺事项"],
}


def split_approval_clauses(text: str) -> list[str]:
    compact = clean_text(text)
    parts = []
    for part in __import__("re").split(r"(?:(?:^|[。；;])\s*(?:\d+|[一二三四五六七八九十])\s*[、.．])", compact):
        part = part.strip()
        if 40 <= len(part) <= 1200:
            parts.append(part)
    if not parts:
        parts = [p.strip() for p in compact.split("。") if 40 <= len(p.strip()) <= 800]
    return parts[:80]


def detect_element(text: str) -> str:
    scores = {element: sum(1 for kw in kws if kw in text) for element, kws in ELEMENT_PATTERNS.items()}
    element, score = max(scores.items(), key=lambda item: item[1])
    return element if score > 0 else "其他"


def build_question(meta: dict, element: str) -> str:
    company = meta.get("company", "")[:24]
    industry = meta.get("industry_code", "")
    project_type = meta.get("project_type", "")
    return f"【区级】{company}（{industry} {project_type}项目）{element}方面的审批要求、执行标准和报告支撑内容是什么？"


def metadata_for_element(element: str) -> dict:
    if element in {"废水", "废气", "噪声", "固废", "危废"}:
        question_type = "extraction"
        difficulty = "simple"
        cognitive = "L1_fact"
    elif element in {"总量控制", "排污许可", "验收", "重大变动", "承诺制"}:
        question_type = "reasoning"
        difficulty = "medium"
        cognitive = "L2_alignment"
    else:
        question_type = "evaluation"
        difficulty = "medium"
        cognitive = "L3_review_reasoning"
    return {
        "task_domain": element,
        "difficulty": difficulty,
        "question_type": question_type,
        "cognitive_level": cognitive,
        "evaluation_dimensions": ["professionalism", "clarity", "feasibility", "evidence_grounding"],
    }


def main() -> None:
    ensure_dirs(QA_OUT)
    qas = []
    for pair_dir in sorted(CLEAN_PAIRS_DIR.glob("pair_*")):
        report_text, approval_text, meta = load_pair_text(pair_dir)
        clauses = split_approval_clauses(approval_text)
        for idx, clause in enumerate(clauses, start=1):
            element = detect_element(clause)
            if element == "其他":
                continue
            terms = ELEMENT_PATTERNS.get(element, []) + [s["standard_code"] for s in extract_standards(clause)]
            report_ev = find_evidence(report_text, terms)
            approval_ev = find_evidence(approval_text, [clause[:80]] + terms)
            standards = extract_standards(clause)
            for std in standards:
                std["source"] = "approval"
            qa = {
                "qa_id": f"QA_{pair_dir.name}_{idx:03d}",
                "pair_id": pair_dir.name,
                "level": "区级",
                "region": "佛山市顺德区",
                "company": meta.get("company", ""),
                "project_name": meta.get("project_name", ""),
                "industry_code": meta.get("industry_code", ""),
                "industry_name": meta.get("industry_name", ""),
                "project_type": meta.get("project_type", ""),
                "report_type": meta.get("report_type", ""),
                "element": element,
                "review_point": "审批要求与报告支撑核查",
                "question": build_question(meta, element),
                "answer": clause,
                "standards_normalized": standards,
                "approval_evidence": [
                    {
                        "source_file": "approval.md",
                        "text": approval_ev["text"] if approval_ev else clause[:260],
                        "char_start": approval_ev["char_start"] if approval_ev else -1,
                        "char_end": approval_ev["char_end"] if approval_ev else -1,
                    }
                ],
                "report_evidence": [
                    {
                        "source_file": "report.md",
                        "section": "body",
                        "text": report_ev["text"] if report_ev else "",
                        "char_start": report_ev["char_start"] if report_ev else -1,
                        "char_end": report_ev["char_end"] if report_ev else -1,
                    }
                ],
                "evidence_alignment": {"level": "pending", "reason": "generated before strict audit"},
                "benchmark_metadata": metadata_for_element(element),
                "quality_score": 0,
                "quality_issues": [],
                "need_human_review": True,
            }
            qas.append(qa)

    write_jsonl(qas, QA_OUT / "qa_strict_all.jsonl")
    report = ["# Strict QA Generation Report\n\n", f"- qa_strict_all: {len(qas)}\n", "- source: data/clean_pairs only\n"]
    (QA_OUT.parent.parent / "outputs" / "strict_pipeline" / "qa_generation").mkdir(parents=True, exist_ok=True)
    (QA_OUT.parent.parent / "outputs" / "strict_pipeline" / "qa_generation" / "qa_generation_report.md").write_text(
        "".join(report), encoding="utf-8"
    )
    print(f"qa_strict_all={len(qas)}")


if __name__ == "__main__":
    main()
