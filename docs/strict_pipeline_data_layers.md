# Strict Pipeline Data Layers

This document describes the current strict clean-pairs pipeline data contract. The older `qa_v3` and `qa_v4` datasets remain in the repository for historical comparison, but the current benchmark construction path is:

```text
MinerU parsed report Markdown
-> approval Markdown
-> data/clean_pairs/
-> data/qa_strict/qa_strict_all.jsonl
-> data/qa_strict/qa_strict_high.jsonl
-> data/qa_strict/qa_strict_medium.jsonl
-> data/qa_strict/qa_strict_review.jsonl
-> outputs/experience_library_strict/
```

## Layer Contract

`data/clean_pairs/` is the trusted entry point. Each `pair_id` directory must contain:

- `report.md`
- `approval.md`
- `pair_metadata.json`

`pair_metadata.json` must identify the company, project name, report source, approval source, and matching basis.

`qa_strict_all.jsonl` is generated only from `data/clean_pairs/`. It must not consume old `qa_v3`, `qa_v4`, or manually matched legacy QA files.

`qa_strict_high.jsonl` is the high-confidence benchmark candidate set. A high QA requires consistent `qa_id`, `element`, `benchmark_metadata.task_domain`, `answer_terms`, standards, approval evidence, and report evidence.

`qa_strict_medium.jsonl` contains samples that may be useful after manual review.

`qa_strict_review.jsonl` contains downgraded or unresolved samples and must not feed the experience library.

`outputs/experience_library_strict/` must be generated only from `qa_strict_high.jsonl`.

## Audit

Run:

```bash
python scripts/strict_pipeline/08_framework_consistency_audit.py
```

The audit writes:

- `outputs/framework_audit/framework_consistency_report.md`
- `outputs/framework_audit/framework_consistency_summary.csv`
- `outputs/framework_audit/qa_strict_high_field_errors.csv`
- `outputs/framework_audit/clean_pair_errors.csv`
- `outputs/framework_audit/experience_library_errors.csv`
- `outputs/framework_audit/readme_update_suggestion.md`
