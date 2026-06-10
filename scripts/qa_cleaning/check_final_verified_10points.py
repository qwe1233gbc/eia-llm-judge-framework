# -*- coding: utf-8 -*-
"""10-point rigorous check on qa_v4_final_verified.jsonl"""
import sys, json, re, os
sys.stdout.reconfigure(encoding='utf-8')

BASE = r"E:\软件"
DATA = os.path.join(BASE, "eia-llm-judge-framework/data/qa_v4")
IN_FILE = os.path.join(DATA, "qa_v4_final_verified.jsonl")
OUT_DIR = os.path.join(BASE, "outputs/final_verified_check")
os.makedirs(OUT_DIR, exist_ok=True)

with open(IN_FILE, encoding='utf-8') as f:
    items = [json.loads(line) for line in f if line.strip()]
print("Loaded: %d" % len(items))

keep = []
demote = []
results = []

for qa in items:
    issues = []
    company = qa.get('company','') or ''
    af = qa.get('approval_file','') or ''
    ae_list = qa.get('approval_evidence',[]) or []
    ae_source = ae_list[0].get('source','') if ae_list and isinstance(ae_list[0], dict) else ''
    oq = qa.get('original_question','') or qa.get('question','')
    answer = qa.get('answer','') or ''
    ev_list = qa.get('report_evidence',[]) or []
    ev_text = ' '.join([e.get('text','') if isinstance(e,dict) else str(e) for e in ev_list])
    ae_text = ' '.join([e.get('text','') if isinstance(e,dict) else str(e) for e in ae_list])
    stds_norm = qa.get('standards_normalized',[]) or []
    elem = qa.get('element','')
    score = qa.get('corrected_quality_score',0)
    qa_issues = qa.get('quality_issues',[]) or []
    ea = qa.get('evidence_alignment',{}) or {}
    co_chars = ''.join(re.findall(r'[一-鿿]+', company))[:6]

    # ============ CHECK 1: company in approval_file or approval_evidence.source ============
    in_af = co_chars and co_chars in af
    in_ae = co_chars and co_chars in ae_source
    if not (in_af or in_ae):
        issues.append("c1_company_not_in_approval_source")

    # ============ CHECK 2: approval_file, approval_evidence.source, company consistent ============
    if in_af and in_ae:
        # Extract company chars from each source
        af_chars = ''.join(re.findall(r'[一-鿿]+', af))[:6]
        ae_chars = ''.join(re.findall(r'[一-鿿]+', ae_source))[:6]
        if af_chars and ae_chars and af_chars != ae_chars:
            issues.append("c2_approval_source_mismatch")

    # ============ CHECK 3: original_question company must match ============
    oq_companies = re.findall(r'(?:关于|佛山市?\S{2,15}(?:有限公司|厂|经营部|公司))', oq)
    for oc in oq_companies:
        oc_chars = ''.join(re.findall(r'[一-鿿]+', oc))[:6]
        if oc_chars and oc_chars != co_chars and len(oc_chars) >= 4:
            issues.append("c3_question_company_mismatch")
            break

    # ============ CHECK 4: quality_issues with company_mismatch → demote ============
    if any('company' in i.lower() or 'mismatch' in i.lower() for i in qa_issues):
        issues.append("c4_company_mismatch_flagged")

    # ============ CHECK 5: evidence_alignment=high verification ============
    if ea.get('level') == 'high':
        # Check answer key terms in approval_evidence
        key_terms = re.findall(r'[A-Z]{1,3}[\d/-]+[\d-]*', answer)[:3]
        cn_terms = re.findall(r'[一-鿿]{4,}(?:标准|排放|限值|执行|废[水气]|噪声)', answer)[:3]
        all_terms = key_terms + cn_terms
        ans_in_ae = sum(1 for t in all_terms if t in ae_text)
        ans_in_ev = sum(1 for t in all_terms if t in ev_text)
        if ans_in_ae < 1:
            issues.append("c5_high_ae_no_key_terms")
        if ans_in_ev < 1:
            issues.append("c5_high_ev_no_key_terms")

    # ============ CHECK 6: report_evidence discharge route vs answer ============
    # Extract discharge destinations from both
    dest_answer = re.findall(r'排入\S{2,10}(?:污水厂|处理厂|管网|水体|河流|海域)', answer)
    dest_evidence = re.findall(r'排入\S{2,10}(?:污水厂|处理厂|管网|水体|河流|海域)', ev_text)
    if dest_answer and dest_evidence:
        if dest_answer[0][:8] != dest_evidence[0][:8]:
            issues.append("c6_discharge_mismatch")

    # ============ CHECK 7: standards_normalized only relevant to this QA ============
    valid_stds = []
    for s in stds_norm:
        code = s.get('standard_code','') if isinstance(s,dict) else ''
        code = code.strip()
        # CHECK 8: delete empty codes
        if not code:
            continue
        # CHECK 9: delete DA001, DA002, G1, G2 etc.
        if code in ('DA001','DA002','DA003','DA004','DA005','G1','G2','G3','DB44','DB','HJ'):
            continue
        if len(code) < 5:
            continue
        # Only keep if code appears in answer or evidence
        if code in answer or code[:10] in ae_text or code[:10] in ev_text:
            valid_stds.append(s)
        else:
            issues.append("c7_std_not_in_answer_%s" % code[:15])
    qa['standards_normalized'] = valid_stds

    # ============ CHECK 10: score 100 only for perfect ============
    if score == 100 and issues:
        issues.append("c10_score_100_with_issues")

    qa['_check_issues'] = issues
    if issues:
        qa['_check_result'] = 'demoted'
        demote.append(qa)
    else:
        qa['_check_result'] = 'verified'
        keep.append(qa)

# ============ Results ============
from collections import Counter
ic = Counter()
for q in demote:
    for i in q.get('_check_issues',[]):
        ic[i] += 1

print("\n=== Results ===")
print("Keep verified: %d" % len(keep))
print("Demoted: %d" % len(demote))
print("\nIssue distribution:")
for i, n in ic.most_common():
    print("  %s: %d" % (i, n))

# Save
with open(os.path.join(DATA, 'qa_v4_final_verified.jsonl'), 'w', encoding='utf-8') as f:
    for q in keep:
        f.write(json.dumps(q, ensure_ascii=False) + '\n')
with open(os.path.join(DATA, 'qa_v4_demoted.jsonl'), encoding='utf-8') as f:
    existing = [json.loads(l) for l in f if l.strip()]
all_demoted = existing + demote
with open(os.path.join(DATA, 'qa_v4_demoted.jsonl'), 'w', encoding='utf-8') as f:
    for q in all_demoted:
        f.write(json.dumps(q, ensure_ascii=False) + '\n')

print("\nUpdated: final_verified=%d demoted=%d" % (len(keep), len(all_demoted)))
print("Done!")
