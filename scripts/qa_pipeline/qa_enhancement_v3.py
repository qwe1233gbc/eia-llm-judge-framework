# -*- coding: utf-8 -*-
"""
QA Enhancement Pipeline v3 - 5 improvements:
1. Project matching validation (company/project_name/approval_file consistency)
2. Split answer by element (multi-element clauses → separate QA pairs)
3. Restrictive quality_score (needs all 4: report+approval+standards+matching)
4. Structured behavior_rule (trigger → checkpoint → content → requirement)
5. evidence_alignment check (does evidence actually support the answer?)
"""
import sys, json, re, os
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

QA_V2 = r"E:\软件\outputs\qa_v2\qa_v2.json"
PROJECT_INDEX = r"E:\软件\outputs\eia_industry_pattern\project_index.jsonl"
APPROVAL_DIR = r"E:\软件\2023-2026年顺德批复文件"
OUT_DIR = r"E:\软件\outputs\qa_v3"
os.makedirs(OUT_DIR, exist_ok=True)

log = lambda msg: print("[%s] %s" % (__import__('time').strftime('%H:%M:%S'), msg), flush=True)

# Load data
with open(QA_V2, encoding='utf-8') as f:
    qas = json.load(f)
log("Loaded QA v2: %d" % len(qas))

projs = {}
with open(PROJECT_INDEX, encoding='utf-8') as f:
    for line in f:
        p = json.loads(line)
        projs[p['project_id']] = p
log("Loaded projects: %d" % len(projs))

# ========== Step 1: Project Matching Validation ==========
log("\n=== Step 1: Project Matching Validation ===")
match_issues = 0
for qa in qas:
    pid = qa.get('project_id', '')
    proj = projs.get(pid, {})
    qa_company = qa.get('company', '') or ''
    proj_company = proj.get('construction_unit', '') or proj.get('project_name', '') or ''
    af = qa.get('approval_file', '') or ''

    issues = []

    # Check company consistency
    if proj_company and qa_company:
        # Check if they share at least 3 Chinese chars
        qa_chars = set(re.findall(r'[一-鿿]', qa_company))
        proj_chars = set(re.findall(r'[一-鿿]', proj_company))
        overlap = qa_chars & proj_chars
        if len(overlap) < 2:
            issues.append("company_mismatch: QA=%s vs PROJ=%s" % (qa_company[:10], proj_company[:10]))

    # Check approval file exists
    if af:
        af_path = os.path.join(APPROVAL_DIR, af)
        if not os.path.exists(af_path):
            issues.append("approval_file_not_found: %s" % af[:30])
    else:
        issues.append("no_approval_file")

    # Check approval file contains company name
    if af and proj_company:
        chn = ''.join(re.findall(r'[一-鿿]+', proj_company))[:4]
        if chn and chn not in af:
            issues.append("approval_company_mismatch: %s not in %s" % (chn, af[:30]))

    qa['match_issues'] = issues
    if issues:
        qa['need_human_review'] = True
        match_issues += 1

log("Match issues: %d/%d" % (match_issues, len(qas)))

# ========== Step 2: Split by Element ==========
log("\n=== Step 2: Split by Element ===")
ELEM_RULES = {
    '废水': ['废水', '污水', 'COD', '氨氮', '水污染', '排水', '纳管'],
    '废气': ['废气', 'VOCs', '烟尘', '粉尘', '颗粒物', '非甲烷总烃', '排气', '臭气'],
    '噪声': ['噪声', '噪音', '厂界'],
    '固废': ['固废', '固体废物', '一般工业', '综合利用'],
    '危废': ['危废', '危险废物', '废活性炭', '废机油', '委托处置'],
    '环境管理': ['排污许可', '竣工验收', '监测', '台账', '变动', '重新报批'],
}

def detect_elements(text):
    """Detect which elements are mentioned in a text"""
    found = set()
    for elem, keywords in ELEM_RULES.items():
        if any(k in text for k in keywords):
            found.add(elem)
    return found or {'其他'}

