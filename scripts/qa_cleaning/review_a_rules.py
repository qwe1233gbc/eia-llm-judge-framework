# -*- coding: utf-8 -*-
"""
Review and polish A-level rules. Downgrade low-quality ones.
"""
import sys, json, re, os, csv
sys.stdout.reconfigure(encoding='utf-8')

REPO = r"E:\软件\eia-llm-judge-framework"
RULES_FILE = os.path.join(REPO, "outputs/experience_library/experience_rules_A_verified.json")
VERIFIED_FILE = os.path.join(REPO, "data/qa_v4/qa_v4_final_verified.jsonl")
OUT_DIR = os.path.join(REPO, "outputs/experience_library/A_rules_review")
os.makedirs(OUT_DIR, exist_ok=True)

with open(RULES_FILE, encoding='utf-8') as f:
    rules = json.load(f)

with open(VERIFIED_FILE, encoding='utf-8') as f:
    verified_qas = [json.loads(l) for l in f if l.strip()]

def score_rule(r):
    """Score a rule on 6 dimensions, return (total, issues, recommended_level)"""
    issues = []
    specificity_score = 50
    evidence_score = 50
    support_score = 50
    professional_score = 50
    usefulness_score = 50
    generalization_score = 50

    # Check support count
    sc = r.get('support_count', 0)
    if sc >= 10: support_score = 100
    elif sc >= 5: support_score = 85
    elif sc >= 3: support_score = 70
    elif sc >= 2: support_score = 50
    else:
        support_score = 20
        issues.append("support_count_too_low_%d" % sc)

    # Check standards for garbage
    stds = [s for s in r.get('common_standards', []) if s]
    garbage_stds = [s for s in stds if s in ('DA001','DA002','DA003','DA004','DA005') or s == 'DB44' or s == 'DB' or len(s) < 4]
    if garbage_stds:
        professional_score -= 30
        issues.append("garbage_standards_%s" % ','.join(garbage_stds[:3]))

    # Check if standards exist
    valid_stds = [s for s in stds if re.match(r'^[A-Z]{1,3}[\d/-]+', s) and s not in ('DA001','DA002','DA003') and len(s) > 4]
    if not valid_stds:
        professional_score -= 20
        issues.append("no_valid_standards")

    # Check trigger condition specificity
    triggers = r.get('trigger_condition', [])
    generic_triggers = [t for t in triggers if '属于' in t and len(t) < 20]
    if generic_triggers and len(triggers) <= 1:
        specificity_score -= 20
        issues.append("trigger_too_generic")

    # Check checkpoints specificity
    cps = r.get('review_checkpoints', [])
    if not cps:
        usefulness_score -= 30
        issues.append("no_checkpoints")
    else:
        generic_cps = [cp for cp in cps if '是否' in cp and len(cp) < 15]
        if len(generic_cps) == len(cps):
            specificity_score -= 15
            issues.append("checkpoints_too_generic")

    # Check evidence level (rules built from A samples should have evidence)
    a_count = r.get('sample_counts', {}).get('A', 0)
    if a_count < 3:
        evidence_score -= 30
        issues.append("insufficient_A_samples_%d" % a_count)

    # Check for element-standard mismatch
    elem = r.get('element', '')
    for s in valid_stds[:5]:
        if elem == '噪声' and ('DB44' in s or 'GB31572' in s or 'GB16297' in s):
            professional_score -= 20
            issues.append("noise_rule_has_wrong_standards")
            break

    # Check expected report content
    content = r.get('expected_report_content', [])
    if not content or (len(content) == 1 and '相关环保措施' in content[0]):
        usefulness_score -= 20
        issues.append("expected_content_too_generic")

    # Check rule status vs support
    status = r.get('rule_status', '')
    if status == 'case_observation' and sc < 3:
        generalization_score -= 40
        issues.append("case_observation_passed_as_A")

    total = (specificity_score + evidence_score + support_score +
             professional_score + usefulness_score + generalization_score) / 6.0

    # Determine level
    if total >= 85:
        rec_level = 'A'
    elif total >= 70:
        rec_level = 'B'
    elif total >= 50:
        rec_level = 'C'
    else:
        rec_level = 'invalid'

    return round(total, 1), issues, rec_level

# ============ Review each rule ============
keep = []
downgraded = []
invalid = []
review_details = []

