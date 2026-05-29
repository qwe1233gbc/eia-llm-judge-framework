# -*- coding: utf-8 -*-
"""
批复文件 ↔ 项目行业 匹配脚本
用批复文件的标题（"关于XX公司...的批复"）匹配 matched_pairs 中的 approval_title，
从而将批复文件关联到行业，再提取审查条件。
"""
import fitz, os, re, json, sys
from collections import defaultdict, Counter
sys.stdout.reconfigure(encoding='utf-8')

PDF_DIR = r"E:\软件\2023-2026年顺德批复文件"
OUT_DIR = r"E:\软件\outputs\approval_review_rules"
os.makedirs(OUT_DIR, exist_ok=True)


def extract_approval_title(text):
    """从批复文件文本中提取"关于...的批复"标题"""
    m = re.search(r'关于[^。]{5,80}的批复', text)
    return m.group(0) if m else None


def extract_review_conditions(section_text):
    """提取第三部分的审查条件"""
    elements_def = {
        '废水': ['废水', '水污染'],
        '废气': ['废气', '大气污染', 'VOCs', '烟尘', '粉尘', '颗粒物'],
        '噪声': ['噪声', '噪音'],
        '固废': ['固废', '固体废物', '一般工业固', '一般固废'],
        '危废': ['危废', '危险废物'],
    }
    conditions = {}
    for elem_name, keywords in elements_def.items():
        if not any(kw in section_text for kw in keywords):
            continue
        sentences = re.split(r'[。；]', section_text)
        related = [s for s in sentences if any(kw in s for kw in keywords)]
        stds = set()
        for s in related:
            found = re.findall(r'[GBDBHJ][A-Z0-9/.-]*-\d{4}', s)
            stds.update(found)
        limits = []
        for s in related:
            for m in re.finditer(
                r'([一-鿿\w]+?)\s*[:：≤≥≈]\s*([\d]+\.?[\d]*)\s*(t/a|mg/m3|mg/Nm3|吨/年|kg/h|dB|dB\(A\)|mg/L)',
                s
            ):
                limits.append({
                    'pollutant': m.group(1),
                    'value': float(m.group(2)),
                    'unit': m.group(3)
                })
        conditions[elem_name] = {
            'standards': list(stds),
            'limits': limits,
        }
    return conditions


def extract_vocs_cap(section4_text):
    """提取VOCs总量"""
    if not section4_text:
        return None
    m = re.search(r'VOCs\s*[排放量]*\s*[为是：:]*\s*([\d]+\.?[\d]*)\s*(t/a|吨/年)', section4_text)
    return float(m.group(1)) if m else None


def parse_sections(text):
    """按一、二、三...拆分章节"""
    sections = {}
    current_num = None
    current_text = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^([一二三四五六七八九十])[、．.]', line)
        if m:
            if current_num:
                sections[current_num] = ''.join(current_text)
            current_num = m.group(1)
            current_text = [line]
        elif current_num:
            current_text.append(line)
    if current_num:
        sections[current_num] = ''.join(current_text)
    return sections


def log(msg):
    print("[%s] %s" % (__import__('time').strftime('%H:%M:%S'), msg), flush=True)


# ============ 主流程 ============

# Step 1: 加载 matched_pairs，建立 title -> industry_code 索引
log("Loading matched pairs...")
with open(r'E:\软件\outputs\eia_pair_commonality\all_matched_pairs.jsonl', 'r', encoding='utf-8') as f:
    pairs = [json.loads(l) for l in f if l.strip()]

# 建立 approval_title -> {industry_code, industry_name, project_id} 的映射
title_to_industry = {}
for p in pairs:
    title = p.get('approval_title', '')
    if title:
        # 标准化：去掉多余空格
        key = re.sub(r'\s+', '', title)
        title_to_industry[key] = {
            'industry_code': p.get('industry_code'),
            'industry_name': p.get('industry_name'),
            'project_id': p.get('project_id'),
        }

log("Loaded %d title mappings" % len(title_to_industry))