# Split multi-element QA pairs
new_qas = []
split_count = 0
for qa in qas:
    answer = qa.get('answer', '')
    current_elem = qa.get('element', '其他')
    elements = detect_elements(answer)

    if len(elements) > 1 and current_elem != '总量':
        # Clause covers multiple elements - create separate QA for each
        for elem in elements:
            if elem == '其他':
                continue
            new_qa = dict(qa)
            new_qa['element'] = elem
            new_qa['review_point'] = '污染防治措施'
            if elem == '环境管理':
                new_qa['review_point'] = '环境管理'
            # Filter answer text to relevant portion
            keywords = ELEM_RULES.get(elem, [])
            filtered = answer
            if keywords:
                # Find sentences containing relevant keywords
                sentences = re.split(r'[。；]', answer)
                relevant = [s for s in sentences if any(k in s for k in keywords)]
                if relevant:
                    filtered = '；'.join(relevant)
            new_qa['answer'] = filtered[:500]
            new_qas.append(new_qa)
            split_count += 1
    else:
        new_qas.append(qa)

log("Split: %d multi-element QA pairs expanded" % split_count)
log("Total QA after split: %d" % len(new_qas))

# ========== Step 3: Restrictive Quality Score ==========
log("\n=== Step 3: Quality Score Recalculation ===")
def calc_quality(qa):
    score = 0
    reasons = []

    # 1. Has report evidence (+25)
    ev = qa.get('report_evidence', [])
    has_report = bool(ev and any(e for e in ev))
    if has_report:
        score += 25
    else:
        reasons.append("no_report_evidence")

    # 2. Has approval evidence (+25)
    ae = qa.get('approval_evidence', [])
    has_approval = bool(ae and any(e.get('text','') for e in ae))
    if has_approval:
        score += 25
    else:
        reasons.append("no_approval_evidence")

    # 3. Has standards (+25)
    stds = qa.get('standards', [])
    if stds:
        score += 25
    else:
        reasons.append("no_standards")

    # 4. Project matching consistent (+25)
    mi = qa.get('match_issues', [])
    if not mi:
        score += 25
    else:
        reasons.append("match_issues: " + ';'.join(mi[:2]))

    return score, reasons

for qa in new_qas:
    score, reasons = calc_quality(qa)
    qa['quality_score'] = score
    qa['quality_issues'] = reasons
    qa['need_human_review'] = score < 75

grades = {'A(>=90)':0, 'B(75-89)':0, 'C(50-74)':0, 'D(<50)':0}
for qa in new_qas:
    s = qa['quality_score']
    if s >= 90: grades['A(>=90)'] += 1
    elif s >= 75: grades['B(75-89)'] += 1
    elif s >= 50: grades['C(50-74)'] += 1
    else: grades['D(<50)'] += 1

for g, n in grades.items():
    log("  %s: %d (%.0f%%)" % (g, n, n/len(new_qas)*100))

# ========== Step 4: Structured behavior_rule ==========
log("\n=== Step 4: Behavior Rule Rewrite ===")
def build_behavior_rule(qa):
    ic = qa.get('industry_code', '?')
    elem = qa.get('element', '?')
    pt = qa.get('project_type', '?')
    stds = qa.get('standards', [])
    answer = qa.get('answer', '')

    trigger_map = {
        '废水': '项目产生工业废水或生活污水',
        '废气': '项目存在工艺废气产生工序（如注塑、挤出、焊接等）',
        '噪声': '项目存在固定设备噪声源',
        '固废': '项目产生一般工业固体废物',
        '危废': '项目产生危险废物（如废活性炭、废机油等）',
        '环境管理': '项目涉及排污许可或竣工环保验收',
    }
    trigger = trigger_map.get(elem, '项目属于%s行业' % ic)

    checkpoint_map = {
        '废水': ['是否识别废水类别和主要污染因子', '是否说明预处理措施及效率',
                '是否明确排放去向（纳管/地表水/循环）', '是否引用正确的排放标准'],
        '废气': ['是否识别废气污染因子和源强', '是否说明收集方式（集气罩/密闭）和收集效率',
                '是否说明治理工艺（活性炭/布袋/洗涤）', '是否引用对应的排放标准'],
        '噪声': ['是否说明厂界噪声执行标准类别', '是否与声环境功能区划一致'],
        '固废': ['是否识别一般固废类别和产生量', '是否说明综合利用或处置去向'],
        '危废': ['是否识别危废类别（HW代码）和产生量', '是否说明暂存要求和委托处置资质'],
    }
    checkpoints = checkpoint_map.get(elem, ['是否满足相关环保要求'])

    content_map = {
        '废水': ['废水产生来源和水量', '主要污染因子（COD、NH3-N等）', '预处理措施', '排放去向', '执行标准'],
        '废气': ['废气产生工序和源强', '污染因子（颗粒物、VOCs等）', '收集方式和效率', '治理工艺', '排气筒高度'],
    }
    content = content_map.get(elem, ['相关环保措施'])

    requirement = answer[:150] if answer else ''

    rule = {
        'trigger_condition': trigger,
        'review_checkpoints': checkpoints,
        'expected_report_content': content,
        'common_approval_requirement': requirement,
        'common_standards': stds[:5],
    }
    return rule

