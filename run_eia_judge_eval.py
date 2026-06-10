# -*- coding: utf-8 -*-
"""
EIA Judge Evaluation Script
Based on Chen et al. 2026 ES&T evaluation workflow.

Reads sample evaluation data, loads judge prompt and schema,
constructs evaluation input, runs evaluation (mock or real API),
outputs structured results and summary.
"""
import sys, os, json, csv, time, re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# ====== CONFIG ======
BASE_DIR = Path(r"E:\软件")
PROMPT_FILE = BASE_DIR / "prompts" / "eia_llm_judge_prompt.md"
SCHEMA_FILE = BASE_DIR / "schemas" / "eia_judge_schema.json"
EVAL_SET_FILE = BASE_DIR / "evaluation" / "sample_eia_eval_set.jsonl"
RESULTS_FILE = BASE_DIR / "evaluation" / "eia_judge_results.jsonl"
SUMMARY_FILE = BASE_DIR / "evaluation" / "eia_judge_summary.csv"

os.makedirs(BASE_DIR / "evaluation", exist_ok=True)


def log(msg):
    print("[%s] %s" % (time.strftime('%H:%M:%S'), msg), flush=True)


def load_prompt():
    """Load the judge evaluation prompt template."""
    if PROMPT_FILE.exists():
        with open(PROMPT_FILE, encoding='utf-8') as f:
            return f.read()
    log("WARNING: Prompt file not found, using minimal fallback")
    return "Evaluate the AI response for EIA review quality. Output JSON."


def load_schema():
    """Load the evaluation output schema."""
    if SCHEMA_FILE.exists():
        with open(SCHEMA_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_samples():
    """Load evaluation samples."""
    samples = []
    with open(EVAL_SET_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def check_api_available():
    """Check if any LLM API is configured."""
    # Check for OpenAI-compatible API
    api_key = os.environ.get('OPENAI_API_KEY', '')
    api_base = os.environ.get('OPENAI_API_BASE', '')
    if api_key:
        return 'openai', {'key': api_key, 'base': api_base}

    # Check for local env file
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        with open(env_file) as f:
            content = f.read()
        key_match = re.search(r'OPENAI_API_KEY\s*=\s*["\']?([^"\'\n]+)["\']?', content)
        if key_match:
            return 'openai', {'key': key_match.group(1).strip()}
        key_match = re.search(r'ANTHROPIC_API_KEY\s*=\s*["\']?([^"\'\n]+)["\']?', content)
        if key_match:
            return 'anthropic', {'key': key_match.group(1).strip()}

    return None, None


def call_llm_api(prompt_text, api_type, api_config):
    """Call real LLM API for evaluation. Reserved for future use."""
    if api_type == 'openai':
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=api_config['key'],
                base_url=api_config.get('base') or 'https://api.openai.com/v1'
            )
            response = client.chat.completions.create(
                model=os.environ.get('EVAL_MODEL', 'gpt-4'),
                messages=[
                    {"role": "user", "content": "[System]\nYou are an expert EIA review evaluator. Output ONLY valid JSON.\n\n" + prompt_text}
                ],
                temperature=0.0,
                max_tokens=4096
            )
            return response.choices[0].message.content
        except ImportError:
            log("openai package not installed, falling back to mock")
            return None
        except Exception as e:
            log("API call failed: %s" % str(e))
            return None
    elif api_type == 'anthropic':
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_config['key'])
            response = client.messages.create(
                model=os.environ.get('EVAL_MODEL', 'claude-sonnet-4-6'),
                max_tokens=4096,
                temperature=0.0,
                system="You are an expert EIA review evaluator. Output ONLY valid JSON.",
                messages=[{"role": "user", "content": prompt_text}]
            )
            return response.content[0].text
        except ImportError:
            log("anthropic package not installed, falling back to mock")
            return None
        except Exception as e:
            log("API call failed: %s" % str(e))
            return None
    return None


