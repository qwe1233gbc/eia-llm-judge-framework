# -*- coding: utf-8 -*-
"""Phase 2: Re-score existing QA pairs with GPT's 5-dimension framework"""
import sys, json, re, os, csv
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

QA_FILES = [
    r"E:\软件\outputs\qa_batch_full\qa_batch_full.json",
    r"E:\软件\outputs\qa_foshan\foshan_qa.json",
]

OUT_DIR = r"E:\软件\outputs\quality_v2"
os.makedirs(OUT_DIR, exist_ok=True)

def score_evidence_grounding(qa):
    """是否有报告和批复双证据"""
    a = qa.get('answer', '')
    e = qa.get('report_evidence', [])
    s = qa.get('standards', [])
    score = 30  # base
    if len(a) > 50: score += 15
    if s: score += 20
    clean_ev = [x for x in e if x and 'td>' not in x and len(x) > 20]
    if clean_ev: score += 25
    if clean_ev and s: score += 10  # both evidence and standards
    return min(100, score)

def score_specificity(qa):
    """问题和规则是否具体"""
    q = qa.get('question', '')
    a = qa.get('answer', '')
    score = 30
    # Check if question contains specific elements
    if '标准' in q: score += 10
    if '多少' in q or '类别' in q or '类标准' in q: score += 10
    if '排放' in q or '去向' in q or '限值' in q: score += 10
    if len(q) > 30: score += 10
    if '标准' in a: score += 10
    # Check for GB/DB numbers
    if re.search(r'[GBDB]\w+', a): score += 20
    return min(100, score)

def score_professional(qa):
    """标准、污染因子、治理措施是否专业正确"""
    a = qa.get('answer', '')
    s = qa.get('standards', [])
    score = 30
    if s: score += 25
    # Check for proper standard format
    valid_stds = [x for x in s if re.match(r'[A-Z]{2}\d+', x)]
    if valid_stds: score += 15
    if '执行' in a: score += 10
    if '排放' in a: score += 10
    if '标准' in a: score += 10
    return min(100, score)

def score_generalization(qa):
    """是否避免从单个样本过度外推"""
    v = qa.get('validation', '')
    if v == '已验证': return 90
    if v and '参考' in v: return 60
    return 50  # no validation info

def score_review_usefulness(qa):
    """是否能转化为后续审核检查点"""
    q = qa.get('question', '')
    a = qa.get('answer', '')
    s = qa.get('standards', [])
    score = 30
    # Useful questions have specific review focus
    for kw in ['标准', '排放', '限值', '处理', '措施', '总量', '识别', '因子', '监测', '验收']:
        if kw in q: score += 7
    if s: score += 15
    if len(a) > 100: score += 10  # detailed answer
    return min(100, score)

def main():
    all_qas = []
    for path in QA_FILES:
        with open(path, encoding='utf-8') as f:
            qas = json.load(f)
        label = '区级' if 'batch_full' in path else '市级'
        for q in qas:
            q['_src'] = label
        all_qas.extend(qas)
        print("Loaded %d from %s" % (len(qas), path))

    results = []
    for qa in all_qas:
        scores = {
            "evidence_grounding": score_evidence_grounding(qa),
            "specificity": score_specificity(qa),
            "professional_correctness": score_professional(qa),
            "generalization_control": score_generalization(qa),
            "review_usefulness": score_review_usefulness(qa),
        }
        overall = sum(scores.values()) / 5
        issues = []
        if scores['evidence_grounding'] < 60: issues.append("evidence_grounding")
        if scores['specificity'] < 60: issues.append("specificity")
        if scores['professional_correctness'] < 60: issues.append("professional_correctness")
        if scores['review_usefulness'] < 60: issues.append("review_usefulness")

        qa['quality_scores'] = scores
        qa['quality_overall'] = round(overall, 1)
        qa['quality_issues'] = issues
        qa['need_human_review'] = overall < 70

        results.append({
            'company': qa.get('company','')[:15],
            'industry': qa.get('industry_code',''),
            'element': qa.get('element',''),
            'overall': round(overall, 1),
            'scores': scores,
            'issues': issues,
            'need_review': overall < 70,
        })

    # Stats
    print("\n=== Quality Reassessment Results ===")
    print("Total: %d" % len(results))
    print("Avg overall: %.1f" % (sum(r['overall'] for r in results) / len(results)))

    grades = {'A(>=80)':0, 'B(60-79)':0, 'C(40-59)':0, 'D(<40)':0}
    for r in results:
        o = r['overall']
        if o >= 80: grades['A(>=80)'] += 1
        elif o >= 60: grades['B(60-79)'] += 1
        elif o >= 40: grades['C(40-59)'] += 1
        else: grades['D(<40)'] += 1

    for g, n in grades.items():
        print("  %s: %d (%.0f%%)" % (g, n, n/len(results)*100))

    need_review = [r for r in results if r['need_review']]
    print("\nNeed human review: %d (%.0f%%)" % (len(need_review), len(need_review)/len(results)*100))

    # Top issues
    issue_counts = defaultdict(int)
    for r in results:
        for iss in r['issues']:
            issue_counts[iss] += 1
    print("\nIssue distribution:")
    for iss, n in sorted(issue_counts.items(), key=lambda x:-x[1]):
        print("  %s: %d" % (iss, n))

    # Save results
    # Update QA files
    for path in QA_FILES:
        with open(path, encoding='utf-8') as f:
            qas = json.load(f)
        label = '区级' if 'batch_full' in path else '市级'
        src_qas = [q for q in all_qas if q.get('_src') == label]
        for q in qas:
            for sq in src_qas:
                if (q.get('company')==sq.get('company') and
                    q.get('element')==sq.get('element') and
                    q.get('clause_index')==sq.get('clause_index')):
                    q['quality_scores'] = sq.get('quality_scores', {})
                    q['quality_overall'] = sq.get('quality_overall', 0)
                    q['quality_issues'] = sq.get('quality_issues', [])
                    q['need_human_review'] = sq.get('need_human_review', False)
                    break
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(qas, f, ensure_ascii=False, indent=2)
        print("\nUpdated: %s" % path)

    # Save human review list
    csv_path = os.path.join(OUT_DIR, 'needs_human_review.csv')
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['company','industry','element','overall','issues'])
        for r in need_review:
            w.writerow([r['company'], r['industry'], r['element'], r['overall'], ';'.join(r['issues'])])
    print("Saved: %s" % csv_path)

    # Save quality report
    with open(os.path.join(OUT_DIR, 'quality_report.json'), 'w', encoding='utf-8') as f:
        json.dump({
            'total': len(results),
            'avg_overall': round(sum(r['overall'] for r in results)/len(results), 1),
            'grade_distribution': grades,
            'need_human_review': len(need_review),
            'issue_distribution': dict(issue_counts),
        }, f, ensure_ascii=False, indent=2)
    print("Saved: quality_report.json")
    print("\nDone!")

if __name__ == '__main__':
    main()
