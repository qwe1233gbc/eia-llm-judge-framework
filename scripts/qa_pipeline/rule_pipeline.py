# -*- coding: utf-8 -*-
"""Phase 3: Rule Pipeline - QA -> Candidate Rules -> Aggregated Rules (5 samples)"""
import sys, json, re, os, csv
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
import fitz

OUT_DIR = r"E:\软件\outputs\expert_rules"
SAMPLE_DIR = r"E:\软件\sample_for_gpt"
os.makedirs(OUT_DIR, exist_ok=True)

# ========== QA Generation from PDF Pairs ==========
ELEM_KEYS = {
    '废水': ['废水','水污染','污水','COD','氨氮'],
    '废气': ['废气','VOCs','烟尘','粉尘','颗粒物','臭气'],
    '噪声': ['噪声','噪音'],
    '固废': ['固废','固体废物','一般工业'],
    '危废': ['危废','危险废物','废活性炭'],
    '总量': ['总量','排放量','指标','吨/年'],
}

def extract_pdf_text(path):
    try:
        doc = fitz.open(path)
        text = ''
        for p in doc:
            text += p.get_text()
        doc.close()
        return text
    except:
        return ''

def extract_approval_clauses(text):
    """Extract numbered clauses from approval"""
    clauses = []
    # Find section 三、 (the review requirements section)
    sec_match = re.split(r'[三三][、．.]', text)
    if len(sec_match) < 2:
        return clauses
    sec3 = sec_match[1]
    # Split by numbered items
    parts = re.split(r'(?:\d+\s*[.．、]|\n[（(]\d+[)）])', sec3)
    for p in parts:
        p = p.strip()
        if len(p) < 20:
            continue
        # Detect element
        elem = '其他'
        for e, ks in ELEM_KEYS.items():
            if any(k in p for k in ks):
                elem = e
                break
        # Extract standards
        stds = re.findall(r'(?:[GBDBHJ][A-Z0-9/.-]*\d{4})', p)
        clauses.append({
            'element': elem,
            'text': re.sub(r'\s+', ' ', p)[:400],
            'standards': list(set(s.replace('-','') for s in stds)),
        })
    return clauses

def extract_report_info(text):
    """Extract basic info from report"""
    info = {'industry_code': '', 'industry_name': '', 'project_type': '新建'}
    # Try to find industry
    m = re.search(r'C\d{4}', text)
    if m: info['industry_code'] = m.group()
    # Project type
    for t in ['技改', '扩建', '迁建', '搬迁', '改建']:
        if t in text[:5000]:
            info['project_type'] = {'技改':'技改','扩建':'扩建','迁建':'迁建','搬迁':'迁建','改建':'扩建'}[t]
            break
    return info

def search_in_report(report_text, clause_text, clause_element):
    """Find evidence in report matching the clause"""
    keywords = re.findall(r'[一-鿿]{3,}(?:标准|限值|排放|执行|噪声|废水|废气|类别)', clause_text)
    found = []
    flat = report_text.replace('\n', ' ').replace('\r', ' ')
    for kw in keywords[:5]:
        idx = flat.find(kw)
        if idx != -1:
            snippet = flat[max(0,idx-50):idx+len(kw)+100].strip()
            snippet = re.sub(r'\s+', ' ', snippet)
            if snippet not in found and len(snippet) > 30:
                found.append(snippet)
    return found[:3]

