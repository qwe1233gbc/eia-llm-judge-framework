# -*- coding: utf-8 -*-
"""Step 4: generate trimmed, element-specific QA only from strict clean pairs."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parent))
from strict_utils import (  # noqa: E402
    CLEAN_PAIRS_DIR,
    QA_OUT,
    clean_text,
    ensure_dirs,
    extract_standards,
    load_pair_text,
    write_jsonl,
)


ELEMENTS = {
    "废水": {
        "keywords": ["废水", "污水", "生活污水", "生产废水", "清洗废水", "喷淋废水", "COD", "氨氮", "水污染物"],
        "support": ["化粪池", "隔油", "预处理", "污水处理", "市政污水管网", "纳管", "排入", "回用", "外委", "委托", "处理厂", "不外排"],
        "question": "该项目废水的来源、处理方式、执行标准和排放去向是什么？",
    },
    "废气": {
        "keywords": ["废气", "VOCs", "非甲烷总烃", "颗粒物", "粉尘", "臭气", "喷漆", "烘干", "焊接烟尘", "排气筒", "无组织"],
        "support": ["收集", "治理", "活性炭", "喷淋", "催化燃烧", "UV", "布袋除尘", "排气筒", "高空排放", "密闭"],
        "question": "该项目废气涉及哪些工序、污染因子、治理设施、排气筒和废气标准？",
    },
    "噪声": {
        "keywords": ["噪声", "厂界", "隔声", "减振", "消声", "昼间", "夜间", "GB12348"],
        "support": ["隔声", "减振", "消声", "厂界", "达标", "昼间", "夜间"],
        "question": "该项目厂界噪声执行什么标准，批复要求采取哪些降噪措施？",
    },
    "危废": {
        "keywords": ["危险废物", "危废", "废活性炭", "废机油", "HW", "GB18597"],
        "support": ["暂存", "规范暂存", "危废暂存", "委托", "有资质", "转移联单", "GB18597"],
        "question": "该项目危险废物如何暂存和委托处置，是否执行 GB18597？",
    },
}

EXCLUDED_REPORT_EVIDENCE_MARKERS = [
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


def split_sentences(text: str) -> list[str]:
    compact = clean_text(text)
    compact = re.sub(r"(。|；|;)\s*(项目|本项目|其|其中)", r"\1\n\2", compact)
    compact = re.sub(r"\s+(项目|本项目)(?=(?:生活污水|生产废水|废水|废气|VOCs|噪声|危险废物|危废))", r"\n\1", compact)
    chunks = re.split(r"[\n。；;]+", compact)
    return [chunk.strip(" ，,。；;") for chunk in chunks if 12 <= len(chunk.strip()) <= 900]


def contains_any(text: str, terms: list[str]) -> bool:
    return any(term and term in text for term in terms)


def remove_non_hazard_standards(text: str) -> str:
    text = re.sub(r"[，,、]?[《〈][^》〉]{0,60}(?:一般工业固体废物|固体废物贮存|固体废物污染)[^》〉]*[》〉][（(]GB18599-\d{4}[）)]", "", text)
    text = re.sub(r"[，,、]?以及[《〈]关于发布[《〈]一般工业[^。；;]*GB18599-\d{4}[^。；;]*", "", text)
    text = re.sub(r"[，,、]?GB18599-\d{4}", "", text)
    return text.strip(" ，,、。；;")


def focus_sentence(sentence: str, keywords: list[str], limit: int = 280) -> str:
    if len(sentence) <= limit:
        return sentence
    positions = [sentence.find(kw) for kw in keywords if sentence.find(kw) >= 0]
    if not positions:
        return sentence[:limit].rstrip()
    pos = min(positions)
    start = max(0, pos - 80)
    end = min(len(sentence), start + limit)
    if end - start < limit:
        start = max(0, end - limit)
    focused = sentence[start:end].strip(" ，,。；;")
    if start > 0:
        focused = "..." + focused
    if end < len(sentence):
        focused += "..."
    return focused


def focus_element_sentence(element: str, sentence: str) -> str:
    if element != "危废":
        return focus_sentence(sentence, ELEMENTS[element]["keywords"] + ELEMENTS[element]["support"])
    snippets = []
    for anchor in ["GB18597", "危险废物", "危废", "委托", "有资质", "废活性炭", "废机油"]:
        pos = sentence.find(anchor)
        if pos < 0:
            continue
        start = max(0, pos - 70)
        end = min(len(sentence), pos + 150)
        snippet = sentence[start:end].strip(" ，,。；;")
        snippet = remove_non_hazard_standards(snippet)
        if snippet and snippet not in snippets:
            snippets.append(snippet)
        if "GB18597" in "。".join(snippets) and ("委托" in "。".join(snippets) or "有资质" in "。".join(snippets)):
            break
    if not snippets:
        return remove_non_hazard_standards(focus_sentence(sentence, ELEMENTS[element]["keywords"] + ELEMENTS[element]["support"]))
    return "。".join(snippets)


def element_relevant_sentence(element: str, sentence: str) -> bool:
    cfg = ELEMENTS[element]
    if not contains_any(sentence, cfg["keywords"]):
        return False
    if element == "噪声" and not contains_any(sentence, ["噪声", "GB12348", "隔声", "减振", "消声", "昼间", "夜间"]):
        return False
    if element == "危废" and not contains_any(sentence, ["危险废物", "危废", "HW", "GB18597", "废活性炭", "废机油"]):
        return False
    return True


def build_element_answer(element: str, approval_sentences: list[str]) -> str:
    cfg = ELEMENTS[element]
    selected = []
    for sentence in approval_sentences:
        if not element_relevant_sentence(element, sentence):
            continue
        focused = focus_element_sentence(element, sentence)
        if focused not in selected:
            selected.append(focused)
        if len("。".join(selected)) >= 520:
            break
    answer = "。".join(selected).strip("。")
    if not answer:
        return ""
    return f"批复要求：{answer}。"


def element_standards(element: str, answer: str) -> list[dict[str, str]]:
    standards = []
    for std in extract_standards(answer):
        code = std.get("standard_code", "")
        if element == "危废" and not code.startswith("GB18597-"):
            continue
        if element == "噪声" and not (code.startswith("GB12348-") or code.startswith("GB/T3096-")):
            continue
        std["source"] = "approval_answer"
        standards.append(std)
    return standards


def answer_terms(element: str, answer: str) -> list[str]:
    cfg = ELEMENTS[element]
    standards = [s["standard_code"] for s in element_standards(element, answer)]
    terms = [term for term in cfg["keywords"] + cfg["support"] if term in answer]
    return list(dict.fromkeys(standards + terms))


def excluded_report_window(text: str) -> bool:
    return any(marker in text for marker in EXCLUDED_REPORT_EVIDENCE_MARKERS)


def find_report_evidence(report_text: str, element: str, terms: list[str]) -> dict[str, Any] | None:
    flat = clean_text(report_text)
    cfg = ELEMENTS[element]
    candidates = []
    search_terms = list(dict.fromkeys(cfg["keywords"] + terms))
    for term in search_terms:
        if not term:
            continue
        start = 0
        while True:
            idx = flat.find(term, start)
            if idx < 0:
                break
            left = max(0, idx - 260)
            right = min(len(flat), idx + 520)
            window = flat[left:right].strip()
            start = idx + max(1, len(term))
            if excluded_report_window(window):
                continue
            element_hits = sum(1 for kw in cfg["keywords"] if kw in window)
            standard_hits = sum(1 for t in terms if re.match(r"^(GB|HJ|DB)", t or "") and t in window)
            support_hits = sum(1 for t in terms if not re.match(r"^(GB|HJ|DB)", t or "") and t in window)
            score = element_hits * 3 + standard_hits * 4 + support_hits * 2
            if score > 0:
                candidates.append((score, left, right, window))
    if not candidates:
        return None
    score, left, right, window = max(candidates, key=lambda item: (item[0], -item[1]))
    return {"text": window[:780], "char_start": left, "char_end": min(right, left + 780), "score": score}


def find_approval_evidence(approval_text: str, answer: str, element: str) -> dict[str, Any]:
    flat = clean_text(approval_text)
    body = answer.replace("批复要求：", "").strip("。")
    anchor = body[:60]
    idx = flat.find(anchor) if anchor else -1
    if idx < 0:
        terms = answer_terms(element, answer)
        idx = min([flat.find(t) for t in terms if t and flat.find(t) >= 0] or [-1])
    if idx < 0:
        return {"source_file": "approval.md", "text": body[:360], "char_start": -1, "char_end": -1}
    start = max(0, idx - 80)
    end = min(len(flat), idx + 520)
    return {"source_file": "approval.md", "text": flat[start:end], "char_start": start, "char_end": end}


def infer_project_type(project_name: str, fallback: str = "") -> str:
    name = project_name or ""
    if re.search(r"重新报批|重大变动重新报批|重新审核", name):
        return "重新报批"
    if "迁扩建" in name or "迁改扩建" in name:
        return "迁扩建"
    if "改扩建" in name:
        return "改扩建"
    if "技改" in name or "技术改造" in name:
        return "技改"
    if "新建项目" in name or "新建" in name:
        return "新建"
    if "扩建项目" in name or "扩建" in name:
        return "扩建"
    return fallback or ""


def build_question(meta: dict, element: str, project_type: str) -> str:
    company = meta.get("company", "")[:28]
    return f"【区级】{company}（{project_type}项目）{ELEMENTS[element]['question']}"


def metadata_for_element(element: str) -> dict[str, Any]:
    return {
        "task_domain": element,
        "difficulty": "simple",
        "question_type": "extraction",
        "cognitive_level": "L1_fact",
        "evaluation_dimensions": ["professionalism", "clarity", "feasibility", "evidence_grounding"],
    }


def main() -> None:
    ensure_dirs(QA_OUT)
    qas = []
    for pair_dir in sorted(CLEAN_PAIRS_DIR.glob("pair_*")):
        report_text, approval_text, meta = load_pair_text(pair_dir)
        approval_sentences = split_sentences(approval_text)
        project_name = meta.get("project_name", "")
        project_type = infer_project_type(project_name, meta.get("project_type", ""))
        for element in ELEMENTS:
            answer = build_element_answer(element, approval_sentences)
            if not answer:
                continue
            standards = element_standards(element, answer)
            terms = answer_terms(element, answer)
            approval_ev = find_approval_evidence(approval_text, answer, element)
            report_ev = find_report_evidence(report_text, element, terms)
            qa = {
                "qa_id": f"QA_{pair_dir.name}_{element}",
                "pair_id": pair_dir.name,
                "level": "区级",
                "region": "佛山市顺德区",
                "company": meta.get("company", ""),
                "project_name": project_name,
                "industry_code": meta.get("industry_code", ""),
                "industry_name": meta.get("industry_name", ""),
                "project_type": project_type,
                "report_type": meta.get("report_type", ""),
                "element": element,
                "review_point": "审批要求与报告支撑核查",
                "question": build_question(meta, element, project_type),
                "answer": answer,
                "standards_normalized": standards,
                "approval_evidence": [approval_ev],
                "report_evidence": [
                    {
                        "source_file": "report.md",
                        "section": "body",
                        "text": report_ev["text"] if report_ev else "",
                        "char_start": report_ev["char_start"] if report_ev else -1,
                        "char_end": report_ev["char_end"] if report_ev else -1,
                    }
                ],
                "answer_terms": terms,
                "evidence_alignment": {"level": "pending", "reason": "generated before strict audit"},
                "benchmark_metadata": metadata_for_element(element),
                "quality_score": 0,
                "quality_issues": [],
                "need_human_review": True,
            }
            qas.append(qa)

    write_jsonl(qas, QA_OUT / "qa_strict_all.jsonl")
    report = [
        "# Strict QA Generation Report\n\n",
        f"- qa_strict_all: {len(qas)}\n",
        "- source: data/clean_pairs only\n",
        "- answer policy: element-specific clipped approval requirements, not full approval clauses\n",
        "- elements: 废水、废气、噪声、危废\n",
    ]
    out_dir = QA_OUT.parent.parent / "outputs" / "strict_pipeline" / "qa_generation"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "qa_generation_report.md").write_text("".join(report), encoding="utf-8")
    print(f"qa_strict_all={len(qas)}")


if __name__ == "__main__":
    main()