def generate_mock_evaluation(sample):
    """Generate a realistic mock evaluation based on sample characteristics.

    This is NOT random - it simulates what a real evaluator would produce
    for demonstration and pipeline testing purposes.
    """
    sample_id = sample['sample_id']
    task_level = sample['task_level']
    difficulty = sample.get('difficulty', 'medium')

    # Base scores differ by task level and difficulty
    base_scores = {
        ('L1_信息抽取', 'easy'):    {'overall': 78, 'evidence': 85, 'industry': 90, 'standard': 75,
                                      'pollutant': 72, 'measure': 80, 'actionability': 75, 'hallucination': 85, 'review_point': 80},
        ('L1_信息抽取', 'medium'):  {'overall': 72, 'evidence': 80, 'industry': 88, 'standard': 70,
                                      'pollutant': 68, 'measure': 75, 'actionability': 70, 'hallucination': 80, 'review_point': 75},
        ('L2_规则匹配', 'medium'):  {'overall': 75, 'evidence': 82, 'industry': 85, 'standard': 78,
                                      'pollutant': 70, 'measure': 72, 'actionability': 72, 'hallucination': 82, 'review_point': 78},
        ('L3_审核推理', 'hard'):    {'overall': 65, 'evidence': 70, 'industry': 75, 'standard': 68,
                                      'pollutant': 62, 'measure': 60, 'actionability': 68, 'hallucination': 70, 'review_point': 65},
    }

    key = (task_level, difficulty)
    scores = base_scores.get(key, base_scores[('L1_信息抽取', 'medium')])

    # L1 easy tasks tend to score higher on industry and evidence
    # L3 hard tasks tend to score lower on measure alignment and completeness

    def score_label(s):
        if s >= 90: return "高度可靠_证据充分"
        if s >= 70: return "基本可靠_少量遗漏"
        if s >= 50: return "部分正确_证据不足"
        if s >= 30: return "严重缺漏_明显错误"
        return "大部分错误_存在幻觉"

    overall = scores['overall']

    dim_scores = {
        "evidence_grounding": scores['evidence'],
        "industry_classification": scores['industry'],
        "standard_accuracy": scores['standard'],
        "pollutant_completeness": scores['pollutant'],
        "measure_approval_alignment": scores['measure'],
        "actionability": scores['actionability'],
        "hallucination_control": scores['hallucination'],
        "review_point_compliance": scores['review_point'],
    }

    # Generate strengths and weaknesses based on dimension scores
    strengths = []
    weaknesses = []

    if scores['industry'] >= 85:
        strengths.append("行业判断准确，代码和名称与报告一致")
    if scores['evidence'] >= 80:
        strengths.append("主要结论有原文证据支撑")
    if scores['hallucination'] >= 80:
        strengths.append("无明显的幻觉或编造内容")
    if scores['standard'] >= 78:
        strengths.append("标准引用基本正确")

    if scores['pollutant'] < 75:
        weaknesses.append("污染因子识别存在遗漏")
    if scores['measure'] < 75:
        weaknesses.append("治理措施描述不够完整或具体")
    if scores['evidence'] < 75:
        weaknesses.append("部分结论缺乏明确的原文证据引用")
    if scores['actionability'] < 75:
        weaknesses.append("审核建议可操作性不足")

    missing_evidence = []
    if scores['evidence'] < 85:
        missing_evidence.append({
            "claim": "部分污染因子识别",
            "expected_source": "报告中污染因子列表原文"
        })

    unsupported = []
    if scores['hallucination'] < 85:
        unsupported.append("可能存在过度推断的治理措施建议")

    need_review = overall < 50 or scores['hallucination'] < 50 or scores['standard'] < 40

    return {
        "sample_id": sample_id,
        "task_type": task_level,
        "overall_score": overall,
        "dimension_scores": dim_scores,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "missing_evidence": missing_evidence,
        "unsupported_claims": unsupported,
        "final_judgment": score_label(overall),
        "need_human_review": need_review,
        "review_priority": "高" if overall < 50 else ("中" if overall < 70 else "低"),
        "evaluator_notes": "[MOCK] 此评估为模拟评分，用于流程验证。实际使用时需替换为LLM API调用。",
        "evaluation_timestamp": time.strftime('%Y-%m-%dT%H:%M:%S'),
        "_mock": True
    }


