# -*- coding: utf-8 -*-
"""
佛山市级审批经验库生成
从92份批复中提取条款，匹配行业，生成QA对
"""
import sys, os, json, re, fitz
from collections import defaultdict, Counter
sys.stdout.reconfigure(encoding='utf-8')

PDF_DIR = r"E:\软件\环评原始数据\佛山市批复"
SHUNDE_QA = r"E:\软件\outputs\qa_batch_full\qa_batch_full.json"
OUT_DIR = r"E:\软件\outputs\qa_foshan"
os.makedirs(OUT_DIR, exist_ok=True)

ELEM_KEYS = {'废水': ['废水','水污染','污水'], '废气': ['废气','大气','VOCs','烟尘','粉尘','颗粒物'],
             '噪声': ['噪声','噪音'], '固废': ['固废','固体废物'], '危废': ['危废','危险废物'],
             '总量': ['总量','排放量'], '监测': ['监测']}

# 标准→行业推测映射
STD_TO_IND = {
    'GB31572': 'C2929', 'GB21902': 'C2929',  # 塑料
    'GB41616': 'C2319',                        # 印刷
    'GB39726': 'C3392', 'GB9078': 'C3392',    # 铸造
    'GB27632': 'C2913',                        # 橡胶
    'GB28665': 'C3360',                        # 金属表面处理
    'GB37824': 'C2641',                        # 涂料/油墨
    'GB18483': 'C6210',                        # 餐饮
    'GB4287': 'C1713',                         # 纺织/印染
}


def guess_industry(stds, text=''):
    """根据标准+文本关键词推测行业"""
    for std in stds:
        base = re.sub(r'-\d{4}$', '', std)
        if base in STD_TO_IND:
            return STD_TO_IND[base]
    kw_map = [
        (['塑料','塑胶','注塑','挤出','吹塑'], 'C2929'),
        (['金属','五金','电镀','蚀刻','酸洗','抛光','喷涂'], 'C3360'),
        (['电子','电路','半导体','元器件'], 'C3979'),
        (['食品','饮料','调味','速冻'], 'C1432'),
        (['印刷','包装','彩印','纸箱'], 'C2319'),
        (['家具','木','木质','板材'], 'C2110'),
        (['模具','机械加工','机床'], 'C3525'),
        (['涂料','油墨','胶粘','油漆'], 'C2641'),
        (['服装','纺织','印染','布料'], 'C1713'),
        (['汽车','零配件','汽配'], 'C3670'),
        (['陶瓷','砖','洁具'], 'C3071'),
        (['医院','医疗','制药','医药'], 'C2770'),
        (['橡胶','轮胎','密封'], 'C2913'),
        (['纸板','造纸','纸品'], 'C2231'),
        (['电线','电缆'], 'C3831'),
        (['混凝土','水泥','搅拌'], 'C3021'),
        (['冰箱','空调','家电','电器'], 'C3854'),
    ]
    for keywords, code in kw_map:
        if any(k in text for k in keywords):
            return code
    return '其他'


def extract_clauses(text):
    """提取批复第三部分中的条款"""
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
        elem = None
        for e, ks in ELEM_KEYS.items():
            if any(k in p for k in ks):
                elem = e
                break
        stds = re.findall(r'[GBDBHJ][A-Z0-9/.-]*-\d{4}', p)
        clauses.append({
            'element': elem or '其他',
            'text': re.sub(r'\s+', ' ', p)[:300],
            'standards': list(set(s.replace('-', '') for s in stds)),
        })
    return clauses


def log(msg):
    print("[%s] %s" % (__import__('time').strftime('%H:%M:%S'), msg), flush=True)


def main():
    log("=" * 55)
    log("佛山市级审批经验库生成")
    log("=" * 55)

    pdfs = [f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')]
    log("总批复: %d" % len(pdfs))

    qa_pairs = []
    matched = 0
    total_stds = Counter()

    for f in pdfs:
        try:
            doc = fitz.open(os.path.join(PDF_DIR, f))
            text = ''
            for p in doc:
                text += p.get_text()
            doc.close()
        except:
            continue
        if len(text) < 200:
            continue

        # 提取条款
        clauses = extract_clauses(text)
        if not clauses:
            continue

        # 提取公司名（从文件名/文本第一行）
        company = ''
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines:
            company = lines[0][:30]

        # 收集所有标准用于行业推测
        all_stds = list(set(s for c in clauses for s in c['standards']))
        ind_code = guess_industry(all_stds, text)
        for s in all_stds:
            total_stds[s] += 1

        matched += 1

        for ci, clause in enumerate(clauses):
            elem = clause['element']
            text_c = clause['text']
            stds = clause['standards']

            if elem == '噪声':
                q = '【市级】%s噪声执行什么标准？几类？' % company[:20]
            elif elem == '废水':
                q = '【市级】%s废水执行什么标准？去向？' % company[:20]
            elif elem == '废气':
                q = '【市级】%s废气执行什么标准？污染物？' % company[:20]
            elif elem in ('固废', '危废'):
                q = '【市级】%s%s暂存/处置要求？' % (company[:20], elem)
            elif elem == '总量':
                q = '【市级】%s总量指标是多少？' % company[:20]
            else:
                q = '【市级】%s关于%s的要求？' % (company[:20], elem)

            qa_pairs.append({
                'level': '市级',
                'region': '佛山市',
                'company': company[:30],
                'industry_code': ind_code,
                'element': elem,
                'clause_index': ci + 1,
                'question': q,
                'answer': text_c[:300],
                'standards': stds,
                'validation': '参考（佛山市级）',
            })

    log("匹配成功: %d" % matched)
    log("生成QA对: %d" % len(qa_pairs))

    # 按行业统计
    ind_cnt = Counter(q['industry_code'] for q in qa_pairs)
    log("\n按行业:")
    for c, n in ind_cnt.most_common(10):
        log("  %s: %d" % (c, n))

    # 按标准统计
    log("\nTop 标准:")
    for s, c in total_stds.most_common(10):
        log("  %s: %d" % (s, c))

    # 保存
    with open(os.path.join(OUT_DIR, 'foshan_qa.json'), 'w', encoding='utf-8') as f:
        json.dump(qa_pairs, f, ensure_ascii=False, indent=2)

    md = ["# 佛山市级审批经验库\n"]
    md.append("| 指标 | 数值 |\n|------|:----:|\n")
    md.append("| 总QA对 | %d |\n" % len(qa_pairs))
    md.append("| 覆盖行业 | %d |\n" % len(ind_cnt))
    md.append("| 来源批复 | %d份 |\n" % matched)
    md.append("\n## QA样例\n\n")
    for q in qa_pairs[:15]:
        md.append("### [%s] %s | %s\n" % (q['level'], q['industry_code'], q['element']))
        md.append("**公司**: %s\n" % q['company'])
        md.append("**Q**: %s\n" % q['question'])
        md.append("**A**: %s\n" % q['answer'])
        md.append("**标准**: %s\n" % '、'.join(q['standards'][:5]))
        md.append("\n---\n")

    with open(os.path.join(OUT_DIR, 'foshan_qa.md'), 'w', encoding='utf-8') as f:
        f.write(''.join(md))

    log("保存: foshan_qa.json")
    log("保存: foshan_qa.md")


if __name__ == '__main__':
    main()
