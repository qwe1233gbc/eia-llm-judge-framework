# ELLE Dataset Construction Methodology Transfer — Final Summary

**Date**: 2026-05-28
**Task**: Learn ELLE original dataset paper, migrate construction methodology to EIA LLM Judge Framework
**Branch**: `feature/elle-dataset-construction`

---

## 1. Task Recap

The user requested a comprehensive methodology transfer from the ELLE-QA Benchmark paper (Guo et al., 2024, Beijing Information Science & Technology University & Tsinghua University) to the EIA report review domain. ELLE is the first dedicated benchmark dataset for evaluating LLMs in ecological and environmental sciences (1,130 QA pairs, 16 environmental subjects, 3 difficulty levels, 3 question types, 3 evaluation dimensions).

## 2. Files Created

| # | File | Type | Lines | Description |
|---|------|------|-------|-------------|
| 1 | `docs/papers/ELLE_dataset_construction_notes.md` | 文档 | ~209 | 12-section paper analysis: summary, data sources, classification, evaluation dimensions, cross-screening, transferable insights |
| 2 | `docs/eia_benchmark_construction_plan.md` | 文档 | ~261 | 10-section benchmark design: objective, data sources, sample unit, classification, evaluation, evidence, phases |
| 3 | `schemas/eia_benchmark_sample_schema.json` | Schema | ~205 | JSON Schema v0.7 with required fields, regex patterns, enum constraints, maxLength limits |
| 4 | `schemas/eia_benchmark_taxonomy.yaml` | Schema | ~212 | Complete taxonomy: 14 task domains, 3 difficulty levels, 6 question types, 4 evaluation dimensions |
| 5 | `data/sample_eia_benchmark.jsonl` | 数据 | 10 lines | 10 sample entries covering all 6 question types, multiple task domains, all 3 difficulty levels |
| 6 | `scripts/build_eia_benchmark_dataset.py` | 脚本 | ~380 | Builder script skeleton: CLI args, 6 candidate generators, graceful fallback, CSV export for human review |
| 7 | `README.md` | 文档 | Updated | Added ELLE-inspired EIA Benchmark Construction section with usage, taxonomy, phases |
| 8 | `outputs/elle_dataset_transfer/final_summary.md` | 文档 | This file | Final comprehensive summary report |

## 3. Methodology Mapping: ELLE → EIA

### Classification System

| ELLE Component | EIA Counterpart | Notes |
|---------------|-----------------|-------|
| 16 environmental subjects | 14 EIA task domains | Merged overlapping subjects; added EIA-specific domains (report-approval matching, industry pattern induction) |
| Simple/Medium/Hard | Same 3 levels | EIA-specific definitions: single extraction → cross-field matching → multi-source synthesis |
| Knowledge/Calculation/Reasoning | 6 types (extended) | +Extraction, Matching, Evaluation (EIA-specific needs) |
| Professionalism/Clarity/Feasibility | 4 dimensions (extended) | +Evidence Grounding (key differentiator from general QA) |

### Data Sources

| ELLE Source | EIA Counterpart | Status |
|-------------|-----------------|--------|
| Expert questionnaire | Real EIA report-approval pairs (234 projects) | Available |
| Open-source materials (textbooks, exams) | Government approval announcements (8,468 articles) | Available |
| Professional consultations | National/provincial/industry standards library (8,108 codes) | Available |
| N/A | Historical case patterns (multi-industry commonality analysis) | Available (130 triples, 12 rules) |

### Validation Workflow

| ELLE Step | EIA Counterpart | Status |
|-----------|-----------------|--------|
| 3-round expert cross-review | Evidence-based auto-validation + expert fallback | Designed |
| Flag uncertain pairs | `need_human_review: true` flag | Implemented |
| Consensus meetings | Expert panel for ambiguous/disputed cases | Future (Phase 3) |

## 4. Sample Coverage (10 Framework Samples)

| Sample ID | Question Type | Task Domain | Difficulty | Has Evidence? |
|-----------|--------------|-------------|------------|---------------|
| SAMPLE_C2929_KNOWLEDGE_001 | knowledge | 标准引用 | simple | Yes (standard codes) |
| SAMPLE_C2929_EXTRACTION_002 | extraction | 废气 | simple | PLACEHOLDER |
| SAMPLE_C2929_EXTRACTION_003 | extraction | 危废 | simple | PLACEHOLDER |
| SAMPLE_C2929_MATCHING_004 | matching | 报告-批复对应 | medium | PLACEHOLDER |
| SAMPLE_C2929_MATCHING_005 | matching | 标准引用 | medium | Yes (version info) |
| SAMPLE_C2929_REASONING_006 | reasoning | 行业经验归纳 | hard | Expert-dependent |
| SAMPLE_C2929_REASONING_007 | reasoning | 废气 | hard | Expert-dependent |
| SAMPLE_C2929_EVALUATION_008 | evaluation | 废水 | hard | Expert-dependent |
| SAMPLE_C2929_CALCULATION_009 | calculation | 废气/危废 | medium | PLACEHOLDER |
| SAMPLE_C2929_EXTRACTION_010 | extraction | 行业识别 | simple | PLACEHOLDER |

