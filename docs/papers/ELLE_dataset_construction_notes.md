# ELLE Dataset Construction — Study Notes for EIA Benchmark Migration

**Paper**: Guo et al., "Environmental large language model Evaluation (ELLE) dataset: A Benchmark for Evaluating Generative AI applications in Eco-environment Domain"

**Source**: Beijing Information Science & Technology University & Tsinghua University

**Dataset**: ELLE-QA Benchmark — 1,130 QA pairs, 16 environmental subjects, 3 difficulty levels, 3 question types, 3 evaluation dimensions

---

## 1. One-sentence summary

ELLE-QA is the **first dedicated benchmark dataset** for evaluating LLMs in the ecological and environmental sciences, built from expert questionnaires and open-source authoritative materials, with a rigorous 3-round cross-review validation process.

## 2. Why ELLE-QA Benchmark exists

The paper identifies a critical gap: while LLMs show potential for environmental applications (monitoring, data analysis, policy support, education), there is **no unified, reliable evaluation framework** to assess their **professionalism and applicability** in this specialized domain. General benchmarks (SuperCLUE, C-Eval, JioNLP) and even domain-specific ones (OmniEval for finance, BioMistral for biomedicine) do not cover the ecological/environmental sciences.

This directly parallels our EIA review domain: general LLM benchmarks cannot assess whether a model correctly evaluates an environmental impact assessment report, because EIA review requires domain-specific knowledge of industry classification, pollutant standards, treatment measures, and approval regulations.

## 3. ELLE-QA Benchmark goals

| ELLE Goal | EIA Counterpart |
|-----------|----------------|
| Evaluate LLM performance on ecological/environmental tasks | Evaluate LLM performance on EIA report review tasks |
| Standardize AI assessment in the eco-environment domain | Standardize AI assessment for EIA report auditing |
| Provide a unified comparison benchmark | Provide a unified benchmark for EIA review accuracy |
| Bridge the gap between general NLP evaluation and domain needs | Bridge the gap between general LLM evaluation and EIA-specific review needs |

## 4. Data Sources

### ELLE's two data sources:

1. **Expert questionnaire collection** (medium-hard level)
   - Diverse experts: ecology, environmental science, data science, AI, statistics
   - Structured questionnaire via online survey
   - Regular follow-ups and reminders to maintain engagement
   - Planned second round if needed

2. **Manual collection from open-source authoritative materials** (medium difficulty)
   - English and Chinese environmental science textbooks
   - Past examination question sets from environmental science courses and certification exams
   - Professional consultations (queries to environmental departments + expert responses)
   - Bilingual inclusion strategy (English + Chinese materials)

### Migration to EIA domain:

| ELLE Source | EIA Counterpart |
|-------------|----------------|
| Environmental science textbooks | GB/T 4754-2017 industry codebook, EIA technical guidelines (HJ series) |
| Exam questions from certification exams | EIA engineer certification exam questions (注册环评工程师考试) |
| Expert questionnaires | EIA review experts (审批人员, 环评工程师, 环境监测人员) |
| Professional consultations | Real approval decisions from government websites (政府批复文件) |
| — (no historical case equivalent) | **Historical report-approval pairs** (本课题优势: 234 project pairs) |
| — (no evidence tracing equivalent) | **Evidence chains**: report text → extracted fact → standard reference → approval condition |

## 5. Classification / Taxonomy System

### ELLE's classification:
- **16 content domains**: Environmental Geology, Chemistry, Ecology, Mathematics, Toxicology, Physics, Water/Atmospheric/Soil/Biological Environment, Environmental Engineering/Control/Monitoring/Law/Economics/Management/Ethics
- **3 difficulty levels**: Simple, Medium, Hard
- **3 question types**: Knowledge, Calculation, Reasoning

### Migration to EIA domain:

