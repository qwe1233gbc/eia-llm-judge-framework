# -*- coding: utf-8 -*-
"""
Build EIA Review Experience Library from QA data
Levels: A (final_verified), B (verified), C (demoted/needs_review), D (rejected analysis)
"""
import sys, json, re, os, csv
from collections import defaultdict, Counter
sys.stdout.reconfigure(encoding='utf-8')

BASE = r"E:\软件"
REPO = os.path.join(BASE, "eia-llm-judge-framework")
DATA = os.path.join(REPO, "data/qa_v4")
OUT = os.path.join(REPO, "outputs/experience_library")
os.makedirs(OUT, exist_ok=True)

log = lambda msg: print("[%s] %s" % (__import__('time').strftime('%H:%M:%S'), msg), flush=True)

def load_jsonl(path):
    items = []
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    items.append(json.loads(line))
    return items

# Load data
final_verified = load_jsonl(os.path.join(DATA, "qa_v4_final_verified.jsonl"))
verified = load_jsonl(os.path.join(DATA, "qa_v4_verified.jsonl"))
demoted = load_jsonl(os.path.join(DATA, "qa_v4_demoted.jsonl"))
needs_review = load_jsonl(os.path.join(DATA, "qa_v4_needs_human_review.jsonl"))
rejected = load_jsonl(os.path.join(DATA, "qa_v4_rejected.jsonl"))
all_scored = load_jsonl(os.path.join(DATA, "qa_v4_all_scored.jsonl"))

log("Loaded: final_verified=%d verified=%d demoted=%d needs_review=%d rejected=%d" % (
    len(final_verified), len(verified), len(demoted), len(needs_review), len(rejected)))

# Build lookup sets
final_ids = set(q.get('project_id','')+'_'+q.get('element','') for q in final_verified)
verified_ids = set(q.get('project_id','')+'_'+q.get('element','') for q in verified)
demoted_ids = set(q.get('project_id','')+'_'+q.get('element','') for q in demoted)

# Classify each QA into evidence level
all_qas = []
for q in all_scored:
    qid = q.get('project_id','')+'_'+q.get('element','')
    if qid in final_ids:
        q['_evidence_level'] = 'A'
        all_qas.append(q)
    elif qid in demoted_ids:
        q['_evidence_level'] = 'B'
        all_qas.append(q)
    elif q.get('corrected_validation') == 'needs_human_review':
        q['_evidence_level'] = 'C'
        all_qas.append(q)

log("Classified: A=%d B=%d C=%d" % (
    sum(1 for q in all_qas if q['_evidence_level']=='A'),
    sum(1 for q in all_qas if q['_evidence_level']=='B'),
    sum(1 for q in all_qas if q['_evidence_level']=='C')))

# ============ Rule Templates ============
ELEM_CHECKPOINTS = {
    '废水': ['是否识别废水类别和主要污染因子', '是否说明预处理措施及效率',
            '是否明确排放去向（纳管/地表水/循环利用）', '是否引用正确的排放标准',
            '是否说明污水处理厂名称或纳管条件'],
    '废气': ['是否识别VOCs/非甲烷总烃/颗粒物等污染因子', '是否说明集气罩或密闭收集方式',
            '是否说明活性炭吸附等治理工艺', '是否明确排气筒高度和排放标准',
            '是否说明废活性炭等二次污染物的处置'],
    '噪声': ['是否说明厂界噪声执行标准类别', '是否与声环境功能区划一致',
            '是否说明隔声减振措施', '是否明确昼间/夜间限值'],
    '固废': ['是否识别一般固废类别和产生量', '是否说明综合利用或处置去向',
            '是否引用GB18599等标准'],
    '危废': ['是否识别危废名称和HW代码', '是否说明暂存设施要求',
            '是否说明委托有资质单位处置', '是否引用GB18597标准'],
    '环境管理': ['是否明确排污许可或排污登记要求', '是否说明竣工环保验收要求',
             '是否说明重大变动重新报批要求'],
    '总量': ['是否明确总量控制指标', '是否说明COD/NH3-N/SO2/NOx/VOCs排放量',
           '是否与批复要求一致'],
}

