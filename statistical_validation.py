# -*- coding: utf-8 -*-
"""
Statistical Validation for EIA LLM Evaluation Results
Based on Chen et al. 2026 ES&T SI statistical validation workflow.

Implements: Bootstrap CI, Paired t-test, Wilcoxon signed-rank test, Cohen's d.
"""
import sys, os, json, csv, math, random, time
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'evaluation')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def log(msg):
    print("[%s] %s" % (time.strftime('%H:%M:%S'), msg), flush=True)


def bootstrap_ci(scores, n_bootstrap=10000, confidence=0.95):
    """
    Compute bootstrap confidence interval for a set of scores.

    Args:
        scores: list of numeric scores
        n_bootstrap: number of bootstrap resamples
        confidence: confidence level (default 0.95)

    Returns:
        dict with mean, ci_lower, ci_upper, std_err
    """
    n = len(scores)
    if n < 3:
        return {
            'mean': sum(scores) / max(n, 1),
            'ci_lower': None,
            'ci_upper': None,
            'std_err': None,
            'n': n,
            'warning': '样本量过小(n=%d)，bootstrap结果不可靠，仅供流程演示' % n
        }

    means = []
    for _ in range(n_bootstrap):
        sample = random.choices(scores, k=n)
        means.append(sum(sample) / n)

    means.sort()
    alpha = (1 - confidence) / 2
    lower_idx = int(alpha * n_bootstrap)
    upper_idx = int((1 - alpha) * n_bootstrap)

    return {
        'mean': sum(scores) / n,
        'ci_lower': means[lower_idx],
        'ci_upper': means[upper_idx],
        'std_err': (sum((x - sum(scores)/n)**2 for x in scores) / (n-1))**0.5 / (n**0.5) if n > 1 else None,
        'n': n,
        'bootstrap_samples': n_bootstrap,
        'confidence': confidence
    }


def paired_t_test(scores_a, scores_b):
    """
    Paired t-test for comparing two sets of scores.

    Requires equal length lists (paired observations).

    Args:
        scores_a: list of scores from method A
        scores_b: list of scores from method B

    Returns:
        dict with t_statistic, p_value, mean_diff, interpretation
    """
    n = len(scores_a)
    if n != len(scores_b):
        return {'error': 'Pair sizes must be equal', 'n_a': n, 'n_b': len(scores_b)}
    if n < 3:
        return {
            't_statistic': None,
            'p_value': None,
            'mean_diff': sum(a-b for a,b in zip(scores_a, scores_b)) / n,
            'n': n,
            'warning': '样本量过小(n=%d)，t检验结果不可靠，仅供流程演示' % n
        }

    diffs = [a - b for a, b in zip(scores_a, scores_b)]
    mean_diff = sum(diffs) / n

    # Standard error of differences
    se = (sum((d - mean_diff)**2 for d in diffs) / (n-1))**0.5 / (n**0.5)
    if se == 0:
        return {'t_statistic': 0, 'p_value': 1.0, 'mean_diff': mean_diff, 'n': n, 'note': 'No variance in differences'}

    t_stat = mean_diff / se

    # Approximate p-value using normal distribution (t distribution with df=n-1 for large n)
    # Using simple approximation for demonstration
    from math import exp, pi
    def t_cdf(t, df):
        """Simple t-distribution CDF approximation (for demo purposes)."""
        # Using normal approximation for demo
        z = abs(t)
        # Abramowitz and Stegun approximation
        p = 1 - (1 / (1 + exp(-1.702 * z)))  # Simplified logistic approximation
        # This is a rough demo; real implementation should use scipy.stats.t
        return p

    p_value = 2 * (1 - t_cdf(abs(t_stat), n-1))  # Two-tailed
    p_value = min(max(p_value, 0.001), 1.0)  # Clamp for demo

    interpretation = "无显著差异" if p_value > 0.05 else "存在显著差异"
    if p_value <= 0.01:
        interpretation = "高度显著差异"

    return {
        't_statistic': round(t_stat, 4),
        'p_value': round(p_value, 4),
        'mean_diff': round(mean_diff, 2),
        'n_pairs': n,
        'interpretation': interpretation,
        'significant_at_0.05': p_value <= 0.05
    }