**Content domains → Task Domains**:
```
ELLE: 16 environmental subjects
EIA:  14 EIA review task domains
       - 行业识别 (Industry identification)
       - 标准引用 (Standard citation)
       - 废水 (Wastewater)
       - 废气 (Waste gas)
       - 噪声 (Noise)
       - 固废 (Solid waste)
       - 危废 (Hazardous waste)
       - 环境风险 (Environmental risk)
       - 排污许可 (Discharge permit)
       - 总量控制 (Total emission control)
       - 竣工环保验收 (Completion acceptance)
       - 重大变动 (Major changes)
       - 报告-批复对应 (Report-approval matching)
       - 行业经验归纳 (Industry pattern induction)
```

**Difficulty levels** (same three, domain-specific definitions):
- **Simple**: Single fact extraction (e.g., identify industry code, list standards used, extract pollutant names)
- **Medium**: Cross-field matching (e.g., verify pollutants have matching treatment measures, check approval conditions are addressed in report)
- **Hard**: Comprehensive reasoning (e.g., identify missing review points based on industry patterns, synthesize cross-project rules)

**Question types** (extended from 3 to 6 for EIA needs):
| ELLE Type | EIA Type | Description |
|-----------|----------|-------------|
| Knowledge | Knowledge | Standards, terminology, industry categories, report structure |
| Calculation | Calculation | Emission quantities, hazardous waste volumes, treatment efficiency |
| Reasoning | Reasoning | Multi-evidence synthesis, industry pattern inference, risk assessment |
| — | Extraction | Structured fact extraction from unstructured EIA reports |
| — | Matching | Cross-referencing report content with approval requirements |
| — | Evaluation | Assessing whether model-generated review opinions are reliable |

## 6. Evaluation Dimensions

### ELLE's 3 dimensions:
1. **Professionalism**: Accuracy and domain relevance
2. **Clarity**: Clear, concise, understandable articulation
3. **Feasibility**: Practical applicability in real-world contexts

### ELLE's detailed criteria by question type:

| Dimension | Knowledge | Reasoning | Calculation |
|-----------|-----------|-----------|-------------|
| Accuracy | Aligns with authoritative knowledge | Conclusions align with logical rules | Outcomes accurate, accounts for boundary conditions |
| Logical consistency | Rigorous derivations, clear logic | Step-by-step progression, uses known conditions | Steps complete, efficient methods, well-defined assumptions |
| Normative expression | Precise terminology, concise language | Coherent presentation, clear logic | Standardized math, well-defined variables, clear summary |

### Migration to EIA domain:

Our framework extends ELLE's 3 dimensions into **4 dimensions**, adding evidence traceability:

| EIA Dimension | Definition | Corresponds to |
|---------------|------------|----------------|
| **Professionalism** (专业性) | Industry judgment accuracy, standard citation correctness, pollutant-treatment measure logic | ELLE Professionalism |
| **Clarity** (清晰性) | Structured output, enabling reviewers to quickly locate issues | ELLE Clarity |
| **Feasibility** (可行性) | Review suggestions convertible to actual report modifications | ELLE Feasibility |
| **Evidence Grounding** (证据可追溯性) | Every conclusion traceable to report source, approval document, or standard | **NEW — EIA-specific** |

Evidence grounding is the key addition. Unlike general environmental QA, EIA review recommendations **must** be traceable to source text. A conclusion without evidence is legally and procedurally non-actionable.

## 7. Data Validation / Cross-Screening

### ELLE's process:
1. Initial screening: remove redundant, overly simplistic, or off-topic pairs
2. Categorize by: professional domain, difficulty level, question type
3. Expert panel: 3-round cross-review process
4. Flagging: QA pairs with uncertainty/disagreement flagged for discussion
5. Consensus meetings: in-depth expert discussions to resolve disputes
6. Final retention: only QA pairs meeting highest standards of scientific accuracy and relevance

### Migration to EIA domain:

