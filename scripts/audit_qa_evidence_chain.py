#!/usr/bin/env python3
"""
环评 QA 数据集证据链审计助手
================================
审计 data/ 下的 QA 对，建立证据索引和原文溯源记录，
输出分级结果到 data/audit/。

运行: python scripts/audit_qa_evidence_chain.py --input data --output data/audit
"""

import argparse
import json
import os
import re
import sys
import glob
from collections import defaultdict
from datetime import datetime


# ============================================================
# 1. 输入扫描
# ============================================================
def scan_input_files(input_dir):
    """递归扫描 input_dir 下的 QA 和证据文件"""
    qa_files = []
    evidence_files = []
    theory_dirs = ['llm_wiki', 'wiki', 'theory', 'domain_knowledge']

    for root, dirs, files in os.walk(input_dir):
        # 跳过输出目录和 .git
        if 'audit' in root.split(os.sep) or '.git' in root.split(os.sep):
            continue
        for f in files:
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, input_dir)
            ext = os.path.splitext(f)[1].lower()
            if ext in ('.jsonl', '.json'):
                qa_files.append(fp)
            elif ext in ('.md', '.txt'):
                # 判断是证据文件还是理论文件
                parent = os.path.basename(os.path.dirname(fp))
                is_theory = any(d in rel.split(os.sep) for d in theory_dirs)
                if is_theory:
                    evidence_files.append(('theory', fp))
                else:
                    evidence_files.append(('evidence', fp))

    return qa_files, evidence_files


def load_qa_file(filepath):
    """加载 QA 文件(json/jsonl)，返回列表"""
    results = []
    try:
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.jsonl':
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            results.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        elif ext == '.json':
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    results.extend(data)
                elif isinstance(data, dict):
                    results.append(data)
    except Exception as e:
        print(f"  [WARN] 跳过 {filepath}: {e}")
    return results


# ============================================================
# 2. 建立证据索引
# ============================================================
def build_evidence_index(evidence_files, input_dir):
    """构建证据索引"""
    index = {
        'report_index': [],
        'approval_index': [],
        'standard_index': [],
        'historical_case_index': [],
        'llm_wiki_theory_index': []
    }

    for ftype, fp in evidence_files:
        rel = os.path.relpath(fp, input_dir)
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            continue

        source_type = 'report'
        if 'approval' in rel.lower():
            source_type = 'approval'
        elif 'standards' in rel.lower() or 'policy' in rel.lower() or '标准' in rel or '导则' in rel:
            source_type = 'standard'
        elif 'historical_db' in rel.lower():
            source_type = 'historical_case'
        elif any(d in rel.split(os.sep) for d in ['llm_wiki', 'wiki', 'theory', 'domain_knowledge']):
            source_type = 'theory'
            for i, line in enumerate(lines):
                if line.strip():
                    entry = {
                        'source_type': 'theory',
                        'source_file': rel,
                        'project_id': '',
                        'standard_code': '',
                        'standard_name': '',
                        'section_title': '',
                        'line_start': i,
                        'line_end': i,
                        'text': line.strip()[:500]
                    }
                    index['llm_wiki_theory_index'].append(entry)
            continue

        # 对 md/txt 按段切分
        current_section = ''
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            # 识别标题
            if re.match(r'^#{1,6}\s+', stripped):
                current_section = re.sub(r'^#+\s*', '', stripped)
            # 每20行或每段作为一个条目
            entry = {
                'source_type': source_type,
                'source_file': rel,
                'project_id': _extract_project_id(rel, lines),
                'standard_code': _extract_standard_code(stripped),
                'standard_name': '',
                'section_title': current_section,
                'line_start': i,
                'line_end': i,
                'text': stripped[:500]
            }
            key = f'{source_type}_index'
            if key in index:
                index[key].append(entry)

    return index


def _extract_project_id(rel, lines):
    """从路径和内容中提取项目ID"""
    m = re.search(r'pair_(\d+)', rel)
    if m:
        return f'pair_{m.group(1)}'
    m = re.search(r'([a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', rel, re.I)
    if m:
        return m.group(1)
    return ''