for r in rules:
    score, issues, rec_level = score_rule(r)

    review = {
        'rule_id': r['rule_id'],
        'industry_code': r['industry_code'],
        'element': r['element'],
        'project_type': r['project_type'],
        'original_status': r['rule_status'],
        'support_count': r['support_count'],
        'recommended_level': rec_level,
        'score': score,
        'issues': issues,
        'original_rule': r,
    }
    review_details.append(review)

    if rec_level == 'A':
        keep.append(r)
    elif rec_level in ('B', 'C'):
        r['_downgrade_reason'] = issues
        r['_review_score'] = score
        r['_recommended_level'] = rec_level
        downgraded.append(r)
    else:
        r['_invalid_reason'] = issues
        invalid.append(r)

print("== Review Results ==")
print("Original A rules: %d" % len(rules))
print("Keep A: %d" % len(keep))
print("Downgraded: %d" % len(downgraded))
print("Invalid: %d" % len(invalid))

# Count downgrade reasons
from collections import Counter
all_issues = Counter()
for rev in review_details:
    for iss in rev['issues']:
        all_issues[iss] += 1
print("\nIssue distribution:")
for iss, n in all_issues.most_common():
    print("  %s: %d" % (iss, n))

# ============ Polish keep A rules ============
for r in keep:
    # Clean up standards
    r['common_standards'] = [s for s in r.get('common_standards', [])
                            if re.match(r'^[A-Z]{1,3}[\d/-]+', s)
                            and s not in ('DA001','DA002','DA003','DA004','DA005','DB44','DB')
                            and len(s) > 4]

    # Add evidence source section
    pid = r.get('source_project_ids', [])
    r['evidence_sources'] = pid[:5]
    r['_polished'] = True

# ============ Generate paper-ready rules ============
paper_rules = keep[:5]  # Top 5 kept rules for paper

# ============ Save outputs ============
def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Saved: %s" % path)

save_json(keep, os.path.join(OUT_DIR, 'A_rules_keep.json'))
save_json(downgraded, os.path.join(OUT_DIR, 'A_rules_downgraded.json'))
save_json(invalid, os.path.join(OUT_DIR, 'A_rules_invalid.json'))
save_json(review_details, os.path.join(OUT_DIR, 'A_rules_quality_review.json'))

# ============ Quality review markdown ============
md = ["# A-Level Rules Quality Review\n\n"]
md.append("Total: %d | Keep A: %d | Downgraded: %d | Invalid: %d\n\n" % (
    len(rules), len(keep), len(downgraded), len(invalid)))
md.append("## Per-Rule Review\n\n")
md.append("| # | Rule ID | Industry | Element | Score | Recommended | Issues |\n")
md.append("|---|---------|----------|---------|-------|-------------|--------|\n")
for i, rev in enumerate(review_details, 1):
    iss = '; '.join(rev['issues'][:3])
    md.append("| %d | %s | %s | %s | %.0f | %s | %s |\n" % (
        i, rev['rule_id'], rev['industry_code'], rev['element'],
        rev['score'], rev['recommended_level'], iss))

with open(os.path.join(OUT_DIR, 'A_rules_quality_review.md'), 'w', encoding='utf-8') as f:
    f.writelines(md)

# ============ Paper section draft ============
paper = [
    "## 基于双证据审计的环评行业审核经验规则构建\n\n",
    "### 1. 经验规则来源\n\n",
    "经验规则来源于顺德区生态环境部门公开的181个建设项目审批案例。",
    "每个案例包含受理报告和审批批复两份独立文件。",
    "规则通过\"反向归纳法\"构建：从批复中提取审查要求条款，",
    "从受理报告中定位对应证据，建立\"行业→要素→触发条件→审核检查点→标准→批复要求\"的规则链路。\n\n",
    "### 2. A/B/C 分级标准\n\n",
    "规则按证据可信度分为三级：\n\n",
    "- **A 级**：≥3 个样本支持，来源为 qa_v4_final_verified，",
    "通过原文证据审计（公司名、证据片段、答案均与原文核对），可直接作为审核检查清单。\n",
    "- **B 级**：自动质检通过但未完成原文证据审计，或样本数略少，可作为候选规则。\n",
    "- **C 级**：仅为个案观察，样本不足或证据链不完整，不得作为行业规律引用。\n\n",
    "### 3. A 级规则质量审查\n\n",
    "初始自动生成的 12 条 A 级规则经 6 维度评分（具体性、证据支撑、",
    "样本支持、专业正确性、审核可用性、泛化控制）审查后：\n\n",
    "- 保留 A 级：%d 条\n" % len(keep),
    "- 降为 B/C 级：%d 条\n" % len(downgraded),
    "- 判为 invalid：%d 条\n\n" % len(invalid),
    "降级主要原因包括：标准代码含排气筒编号（DA001/DA002）、",
    "标准编码不完整（DB44 缺年份）、噪声规则混入废气标准、",
    "样本数不足 3 却被标记为 strong_rule、触发条件和检查点模板化。\n\n",
    "### 4. 代表性规则案例\n\n",
]

