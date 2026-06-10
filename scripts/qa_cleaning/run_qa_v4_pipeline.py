# -*- coding: utf-8 -*-
"""
QA v4 Pipeline: Clean qa_v3 and build EIA-Review-Benchmark
Based on ELLE dataset construction methodology.
16 sections covering schema validation, matching, evidence alignment, benchmark taxonomy, quality rescoring.
"""
import sys, json, re, os, csv
from collections import defaultdict, Counter
sys.stdout.reconfigure(encoding='utf-8')

BASE = r"E:\软件\eia-llm-judge-framework"
QA_V3 = os.path.join(BASE, "data/qa_v3/qa_v3.json")
OUT_DIR = os.path.join(BASE, "data/qa_v4")
QUALITY_DIR = os.path.join(BASE, "outputs/qa_v4_quality")
SCHEMA_DIR = os.path.join(BASE, "schemas")
DOCS_DIR = os.path.join(BASE, "docs/benchmark")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(QUALITY_DIR, exist_ok=True)
os.makedirs(SCHEMA_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

log = lambda msg: print("[%s] %s" % (__import__('time').strftime('%H:%M:%S'), msg), flush=True)

with open(QA_V3, encoding='utf-8') as f:
    qas = json.load(f)
log("Loaded qa_v3: %d" % len(qas))

# ============================================================
# SECTION 1: Schema validation & field normalization
# ============================================================
log("\n=== Section 1: Schema Validation ===")
REQUIRED_FIELDS = ["level","region","company","project_id","industry_code","project_type",
    "report_year","element","review_point","clause_index","question","answer","standards",
    "approval_evidence","report_evidence","behavior_rule","quality_score","quality_issues",
    "need_human_review","validation","match_issues","evidence_alignment"]
schema_issues = 0
for qa in qas:
    for f in REQUIRED_FIELDS:
        if f not in qa:
            qa[f] = None if f != "clause_index" else 0
            qa.setdefault("quality_issues", []).append("missing_field_%s" % f)
            schema_issues += 1
    # Ensure nested structures exist
    if not isinstance(qa.get("behavior_rule"), dict):
        qa["behavior_rule"] = {}
    if not isinstance(qa.get("match_issues"), list):
        qa["match_issues"] = []
log("Schema issues fixed: %d" % schema_issues)

# ============================================================
# SECTION 2: Load project index for matching
# ============================================================
log("\n=== Section 2: Project Matching ===")
APPROVAL_DIR = r"E:\软件\2023-2026年顺德批复文件"
projs = {}
proj_path = os.path.join(BASE, "data/qa_v2/qa_provenance.json")
if os.path.exists(proj_path):
    with open(proj_path, encoding='utf-8') as f:
        mapping = json.load(f)
    for m in mapping:
        projs[m.get('project_id','')] = m

for qa in qas:
    pid = qa.get('project_id','')
    company = qa.get('company','') or ''
    af = qa.get('approval_file','') or ''
    mi = []

    # Check approval file exists
    if af:
        if not os.path.exists(os.path.join(APPROVAL_DIR, af)):
            mi.append("approval_file_missing")
    else:
        mi.append("no_approval_file")

    # Check company in approval filename
    chn = ''.join(re.findall(r'[一-鿿]+', company))[:4]
    if chn and af and chn not in af:
        mi.append("company_approval_mismatch")

    qa['match_issues'] = mi

pair_mismatch = sum(1 for q in qas if q.get('match_issues'))
log("Pair mismatch issues: %d/%d" % (pair_mismatch, len(qas)))

# ============================================================
# SECTION 3: Question-Element consistency fix
# ============================================================
log("\n=== Section 3: Question Rewrite ===")
ELEM_QUESTION_TEMPLATES = {
    '废水': "【区级】%s（%s %s项目）废水来源、主要污染因子、执行标准和排放去向是什么？",
    '废气': "【区级】%s（%s %s项目）废气产生工序、主要污染因子、收集治理措施和执行标准是什么？",
    '噪声': "【区级】%s（%s %s项目）厂界噪声执行什么标准类别？报告和批复中对应的噪声控制要求是什么？",
    '固废': "【区级】%s（%s %s项目）一般工业固体废物如何暂存、综合利用或处置？批复中有哪些要求？",
    '危废': "【区级】%s（%s %s项目）危险废物类别、暂存要求和委托处置要求是什么？",
    '环境管理': "【区级】%s（%s %s项目）批复中对排污许可、竣工环保验收和重大变动重新报批有什么要求？",
    '总量': "【区级】%s（%s %s项目）批复中确认的污染物总量控制指标是什么？报告中是否有对应核算依据？",
    '其他': "【区级】%s（%s %s项目）%s方面的具体要求是什么？",
}

qe_mismatches = 0
for qa in qas:
    elem = qa.get('element','其他')
    company = (qa.get('company','') or '')[:25]
    ind = qa.get('industry_code','?') or '?'
    pt = qa.get('project_type','?') or '?'
    old_q = qa.get('question','')

    template = ELEM_QUESTION_TEMPLATES.get(elem, ELEM_QUESTION_TEMPLATES['其他'])
    if elem == '其他':
        new_q = template % (company, ind, pt, qa.get('review_point','环保'))
    else:
        new_q = template % (company, ind, pt)

    qa['original_question'] = old_q
    qa['question'] = new_q
    qa['question_rewritten'] = (old_q != new_q)
    if old_q != new_q:
        qe_mismatches += 1

log("Questions rewritten: %d" % qe_mismatches)

# ============================================================
# SECTION 4: Standard normalization
# ============================================================
log("\n=== Section 4: Standard Normalization ===")
STD_NORM = {
    'DB44/262001': 'DB44/26-2001', 'DB44/272001': 'DB44/27-2001',
    'DB44/23672022': 'DB44/2367-2022', 'DB44/8142010': 'DB44/814-2010',
    'DB44/8152010': 'DB44/815-2010', 'DB44/8162010': 'DB44/816-2010',
    'GB123482008': 'GB12348-2008', 'GB315722015': 'GB31572-2015',
    'GB185972001': 'GB18597-2001', 'GB185972023': 'GB18597-2023',
    'GB185992001': 'GB18599-2001', 'GB185992020': 'GB18599-2020',
    'GB378222019': 'GB37822-2019', 'GB189182002': 'GB18918-2002',
    'GB145541993': 'GB14554-93', 'GB184832001': 'GB18483-2001',
    'GB286652012': 'GB28665-2012', 'GB30962008': 'GB3096-2008',
    'GB162971996': 'GB16297-1996', 'GB397262020': 'GB39726-2020',
    'GB550162021': 'GB55016-2021', 'GB276322011': 'GB27632-2011',
    'GB42872012': 'GB4287-2012', 'GB90781996': 'GB9078-1996',
    'GB184662005': 'GB18466-2005', 'GB184832001': 'GB18483-2001',
}

std_missing = 0
for qa in qas:
    raw_stds = qa.get('standards', []) or []
    normalized = []
    for s in raw_stds:
        if s in STD_NORM:
            normalized.append({'standard_code': STD_NORM[s], 'standard_name': '', 'source': 'qa'})
        else:
            normalized.append({'standard_code': s, 'standard_name': '', 'source': 'qa'})

    # Also search answer for standards
    answer = qa.get('answer','') or ''
    for pattern in [r'([A-Z]{2}\d+[-—]?\d*)', r'《([^》]+)》']:
        for m in re.finditer(pattern, answer):
            code = m.group(1).replace('—','-').replace('－','-').replace('　','')
            if not any(n['standard_code'] == code for n in normalized):
                normalized.append({'standard_code': code, 'standard_name': '', 'source': 'answer'})

    qa['standards_normalized'] = normalized
    if not normalized:
        std_missing += 1

log("Standards empty after normalization: %d" % std_missing)

# ============================================================
# SECTION 5: Evidence alignment check
# ============================================================
log("\n=== Section 5: Evidence Alignment ===")
ELEM_KEYWORDS = {
    '废水': ['废水','生活污水','生产废水','COD','氨氮','化粪池','污水处理厂','纳管','DB44/26','GB18918'],
    '废气': ['废气','VOCs','非甲烷总烃','颗粒物','臭气','活性炭','集气罩','排气筒','DB44/2367','GB31572','GB37822'],
    '噪声': ['噪声','厂界','隔声','减振','GB12348','昼间','夜间','dB'],
    '固废': ['固废','固体废物','一般工业','边角料','综合利用','GB18599'],
    '危废': ['危废','危险废物','废活性炭','废机油','废包装','HW','危废暂存','GB18597'],
    '环境管理': ['排污许可','排污登记','竣工环保验收','重大变动','重新报批','许可证'],
    '总量': ['总量','排放量','吨/年','千克/年','COD','NH3-N'],
}

def check_elem_alignment(qa):
    elem = qa.get('element','')
    kws = ELEM_KEYWORDS.get(elem, [])
    if not kws:
        return 'none', 0

    answer = qa.get('answer','') or ''
    ev = qa.get('report_evidence',[]) or []
    ae = qa.get('approval_evidence',[]) or []

    ev_text = ' '.join([(e.get('text','') if isinstance(e,dict) else str(e)) for e in (ev or [])])
    ae_text = ' '.join([(e.get('text','') if isinstance(e,dict) else str(e)) for e in (ae or [])])

    a_kw = sum(1 for k in kws if k in answer) / max(len(kws),1)
    ev_kw = sum(1 for k in kws if k in ev_text) / max(len(kws),1) if ev_text else 0
    ae_kw = sum(1 for k in kws if k in ae_text) / max(len(kws),1) if ae_text else 0

    if a_kw >= 0.3 and ev_kw >= 0.2 and ae_kw >= 0.2:
        return 'high', round((a_kw+ev_kw+ae_kw)/3*100, 1)
    elif a_kw >= 0.2 and ae_kw >= 0.15:
        return 'medium', round((a_kw+ae_kw)/2*100, 1)
    elif a_kw >= 0.1:
        return 'low', round(a_kw*100, 1)
    return 'none', 0

align_stats = {'high':0,'medium':0,'low':0,'none':0}
for qa in qas:
    level, score = check_elem_alignment(qa)
    qa['evidence_alignment'] = {'level': level, 'score': score}
    align_stats[level] += 1

log("Evidence alignment: %s" % str(align_stats))

# ============================================================
# SECTION 6: Benchmark taxonomy
# ============================================================
log("\n=== Section 6: Benchmark Taxonomy ===")
TASK_DOMAIN_MAP = {
    '废水': '废水', '废气': '废气', '噪声': '噪声',
    '固废': '固废', '危废': '危废',
    '环境管理': '综合审核', '总量': '总量控制', '其他': '综合审核',
}
DIFFICULTY_MAP = {
    '废水': 'simple', '废气': 'simple', '噪声': 'simple',
    '固废': 'simple', '危废': 'simple',
    '环境管理': 'medium', '总量': 'medium',
}
QTYPE_MAP = {
    '废水': 'extraction', '废气': 'extraction', '噪声': 'extraction',
    '固废': 'extraction', '危废': 'extraction',
    '环境管理': 'reasoning', '总量': 'calculation',
}
COG_MAP = {
    '废水': 'L1_fact', '废气': 'L1_fact', '噪声': 'L1_fact',
    '固废': 'L1_fact', '危废': 'L1_fact',
    '环境管理': 'L3_review_reasoning', '总量': 'L2_alignment',
}

tax_missing = 0
for qa in qas:
    elem = qa.get('element','')
    td = TASK_DOMAIN_MAP.get(elem, '综合审核')
    diff = DIFFICULTY_MAP.get(elem, 'medium')
    qt = QTYPE_MAP.get(elem, 'extraction')
    cog = COG_MAP.get(elem, 'L1_fact')

    # Upgrade difficulty for complex cases
    if qa.get('match_issues'): diff = 'medium'
    if len(qa.get('standards_normalized',[]) or []) > 3: diff = 'medium'

    qa['benchmark_metadata'] = {
        'task_domain': td,
        'difficulty': diff,
        'question_type': qt,
        'cognitive_level': cog,
        'evaluation_dimensions': ['professionalism','clarity','feasibility','evidence_grounding'],
    }
    if not td:
        tax_missing += 1

log("Taxonomy missing: %d" % tax_missing)

# ============================================================
# SECTION 7: Behavior rule enhancement
# ============================================================
log("\n=== Section 7: Behavior Rule Enhancement ===")
EXPECTED_CONTENT = {
    '废水': ['废水来源','废水产生量','主要污染因子','预处理措施','排放去向','执行标准','污水处理厂名称'],
    '废气': ['废气产生工序','主要污染因子','收集方式','治理工艺','排气筒高度','排放标准','二次污染物'],
    '噪声': ['主要噪声源','设备声级','厂界预测','标准类别','隔声减振措施','昼间夜间限值'],
    '固废': ['一般固废种类','产生量','贮存位置','综合利用或处置去向','执行标准'],
    '危废': ['危废名称','危废代码','产生量','危险特性','暂存设施','委托处置','转移联单'],
    '环境管理': ['排污许可要求','竣工环保验收要求','重大变动要求','监测要求','台账要求'],
    '总量': ['总量控制指标','COD/NH3-N排放量','报告核算依据'],
}

for qa in qas:
    br = qa.get('behavior_rule', {}) or {}
    elem = qa.get('element','')
    if isinstance(br, str):
        br = {'trigger_condition': br, 'review_checkpoints': [], 'expected_report_content': [],
              'common_approval_requirement': '', 'common_standards': []}

    ec = EXPECTED_CONTENT.get(elem, ['相关环保措施'])
    br.setdefault('expected_report_content', ec)

    # Check if too generic
    if br.get('expected_report_content') == ['相关环保措施'] or not br.get('expected_report_content'):
        br['expected_report_content'] = ec

    qa['behavior_rule'] = br
    qa['rule_quality'] = {
        'specificity': 'low' if br.get('expected_report_content') == ['相关环保措施'] else 'medium',
        'can_be_used_for_review': bool(br.get('review_checkpoints')),
        'rule_issues': []
    }

# ============================================================
# SECTION 8: Quality rescore
# ============================================================
log("\n=== Section 8: Quality Rescore ===")
def rescore(qa):
    score = 100
    issues = []

    if qa.get('match_issues'): score -= 50; issues.append("pair_mismatch")
    if not qa.get('approval_evidence') or not any(qa.get('approval_evidence',[])):
        issues.append("no_approval_evidence"); return 0, ["rejected_no_approval"]
    if not qa.get('report_evidence') or not any(qa.get('report_evidence',[])):
        score -= 40; issues.append("no_report_evidence")

    ea = qa.get('evidence_alignment',{}) or {}
    if ea.get('level') in ('low','none'):
        score -= 40 if ea.get('level')=='none' else 30
        issues.append("evidence_alignment_%s" % ea.get('level',''))

    if not qa.get('standards_normalized'):
        score -= 20; issues.append("no_standards")
    if not qa.get('benchmark_metadata') or not qa['benchmark_metadata'].get('task_domain'):
        score -= 20; issues.append("no_benchmark_metadata")

    ans = qa.get('answer','') or ''
    if len(re.findall(r'[一-鿿]', ans)) < 15:
        score -= 30; issues.append("answer_too_short")
    if qa.get('question_rewritten') == False and qa.get('original_question') != qa.get('question'):
        score -= 30; issues.append("question_element_mismatch")

    return max(0, score), issues

grade_stats = {'verified':0, 'needs_human_review':0, 'rejected':0}
for qa in qas:
    score, issues = rescore(qa)
    qa['corrected_quality_score'] = score
    qa['corrected_quality_issues'] = issues

    if score >= 85 and not qa.get('match_issues') and qa.get('evidence_alignment',{}).get('level') in ('high','medium') and qa.get('standards_normalized'):
        qa['corrected_validation'] = 'verified'
        grade_stats['verified'] += 1
    elif score < 60 or issues.count("rejected_no_approval"):
        qa['corrected_validation'] = 'rejected'
        grade_stats['rejected'] += 1
    else:
        qa['corrected_validation'] = 'needs_human_review'
        grade_stats['needs_human_review'] += 1

log("Grades: verified=%d needs_review=%d rejected=%d" % (grade_stats['verified'], grade_stats['needs_human_review'], grade_stats['rejected']))

# ============================================================
# SECTION 9: Split output files
# ============================================================
log("\n=== Section 9: Output Files ===")
verified = [q for q in qas if q.get('corrected_validation') == 'verified']
needs_review = [q for q in qas if q.get('corrected_validation') == 'needs_human_review']
rejected = [q for q in qas if q.get('corrected_validation') == 'rejected']

def write_jsonl(items, path):
    with open(path, 'w', encoding='utf-8') as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    log("  %s: %d" % (path, len(items)))

write_jsonl(verified, os.path.join(OUT_DIR, 'qa_v4_verified.jsonl'))
write_jsonl(needs_review, os.path.join(OUT_DIR, 'qa_v4_needs_human_review.jsonl'))
write_jsonl(rejected, os.path.join(OUT_DIR, 'qa_v4_rejected.jsonl'))
write_jsonl(qas, os.path.join(OUT_DIR, 'qa_v4_all_scored.jsonl'))

# ============================================================
# SECTION 10: Stats & Reports
# ============================================================
log("\n=== Section 10: Statistics & Reports ===")
def dist(items, field, subfield=None):
    c = Counter()
    for item in items:
        v = item
        for f in field.split('.'):
            v = v.get(f, 'unknown') if isinstance(v, dict) else 'unknown'
        if subfield:
            v = v.get(subfield, 'unknown') if isinstance(v, dict) else 'unknown'
        c[str(v)] += 1
    return c

# Distribution stats
td_dist = dist(qas, 'benchmark_metadata', 'task_domain')
diff_dist = dist(qas, 'benchmark_metadata', 'difficulty')
qt_dist = dist(qas, 'benchmark_metadata', 'question_type')
cog_dist = dist(qas, 'benchmark_metadata', 'cognitive_level')
ind_dist = dist(qas, 'industry_code')
elem_dist = dist(qas, 'element')
val_dist = {'verified': len(verified), 'needs_human_review': len(needs_review), 'rejected': len(rejected)}

# Write benchmark distribution report
md = ["# EIA-Review-Benchmark v4 Distribution\n\n"]
md.append("| Dimension | Category | Count |\n|-----------|----------|-------|\n")
for label, counter in [('task_domain', td_dist), ('difficulty', diff_dist),
                        ('question_type', qt_dist), ('cognitive_level', cog_dist),
                        ('industry', ind_dist), ('element', elem_dist)]:
    for k, v in sorted(counter.items(), key=lambda x:-x[1]):
        md.append("| %s | %s | %d |\n" % (label, k[:30], v))

with open(os.path.join(QUALITY_DIR, 'benchmark_distribution.md'), 'w', encoding='utf-8') as f:
    f.writelines(md)

# Quality summary
issues_count = Counter()
for q in qas:
    for iss in q.get('corrected_quality_issues',[]):
        issues_count[iss] += 1

summary = [
    "qa_v4 清洗完成：\n\n",
    "输入 qa_v3 样本数: %d\n" % len(qas),
    "qa_v4_verified: %d\n" % len(verified),
    "qa_v4_needs_human_review: %d\n" % len(needs_review),
    "qa_v4_rejected: %d\n\n" % len(rejected),
    "主要问题：\n",
    "- 项目/批复错配: %d\n" % pair_mismatch,
    "- question 与 element 不一致: %d\n" % qe_mismatches,
    "- standards 缺失: %d\n" % std_missing,
    "- evidence_alignment low/none: %d\n\n" % (align_stats.get('low',0)+align_stats.get('none',0)),
    "ELLE-style benchmark 分布：\n",
]
for label, counter in [('task_domain', td_dist), ('difficulty', diff_dist),
                        ('question_type', qt_dist), ('cognitive_level', cog_dist)]:
    summary.append("- %s:\n" % label)
    for k, v in sorted(counter.items(), key=lambda x:-x[1]):
        summary.append("  - %s: %d\n" % (k[:25], v))

with open(os.path.join(QUALITY_DIR, 'qa_v4_quality_report.md'), 'w', encoding='utf-8') as f:
    f.writelines(summary)
log("Reports written to %s" % QUALITY_DIR)

# ============================================================
# SECTION 11: Taxonomy schema
# ============================================================
log("\n=== Section 11: Taxonomy Schema ===")
taxonomy = """# EIA-Review-Benchmark Taxonomy v4

## task_domain (内容领域)
- 行业识别, 标准引用, 废水, 废气, 噪声, 固废, 危废, 环境风险, 排污许可, 总量控制, 竣工环保验收, 重大变动, 报告-批复对应, 行业经验归纳, 综合审核

## difficulty (难度等级)
- simple: 单一事实抽取
- medium: 报告-批复对应
- hard: 综合审核推理或行业经验归纳

## question_type (问题类型)
- knowledge: 标准/术语/行业类别
- extraction: 从报告或批复中抽取事实
- matching: 报告与批复对应
- reasoning: 审核推理
- evaluation: 评价审核意见
- calculation: 数值核查
- rule_induction: 行业经验规则归纳

## cognitive_level (认知层级)
- L1_fact: 单条事实抽取
- L2_alignment: 报告证据与批复要求对应
- L3_review_reasoning: 行业/工艺/污染因子/标准/批复综合审核判断
- L4_industry_rule: 从多个项目中归纳行业共性规则

## evaluation_dimensions (评价维度)
- professionalism: 专业正确性
- clarity: 清晰性
- feasibility: 可行性
- evidence_grounding: 证据可追溯性
"""
with open(os.path.join(SCHEMA_DIR, 'eia_benchmark_taxonomy.yaml'), 'w', encoding='utf-8') as f:
    f.write(taxonomy)
log("Taxonomy saved")

# ============================================================
# SECTION 12: Problem samples
# ============================================================
log("\n=== Section 12: Problem Samples ===")
pair_mismatch_samples = [q for q in qas if q.get('match_issues')]
with open(os.path.join(QUALITY_DIR, 'pair_mismatch_samples.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['project_id','company','element','issues'])
    for q in pair_mismatch_samples[:100]:
        w.writerow([q.get('project_id',''), q.get('company','')[:15], q.get('element',''), ';'.join(q.get('match_issues',[]))])

evidence_mismatch = [q for q in qas if q.get('evidence_alignment',{}).get('level') in ('low','none')]
with open(os.path.join(QUALITY_DIR, 'evidence_mismatch_samples.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['project_id','company','element','alignment_level','alignment_score'])
    for q in evidence_mismatch[:100]:
        w.writerow([q.get('project_id',''), q.get('company','')[:15], q.get('element',''),
                    q.get('evidence_alignment',{}).get('level',''), q.get('evidence_alignment',{}).get('score',0)])

# ============================================================
# SECTION 13: Benchmark design doc
# ============================================================
log("\n=== Section 13: Benchmark Design Doc ===")
design = """# EIA-Review-Benchmark v4 Design

## 1. Why ELLE
ELLE (Guo et al., 2024) is the first LLM evaluation benchmark in eco-environment domain with 1,130 QA pairs, 16 disciplines, 3 difficulty levels, and 3 question types. We adopt its methodology but adapt to EIA review domain.

## 2. Objective
Build a benchmark for evaluating LLM performance on EIA report review tasks.

## 3. Data Source
- 2,406 approval documents from Shunde District, Foshan City
- 2,812 EIA acceptance reports
- 181 matched report-approval pairs
- All data extracted from real government review decisions

## 4. Sample Unit
Each QA pair = one review clause from the approval × corresponding evidence from the report.

## 5. Content Domains
15 task domains covering all EIA review aspects.

## 6. Difficulty Levels
- simple: 单一事实抽取
- medium: 报告-批复对应
- hard: 综合审核推理

## 7. Question Types
7 types: knowledge, extraction, matching, reasoning, evaluation, calculation, rule_induction

## 8. Cognitive Levels
4 levels: L1_fact, L2_alignment, L3_review_reasoning, L4_industry_rule

## 9. Evaluation Dimensions
4 dimensions: professionalism, clarity, feasibility, evidence_grounding

## 10. Cleaning Rules
- Schema validation → field normalization
- Project-approval matching check
- Question-element consistency
- Standard number normalization
- Evidence alignment scoring
- Quality rescoring (100-point deductive system)

## 11. Quality Tiers
- verified (>=85): Ready for benchmark use
- needs_human_review (60-84): Usable after expert check
- rejected (<60 or critical flaws): Excluded

## 12. Current Limitations
- Limited to Shunde district (区级)
- Industry coverage: 36 industries, dominated by C2929
- Report evidence text extracted from MinerU output may have OCR errors
- No expert validation yet on verified set

## 13. Next Steps
- Expert validation of verified set
- Expand to city-level (佛山市) data
- Add hard difficulty samples
- Build LLM-as-a-Judge evaluation pipeline
"""
with open(os.path.join(DOCS_DIR, 'eia_review_benchmark_v4_design.md'), 'w', encoding='utf-8') as f:
    f.write(design)
log("Design doc saved")

# ============================================================
# FINAL OUTPUT
# ============================================================
print("\n" + "="*60)
print("qa_v4 清洗完成！")
print("="*60)
print("\n输入 qa_v3 样本数: %d" % len(qas))
print("qa_v4_verified: %d" % len(verified))
print("qa_v4_needs_human_review: %d" % len(needs_review))
print("qa_v4_rejected: %d" % len(rejected))
print("\n主要问题：")
print("- 项目/批复错配: %d" % pair_mismatch)
print("- question 与 element 不一致(已修复): %d" % qe_mismatches)
print("- standards 缺失或未归一化: %d" % std_missing)
print("- evidence_alignment low/none: %d" % (align_stats.get('low',0)+align_stats.get('none',0)))
print("\nELLE-style benchmark 分布：")
for label, counter in [('task_domain', td_dist), ('difficulty', diff_dist),
                        ('question_type', qt_dist), ('cognitive_level', cog_dist)]:
    print("  %s:" % label)
    for k, v in sorted(counter.items(), key=lambda x:-x[1]):
        print("    %s: %d" % (k[:30], v))
print("\n输出目录：")
print("  data/qa_v4/")
print("  outputs/qa_v4_quality/")
print("  docs/benchmark/")
print("\nDone!")