def _extract_standard_code(text):
    """从文本中提取标准编号"""
    patterns = [
        r'(?:GB|HJ|DB\d{2}|GB/T|HJ/T|DB\d{2}/T)\s*[\d.]+[-—]\s*\d{4}',
        r'(?:GB|HJ|DB\d{2}|GB/T|HJ/T|DB\d{2}/T)\s*[\d.]+',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return m.group()
    return ''


# ============================================================
# 3. LLM Wiki 理论辅助索引
# ============================================================
def build_llm_wiki_theory_index(input_dir):
    """从 theory/wiki 目录构建理论索引"""
    index = []
    theory_dirs = ['llm_wiki', 'wiki', 'theory', 'domain_knowledge']
    found = False

    for d in theory_dirs:
        path = os.path.join(input_dir, d)
        if not os.path.isdir(path):
            continue
        for root, dirs, files in os.walk(path):
            for f in files:
                if not f.endswith(('.md', '.txt', '.json', '.jsonl')):
                    continue
                found = True
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, input_dir)
                try:
                    with open(fp, 'r', encoding='utf-8') as fh:
                        content = fh.read()
                except Exception:
                    continue

                # 按行处理
                lines = content.split('\n')
                current_concept = ''
                for i, line in enumerate(lines):
                    s = line.strip()
                    if not s:
                        continue
                    if re.match(r'^#{1,3}\s+', s):
                        current_concept = re.sub(r'^#+\s*', '', s)
                    entry = {
                        'theory_id': f"{os.path.splitext(f)[0]}_{i:04d}",
                        'concept': current_concept,
                        'aliases': _generate_aliases(s),
                        'definition': s[:300],
                        'related_processes': _find_related_processes(s),
                        'related_pollutants': _find_related_pollutants(s),
                        'related_measures': _find_related_measures(s),
                        'risk_warnings': _find_risk_warnings(s),
                        'source_file': rel,
                        'line_start': i,
                        'line_end': i,
                        'review_status': 'llm_generated_unchecked',
                        'evidence_role': 'theory_auxiliary_only',
                        'can_support_gold_answer': False
                    }
                    index.append(entry)

    if not found:
        # 创建空索引模板
        print("  [INFO] 未找到理论/知识目录，创建空索引模板")
        index.append({
            'theory_id': 'template_placeholder',
            'concept': '（无理论数据，此为占位模板）',
            'aliases': [],
            'definition': '请将环评理论、导则说明、技术规范解读放入 data/llm_wiki/、data/theory/ 等目录',
            'related_processes': [],
            'related_pollutants': [],
            'related_measures': [],
            'risk_warnings': [],
            'source_file': '',
            'line_start': 0,
            'line_end': 0,
            'review_status': 'unknown',
            'evidence_role': 'theory_auxiliary_only',
            'can_support_gold_answer': False
        })

    return index


def _generate_aliases(text):
    """为关键词生成同义词/扩展词"""
    alias_map = {
        'VOCs': ['挥发性有机物', '非甲烷总烃', 'NMHC', '有机废气'],
        '废活性炭': ['饱和活性炭', '危险废物', 'HW49', '废吸附剂'],
        '袋式除尘': ['布袋除尘', '过滤除尘', '袋滤'],
        '活性炭吸附': ['活性炭', '吸附装置', 'VOCs吸附'],
        '集气罩': ['集气设施', '收集罩', '吸气罩', '排风罩'],
        '排气筒': ['DA001', 'DA002', '排放口', '烟囱'],
        '化粪池': ['三级化粪', '预处理'],
        'COD': ['化学需氧量', 'CODCr'],
        '氨氮': ['NH3-N', 'NH₃-N'],
        '总磷': ['TP', '磷酸盐'],
    }
    result = []
    for key, vals in alias_map.items():
        if key in text:
            result.extend(vals)
    return result


def _find_related_processes(text):
    processes = ['注塑', '印刷', '涂装', '喷漆', '烘干', '焊接', '破碎', '混料',
                 '挤塑', '吹塑', '发泡', '硫化', '清洗', '电镀', '酸洗']
    return [p for p in processes if p in text]


def _find_related_pollutants(text):
    pollutants = ['VOCs', '非甲烷总烃', 'NMHC', '颗粒物', '粉尘', 'SO₂', 'NOx',
                  '苯', '甲苯', '二甲苯', '苯乙烯', '臭气', '硫化氢']
    return [p for p in pollutants if p in text]


