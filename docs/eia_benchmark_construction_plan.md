# EIA-Review-Benchmark: Construction Plan

## Inspired by: ELLE-QA Benchmark (Guo et al., 2024)
## Domain: Environmental Impact Assessment Report Review
## Version: 0.1.0 (framework)

---

## 1. Benchmark Objective

**EIA-Review-Benchmark** (or **EIA-LLM-Judge-Benchmark**) is a domain-specific evaluation dataset designed to:

1. **Assess LLM performance** on environmental impact assessment (EIA) report review tasks
2. **Standardize evaluation** of AI-assisted EIA auditing across industries, environmental elements, and task types
3. **Enable evidence-based comparison** between models by anchoring every sample to traceable source text (report, approval, or standard)
4. **Support both LLM-as-a-Judge** evaluation and direct model output assessment

### Distinction from ELLE-QA

| Aspect | ELLE-QA | EIA-Review-Benchmark |
|--------|---------|---------------------|
| Domain | General ecological/environmental sciences | EIA report review (regulatory compliance) |
| Question source | Expert questionnaire + textbooks/exams | Real EIA reports + approval decisions + national standards |
| Sample unit | QA pair (question → answer) | **Context-rich sample** (source texts → question → answer → evidence spans) |
| Validation | 3-round expert cross-review | Evidence-based validation + expert review for ambiguous cases |
| Key addition | — | **Evidence traceability** (every answer must link to source text) |
| Language | Bilingual (EN/ZH) | Chinese only (domestic EIA reports) |

## 2. Data Sources

### Primary sources (existing)

| Source | Quantity | What it provides |
|--------|----------|-----------------|
| MinerU-parsed EIA reports | 234 projects | Report text, project info, pollution data, standards, measures |
| Government approval announcements | 8,468 articles | Approval decisions, required conditions, approval dates |
| Matched report-approval pairs | 234 pairs | Cross-reference between report promises and approval requirements |
| Industry classification (GB/T 4754-2017) | 82 industries | Industry codes and names for classification tasks |
| National/provincial/industry standards | 8,108 unique codes | Standard references for knowledge and matching tasks |

### Secondary sources (to be developed)

| Source | Purpose |
|--------|---------|
| Expert review annotations | Ground truth for Hard-level reasoning samples |
| Historical audit findings (审批常见退回原因) | Real-world review failure patterns |
| EIA engineer certification exams (环评工程师考试) | Knowledge-type benchmark questions |

### Data source design (ELLE-inspired)

```
ELLE approach:
  Expert questionnaire ──→  Medium-Hard QA pairs
  Textbooks + exams   ──→  Medium Knowledge/Calculation QA pairs
  Professional consultations ──→ Real-world scenario QA pairs

EIA-Review-Benchmark approach:
  EIA reports (MinerU parsed) ──→ Extraction QA pairs (Simple/Medium)
  Approval decisions (government) ──→ Matching QA pairs (Medium)
  Report-Approval pairs ──→ Cross-reference QA pairs (Medium/Hard)
  Industry patterns (cross-project) ──→ Reasoning QA pairs (Hard)
  Standards library ──→ Knowledge QA pairs (Simple/Medium)
  Expert annotations (future) ──→ Evaluation QA pairs (Hard)
```

## 3. Sample Unit Design

Each benchmark sample is a **context-rich unit** containing:

```
┌─────────────────────────────────────────┐
│ sample_id: unique identifier            │
│ source_project_id: link to source data  │
│ industry_code + industry_name           │
│ task_domain: 1 of 14 categories         │
│ difficulty: simple / medium / hard      │
│ question_type: 1 of 6 types             │
│                                         │
│ question: the evaluation prompt         │
│                                         │
│ input_context:                          │
│   ├── report_text (extracted from EIA)  │
│   ├── approval_text (from decision)     │
│   ├── standard_text (relevant clauses)  │
│   └── historical_case_context (industry)│
│                                         │
│ reference_answer: ground truth          │
│                                         │
│ expected_evidence: [                    │
│   {source_type, source_file, text_span} │
│ ]                                       │
│                                         │
│ evaluation_dimensions: {                │
│   professionalism, clarity,             │
│   feasibility, evidence_grounding       │
│ }                                       │
│                                         │
│ need_human_review: bool                 │
│ review_notes: string                    │
└─────────────────────────────────────────┘
```

