# -*- coding: utf-8 -*-
"""
全量条款QA对生成（改进版）
匹配方式：approval_title → 批复文件，大幅提升匹配率
"""
import sys, os, json, re, fitz
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

PROJECT_INDEX = r"E:\软件\outputs\eia_industry_pattern\project_index.jsonl"
MATCHED_PAIRS = r"E:\软件\outputs\eia_pair_commonality\all_matched_pairs.jsonl"
EXTRACTED_DIR = r"E:\软件\mineru_extracted"
APPROVAL_DIR = r"E:\软件\2023-2026年顺德批复文件"
OUT_DIR = r"E:\软件\outputs\qa_batch_full"
os.makedirs(OUT_DIR, exist_ok=True)

TYPES = [('新建', ['新建']), ('扩建', ['扩建']), ('技改', ['技术改造', '技改']), ('迁建', ['迁建', '搬迁'])]
ELEM_KEYS = {'废水': ['废水','水污染','污水'], '废气': ['废气','大气','VOCs','烟尘','粉尘','颗粒物'],
             '噪声': ['噪声','噪音'], '固废': ['固废','固体废物','一般工业'], '危废': ['危废','危险废物'],
             '总量': ['总量','排放量','指标'], '监测': ['监测','跟踪监测']}


def detect_type(t):
    t = t or ''
    for label, keys in TYPES:
        if any(k in t for k in keys):
            return label
    return '新建'


def clean_md(c):
    return re.sub(r'<details>.*?</details>', '', c, flags=re.DOTALL).strip()


def extract_clauses(text):
    """提取批复第三部分中的逐条编号条款"""
    secs = re.split(r'\n[一二三四五六七八九十][、．.]', text)
    if len(secs) < 4:
        return []
    sec3 = secs[3]
    parts = re.split(r'(?=\d+\s*[.．、])', sec3)
    clauses = []
    for p in parts:
        p = p.strip()
        if len(p) < 20:
            continue
        # 判断要素
        elem = None
        for e, ks in ELEM_KEYS.items():
            if any(k in p for k in ks):
                elem = e
                break
        stds = re.findall(r'[GBDBHJ][A-Z0-9/.-]*-\d{4}', p)
        # 去横线
        clauses.append({
            'element': elem or '其他',
            'text': re.sub(r'\s+', ' ', p)[:300],
            'standards': list(set(s.replace('-', '') for s in stds)),
        })
    return clauses


def extract_company_from_title(title):
    """从approval_title提取公司名"""
    m = re.search(r'关于(.+?)(?:新建|扩建|迁建|技改|建设|项目)', title)
    return m.group(1).strip() if m else ''


def find_approval_file(company, approval_files):
    """在批复目录中查找匹配的文件"""
    # 用最长的中文子串匹配
    chinese = re.findall(r'[一-鿿]+', company)
    key = ''.join(chinese[:5])  # 取前几个中文字
    for f in approval_files:
        if key in f:
            return f
    # 尝试用后6个字
    if len(key) > 6:
        for f in approval_files:
            if key[-6:] in f:
                return f
    return None


def search_report(report_text, clause_text):
    """在报告中查找条款对应的原文"""
    flat = report_text.replace('\n', ' ').replace('\r', ' ')
    # 提取关键词
    words = re.findall(r'[一-鿿]{3,}(?:标准|限值|排放|执行|噪声|废水|废气|类别|方位)', clause_text)
    found = []
    for w in words[:5]:
        idx = flat.find(w)
        if idx != -1:
            snippet = flat[max(0, idx-30):idx+len(w)+70].strip()
            snippet = re.sub(r'\s+', ' ', snippet)
            if snippet not in found:
                found.append(snippet)
    return found[:3]


def log(msg):
    print("[%s] %s" % (__import__('time').strftime('%H:%M:%S'), msg), flush=True)