def _find_related_measures(text):
    measures = ['活性炭吸附', '袋式除尘', '旋风除尘', '水喷淋', '催化燃烧',
                '冷凝回收', 'UV光解', '等离子', '集气罩', '密闭收集']
    return [m for m in measures if m in text]


def _find_risk_warnings(text):
    warnings = []
    if re.search(r'旧标准|废止|替代|更新|新版', text): warnings.append('标准版本可能已更新')
    if re.search(r'浓度高|超标|风险|隐患', text): warnings.append('存在超标风险')
    if re.search(r'不明确|待定|需核实', text): warnings.append('描述不明确需要核实')
    if re.search(r'VOCs|有机废气', text) and not re.search(r'收集|处理|治理', text): warnings.append('VOCs无收集/处理措施说明')
    return warnings


# ============================================================
# 4. 拆解 QA 为 claim
# ============================================================
CLAIM_PATTERNS = [
    ('项目基本信息', [
        r'(建设单位|申报单位)([^。]*?)(?:公司|厂|企业)',
        r'(项目名称|建设内容)([^。]*)',
        r'(建设性质|新建|改建|扩建|技改|迁建)',
        r'(建设地点|地址|位于)([^。]*)',
        r'(行业类别|行业代码)([^。]*)',
    ]),
    ('污染源', [
        r'(废气|废水|噪声|固废|危废|生态|风险|地下水)([^。]*?)(?:污染|排放|产生)',
        r'(注塑|印刷|涂装|焊接|破碎|混料|烘干)([^。]*?)(?:废气|工序|工位)',
        r'(有组织|无组织)([^。]*?)(?:排放|废气)',
    ]),
    ('污染因子', [
        r'(VOCs|NMHC|非甲烷总烃|挥发性有机物)([^。]*)',
        r'(颗粒物|粉尘|烟尘)([^。]*)',
        r'(苯|甲苯|二甲苯|苯乙烯)([^。]*)',
        r'(臭气浓度|硫化氢|氨|恶臭)([^。]*)',
        r'(COD|氨氮|总磷|SS|BOD|石油类)([^。]*)',
        r'(SO₂|NOx|氮氧化物|二氧化硫)([^。]*)',
    ]),
    ('治理措施', [
        r'(集气罩|密闭|收集|集气)([^。]*?)(?:设施|方式|效率)',
        r'(活性炭|吸附|催化燃烧|RTO|RCO|沸石)([^。]*)',
        r'(袋式除尘|旋风除尘|水喷淋|洗涤|静电)([^。]*)',
        r'(排气筒|DA00|排放口|烟囱)([^。]*)',
        r'(治理设施|处理效率|去除率)([^。]*)',
    ]),
    ('标准依据', [
        r'(GB|HJ|DB|HJ/T|GB/T|DB/T)\s*[\d.]+',
        r'(执行|达到|满足|符合|参照)([^。]*?)(?:标准|限值|要求)',
        r'(排放限值|排放标准|厂界|浓度限值)([^。]*)',
    ]),
    ('批复要求', [
        r'(批复|审批|环保局|生态环境局)([^。]*?)(?:要求|意见|批复)',
        r'(总量|排污许可|验收|监测|危废|委托)([^。]*)',
        r'(污染防治|环境保护|整改|限期)([^。]*)',
    ]),
    ('判断结论', [
        r'(达标|合规|可行|满足|符合)([^。]*)',
        r'(不达标|不合规|缺漏|矛盾|不一致)([^。]*)',
        r'(部分匹配|无法判断|需补充)([^。]*)',
    ]),
]


