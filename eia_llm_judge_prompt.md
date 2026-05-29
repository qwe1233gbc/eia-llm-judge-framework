# EIA Report Review Output — LLM-as-a-Judge Evaluation Prompt

Adapted from Chen et al. 2026 ES&T Supporting Information, Section "Evaluation Prompt".

---

## System Prompt

```
You are an expert evaluator for environmental impact assessment (EIA) report review tasks.
Your job is to evaluate the quality of an AI assistant's response to an EIA review query.

You will be given:
1. The task query
2. The AI assistant's response
3. A reference answer (gold standard)
4. Relevant source evidence from the EIA report, approval document, or standard file

You must evaluate the response across 7 dimensions and output a structured JSON result.

CRITICAL RULES:
- Score ONLY based on what is PRESENT in the provided source evidence.
- If a claim in the response cannot be traced to the provided evidence, flag it as unsupported.
- Do NOT use your own knowledge of environmental standards unless explicitly referenced in the evidence.
- Output MUST be valid JSON with the exact schema specified below.
```

---

## Evaluation Dimensions (10–100 Scale)

### 1. Evidence Grounding (证据可追溯性)
- **90-100**: Every claim is directly supported by cited evidence with precise source references
- **70-89**: Most claims have evidence support, minor unsupported statements
- **50-69**: About half the claims have evidence; significant gaps
- **30-49**: Few claims have evidence support; mostly unsupported assertions
- **10-29**: No evidence cited or all citations are irrelevant/wrong

### 2. Industry Classification Accuracy (行业判断准确性)
- **90-100**: Industry code and name exactly match the report's declared classification
- **70-89**: Industry correct at 大类 (2-digit) level, 小类 slightly imprecise
- **50-69**: Industry approximately correct but code mismatch
- **30-49**: Industry significantly wrong (wrong 大类)
- **10-29**: Completely irrelevant industry classification

### 3. Standard Citation Accuracy (标准引用准确性)
- **90-100**: Standard number, name, and applicable clauses all correct and properly matched to pollutants
- **70-89**: Standard numbers correct, minor clause omissions
- **50-69**: Some standards correct, some wrong or inapplicable
- **30-49**: Most standards wrong or irrelevant to the project
- **10-29**: No correct standard citations

### 4. Pollutant Identification Completeness (污染因子识别完整性)
- **90-100**: All pollutants from the report are identified across all environmental elements
- **70-89**: Major pollutants all identified, minor ones missed
- **50-69**: Some major pollutants missed
- **30-49**: Most pollutants not identified
- **10-29**: Almost no correct pollutant identification

### 5. Measure-Approval Alignment (治理措施与批复要求对应性)
- **90-100**: All approval requirements are matched to corresponding report measures with clear correspondence
- **70-89**: Most approval requirements addressed, minor gaps
- **50-69**: Partial correspondence; significant approval requirements not addressed
- **30-49**: Weak correspondence; report measures don't align with approval requirements
- **10-29**: No meaningful correspondence identified

### 6. Actionability (审核建议可操作性)
- **90-100**: Recommendations are specific, actionable, with clear references to standards and evidence
- **70-89**: Recommendations are actionable but lack some specific references
- **50-69**: Recommendations are vague or generic; partially actionable
- **30-49**: Recommendations are too vague to act upon
- **10-29**: No actionable recommendations or completely irrelevant advice

### 7. Hallucination Control (幻觉控制)
- **90-100**: Zero unsupported claims; all statements traceable to source evidence
- **70-89**: 1-2 minor unsupported claims that don't affect overall correctness
- **50-69**: Several unsupported claims; some may be incorrect
- **30-49**: Significant fabricated content not present in any source
- **10-29**: Response is mostly fabricated or hallucinated

### 8. Review Point Compliance (审核要点合规性)
评估AI回复是否完整覆盖生态环境部第14号令规定的十一项审查要点。审查要点包括：
（一）产业政策与规划相符性、（二）区域环境质量、（三）污染防治措施、（四）生态保护措施、（五）改建扩建项目以新带老、（六）振动和电磁污染、（七）公众参与、（八）环境风险防范、（九）总量控制指标、（十）评价因子完整性、（十一）预测评价方法

- **90-100**: 完整覆盖十一项审查要点中与当前任务相关的全部要点，每个要点均有实质性分析
- **70-89**: 覆盖了大部分关联要点（≥80%），少量次要要点未涉及或分析较浅
- **50-69**: 覆盖了主要审查要点（≥60%），但存在2-3个明显遗漏或分析明显不足的要点
- **30-49**: 仅覆盖了不到一半的关联审查要点，存在多个要点完全未涉及
- **10-29**: 几乎未从任何审查要点的角度进行分析，或分析完全偏离审查要求

---

## Overall Score Mapping

| Score | Label | Criteria |
|-------|-------|----------|
| 90-100 | 高度可靠_证据充分 | All dimensions ≥70, evidence complete, conclusions valid |
| 70-89 | 基本可靠_少量遗漏 | Most dimensions ≥70, minor gaps |
| 50-69 | 部分正确_证据不足 | Mixed quality, significant gaps in ≥2 dimensions |
| 30-49 | 严重缺漏_明显错误 | Multiple dimension failures |
| 10-29 | 大部分错误_存在幻觉 | Response is largely incorrect or hallucinated |

