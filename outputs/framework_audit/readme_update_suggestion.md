# README / Docs Update Suggestion

- README_outdated: False
- docs_need_strict_pipeline_notes: False

## Suggested README section

Add or keep a `## Strict Clean-Pairs Pipeline` section that explains:

- The legacy `qa_v3/qa_v4` datasets are historical versions.
- The current mainline uses `data/clean_pairs` as the trusted data entry point.
- `qa_strict_high` is the high-confidence benchmark candidate set.
- `qa_strict_medium` is a manual-review candidate set.
- `qa_strict_review` contains downgraded or unresolved samples.
- `outputs/experience_library_strict` must be generated only from `qa_strict_high`.

## Current audit warning counts

- clean_pair_errors: 0
- qa_high_field_errors: 0
- experience_library_errors: 4
- report_count_mismatch: 0
- README_outdated: 0
- docs_need_strict_pipeline_notes: 0
- script_errors: 0
