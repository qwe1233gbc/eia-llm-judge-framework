# -*- coding: utf-8 -*-
"""Shared helpers for the strict EIA report-approval pipeline."""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT.parent

MINERU_PARSED = DATA_ROOT / "mineru_parsed"
MINERU_EXTRACTED = DATA_ROOT / "mineru_extracted"
RAW_EIA_ROOT = DATA_ROOT / "环评原始数据"
APPROVAL_ROOT = DATA_ROOT / "2023-2026年顺德批复文件"

STRICT_OUT = REPO_ROOT / "outputs" / "strict_pipeline"
SCAN_OUT = STRICT_OUT / "file_scan"
PAIR_OUT = STRICT_OUT / "pair_cleaning"
QA_OUT = REPO_ROOT / "data" / "qa_strict"
CLEAN_PAIRS_DIR = REPO_ROOT / "data" / "clean_pairs"
RULE_OUT = REPO_ROOT / "outputs" / "experience_library_strict"


REPORT_KEYWORDS = [
    "建设项目环境影响报告表",
    "建设项目环境影响报告书",
    "建设项目基本情况",
    "建设项目工程分析",
    "区域环境质量现状",
    "主要环境影响和保护措施",
    "环境保护措施监督检查清单",
    "污染物排放量汇总表",
    "国民经济行业类别",
    "建设项目行业类别",
]

APPROVAL_KEYWORDS = [
    "批复如下",
    "经研究，批复如下",
    "我局同意你单位",
    "从生态环境保护角度可行",
    "主动公开",
    "佛环",
    "环审",
    "行政许可",
    "若违反承诺事项",
    "撤销本次行政许可",
    "三同时",
    "排污许可",
    "重大变动",
    "重新报批",
]

PUBLIC_PARTICIPATION_KEYWORDS = [
    "环境影响评价公众参与说明",
    "首次环境影响评价信息公开",
    "征求意见稿公示",
    "报批前公示",
    "公众意见处理情况",
    "诚信承诺",
]

ELEMENT_KEYWORDS = {
    "废水": ["废水", "污水", "生活污水", "生产废水", "COD", "氨氮", "水污染物"],
    "废气": ["废气", "大气", "VOCs", "非甲烷总烃", "颗粒物", "粉尘", "臭气", "排气筒"],
    "噪声": ["噪声", "厂界", "隔声", "减振", "昼间", "夜间", "dB"],
    "固废": ["固废", "固体废物", "一般工业固体废物", "边角料", "综合利用"],
    "危废": ["危废", "危险废物", "废活性炭", "废机油", "HW", "危险废物暂存"],
    "环境风险": ["环境风险", "风险防范", "事故应急", "应急预案"],
    "总量控制": ["总量", "COD", "氨氮", "SO2", "NOx", "VOCs"],
    "排污许可": ["排污许可", "排污登记", "许可排放"],
    "验收": ["竣工环境保护验收", "环保验收", "验收"],
    "重大变动": ["重大变动", "重新报批", "变动"],
    "承诺制": ["承诺制", "承诺事项", "告知承诺"],
}

PROJECT_TYPES = ["新建", "扩建", "迁建", "搬迁", "改建", "技改", "迁扩建", "改扩建"]
TOWNS = ["大良", "容桂", "伦教", "勒流", "陈村", "北滘", "乐从", "龙江", "杏坛", "均安"]


def ensure_dirs(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=encoding, errors="strict")
        except UnicodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def extract_pdf_text(path: Path, max_pages: int = 8) -> str:
    try:
        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages[:max_pages]:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)
    except Exception:
        return ""