This is more complex than ELLE's `question → answer` format because EIA review tasks require context: you cannot evaluate a review opinion without seeing the report, approval, and standards it references.

## 4. Sample Classification System

### 4.1 Task domains (14 categories)

| # | Domain | ELLE analogue |
|---|--------|--------------|
| 1 | 行业识别 | Environmental subject classification |
| 2 | 标准引用 | Knowledge — factual accuracy |
| 3 | 废水 | Water Environment |
| 4 | 废气 | Atmospheric Environment |
| 5 | 噪声 | Environmental Engineering |
| 6 | 固废 | Environmental Engineering |
| 7 | 危废 | Environmental Toxicology |
| 8 | 环境风险 | Environmental Control |
| 9 | 排污许可 | Environmental Law |
| 10 | 总量控制 | Environmental Management |
| 11 | 竣工环保验收 | Environmental Management |
| 12 | 重大变动 | Environmental Law |
| 13 | 报告-批复对应 | N/A (EIA-specific) |
| 14 | 行业经验归纳 | Reasoning (EIA-specific) |

### 4.2 Difficulty levels

| Level | EIA definition | ELLE analogue | % target |
|-------|---------------|--------------|----------|
| **Simple** | Single fact extraction from one source section | Simple: basic concepts | 30% |
| **Medium** | Cross-field matching across 2+ sections/documents | Medium: multi-concept integration | 45% |
| **Hard** | Multi-source synthesis with industry knowledge inference | Hard: advanced analysis | 25% |

Note: ELLE has 18.8% Easy / 43.1% Medium / 38.1% Hard. We shift toward more Simple/Medium because:
1. Real EIA review workflows are dominated by fact extraction and cross-checking
2. Hard-level samples require expert annotations (costly, will grow over time)
3. The benchmark should reflect actual review task distribution

### 4.3 Question types

| Type | EIA definition | ELLE analogue |
|------|---------------|--------------|
| **Knowledge** | Standards, terminology, regulatory requirements | Knowledge |
| **Extraction** | Structured fact extraction from report/approval text | N/A (EIA-specific) |
| **Matching** | Cross-referencing report vs. approval requirements | N/A (EIA-specific) |
| **Reasoning** | Multi-evidence synthesis, pattern inference | Reasoning |
| **Evaluation** | Judging quality of AI-generated review opinions | N/A (meta-evaluation) |
| **Calculation** | Emission quantity, treatment efficiency verification | Calculation |

ELLE has 50% Knowledge / 28.8% Reasoning / 7.6% Calculation (with ~13.5% mixed). Our distribution will be:
- Extraction: 30% (most common real task)
- Matching: 25% (core audit workflow)
- Knowledge: 20% (foundational)
- Reasoning: 15% (advanced pattern induction)
- Evaluation: 5% (meta-evaluation)
- Calculation: 5% (quantitative checks)

## 5. Evaluation Dimensions

| Dimension | Weight | Scoring | ELLE Match |
|-----------|--------|---------|------------|
| Professionalism (专业性) | 35% | 10-100 | Professionalism |
| Evidence Grounding (证据可追溯性) | 30% | 10-100 | **NEW** |
| Feasibility (可行性) | 20% | 10-100 | Feasibility |
| Clarity (清晰性) | 15% | 10-100 | Clarity |