| ELLE Step | EIA Counterpart |
|-----------|----------------|
| Remove off-topic/redundant | Remove samples with OCR errors, incomplete projects, bad parsing quality |
| Categorize by domain/difficulty/type | Categorize by task domain, difficulty, question type |
| Expert cross-review (3 rounds) | **Cross-validation against evidence**: report text, approval text, standards |
| Flag uncertain pairs | Flag samples as `need_human_review: true` |
| Expert consensus meetings | For samples where report/approval/standard disagree or are ambiguous |
| Retain only highest-quality | Retain samples with complete evidence chains |

Our process replaces expert-only validation with **evidence-based validation**: instead of expert opinion, the primary validation is whether the claim matches the source text (report, approval, or standard). Expert review supplements but does not replace evidence checking.

## 8. ELLE Evaluation Protocol

Key design decisions:
- **Questions published with classifications, answers withheld**: prevents bias during assessment
- **Answers released only after evaluation results published**: enables unbiased assessment
- **Leaderboard system with "seasons"**: periodically updated evaluation results
- **Hybrid scoring**: AI + human expert assessments combined

This "withhold answers" approach is relevant to our EIA benchmark: we should maintain a held-out test set with verified answers for model evaluation, separate from the development set.

## 9. Transferable Insights for EIA Benchmark

| ELLE Feature | Transferable? | Implementation |
|-------------|---------------|----------------|
| Expert questionnaire for QA generation | Yes, but limited | Use existing report-approval pairs as primary source; supplement with expert input |
| Open-source authoritative materials | **Yes — core** | Our "open-source materials" = real EIA reports + approval decisions + national standards |
| Content domain classification | **Yes** | Migrate to 14 EIA task domains |
| 3 difficulty levels | **Yes** | Simple/Medium/Hard with EIA-specific definitions |
| 3 question types | **Yes (extended)** | Knowledge, Calculation, Reasoning + Extraction, Matching, Evaluation |
| 3 evaluation dimensions | **Yes (extended)** | Professionalism, Clarity, Feasibility + Evidence Grounding |
| 3-round expert cross-review | **Partially** | Replace with evidence-based validation; expert review for ambiguous cases |
| Leaderboard seasons | Future | Can adopt once community exists |
| Hybrid AI-human scoring | **Yes** | LLM-as-a-Judge + human expert verification |
| Bilingual strategy | Not needed | Chinese-only for domestic EIA reports |
| 16 environmental subjects | **Migrated** | 14 EIA task domains |

## 10. What NOT to replicate from ELLE

| ELLE Feature | Why Not Replicate |
|-------------|-------------------|
| Pure QA format (question → answer) | EIA review needs **context-rich** samples: report text + approval text + standards as input |
| Expert-only validation | EIA has a stronger ground truth: **real reports and approval decisions** serve as evidence |
| Textbook/exam question sources | EIA review questions should derive from **real review cases**, not synthetic exam questions |
| All-hard emphasis (38% hard) | EIA needs a **wider difficulty spread**: basic fact extraction (Simple) is the most common real-world task |
| Withholding all answers | We can publish **evidence-based** answers where evidence is available; only withhold for expert-only judgments |

## 11. Modules Ready for Immediate Implementation

Based on existing data (234 projects, 84+ industries, 8,468 approval articles):

1. **Task Domain Classification**: Already mapped — 14 EIA domains, ready to use
2. **Simple-level QA generation**: Fact extraction from reports (standards, pollutants, measures) — script-ready
3. **Evidence fields**: Report/approval/standard text spans — schema prepared
4. **Difficulty classification**: Simple/Medium/Hard with EIA definitions — taxonomy ready
5. **Expert review workflow**: `need_human_review` flag — implemented in existing evaluation scripts

## 12. Key References

- ELLE dataset website: https://elle.ceeai.net/
- ELLE GitHub: https://github.com/CEEAI/elle
- SuperCLUE: Xu et al. (2023), Chinese LLM evaluation benchmark
- OmniEval: Wang et al. (2024), Financial RAG evaluation
- BioMistral: Labrak et al. (2024), Biomedical domain LLM evaluation

---

*Generated: 2026-05-28 | For: EIA-LLM-Judge-Framework ELLE-inspired benchmark migration*