def generate_qa(clause, report_text, pid, report_info):
    """Generate QA pair from a clause"""
    elem = clause['element']
    text = clause['text']
    stds = clause['standards']
    report_ev = search_in_report(report_text, text, elem)

    # Generate specific question
    if elem == '噪声':
        cls = re.search(r'(\d)\s*类', text)
        cls_info = '（' + cls.group(0) + '）' if cls else ''
        q = '【区级】%s（%s %s项目）噪声执行什么标准？%s' % (pid[:20], report_info.get('industry_code','?'), report_info.get('project_type','?'), cls_info)
    elif elem == '废水':
        q = '【区级】%s（%s %s项目）废水执行什么标准？排放去向及预处理要求？' % (pid[:20], report_info.get('industry_code','?'), report_info.get('project_type','?'))
    elif elem == '废气':
        q = '【区级】%s（%s %s项目）废气污染因子有哪些？执行什么标准？治理措施？' % (pid[:20], report_info.get('industry_code','?'), report_info.get('project_type','?'))
    elif elem in ('固废','危废'):
        q = '【区级】%s（%s %s项目）%s应如何暂存和处置？执行什么标准？' % (pid[:20], report_info.get('industry_code','?'), report_info.get('project_type','?'), elem)
    elif elem == '总量':
        q = '【区级】%s（%s %s项目）总量控制指标是多少？COD和NH3-N排放量？' % (pid[:20], report_info.get('industry_code','?'), report_info.get('project_type','?'))
    else:
        q = '【区级】%s（%s %s项目）%s方面的审查要求是什么？' % (pid[:20], report_info.get('industry_code','?'), report_info.get('project_type','?'), elem)

    return {
        'qa_id': 'QA_%s_%s' % (pid, elem),
        'project_id': pid,
        'level': '区级', 'region': '佛山市顺德区',
        'industry_code': report_info.get('industry_code',''),
        'project_type': report_info.get('project_type',''),
        'element': elem,
        'review_point': '污染防治措施',
        'question': q,
        'answer': text[:400],
        'standards': stds,
        'approval_evidence': [{'source_file': pid+'_approval.pdf', 'text': text[:200]}],
        'report_evidence': [{'section': 'report', 'text': e[:200]} for e in report_ev],
        'quality_score': 0,
        'quality_issues': [],
        'need_human_review': True,
    }

# ========== Candidate Rule Generation ==========
def generate_candidate_rule(qa):
    """Generate a candidate rule from a single QA pair"""
    ic = qa.get('industry_code','?')
    elem = qa.get('element','?')
    pt = qa.get('project_type','?')
    q = qa.get('question','')
    a = qa.get('answer','')
    stds = qa.get('standards',[])

    trigger = []
    if ic: trigger.append("项目属于 %s 行业" % ic)
    if elem == '废水': trigger.extend(["项目产生废水", "项目位于工业园区或污水处理厂纳管范围内"])
    elif elem == '废气': trigger.extend(["项目存在工艺废气产生工序"])
    elif elem == '噪声': trigger.extend(["项目存在固定设备噪声源"])
    elif elem in ('固废','危废'): trigger.extend(["项目产生固体废物或危险废物"])
    elif elem == '总量': trigger.extend(["项目涉及总量控制指标"])

    checkpoints = []
    if elem == '废水':
        checkpoints = ["是否识别废水类别和主要污染因子", "是否说明预处理措施", "是否明确排放去向", "是否引用正确的排放标准"]
    elif elem == '废气':
        checkpoints = ["是否识别废气污染因子和源强", "是否说明收集方式和效率", "是否说明治理工艺", "是否引用对应标准"]
    elif elem == '噪声':
        checkpoints = ["是否说明厂界噪声标准类别", "是否与声环境功能区划一致"]
    elif elem in ('固废','危废'):
        checkpoints = ["是否识别固废/危废类别和产生量", "是否说明暂存要求", "是否说明处置去向"]

    rule_id = 'RULE_%s_%s_%s_001' % (ic, elem.upper(), pt)

    return {
        'rule_id': rule_id,
        'rule_status': 'candidate',
        'scope': {
            'level': '区级', 'region': '佛山市顺德区',
            'industry_code': ic,
            'project_type': pt,
            'element': elem,
        },
        'trigger_condition': trigger,
        'review_checkpoints': checkpoints,
        'expected_report_content': [],
        'common_approval_requirement': [a[:200]],
        'common_standards': [{'standard_code': s, 'standard_name': ''} for s in stds[:3]],
        'evidence_cases': [{
            'project_id': qa.get('project_id',''),
            'approval_text': a[:200],
            'report_text': qa.get('report_evidence',[{}])[0].get('text','') if isinstance(qa.get('report_evidence',[]), list) and len(qa['report_evidence'])>0 else '',
        }],
        'support_count': 1,
        'confidence': 0.3,
        'limitations': ['仅来自单个项目，不能视为稳定行业规律'],
        'need_human_review': True,
    }

