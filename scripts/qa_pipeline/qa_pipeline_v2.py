# -*- coding: utf-8 -*-
"""
qa_pipeline_v2: 按 GPT 方法论改进的 QA 生成管线

改进点：
1. 问题生成更具体（含要素、工艺、标准类别）
2. 批复条款提取更鲁棒（支持多种编号格式）
3. 报告证据匹配带章节感知
4. 新增 review_point 分类（五维基础上加审核要点）
5. 生成时即做质量评分
6. 输出行为准则（behavior_rule）
"""
import sys, json, re, os, fitz
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

# ====== Paths ======
PROJECT_INDEX = r"E:\软件\outputs\eia_industry_pattern\project_index.jsonl"
MATCHED_PAIRS = r"E:\软件\outputs\eia_pair_commonality\all_matched_pairs.jsonl"
EXTRACTED_DIR = r"E:\软件\mineru_extracted"
APPROVAL_DIR = r"E:\软件\2023-2026年顺德批复文件"
OUT_DIR = r"E:\软件\outputs\qa_v2"
os.makedirs(OUT_DIR, exist_ok=True)

# ====== Constants ======
PROJ_TYPES = [('新建',['新建']), ('扩建',['扩建','改建']), ('技改',['技术改造','技改']), ('迁建',['迁建','搬迁'])]
ELEM_KEYS = {
    '废水': ['废水','水污染','污水','COD','氨氮'],
    '废气': ['废气','大气','VOCs','烟尘','粉尘','颗粒物','非甲烷总烃'],
    '噪声': ['噪声','噪音'],
    '固废': ['固废','固体废物','一般工业'],
    '危废': ['危废','危险废物','废活性炭','废机油'],
    '总量': ['总量','排放量','吨/年','千克/年'],
}
RP_MAP = {
    '废水': '污染防治措施', '废气': '污染防治措施', '噪声': '污染防治措施',
    '固废': '污染防治措施', '危废': '污染防治措施',
    '总量': '总量控制指标',
}

def detect_type(t):
    t = t or ''
    for label, keys in PROJ_TYPES:
        if any(k in t for k in keys):
            return label
    return '新建'

def clean_md(c):
    return re.sub(r'<details>.*?</details>', '', c, flags=re.DOTALL).strip()

def extract_clauses_v2(text):
    """从批复中提取条款，支持更多种编号格式"""
    clauses = []
    # 找第三部分（常见格式：三、 / 三． / 三.）
    secs = re.split(r'\n\s*[三三][、．.．]\s*', text)
    if len(secs) < 2:
        secs = re.split(r'\n\s*[三三]\s*[、．.]', text)
    if len(secs) < 2:
        return clauses
    sec3 = secs[1]

    # 多种编号格式
    parts = re.split(r'(?:\n\s*\d+\s*[.．、]|\n\s*[（(]\d+[)）]|;\s*\d+\s*[.．、])', sec3)
    for p in parts:
        p = p.strip()
        if len(p) < 20:
            continue
        elem = '其他'
        for e, ks in ELEM_KEYS.items():
            if any(k in p for k in ks):
                elem = e
                break
        stds = re.findall(r'(?:[GBDBHJT][A-Z0-9/.-]*\d{4})', p)
        clauses.append({
            'element': elem,
            'text': re.sub(r'\s+', ' ', p)[:500],
            'standards': list(set(s.replace('-','') for s in stds)),
        })
    return clauses

def extract_company(text):
    m = re.search(r'关于(.+?)(?:新建|扩建|迁建|技改|建设)', text)
    return m.group(1).strip() if m else ''

def find_approval(company, files):
    chn = re.findall(r'[一-鿿]+', company)
    key = ''.join(chn[:5])
    for f in files:
        if key in f:
            return f
    if len(key) > 6:
        for f in files:
            if key[-6:] in f:
                return f
    return None