Evidence Grounding is weighted higher than in ELLE (where it doesn't exist) because:
- EIA review is a **regulatory compliance task**: recommendations must be actionable
- Without evidence, a review opinion has **zero legal standing**
- This directly supports the thesis methodology: "基于历史审查结果反向归纳" (reverse induction from historical review results)

## 6. Standard Answer Design

Unlike ELLE which withholds answers, our benchmark provides **evidence-anchored answers** where possible:

| Evidence available? | Answer type | Example |
|---------------------|-------------|---------|
| Yes (report text) | Direct extraction with text span | "GB31572-2015" citing Report §3.2 |
| Yes (approval text) | Direct extraction with text span | "VOCs ≤ 60 mg/m³" citing Approval §2 |
| Yes (standard) | Standard clause reference | "GB12348-2008, Class II, 60 dB(A) daytime" |
| No (requires expert) | `need_human_review: true` with placeholder | `[PLACEHOLDER_EXPERT_JUDGMENT]` |

## 7. Evidence Field Design

Each sample's `expected_evidence` is an array of evidence links:

```json
{
  "source_type": "report | approval | standard | historical_case",
  "source_file": "P0001_report.md or 佛环0301环审〔2026〕10号",
  "text_span": "exact text supporting the answer",
  "section": "report section or standard clause number",
  "reliability": "direct_match | inferred | expert_judgment"
}
```

Evidence reliability levels:
- **direct_match**: answer explicitly stated in source (highest confidence)
- **inferred**: answer logically derived from source (medium confidence)
- **expert_judgment**: answer requires expert interpretation (lowest confidence → triggers human review)

## 8. Human Review Workflow

Adapted from ELLE's 3-round expert cross-review:

| ELLE Step | EIA Step |
|-----------|----------|
| Round 1: Independent expert evaluation | **Auto-check**: Does extracted fact match report/approval/standard source text? |
| Round 2: Cross-review by different expert group | **Cross-source verification**: Does the fact appear consistently across report AND approval? |
| Round 3: Flag and discuss disagreements | **Expert review**: If auto-check fails or is ambiguous, flag `need_human_review: true` |
| Consensus meeting | **Expert adjudication**: For disputed samples, expert panel resolves |

Our process is more automated than ELLE's because we have **ground truth in the source documents**. Expert review is the fallback, not the default.

## 9. Construction Phases

### Phase 1: Framework (current) ✓
- [x] Taxonomy and schema design
- [x] Sample data structure
- [x] Builder script skeleton
- [x] 10 illustrative benchmark samples (C2929)
- [ ] No real expert annotations yet

### Phase 2: Automated generation (requires existing data)
- [ ] Run builder script on existing 234 project pairs
- [ ] Generate Simple extraction samples from report data
- [ ] Generate Medium matching samples from report-approval pairs
- [ ] Auto-validate: check extracted facts against source texts
- [ ] Output: 500+ auto-generated and auto-validated samples

### Phase 3: Expert enrichment
- [ ] Expert annotation of Hard-level reasoning samples
- [ ] Expert review of auto-generated Medium samples
- [ ] Expert adjudication of `need_human_review` samples
- [ ] Output: 200+ expert-validated samples

### Phase 4: Benchmark release
- [ ] Split: train (60%) / dev (20%) / test (20%)
- [ ] Publish test set questions (withhold answers initially — ELLE-style)
- [ ] Leaderboard infrastructure
- [ ] Documentation and usage guide

## 10. Mapping to ELLE

| ELLE Component | EIA-Review-Benchmark Implementation | Status |
|---------------|-------------------------------------|--------|
| 16 environmental subjects | 14 EIA task domains | Designed |
| Simple/Medium/Hard difficulty | Same 3 levels, EIA-specific definitions | Designed |
| Knowledge/Calculation/Reasoning | Extended to 6 types (+Extraction, Matching, Evaluation) | Designed |
| Professionalism/Clarity/Feasibility | Same 3 + Evidence Grounding (4 total) | Designed |
| Expert questionnaire | Replaced with report-approval pairs (stronger ground truth) | Available (234 pairs) |
| Open-source materials | Real government approval announcements (8,468 articles) | Available |
| 3-round cross-review | Evidence-based auto-validation + expert fallback | Partially implemented |
| 1,130 QA pairs | Target: 1,000+ benchmark samples | 10 framework samples ready |
| Bilingual strategy | Chinese-only (appropriate for domestic EIA) | N/A |
| Leaderboard seasons | Future (post-Phase 4) | Not started |

---

*Last updated: 2026-05-28*
