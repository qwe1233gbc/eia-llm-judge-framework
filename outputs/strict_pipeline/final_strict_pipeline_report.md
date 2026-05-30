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
9. strict high QA: 44
10. strict medium QA: 107
11. strict review QA: 102
12. strict experience rules from high QA: 22
13. A rules: 4
14. B rules: 5
15. C rules: 13

## 4. Remaining manual review

Candidate pairs and QA outside `qa_strict_high.jsonl` remain outside the experience library and require manual review before use.

## 5. Data expansion

Add more MinerU parsed reports and authoritative approval PDFs, then rerun this strict pipeline. Prefer more verified pairs over looser matching thresholds.
