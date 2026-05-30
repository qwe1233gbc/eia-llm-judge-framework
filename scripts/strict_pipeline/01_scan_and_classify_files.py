# -*- coding: utf-8 -*-
"""Step 1: scan local source files and classify them by content."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from strict_utils import (  # noqa: E402
    APPROVAL_ROOT,
    MINERU_EXTRACTED,
    MINERU_PARSED,
    RAW_EIA_ROOT,
    SCAN_OUT,
    classify_text,
    ensure_dirs,
    extract_pdf_text,
    read_text,
    write_csv,
    write_jsonl,
)


MAX_PDF_BYTES = 8 * 1024 * 1024
PDF_SCAN_PAGES = 3


def iter_sources() -> list[Path]:
    paths: list[Path] = []
    if MINERU_EXTRACTED.exists():
        paths.extend(sorted(MINERU_EXTRACTED.glob("*/full.md")))
    if MINERU_PARSED.exists():
        for ext in ("*.md", "*.txt", "*.json"):
            paths.extend(sorted(MINERU_PARSED.rglob(ext)))
    if RAW_EIA_ROOT.exists():
        for ext in ("*.md", "*.txt", "*.json"):
            paths.extend(sorted(RAW_EIA_ROOT.rglob(ext)))
        paths.extend([p for p in sorted(RAW_EIA_ROOT.rglob("*.pdf")) if p.stat().st_size <= MAX_PDF_BYTES])
    if APPROVAL_ROOT.exists():
        paths.extend([p for p in sorted(APPROVAL_ROOT.rglob("*.pdf")) if p.stat().st_size <= MAX_PDF_BYTES])
    seen: set[str] = set()
    unique = []
    for path in paths:
        key = str(path.resolve()).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def load_body(path: Path) -> tuple[str, str]:
    try:
        if path.suffix.lower() == ".pdf":
            text = extract_pdf_text(path, max_pages=PDF_SCAN_PAGES)
            return text, "ok" if text else "pdf_text_empty"
        if path.suffix.lower() == ".json":
            raw = read_text(path)
            try:
                obj = json.loads(raw)
                return json.dumps(obj, ensure_ascii=False), "ok"
            except json.JSONDecodeError:
                return raw, "json_decode_failed_used_raw"
        return read_text(path), "ok"
    except Exception as exc:
        return "", f"read_failed:{type(exc).__name__}"


def main() -> None:
    ensure_dirs(SCAN_OUT)
    rows = []
    sources = iter_sources()
    print(f"source_candidates={len(sources)}", flush=True)
    for idx, path in enumerate(sources, start=1):
        if idx % 100 == 0:
            print(f"scanning {idx}/{len(sources)}: {path.name}", flush=True)
        text, parse_status = load_body(path)
        file_type, confidence, evidence = classify_text(text)
        rows.append(
            {
                "file_id": f"F{idx:06d}",
                "source_file": str(path),
                "source_md": str(path) if path.suffix.lower() != ".pdf" else "",
                "detected_file_type": file_type,
                "confidence": confidence,
                "file_size": path.stat().st_size if path.exists() else 0,
                "parse_status": parse_status,
                "evidence_text": evidence,
            }
        )
        if idx % 500 == 0:
            print(f"scanned {idx} files", flush=True)

    fields = [
        "file_id",
        "source_file",
        "source_md",
        "detected_file_type",
        "confidence",
        "file_size",
        "parse_status",
        "evidence_text",
    ]
    write_csv(rows, SCAN_OUT / "file_classification.csv", fields)
    write_jsonl(rows, SCAN_OUT / "file_classification.jsonl")

    counts = {}
    for row in rows:
        counts[row["detected_file_type"]] = counts.get(row["detected_file_type"], 0) + 1
    print(f"scanned_files={len(rows)} counts={counts}")


if __name__ == "__main__":
    main()
