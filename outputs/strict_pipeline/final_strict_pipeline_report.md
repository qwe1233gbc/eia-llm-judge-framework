# Final Strict Pipeline Report

## 1. Why the old pipeline failed

The old pipeline trusted sequence IDs such as P000x and file-name hints like report/approval. Those IDs were only ordinal labels, so report text, approval text, QA answers, and evidence could come from different projects.

## 2. How this run avoids P000x mismatches

This pipeline classifies files by body text, extracts project/company fields again, performs strict one-to-one record linkage, and generates QA only from `data/clean_pairs/`.

## 3. Counts

1. scanned files: 9194
2. report files: 1365
3. approval files: 4782
4. public_participation files: 58
5. clean_pairs: 65
6. candidate_pairs: 5303
7. unmatched/mismatch sampled: 1000
8. strict QA: 253
9. strict high QA: 65
10. strict medium QA: 48
11. strict review QA: 140
12. strict experience rules from high QA: 30
13. A rules: 4
14. B rules: 5
15. C rules: 21

## 4. High QA Element Distribution

- 噪声: 32
- 废水: 30
- 废气: 2
- 危废: 1

## 5. High QA Project Type Distribution

- 迁扩建: 30
- 扩建: 25
- 改扩建: 8
- 新建: 2

## 6. Downgrade Reason Statistics

- same_standard_alignment_failed: 74
- answer_supported_by_approval_failed: 66
- 危废_qa_contains_forbidden_marker:GB12348: 59
- company_in_approval_failed: 56
- project_name_match_failed: 52
- same_destination_or_measure_failed: 48
- answer_terms_not_current_answer_element: 15
- water_qa_contains_cross_element_standard: 15
- 噪声_qa_contains_forbidden_marker:危险废物: 8
- standards_missing_or_out_of_answer_scope: 4
- 噪声_qa_contains_forbidden_marker:GB18597: 4
- 噪声_qa_contains_forbidden_marker:危废: 4
- approval_element_missing: 2
- answer_not_trimmed_to_element: 1

## 7. Typical High QA Samples

- QA_pair_00001_废水 | 废水 | 迁扩建 | standards: DB44/26-2001 | issues: none | 批复要求：项目生活污水经三 — 2 — 级化粪预处理后达到广东省地方标准《水污染物排放限值》 （DB44/26-2001）第二时段三级标准后排入龙潭安教农村污水处 理设施。
- QA_pair_00001_噪声 | 噪声 | 迁扩建 | standards: GB12348-2008 | issues: none | 批复要求：厂界噪声执行《工业企业厂界环境噪声排放标准》 （GB12348-2008）中的 2 类标准。
- QA_pair_00002_废水 | 废水 | 迁扩建 | standards: DB44/26-2001 | issues: none | 批复要求：1.生活污水经预处理达标后经市政管网排入北滘污水处理 厂处理，排放标准执行广东省《水污染物排放限值》（DB44/26- 2001）的第二时段三级标准。
- QA_pair_00002_噪声 | 噪声 | 迁扩建 | standards: GB12348-2008 | issues: none | 批复要求：3.本项目营运期边界噪声执行《工业企业厂界环境噪声排放 标准》（GB12348-2008）中的 2 类标准。
- QA_pair_00003_废水 | 废水 | 扩建 | standards: DB44/26-2001 | issues: none | 批复要求：（一）项目冷却塔定期排水作为清静下水排至市政雨水管 网，项目生活污水经三级化粪池预处理达到广东省《水污染物排 放限值》（DB 44/26—2001）第二时段三级标准后排入杏坛污水 处理厂处理。

## 8. Typical Downgraded Samples

- QA_pair_00001_废气 | 废气 | 迁扩建 | standards: DB44/815-2010, GB14554-1993, DB44/27-2001, GB31572-2015, DB44/2367-2022, GB41616-2022 | issues: same_standard_alignment_failed | 批复要求：项目 VOCs 排放浓度和速率执行广东省地方标准《印刷行 业挥发性有机化合物排放标准》(DB44/815-2010)排气筒 VOCs 排 放限值中 II 时段柔性板印刷标准和无组织排放监控点浓度限值。臭气浓度执行《恶臭污染物排放标准》（GB 14554-1993） 表 2 恶臭污染物排放标准及表 1 恶臭污染
- QA_pair_00002_废气 | 废气 | 迁扩建 | standards: GB31572-2015, DB44/27-2001 | issues: same_destination_or_measure_failed | 批复要求：2.项目发泡工序产生的非甲烷总烃排放执行《合成树脂工业 污染物排放标准》（GB31572-2015）中表 4 大气污染物排放限值和 表 9 企业边界大气污染物浓度限值。颗粒物执行广东省地方标 准《大气污染物排放限值》（DB44/27-2001）第二时段无组织排放 监控浓度限值。四、项目迁建前 VOCs 总量为
- QA_pair_00003_废气 | 废气 | 扩建 | standards: DB44/2367-2022, GB31572-2015, GB14554-1993, DB44/27-2001 | issues: same_standard_alignment_failed | 批复要求：（二）落实《固定污染源挥发性有机物综合排放标准》（DB 44/2367—2022）中相应控制要求，做好物料储存、转移和输送等 环节挥发性有机物无组织排放控制，并采取有效废气收集处理措 施，最大限度减少废气排放影响。1．项目挤出、检测工序产生废气经双层密闭收集通过沸石 转轮吸附+催化燃烧废气处理后引至 50m
- QA_pair_00004_废水 | 废水 | 扩建 | standards: DB44/26-2001 | issues: same_destination_or_measure_failed | 批复要求：项目生活污水、食 堂废水排放执行广东省地方标准《水污染物排放限值》（DB 44/26 —2001）第二时段三级标准。
- QA_pair_00004_废气 | 废气 | 扩建 | standards: DB44/27-2001, DB44/2367-2022, GB31572-2015, GB14554-1993 | issues: same_standard_alignment_failed | 批复要求：做好物料储存、转移和输送等环节挥 发性有机物无组织排放控制，并采取有效废气收集处理措施，最 大限度减少废气排放影响。项目切割、铣削、钻孔、打磨、焊接 等工序产生粉（烟）尘（颗粒物）排放执行广东省地方标准《大 气污染物排放限值》（DB44/27-2001）第二时段无组织排放监控浓 度限值。喷胶工序产生的胶雾（颗

## 9. Experience Library Recommendation

建议进入经验库生成：仅使用 `qa_strict_high.jsonl`。

## 10. Remaining Manual Review

Candidate pairs and QA outside `qa_strict_high.jsonl` remain outside the experience library and require manual review before use.

## 11. Data Expansion

Add more MinerU parsed reports and authoritative approval PDFs, then rerun this strict pipeline. Prefer more verified pairs over looser matching thresholds.
