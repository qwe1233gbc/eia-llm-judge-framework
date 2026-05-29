# -*- coding: utf-8 -*-
"""Rebuild experience library v2 with standard whitelist, element-std compatibility, better aggregation"""
import sys, json, re, os, csv
from collections import defaultdict, Counter
sys.stdout.reconfigure(encoding='utf-8')

BASE = r"E:\软件"
REPO = os.path.join(BASE, "eia-llm-judge-framework")
DATA = os.path.join(REPO, "data/qa_v4")
OUT = os.path.join(REPO, "outputs/experience_library_v2")
os.makedirs(OUT, exist_ok=True)

log = lambda msg: print("[%s] %s" % (__import__('time').strftime('%H:%M:%S'), msg), flush=True)

# ============ 1. Standard code whitelist ============
STD_PATTERN = re.compile(r'^(GB|GB/T|HJ|HJ/T|DB44|DB44/T|DB\d{2}|DB\d{2}/T|GH)\s*[/／]?\s*\d{2,6}\s*[-—－]?\s*\d{2,4}$')
# Normalized form
def normalize_std(code):
    c = code.strip().replace('—','-').replace('－','-').replace('／','/').replace(' ','').replace('　','')
    # Insert hyphen: GB123482008 -> GB12348-2008
    m = re.match(r'^([A-Z]{1,3}\d{2,6})(\d{4})$', c)
    if m: c = m.group(1) + '-' + m.group(2)
    return c

def is_valid_std(code):
    if not code: return False
    c = normalize_std(code)
    # Reject garbage
    if c in ('DA001','DA002','DA003','DA004','DA005','DA','DB','DB44','DB44/'): return False
    if len(c) < 6: return False
    if not re.match(r'^(GB|GB/T|HJ|HJ/T|DB\d{2}|DB\d{2}/T)', c): return False
    return True

# ============ 2. Element-Standard Compatibility ============
ELEMENT_STD_MAP = {
    '废水': ['DB44/26','GB18918','GB8978','GB21902','GB25461','GB25462','GB25463','GB25464',
             'GB25465','GB25466','GB25467','GB25468','GB4287','GB13456','GB13457','GB13458',
             'GB14470','GB15580','GB15581','GB20425','GB20426','GB21523','GB27631','GB27632',
             'GB30484','GB30485','GB30486','GB31571','GB31572','GB31573','GB31574','GB39731'],
    '废气': ['DB44/27','DB44/2367','GB31572','GB37822','GB14554','GB16297','GB9078','GB18483',
             'GB28665','GB29620','GB31570','GB31571','GB31572','GB31573','GB4915','GB13223',
             'GB13271','GB16171','GB16297','GB18484','GB18485','GB28662','GB28663','GB28664'],
    '噪声': ['GB12348','GB3096','GB22337'],
    '固废': ['GB18599','GB5085','GB34330','GB/T34911'],
    '危废': ['GB18597','GB5085','HJ2025','HJ1276','国家危险废物名录'],
    '环境管理': ['排污许可','竣工环保验收','重大变动','HJ942','HJ944','HJ1108'],
    '总量': ['总量','排放量'],
}

def std_matches_element(std_code, element):
    if not element or not std_code: return True
    prefixes = ELEMENT_STD_MAP.get(element, [])
    if not prefixes: return True
    std_norm = normalize_std(std_code)
    for prefix in prefixes:
        if prefix in std_norm:
            return True
    return False

# ============ Load and classify QA data ============
log("Loading QA data...")
def load_jsonl(path):
    items = []
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    items.append(json.loads(line))
    return items

final_v = load_jsonl(os.path.join(DATA, "qa_v4_final_verified.jsonl"))
verified = load_jsonl(os.path.join(DATA, "qa_v4_verified.jsonl"))
demoted = load_jsonl(os.path.join(DATA, "qa_v4_demoted.jsonl"))
needs_review = load_jsonl(os.path.join(DATA, "qa_v4_needs_human_review.jsonl"))

log("final_verified=%d verified=%d demoted=%d needs_review=%d" % (
    len(final_v), len(verified), len(demoted), len(needs_review)))

# Classify each QA by evidence level
final_ids = set(q.get('project_id','')+'_'+q.get('element','') for q in final_v)
demoted_ids = set(q.get('project_id','')+'_'+q.get('element','') for q in demoted)

all_qas = []
for q in final_v:
    q['_evidence_level'] = 'A'; all_qas.append(q)
for q in demoted:
    q['_evidence_level'] = 'B'; all_qas.append(q)