ELEM_CONTENT = {
    '废水': ['废水来源', '废水产生量', '主要污染因子', '预处理措施', '排放去向', '执行标准', '污水处理厂名称'],
    '废气': ['废气产生工序', '主要污染因子', '收集方式', '治理工艺', '排气筒高度', '排放标准', '二次污染物'],
    '噪声': ['主要噪声源', '设备声级', '厂界预测结果', '标准类别', '隔声减振措施'],
    '固废': ['一般固废种类', '产生量', '贮存位置', '综合利用或处置去向', '执行标准'],
    '危废': ['危废名称', '危废代码', '产生量', '暂存设施', '委托处置资质', '转移联单'],
    '环境管理': ['排污许可要求', '竣工环保验收要求', '重大变动要求', '监测要求'],
    '总量': ['总量控制指标', 'COD/NH3-N排放量', '报告核算依据'],
}

ELEM_POLLUTANTS = {
    '废水': ['COD', '氨氮', 'SS', 'BOD', '总磷', '总氮', '石油类', 'LAS'],
    '废气': ['非甲烷总烃', 'VOCs', '颗粒物', '臭气浓度', 'SO2', 'NOx', '烟尘', '粉尘'],
    '噪声': ['等效连续A声级', 'Leq'],
    '固废': ['一般工业固体废物'],
    '危废': ['废活性炭', '废机油', '废包装桶', '废液压油'],
}

ELEM_MEASURES = {
    '废水': ['化粪池', '隔油池', '沉淀池', '调节池', '生化处理', '消毒', '预处理'],
    '废气': ['集气罩收集', '密闭收集', '活性炭吸附', '布袋除尘', '水喷淋', '催化燃烧', 'UV光解'],
    '噪声': ['隔声门窗', '减振基础', '距离衰减', '消声器', '厂房隔声'],
    '固废': ['分类收集', '综合利用', '专业公司回收', '暂存间'],
    '危废': ['危废暂存间', '委托有资质单位处置', '转移联单管理'],
}

# ============ Build Rules ============
log("\n=== Building Rules ===")

# Group QA by industry + element
groups = defaultdict(list)
for q in all_qas:
    key = (q.get('industry_code','?'), q.get('element','?'), q.get('project_type','?'))
    groups[key].append(q)