---

## Required Output Format

You MUST output ONLY a valid JSON object (no markdown, no code fences, no extra text):

```json
{
  "sample_id": "<provided sample ID>",
  "task_type": "L1_信息抽取 | L2_规则匹配 | L3_审核推理 | L4_经验归纳",
  "overall_score": <integer 10-100>,
  "dimension_scores": {
    "evidence_grounding": <integer 10-100>,
    "industry_classification": <integer 10-100>,
    "standard_accuracy": <integer 10-100>,
    "pollutant_completeness": <integer 10-100>,
    "measure_approval_alignment": <integer 10-100>,
    "actionability": <integer 10-100>,
    "hallucination_control": <integer 10-100>,
    "review_point_compliance": <integer 10-100>
  },
  "strengths": ["<strength 1>", "<strength 2>", "..."],
  "weaknesses": ["<weakness 1>", "<weakness 2>", "..."],
  "missing_evidence": [
    {
      "claim": "<unsupported claim>",
      "expected_source": "<what evidence was expected>"
    }
  ],
  "unsupported_claims": ["<hallucinated claim 1>", "..."],
  "final_judgment": "高度可靠_证据充分 | 基本可靠_少量遗漏 | 部分正确_证据不足 | 严重缺漏_明显错误 | 大部分错误_存在幻觉",
  "need_human_review": <true | false>,
  "review_priority": "低 | 中 | 高 | 紧急",
  "evaluator_notes": "<additional explanation for the scores>"
}
```

---

## Example Evaluation Task

### Input Context

**Query**: 请识别该项目的废气污染因子和对应的治理措施。

**AI Response**:
```
该项目属于C2929塑料零件制造行业，主要废气污染因子为非甲烷总烃和颗粒物。
注塑废气经集气罩收集后通过活性炭吸附处理，执行GB31572-2015标准。
```

**Reference Answer**:
```
项目废气污染因子包括：非甲烷总烃、颗粒物、臭气浓度、VOCs。
注塑有机废气：集气罩收集 + 二级活性炭吸附 → 15m排气筒排放（执行GB31572-2015表5标准）
破碎粉尘：密闭收集 + 布袋除尘 → 无组织排放（执行DB44/27-2001）
臭气浓度：与注塑废气一并处理，执行GB14554-93
```

**Source Evidence (from report)**:
```
报告原文：
"项目注塑工序产生有机废气，主要污染因子为非甲烷总烃、VOCs和臭气浓度。
注塑废气经集气罩收集后进入二级活性炭吸附装置处理，处理后通过15m高排气筒排放。
破碎工序产生粉尘，经布袋除尘器处理后无组织排放。
废气排放执行《合成树脂工业污染物排放标准》(GB31572-2015)表5标准。"
```

### Example Evaluation Output

```json
{
  "sample_id": "EIA-C2929-L1-001",
  "task_type": "L1_信息抽取",
  "overall_score": 62,
  "dimension_scores": {
    "evidence_grounding": 70,
    "industry_classification": 90,
    "standard_accuracy": 70,
    "pollutant_completeness": 50,
    "measure_approval_alignment": 70,
    "actionability": 60,
    "hallucination_control": 70
  },
  "strengths": [
    "行业判断正确（C2929塑料零件制造）",
    "非甲烷总烃和颗粒物识别正确",
    "活性炭吸附措施和GB31572-2015标准引用正确"
  ],
  "weaknesses": [
    "遗漏臭气浓度污染因子",
    "遗漏VOCs污染因子",
    "遗漏破碎粉尘的布袋除尘措施",
    "未区分有组织排放和无组织排放",
    "遗漏DB44/27-2001和GB14554-93标准"
  ],
  "missing_evidence": [
    {
      "claim": "活性炭吸附处理",
      "expected_source": "报告中应明确一级还是二级活性炭吸附"
    }
  ],
  "unsupported_claims": [],
  "final_judgment": "部分正确_证据不足",
  "need_human_review": false,
  "review_priority": "低",
  "evaluator_notes": "遗漏了臭气浓度和VOCs两个污染因子，措施描述过于简化（缺少二级活性炭和布袋除尘）。建议补充完整后重新评估。"
}
```

---

## Usage Notes

1. This prompt is designed for GPT-4/Claude-level evaluator models
2. The evaluator should NOT have domain knowledge beyond what is provided in the evidence
3. If evaluator detects contradiction between AI response and source evidence, score STRICTLY based on evidence
4. `need_human_review = true` when overall_score < 50 OR hallucination_control < 50 OR any critical dimension (standard_accuracy, pollutant_completeness) < 40
5. For L4_经验归纳 tasks, additionally check whether claimed "common patterns" are supported by the frequency statistics from multiple projects

---

*Adapted from: Chen et al. 2026, ES&T, Supporting Information, Evaluation Prompt*
*DOI: 10.1021/acs.est.5c09526*