for q in needs_review:
    q['_evidence_level'] = 'C'; all_qas.append(q)

log("Classified: A=%d B=%d C=%d" % (
    sum(1 for q in all_qas if q['_evidence_level']=='A'),
    sum(1 for q in all_qas if q['_evidence_level']=='B'),
    sum(1 for q in all_qas if q['_evidence_level']=='C')))

# ============ Checkpoint templates by element ============
CHECKPOINTS = {
    '废水': [
        "是否识别废水类别（生活污水/生产废水/冷却废水）和主要污染因子（COD、氨氮等）",
        "是否说明预处理措施及处理效率（化粪池/隔油池/沉淀池等）",
        "是否明确排放去向（纳管/地表水/循环利用）及污水处理厂名称",
        "是否引用正确的排放标准（DB44/26-2001或行业标准）",
    ],
    '废气': [
        "是否识别VOCs/非甲烷总烃、颗粒物、臭气浓度等污染因子",
        "是否说明废气收集方式（集气罩/密闭收集）及收集效率",
        "是否说明治理工艺（活性炭吸附/布袋除尘/水喷淋等）",
        "是否明确排气筒高度及排放标准（GB31572/DB44/2367等）",
        "是否说明废活性炭等二次污染物的产生量和危废去向",
    ],
    '噪声': [
        "是否说明厂界噪声执行标准类别（GB12348-2008 3类/4类）",
        "是否与声环境功能区划一致",
        "是否说明主要噪声源及隔声减振措施",
        "是否明确昼间/夜间噪声限值",
    ],
    '固废': [
        "是否识别一般工业固体废物类别和产生量",
        "是否说明综合利用或处置去向",
        "是否引用GB18599等相关标准",
    ],
    '危废': [
        "是否识别危险废物名称和HW代码",
        "是否说明暂存设施要求（危废暂存间）",
        "是否说明委托有资质单位处置及转移联单管理",
        "是否引用GB18597等相关标准",
    ],
    '环境管理': [
        "是否明确排污许可或排污登记要求",
        "是否说明竣工环保验收要求",
        "是否说明重大变动重新报批要求",
        "是否明确日常监测要求和环境管理台账",
    ],
    '总量': [
        "是否明确总量控制指标（COD、NH3-N、SO2、NOx、VOCs）",
        "是否与批复要求一致",
        "报告中是否有对应核算依据",
    ],
}

EXPECTED_CONTENT = {
    '废水': ['废水来源','废水产生量','主要污染因子','预处理措施','排放去向','执行标准','污水处理厂名称'],
    '废气': ['废气产生工序','主要污染因子','收集方式','治理工艺','排气筒高度','排放标准','二次污染物处置'],
    '噪声': ['主要噪声源','设备声级','厂界预测','标准类别','隔声减振措施','昼间/夜间限值'],
    '固废': ['一般固废种类','产生量','贮存位置','综合利用或处置去向','执行标准'],
    '危废': ['危废名称','危废代码','产生量','暂存设施','委托处置','转移联单'],
    '环境管理': ['排污许可要求','竣工环保验收要求','重大变动要求','监测要求','台账要求'],
    '总量': ['总量控制指标','COD/NH3-N排放量','报告核算依据'],
}

# ============ Build rules ============
log("\nBuilding rules...")

# Clean standards per QA, then group
for q in all_qas:
    raw_stds = q.get('standards_normalized', []) or []
    clean = []
    for s in raw_stds:
        code = s.get('standard_code','') if isinstance(s, dict) else ''
        if is_valid_std(code):
            code_norm = normalize_std(code)
            if std_matches_element(code_norm, q.get('element','')):
                clean.append({'code': code_norm, 'name': s.get('standard_name','') if isinstance(s,dict) else ''})
    q['_clean_stds'] = list(set(c['code'] for c in clean))

# Group by industry + element + project_type
groups = defaultdict(list)
for q in all_qas:
    key = (q.get('industry_code','?'), q.get('element','?'), q.get('project_type','?'))
    groups[key].append(q)

