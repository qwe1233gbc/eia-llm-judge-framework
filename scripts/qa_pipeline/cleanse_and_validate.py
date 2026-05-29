# -*- coding: utf-8 -*-
"""
清洗 + 验证：
1. 清理 HTML 残留标签
2. 每条经验至少 2 家不同公司出现才入库
"""
import sys, os, json, re
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

CLAUSE_QA = r"E:\软件\outputs\qa_by_clause\qa_by_clause.json"
OUT_DIR = r"E:\软件\outputs\qa_by_clause"
os.makedirs(OUT_DIR, exist_ok=True)


def clean_html(text):
    """清理 HTML 标签和多余空白"""
    text = re.sub(r'</?[a-z]+[^>]*>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def log(msg):
    print("[%s] %s" % (__import__('time').strftime('%H:%M:%S'), msg), flush=True)


def main():
    log("=" * 55)
    log("清洗 + 验证 QA 对")
    log("规则：同行业+同要素+同标准 → 至少2家公司 → 入库")
    log("=" * 55)

    with open(CLAUSE_QA, 'r', encoding='utf-8') as f:
        qa_pairs = json.load(f)

    log("原始QA对: %d" % len(qa_pairs))

    # Step 1: 清洗HTML
    cleaned = 0
    for qa in qa_pairs:
        qa['answer'] = clean_html(qa['answer'])
        qa['question'] = clean_html(qa['question'])
        if qa.get('report_evidence'):
            qa['report_evidence'] = [clean_html(e) for e in qa['report_evidence'] if clean_html(e)]
        cleaned += 1
    log("清洗HTML: %d 条" % cleaned)

    # Step 2: 按 (行业代码, 要素, 标准) 统计出现公司数
    exp_counter = defaultdict(set)  # key=(code, elem, std) → set of companies

    for qa in qa_pairs:
        code = qa['industry_code']
        elem = qa['element']
        company = qa.get('company', '')
        for std in qa.get('approval_standards', []):
            exp_counter[(code, elem, std)].add(company)

    # 找出哪些经验的验证数 >= 2
    validated_keys = set()
    for key, companies in exp_counter.items():
        if len(companies) >= 2:
            validated_keys.add(key)

    log("总经验组合(行业+要素+标准): %d" % len(exp_counter))
    log("至少2家公司验证: %d" % len(validated_keys))

    # Step 3: 标记 QA 对的验证状态
    validated_count = 0
    for qa in qa_pairs:
        code = qa['industry_code']
        elem = qa['element']
        company = qa.get('company', '')
        stds = qa.get('approval_standards', [])

        # 检查是否每个标准都至少有2家公司支持
        all_validated = True
        for std in stds:
            if (code, elem, std) not in validated_keys:
                all_validated = False
                break

        qa['validation_status'] = '已验证(>=2家)' if all_validated else '仅1家公司(参考)'

        if all_validated:
            validated_count += 1

    # Step 4: 统计各行业的验证情况
    ind_stats = defaultdict(lambda: {'total': 0, 'validated': 0, 'companies': set()})
    for qa in qa_pairs:
        code = qa['industry_code']
        ind_stats[code]['total'] += 1
        ind_stats[code]['companies'].add(qa.get('company', ''))
        if qa['validation_status'] == '已验证(>=2家)':
            ind_stats[code]['validated'] += 1

    log("\n=== 各行业验证情况 ===")
    for code in sorted(ind_stats.keys(), key=lambda c: -ind_stats[c]['total']):
        s = ind_stats[code]
        log("  %s: %d/%d 已验证 (%d家公司)" % (code, s['validated'], s['total'], len(s['companies'])))

    # Step 5: 更新 QA 对中的验证状态，并保存
    with open(os.path.join(OUT_DIR, 'qa_by_clause.json'), 'w', encoding='utf-8') as f:
        json.dump(qa_pairs, f, ensure_ascii=False, indent=2)

    # 生成最终版 Markdown
    md = ["# 逐条款QA对（经验验证版）\n"]
    md.append("层级: 区域 → 行业 → 项目类型 → 具体条款\n")
    md.append("验证规则: 同行业同要素同标准 至少2家公司出现 才确认为行业规律\n\n")
    md.append("| 指标 | 数值 |\n|------|:----:|\n")
    md.append("| 总QA对 | %d |\n" % len(qa_pairs))
    md.append("| 已验证(>=2家公司) | %d |\n" % validated_count)
    md.append("| 覆盖项目 | %d |\n" % len(set(q['project_id'] for q in qa_pairs)))
    md.append("| 覆盖行业 | %d |\n" % len(set(q['industry_code'] for q in qa_pairs)))
    md.append("\n## QA对（已验证）\n\n")

    shown = 0
    for qa in qa_pairs:
        if qa['validation_status'] != '已验证(>=2家)':
            continue
        if shown >= 15:
            break
        shown += 1
        md.append("### [%s] %s | %s | %s\n" % (qa['level'], qa['industry_code'], qa['project_type'], qa['element']))
        md.append("**公司**: %s | **验证**: %s\n" % (qa['company'], qa['validation_status']))
        md.append("**Q**: %s\n" % qa['question'])
        md.append("**A**: %s\n" % qa['answer'])
        if qa.get('approval_standards'):
            md.append("**标准**: %s\n" % '、'.join(qa['approval_standards']))
        if qa.get('report_evidence'):
            for ev in qa['report_evidence'][:2]:
                md.append("**报告原文**: ...%s...\n" % ev[:150])
        md.append("\n---\n")

    # 也展示未验证的（给你参考用）
    md.append("\n## 参考QA对（仅1家公司，未达验证阈值）\n\n")
    shown = 0
    for qa in qa_pairs:
        if qa['validation_status'] != '仅1家公司(参考)':
            continue
        if shown >= 10:
            break
        shown += 1
        md.append("### [%s] %s | %s | %s\n" % (qa['level'], qa['industry_code'], qa['project_type'], qa['element']))
        md.append("**公司**: %s | **验证**: %s\n" % (qa['company'], qa['validation_status']))
        md.append("**Q**: %s\n" % qa['question'])
        md.append("**A**: %s\n" % qa['answer'])
        md.append("\n---\n")

    with open(os.path.join(OUT_DIR, 'qa_by_clause.md'), 'w', encoding='utf-8') as f:
        f.write(''.join(md))

    log("保存: qa_by_clause.json (更新)")
    log("保存: qa_by_clause.md (更新)")
    log("\n验证通过的QA对: %d (可用于经验库)" % validated_count)


if __name__ == '__main__':
    main()
