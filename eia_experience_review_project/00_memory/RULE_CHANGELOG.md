# Rule Changelog

## Rule Change 2026-06-10 — Round 3: C2929经验对构建

### New Rules (6 added from Round 2 review findings)

| experience_id | action | evidence_level | source |
|---------------|--------|---------------|--------|
| EXP_C2929_SPATIAL_001 | add | A | round2_finding_F05 |
| EXP_C2929_AIR_002 | add | A | round2_finding_F06 |
| EXP_C2929_MATBAL_001 | add | B | round2_finding_F01 |
| EXP_C2929_PROC_003 | add | A | round2_finding_F02 |
| EXP_C2929_WW_001 | add | B | round2_finding_F08 |
| EXP_C2929_AC_001 | add | A | round2_finding_F03 |

### Converted Rules (15 migrated from existing source_rules)

| experience_id | evidence_level | old_confidence | new_automation |
|---------------|---------------|----------------|----------------|
| EXP_RULE_C2929_噪声_扩建 | A | 0.8 | auto_rule |
| EXP_RULE_C2929_噪声_新建 | A | 0.6 | strong_hint |
| EXP_RULE_C2929_废气_新建 | A | 0.8 | auto_rule |
| EXP_RULE_C2929_废水_扩建 | A | 0.6 | strong_hint |
| EXP_RULE_C2929_废水_新建 | A | 1.0 | auto_rule |
| EXP_RULE_C2929_固废_新建 | B | 0.4 | strong_hint |
| EXP_RULE_C2929_危废_扩建 | C | 0.3 | human_attention |
| EXP_RULE_C2929_危废_新建 | C | 0.3 | human_attention |
| EXP_RULE_C2929_固废_扩建 | C | 0.3 | human_attention |
| EXP_RULE_C2929_废气_扩建 | C | 0.3 | human_attention |
| EXP_RULE_C2929_废气_迁建 | C | 0.1 | human_attention |
| EXP_RULE_C2929_废水_迁建 | C | 0.1 | human_attention |
| EXP_RULE_C2929_总量_扩建 | C | 0.1 | human_attention |
| EXP_RULE_C2929_环境管理_扩建 | C | 0.1 | human_attention |
| EXP_RULE_C2929_环境管理_新建 | C | 0.3 | human_attention |

### Notes
- 15 converted rules had the old `rule_id` format; all migrated with `EXP_` prefix
- C-level rules (confidence < 0.4) marked as `human_attention` — must not auto-judge
- 6 new rules address specific gaps found during Round 2 review of Shengzhiqiang report
- All A-level rules reference verifiable evidence sources
- Automation mapping: A+conf>=0.8 -> auto_rule, A/B -> strong_hint, C -> human_attention