all_rules = []
for (ind_code, elem, proj_type), qas in sorted(groups.items()):
    a_count = sum(1 for q in qas if q['_evidence_level'] == 'A')
    b_count = sum(1 for q in qas if q['_evidence_level'] == 'B')
    c_count = sum(1 for q in qas if q['_evidence_level'] == 'C')
    total = len(qas)

    # Collect clean standards
    all_stds = set()
    for q in qas:
        for s in q.get('_clean_stds', []):
            all_stds.add(s)

    # Collect trigger conditions
    triggers = ['项目属于 %s 行业' % ind_code]
    if elem == '废水': triggers.append('项目产生工业废水或生活污水，需明确处理工艺和排放去向')
    elif elem == '废气': triggers.append('项目存在注塑/挤出/吹塑/焊接/喷涂等工艺废气产生工序')
    elif elem == '噪声': triggers.append('项目存在风机/空压机/冷却塔等固定设备噪声源')
    elif elem == '固废': triggers.append('项目产生一般工业固体废物')
    elif elem == '危废': triggers.append('项目产生废活性炭/废机油/废包装桶等危险废物')
    elif elem == '环境管理': triggers.append('项目涉及排污许可或竣工环保验收')
    elif elem == '总量': triggers.append('项目涉及总量控制指标')

    # Evidence level for this rule
    if a_count >= 3:
        ev_level = 'A'
    elif b_count >= 3:
        ev_level = 'B'
    elif total >= 2:
        ev_level = 'C'
    else:
        ev_level = 'C'

    # Rule stability
    project_ids = list(set(q.get('project_id','') for q in qas if q.get('project_id')))
    sc = len(project_ids)
    if sc >= 5 and (a_count + b_count) / max(total,1) >= 0.6:
        status = 'strong_rule'
    elif sc >= 3:
        status = 'common_rule'
    elif sc >= 2:
        status = 'candidate_rule'
    else:
        status = 'case_observation'

    checkpoints = CHECKPOINTS.get(elem, ['满足相关环保要求'])
    content = EXPECTED_CONTENT.get(elem, ['相关环保措施'])

    # Approval requirements
    approval_reqs = []
    seen_req = set()
    for q in qas:
        a = q.get('answer','')
        if a and len(a) > 30:
            key = a[:100]
            if key not in seen_req:
                seen_req.add(key)
                approval_reqs.append(a[:200])
    approval_reqs = approval_reqs[:5]

    rule_id = 'RULE_%s_%s_%s' % (ind_code, elem.upper(), proj_type[:2])

    limitations = []
    if sc < 3: limitations.append('样本数不足，仅%d个项目，不能作为行业稳定规律' % sc)
    if ev_level == 'C': limitations.append('证据等级为C，未通过原文证据审计')
    if c_count > a_count + b_count: limitations.append('低可信样本占比过高')

    rule = {
        'rule_id': rule_id,
        'industry_code': ind_code,
        'industry_name': '',
        'element': elem,
        'project_type': proj_type,
        'rule_type': elem + '_review_rule',
        'rule_status': status,
        'evidence_level': ev_level,
        'confidence': round(min(1.0, sc/5), 2) if ev_level == 'A' else round(min(0.6, sc/5), 2),
        'trigger_condition': triggers,
        'review_checkpoints': checkpoints,
        'expected_report_content': content,
        'common_approval_requirement': approval_reqs,
        'common_standards': sorted(list(all_stds))[:10],
        'source_project_ids': project_ids[:20],
        'source_qa_ids': [q.get('project_id','')+'_'+q.get('element','') for q in qas[:10]],
        'support_count': sc,
        'sample_counts': {'A': a_count, 'B': b_count, 'C': c_count, 'total': total},
        'limitations': limitations,
        'need_human_review': ev_level == 'C',
    }
    all_rules.append(rule)

log("Generated %d rules" % len(all_rules))

# ============ Split by evidence level ============
rules_A = [r for r in all_rules if r['evidence_level'] == 'A']
rules_B = [r for r in all_rules if r['evidence_level'] == 'B']
rules_C = [r for r in all_rules if r['evidence_level'] == 'C']

# Verify A rules have no garbage standards
for r in rules_A:
    r['common_standards'] = [s for s in r.get('common_standards', []) if is_valid_std(s)]
    r['_verified'] = True

log("A=%d B=%d C=%d" % (len(rules_A), len(rules_B), len(rules_C)))

# ============ Save ============
def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log("Saved: %s" % path)

save_json(all_rules, os.path.join(OUT, 'rules_all.json'))
save_json(rules_A, os.path.join(OUT, 'rules_A_verified.json'))
save_json(rules_B, os.path.join(OUT, 'rules_B_candidate.json'))
save_json(rules_C, os.path.join(OUT, 'rules_C_observation.json'))