def decompose_claims(qa):
    """将 QA 的 answer 拆解为最小可验证声明"""
    claims = []
    answer = qa.get('answer', qa.get('reference_answer', qa.get('standard_answer', '')))
    question = qa.get('question', '')
    text = f"{question} {answer}"

    for claim_type, patterns in CLAIM_PATTERNS:
        for pattern in patterns:
            for m in re.finditer(pattern, text):
                claim_text = m.group().strip()
                if len(claim_text) < 6:
                    continue
                # 去重
                if not any(c['claim'] == claim_text for c in claims):
                    claims.append({
                        'claim': claim_text[:300],
                        'claim_type': claim_type,
                        'support_status': 'unsupported',
                        'source_type': '',
                        'source_file': '',
                        'section_title': '',
                        'line_start': 0,
                        'line_end': 0,
                        'exact_quote': '',
                        'theory_assist': {
                            'used': False,
                            'theory_id': '',
                            'expanded_terms': [],
                            'role': ''
                        },
                        'explanation': ''
                    })

    if not claims:
        claims.append({
            'claim': text[:200],
            'claim_type': 'general',
            'support_status': 'unsupported',
            'source_type': '',
            'source_file': '',
            'section_title': '',
            'line_start': 0,
            'line_end': 0,
            'exact_quote': '',
            'theory_assist': {
                'used': False,
                'theory_id': '',
                'expanded_terms': [],
                'role': ''
            },
            'explanation': ''
        })

    return claims


# ============================================================
# 5. 原文溯源
# ============================================================
def trace_claims(claims, evidence_index, llm_wiki_index, qa, input_dir):
    """对每个 claim 进行原文溯源"""
    missing_sources = set()

    # 收集 QA 自带的证据
    qa_evidences = _collect_qa_evidence(qa)

    for claim in claims:
        # 先用理论索引扩展检索词
        expanded_terms = _expand_with_theory(claim['claim'], llm_wiki_index)
        if expanded_terms:
            claim['theory_assist'] = {
                'used': True,
                'theory_id': '',
                'expanded_terms': expanded_terms,
                'role': 'retrieval_expansion'
            }

        # 在 QA 自带 evidence 中查找
        found_in_qa = _search_in_qa_evidence(claim['claim'], qa_evidences)
        if found_in_qa:
            claim.update(found_in_qa)
            claim['support_status'] = 'direct_supported'
            continue

        # 在 evidence_index 中查找
        found = False
        for idx_key in ['report_index', 'approval_index', 'standard_index', 'historical_case_index']:
            for entry in evidence_index.get(idx_key, []):
                if _text_match(claim['claim'], entry['text']):
                    # 只允许同项目 report/approval 匹配
                    if idx_key in ('report_index', 'approval_index'):
                        qa_project = qa.get('qa_id', qa.get('pair_id', ''))
                        entry_project = entry.get('project_id', '')
                        if entry_project and qa_project and entry_project not in qa_project and qa_project not in entry_project:
                            continue

                    claim.update({
                        'support_status': 'direct_supported' if idx_key != 'historical_case_index' else 'indirect_supported',
                        'source_type': idx_key.replace('_index', ''),
                        'source_file': entry['source_file'],
                        'section_title': entry['section_title'],
                        'line_start': entry['line_start'],
                        'line_end': entry['line_end'],
                        'exact_quote': entry['text'][:300],
                        'explanation': f'在 {entry["source_file"]} 中找到匹配文本'
                    })
                    found = True
                    break
            if found:
                break

        if not found:
            # 检查是否有对应文件缺失
            claim['support_status'] = 'unsupported'
            claim['explanation'] = '未在证据索引和QA自带evidence中找到匹配原文'
            missing_sources.add('evidence_index_no_match')

    return claims, list(missing_sources)


def _collect_qa_evidence(qa):
    """收集QA中自带的证据字段"""
    evidences = []
    for key in ['report_evidence', 'approval_evidence', 'standard_evidence']:
        evs = qa.get(key, [])
        if isinstance(evs, list):
            for e in evs:
                if isinstance(e, dict):
                    e['_source_key'] = key
                    evidences.append(e)
                elif isinstance(e, str):
                    evidences.append({'text': e, '_source_key': key})
        elif isinstance(evs, str):
            evidences.append({'text': evs, '_source_key': key})
    return evidences


def _search_in_qa_evidence(claim_text, evidences):
    """在 QA 自带 evidence 中搜索"""
    for ev in evidences:
        ev_text = ev.get('text', '') if isinstance(ev, dict) else str(ev)
        if _text_match(claim_text, ev_text[:1000]):
            return {
                'source_type': ev.get('_source_key', '').replace('_evidence', ''),
                'source_file': ev.get('source_file', 'qa自带evidence'),
                'section_title': ev.get('section', ev.get('section_title', '')),
                'line_start': ev.get('char_start', ev.get('line_start', 0)),
                'line_end': ev.get('char_end', ev.get('line_end', 0)),
                'exact_quote': ev_text[:300],
                'explanation': '在QA自带evidence中找到匹配'
            }
    return None