all_rules = []
for (ind_code, elem, proj_type), qas in sorted(groups.items()):
    # Count by evidence level
    a_count = sum(1 for q in qas if q['_evidence_level'] == 'A')
    b_count = sum(1 for q in qas if q['_evidence_level'] == 'B')
    c_count = sum(1 for q in qas if q['_evidence_level'] == 'C')
    total = len(qas)

    # Collect standards
    all_stds = set()
    for q in qas:
        for s in q.get('standards_normalized',[]) or []:
            code = s.get('standard_code','')
            if code: all_stds.add(code)

    # Collect pollutants
    all_pollutants = ELEM_POLLUTANTS.get(elem, [])

    # Collect measures
    all_measures = ELEM_MEASURES.get(elem, [])

    # Collect projects
    project_ids = list(set(q.get('project_id','') for q in qas if q.get('project_id')))
    support_count = len(project_ids)

    # Build rules at different detail levels
    # If enough A samples, create A-level rule
    # If only B/C, create B or C level rule

    # Determine evidence level for this rule
    if a_count >= 3:
        evidence_level = 'A'
        confidence = min(1.0, a_count / 5)
    elif b_count >= 2:
        evidence_level = 'B'
        confidence = min(0.7, b_count / 5)
    elif total >= 2:
        evidence_level = 'C'
        confidence = 0.3
    else:
        evidence_level = 'C'
        confidence = 0.1

    # Rule stability
    if support_count >= 5 and (a_count + b_count) / max(total,1) >= 0.6:
        rule_status = 'strong_rule'
    elif support_count >= 3:
        rule_status = 'common_rule'
    elif support_count >= 2:
        rule_status = 'candidate_rule'
    else:
        rule_status = 'case_observation'

    rule_id = 'RULE_%s_%s_%s' % (ind_code, elem.upper(), proj_type[:2])

    # Build approval requirements from answers
    approval_reqs = []
    seen = set()
    for q in qas:
        a = q.get('answer','')
        if a and len(a) > 20:
            key = a[:120]
            if key not in seen:
                seen.add(key)
                approval_reqs.append(key)
    approval_reqs = approval_reqs[:5]

    # Build trigger conditions
    triggers = ['项目属于 %s 行业' % ind_code]
    if elem == '废水': triggers.append('项目产生工业废水或生活污水')
    elif elem == '废气': triggers.append('项目存在工艺废气产生工序')
    elif elem == '噪声': triggers.append('项目存在固定设备噪声源')
    elif elem == '固废': triggers.append('项目产生一般工业固体废物')
    elif elem == '危废': triggers.append('项目产生危险废物')

    # Checkpoints
    checkpoints = ELEM_CHECKPOINTS.get(elem, ['满足相关环保要求'])

    # Expected content
    content = ELEM_CONTENT.get(elem, ['相关环保措施'])

    rule = {
        'rule_id': rule_id,
        'industry_code': ind_code,
        'industry_name': '',
        'element': elem,
        'project_type': proj_type,
        'rule_type': elem + '_review',
        'rule_status': rule_status,
        'evidence_level': evidence_level,
        'confidence': round(confidence, 2),
        'trigger_condition': triggers,
        'review_checkpoints': checkpoints,
        'expected_report_content': content,
        'common_approval_requirement': approval_reqs,
        'common_standards': sorted(list(all_stds))[:10],
        'common_pollutants': all_pollutants,
        'common_control_measures': all_measures,
        'source_qa_ids': [q.get('project_id','')+'_'+q.get('element','') for q in qas[:10]],
        'source_project_ids': project_ids[:20],
        'support_count': support_count,
        'support_ratio': round(support_count / max(total, 1), 2),
        'sample_counts': {'A': a_count, 'B': b_count, 'C': c_count, 'total': total},
        'limitations': [],
        'need_human_review': evidence_level == 'C',
    }

    # Add limitations
    if support_count < 3:
        rule['limitations'].append('样本数不足，仅%d个项目' % support_count)
    if evidence_level == 'C':
        rule['limitations'].append('证据等级为C级，未通过原文证据审计')
    if c_count > a_count + b_count:
        rule['limitations'].append('低可信样本占比过高')

    all_rules.append(rule)

log("Generated %d rules" % len(all_rules))

# ============ Split by Level ============
rules_A = [r for r in all_rules if r['evidence_level'] == 'A']
rules_B = [r for r in all_rules if r['evidence_level'] == 'B']
rules_C = [r for r in all_rules if r['evidence_level'] == 'C']

log("A=%d B=%d C=%d" % (len(rules_A), len(rules_B), len(rules_C)))

# ============ Save ============
def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log("Saved: %s (%d)" % (path, len(data) if isinstance(data, list) else 1))

save_json(all_rules, os.path.join(OUT, 'experience_rules_all.json'))
save_json(rules_A, os.path.join(OUT, 'experience_rules_A_verified.json'))
save_json(rules_B, os.path.join(OUT, 'experience_rules_B_candidate.json'))
save_json(rules_C, os.path.join(OUT, 'experience_rules_C_observation.json'))

# ============ By Industry Report ============
md = ["# EIA Review Experience Library\n\n"]
by_ind = defaultdict(list)
for r in all_rules:
    by_ind[r['industry_code']].append(r)