# Step 2: 扫描批复文件
log("Scanning approval PDFs...")
files = [f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')]
n = len(files)

matched_results = []
unmatched_titles = []
all_cond_count = 0
matched_count = 0

for i, fname in enumerate(files):
    # 提取文本
    doc = fitz.open(os.path.join(PDF_DIR, fname))
    text = ''
    for page in doc:
        text += page.get_text()
    doc.close()
    if len(text) < 100:
        continue

    # 提取标题
    title = extract_approval_title(text)
    if not title:
        continue

    # 标准化标题用于匹配
    title_key = re.sub(r'\s+', '', title)

    # 尝试匹配
    ind_info = title_to_industry.get(title_key)

    if not ind_info:
        # 尝试部分匹配（去掉文号差异）
        for k, v in title_to_industry.items():
            # 检查项目名称部分是否匹配
            # 提取"关于X的批复"中的核心内容
            core_m = re.search(r'关于(.+?)的批复', title_key)
            core = core_m.group(1) if core_m else ''
            k_core_m = re.search(r'关于(.+?)的批复', k)
            k_core = k_core_m.group(1) if k_core_m else ''
            # 如果项目名核心部分相似度高
            if core and k_core and (core[:10] in k_core or k_core[:10] in core):
                ind_info = v
                break

    # 解析审查条件
    sections = parse_sections(text)
    sec3 = sections.get('三', sections.get('叁', ''))
    sec4 = sections.get('四', sections.get('肆', ''))

    entry = {
        'file': fname,
        'approval_title': title,
        'matched': ind_info is not None,
    }

    if ind_info:
        entry['industry_code'] = ind_info['industry_code']
        entry['industry_name'] = ind_info['industry_name']
        entry['project_id'] = ind_info['project_id']
        matched_count += 1

    if sec3:
        cond = extract_review_conditions(sec3)
        entry['conditions'] = cond
        all_cond_count += 1
    else:
        entry['conditions'] = {}

    vocs = extract_vocs_cap(sec4)
    if vocs:
        entry['vocs_cap'] = vocs

    if ind_info and sec3:
        matched_results.append(entry)

    if (i+1) % 500 == 0:
        log("Progress: %d/%d matched=%d cond=%d" % (i+1, n, matched_count, all_cond_count))

log("Done: total=%d matched=%d cond=%d" % (n, matched_count, all_cond_count))

# Step 3: 按行业归类
log("\n=== 按行业归类 ===")
ind_data = defaultdict(list)
for e in matched_results:
    code = e.get('industry_code')
    if code:
        ind_data[code].append(e)

ind_summary = {}
for code, entries in ind_data.items():
    name = entries[0].get('industry_name', '')
    total = len(entries)
    sc = Counter()
    lc = Counter()
    vlist = []
    for e in entries:
        for ename, cond in e.get('conditions', {}).items():
            for s in cond.get('standards', []):
                sc[s] += 1
            for lim in cond.get('limits', []):
                lc[lim['pollutant'] + ' ' + lim['unit']] += 1
        if e.get('vocs_cap'):
            vlist.append(e['vocs_cap'])

    ind_summary[code] = {
        'industry_name': name,
        'total_approvals': total,
        'approval_files': [e['file'] for e in entries],
        'strong_common_standards': [s for s, c in sc.items() if c/total >= 0.8],
        'general_common_standards': [s for s, c in sc.items() if 0.6 <= c/total < 0.8],
        'all_standards_freq': sc.most_common(),
        'vocs_avg': sum(vlist)/len(vlist) if vlist else None,
        'vocs_range': (min(vlist), max(vlist)) if vlist else None,
    }

    log("  %s %s: %d份批复" % (code, name, total))
    if ind_summary[code]['strong_common_standards']:
        log("    强共性: %s" % ind_summary[code]['strong_common_standards'])
    if ind_summary[code]['general_common_standards']:
        log("    一般共性: %s" % ind_summary[code]['general_common_standards'])

# 保存
with open(os.path.join(OUT_DIR, 'matched_industry_patterns.json'), 'w', encoding='utf-8') as f:
    json.dump(ind_summary, f, ensure_ascii=False, indent=2)

# 生成可读规则库
lines = []
lines.append("# 环评批复文件审查规则库（按行业）\n")
lines.append("---\n")
for code in sorted(ind_summary.keys(), key=lambda c: -ind_summary[c]['total_approvals']):
    d = ind_summary[code]
    lines.append("\n## %s %s（%d份批复）\n" % (code, d['industry_name'], d['total_approvals']))
    if d['strong_common_standards']:
        lines.append("### 强共性标准（>=80%）\n")
        for s in d['strong_common_standards']:
            f = dict(d['all_standards_freq']).get(s, 0)
            lines.append("- **%s**（%d/%d, %.0f%%）" % (s, f, d['total_approvals'], f/d['total_approvals']*100))
        lines.append("")
    if d['general_common_standards']:
        lines.append("### 一般共性标准（60%-80%）\n")
        for s in d['general_common_standards']:
            f = dict(d['all_standards_freq']).get(s, 0)
            lines.append("- %s（%d/%d, %.0f%%）" % (s, f, d['total_approvals'], f/d['total_approvals']*100))
        lines.append("")
    if d['vocs_avg']:
        lines.append("### VOCs总量\n- 平均: %.3f t/a\n- 范围: %.3f ~ %.3f t/a\n" % (
            d['vocs_avg'], d['vocs_range'][0], d['vocs_range'][1]))
    lines.append("### 全部标准频率\n")
    for s, c in d['all_standards_freq'][:10]:
        lines.append("- %s: %d次（%.0f%%）" % (s, c, c/d['total_approvals']*100))
    lines.append("")

with open(os.path.join(OUT_DIR, 'matched_review_rules.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

log("\nSaved:")
log("  1. matched_industry_patterns.json")
log("  2. matched_review_rules.md")
log("  3. 原始数据: all_approval_conditions.json")