def clean_text(text: str) -> str:
    text = re.sub(r"<details>.*?</details>", " ", text, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_for_match(text: str) -> str:
    return "".join(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", str(text))).lower()


def chinese_only(text: str) -> str:
    return "".join(re.findall(r"[\u4e00-\u9fff]+", str(text)))


def first_match(patterns: Iterable[str], text: str, default: str = "") -> str:
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.S)
        if m:
            value = re.sub(r"\s+", " ", m.group(1)).strip(" ：:，,。；;")
            if value:
                return value[:120]
    return default


def classify_text(text: str) -> tuple[str, int, str]:
    sample = clean_text(text[:12000])
    report_score = sum(1 for kw in REPORT_KEYWORDS if kw in sample)
    approval_score = sum(1 for kw in APPROVAL_KEYWORDS if kw in sample)
    public_score = sum(1 for kw in PUBLIC_PARTICIPATION_KEYWORDS if kw in sample)

    if public_score >= 2 and report_score < 4:
        return "public_participation", public_score * 20, evidence_for_keywords(sample, PUBLIC_PARTICIPATION_KEYWORDS)
    if approval_score >= 3 and approval_score >= report_score:
        return "approval", min(100, approval_score * 12), evidence_for_keywords(sample, APPROVAL_KEYWORDS)
    if report_score >= 3:
        return "report", min(100, report_score * 12), evidence_for_keywords(sample, REPORT_KEYWORDS)
    if approval_score >= 2 and "批复" in sample[:1500]:
        return "approval", min(100, approval_score * 12), evidence_for_keywords(sample, APPROVAL_KEYWORDS)
    return "unknown", 0, sample[:300]


def evidence_for_keywords(text: str, keywords: list[str]) -> str:
    hits = [kw for kw in keywords if kw in text]
    if not hits:
        return text[:300]
    first = min((text.find(kw), kw) for kw in hits if text.find(kw) >= 0)
    start = max(0, first[0] - 120)
    end = min(len(text), first[0] + 260)
    return text[start:end]


def extract_company(text: str) -> str:
    head = text[:8000]
    patterns = [
        r"(?:建设单位|建设单位名称|建设方|项目单位|报批单位)\s*[:：]\s*([\u4e00-\u9fffA-Za-z0-9（）()·\-]{4,60}(?:有限公司|公司|厂|经营部|合作社|中心|分公司))",
        r"([\u4e00-\u9fffA-Za-z0-9（）()·\-]{4,60}(?:有限公司|公司|厂|经营部|合作社|中心|分公司))\s*[:：]\s*你单位",
        r"你单位报批的《?([\u4e00-\u9fffA-Za-z0-9（）()·\-]{4,60}(?:有限公司|公司|厂|经营部|合作社|中心|分公司))",
        r"关于([\u4e00-\u9fffA-Za-z0-9（）()·\-]{4,60}(?:有限公司|公司|厂|经营部|合作社|中心|分公司))",
        r"([\u4e00-\u9fffA-Za-z0-9（）()·\-]{4,60}(?:有限公司|公司|厂|经营部|合作社|中心|分公司))",
    ]
    value = first_match(patterns, head)
    return trim_company(value)


def trim_company(value: str) -> str:
    value = re.sub(r"^(关于|公示|建设单位|项目单位)", "", value or "")
    value = re.sub(r"(建设项目|新建项目|扩建项目|迁建项目|改扩建项目|环境影响.*)$", "", value)
    return value.strip(" ：:，,。；;《》")


def extract_project_name(text: str) -> str:
    head = text[:10000]
    patterns = [
        r"(?:项目名称|建设项目名称)\s*[:：]\s*([^\n\r]{4,100})",
        r"《([^》]{4,120}(?:环境影响报告书|环境影响报告表))》",
        r"关于([^。\n\r]{4,120}?(?:新建|扩建|迁建|改建|技改|建设|搬迁|改扩建)[^。\n\r]{0,40}?项目)",
    ]
    value = first_match(patterns, head)
    value = re.sub(r"环境影响报告[书表].*$", "", value)
    return value.strip(" ：:，,。；;《》")


def extract_report_type(text: str) -> str:
    head = text[:5000]
    if "环境影响报告书" in head or "报告书" in head:
        return "报告书"
    if "环境影响报告表" in head or "报告表" in head:
        return "报告表"
    return ""


def extract_project_type(text: str) -> str:
    head = text[:10000]
    for item in ["迁扩建", "改扩建", "技改", "扩建", "迁建", "搬迁", "改建", "新建"]:
        if item in head:
            if item == "搬迁":
                return "迁建"
            return item
    return ""


def extract_town(text: str) -> str:
    head = text[:12000]
    for town in TOWNS:
        if town in head:
            return town
    return ""


def extract_year(text: str, fallback: str = "") -> str:
    m = re.search(r"(20\d{2})\s*年", text[:5000])
    if m:
        return m.group(1)
    m = re.search(r"(20\d{2})", fallback)
    return m.group(1) if m else ""


def extract_date(text: str, fallback: str = "") -> str:
    m = re.search(r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text[:12000])
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(20\d{2})[-./](\d{1,2})[-./](\d{1,2})", text[:12000] + " " + fallback)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(20\d{2})", fallback)
    return m.group(1) if m else ""