for qa in new_qas:
    qa['behavior_rule'] = build_behavior_rule(qa)

# ========== Step 5: Evidence Alignment Check ==========
log("\n=== Step 5: Evidence Alignment Check ===")
def check_alignment(qa):
    answer = qa.get('answer', '')
    evidence = qa.get('report_evidence', [])
    stds = qa.get('standards', [])

    if not evidence or not answer:
        return 'no_evidence', 0

    # Extract key claims from answer
    answer_clean = re.sub(r'\s+', ' ', answer)
    evidence_texts = []
    for e in evidence:
        if isinstance(e, dict):
            evidence_texts.append(e.get('text', ''))
        else:
            evidence_texts.append(str(e))
    evidence_flat = ' '.join(evidence_texts)

    # Check 1: Do standards appear in evidence?
    std_overlap = 0
    for s in stds:
        if s[:8] in evidence_flat:
            std_overlap += 1
    std_ratio = std_overlap / max(len(stds), 1)

    # Check 2: Do key Chinese terms appear in evidence?
    key_terms = re.findall(r'[一-鿿]{4,}(?:标准|限值|排放|噪声|废气|废水)', answer_clean)
    term_overlap = sum(1 for t in key_terms[:5] if t in evidence_flat)
    term_ratio = term_overlap / max(len(key_terms[:5]), 1)

    # Check 3: Is evidence long enough to be meaningful?
    min_length = min(50, len(answer_clean))
    has_substance = any(len(t) > min_length for t in evidence_texts)

    score = (std_ratio * 0.4 + term_ratio * 0.4 + (0.2 if has_substance else 0)) * 100

    if score >= 60:
        level = 'high'
    elif score >= 30:
        level = 'medium'
    else:
        level = 'low'

    return level, round(score, 1)

align_stats = {'high': 0, 'medium': 0, 'low': 0, 'no_evidence': 0}
for qa in new_qas:
    level, score = check_alignment(qa)
    qa['evidence_alignment'] = {'level': level, 'score': score}
    align_stats[level] = align_stats.get(level, 0) + 1

log("Evidence alignment: high=%d medium=%d low=%d no_evidence=%d" % (
    align_stats['high'], align_stats['medium'], align_stats['low'], align_stats['no_evidence']))

# ========== Save ==========
log("\n=== Saving ===")
with open(os.path.join(OUT_DIR, 'qa_v3.json'), 'w', encoding='utf-8') as f:
    json.dump(new_qas, f, ensure_ascii=False, indent=2)
log("Saved: qa_v3.json (%d QA pairs)" % len(new_qas))

# Summary
a_grade = sum(1 for q in new_qas if q['quality_score'] >= 90)
b_grade = sum(1 for q in new_qas if 75 <= q['quality_score'] < 90)
c_grade = sum(1 for q in new_qas if 50 <= q['quality_score'] < 75)
d_grade = sum(1 for q in new_qas if q['quality_score'] < 50)
log("\n=== Final Stats ===")
log("Grade A(>=90): %d" % a_grade)
log("Grade B(75-89): %d" % b_grade)
log("Grade C(50-74): %d" % c_grade)
log("Grade D(<50): %d" % d_grade)
log("Need human review: %d" % sum(1 for q in new_qas if q.get('need_human_review')))
log("Done!")