# ============ Quality Report ============
md = ["# Experience Library v2 - Generation Quality Report\n\n"]
md.append("## Input Data\n\n")
md.append("- final_verified (A): %d\n" % len(final_v))
md.append("- demoted (B): %d\n" % len(demoted))
md.append("- needs_review (C): %d\n" % len(needs_review))
md.append("\n## Output Rules\n\n")
md.append("| Level | Count | Criteria |\n|-------|-------|----------|\n")
md.append("| A | %d | >=3 A-samples, element-std matched, no garbage, specific checkpoints |\n" % len(rules_A))
md.append("| B | %d | >=3 B-samples, auto-QC passed |\n" % len(rules_B))
md.append("| C | %d | <3 samples or needs review |\n" % len(rules_C))
md.append("| Total | %d | |\n\n" % len(all_rules))
md.append("## Improvements over v1\n\n")
md.append("1. Standard code whitelist: only GB/GB/T/HJ/DB44/DBxx/T with correct format\n")
md.append("2. Element-standard compatibility: noise rules no longer contain DB44/GB31572\n")
md.append("3. DA001/DA002 exhaust vent IDs filtered out\n")
md.append("4. DB44 (bare, no year) filtered out\n")
md.append("5. Review checkpoints are element-specific\n\n")
md.append("## Issue Distribution\n\n")
# Count issues
issue_stats = {}
for r in all_rules:
    if r['evidence_level'] == 'A': issue_stats['A_level'] = issue_stats.get('A_level',0)+1
for r in rules_B: issue_stats['B_level'] = issue_stats.get('B_level',0)+1
for r in rules_C:
    for l in r.get('limitations',[]):
        issue_stats[l] = issue_stats.get(l,0)+1
for k,v in sorted(issue_stats.items(), key=lambda x:-x[1]):
    md.append("- %s: %d\n" % (k[:50], v))

with open(os.path.join(OUT, 'rule_generation_quality_report.md'), 'w', encoding='utf-8') as f:
    f.writelines(md)

# ============ A-level paper doc ============
paper_md = ["# A-Level Review Rules (v2)\n\n"]
paper_md.append("Total A-level rules: %d\n\n" % len(rules_A))
for r in rules_A:
    paper_md.append("## %s\n\n" % r['rule_id'])
    paper_md.append("**行业**: %s | **要素**: %s | **项目类型**: %s\n\n" % (
        r['industry_code'], r['element'], r['project_type']))
    paper_md.append("**触发条件**:\n")
    for t in r['trigger_condition']:
        paper_md.append("- %s\n" % t)
    paper_md.append("\n**审核检查点**:\n")
    for cp in r['review_checkpoints']:
        paper_md.append("- %s\n" % cp)
    if r['common_standards']:
        paper_md.append("\n**常见标准**: %s\n\n" % ', '.join(r['common_standards'][:5]))
    paper_md.append("**支撑项目数**: %d (A=%d B=%d C=%d)\n\n" % (
        r['support_count'], r['sample_counts']['A'], r['sample_counts']['B'], r['sample_counts']['C']))
    paper_md.append("**常用批复要求**:\n")
    for req in r['common_approval_requirement'][:2]:
        paper_md.append("> %s\n\n" % req[:120])
    if r['limitations']:
        paper_md.append("**局限性**: %s\n\n" % '; '.join(r['limitations']))
    paper_md.append("---\n\n")

with open(os.path.join(OUT, 'A_rules_for_paper.md'), 'w', encoding='utf-8') as f:
    f.writelines(paper_md)

# ============ Neo4j triples ============
triples = []
for r in all_rules[:100]:
    ic = r['industry_code']
    elem = r['element']
    triples.append({'head':ic, 'relation':'HAS_RULE', 'tail':r['rule_id']})
    triples.append({'head':r['rule_id'], 'relation':'CHECKS', 'tail':elem})
    for pid in r['source_project_ids'][:3]:
        triples.append({'head':r['rule_id'], 'relation':'SUPPORTED_BY', 'tail':pid})
    for s in r['common_standards'][:3]:
        if is_valid_std(s):
            triples.append({'head':r['rule_id'], 'relation':'USES_STANDARD', 'tail':s})

with open(os.path.join(OUT, 'neo4j_triples.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['head','relation','tail'])
    for t in triples:
        w.writerow([t['head'], t['relation'], t['tail']])

log("\n=== Done ===")
print("\nExperience Library v2 Summary:")
print("  A级规则: %d" % len(rules_A))
print("  B级规则: %d" % len(rules_B))
print("  C级规则: %d" % len(rules_C))
print("  总规则: %d" % len(all_rules))
print("\n输出: %s" % OUT)