def _text_match(claim, text):
    """检查 claim 是否在 text 中出现"""
    # 提取核心词
    core = claim.strip()
    if len(core) < 4:
        return False
    words = re.split(r'[\s,，。；;、]', core)
    keywords = [w for w in words if len(w) >= 4]
    if not keywords:
        keywords = [core[:10]]

    # 至少2/3关键词匹配
    match_count = sum(1 for k in keywords if k in text)
    return match_count >= max(2, int(len(keywords) * 0.6))


def _expand_with_theory(claim_text, llm_wiki_index):
    """用理论索引扩展检索词"""
    expanded = []
    for entry in llm_wiki_index:
        concept = entry.get('concept', '')
        if any(w in claim_text for w in [concept] if concept):
            expanded.extend(entry.get('aliases', []))
    return list(set(expanded))


# ============================================================
# 6. 审计分级
# ============================================================
def determine_audit_status(claims, qa, missing_sources, has_report_evidence, has_approval_evidence):
    """确定 audit_status"""
    supported = sum(1 for c in claims if c['support_status'] in ('direct_supported', 'indirect_supported'))
    unsupported = sum(1 for c in claims if c['support_status'] == 'unsupported')
    contradicted = sum(1 for c in claims if c['support_status'] == 'contradicted')
    total = len(claims) if claims else 1

    # 检查 rejection 条件
    answer = qa.get('answer', qa.get('reference_answer', qa.get('standard_answer', '')))
    if not answer or answer in ('', '未提供', '无'):
        return 'rejected', '答案为空或为占位符'

    if '[PLACEHOLDER]' in answer or answer.strip().startswith('{'):
        return 'rejected', '答案为占位符或JSON结构，无实际内容'

    # 检查是否来自 historical_db（缺 report/standard 证据）
    is_historical = any('historical_db' in str(qa.get(k, '')) for k in ['qa_id', 'pair_id', 'source_file'])

    if contradicted > 0:
        return 'rejected', f'存在 {contradicted} 个矛盾的 claim'

    # 检查报告-批复证据
    if is_historical:
        return 'reference_case', '来自历史数据库，缺乏报告原文和标准原文证据'

    if not has_report_evidence or not has_approval_evidence:
        return 'need_human_review', '缺少report_evidence或approval_evidence'

    if unsupported > 0:
        if unsupported <= total * 0.3:
            return 'need_human_review', f'{unsupported}/{total} 个claim未找到原文支持'
        else:
            return 'rejected', f'{unsupported}/{total} 个claim未找到原文支持，证据链严重不足'

    # 检查标准版本
    std_risk = 'none'
    for c in claims:
        if '标准' in c['claim_type'] and c['support_status'] == 'unsupported':
            std_risk = 'unknown'

    # gold_verified 条件
    if supported >= total * 0.8 and has_report_evidence and has_approval_evidence:
        return 'gold_verified', ''
    else:
        return 'need_human_review', '证据支持度不足 gold_verified 标准'


def check_standard_version_risk(answer_text):
    """检查标准版本风险"""
    outdated_patterns = [
        (r'DB44/27-2001', 'DB44/27-2001 已被 DB44/2367-2022 部分替代'),
        (r'GB16297-1996', 'GB16297-1996 已有较新行业标准替代'),
        (r'GB12348-90', '已被 GB12348-2008 替代'),
        (r'GB13223-1996', '已被 GB13223-2011 替代'),
        (r'DB44/26-2001', 'DB44/26-2001 已被 DB44/2367-2022 部分替代'),
        (r'GB8978-1996', '已有行业排放标准替代'),
    ]
    for pattern, warning in outdated_patterns:
        if re.search(pattern, answer_text):
            return 'outdated', warning
    return 'none', ''


