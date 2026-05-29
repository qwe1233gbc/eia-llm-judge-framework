# -*- coding: utf-8 -*-
"""
连接环评报告(full.md) ↔ 审查条件(批复文件)
对每个项目：读取full.md → 清洗 → 匹配对应的批复审查条件 → 按行业输出
"""
import sys, os, json, re
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

EXTRACTED_DIR = r"E:\软件\mineru_extracted"
PROJECT_INDEX = r"E:\软件\outputs\eia_industry_pattern\project_index.jsonl"
MATCHED_PAIRS = r"E:\软件\outputs\eia_pair_commonality\all_matched_pairs.jsonl"
APPROVAL_CONDITIONS = r"E:\软件\outputs\approval_review_rules\all_approval_conditions.json"
OUT_DIR = r"E:\软件\outputs\report_approval_link"
os.makedirs(OUT_DIR, exist_ok=True)


def clean_full_md(content):
    """清洗 full.md：去除 text_image 块和图片引用"""
    content = re.sub(r'<details>.*?</details>', '', content, flags=re.DOTALL)
    content = re.sub(r'!\[\]\(images/[^)]+\)', '', content)
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content.strip()


def extract_standards_from_md(text):
    """从 full.md 提取引用的标准代码"""
    return list(set(re.findall(r'[GBDBHJ][A-Z0-9/.-]*-\d{4}', text)))


def extract_project_name_from_md(text):
    """从 full.md 提取项目名称"""
    m = re.search(r'项目名称[：:]\s*([一-鿿\w]{4,60})', text)
    return m.group(1).strip() if m else ''


def log(msg):
    print("[%s] %s" % (__import__('time').strftime('%H:%M:%S'), msg), flush=True)