for ind_code in sorted(by_ind.keys()):
    rules = by_ind[ind_code]
    a = [r for r in rules if r['evidence_level']=='A']
    b = [r for r in rules if r['evidence_level']=='B']
    c = [r for r in rules if r['evidence_level']=='C']

    md.append("## %s\n\n" % ind_code)
    md.append("- A级规则: %d\n" % len(a))
    md.append("- B级规则: %d\n" % len(b))
    md.append("- C级规则: %d\n" % len(c))
    md.append("- 规则总数: %d\n\n" % len(rules))

    for r in rules[:5]:  # Show top 5 per industry
        md.append("### %s (%s)\n\n" % (r['rule_id'], r['rule_status']))
        md.append("**要素**: %s | **证据等级**: %s | **置信度**: %.2f\n\n" % (
            r['element'], r['evidence_level'], r['confidence']))
        md.append("**触发条件**:\n")
        for t in r['trigger_condition'][:3]:
            md.append("- %s\n" % t)
        md.append("\n**审核检查点**:\n")
        for cp in r['review_checkpoints'][:5]:
            md.append("- %s\n" % cp)
        md.append("\n**常见标准**: %s\n\n" % ', '.join(r['common_standards'][:5]))
        md.append("**支撑项目数**: %d | **样本分布**: A=%d B=%d C=%d\n\n" % (
            r['support_count'], r['sample_counts']['A'], r['sample_counts']['B'], r['sample_counts']['C']))
        if r['limitations']:
            md.append("**局限**: %s\n\n" % '; '.join(r['limitations']))
        md.append("---\n\n")

with open(os.path.join(OUT, 'experience_rules_by_industry.md'), 'w', encoding='utf-8') as f:
    f.writelines(md)

# ============ Summary CSV ============
with open(os.path.join(OUT, 'experience_rules_summary.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['rule_id','industry','element','project_type','rule_status','evidence_level',
                'confidence','support_count','support_ratio','a_count','b_count','c_count','total'])
    for r in all_rules:
        w.writerow([r['rule_id'], r['industry_code'], r['element'], r['project_type'],
                    r['rule_status'], r['evidence_level'], r['confidence'],
                    r['support_count'], r['support_ratio'],
                    r['sample_counts']['A'], r['sample_counts']['B'],
                    r['sample_counts']['C'], r['sample_counts']['total']])