# ============================================================
# 7. 证据完整性评分
# ============================================================
def calculate_score(claims, audit_status, missing_sources):
    """计算 evidence_completeness_score (0-100)"""
    total = len(claims) if claims else 1
    supported = sum(1 for c in claims if c['support_status'] in ('direct_supported', 'indirect_supported'))
    direct = sum(1 for c in claims if c['support_status'] == 'direct_supported')

    base = int((direct / total) * 60) + int(((supported - direct) / total) * 20)

    if audit_status == 'rejected':
        base = min(base, 30)
    elif audit_status == 'reference_case':
        base = min(base, 50)
    elif audit_status == 'need_human_review':
        base = min(base, 75)
    elif audit_status == 'gold_verified':
        base = max(base, 80)

    if missing_sources:
        base -= len(missing_sources) * 5

    return max(0, min(100, base))


# ============================================================
# 8. 主审计流程
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='环评 QA 证据链审计助手')
    parser.add_argument('--input', default='data', help='输入目录')
    parser.add_argument('--output', default='data/audit', help='输出目录')
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input)
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    print(f"=" * 60)
    print(f"  环评 QA 证据链审计")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 60)

    # --- 1. 扫描输入 ---
    print(f"\n[1/8] 扫描输入文件...")
    qa_files, evidence_files = scan_input_files(input_dir)
    print(f"  找到 {len(qa_files)} 个 QA 文件, {len(evidence_files)} 个证据/理论文件")

    all_qa = []
    qa_source_map = {}
    for fp in qa_files:
        qas = load_qa_file(fp)
        rel = os.path.relpath(fp, input_dir)
        all_qa.extend(qas)
        for q in qas:
            qa_source_map[q.get('qa_id', q.get('pair_id', f'unknown_{len(qa_source_map)}'))] = rel
    print(f"  共加载 {len(all_qa)} 条 QA 记录")

    # --- 2. 建立证据索引 ---
    print(f"\n[2/8] 建立证据索引...")
    evidence_index = build_evidence_index(evidence_files, input_dir)
    for key in evidence_index:
        print(f"  {key}: {len(evidence_index[key])} 条")

    # --- 3. LLM Wiki 理论索引 ---
    print(f"\n[3/8] 建立 LLM Wiki 理论辅助索引...")
    llm_wiki_index = build_llm_wiki_theory_index(input_dir)
    print(f"  理论索引: {len(llm_wiki_index)} 条")

    # --- 4-8. 审计每条 QA ---
    print(f"\n[4-8/8] 审计 QA 对...")
    results = {
        'gold_verified': [],
        'reference_case': [],
        'need_human_review': [],
        'rejected': []
    }
    all_audited = []
    audit_stats = {
        'total': len(all_qa),
        'gold_verified': 0, 'reference_case': 0,
        'need_human_review': 0, 'rejected': 0,
        'missing_report_evidence': 0, 'missing_approval_evidence': 0,
        'missing_standard_evidence': 0,
        'unsupported_claims': 0, 'contradicted_claims': 0,
        'source_missing_count': 0,
        'theory_used_count': 0,
        'rejection_reasons': defaultdict(int),
        'standard_risks': defaultdict(int)
    }

    for idx, qa in enumerate(all_qa):
        qa_id = qa.get('qa_id', qa.get('pair_id', f'qa_{idx:05d}'))
        if (idx + 1) % 100 == 0:
            print(f"  已审计 {idx+1}/{len(all_qa)}...")

        # 检查证据存在性
        has_report = bool(qa.get('report_evidence'))
        has_approval = bool(qa.get('approval_evidence'))
        has_standard = bool(qa.get('standard_evidence'))
        has_evidence_from_file = (qa.get('report_evidence') or qa.get('approval_evidence') or
                                  qa.get('evidence', qa.get('source_evidence', '')))

        if not has_report:
            audit_stats['missing_report_evidence'] += 1
        if not has_approval:
            audit_stats['missing_approval_evidence'] += 1
        if not has_standard:
            audit_stats['missing_standard_evidence'] += 1

        # 拆解 claim
        claims = decompose_claims(qa)

        # 溯源
        traced_claims, missing_sources = trace_claims(claims, evidence_index, llm_wiki_index, qa, input_dir)

        # 统计
        unsup = sum(1 for c in traced_claims if c['support_status'] == 'unsupported')
        cont = sum(1 for c in traced_claims if c['support_status'] == 'contradicted')
        theory_used = sum(1 for c in traced_claims if c['theory_assist']['used'])
        audit_stats['unsupported_claims'] += unsup
        audit_stats['contradicted_claims'] += cont
        audit_stats['theory_used_count'] += theory_used
        audit_stats['source_missing_count'] += len(missing_sources)

        # 审计分级
        audit_status, reject_reason = determine_audit_status(
            traced_claims, qa, missing_sources, has_report, has_approval)

        # 标准版本风险
        answer_text = qa.get('answer', qa.get('reference_answer', qa.get('standard_answer', '')))
        std_risk, std_warning = check_standard_version_risk(answer_text)
        audit_stats['standard_risks'][std_risk] += 1

        # 评分
        score = calculate_score(traced_claims, audit_status, missing_sources)

        # 构建审计结果
        audited = dict(qa)  # 保留原始字段
        audited.update({
            'audit_status': audit_status,
            'source_trace_status': 'complete' if unsup == 0 and cont == 0 and not missing_sources
                                   else 'partial' if unsup <= len(traced_claims) * 0.3
                                   else 'failed',
            'evidence_completeness_score': score,
            'claim_count': len(traced_claims),
            'supported_claim_count': sum(1 for c in traced_claims if c['support_status'] in ('direct_supported', 'indirect_supported')),
            'unsupported_claims': [c['claim'] for c in traced_claims if c['support_status'] == 'unsupported'],
            'contradicted_claims': [c['claim'] for c in traced_claims if c['support_status'] == 'contradicted'],
            'missing_source_files': missing_sources,
            'claim_evidence_alignment': traced_claims,
            'evidence_chain': [{
                'claim': c['claim'],
                'status': c['support_status'],
                'source': c['source_file'],
                'quote': c['exact_quote'][:100]
            } for c in traced_claims],
            'rejection_reason': reject_reason,
            'standard_version_risk': std_risk,
            'human_review_note': std_warning if std_risk == 'outdated' else ''
        })

        audit_stats['rejection_reasons'][audit_status] += 1
        results[audit_status].append(audited)
        all_audited.append(audited)

    # --- 输出文件 ---
    print(f"\n[9/8] 输出审计结果...")
    status_map = {
        'qa_gold_verified.jsonl': 'gold_verified',
        'qa_reference_case.jsonl': 'reference_case',
        'qa_need_human_review.jsonl': 'need_human_review',
        'qa_rejected.jsonl': 'rejected'
    }

    for filename, status in status_map.items():
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            for item in results[status]:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        print(f"  {filename}: {len(results[status])} 条")

    # all audited
    all_path = os.path.join(output_dir, 'qa_all_audited.jsonl')
    with open(all_path, 'w', encoding='utf-8') as f:
        for item in all_audited:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"  qa_all_audited.jsonl: {len(all_audited)} 条")

    # evidence index manifest
    manifest = {
        'generated_at': datetime.now().isoformat(),
        'input_dir': input_dir,
        'qa_files_count': len(qa_files),
        'evidence_files_count': len(evidence_files),
        'qa_total': len(all_qa),
        'index_stats': {k: len(v) for k, v in evidence_index.items()},
        'llm_wiki_theory_index_count': len(llm_wiki_index)
    }
    with open(os.path.join(output_dir, 'evidence_index_manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # llm_wiki_theory_index
    theory_path = os.path.join(output_dir, 'llm_wiki_theory_index.jsonl')
    with open(theory_path, 'w', encoding='utf-8') as f:
        for item in llm_wiki_index:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"  llm_wiki_theory_index.jsonl: {len(llm_wiki_index)} 条")

    # --- 10. 审计报告 ---
    print(f"\n[10/8] 生成审计报告...")
    report = _generate_audit_report(audit_stats, results, input_dir)
    report_path = os.path.join(output_dir, 'audit_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"  audit_report.md 已生成")

    print(f"\n{'='*60}")
    print(f"  审计完成！结果在 {output_dir}")
    print(f"{'='*60}")
    return 0


def _generate_audit_report(stats, results, input_dir):
    """生成审计报告 markdown"""
    total = stats['total']

    report = f"""# 环评 QA 证据链审计报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**输入目录**: `{input_dir}`

---

## 1. 审计概况

| 指标 | 数值 |
|------|:----:|
| 输入文件数 | {stats.get('qa_files_loaded', '—')} |
| QA 总数 | **{total}** |
| gold_verified | **{len(results['gold_verified'])}** ({len(results['gold_verified'])/total*100:.1f}%) |
| reference_case | **{len(results['reference_case'])}** ({len(results['reference_case'])/total*100:.1f}%) |
| need_human_review | **{len(results['need_human_review'])}** ({len(results['need_human_review'])/total*100:.1f}%) |
| rejected | **{len(results['rejected'])}** ({len(results['rejected'])/total*100:.1f}%) |

## 2. 证据缺失统计

| 缺失类型 | 数量 | 占比 |
|---------|:----:|:----:|
| 缺少 report_evidence | {stats['missing_report_evidence']} | {stats['missing_report_evidence']/total*100:.1f}% |
| 缺少 approval_evidence | {stats['missing_approval_evidence']} | {stats['missing_approval_evidence']/total*100:.1f}% |
| 缺少 standard_evidence | {stats['missing_standard_evidence']} | {stats['missing_standard_evidence']/total*100:.1f}% |

## 3. Claim 溯源统计

| 指标 | 数值 |
|------|:----:|
| 未找到原文支持的 claim | **{stats['unsupported_claims']}** |
| 与原文矛盾的 claim | **{stats['contradicted_claims']}** |
| source_missing 标记 | **{stats['source_missing_count']}** |
| 理论索引使用次数 | **{stats['theory_used_count']}** |

## 4. 标准版本风险

| 风险等级 | 数量 |
|---------|:----:|
| none | {stats['standard_risks'].get('none', 0)} |
| outdated | {stats['standard_risks'].get('outdated', 0)} |
| unknown | {stats['standard_risks'].get('unknown', 0)} |
| not_applicable | {stats['standard_risks'].get('not_applicable', 0)} |

## 5. Rejected Top 原因

"""

    # 收集被拒原因
    reject_reasons = defaultdict(int)
    for item in results['rejected']:
        reason = item.get('rejection_reason', '未知')[:80]
        reject_reasons[reason] += 1

    for i, (reason, count) in enumerate(sorted(reject_reasons.items(), key=lambda x: -x[1])[:10]):
        report += f"{i+1}. **{reason}** — {count} 条\n"

    report += """
## 6. 示例展示

### 6.1 Gold Verified 示例（10条）

"""

    for item in results['gold_verified'][:10]:
        qid = item.get('qa_id', item.get('pair_id', 'unknown'))
        score = item.get('evidence_completeness_score', 0)
        q = item.get('question', '')[:80]
        report += f"- **{qid}** (评分:{score}) — {q}...\n"

    report += """
### 6.2 Need Human Review 示例（10条）

"""

    for item in results['need_human_review'][:10]:
        qid = item.get('qa_id', item.get('pair_id', 'unknown'))
        score = item.get('evidence_completeness_score', 0)
        q = item.get('question', '')[:80]
        note = item.get('human_review_note', item.get('rejection_reason', ''))[:50]
        report += f"- **{qid}** (评分:{score}) — {q}... — ⚠️{note}\n"

    report += """
### 6.3 Rejected 示例（10条）

"""

    for item in results['rejected'][:10]:
        qid = item.get('qa_id', item.get('pair_id', 'unknown'))
        reason = item.get('rejection_reason', '未知')[:60]
        report += f"- **{qid}** — ❌ {reason}\n"

    report += """
## 7. 理论索引使用统计

| 使用角色 | 说明 |
|---------|------|
| retrieval_expansion | 检索词扩展，帮助找到更多原文 |
| concept_explanation | 概念解释（辅助人工复核） |
| risk_hint | 风险提示（标准版本、遗漏等） |
| human_review_reference | 人工复核时参考 |

> **⚠️ 注意**: llm_wiki_theory_index 仅供辅助检索和解释用途，不能作为 gold_verified 的证据。

---
*报告由 audit_qa_evidence_chain.py 自动生成*
"""
    return report


if __name__ == '__main__':
    sys.exit(main())
