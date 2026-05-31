# Framework Consistency Report

This audit reads existing strict pipeline artifacts only. It does not regenerate QA, clean pairs, or experience rules.

## Counts

- clean_pairs: 65
- qa_strict_all: 253
- qa_strict_high: 65
- qa_strict_medium: 48
- qa_strict_review: 140
- experience_rules_all: 30
- A_rules: 4

## Error Counts

- clean_pair_errors: 0
- qa_high_field_errors: 0
- experience_library_errors: 4
- report_count_mismatch: 0
- README_outdated: False

## Key Findings

- `qa_strict_high` passes the implemented field, element, standard, and evidence-location checks.
- `experience_library_strict` has source or A-level rule consistency issues. Do not treat these rules as final until fixed.

## Outputs

See `outputs/framework_audit/*.csv` for row-level details.
