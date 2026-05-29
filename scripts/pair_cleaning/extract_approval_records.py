# -*- coding: utf-8 -*-
"""Extract records from approval PDFs"""
import sys, json, re, os, csv
sys.stdout.reconfigure(encoding='utf-8')
import fitz

APPROVAL_DIR = r"E:\软件\2023-2026年顺德批复文件"
OUT = r"E:\软件\outputs\pair_cleaning"
os.makedirs(OUT, exist_ok=True)

def extract_approval_record(filepath):
    fn = os.path.basename(filepath)
    try:
        doc = fitz.open(filepath)
        text = ''
        for p in doc:
            text += p.get_text()
        doc.close()
    except:
        return {'approval_file': fn, 'error': 'unreadable'}

    first_page = text[:1500]

    # Extract company: 某某公司：
    company = ''
    m = re.search(r'(佛山市?\S{2,30}(?:有限公司|厂|经营部|公司))\s*[：:]', first_page)
    if m: company = m.group(1)
    if not company:
        m = re.search(r'关于(.+?)(?:新建|扩建|迁建|技改|建设|技术)', first_page)
        if m: company = m.group(1).strip()

    # Document number
    doc_no = ''
    m = re.search(r'(佛环[^。\s]{5,30})', fn)
    if m: doc_no = m.group(1)
    if not doc_no:
        m = re.search(r'(佛环[^。\s]{5,30})', first_page)
        if m: doc_no = m.group(1)

    # Approval date
    date_str = ''
    m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', first_page)
    if m: date_str = '%s-%s-%s' % (m.group(1), m.group(2).zfill(2), m.group(3).zfill(2))

    # Report type referenced
    report_type = ''
    if '报告书' in first_page: report_type = '报告书'
    elif '报告表' in first_page: report_type = '报告表'

    # Project type
    proj_type = '新建'
    for t in ['扩建','迁建','技改','改建','搬迁']:
        if t in first_page[:500]:
            proj_type = {'扩建':'扩建','迁建':'迁建','技改':'技改','改建':'扩建','搬迁':'迁建'}[t]
            break

    # Town
    town = ''
    towns = ['大良','容桂','伦教','勒流','陈村','北滘','乐从','龙江','杏坛','均安']
    for t in towns:
        if t in first_page:
            town = t
            break

    return {
        'approval_file': fn,
        'company': company,
        'doc_no': doc_no,
        'approval_date': date_str,
        'report_type_referenced': report_type,
        'project_type': proj_type,
        'town': town,
        'text_sample': first_page[:500],
    }

def main():
    records = []
    files = [f for f in os.listdir(APPROVAL_DIR) if f.endswith('.pdf')]
    print("Processing %d approval files..." % len(files))

    for i, fn in enumerate(files):
        fp = os.path.join(APPROVAL_DIR, fn)
        rec = extract_approval_record(fp)
        records.append(rec)
        if (i+1) % 500 == 0:
            print("  %d/%d done..." % (i+1, len(files)))

    # Stats
    with_company = sum(1 for r in records if r.get('company'))
    with_doc = sum(1 for r in records if r.get('doc_no'))
    print("\nExtracted %d records" % len(records))
    print("  With company: %d, With doc_no: %d" % (with_company, with_doc))

    # Save
    with open(os.path.join(OUT, 'approval_records.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['approval_file','company','doc_no','approval_date',
                                           'report_type_referenced','project_type','town','text_sample'])
        w.writeheader()
        for r in records:
            w.writerow(r)
    print("Saved: approval_records.csv")

if __name__ == '__main__':
    main()