## 5. Key Design Decisions

### What we kept from ELLE
- 3-level difficulty system (Simple/Medium/Hard)
- Expert review workflow (adapted to evidence-based)
- Leaderboard "seasons" concept (future)
- Withhold test set answers for unbiased evaluation

### What we extended
- **Question types**: 3 → 6 (added Extraction, Matching, Evaluation)
- **Evaluation dimensions**: 3 → 4 (added Evidence Grounding at 30% weight)
- **Sample unit**: Simple QA pair → Context-rich sample with source texts and evidence spans
- **Validation**: Expert-only → Evidence-based auto-validation + expert fallback

### What we changed
- **Answer design**: ELLE withholds all answers; we publish evidence-based answers where evidence exists, use PLACEHOLDER markers for expert-dependent ones
- **Difficulty distribution**: ELLE 38% Hard → EIA 25% Hard (reflects real review task distribution)
- **Language**: Bilingual (EN/ZH) → Chinese-only (domestic EIA reports)
- **Data sources**: Expert questionnaire + textbooks → Real reports + approvals + standards (stronger ground truth)

## 6. Data Gaps & Future Work

### Immediate gaps (Phase 2)
- [ ] Replace all `[PLACEHOLDER]` report/approval texts with real MinerU-parsed content
- [ ] Run `build_eia_benchmark_dataset.py` on all 234 project pairs
- [ ] Auto-validate extracted facts against source texts
- [ ] Generate 500+ auto-validated samples

### Expert-dependent gaps (Phase 3)
- [ ] Expert annotation of Hard-level reasoning samples
- [ ] Expert review of auto-generated Medium matching samples
- [ ] Expert adjudication of `need_human_review: true` samples
- [ ] 200+ expert-validated samples

### Infrastructure gaps (Phase 4)
- [ ] Train/dev/test split (60/20/20)
- [ ] Test set answers withheld (ELLE-style)
- [ ] Leaderboard infrastructure
- [ ] Documentation and usage guide

## 7. Builder Script Capabilities

The `build_eia_benchmark_dataset.py` script supports:

```
--industry C2929          Filter by industry code
--difficulty simple       Filter by difficulty level
--question-type extraction  Filter by question type
--task-domain 废气         Filter by task domain (Chinese)
--max-samples 50          Limit output count
--dry-run                 Validate without writing files
--output custom.jsonl     Custom output path
```

It generates 6 types of candidates:
1. **Extraction** (from project_index data)
2. **Matching** (from report-approval pairs)
3. **Knowledge** (from industry codes and standards)
4. **Reasoning** (from multi-industry review rules)
5. **Evaluation** (meta-evaluation scenarios)
6. **Calculation** (emission quantity verification)

All candidates containing PLACEHOLDER text are flagged `need_human_review: true` and exported to a CSV for expert workflow tracking.

## 8. Git Status

```
Branch: feature/elle-dataset-construction
Base: main (detached HEAD → feature branch)

New files (8):
  docs/papers/ELLE_dataset_construction_notes.md
  docs/eia_benchmark_construction_plan.md
  schemas/eia_benchmark_sample_schema.json
  schemas/eia_benchmark_taxonomy.yaml
  data/sample_eia_benchmark.jsonl
  scripts/build_eia_benchmark_dataset.py
  outputs/elle_dataset_transfer/final_summary.md
  README.md (updated)

Commit message:
  "Add ELLE-inspired EIA benchmark construction framework"
```

## 9. Push Status

The `feature/elle-dataset-construction` branch exists locally. To push to GitHub:

```bash
cd E:/软件/eia-llm-judge-framework
git push -u origin feature/elle-dataset-construction
```

If the push fails due to permissions, the user needs to:
1. Verify GitHub PAT token has `repo` scope
2. Or add the user's GitHub account as a collaborator to `qwe1233gbc/eia-llm-judge-framework`
3. The local files are complete and ready — push is the only remaining step

---

*Generated: 2026-05-28 | EIA-LLM-Judge-Framework | ELLE-inspired benchmark migration*