def wilcoxon_test(scores_a, scores_b):
    """
    Wilcoxon signed-rank test (non-parametric, paired).

    More robust than t-test when data is not normally distributed.

    Args:
        scores_a: list of scores from method A
        scores_b: list of scores from method B

    Returns:
        dict with w_statistic, p_value, median_diff, interpretation
    """
    n = len(scores_a)
    if n != len(scores_b):
        return {'error': 'Pair sizes must be equal'}
    if n < 5:
        return {
            'w_statistic': None,
            'p_value': None,
            'median_diff': None,
            'n': n,
            'warning': '样本量过小(n=%d)，Wilcoxon检验无法提供可靠p值，仅供流程演示' % n
        }

    # Compute differences
    diffs = [a - b for a, b in zip(scores_a, scores_b)]
    # Remove zero differences for Wilcoxon
    non_zero = [(i, d) for i, d in enumerate(diffs) if d != 0]

    if not non_zero:
        return {'w_statistic': 0, 'p_value': 1.0, 'median_diff': 0, 'n_pairs': n, 'n_nonzero': 0}

    # Rank the absolute differences
    abs_diffs = [(abs(d), i, d) for i, d in non_zero]
    abs_diffs.sort(key=lambda x: x[0])

    ranks = {}
    j = 0
    while j < len(abs_diffs):
        k = j
        while k < len(abs_diffs) and abs_diffs[k][0] == abs_diffs[j][0]:
            k += 1
        avg_rank = (j + 1 + k) / 2.0
        for m in range(j, k):
            ranks[abs_diffs[m][1]] = avg_rank
        j = k

    # Sum of ranks for positive differences
    w_plus = sum(ranks[i] for i, d in non_zero if d > 0)
    w_minus = sum(ranks[i] for i, d in non_zero if d < 0)
    w_stat = min(w_plus, w_minus)

    # For demo: approximate p-value using normal approximation
    nnz = len(non_zero)
    mean_w = nnz * (nnz + 1) / 4
    std_w = (nnz * (nnz + 1) * (2 * nnz + 1) / 24) ** 0.5
    if std_w > 0:
        z = (w_stat - mean_w) / std_w
        # Two-tailed p-value approximation
        p_value = 2 * (1 / (1 + abs(z)**2.5))  # Rough approximation
        p_value = min(max(p_value, 0.005), 1.0)
    else:
        p_value = 1.0

    sorted_diffs = sorted(diffs)
    mid = len(sorted_diffs) // 2
    median_diff = sorted_diffs[mid] if len(sorted_diffs) % 2 == 1 else (sorted_diffs[mid-1] + sorted_diffs[mid]) / 2

    interpretation = "无显著差异" if p_value > 0.05 else "存在显著差异"

    return {
        'w_statistic': round(w_stat, 2),
        'p_value': round(p_value, 4),
        'median_diff': round(median_diff, 2),
        'n_pairs': n,
        'n_nonzero_diffs': nnz,
        'interpretation': interpretation,
        'significant_at_0.05': p_value <= 0.05
    }


def cohens_d(scores_a, scores_b):
    """
    Cohen's d effect size for paired samples.

    Args:
        scores_a: list of scores from method A
        scores_b: list of scores from method B

    Returns:
        dict with d_value, effect_size_label, mean_diff, pooled_sd
    """
    n = len(scores_a)
    if n != len(scores_b):
        return {'error': 'Pair sizes must be equal'}
    if n < 2:
        return {'d_value': None, 'effect_size_label': '未知', 'warning': '样本量过小'}

    diffs = [a - b for a, b in zip(scores_a, scores_b)]
    mean_diff = sum(diffs) / n

    # Standard deviation of differences
    sd_diff = (sum((d - mean_diff)**2 for d in diffs) / (n-1))**0.5 if n > 1 else 0

    if sd_diff == 0:
        return {'d_value': 0, 'effect_size_label': '无差异', 'mean_diff': mean_diff, 'sd_diff': 0}

    d = mean_diff / sd_diff

    # Interpret Cohen's d
    abs_d = abs(d)
    if abs_d < 0.2:
        label = '可忽略'
    elif abs_d < 0.5:
        label = '小效应'
    elif abs_d < 0.8:
        label = '中等效应'
    else:
        label = '大效应'

    return {
        'd_value': round(d, 4),
        'effect_size_label': label,
        'mean_diff': round(mean_diff, 2),
        'sd_diff': round(sd_diff, 2),
        'n_pairs': n,
        'direction': 'A > B' if mean_diff > 0 else ('A < B' if mean_diff < 0 else '无差异')
    }


