# -*- coding: utf-8 -*-
"""Match reports to approvals using weighted record linkage (rapidfuzz). Optimized with blocking."""
import sys, json, re, os, csv
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
from rapidfuzz import fuzz
from collections import defaultdict
import time

OUT = r"E:\软件\outputs\pair_cleaning"
os.makedirs(OUT, exist_ok=True)

t0 = time.time()
reports = pd.read_csv(os.path.join(OUT, 'report_records.csv'), encoding='utf-8-sig')
approvals = pd.read_csv(os.path.join(OUT, 'approval_records.csv'), encoding='utf-8-sig')

# Filter to ones with company names
reports = reports[reports['company'].notna() & (reports['company'] != '')].reset_index(drop=True)
approvals = approvals[approvals['company'].notna() & (approvals['company'] != '')].reset_index(drop=True)
print(f"Reports: {len(reports)}, Approvals: {len(approvals)} (loaded in {time.time()-t0:.0f}s)")

def get_cn(text):
    return ''.join(re.findall(r'[一-鿿]', str(text)))

def company_sim(c1, c2):
    c1_cn, c2_cn = get_cn(c1), get_cn(c2)
    if not c1_cn or not c2_cn: return 0
    if c1_cn == c2_cn: return 100
    return max(fuzz.partial_ratio(c1_cn, c2_cn), fuzz.token_sort_ratio(c1_cn, c2_cn))

def project_name_sim(t1, t2):
    s1, s2 = get_cn(str(t1)[:300]), get_cn(str(t2)[:300])
    if not s1 or not s2: return 0
    return fuzz.partial_ratio(s1, s2)

def exact_match(v1, v2):
    return 100 if str(v1).strip() == str(v2).strip() else 0

def date_valid(rd, ad):
    try:
        return 100 if str(rd)[:10] <= str(ad)[:10] else 0
    except:
        return 50

# Blocking: group approvals by town + first 4 Chinese chars of company
print("Building blocks...")
blocks = defaultdict(list)
for idx, row in approvals.iterrows():
    cn4 = get_cn(row.get('company',''))[:4]
    town = str(row.get('town','')).strip()
    # Primary block key
    for key in [town, cn4, 'fallback']:
        if key:
            blocks[key].append(idx)
            break

print(f"Blocks: {len(blocks)} unique keys")
t1 = time.time()

# Matching
pairs = []
matched_a = set()
report_count = len(reports)

for ri in range(report_count):
    report = reports.iloc[ri]
    r_cn4 = get_cn(report.get('company',''))[:4]
    r_town = str(report.get('town','')).strip()

    # Determine which blocks to search
    search_keys = []
    if r_town and r_town in blocks: search_keys.append(r_town)
    if r_cn4 and r_cn4 in blocks: search_keys.append(r_cn4)
    if not search_keys:
        search_keys = ['fallback'] if 'fallback' in blocks else []

    if ri % 100 == 0:
        elapsed = time.time() - t1
        rate = ri / elapsed if elapsed > 0 else 0
        print(f"  report {ri}/{report_count} ({rate:.0f}/s)")

    best_score, best_ai = 0, None
    for key in search_keys:
        for ai in blocks.get(key, []):
            if ai in matched_a:
                continue
            approval = approvals.iloc[ai]
            c_sim = company_sim(report.get('company',''), approval.get('company',''))
            if c_sim < 30:
                continue
            p_sim = project_name_sim(report.get('text_sample',''), approval.get('text_sample',''))
            rt_m = exact_match(report.get('report_type',''), approval.get('report_type_referenced',''))
            pt_m = exact_match(report.get('project_type',''), approval.get('project_type',''))
            t_m = exact_match(report.get('town',''), approval.get('town',''))
            d_v = date_valid(report.get('date',''), approval.get('approval_date',''))
            score = (c_sim * 0.40 + p_sim * 0.35 + rt_m * 0.10 +
                     pt_m * 0.05 + t_m * 0.05 + d_v * 0.05)
            if score > best_score:
                best_score, best_ai = score, ai

    if best_ai is not None:
        approval = approvals.iloc[best_ai]
        c_sim_final = company_sim(report.get('company',''), approval.get('company',''))
        # Company exact match on Chinese chars = clean regardless
        is_clean = c_sim_final >= 90 or best_score >= 90
        if is_clean or best_score >= 80:
            pairs.append({
                'report_file': report.get('report_file',''),
                'report_company': report.get('company',''),
                'approval_file': approval.get('approval_file',''),
                'approval_company': approval.get('company',''),
                'company_similarity': round(c_sim_final, 1),
                'match_score': round(best_score, 1),
                'pair_status': 'clean' if is_clean else 'needs_review',
            })
            if is_clean:
                matched_a.add(best_ai)

t2 = time.time()
print(f"\nMatching completed in {t2-t1:.0f}s")

# Outputs
clean = [p for p in pairs if p['pair_status'] == 'clean']
needs_review = [p for p in pairs if p['pair_status'] == 'needs_review']

clean_files = set(p['report_file'] for p in clean)
needs_files = set(p['report_file'] for p in needs_review)

unmatched_reports = reports[~reports['report_file'].isin(clean_files | needs_files)]
matched_af = set(p['approval_file'] for p in pairs)
unmatched_approvals = approvals[~approvals['approval_file'].isin(matched_af)]

print(f"\nClean pairs (>=90): {len(clean)}")
print(f"Needs review (80-89): {len(needs_review)}")
print(f"Unmatched reports: {len(unmatched_reports)}")
print(f"Unmatched approvals: {len(unmatched_approvals)}")

def save_csv(data, path):
    if not data: return
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=data[0].keys())
        w.writeheader()
        for d in data:
            w.writerow(d)
    print(f"Saved: {path} ({len(data)})")

save_csv(clean, os.path.join(OUT, 'clean_pairs.csv'))
save_csv(needs_review, os.path.join(OUT, 'candidate_pairs_needs_review.csv'))
save_csv(pairs, os.path.join(OUT, 'mismatch_pairs.csv'))
unmatched_reports.to_csv(os.path.join(OUT, 'unmatched_reports.csv'), index=False, encoding='utf-8-sig')
unmatched_approvals.to_csv(os.path.join(OUT, 'unmatched_approvals.csv'), index=False, encoding='utf-8-sig')

print(f"\nTotal time: {time.time()-t0:.0f}s")