def main():
    log("=" * 55)
    log("全量条款QA对生成（approval_title匹配）")
    log("=" * 55)

    with open(PROJECT_INDEX, 'r', encoding='utf-8') as f:
        projects = {p['project_id']: p for p in [json.loads(l) for l in f if l.strip()]}
    with open(MATCHED_PAIRS, 'r', encoding='utf-8') as f:
        pairs = [json.loads(l) for l in f if l.strip()]

    # 预加载批复文件列表
    approval_files = os.listdir(APPROVAL_DIR)
    log("批复文件: %d" % len(approval_files))

    qa_pairs = []
    match_stats = {'total': 0, 'no_report': 0, 'no_approval': 0, 'no_text': 0, 'no_clause': 0, 'success': 0}

    for idx, pair in enumerate(pairs):
        pid = pair['project_id']
        ind_code = pair.get('industry_code', '') or ''
        ind_name = pair.get('industry_name', '') or ''
        if not ind_code:
            continue

        match_stats['total'] += 1
        proj = projects.get(pid, {})
        proj_name = proj.get('project_name', '') or ''
        report_year = proj.get('report_year', '')
        proj_type = detect_type(proj_name)

        # 读受理报告
        fname = proj.get('file_name', '')
        report_text = ''
        if fname:
            md_path = os.path.join(EXTRACTED_DIR, fname.replace('.zip', ''), 'full.md')
            if os.path.exists(md_path):
                with open(md_path, 'r', encoding='utf-8', errors='replace') as f:
                    report_text = clean_md(f.read())
        if not report_text or len(report_text) < 200:
            match_stats['no_report'] += 1
            continue

        # 用approval_title匹配批复文件
        title = pair.get('approval_title', '')
        company = extract_company_from_title(title)
        if not company:
            match_stats['no_approval'] += 1
            continue

        approval_file = find_approval_file(company, approval_files)
        if not approval_file:
            match_stats['no_approval'] += 1
            continue

        # 读批复文本
        try:
            doc = fitz.open(os.path.join(APPROVAL_DIR, approval_file))
            approval_text = ''
            for p in doc:
                approval_text += p.get_text()
            doc.close()
        except:
            match_stats['no_text'] += 1
            continue

        if len(approval_text) < 200:
            match_stats['no_text'] += 1
            continue

        # 提取条款
        clauses = extract_clauses(approval_text)
        if not clauses:
            match_stats['no_clause'] += 1
            continue

        match_stats['success'] += 1

        for ci, clause in enumerate(clauses):
            elem = clause['element']
            text = clause['text']
            stds = clause['standards']

            # 在报告中验证
            report_ev = search_report(report_text, text)

            # 构建问题
            if elem == '噪声':
                cls = re.search(r'(\d)\s*类', text)
                cls_info = cls.group(0) if cls else ''
                q = '【区级】%s（%s %s项目）噪声执行什么标准？%s' % (company[:20], ind_code, proj_type, cls_info)
            elif elem == '废水':
                q = '【区级】%s（%s %s项目）废水执行什么标准？排放去向？' % (company[:20], ind_code, proj_type)
            elif elem == '废气':
                q = '【区级】%s（%s %s项目）废气执行什么标准？主要污染物？' % (company[:20], ind_code, proj_type)
            elif elem in ('固废', '危废'):
                q = '【区级】%s（%s %s项目）%s的暂存/处置应执行什么标准？' % (company[:20], ind_code, proj_type, elem)
            elif elem == '总量':
                q = '【区级】%s（%s %s项目）总量控制指标是多少？' % (company[:20], ind_code, proj_type)
            else:
                q = '【区级】%s（%s %s项目）关于%s的要求是什么？' % (company[:20], ind_code, proj_type, elem)

            qa_pairs.append({
                'level': '区级', 'region': '佛山市顺德区',
                'company': company[:30], 'project_id': pid,
                'industry_code': ind_code, 'industry_name': ind_name,
                'project_type': proj_type, 'report_year': report_year,
                'element': elem, 'clause_index': ci + 1,
                'question': q, 'answer': re.sub(r'\s+', ' ', text)[:300],
                'standards': stds,
                'report_evidence': [re.sub(r'\s+', ' ', e) for e in report_ev],
            })

        if match_stats['success'] % 30 == 0:
            log("进度: %d成功/%d总, QA: %d" % (match_stats['success'], match_stats['total'], len(qa_pairs)))

    log("\n=== 匹配统计 ===")
    for k, v in match_stats.items():
        log("  %s: %d" % (k, v))

    # 2公司验证
    exp_cnt = defaultdict(set)
    for q in qa_pairs:
        for s in q.get('standards', []):
            exp_cnt[(q['industry_code'], q['element'], s)].add(q['company'])

    validated = set(k for k, v in exp_cnt.items() if len(v) >= 2)
    for q in qa_pairs:
        all_v = all((q['industry_code'], q['element'], s) in validated for s in q.get('standards', []))
        q['validation'] = '已验证' if all_v else '参考'

    val_count = sum(1 for q in qa_pairs if q['validation'] == '已验证')
    log("\nQA对: %d, 已验证(>=2公司): %d" % (len(qa_pairs), val_count))

    # 按行业统计
    ind_stat = defaultdict(lambda: [0, 0, set()])
    for q in qa_pairs:
        c = q['industry_code']
        ind_stat[c][0] += 1
        ind_stat[c][2].add(q['company'])
        if q['validation'] == '已验证':
            ind_stat[c][1] += 1

    log("\n按行业:")
    for c in sorted(ind_stat, key=lambda c: -ind_stat[c][0]):
        log("  %s: %d/%d已验证 (%d家公司)" % (c, ind_stat[c][1], ind_stat[c][0], len(ind_stat[c][2])))

    # 保存
    with open(os.path.join(OUT_DIR, 'qa_batch_full.json'), 'w', encoding='utf-8') as f:
        json.dump(qa_pairs, f, ensure_ascii=False, indent=2)

    md = ["# 全量条款QA对\n"]
    md.append("匹配方式: approval_title → 批复文件\n\n")
    md.append("| 指标 | 数值 |\n|------|:----:|\n")
    md.append("| 总QA对 | %d |\n" % len(qa_pairs))
    md.append("| 已验证(>=2公司) | %d |\n" % val_count)
    md.append("| 匹配成功项目 | %d/%d |\n" % (match_stats['success'], match_stats['total']))
    md.append("| 覆盖行业 | %d |\n" % len(set(q['industry_code'] for q in qa_pairs)))
    md.append("\n## 已验证QA样例\n\n")

    shown = 0
    for q in qa_pairs:
        if q['validation'] != '已验证':
            continue
        if shown >= 20:
            break
        shown += 1
        md.append("### [%s] %s | %s | %s\n" % (q['level'], q['industry_code'], q['project_type'], q['element']))
        md.append("**公司**: %s | **验证**: %s\n" % (q['company'], q['validation']))
        md.append("**Q**: %s\n" % q['question'])
        md.append("**A**: %s\n" % q['answer'])
        if q.get('standards'):
            md.append("**标准**: %s\n" % '、'.join(q['standards'][:5]))
        if q.get('report_evidence'):
            for e in q['report_evidence'][:2]:
                md.append("**报告原文**: ...%s...\n" % e[:150])
        md.append("\n---\n")

    with open(os.path.join(OUT_DIR, 'qa_batch_full.md'), 'w', encoding='utf-8') as f:
        f.write(''.join(md))

    log("保存: qa_batch_full.json")
    log("保存: qa_batch_full.md")


if __name__ == '__main__':
    main()