# ========== Main Pipeline ==========
def main():
    print("="*60)
    print("Rule Pipeline: QA -> Candidate Rules -> Aggregated Rules")
    print("="*60)

    # Step 1: Read sample PDF pairs and generate QA
    all_qas = []
    all_rules = []

    for pid in ['P0001','P0002','P0003','P0004','P0005']:
        rp = os.path.join(SAMPLE_DIR, pid + '_report.pdf')
        ap = os.path.join(SAMPLE_DIR, pid + '_approval.pdf')

        if not os.path.exists(rp) or not os.path.exists(ap):
            print("Skip %s: files missing" % pid)
            continue

        print("\n--- Processing %s ---" % pid)

        # Extract texts
        report_text = extract_pdf_text(rp)
        approval_text = extract_pdf_text(ap)

        if len(report_text) < 100:
            print("  Report too short (%d chars), skip" % len(report_text))
            continue
        if len(approval_text) < 100:
            print("  Approval too short (%d chars), skip" % len(approval_text))
            continue

        print("  Report: %d chars, Approval: %d chars" % (len(report_text), len(approval_text)))

        # Extract report info
        report_info = extract_report_info(report_text)
        print("  Industry: %s, Type: %s" % (report_info['industry_code'], report_info['project_type']))

        # Extract clauses from approval
        clauses = extract_approval_clauses(approval_text)
        print("  Clauses: %d" % len(clauses))

        # Generate QA for each clause
        for ci, clause in enumerate(clauses):
            qa = generate_qa(clause, report_text, pid, report_info)
            qa['element'] = clause['element']
            qa['answer'] = clause['text']
            qa['standards'] = clause['standards']
            all_qas.append(qa)

            # Generate candidate rule
            rule = generate_candidate_rule(qa)
            rule['scope']['industry_code'] = report_info['industry_code']
            all_rules.append(rule)

        print("  Generated %d QA pairs" % len(clauses))

    print("\n=== Results ===")
    print("Total QA pairs: %d" % len(all_qas))
    print("Total candidate rules: %d" % len(all_rules))

    # Aggregate rules by industry+element+project_type
    rule_groups = defaultdict(list)
    for r in all_rules:
        key = (r['scope']['industry_code'], r['scope']['element'], r['scope']['project_type'])
        rule_groups[key].append(r)

    print("\nRule groups:")
    for key, rules in sorted(rule_groups.items()):
        print("  %s|%s|%s: %d rules" % (key[0] or '?', key[1], key[2], len(rules)))

    # ========== Save Outputs ==========
    # QA pairs
    with open(os.path.join(OUT_DIR, 'qa_pairs.json'), 'w', encoding='utf-8') as f:
        json.dump(all_qas, f, ensure_ascii=False, indent=2)
    print("\nSaved: qa_pairs.json")

    # Candidate rules
    with open(os.path.join(OUT_DIR, 'candidate_rules.json'), 'w', encoding='utf-8') as f:
        json.dump(all_rules, f, ensure_ascii=False, indent=2)
    print("Saved: candidate_rules.json")

    # Aggregated rules (merge by key)
    aggregated = []
    for key, rules in sorted(rule_groups.items()):
        ind_code, elem, proj_type = key
        support_count = len(set(r['evidence_cases'][0]['project_id'] for r in rules if r['evidence_cases']))

        ar = {
            'rule_id': 'RULE_%s_%s_%s_AGG' % (ind_code or 'X', elem.upper(), proj_type),
            'rule_status': 'strong' if support_count >= 5 else ('common' if support_count >= 3 else 'candidate'),
            'scope': {'industry_code': ind_code, 'element': elem, 'project_type': proj_type},
            'trigger_condition': rules[0]['trigger_condition'] if rules else [],
            'review_checkpoints': rules[0]['review_checkpoints'] if rules else [],
            'common_approval_requirement': list(set(r['common_approval_requirement'][0] for r in rules if r['common_approval_requirement'])),
            'common_standards': list(set(s['standard_code'] for r in rules for s in r['common_standards'])),
            'support_count': support_count,
            'confidence': min(1.0, support_count / 5),
            'evidence_cases': [r['evidence_cases'][0] for r in rules if r['evidence_cases']],
            'limitations': ['样本有限，需更多项目验证'] if support_count < 5 else [],
        }
        aggregated.append(ar)

    with open(os.path.join(OUT_DIR, 'aggregated_rules.json'), 'w', encoding='utf-8') as f:
        json.dump(aggregated, f, ensure_ascii=False, indent=2)
    print("Saved: aggregated_rules.json")

    # Aggregated rules markdown
    md_lines = ["# Aggregated Review Rules\n"]
    for ar in aggregated:
        ic = ar['scope'].get('industry_code','?') or '?'
        md_lines.append("\n## RULE: %s %s %s\n" % (ic, ar['scope'].get('element','?'), ar['scope'].get('project_type','?')))
        md_lines.append("**Status**: %s (support: %d)\n\n" % (ar['rule_status'], ar['support_count']))
        md_lines.append("**Trigger conditions**:\n")
        for t in ar['trigger_condition']:
            md_lines.append("- %s\n" % t)
        md_lines.append("\n**Review checkpoints**:\n")
        for c in ar['review_checkpoints']:
            md_lines.append("- %s\n" % c)
        if ar['common_standards']:
            md_lines.append("\n**Common standards**: %s\n" % ', '.join(ar['common_standards']))
        if ar['common_approval_requirement']:
            md_lines.append("\n**Common approval requirements**:\n")
            for req in ar['common_approval_requirement'][:2]:
                md_lines.append("- %s\n" % req[:100])
        if ar['limitations']:
            md_lines.append("\n**Limitations**:\n")
            for lim in ar['limitations']:
                md_lines.append("- %s\n" % lim)

    with open(os.path.join(OUT_DIR, 'aggregated_rules.md'), 'w', encoding='utf-8') as f:
        f.writelines(md_lines)
    print("Saved: aggregated_rules.md")

    # Quality report
    qr = {
        'total_qa': len(all_qas),
        'total_candidate_rules': len(all_rules),
        'total_aggregated_rules': len(aggregated),
        'rule_status_distribution': {},
    }
    for ar in aggregated:
        qr['rule_status_distribution'][ar['rule_status']] = qr['rule_status_distribution'].get(ar['rule_status'], 0) + 1
    with open(os.path.join(OUT_DIR, 'rule_quality_report.md'), 'w', encoding='utf-8') as f:
        f.write("# Rule Quality Report\n\n")
        f.write("Total QA: %d\n" % len(all_qas))
        f.write("Total candidate rules: %d\n" % len(all_rules))
        f.write("Total aggregated rules: %d\n" % len(aggregated))
        f.write("\nStatus distribution:\n")
        for s, n in qr['rule_status_distribution'].items():
            f.write("- %s: %d\n" % (s, n))

    print("Saved: rule_quality_report.md")

    # Human review CSV
    need_review = [r for r in all_rules if r.get('need_human_review')]
    with open(os.path.join(OUT_DIR, 'needs_human_review.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['rule_id','industry','element','status','reason'])
        for r in need_review:
            w.writerow([r['rule_id'], r['scope']['industry_code'], r['scope']['element'], r['rule_status'], 'candidate rule, needs validation'])
    print("Saved: needs_human_review.csv")

    # Neo4j triples
    triples = []
    for ar in aggregated:
        ic = ar['scope'].get('industry_code','?') or '?'
        elem = ar['scope'].get('element','?')
        pt = ar['scope'].get('project_type','?')
        # Industry -> Element
        triples.append({'head':'%s' % ic, 'relation':'涉及要素', 'tail':elem, 'industry':ic, 'evidence':'aggregated rule'})
        # Element -> Standards
        for s in ar['common_standards'][:3]:
            triples.append({'head':elem, 'relation':'执行标准', 'tail':s, 'industry':ic, 'evidence':'aggregated rule'})
        # Checkpoints
        for cp in ar['review_checkpoints'][:2]:
            triples.append({'head':'审核检查点', 'relation':'针对要素', 'tail':cp, 'industry':ic, 'evidence':'aggregated rule'})

    with open(os.path.join(OUT_DIR, 'neo4j_triples.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['head','relation','tail','industry','evidence','source_type'])
        for t in triples:
            w.writerow([t['head'], t['relation'], t['tail'], t['industry'], t['evidence'], 'rule'])
    print("Saved: neo4j_triples.csv")

    print("\nDone! All outputs in %s" % OUT_DIR)

if __name__ == '__main__':
    main()
