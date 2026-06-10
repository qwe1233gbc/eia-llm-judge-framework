# EIA-Review-Benchmark v4 Design

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
