# -*- coding: utf-8 -*-
"""Analyze common approval-side requirements from parsed approval Markdown only.

This stage intentionally does not read EIA reports, does not pair reports with
approvals, and does not consume any old QA datasets.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parent))
from strict_utils import ensure_dirs, write_csv, write_jsonl  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_ROOT = REPO_ROOT.parent / "approval_mineru_parsed"
OUT_DIR = REPO_ROOT / "outputs" / "approval_issue_analysis"

VALID_KEYWORDS = [
    "批复",
    "佛山市生态环境局",
    "主动公开",
    "佛环",
    "环审",
    "我局同意",
    "经研究",
    "从生态环境保护角度可行",
    "排污许可",
    "三同时",
    "重大变动",
    "行政许可",
]

APPROVAL_CORE_KEYWORDS = [
    "批复",
    "佛山市生态环境局",
    "主动公开",
    "佛环",
    "环审",
    "我局同意",
    "经研究",
    "从生态环境保护角度可行",
    "行政许可",
    "形式审查",
    "同意你单位",
]

REPORT_KEYWORDS = [
    "建设项目基本情况",
    "建设项目工程分析",
    "主要环境影响和保护措施",
    "环境保护措施监督检查清单",
    "污染物排放量汇总表",
    "国民经济行业类别",
    "建设项目行业类别",
]

PUBLIC_KEYWORDS = [
    "环境影响评价公众参与说明",
    "首次环境影响评价信息公开",
    "征求意见稿公示",
    "报批前公示",
    "公众意见处理情况",
    "诚信承诺",
]

REQ_KEYWORDS = {
    "责任承担": ["内容和结论负责", "承担相应责任", "建设单位", "编制单位", "对报告表承担"],
    "项目概况": ["项目选址", "项目主要从事", "项目的规模", "项目建设内容", "生产加工", "年产"],
    "审批可行性结论": ["从生态环境保护角度可行", "同意", "原则同意", "可行"],
    "废水要求": ["废水", "污水", "生活污水", "生产废水", "COD", "氨氮", "水污染物", "污水处理厂", "纳管"],
    "废气要求": ["废气", "大气污染物", "VOCs", "非甲烷总烃", "颗粒物", "粉尘", "臭气", "排气筒", "无组织排放"],
    "噪声要求": ["噪声", "厂界", "隔声", "减振", "昼间", "夜间", "GB12348"],
    "固废要求": ["一般工业固体废物", "一般固废", "固体废物", "固废", "边角料", "综合利用"],
    "危废要求": ["危险废物", "危废", "废活性炭", "废机油", "HW", "有资质单位", "危废暂存"],
    "环境风险": ["环境风险", "风险防范", "事故", "应急预案", "应急"],
    "总量控制": ["总量控制", "总量指标", "排放总量", "VOCs总量", "新增排污指标"],
    "排污许可": ["排污许可", "排污许可证", "排污登记", "许可排放"],
    "竣工环保验收": ["竣工环境保护验收", "环保验收", "验收合格", "验收"],
    "重大变动": ["重大变动", "重新报批", "性质、规模、地点", "生产工艺", "环境保护措施发生"],
    "三同时": ["三同时", "同时设计", "同时施工", "同时投产使用"],
    "承诺制要求": ["承诺制", "承诺事项", "形式审查", "撤销本次行政许可", "告知承诺"],
    "特殊限制条件": ["不得", "禁止", "未接通", "方可", "限值", "应当"],
}

POLLUTANTS = [
    "COD",
    "氨氮",
    "NH3-N",
    "VOCs",
    "非甲烷总烃",
    "颗粒物",
    "粉尘",
    "臭气",
    "二氧化硫",
    "氮氧化物",
    "SO2",
    "NOx",
    "总磷",
    "总氮",
    "悬浮物",
]

MEASURES = [
    "化粪池",
    "隔油隔渣",
    "污水处理厂",
    "市政污水管网",
    "活性炭吸附",
    "布袋除尘",
    "水喷淋",
    "收集处理",
    "密闭收集",
    "隔声",
    "减振",
    "规范暂存",
    "委托有资质单位",
    "转移联单",
    "应急预案",
    "台账",
]

QA_TEMPLATES = {
    "废水要求": [
        "项目废水来源、预处理方式、执行标准和排放去向是什么？",
        "生产废水是否回用、外委处理或纳管？",
        "是否要求建立废水外委处理台账？",
    ],
    "废气要求": [
        "哪些工序产生废气？",
        "主要污染因子是什么？",
        "废气如何收集和处理？",
        "执行哪些有组织/无组织排放标准？",
        "是否有 VOCs 总量控制要求？",
    ],
    "噪声要求": ["厂界噪声执行几类标准？", "批复要求采取哪些降噪措施？"],
    "固废要求": ["一般固废如何贮存和处置？"],
    "危废要求": ["危险废物是否要求规范暂存并委托有资质单位处置？", "执行哪些危废贮存标准？"],
    "排污许可": ["是否要求办理排污许可或排污登记？"],
    "竣工环保验收": ["是否要求开展竣工环保验收？"],
    "重大变动": ["重大变动是否需要重新报批？"],
    "三同时": ["是否有“三同时”要求？"],
    "承诺制要求": [
        "审批机关为何同意项目开展？",
        "建设单位和编制单位承担什么责任？",
        "违反承诺事项会有什么后果？",
    ],
}


def read_text(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def repair_mojibake(text: str) -> str:
    markers = ["浣涘", "鐜", "鎵瑰", "寤鸿", "椤圭", "涓诲", "鈥", "銆"]
    if sum(text.count(m) for m in markers) < 2:
        return text
    try:
        fixed = text.encode("gbk", errors="strict").decode("utf-8", errors="strict")
        if count_valid_keywords(fixed) >= count_valid_keywords(text):
            return fixed
    except UnicodeError:
        pass
    return text


def clean_text(text: str) -> str:
    text = repair_mojibake(text)
    text = re.sub(r"<details>.*?</details>", " ", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def count_hits(text: str, keywords: list[str]) -> int:
    return sum(1 for kw in keywords if kw in text)


def count_valid_keywords(text: str) -> int:
    return count_hits(text, VALID_KEYWORDS)


def iter_documents() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for directory in sorted([p for p in INPUT_ROOT.rglob("*") if p.is_dir()]):
        approval_md = directory / "approval.md"
        metadata_path = directory / "metadata.json"
        if approval_md.exists():
            docs.append({"source_md": approval_md, "metadata_path": metadata_path if metadata_path.exists() else None})

    used = {d["source_md"].resolve() for d in docs}
    for md in sorted(INPUT_ROOT.rglob("*.md")):
        if md.resolve() not in used:
            docs.append({"source_md": md, "metadata_path": md.with_name("metadata.json") if md.with_name("metadata.json").exists() else None})
    return docs


def load_metadata(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        raw = repair_mojibake(read_text(path))
        return json.loads(raw)
    except Exception:
        return {"metadata_parse_warning": str(path)}


def classify_validity(text: str) -> tuple[str, bool, list[str]]:
    valid = count_hits(text, VALID_KEYWORDS)
    core = count_hits(text, APPROVAL_CORE_KEYWORDS)
    report = count_hits(text, REPORT_KEYWORDS)
    public = count_hits(text, PUBLIC_KEYWORDS)
    head = text[:5000]
    warnings = []
    starts_like_report = (
        ("建设项目环境影响报告表" in head or "建设项目环境影响报告书" in head)
        and ("建设单位（盖章）" in head or "中华人民共和国生态环境部制" in head or "一、建设项目基本情况" in head)
    )
    if report >= 3 and (report > valid or core < 2 or starts_like_report):
        return "wrong_type_report", False, ["body_looks_like_eia_report"]
    if public >= 2 and (public > valid or core < 2):
        return "wrong_type_public_participation", False, ["body_looks_like_public_participation"]
    if valid >= 2 and core >= 1:
        return "valid_approval", True, warnings
    return "invalid_or_unknown", False, ["valid_approval_keywords_less_than_2_or_core_keyword_missing"]


def first_match(patterns: list[str], text: str) -> str:
    for pat in patterns:
        m = re.search(pat, text, flags=re.S)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip(" ：:，,。；;《》")
    return ""


def normalize_company(value: str) -> str:
    value = re.sub(r"^(关于|公示|你单位报批的|你单位)", "", value or "")
    value = re.sub(r"(新建项目|扩建项目|迁建项目|改扩建项目|建设项目|环境影响.*)$", "", value)
    return value.strip(" ：:，,。；;《》")


def extract_company(text: str) -> str:
    value = first_match(
        [
            r"([\u4e00-\u9fffA-Za-z0-9（）()·\-]{4,80}(?:有限公司|公司|厂|经营部|分公司|合作社|中心))\s*[：:]?\s*你单位",
            r"你单位报批的《?([\u4e00-\u9fffA-Za-z0-9（）()·\-]{4,80}(?:有限公司|公司|厂|经营部|分公司|合作社|中心))",
            r"关于([\u4e00-\u9fffA-Za-z0-9（）()·\-]{4,80}(?:有限公司|公司|厂|经营部|分公司|合作社|中心))",
            r"([\u4e00-\u9fffA-Za-z0-9（）()·\-]{4,80}(?:有限公司|公司|厂|经营部|分公司|合作社|中心))",
        ],
        text[:5000],
    )
    return normalize_company(value)


def extract_project_name(text: str) -> str:
    value = first_match(
        [
            r"《([^》]{4,160}(?:环境影响报告书|环境影响报告表))》",
            r"关于([^。\n\r]{4,160}?(?:新建|扩建|迁建|改建|技改|建设|搬迁|改扩建)[^。\n\r]{0,60}?项目)",
        ],
        text[:8000],
    )
    value = re.sub(r"环境影响报告[书表].*$", "", value)
    return value.strip(" ：:，,。；;《》")


def extract_title(text: str) -> str:
    lines = [ln.strip() for ln in re.split(r"[\r\n]+", repair_mojibake(text)) if ln.strip()]
    for line in lines[:80]:
        if "关于" in line and ("批复" in line or "环境影响报告" in line):
            return clean_text(line)[:260]
    return first_match([r"(佛山市生态环境局关于[^。]{8,220})"], clean_text(text))


def extract_doc_no(text: str, source_pdf: str = "") -> str:
    blob = source_pdf + " " + text[:6000]
    return first_match(
        [
            r"(佛环[\u4e00-\u9fff0-9（）()〔〕\[\]第号\- ]{4,60})",
            r"([\u4e00-\u9fff]{1,8}环审[\u4e00-\u9fff0-9（）()〔〕\[\]第号\- ]{4,60})",
        ],
        blob,
    )


def extract_date(text: str, source_pdf: str = "") -> str:
    blob = text[-1000:] + " " + source_pdf
    m = re.search(r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", blob)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(20\d{2})", source_pdf)
    return m.group(1) if m else ""


def extract_authority(text: str) -> str:
    return first_match([r"((?:佛山市|[\u4e00-\u9fff]{2,8})生态环境局[\u4e00-\u9fff分局]*)"], text[:6000])


def report_type(text: str) -> str:
    if "报告书" in text[:8000]:
        return "报告书"
    if "报告表" in text[:8000]:
        return "报告表"
    return "未知"


def classify_doc_type(text: str) -> tuple[str, str, str]:
    head = text[:12000]
    if any(k in head for k in ["不予批准", "退回", "补正", "不予许可"]):
        conclusion = "不予批准" if "不予批准" in head else ("需补正" if "补正" in head else "未知")
        return "不予批准/退回/补正类", "未知", conclusion
    if "形式审查" in head or "承诺事项" in head or "撤销本次行政许可" in head:
        return "报告表承诺制批复", "承诺制", "同意" if "同意" in head else "未知"
    if "审批决定公告" in head or "审批公告" in head:
        return "审批决定公告", "未知", "未知"
    if "报告书" in head:
        return "报告书批复", "普通审批", "同意" if "可行" in head or "同意" in head else "未知"
    if "报告表" in head and ("经研究" in head or "批复如下" in head or "同意项目" in head or "从生态环境保护角度可行" in head):
        return "报告表普通批复", "普通审批", "同意" if "同意" in head or "可行" in head else "未知"
    return "未知批复", "未知", "未知"


def normalize_standard(code: str) -> str:
    c = re.sub(r"\s+", "", code.upper()).replace("—", "-").replace("－", "-")
    known = {
        "DB44/262001": "DB44/26-2001",
        "DB44/272001": "DB44/27-2001",
        "DB44/23672022": "DB44/2367-2022",
        "GB123482008": "GB12348-2008",
        "GB315722015": "GB31572-2015",
        "GB185972023": "GB18597-2023",
        "GB185992020": "GB18599-2020",
        "GB378222019": "GB37822-2019",
        "GB189182002": "GB18918-2002",
        "GB14554": "GB14554-93",
    }
    if c in known:
        return known[c]
    c = re.sub(r"^(DB\d{2})(\d)", r"\1/\2", c)
    m = re.match(r"^((?:GB/T|GB|HJ/T|HJ|DB\d{2}/T|DB\d{2}/)\d{1,6})(\d{4})$", c)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return c


def valid_standard(code: str) -> bool:
    if not code or code in {"GB", "HJ", "DB44", "DB"}:
        return False
    if re.match(r"^(DA|G)\d+$", code):
        return False
    return bool(re.match(r"^(GB/T|GB|HJ/T|HJ|DB\d{2}/T|DB\d{2}/)\d{1,6}-\d{2,4}$", code))


def extract_standard_mentions(text: str, approval_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates = re.findall(r"\b(?:GB/T|GB|HJ/T|HJ|DB\d{2}/T|DB\d{2}/?)\s*[/]?\s*\d{0,8}\s*[-—－]?\s*\d{0,4}\b|\bDA\d+\b|\bG\d+\b", text)
    good, bad = [], []
    seen = set()
    for raw in candidates:
        raw_clean = re.sub(r"\s+", "", raw)
        norm = normalize_standard(raw_clean)
        row = {"approval_id": approval_id, "raw_code": raw_clean, "standard_code": norm}
        if valid_standard(norm):
            if norm not in seen:
                seen.add(norm)
                good.append(row)
        else:
            bad.append(row | {"reason": "invalid_standard_code"})
    return good, bad


def split_clauses(text: str) -> list[str]:
    compact = clean_text(text)
    parts = re.split(r"(?:(?:^|[。；;])\s*(?:[一二三四五六七八九十]+|\d+)\s*[、.．])", compact)
    clauses = [p.strip() for p in parts if len(p.strip()) >= 25]
    if len(clauses) < 3:
        clauses = [p.strip() for p in re.split(r"[。；;]", compact) if len(p.strip()) >= 25]
    return clauses


def classify_requirement(text: str) -> str:
    scores = {k: sum(1 for kw in kws if kw in text) for k, kws in REQ_KEYWORDS.items()}
    best, score = max(scores.items(), key=lambda item: item[1])
    return best if score > 0 else "其他"


def find_terms(text: str, terms: list[str]) -> list[str]:
    return sorted({term for term in terms if term in text})


def qa_value(req_type: str, text: str) -> tuple[bool, str, str]:
    high = {"废水要求", "废气要求", "噪声要求", "固废要求", "危废要求", "排污许可", "竣工环保验收", "重大变动", "三同时", "承诺制要求"}
    medium = {"环境风险", "总量控制", "项目概况", "责任承担"}
    if req_type in high:
        return True, "high", "批复要求明确，适合转成单要素 QA 并与报告内容逐项比对"
    if req_type in medium:
        return True, "medium", "可形成管理类或背景类 QA，但后续比对需要报告侧支撑"
    return len(text) >= 80, "low", "条款较泛化，适合作为补充背景或人工复核"


def focused_evidence(req_type: str, text: str, limit: int = 320) -> str:
    keywords = REQ_KEYWORDS.get(req_type, [])
    positions = [text.find(kw) for kw in keywords if text.find(kw) >= 0]
    if not positions:
        return text[:limit]
    pos = min(positions)
    start = max(0, pos - 80)
    end = min(len(text), pos + limit - 80)
    snippet = text[start:end].strip(" ，。；;")
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet += "..."
    return snippet


def representative(items: list[dict[str, Any]]) -> dict[str, str]:
    if not items:
        return {"text": "", "project": ""}
    item = max(
        items,
        key=lambda r: (
            bool(r.get("standards")),
            bool(r.get("pollutants")),
            bool(r.get("control_measures")),
            min(len(r.get("requirement_text", "")), 500),
        ),
    )
    return {"text": item.get("evidence", "")[:260], "project": item.get("project_name", "") or item.get("company", "")}


def summarize_requirements(requirements: list[dict[str, Any]], valid_count: int) -> list[dict[str, Any]]:
    grouped = defaultdict(list)
    for item in requirements:
        grouped[item["requirement_type"]].append(item)
    rows = []
    for req_type, items in sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        rep = representative(items)
        rows.append(
            {
                "requirement_type": req_type,
                "count": len(items),
                "ratio": round(len(items) / max(valid_count, 1), 4),
                "representative_text": rep["text"],
                "representative_project": rep["project"],
                "suitable_for_qa": any(i["can_be_qa"] for i in items),
                "suitable_for_report_comparison": req_type
                in {"废水要求", "废气要求", "噪声要求", "固废要求", "危废要求", "环境风险", "总量控制", "排污许可", "竣工环保验收", "重大变动", "三同时"},
            }
        )
    return rows


def quality_gate(inventory: list[dict[str, Any]], suspicious: list[dict[str, Any]], standards: list[dict[str, Any]], summary: list[dict[str, Any]]) -> tuple[bool, str]:
    total = len(inventory)
    valid = sum(1 for r in inventory if r["valid_approval_text"])
    wrong = sum(1 for r in inventory if r["doc_type"] in {"wrong_type_report", "wrong_type_public_participation"})
    standard_error_rate = len(suspicious) / max(len(suspicious) + len(standards), 1)
    main_types = ["废水要求", "废气要求", "噪声要求", "固废要求", "危废要求", "排污许可", "竣工环保验收", "重大变动"]
    summary_types = {r["requirement_type"] for r in summary if r["representative_text"]}
    ok = valid >= 100 and wrong / max(total, 1) < 0.10 and standard_error_rate < 0.05 and all(t in summary_types for t in main_types)
    msg = "批复侧质量基本可用，可进入第二阶段报告—批复配对。" if ok else "批复侧质量暂不足，不建议进入报告—批复配对阶段。"
    return ok, msg


def write_markdown_reports(
    inventory: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    summary: list[dict[str, Any]],
    standards: list[dict[str, Any]],
    suspicious: list[dict[str, Any]],
) -> None:
    valid_count = sum(1 for r in inventory if r["valid_approval_text"])
    total = len(inventory)
    doc_counts = Counter(r["doc_type"] for r in inventory)
    ok, gate_msg = quality_gate(inventory, suspicious, standards, summary)
    summary_by_type = {r["requirement_type"]: r for r in summary}

    def summary_line(req_type: str) -> str:
        row = summary_by_type.get(req_type, {})
        if not row:
            return f"- {req_type}: 未形成稳定统计。\n"
        return (
            f"- {req_type}: {row['count']} 次，占有效批复 {row['ratio']:.1%}；"
            f"代表项目：{row['representative_project']}；适合转 QA：{row['suitable_for_qa']}；"
            f"适合后续比对：{row['suitable_for_report_comparison']}。\n"
            f"  代表原文：{row['representative_text']}\n"
        )

    common_md = [
        "# 顺德区批复常见问题与审批要求总结\n\n",
        "## 批复常见结构\n\n",
        "多数有效批复遵循：建设单位来文与报告类型说明 -> 建设单位/编制单位责任 -> 项目概况 -> "
        "生态环境可行性结论 -> 废水/废气/噪声/固废/危废等污染防治要求 -> 重大变动、三同时、"
        "排污许可或验收等管理要求 -> 落款与抄送。\n\n",
        "## 高频要求\n\n",
    ]
    for req_type in ["废水要求", "废气要求", "噪声要求", "固废要求", "危废要求", "环境风险", "排污许可", "竣工环保验收", "重大变动", "三同时", "承诺制要求"]:
        common_md.append(summary_line(req_type))
    common_md.extend(
        [
            "\n## 报告书批复与报告表批复差异\n\n",
            "- 报告书批复通常更强调专家评审、环境风险、总量控制和系统性污染防治要求。\n",
            "- 报告表普通批复更常见的是按污染要素列明执行标准、处理措施、排放去向和管理要求。\n",
            "- 承诺制批复更强调形式审查、承诺事项、建设单位与编制单位责任，以及违反承诺后的撤销行政许可后果。\n",
            "\n## 最适合转 QA 的问题\n\n",
            "- 废水来源、预处理方式、执行标准、排放去向。\n",
            "- 废气产生工序、污染因子、收集治理措施、有组织/无组织标准。\n",
            "- 厂界噪声标准类别和降噪措施。\n",
            "- 一般固废/危废暂存、处置去向、危废资质与转移联单要求。\n",
            "- 排污许可、竣工环保验收、重大变动重新报批、三同时管理要求。\n",
        ]
    )
    (OUT_DIR / "shunde_approval_common_issues.md").write_text("".join(common_md), encoding="utf-8")

    common_json = {
        "valid_approval_count": valid_count,
        "doc_type_distribution": dict(doc_counts),
        "requirement_summary": summary,
        "quality_gate_passed": ok,
        "quality_gate_message": gate_msg,
    }
    (OUT_DIR / "shunde_approval_common_issues.json").write_text(json.dumps(common_json, ensure_ascii=False, indent=2), encoding="utf-8")

    template_md = ["# 批复侧可转 QA 问题模板\n\n"]
    for req_type, templates in QA_TEMPLATES.items():
        row = summary_by_type.get(req_type, {})
        template_md.append(f"## {req_type}\n\n")
        template_md.append(f"- 出现次数：{row.get('count', 0)}\n")
        template_md.append(f"- 后续与报告比对价值：{'高' if row.get('suitable_for_report_comparison') else '中/低'}\n")
        for tpl in templates:
            template_md.append(f"- {tpl}\n")
        template_md.append("\n")
    (OUT_DIR / "qa_question_templates_from_approval.md").write_text("".join(template_md), encoding="utf-8")

    report_md = [
        "# Approval Issue Analysis Report\n\n",
        f"1. 共读取 approval.md / md 文档：{total}\n",
        f"2. 有效批复：{valid_count}\n",
        f"3. wrong_type_report：{doc_counts.get('wrong_type_report', 0)}；wrong_type_public_participation：{doc_counts.get('wrong_type_public_participation', 0)}\n",
        f"4. 报告书批复：{doc_counts.get('报告书批复', 0)}；报告表普通批复：{doc_counts.get('报告表普通批复', 0)}；承诺制批复：{doc_counts.get('报告表承诺制批复', 0)}\n",
        "5. 顺德区批复最常见结构：来文与报告类型、责任承担、项目概况、可行性结论、污染防治要求、重大变动/三同时/排污许可/验收管理、落款抄送。\n",
        "6. 高频废水要求：\n",
        summary_line("废水要求"),
        "7. 高频废气要求：\n",
        summary_line("废气要求"),
        "8. 高频噪声要求：\n",
        summary_line("噪声要求"),
        "9. 高频固废/危废要求：\n",
        summary_line("固废要求"),
        summary_line("危废要求"),
        "10. 高频排污许可/验收/重大变动要求：\n",
        summary_line("排污许可"),
        summary_line("竣工环保验收"),
        summary_line("重大变动"),
        "11. 最适合转成 QA 的批复问题：废水、废气、噪声、固废/危废、排污许可、竣工环保验收、重大变动、三同时、承诺制责任与后果。\n",
        "12. 最适合后续与报告内容比对的要求：污染物执行标准、治理措施、排放去向、危废暂存处置、排污许可、验收、重大变动重新报批。\n",
        f"13. 数据质量结论：{gate_msg}\n\n",
        "## 质量门槛\n\n",
        f"- 有效批复 md 数量 >= 100：{valid_count >= 100} ({valid_count})\n",
        f"- wrong_type 比例 < 10%：{(sum(1 for r in inventory if r['doc_type'] in {'wrong_type_report', 'wrong_type_public_participation'}) / max(total, 1)) < 0.10}\n",
        f"- 标准编号错误率 < 5%：{(len(suspicious) / max(len(suspicious) + len(standards), 1)) < 0.05} ({len(suspicious)}/{len(suspicious) + len(standards)})\n",
        "- 每类主要要求都有代表性原文：见 `approval_requirement_summary.csv`。\n",
    ]
    (OUT_DIR / "approval_issue_analysis_report.md").write_text("".join(report_md), encoding="utf-8")


def main() -> None:
    ensure_dirs(OUT_DIR)
    docs = iter_documents()
    inventory = []
    requirements = []
    standard_mentions = []
    suspicious_standards = []
    approval_md_total = sum(1 for d in docs if d["source_md"].name == "approval.md")

    for idx, doc in enumerate(docs, start=1):
        source_md = doc["source_md"]
        metadata = load_metadata(doc["metadata_path"])
        raw = read_text(source_md)
        text = clean_text(raw)
        validity_type, is_valid, warnings = classify_validity(text)
        source_pdf = repair_mojibake(str(metadata.get("source_pdf", "")))
        approval_id = f"APPROVAL_{idx:05d}"
        if is_valid:
            doc_type, approval_mode, conclusion = classify_doc_type(text)
        else:
            doc_type, approval_mode, conclusion = validity_type, "未知", "未知"
        title = extract_title(raw)
        company = extract_company(text)
        project_name = extract_project_name(text)
        inventory.append(
            {
                "approval_id": approval_id,
                "source_md": str(source_md),
                "source_pdf": source_pdf,
                "doc_type": doc_type,
                "approval_title": title,
                "approval_doc_no": extract_doc_no(text, source_pdf),
                "approval_date": extract_date(text, source_pdf),
                "approval_authority": extract_authority(text),
                "company": company,
                "project_name": project_name,
                "report_type_referenced": report_type(text),
                "approval_mode": approval_mode,
                "approval_conclusion": conclusion,
                "text_length": len(text),
                "valid_approval_text": is_valid,
                "warnings": ";".join(warnings),
            }
        )

        good_stds, bad_stds = extract_standard_mentions(text, approval_id)
        for std in good_stds:
            std.update({"source_md": str(source_md), "company": company, "project_name": project_name})
        for std in bad_stds:
            std.update({"source_md": str(source_md), "company": company, "project_name": project_name})
        standard_mentions.extend(good_stds)
        suspicious_standards.extend(bad_stds)

        if not is_valid:
            continue
        for clause in split_clauses(text):
            req_type = classify_requirement(clause)
            standards = [s["standard_code"] for s in extract_standard_mentions(clause, approval_id)[0]]
            pollutants = find_terms(clause, POLLUTANTS)
            measures = find_terms(clause, MEASURES)
            can_qa, level, why = qa_value(req_type, clause)
            evidence = focused_evidence(req_type, clause)
            requirements.append(
                {
                    "approval_id": approval_id,
                    "company": company,
                    "project_name": project_name,
                    "doc_type": doc_type,
                    "requirement_type": req_type,
                    "requirement_text": clause[:1200],
                    "standards": ";".join(standards),
                    "pollutants": ";".join(pollutants),
                    "control_measures": ";".join(measures),
                    "evidence": evidence,
                    "can_be_qa": can_qa,
                    "qa_value_level": level,
                    "why_valuable": why,
                }
            )
        if idx % 500 == 0:
            print(f"processed {idx}/{len(docs)}", flush=True)

    summary = summarize_requirements(requirements, sum(1 for r in inventory if r["valid_approval_text"]))

    inventory_fields = [
        "approval_id",
        "source_md",
        "source_pdf",
        "doc_type",
        "approval_title",
        "approval_doc_no",
        "approval_date",
        "approval_authority",
        "company",
        "project_name",
        "report_type_referenced",
        "approval_mode",
        "approval_conclusion",
        "text_length",
        "valid_approval_text",
        "warnings",
    ]
    req_fields = [
        "approval_id",
        "company",
        "project_name",
        "doc_type",
        "requirement_type",
        "requirement_text",
        "standards",
        "pollutants",
        "control_measures",
        "evidence",
        "can_be_qa",
        "qa_value_level",
        "why_valuable",
    ]
    write_jsonl(inventory, OUT_DIR / "approval_inventory.jsonl")
    write_csv(inventory, OUT_DIR / "approval_inventory.csv", inventory_fields)
    write_jsonl(requirements, OUT_DIR / "approval_requirement_items.jsonl")
    write_csv(requirements, OUT_DIR / "approval_requirement_items.csv", req_fields)
    write_csv(summary, OUT_DIR / "approval_requirement_summary.csv")
    write_csv(standard_mentions, OUT_DIR / "approval_standard_mentions.csv")
    write_csv(suspicious_standards, OUT_DIR / "suspicious_standard_codes.csv")
    write_markdown_reports(inventory, requirements, summary, standard_mentions, suspicious_standards)

    doc_counts = Counter(r["doc_type"] for r in inventory)
    req_counts = Counter(r["requirement_type"] for r in requirements)
    _, gate_msg = quality_gate(inventory, suspicious_standards, standard_mentions, summary)
    print("\n批复问题总结完成：\n")
    print(f"approval.md 总数：{approval_md_total}")
    print(f"有效批复：{sum(1 for r in inventory if r['valid_approval_text'])}")
    print(f"wrong_type_report：{doc_counts.get('wrong_type_report', 0)}")
    print(f"wrong_type_public_participation：{doc_counts.get('wrong_type_public_participation', 0)}")
    print(f"报告书批复：{doc_counts.get('报告书批复', 0)}")
    print(f"报告表普通批复：{doc_counts.get('报告表普通批复', 0)}")
    print(f"承诺制批复：{doc_counts.get('报告表承诺制批复', 0)}")
    print("\n高频要求：")
    print(f"- 废水：{req_counts.get('废水要求', 0)}")
    print(f"- 废气：{req_counts.get('废气要求', 0)}")
    print(f"- 噪声：{req_counts.get('噪声要求', 0)}")
    print(f"- 固废/危废：{req_counts.get('固废要求', 0) + req_counts.get('危废要求', 0)}")
    print(f"- 排污许可/验收/重大变动：{req_counts.get('排污许可', 0) + req_counts.get('竣工环保验收', 0) + req_counts.get('重大变动', 0)}")
    print(f"\n是否建议进入第二阶段：{gate_msg}")
    print("输出目录：outputs/approval_issue_analysis/")


if __name__ == "__main__":
    main()