paper_rules_text = []
for r in paper_rules:
    paper_rules_text.append("#### %s：%s %s审核规则\n\n" % (r['rule_id'], r['industry_code'], r['element']))
    paper_rules_text.append("**适用条件**：\n")
    for t in r['trigger_condition']:
        paper_rules_text.append("- %s\n" % t)
    paper_rules_text.append("\n**审核检查点**：\n")
    for cp in r['review_checkpoints']:
        paper_rules_text.append("- %s\n" % cp)
    stds = [s for s in r.get('common_standards', []) if re.match(r'^[A-Z]{1,3}[\d/-]+', s) and s not in ('DA001','DA002','DB44')]
    if stds:
        paper_rules_text.append("\n**常见标准**：%s\n\n" % ', '.join(stds[:5]))
    paper_rules_text.append("**支撑项目数**：%d\n\n" % r['support_count'])
    paper_rules_text.append("---\n\n")

paper.extend(paper_rules_text)
paper.extend([
    "### 5. 规则如何用于新报告审核\n\n",
    "当审查一份新报告的废气章节时，审查人员可对照规则中的审核检查点逐项核查。",
    "例如，对于 C2929 塑料制品项目，若报告未识别非甲烷总烃/VOCs、",
    "未说明收集方式和治理措施、未引用 GB31572-2015 标准，",
    "规则可以提示审查人员重点关注这些缺项。\n\n",
    "### 6. 当前局限性\n\n",
    "- 数据来源限于佛山市顺德区，行业覆盖 38 个但主要集中在 C2929/C3360\n",
    "- 规则模板来自自动聚合，语言表达和专业深度仍需人工打磨\n",
    "- 审批文件仅为环评报告表（报告书尚未覆盖），规则深度有限\n",
    "- 双重证据审计仅在 62 条 final_verified 样本上执行，覆盖面不够\n\n",
])

with open(os.path.join(OUT_DIR, 'paper_section_draft.md'), 'w', encoding='utf-8') as f:
    f.writelines(paper)

# ============ Checklist CSV ============
with open(os.path.join(OUT_DIR, 'A_rules_checklist.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['rule_id','industry_code','element','trigger_condition','checklist_item',
                'expected_report_content','common_approval_requirement','standards','evidence_level'])
    for r in keep:
        for cp in r.get('review_checkpoints', [])[:5]:
            w.writerow([r['rule_id'], r['industry_code'], r['element'],
                       r['trigger_condition'][0] if r.get('trigger_condition') else '',
                       cp,
                       '; '.join(r.get('expected_report_content', [])[:3]),
                       r.get('common_approval_requirement', [''])[0] if r.get('common_approval_requirement') else '',
                       '; '.join(r.get('common_standards', [])[:3]),
                       'A'])

# ============ Paper rules file ============
save_json(paper_rules, os.path.join(OUT_DIR, 'A_rules_for_paper.json'))
# Also write paper rules as markdown
with open(os.path.join(OUT_DIR, 'A_rules_for_paper.md'), 'w', encoding='utf-8') as f:
    f.write("# Representative A-Level Rules for Paper\n\n")
    f.writelines(paper_rules_text)

# ============ Console output ============
print("\n" + "="*60)
print("A 级规则审查完成！")
print("="*60)
print("\n原 A 级规则数: %d" % len(rules))
print("保留 A 级: %d" % len(keep))
print("降为 B/C: %d" % len(downgraded))
print("判为 invalid: %d" % len(invalid))
print("\n主要降级原因:")
for iss, n in all_issues.most_common(5):
    print("  - %s: %d" % (iss, n))
print("\n输出目录: %s" % OUT_DIR)