def demo_with_sample_data():
    """Run statistical validation demonstration with sample data."""
    log("=" * 60)
    log("Statistical Validation Demo — EIA LLM Judge Scores")
    log("Based on Chen et al. 2026 ES&T SI statistical workflow")
    log("=" * 60)

    # Sample data: simulate two evaluation methods on 5 tasks
    # Method A: Rule-based extraction  (行业规律驱动)
    # Method B: LLM direct extraction  (直接大模型抽取)
    # Generate demo data with small sample sizes (matching our 5 samples)
    task_ids = ['EIA-C2929-L1-001', 'EIA-C2929-L1-002', 'EIA-C2929-L1-003',
                'EIA-C2929-L2-001', 'EIA-C2929-L3-001']

    # Method A (pattern-driven) scores — generally higher for standard tasks
    method_a = [78, 82, 72, 75, 65]
    # Method B (direct LLM) scores — more variable
    method_b = [70, 75, 65, 68, 58]

    log("\nSample data:")
    log("Method A (行业规律驱动): %s" % method_a)
    log("Method B (直接大模型抽取): %s" % method_b)

    # 1. Bootstrap CI for each method
    log("\n--- 1. Bootstrap Confidence Intervals ---")
    ci_a = bootstrap_ci(method_a)
    ci_b = bootstrap_ci(method_b)

    log("Method A: mean=%.1f, 95%% CI [%s, %s]" % (
        ci_a['mean'],
        '%.1f' % ci_a['ci_lower'] if ci_a['ci_lower'] else 'N/A',
        '%.1f' % ci_a['ci_upper'] if ci_a['ci_upper'] else 'N/A'
    ))
    log("Method B: mean=%.1f, 95%% CI [%s, %s]" % (
        ci_b['mean'],
        '%.1f' % ci_b['ci_lower'] if ci_b['ci_lower'] else 'N/A',
        '%.1f' % ci_b['ci_upper'] if ci_b['ci_upper'] else 'N/A'
    ))
    if ci_a.get('warning'):
        log("WARNING: %s" % ci_a['warning'])

    # 2. Paired t-test
    log("\n--- 2. Paired t-test ---")
    t_result = paired_t_test(method_a, method_b)
    log("t=%.4f, p=%.4f, mean_diff=%.2f → %s" % (
        t_result.get('t_statistic', float('nan')),
        t_result.get('p_value', float('nan')),
        t_result.get('mean_diff', 0),
        t_result.get('interpretation', 'N/A')
    ))
    if t_result.get('warning'):
        log("WARNING: %s" % t_result['warning'])

    # 3. Wilcoxon signed-rank test
    log("\n--- 3. Wilcoxon Signed-Rank Test ---")
    w_result = wilcoxon_test(method_a, method_b)
    log("W=%.2f, p=%.4f, median_diff=%.2f → %s" % (
        w_result.get('w_statistic', float('nan')),
        w_result.get('p_value', float('nan')),
        w_result.get('median_diff', 0),
        w_result.get('interpretation', 'N/A')
    ))
    if w_result.get('warning'):
        log("WARNING: %s" % w_result['warning'])

    # 4. Cohen's d
    log("\n--- 4. Cohen's d Effect Size ---")
    d_result = cohens_d(method_a, method_b)
    log("d=%.4f (%s), mean_diff=%.2f, direction=%s" % (
        d_result.get('d_value', float('nan')),
        d_result['effect_size_label'],
        d_result['mean_diff'],
        d_result['direction']
    ))

    # 5. Per-dimension bootstrap CI
    log("\n--- 5. Per-Dimension Analysis ---")
    dims = ['evidence_grounding', 'industry_classification', 'standard_accuracy',
            'pollutant_completeness', 'measure_approval_alignment',
            'actionability', 'hallucination_control']

    # Simulated per-dimension scores from evaluation results
    dim_scores_a = {
        'evidence_grounding': [85, 80, 80, 82, 70],
        'industry_classification': [90, 88, 88, 85, 75],
        'standard_accuracy': [75, 70, 70, 78, 68],
        'pollutant_completeness': [72, 68, 68, 70, 62],
        'measure_approval_alignment': [80, 75, 75, 72, 60],
        'actionability': [75, 70, 70, 72, 68],
        'hallucination_control': [85, 80, 80, 82, 70],
    }

    dim_results = []
    for dim in dims:
        scores = dim_scores_a.get(dim, [])
        ci = bootstrap_ci(scores)
        dim_name_cn = {
            'evidence_grounding': '证据可追溯性',
            'industry_classification': '行业判断准确性',
            'standard_accuracy': '标准引用准确性',
            'pollutant_completeness': '污染因子完整性',
            'measure_approval_alignment': '措施-批复对应性',
            'actionability': '可操作性',
            'hallucination_control': '幻觉控制'
        }.get(dim, dim)

        dim_results.append({
            'dimension': dim,
            'dimension_cn': dim_name_cn,
            'mean': ci['mean'],
            'ci_lower': ci['ci_lower'],
            'ci_upper': ci['ci_upper'],
            'se': ci['std_err']
        })
        log("  %s (%s): mean=%.1f, CI=[%.1f, %.1f]" % (
            dim, dim_name_cn, ci['mean'],
            ci['ci_lower'] if ci['ci_lower'] else float('nan'),
            ci['ci_upper'] if ci['ci_upper'] else float('nan')
        ))

    # ====== SAVE OUTPUTS ======

    # Save CSV
    csv_path = os.path.join(OUTPUT_DIR, 'statistical_validation_demo.csv')
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['test', 'statistic', 'value', 'interpretation'])
        writer.writerow(['Bootstrap CI A', 'mean', round(ci_a['mean'], 1), ''])
        writer.writerow(['Bootstrap CI A', '95% CI', '[%.1f, %.1f]' % (ci_a['ci_lower'] or 0, ci_a['ci_upper'] or 0), ''])
        writer.writerow(['Bootstrap CI B', 'mean', round(ci_b['mean'], 1), ''])
        writer.writerow(['Bootstrap CI B', '95% CI', '[%.1f, %.1f]' % (ci_b['ci_lower'] or 0, ci_b['ci_upper'] or 0), ''])
        writer.writerow(['Paired t-test', 't=%.4f, p=%.4f' % (t_result.get('t_statistic', 0), t_result.get('p_value', 0)), round(t_result.get('mean_diff', 0), 2), t_result.get('interpretation', '')])
        writer.writerow(['Wilcoxon', 'W=%s, p=%s' % (str(w_result.get('w_statistic', '')), str(w_result.get('p_value', ''))), str(w_result.get('median_diff', '')), w_result.get('interpretation', '')])
        writer.writerow(['Cohens d', 'd=%.4f' % d_result.get('d_value', 0), d_result['effect_size_label'], d_result['direction']])
        writer.writerow([])
        writer.writerow(['dimension', 'mean', 'ci_lower', 'ci_upper'])
        for dr in dim_results:
            writer.writerow([dr['dimension_cn'], round(dr['mean'], 1), round(dr['ci_lower'] or 0, 1), round(dr['ci_upper'] or 0, 1)])

    log("\nCSV saved to %s" % csv_path)

    # Save Markdown
    md_path = os.path.join(OUTPUT_DIR, 'statistical_validation_demo.md')
    md_lines = []
    md_lines.append('# EIA审核评估 统计验证演示报告\n')
    md_lines.append('基于 Chen et al. 2026 ES&T SI 统计验证流程\n')
    md_lines.append('生成时间: %s\n\n' % time.strftime('%Y-%m-%d %H:%M'))

    md_lines.append('> **重要提示**: 当前样本数仅为 %d，统计结果仅用于流程演示，不用于正式结论。\n\n' % len(method_a))

    md_lines.append('## 1. Bootstrap 置信区间\n\n')
    md_lines.append('| 方法 | 均值 | 95% CI | SE |\n')
    md_lines.append('|------|------|--------|----|\n')
    md_lines.append('| 行业规律驱动 (A) | %.1f | [%.1f, %.1f] | %.1f |\n' % (
        ci_a['mean'], ci_a['ci_lower'] or 0, ci_a['ci_upper'] or 0, ci_a['std_err'] or 0))
    md_lines.append('| 直接LLM抽取 (B) | %.1f | [%.1f, %.1f] | %.1f |\n\n' % (
        ci_b['mean'], ci_b['ci_lower'] or 0, ci_b['ci_upper'] or 0, ci_b['std_err'] or 0))

    md_lines.append('## 2. 配对检验\n\n')
    md_lines.append('| 检验 | 统计量 | p值 | 效应 | 结论 |\n')
    md_lines.append('|------|--------|-----|------|------|\n')
    md_lines.append('| Paired t-test | t=%.4f | %.4f | 均值差=%.1f | %s |\n' % (
        t_result.get('t_statistic', 0), t_result.get('p_value', 0),
        t_result.get('mean_diff', 0), t_result.get('interpretation', '')))
    md_lines.append('| Wilcoxon | W=%.1f | %.4f | 中位数差=%.1f | %s |\n' % (
        w_result.get('w_statistic', 0), w_result.get('p_value', 0),
        w_result.get('median_diff', 0), w_result.get('interpretation', '')))
    md_lines.append('| Cohen\'s d | d=%.4f | — | %s | %s |\n\n' % (
        d_result.get('d_value', 0), d_result['effect_size_label'], d_result['direction']))

    md_lines.append('## 3. 各维度 Bootstrap CI\n\n')
    md_lines.append('| 维度 | 均值 | 95% CI | SE |\n')
    md_lines.append('|------|------|--------|----|\n')
    for dr in dim_results:
        md_lines.append('| %s | %.1f | [%.1f, %.1f] | %.1f |\n' % (
            dr['dimension_cn'], dr['mean'], dr['ci_lower'] or 0, dr['ci_upper'] or 0, dr['se'] or 0))

    md_lines.append('\n## 4. 论文方法对应\n\n')
    md_lines.append('| 论文 SI 方法 | 本报告对应 | 说明 |\n')
    md_lines.append('|-------------|-----------|------|\n')
    md_lines.append('| Bootstrap CI (10,000 resamples) | Section 1, 3 | 评估分数稳定性 |\n')
    md_lines.append('| Paired t-test | Section 2 | 比较两种方法 |\n')
    md_lines.append('| Wilcoxon signed-rank | Section 2 | 非参数稳健检验 |\n')
    md_lines.append('| Cohen\'s d | Section 2 | 效应大小量化 |\n')
    md_lines.append('| Per-dimension analysis | Section 3 | 分维度诊断 |\n\n')

    md_lines.append('## 5. 后续扩展\n\n')
    md_lines.append('当前样本量（n=%d）太小，正式使用时需满足以下条件：\n\n' % len(method_a))
    md_lines.append('- n ≥ 30: 可使用参数检验 (t-test)\n')
    md_lines.append('- n ≥ 10: 可使用 Bootstrap CI (但区间较宽)\n')
    md_lines.append('- n ≥ 5: 可使用 Wilcoxon (但 p 值不可靠)\n')
    md_lines.append('- n < 5: 只宜描述性统计，不做推断性检验\n\n')
    md_lines.append('---\n\n')
    md_lines.append('*参考: Chen et al. 2026, ES&T, Supporting Information, Statistical Validation*\n')
    md_lines.append('*DOI: 10.1021/acs.est.5c09526*\n')

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(''.join(md_lines))

    log("Markdown saved to %s" % md_path)

    log("\n" + "=" * 60)
    log("Statistical validation demo complete.")
    log("IMPORTANT: Results are for DEMONSTRATION only (n=%d)." % len(method_a))
    log("Real conclusions require n >= 30 samples per method.")
    log("=" * 60)


if __name__ == '__main__':
    demo_with_sample_data()