def main():
    log("=" * 55)
    log("连接环评报告 ↔ 审查条件")
    log("=" * 55)

    # 1. 加载项目索引
    with open(PROJECT_INDEX, 'r', encoding='utf-8') as f:
        projects = [json.loads(l) for l in f if l.strip()]
    log("项目: %d" % len(projects))

    # 2. 加载匹配对 (approval_title → industry)
    with open(MATCHED_PAIRS, 'r', encoding='utf-8') as f:
        pairs = [json.loads(l) for l in f if l.strip()]
    title_to_project = {}
    for p in pairs:
        k = re.sub(r'\s+', '', p.get('approval_title', ''))
        title_to_project[k] = {
            'industry_code': p.get('industry_code'),
            'industry_name': p.get('industry_name'),
            'project_id': p.get('project_id'),
        }
    log("匹配对: %d" % len(pairs))

    # 3. 加载审查条件 (批复)
    with open(APPROVAL_CONDITIONS, 'r', encoding='utf-8') as f:
        approvals = json.load(f)
    log("批复条件: %d" % len(approvals))

    # 加载行业匹配结果 (文件→行业对照)
    with open(r"E:\软件\outputs\approval_review_rules\matched_industry_patterns.json", 'r', encoding='utf-8') as f:
        ind_patterns = json.load(f)
    # 建立 file → industry_code 映射
    file_to_industry = {}
    for code, data in ind_patterns.items():
        for fname in data.get('approval_files', []):
            file_to_industry[fname] = {
                'industry_code': code,
                'industry_name': data.get('industry_name', ''),
            }
    log("文件→行业映射: %d 条" % len(file_to_industry))

    # 4. 对每个项目，找 full.md + 审查条件
    linked = []
    no_md = 0
    no_approval = 0
    linked_count = 0

    for proj in projects:
        pid = proj.get('project_id', '')
        fname = proj.get('file_name', '')  # e.g., xxx_mineru.zip
        ind_code = proj.get('industry_code', '') or ''
        ind_name = proj.get('industry_name', '') or ''

        if not ind_code:
            continue

        # 找 full.md
        md_dir_name = fname.replace('.zip', '') if fname else ''
        md_path = os.path.join(EXTRACTED_DIR, md_dir_name, 'full.md') if md_dir_name else ''
        report_text = ''
        md_standards = []
        if md_path and os.path.exists(md_path):
            with open(md_path, 'r', encoding='utf-8', errors='replace') as f:
                raw = f.read()
            report_text = clean_full_md(raw)
            md_standards = extract_standards_from_md(report_text)
        else:
            no_md += 1

        # 找审查条件 → 通过项目名称模糊匹配批复的company字段
        # 先用matched_industry_patterns找到本行业的批复文件列表
        approval_conditions = {}
        proj_name = (proj.get('project_name', '') or '')[:20]
        proj_unit = (proj.get('construction_unit', '') or '')[:20]

        # 从本行业的批复中查找
        for a in approvals:
            a_file = a.get('file', '')
            matched_ind = file_to_industry.get(a_file, {})
            if matched_ind.get('industry_code') != ind_code:
                continue
            # 找到了本行业的批复，检查公司名是否匹配
            a_company = a.get('company', '') or ''
            # 直接用项目名称中的关键词匹配
            keywords = set()
            for name_part in [proj_name, proj_unit]:
                for ch in ['公司', '厂', '有限公司', '厂部']:
                    if ch in name_part:
                        keywords.add(name_part[:name_part.find(ch)+len(ch)])
            # 检查批复company是否包含这些关键词
            if keywords:
                for kw in keywords:
                    if kw and len(kw) >= 4 and kw in a_company:
                        approval_conditions = a.get('conditions', {})
                        break
            if approval_conditions:
                break

        if not approval_conditions:
            no_approval += 1

        entry = {
            'project_id': pid,
            'industry_code': ind_code,
            'industry_name': ind_name,
            'project_name': proj.get('project_name', ''),
            'report_text': report_text[:5000],  # 按 schema 截断
            'report_standards': md_standards,
            'approval_conditions': approval_conditions,
        }

        # 只保留report和approval至少有一方有数据的
        if report_text or approval_conditions:
            linked.append(entry)
            if report_text and approval_conditions:
                linked_count += 1

    log("")
    log("=== 连接结果 ===")
    log("无 full.md: %d" % no_md)
    log("无审查条件: %d" % no_approval)
    log("成功连接(报告+审查): %d" % linked_count)
    log("总计输出: %d" % len(linked))

    # 5. 按行业归类
    by_industry = defaultdict(list)
    for e in linked:
        by_industry[e['industry_code']].append(e)

    log("")
    log("=== 按行业可连接数 ===")
    for code in sorted(by_industry.keys(), key=lambda c: -len(by_industry[c])):
        name = by_industry[code][0]['industry_name']
        total = len(by_industry[code])
        with_both = sum(1 for e in by_industry[code] if e['report_text'] and e['approval_conditions'])
        log("  %s %s: %d个 (报告+审查均有的: %d)" % (code, name, total, with_both))

    # 6. 保存
    with open(os.path.join(OUT_DIR, 'linked_data.json'), 'w', encoding='utf-8') as f:
        json.dump(linked, f, ensure_ascii=False, indent=2)

    # 按行业拆分保存
    for code, entries in by_industry.items():
        name = by_industry[code][0]['industry_name']
        safe_name = re.sub(r'[\\/:*?\"<>|]', '_', name)
        with open(os.path.join(OUT_DIR, '%s_%s.json' % (code, safe_name)), 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)

    log("")
    log("保存: %s/linked_data.json" % OUT_DIR)

    # 7. 生成简单报告
    with open(os.path.join(OUT_DIR, 'linking_summary.md'), 'w', encoding='utf-8') as f:
        f.write("# 环评报告 ↔ 审查条件 连接结果\n\n")
        f.write("| 行业 | 项目数 | 有报告+审查 | 仅有报告 | 仅有审查 |\n")
        f.write("|------|:-----:|:----------:|:--------:|:--------:|\n")
        for code in sorted(by_industry.keys(), key=lambda c: -len(by_industry[c])):
            name = by_industry[code][0]['industry_name']
            entries = by_industry[code]
            both = sum(1 for e in entries if e['report_text'] and e['approval_conditions'])
            only_r = sum(1 for e in entries if e['report_text'] and not e['approval_conditions'])
            only_a = sum(1 for e in entries if not e['report_text'] and e['approval_conditions'])
            f.write("| %s %s | %d | %d | %d | %d |\n" % (code, name, len(entries), both, only_r, only_a))

    log("保存: %s/linking_summary.md" % OUT_DIR)


if __name__ == '__main__':
    main()
