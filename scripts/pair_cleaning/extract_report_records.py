# -*- coding: utf-8 -*-
"""Extract records from report PDFs using MinerU-parsed markdown"""
import sys, json, re, os, csv
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

EXTRACTED_DIR = r"E:\软件\mineru_extracted"
OUT = r"E:\软件\outputs\pair_cleaning"
os.makedirs(OUT, exist_ok=True)

def extract_company(text):
    """Extract company name from report markdown first lines"""
    for line in text.split('\n')[:50]:
        # Look for construction_unit or company pattern
        m = re.search(r'(?:建设单位|建设方|项目单位)[：:]\s*(\S{4,30}(?:有限公司|厂|经营部|公司))', line)
        if m: return m.group(1)
        # Also try: 某某公司
        m = re.search(r'(?:关于|佛山市?\S{2,20}(?:有限公司|厂|经营部|公司))', line)
        if m: return m.group(0).replace('关于','')
    return ''

def extract_industry(text):
    m = re.search(r'C\d{4}', text)
    return m.group(0) if m else ''

def extract_town(text):
    # Very simple: check for 镇/街道 names in Shunde
    towns = ['大良','容桂','伦教','勒流','陈村','北滘','乐从','龙江','杏坛','均安']
    for t in towns:
        if t in text[:3000]:
            return t
    return ''

def extract_project_type(text):
    for t in ['技改','扩建','迁建','搬迁','改建']:
        if t in text[:2000]:
            return {'技改':'技改','扩建':'扩建','迁建':'迁建','搬迁':'迁建','改建':'扩建'}[t]
    return '新建'

def extract_report_type(text):
    if '报告书' in text[:2000]: return '报告书'
    if '报告表' in text[:2000]: return '报告表'
    return ''

def extract_date(text):
    m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text[:500])
    if m: return '%s-%s-%s' % (m.group(1), m.group(2).zfill(2), m.group(3).zfill(2))
    m = re.search(r'(\d{4})', text[:200])
    if m: return m.group(1)
    return ''

def main():
    records = []
    # Read all MinerU-extracted markdown files
    for folder in sorted(os.listdir(EXTRACTED_DIR)):
        md_path = os.path.join(EXTRACTED_DIR, folder, 'full.md')
        if not os.path.exists(md_path):
            continue
        with open(md_path, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()

        if len(text) < 200:
            continue

        # Extract fields
        company = extract_company(text)
        industry = extract_industry(text)
        town = extract_town(text)
        proj_type = extract_project_type(text)
        report_type = extract_report_type(text)
        date_str = extract_date(text)

        records.append({
            'report_file': os.path.join(EXTRACTED_DIR, folder, 'full.md'),
            'original_pdf_guess': folder.replace('_mineru','') + '.pdf',
            'company': company,
            'industry': industry,
            'town': town,
            'project_type': proj_type,
            'report_type': report_type,
            'date': date_str,
            'text_sample': text[:500],
        })

    print("Extracted %d report records" % len(records))

    # Save
    with open(os.path.join(OUT, 'report_records.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['report_file','original_pdf_guess','company','industry',
                                           'town','project_type','report_type','date','text_sample'])
        w.writeheader()
        for r in records:
            w.writerow(r)

    # Stats
    from collections import Counter
    with_company = sum(1 for r in records if r['company'])
    with_industry = sum(1 for r in records if r['industry'])
    print("  With company: %d, With industry: %d" % (with_company, with_industry))
    print("Saved: report_records.csv")

if __name__ == '__main__':
    main()