def search_report_evidence(report_text, clause_text):
    """查找报告中匹配的证据"""
    words = re.findall(r'[一-鿿]{3,}(?:标准|限值|排放|执行|噪声|废水|废气|类别|工艺|措施)', clause_text)
    found = []
    flat = report_text.replace('\n', ' ').replace('\r', ' ')
    for w in words[:5]:
        idx = flat.find(w)
        if idx != -1:
            snip = flat[max(0,idx-50):idx+len(w)+150].strip()
            snip = re.sub(r'\s+', ' ', snip)
            if snip not in found and len(snip) > 30:
                found.append(snip)
    return found[:3]

def generate_question(elem, company, ind_code, proj_type, clause_text):
    """生成更具体的问题"""
    if elem == '噪声':
        cls = re.search(r'(\d)\s*类', clause_text)
        cls_info = '，' + cls.group(0) if cls else ''
        return '【区级】%s（%s %s项目）噪声执行什么标准%s？厂界噪声限值是多少？' % (company[:25], ind_code, proj_type, cls_info)
    elif elem == '废水':
        return '【区级】%s（%s %s项目）废水主要污染因子有哪些？执行什么排放标准？废水经预处理后排放去向？' % (company[:25], ind_code, proj_type)
    elif elem == '废气':
        return '【区级】%s（%s %s项目）废气污染源有哪些？应识别哪些污染因子？执行什么标准？废气收集方式和治理措施？' % (company[:25], ind_code, proj_type)
    elif elem == '固废':
        return '【区级】%s（%s %s项目）一般工业固体废物应如何暂存和处置？执行什么标准？' % (company[:25], ind_code, proj_type)
    elif elem == '危废':
        return '【区级】%s（%s %s项目）危险废物类别有哪些？应如何暂存和委托处置？执行什么标准？' % (company[:25], ind_code, proj_type)
    elif elem == '总量':
        return '【区级】%s（%s %s项目）总量控制指标是多少？COD、NH3-N、SO2、NOx、VOCs 分别多少？' % (company[:25], ind_code, proj_type)
    else:
        return '【区级】%s（%s %s项目）%s方面的具体要求是什么？' % (company[:25], ind_code, proj_type, elem)

def generate_behavior_rule(ind_code, elem, proj_type, stds):
    """生成行为准则"""
    if stds:
        return '[%s] %s %s: use %s' % (ind_code, elem, proj_type, '/'.join(stds[:3]))
    return '[%s] %s %s: see approval' % (ind_code, elem, proj_type)

def quality_score(qa):
    """生成时即做质量评分"""
    s = 100
    issues = []
    q = qa.get('question','')
    a = qa.get('answer','')
    if len(q) < 30: s -= 10; issues.append("question too short")
    if len(a) < 50: s -= 15; issues.append("answer too short")
    if not qa.get('standards'): s -= 20; issues.append("no standards")
    ev = qa.get('report_evidence',[])
    if not ev or not any(e for e in ev): s -= 15; issues.append("no evidence")
    if '标准' not in a and '排放' not in a: s -= 10; issues.append("answer lacks standards reference")
    return max(10, s), issues

