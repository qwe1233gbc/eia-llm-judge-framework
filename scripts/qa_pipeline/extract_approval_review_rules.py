# -*- coding: utf-8 -*-
"""
批复文件审查规则提取脚本
从批复文件中提取第三部分（环保要求），按行业归类，输出结构化审查规则库。
思路参考：Chen et al. 2026 - textbook knowledge base construction
"""
import fitz, os, re, json, sys
from collections import defaultdict, Counter
sys.stdout.reconfigure(encoding='utf-8')

PDF_DIR = r"E:\软件\2023-2026年顺德批复文件"
OUT_DIR = r"E:\软件\outputs\approval_review_rules"
os.makedirs(OUT_DIR, exist_ok=True)


def extract_approval_text(filepath):
    try:
        doc = fitz.open(filepath)
        text = ''
        for page in doc:
            text += page.get_text()
        doc.close()
        return text if len(text) > 100 else None
    except:
        return None


def parse_sections(text):
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


def parse_review_conditions(section_text):
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
            'text_snippet': ('; '.join(related))[:300],
        }
    return conditions


def extract_company_name(text):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    return lines[0].rstrip('：:')[:60] if lines else ''


# ============ 主处理 ============

def process_all_approvals():
    files = [f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')]
    n = len(files)
    log("Total PDFs: %d" % n)

    results = []
    h_text = 0
    h_cond = 0
    scanned = 0

    for i, fname in enumerate(files):
        text = extract_approval_text(os.path.join(PDF_DIR, fname))
        if not text:
            scanned += 1
            continue
        h_text += 1

        sections = parse_sections(text)
        sec3 = sections.get('三', sections.get('叁', ''))
        sec2 = sections.get('二', sections.get('贰', ''))

        entry = {
            'file': fname,
            'company': extract_company_name(text),
            'project_name': extract_company_name(sec2),
        }
        if sec3:
            cond = parse_review_conditions(sec3)
            if cond:
                entry['conditions'] = cond
                h_cond += 1
            else:
                entry['conditions'] = {}
        else:
            entry['conditions'] = {}

        sec4 = sections.get('四', sections.get('肆', ''))
        if sec4:
            m = re.search(r'VOCs\s*[排放量]*\s*[为是：:]*\s*([\d]+\.?[\d]*)\s*(t/a|吨/年)', sec4)
            if m:
                entry['vocs_cap'] = float(m.group(1))

        results.append(entry)

        if (i+1) % 500 == 0:
            log("Progress: %d/%d text=%d cond=%d" % (i+1, n, h_text, h_cond))

    log("Done: total=%d text=%d scanned=%d cond=%d" % (n, h_text, scanned, h_cond))

    with open(os.path.join(OUT_DIR, 'all_approval_conditions.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log("Saved: all_approval_conditions.json")

    return results


def match_industry(company, project_index):
    best = (None, None, None)
    best_score = 0
    for p in project_index:
        pname = p.get('project_name', '') or ''
        unit = p.get('construction_unit', '') or ''
        parts = [c for c in company[:15] if '一' <= c <= '鿿']
        if len(parts) < 3:
            continue
        key = ''.join(parts[:6])
        if key in pname or key in unit:
            s = max(len(key)/max(len(pname),1), len(key)/max(len(unit),1))
            if s > best_score:
                best_score = s
                best = (p.get('industry_code',''), p.get('industry_name',''), p.get('project_id',''))
    return best


def analyze_by_industry(results):
    with open(r'E:\软件\outputs\eia_industry_pattern\project_index.jsonl', 'r', encoding='utf-8') as f:
        projs = [json.loads(l) for l in f if l.strip()]

    ind_data = defaultdict(list)
    ind_cnt = Counter()

    for e in results:
        if not e.get('conditions'):
            continue
        code, name, pid = match_industry(e.get('company',''), projs)
        if code:
            e['industry_code'] = code
            e['industry_name'] = name
            e['project_id'] = pid
            ind_data[code].append(e)
            ind_cnt[code] += 1

    log("\nMatched by industry:")
    for code, cnt in ind_cnt.most_common(30):
        log("  %s %s: %d" % (code, ind_data[code][0].get('industry_name',''), cnt))

    ind_patterns = {}
    for code, entries in ind_data.items():
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

        total = len(entries)
        ind_patterns[code] = {
            'industry_name': entries[0].get('industry_name', ''),
            'total_approvals': total,
            'strong_common_standards': [s for s, c in sc.items() if c/total >= 0.8],
            'general_common_standards': [s for s, c in sc.items() if 0.6 <= c/total < 0.8],
            'all_standards_freq': sc.most_common(),
            'vocs_avg': sum(vlist)/len(vlist) if vlist else None,
            'vocs_range': (min(vlist), max(vlist)) if vlist else None,
        }

    with open(os.path.join(OUT_DIR, 'industry_review_patterns.json'), 'w', encoding='utf-8') as f:
        json.dump(ind_patterns, f, ensure_ascii=False, indent=2)
    log("Saved: industry_review_patterns.json")
    return ind_patterns


def generate_review_rules(ind_patterns):
    lines = []
    lines.append("# 环评批复文件审查规则库\n")
    lines.append("生成时间: 自动提取\n")
    lines.append("来源: 顺德区生态环境分局批复文件\n")
    lines.append("---\n")

    for code in sorted(ind_patterns.keys()):
        d = ind_patterns[code]
        name = d['industry_name']
        total = d['total_approvals']
        lines.append("\n## %s %s（%d份批复）\n" % (code, name, total))

        if d['strong_common_standards']:
            lines.append("### 强共性标准（出现率≥80%）\n")
            freq_dict = dict(d['all_standards_freq'])
            for s in d['strong_common_standards']:
                f = freq_dict.get(s, 0)
                lines.append("- **%s**（%d/%d, %.0f%%）" % (s, f, total, f/total*100))
            lines.append("")

        if d['general_common_standards']:
            lines.append("### 一般共性标准（60%~80%）\n")
            freq_dict = dict(d['all_standards_freq'])
            for s in d['general_common_standards']:
                f = freq_dict.get(s, 0)
                lines.append("- **%s**（%d/%d, %.0f%%）" % (s, f, total, f/total*100))
            lines.append("")

        if d['vocs_avg']:
            lines.append("### VOCs总量控制\n")
            lines.append("- 平均排放量: %.3f t/a" % d['vocs_avg'])
            lines.append("- 范围: %.3f ~ %.3f t/a" % (d['vocs_range'][0], d['vocs_range'][1]))
            lines.append("")

        lines.append("### 全部引用标准（按频率排序）\n")
        for s, c in d['all_standards_freq'][:15]:
            lines.append("- %s: %d次（%.0f%%）" % (s, c, c/total*100))
        lines.append("")

    text = '\n'.join(lines)
    with open(os.path.join(OUT_DIR, 'review_rules_database.md'), 'w', encoding='utf-8') as f:
        f.write(text)
    log("Saved: review_rules_database.md")


def log(msg):
    print("[%s] %s" % (__import__('time').strftime('%H:%M:%S'), msg), flush=True)


if __name__ == '__main__':
    log("=" * 55)
    log("批复文件审查规则提取")
    log("=" * 55)

    results = process_all_approvals()
    ind_patterns = analyze_by_industry(results)
    generate_review_rules(ind_patterns)

    log("\nAll outputs:")
    log("  1. all_approval_conditions.json - 全部批复条件")
    log("  2. industry_review_patterns.json - 按行业统计分析")
    log("  3. review_rules_database.md - 可读的审查规则库")