# ============ Rule Matrix ============
with open(os.path.join(OUT, 'industry_rule_matrix.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['industry','废水','废气','噪声','固废','危废','环境管理','总量','合计'])
    rows = defaultdict(lambda: defaultdict(int))
    for r in all_rules:
        rows[r['industry_code']][r['element']] += 1
    for ind in sorted(rows.keys()):
        row_data = rows[ind]
        w.writerow([ind, row_data.get('废水',0), row_data.get('废气',0), row_data.get('噪声',0),
                    row_data.get('固废',0), row_data.get('危废',0), row_data.get('环境管理',0),
                    row_data.get('总量',0), sum(row_data.values())])

# ============ Traceability ============
with open(os.path.join(OUT, 'rule_source_traceability.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['rule_id','source_qa_id','project_id','company','industry_code','element',
                'evidence_level','evidence_status'])
    for r in all_rules:
        for qid in r['source_qa_ids'][:5]:
            # Find the QA to get company
            company = ''
            for q in all_qas:
                if q.get('project_id','')+'_'+q.get('element','') == qid:
                    company = q.get('company','') or ''
                    break
            status = 'double_verified' if r['evidence_level'] == 'A' else (
                'auto_verified' if r['evidence_level'] == 'B' else 'partial_evidence')
            w.writerow([r['rule_id'], qid, qid.split('_')[0] if '_' in qid else '',
                        company, r['industry_code'], r['element'],
                        r['evidence_level'], status])

# ============ Neo4j Outputs ============
nodes = []
rels = []
triples = []

# Nodes
node_set = set()
def add_node(id_val, label, props=None):
    key = '%s:%s' % (label, id_val)
    if key not in node_set:
        node_set.add(key)
        nodes.append({'id': id_val, 'label': label, 'properties': props or {}})

for r in all_rules[:50]:  # Limit to 50 rules for Neo4j
    add_node(r['rule_id'], 'Rule', {'status': r['rule_status'], 'level': r['evidence_level']})
    add_node(r['industry_code'], 'Industry')
    add_node(r['element'], 'EnvironmentElement')

    rels.append({'source': r['industry_code'], 'target': r['rule_id'], 'type': 'HAS_RULE'})
    triples.append({'head': r['industry_code'], 'relation': 'HAS_RULE', 'tail': r['rule_id']})

    rels.append({'source': r['rule_id'], 'target': r['element'], 'type': 'CHECKS_ELEMENT'})
    triples.append({'head': r['rule_id'], 'relation': 'CHECKS_ELEMENT', 'tail': r['element']})

    for pid in r['source_project_ids'][:3]:
        add_node(pid, 'Project')
        rels.append({'source': r['rule_id'], 'target': pid, 'type': 'SUPPORTED_BY_PROJECT'})
        triples.append({'head': r['rule_id'], 'relation': 'SUPPORTED_BY_PROJECT', 'tail': pid})

    for std in r['common_standards'][:3]:
        add_node(std, 'Standard')
        rels.append({'source': r['rule_id'], 'target': std, 'type': 'USES_STANDARD'})
        triples.append({'head': r['rule_id'], 'relation': 'USES_STANDARD', 'tail': std})

def save_csv(data, path, fieldnames):
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for d in data:
            w.writerow(d)

save_csv(nodes, os.path.join(OUT, 'neo4j_nodes.csv'), ['id','label','properties'])
save_csv(rels, os.path.join(OUT, 'neo4j_relationships.csv'), ['source','target','type'])
save_csv(triples, os.path.join(OUT, 'neo4j_triples.csv'), ['head','relation','tail'])

# ============ Quality Report ============
status_counts = Counter(r['rule_status'] for r in all_rules)
elem_counts = Counter(r['element'] for r in all_rules)

report = [
    "# Experience Library Quality Report\n\n",
    "## Data Sources\n\n",
    "- final_verified (A级证据): %d\n" % len(final_verified),
    "- verified (B级证据): %d\n" % len(verified),
    "- demoted/needs_review (C级证据): %d\n" % (len(demoted)+len(needs_review)),
    "- Total rules: %d\n\n" % len(all_rules),
    "## Rule Distribution\n\n",
    "### By Level\n\n",
]
for level, count in [('A', len(rules_A)), ('B', len(rules_B)), ('C', len(rules_C))]:
    report.append("- %s: %d\n" % (level, count))
report.append("\n### By Status\n\n")
for s, n in status_counts.most_common():
    report.append("- %s: %d\n" % (s, n))
report.append("\n### By Element\n\n")
for e, n in elem_counts.most_common():
    report.append("- %s: %d\n" % (e, n))

report.append("\n## Top Industries\n\n")
ind_counts = Counter(r['industry_code'] for r in all_rules)
for ind, n in ind_counts.most_common(10):
    report.append("- %s: %d rules\n" % (ind, n))

report.append("\n## Limitations\n\n")
report.append("- A级规则仅来自 final_verified 样本\n")
report.append("- B/C级规则未通过原文证据审计\n")
report.append("- C级规则不可作为行业规律引用\n")
report.append("- 当前规则主要覆盖废水/废气/噪声/固废/危废，环境管理和总量控制规则偏少\n")
report.append("- 规则仅在顺德区级批复数据上归纳，市级数据尚未纳入\n\n")
report.append("## Future Work\n\n")
report.append("- 将佛山市级数据纳入经验规则归纳\n")
report.append("- 新增环境管理和总量控制类规则\n")
report.append("- 用新增报告-批复对扩充同行业样本量\n")

with open(os.path.join(OUT, 'final_experience_library_report.md'), 'w', encoding='utf-8') as f:
    f.writelines(report)

log("\n=== Done ===")
print("\nExperience Library Summary:")
print("  A级规则: %d" % len(rules_A))
print("  B级规则: %d" % len(rules_B))
print("  C级规则: %d" % len(rules_C))
print("  总规则: %d" % len(all_rules))
print("  覆盖行业: %d" % len(by_ind))
print("\n输出目录: %s" % OUT)