def evaluate_sample(sample, judge_prompt, api_type, api_config):
    """Evaluate a single sample. Uses mock if no API available."""
    if api_type and api_config:
        # Build evaluation prompt
        prompt_text = f"""{judge_prompt}

---

## EVALUATION TASK

**Sample ID**: {sample['sample_id']}

**Query**: {sample['input'].get('query', 'N/A')}

**AI Response (to be evaluated)**:
{sample.get('reference_answer', 'N/A')}

**Reference Answer**:
{sample.get('reference_answer', 'N/A')}

**Source Evidence**:
Report: {sample['input'].get('report_text', 'N/A')[:2000]}
Approval: {sample['input'].get('approval_text', 'N/A')[:1000]}
Industry Context: {sample['input'].get('industry_context', 'N/A')}
Standard Context: {sample['input'].get('standard_context', 'N/A')}

**Expected Evidence**: {json.dumps(sample.get('expected_evidence', []), ensure_ascii=False)[:500]}

Please evaluate and output JSON.
"""
        result_text = call_llm_api(prompt_text, api_type, api_config)
        if result_text:
            try:
                result = json.loads(result_text)
                result['_mock'] = False
                return result
            except json.JSONDecodeError:
                log("Failed to parse LLM response as JSON, falling back to mock")

    # Fall back to mock
    return generate_mock_evaluation(sample)


def compute_summary(results):
    """Compute summary statistics from evaluation results."""
    summary = {
        'total_samples': len(results),
        'avg_overall_score': sum(r['overall_score'] for r in results) / max(len(results), 1),
        'dimension_averages': {},
        'judgment_distribution': {},
        'human_review_count': sum(1 for r in results if r.get('need_human_review')),
    }

    dims = ['evidence_grounding', 'industry_classification', 'standard_accuracy',
            'pollutant_completeness', 'measure_approval_alignment',
            'actionability', 'hallucination_control', 'review_point_compliance']

    for dim in dims:
        vals = [r['dimension_scores'].get(dim, 0) for r in results]
        summary['dimension_averages'][dim] = round(sum(vals) / max(len(vals), 1), 1)

    for r in results:
        j = r.get('final_judgment', '未知')
        summary['judgment_distribution'][j] = summary['judgment_distribution'].get(j, 0) + 1

    return summary


def main():
    log("=" * 60)
    log("EIA Judge Evaluation Script")
    log("Based on Chen et al. 2026 ES&T evaluation workflow")
    log("=" * 60)

    # Load resources
    judge_prompt = load_prompt()
    schema = load_schema()
    samples = load_samples()
    log("Loaded %d evaluation samples" % len(samples))

    # Check API availability
    api_type, api_config = check_api_available()
    if api_type:
        log("API available: %s (real evaluation mode)" % api_type)
    else:
        log("No API configured, using mock evaluation mode")
        log("To enable real API, set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env or environment")

    # Evaluate each sample
    results = []
    for i, sample in enumerate(samples):
        log("Evaluating %s [%d/%d]..." % (sample['sample_id'], i+1, len(samples)))
        result = evaluate_sample(sample, judge_prompt, api_type, api_config)
        results.append(result)

    # Save results
    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    log("Results saved to %s" % RESULTS_FILE)

    # Compute and save summary
    summary = compute_summary(results)

    with open(SUMMARY_FILE, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['metric', 'value'])
        writer.writerow(['total_samples', summary['total_samples']])
        writer.writerow(['avg_overall_score', round(summary['avg_overall_score'], 1)])
        writer.writerow(['human_review_count', summary['human_review_count']])
        writer.writerow([])
        writer.writerow(['dimension', 'average_score'])
        for dim, avg in summary['dimension_averages'].items():
            writer.writerow([dim, avg])
        writer.writerow([])
        writer.writerow(['judgment', 'count'])
        for judgment, count in summary['judgment_distribution'].items():
            writer.writerow([judgment, count])

    log("Summary saved to %s" % SUMMARY_FILE)

    # Print summary
    log("\n--- Evaluation Summary ---")
    log("Total samples: %d" % summary['total_samples'])
    log("Average overall score: %.1f" % summary['avg_overall_score'])
    log("Samples needing human review: %d" % summary['human_review_count'])
    log("Dimension averages:")
    for dim, avg in summary['dimension_averages'].items():
        log("  %s: %.1f" % (dim, avg))
    log("Judgment distribution:")
    for judgment, count in summary['judgment_distribution'].items():
        log("  %s: %d" % (judgment, count))

    log("\nDone.")


if __name__ == '__main__':
    main()
