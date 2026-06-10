# -*- coding: utf-8 -*-
"""Generate QA provenance report - maps each QA to its source files and evidence"""
import sys, json, os
sys.stdout.reconfigure(encoding='utf-8')

QA_FILE = r"E:\软件\outputs\qa_v2\qa_v2.json"
OUT_DIR = r"E:\软件\outputs\qa_provenance"
os.makedirs(OUT_DIR, exist_ok=True)

with open(QA_FILE, encoding='utf-8') as f:
    qas = json.load(f)

md_lines = ["# QA Pair Provenance Report\n"]
md_lines.append("Maps each QA pair to its source approval file and report evidence.\n\n")
md_lines.append("Total QA pairs: %d\n\n" % len(qas))
md_lines.append("| # | QA ID | Company | Industry | Element | Project Type | Approval File | Standards | Quality |\n")
md_lines.append("|---|-------|---------|----------|---------|-------------|---------------|----------|--------|\n")

for idx, qa in enumerate(qas):
    af = qa.get('approval_file', 'N/A')[:50]
    stds = ';'.join(qa.get('standards', [])[:3])
    qs = qa.get('quality_score', '?')
    md_lines.append("| %d | QA_%s_%s | %s | %s | %s | %s | %s | %s | %d |\n" % (
        idx+1,
        qa.get('project_id','?'),
        qa.get('element','?'),
        qa.get('company','')[:20],
        qa.get('industry_code','?'),
        qa.get('element','?'),
        qa.get('project_type','?'),
        af,
        stds[:30],
        qs if isinstance(qs, int) else 0,
    ))

# Detail section
md_lines.append("\n\n## Detailed Evidence by QA Pair\n\n")
for idx, qa in enumerate(qas):
    md_lines.append("### QA#%d: %s\n" % (idx+1, qa.get('question','')[:100]))
    md_lines.append("**Project**: %s | **Industry**: %s | **Element**: %s | **Type**: %s\n" % (
        qa.get('project_id','?'), qa.get('industry_code','?'),
        qa.get('element','?'), qa.get('project_type','?')))
    md_lines.append("**Approval File**: %s\n" % qa.get('approval_file', 'N/A'))
    md_lines.append("**Standards**: %s\n" % ', '.join(qa.get('standards', [])))
    md_lines.append("**Question**: %s\n" % qa['question'])
    md_lines.append("**Answer**: %s\n" % qa['answer'][:300])

    # Evidence
    ev = qa.get('report_evidence', [])
    if ev:
        md_lines.append("**Report Evidence**:\n")
        for e in ev[:2]:
            txt = e.get('text','')[:200] if isinstance(e, dict) else str(e)[:200]
            md_lines.append("> %s\n" % txt)

    md_lines.append("\n---\n")

with open(os.path.join(OUT_DIR, 'qa_provenance_report.md'), 'w', encoding='utf-8') as f:
    f.writelines(md_lines)

# Also save a JSON mapping
mapping = []
for idx, qa in enumerate(qas):
    mapping.append({
        'qa_num': idx+1,
        'project_id': qa.get('project_id',''),
        'approval_file': qa.get('approval_file',''),
        'company': qa.get('company',''),
        'industry': qa.get('industry_code',''),
        'element': qa.get('element',''),
        'standards': qa.get('standards', []),
        'question': qa['question'][:100],
        'answer_preview': qa['answer'][:200],
    })

with open(os.path.join(OUT_DIR, 'qa_provenance.json'), 'w', encoding='utf-8') as f:
    json.dump(mapping, f, ensure_ascii=False, indent=2)

print("Saved:\n  - qa_provenance_report.md\n  - qa_provenance.json")
print("Total QA pairs: %d" % len(mapping))
