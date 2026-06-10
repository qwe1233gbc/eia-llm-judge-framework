# Experience Library v2 - Generation Quality Report

## Input Data

- final_verified (A): 62
- demoted (B): 37
- needs_review (C): 272

## Output Rules

| Level | Count | Criteria |
|-------|-------|----------|
| A | 4 | >=3 A-samples, element-std matched, no garbage, specific checkpoints |
| B | 1 | >=3 B-samples, auto-QC passed |
| C | 171 | <3 samples or needs review |
| Total | 176 | |

## Improvements over v1

1. Standard code whitelist: only GB/GB/T/HJ/DB44/DBxx/T with correct format
2. Element-standard compatibility: noise rules no longer contain DB44/GB31572
3. DA001/DA002 exhaust vent IDs filtered out
4. DB44 (bare, no year) filtered out
5. Review checkpoints are element-specific

## Issue Distribution

- 证据等级为C，未通过原文证据审计: 171
- 低可信样本占比过高: 128
- 样本数不足，仅1个项目，不能作为行业稳定规律: 125
- 样本数不足，仅2个项目，不能作为行业稳定规律: 18
- A_level: 4
- B_level: 1
