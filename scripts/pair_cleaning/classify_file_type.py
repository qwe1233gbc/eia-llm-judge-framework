# -*- coding: utf-8 -*-
"""Classify files by content: report / approval / public_participation / unknown"""
import sys, json, re, os, csv
sys.stdout.reconfigure(encoding='utf-8')
import fitz

REPORT_DIR = r"E:\软件\环评原始数据"
OUT = r"E:\软件\outputs\pair_cleaning"
os.makedirs(OUT, exist_ok=True)

APPROVAL_KEYWORDS = [
    '批复如下', '经研究，批复如下', '经研究批复如下', '我局同意',
    '佛环', '环审', '环函', '环境影响报告书', '环境影响报告表',
    '你单位报送的', '你公司报送的', '你单位提交的', '你公司提交的',
    '经审查', '经审核', '依法公示',
]
REPORT_KEYWORDS = [
    '建设项目基本情况', '工程分析', '主要环境影响和保护措施',
    '环境保护措施监督检查清单', '结论与建议',
    '项目主要污染物产生及预计排放情况',
    '环境影响分析', '建设项目工程分析',
]
PUBLIC_PARTICIPATION_KEYWORDS = [
    '公众参与', '公众意见', '公示', '听证', '信息公开',
]

def classify_pdf(path):
    try:
        doc = fitz.open(path)
        text = ''
        for p in doc:
            text += p.get_text()
        doc.close()
    except:
        return 'unknown', 'unreadable'

    text_lower = text.lower()
    first_500 = text[:500]

    # Check approval keywords
    approval_score = sum(2 for kw in APPROVAL_KEYWORDS if kw in first_500)
    # Check report keywords
    report_score = sum(2 for kw in REPORT_KEYWORDS if kw in text[:2000])
    # Check public participation
    pp_score = sum(2 for kw in PUBLIC_PARTICIPATION_KEYWORDS if kw in text_lower)

    if approval_score >= 4 and approval_score > report_score:
        return 'approval', 'content_matched'
    if report_score >= 4 and report_score > approval_score:
        return 'report', 'content_matched'
    if pp_score >= 4:
        return 'public_participation', 'content_matched'

    # Fallback: filename heuristics
    fn = os.path.basename(path)
    if '批复' in fn or '环审' in fn or '佛环' in fn:
        return 'approval', 'filename_fallback'
    if '报告书' in fn or '报告表' in fn or '受理' in fn:
        return 'report', 'filename_fallback'
    if '公众' in fn or '公示' in fn:
        return 'public_participation', 'filename_fallback'

    return 'unknown', 'no_match'

def main():
    # Scan all PDFs
    all_pdfs = []
    for root, dirs, files in os.walk(REPORT_DIR):
        for f in files:
            if f.endswith('.pdf'):
                all_pdfs.append(os.path.join(root, f))

    print("Scanning %d PDFs..." % len(all_pdfs))
    results = []
    for fp in all_pdfs:
        ftype, reason = classify_pdf(fp)
        results.append({
            'file_path': fp,
            'file_name': os.path.basename(fp),
            'classified_type': ftype,
            'classification_reason': reason,
        })
        if len(results) % 500 == 0:
            print("  %d/%d done..." % (len(results), len(all_pdfs)))

    # Stats
    from collections import Counter
    stats = Counter(r['classified_type'] for r in results)
    print("\nClassification results:")
    for t, n in stats.most_common():
        print("  %s: %d" % (t, n))

    # Save
    with open(os.path.join(OUT, 'file_classification.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['file_path','file_name','classified_type','classification_reason'])
        w.writeheader()
        for r in results:
            w.writerow(r)
    print("Saved: file_classification.csv")

if __name__ == '__main__':
    main()