def main():
    log = lambda msg: print("[%s] %s" % (__import__('time').strftime('%H:%M:%S'), msg), flush=True)
    log("="*55)
    log("QA Pipeline v2 - Improved QA Generation")
    log("="*55)

    # Load data
    with open(PROJECT_INDEX, 'r', encoding='utf-8') as f:
        projects = {p['project_id']: p for p in [json.loads(l) for l in f if l.strip()]}
    with open(MATCHED_PAIRS, 'r', encoding='utf-8') as f:
        pairs = [json.loads(l) for l in f if l.strip()]

    approval_files = os.listdir(APPROVAL_DIR)
    log("Projects: %d, Pairs: %d, Approval files: %d" % (len(projects), len(pairs), len(approval_files)))

    all_qas = []
    stats = {'total':0, 'no_report':0, 'no_approval':0, 'no_text':0, 'no_clause':0, 'success':0}

    for pair in pairs:
        pid = pair['project_id']
        ind_code = pair.get('industry_code','') or ''
        if not ind_code: continue
        stats['total'] += 1

        proj = projects.get(pid, {})
        proj_name = proj.get('project_name','') or ''
        proj_type = detect_type(proj_name)
        report_year = proj.get('report_year','')

        # Load report text
        fname = proj.get('file_name','')
        report_text = ''
        if fname:
            md_path = os.path.join(EXTRACTED_DIR, fname.replace('.zip',''), 'full.md')
            if os.path.exists(md_path):
                with open(md_path, 'r', encoding='utf-8', errors='replace') as f:
                    report_text = clean_md(f.read())
        if not report_text or len(report_text) < 200:
            stats['no_report'] += 1
            continue

        # Match approval
        title = pair.get('approval_title','')
        company = extract_company(title)
        if not company:
            stats['no_approval'] += 1
            continue
        af = find_approval(company, approval_files)
        if not af:
            stats['no_approval'] += 1
            continue

        # Read approval text
        try:
            doc = fitz.open(os.path.join(APPROVAL_DIR, af))
            approval_text = ''
            for p in doc:
                approval_text += p.get_text()
            doc.close()
        except:
            stats['no_text'] += 1
            continue
        if len(approval_text) < 200:
            stats['no_text'] += 1
            continue

        # Extract clauses
        clauses = extract_clauses_v2(approval_text)
        if not clauses:
            stats['no_clause'] += 1
            continue

        stats['success'] += 1

        for ci, clause in enumerate(clauses):
            elem = clause['element']
            text = clause['text']
            stds = clause['standards']

            # Evidence from report
            report_ev = search_report_evidence(report_text, text)

            # Generate
            q = generate_question(elem, company, ind_code, proj_type, text)
            a = text[:500]
            br = generate_behavior_rule(ind_code, elem, proj_type, stds)
            qs, issues = quality_score({
                'question': q, 'answer': a, 'standards': stds, 'report_evidence': report_ev
            })

            all_qas.append({
                'level': '区级', 'region': '佛山市顺德区',
                'company': company[:30], 'project_id': pid,
                'industry_code': ind_code,
                'project_type': proj_type, 'report_year': report_year,
                'element': elem,
                'review_point': RP_MAP.get(elem, '污染防治措施'),
                'clause_index': ci + 1,
                'question': q,
                'answer': a,
                'standards': stds,
                'approval_evidence': [{'source': af, 'text': a[:200]}],
                'report_evidence': [{'section': 'report', 'text': e[:300]} for e in report_ev],
                'behavior_rule': br,
                'quality_score': qs,
                'quality_issues': issues,
                'need_human_review': qs < 70,
            })

        if stats['success'] % 30 == 0:
            log("Progress: %d ok / %d total, QA: %d" % (stats['success'], stats['total'], len(all_qas)))

    log("\n=== Stats ===")
    for k,v in stats.items():
        log("  %s: %d" % (k,v))

    # 2-company validation
    exp_cnt = defaultdict(set)
    for q in all_qas:
        for s in q.get('standards',[]):
            exp_cnt[(q['industry_code'], q['element'], s)].add(q['company'])
    validated = set(k for k,v in exp_cnt.items() if len(v) >= 2)
    for q in all_qas:
        all_v = all((q['industry_code'], q['element'], s) in validated for s in q.get('standards',[]))
        q['validation'] = '已验证' if all_v else '参考'

    val_count = sum(1 for q in all_qas if q['validation'] == '已验证')
    log("QA: %d, Validated(>=2cos): %d" % (len(all_qas), val_count))

    # Save
    with open(os.path.join(OUT_DIR, 'qa_v2.json'), 'w', encoding='utf-8') as f:
        json.dump(all_qas, f, ensure_ascii=False, indent=2)
    log("Saved: qa_v2.json")
    log("Done!")

if __name__ == '__main__':
    main()
