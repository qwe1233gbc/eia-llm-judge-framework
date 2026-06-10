# -*- coding: utf-8 -*-
"""Run evidence audit on ALL 92 verified QA pairs, move mismatches, create final_verified"""
import sys, json, re, os, fitz
sys.stdout.reconfigure(encoding='utf-8')

BASE = r"E:\软件"
VERIFIED_FILE = os.path.join(BASE, "eia-llm-judge-framework/data/qa_v4/qa_v4_verified.jsonl")
DEMOTED_FILE = os.path.join(BASE, "eia-llm-judge-framework/data/qa_v4/qa_v4_demoted.jsonl")
ALL_SCORED = os.path.join(BASE, "eia-llm-judge-framework/data/qa_v4/qa_v4_all_scored.jsonl")
FINAL_VERIFIED = os.path.join(BASE, "eia-llm-judge-framework/data/qa_v4/qa_v4_final_verified.jsonl")
EXTRACTED_DIR = os.path.join(BASE, "mineru_extracted")
APPROVAL_DIR = os.path.join(BASE, "2023-2026年顺德批复文件")
PROJ_INDEX = os.path.join(BASE, "outputs/eia_industry_pattern/project_index.jsonl")

projs = {}
with open(PROJ_INDEX, encoding='utf-8') as f:
    for line in f:
        p = json.loads(line)
        projs[p['project_id']] = p

def find_report_md(pid, company):
    proj = projs.get(pid, {})
    for key in ['file_name', 'source_file']:
        v = proj.get(key, '')
        if v:
            base = os.path.splitext(os.path.basename(v))[0]
            fp = os.path.join(EXTRACTED_DIR, base, 'full.md')
            if os.path.exists(fp): return fp
    co_chars = ''.join(re.findall(r'[一-鿿]+', company))[:6]
    for d in os.listdir(EXTRACTED_DIR):
        if co_chars and co_chars in d:
            fp = os.path.join(EXTRACTED_DIR, d, 'full.md')
            if os.path.exists(fp): return fp
    return None

def find_approval(company, approval_fn):
    co_chars = ''.join(re.findall(r'[一-鿿]+', company))[:6]
    if not co_chars: return None, None
    if approval_fn:
        fp = os.path.join(APPROVAL_DIR, approval_fn)
        if os.path.exists(fp): return fp, approval_fn
    for fn in os.listdir(APPROVAL_DIR):
        if co_chars in fn:
            return os.path.join(APPROVAL_DIR, fn), fn
    return None, None

def pdf_to_text(path):
    try:
        doc = fitz.open(path)
        text = ''.join(p.get_text() for p in doc)
        doc.close()
        return text
    except:
        return ''

with open(VERIFIED_FILE, encoding='utf-8') as f:
    verified = [json.loads(line) for line in f if line.strip()]
print("Verified loaded: %d" % len(verified))

all_issues = {}
final_verified = []
new_demoted = []

for qa in verified:
    pid = qa.get('project_id','')
    company = qa.get('company','') or ''
    elem = qa.get('element','')
    qid = pid + '_' + elem
    af = qa.get('approval_file','')
    answer = qa.get('answer','') or ''
    ev_list = qa.get('report_evidence',[]) or []
    errors = []

    # 1. company in report.md
    report_src = find_report_md(pid, company)
    company_in_report = False
    evidence_in_report = False
    if report_src:
        with open(report_src, 'r', encoding='utf-8', errors='replace') as f:
            rtext = f.read()
        co_chars = ''.join(re.findall(r'[一-鿿]+', company))[:6]
        company_in_report = co_chars and co_chars in rtext
        if not company_in_report:
            errors.append("company_not_in_report")
        for ev in ev_list[:3]:
            et = ev.get('text','') if isinstance(ev,dict) else str(ev)
            if et[:50] in rtext:
                evidence_in_report = True
                break
        if not evidence_in_report:
            errors.append("evidence_not_in_report")
    else:
        errors.append("report_md_not_found")

    # 2. company + answer in approval
    approval_src, actual_fn = find_approval(company, af)
    company_in_approval = False
    answer_in_approval = False
    if approval_src:
        atext = pdf_to_text(approval_src)
        co_chars = ''.join(re.findall(r'[一-鿿]+', company))[:6]
        company_in_approval = co_chars and co_chars in atext
        if not company_in_approval:
            errors.append("company_not_in_approval")
        terms = re.findall(r'[A-Z]{1,3}[\d/—-]+[\d-]*', answer)[:3]
        cn_terms = re.findall(r'[一-鿿]{4,}(?:标准|排放|限值)', answer)[:3]
        for t in (terms + cn_terms):
            if t and t in atext:
                answer_in_approval = True
                break
        if not answer_in_approval:
            errors.append("answer_not_in_approval")
    else:
        errors.append("approval_not_found")

    # 3. approval filename vs company
    if actual_fn:
        co_chars = ''.join(re.findall(r'[一-鿿]+', company))[:6]
        if co_chars and co_chars not in actual_fn:
            errors.append("company_mismatch_approval_file")

    if errors:
        new_demoted.append(qa)
        all_issues[qid] = errors
    else:
        final_verified.append(qa)

print("\n=== Results ===")
print("Final verified: %d" % len(final_verified))
print("New demoted: %d" % len(new_demoted))

from collections import Counter
ic = Counter()
for qid, errs in all_issues.items():
    for e in errs:
        ic[e] += 1
print("\nIssue distribution:")
for e, n in ic.most_common():
    print("  %s: %d" % (e, n))

# Save final_verified.jsonl
with open(FINAL_VERIFIED, 'w', encoding='utf-8') as f:
    for q in final_verified:
        f.write(json.dumps(q, ensure_ascii=False) + '\n')
print("\nSaved: final_verified.jsonl (%d)" % len(final_verified))

# Update verified.jsonl (replace with only final_verified)
with open(VERIFIED_FILE, 'w', encoding='utf-8') as f:
    for q in final_verified:
        f.write(json.dumps(q, ensure_ascii=False) + '\n')
print("Updated: verified.jsonl -> %d (final_verified only)" % len(final_verified))

# Update demoted.jsonl (append new demoted)
existing_demoted = []
if os.path.exists(DEMOTED_FILE):
    with open(DEMOTED_FILE, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                existing_demoted.append(json.loads(line))
all_demoted = existing_demoted + new_demoted
with open(DEMOTED_FILE, 'w', encoding='utf-8') as f:
    for q in all_demoted:
        f.write(json.dumps(q, ensure_ascii=False) + '\n')
print("Updated: demoted.jsonl -> %d total" % len(all_demoted))

# Update all_scored.jsonl with final_validation
final_ids = set(q.get('project_id','') + '_' + q.get('element','') for q in final_verified)
demoted_ids = set(q.get('project_id','') + '_' + q.get('element','') for q in new_demoted)

all_scored = []
with open(ALL_SCORED, encoding='utf-8') as f:
    for line in f:
        if line.strip():
            q = json.loads(line)
            qid = q.get('project_id','') + '_' + q.get('element','')
            if qid in final_ids:
                q['final_validation'] = 'final_verified'
            elif qid in demoted_ids:
                q['final_validation'] = 'demoted_by_audit'
            else:
                q['final_validation'] = q.get('corrected_validation', 'unknown')
            all_scored.append(q)

with open(ALL_SCORED, 'w', encoding='utf-8') as f:
    for q in all_scored:
        f.write(json.dumps(q, ensure_ascii=False) + '\n')
print("Updated: all_scored.jsonl with final_validation")

print("\nDone!")