def extract_doc_no(text: str, fallback: str = "") -> str:
    source = fallback + "\n" + text[:5000]
    patterns = [
        r"(佛环[\u4e00-\u9fff0-9（）()〔〕\[\]第号\-]{4,50})",
        r"([\u4e00-\u9fff]{1,6}环[\u4e00-\u9fff0-9（）()〔〕\[\]第号\-]{4,50})",
    ]
    return first_match(patterns, source)


def extract_industry_code(text: str) -> str:
    m = re.search(r"\b([A-Z]\d{4})\b", text[:15000])
    return m.group(1) if m else ""


def extract_standards(text: str) -> list[dict[str, str]]:
    pattern = re.compile(r"\b((?:GB/T|GB|HJ/T|HJ|DB\d{2}/T|DB\d{2})\s*/?\s*\d{1,6}\s*[-—－]?\s*\d{2,4})\b")
    seen: set[str] = set()
    standards = []
    for match in pattern.finditer(text):
        code = normalize_standard(match.group(1))
        if is_valid_standard(code) and code not in seen:
            seen.add(code)
            standards.append({"standard_code": code, "standard_name": "", "source": ""})
    return standards


def normalize_standard(code: str) -> str:
    c = re.sub(r"\s+", "", code.upper())
    c = c.replace("—", "-").replace("－", "-")
    c = re.sub(r"^(DB\d{2})(\d)", r"\1/\2", c)
    m = re.match(r"^((?:GB/T|GB|HJ/T|HJ|DB\d{2}/T|DB\d{2}/)\d{1,6})(\d{4})$", c)
    if m:
        c = f"{m.group(1)}-{m.group(2)}"
    m = re.match(r"^((?:GB/T|GB|HJ/T|HJ|DB\d{2}/T|DB\d{2}/)\d{1,6})-(\d{2})$", c)
    if m:
        year = int(m.group(2))
        c = f"{m.group(1)}-{1900 + year if year > 50 else 2000 + year}"
    return c


def is_valid_standard(code: str) -> bool:
    if not code:
        return False
    if re.match(r"^(DA|G)\d+$", code):
        return False
    if code in {"GB", "HJ", "DB44", "DB"}:
        return False
    return bool(re.match(r"^(GB/T|GB|HJ/T|HJ|DB\d{2}/T|DB\d{2}/)\d{1,6}-\d{4}$", code))


def find_evidence(text: str, terms: Iterable[str], window: int = 260) -> dict[str, Any] | None:
    flat = clean_text(text)
    best_idx = -1
    for term in terms:
        term = str(term).strip()
        if not term:
            continue
        idx = flat.find(term)
        if idx >= 0 and (best_idx < 0 or idx < best_idx):
            best_idx = idx
    if best_idx < 0:
        return None
    start = max(0, best_idx - window // 2)
    end = min(len(flat), best_idx + window)
    return {"text": flat[start:end], "char_start": start, "char_end": end}


def write_jsonl(rows: Iterable[dict[str, Any]], path: Path) -> None:
    ensure_dirs(path.parent)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_csv(rows: list[dict[str, Any]], path: Path, fieldnames: list[str] | None = None) -> None:
    ensure_dirs(path.parent)
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_pair_text(pair_dir: Path) -> tuple[str, str, dict[str, Any]]:
    report = read_text(pair_dir / "report.md")
    approval = read_text(pair_dir / "approval.md")
    meta = json.loads(read_text(pair_dir / "pair_metadata.json"))
    return report, approval, meta


@dataclass
class PipelineCounts:
    scanned_files: int = 0
    reports: int = 0
    approvals: int = 0
    public_participation: int = 0
    clean_pairs: int = 0
    candidate_pairs: int = 0
    mismatches: int = 0
    qa_all: int = 0
    qa_verified: int = 0
    rules_all: int = 0
    rules_a: int = 0
    rules_b: int = 0
    rules_c: int = 0
