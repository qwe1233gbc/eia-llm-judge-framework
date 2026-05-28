# -*- coding: utf-8 -*-
"""
EIA Benchmark Dataset Builder
Based on ELLE-QA dataset construction methodology (Guo et al., 2024).
Migrated for EIA report review domain.

Reads project_index, report_facts, and approval_requirements to generate
benchmark candidates in the EIA-Review-Benchmark schema format.

Usage:
    python build_eia_benchmark_dataset.py                          # Generate all candidate types
    python build_eia_benchmark_dataset.py --industry C2929          # Single industry
    python build_eia_benchmark_dataset.py --difficulty simple       # Difficulty filter
    python build_eia_benchmark_dataset.py --question-type extraction  # Question type filter
    python build_eia_benchmark_dataset.py --task-domain 废气         # Task domain filter
    python build_eia_benchmark_dataset.py --max-samples 50          # Limit output
    python build_eia_benchmark_dataset.py --dry-run                 # Validate without writing
"""
import sys, os, json, csv, time, argparse, re
from pathlib import Path
from collections import defaultdict, Counter

sys.stdout.reconfigure(encoding='utf-8')

# ====== CONFIG ======
BASE_DIR = Path(r"E:\软件")
FRAMEWORK_DIR = Path(__file__).resolve().parent.parent  # eia-llm-judge-framework/

# Input paths (may not exist yet — graceful fallback)
PROJECT_INDEX_FILE = BASE_DIR / "outputs" / "eia_industry_pattern" / "project_index.jsonl"
REPORT_FACTS_DIR = BASE_DIR / "outputs" / "eia_pair_commonality"
MATCHED_PAIRS_FILE = REPORT_FACTS_DIR / "all_matched_pairs.jsonl"
APPROVAL_CACHE_FILE = REPORT_FACTS_DIR / "approval_index_cache.json"
REVIEW_RULES_FILE = REPORT_FACTS_DIR / "all_industries_review_rules.json"
TRIPLES_FILE = REPORT_FACTS_DIR / "all_industries_triples.csv"
STANDARDS_SOURCE = BASE_DIR / "data" / "standards_library" / "unique_standards.json"

# Output paths
OUTPUT_DIR = FRAMEWORK_DIR / "data"
SUMMARY_DIR = FRAMEWORK_DIR / "outputs" / "elle_dataset_transfer"
SCHEMA_FILE = FRAMEWORK_DIR / "schemas" / "eia_benchmark_sample_schema.json"
TAXONOMY_FILE = FRAMEWORK_DIR / "schemas" / "eia_benchmark_taxonomy.yaml"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SUMMARY_DIR, exist_ok=True)


def log(msg):
    print("[%s] %s" % (time.strftime('%H:%M:%S'), msg), flush=True)


# ====== DATA LOADING (graceful fallback) ======

def load_jsonl(path):
    """Load JSONL file. Returns [] if file missing or unreadable."""
    if not path.exists():
        log("WARNING: File not found: %s" % path)
        return []
    try:
        records = []
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
    except Exception as e:
        log("WARNING: Failed to load %s: %s" % (path, e))
        return []


def load_json(path):
    """Load JSON file. Returns {} if file missing or unreadable."""
    if not path.exists():
        log("WARNING: File not found: %s" % path)
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log("WARNING: Failed to load %s: %s" % (path, e))
        return {}


def load_schema():
    """Load the benchmark sample schema."""
    return load_json(SCHEMA_FILE)


def load_taxonomy():
    """Load and parse the taxonomy YAML (simple key-value extraction)."""
    if not TAXONOMY_FILE.exists():
        log("WARNING: Taxonomy file not found: %s" % TAXONOMY_FILE)
        return {}
    try:
        taxonomy = {
            "task_domains": [],
            "question_types": [],
            "difficulty_levels": ["simple", "medium", "hard"],
        }
        with open(TAXONOMY_FILE, encoding='utf-8') as f:
            content = f.read()

        # Extract task domain names
        for m in re.finditer(r'name:\s*(.+)', content):
            name = m.group(1).strip()
            if name and name not in taxonomy["task_domains"]:
                taxonomy["task_domains"].append(name)

        # Extract question type names
        for m in re.finditer(r'question_types:.*?\n\s+(\w+):', content, re.DOTALL):
            pass
        # Simpler approach: hardcode from schema
        taxonomy["task_domains"] = [
            "行业识别", "标准引用", "废水", "废气", "噪声", "固废", "危废",
            "环境风险", "排污许可", "总量控制", "竣工环保验收", "重大变动",
            "报告-批复对应", "行业经验归纳"
        ]
        taxonomy["question_types"] = [
            "knowledge", "extraction", "matching", "reasoning", "evaluation", "calculation"
        ]
        return taxonomy
    except Exception as e:
        log("WARNING: Failed to parse taxonomy: %s" % e)
        return {}


# ====== CANDIDATE GENERATORS ======

def _make_sample_id(industry_code, question_type, seq):
    """Generate a sample ID like SAMPLE_C2929_EXTRACTION_001."""
    return "SAMPLE_%s_%s_%03d" % (industry_code, question_type.upper(), seq)


def _default_context(project_id, report_text=None, approval_text=None,
                     standard_text=None, historical_context=None):
    """Build the input_context object with placeholders for missing fields."""
    ctx = {}
    if report_text:
        ctx["report_text"] = report_text[:5000]
    else:
        ctx["report_text"] = "[PLACEHOLDER: %s report text — not yet loaded]" % project_id

    if approval_text:
        ctx["approval_text"] = approval_text[:3000]
    else:
        ctx["approval_text"] = ""

    if standard_text:
        ctx["standard_text"] = standard_text[:2000]
    else:
        ctx["standard_text"] = ""

    if historical_context:
        ctx["historical_case_context"] = historical_context[:3000]
    else:
        ctx["historical_case_context"] = ""

    return ctx


def generate_extraction_candidates(projects, task_domain, seq_start=1):
    """Generate Simple extraction candidates from project data.

    Each project can yield extraction samples for:
    - Basic info (industry code, investment, location)
    - Pollutants (waste gas, wastewater, noise, solid waste, hazardous waste)
    - Standards cited
    - Treatment measures
    """
    candidates = []
    seq = seq_start
    domain_map = {
        "废气": ("waste_gas", "废气"),
        "废水": ("wastewater", "废水"),
        "噪声": ("noise", "噪声"),
        "固废": ("solid_waste", "固废"),
        "危废": ("hazardous_waste", "危废"),
        "标准引用": ("standard_citation", "标准引用"),
        "行业识别": ("industry_identification", "行业识别"),
    }

    for proj in projects:
        industry_code = proj.get("industry_code", "C2929")
        industry_name = proj.get("industry_name", "")
        project_id = proj.get("project_id", "P0001")

        if task_domain and task_domain not in domain_map:
            continue

        domains_to_generate = [task_domain] if task_domain else list(domain_map.keys())

        for domain in domains_to_generate:
            sample = {
                "sample_id": _make_sample_id(industry_code, "extraction", seq),
                "source_project_id": project_id,
                "industry_code": industry_code,
                "industry_name": industry_name,
                "task_domain": domain,
                "difficulty": "simple",
                "question_type": "extraction",
                "question": "[AUTO-GENERATED] Extract %s information from the EIA report for project %s." % (domain, project_id),
                "input_context": _default_context(project_id),
                "reference_answer": "[PLACEHOLDER: auto-extraction pending — run with real report text]",
                "expected_evidence": [{
                    "source_type": "report",
                    "source_file": "[PLACEHOLDER: %s_report.md]" % project_id,
                    "text_span": "[PLACEHOLDER]",
                    "reliability": "direct_match"
                }],
                "evaluation_dimensions": {
                    "professionalism": "Extracted facts must match report text exactly",
                    "clarity": "Output must be structured and well-formatted",
                    "feasibility": "Extracted data usable for downstream audit tasks",
                    "evidence_grounding": "Every extraction must cite report section"
                },
                "need_human_review": True,
                "review_notes": "Auto-generated candidate. Replace PLACEHOLDER text with real report text, verify extraction accuracy.",
                "metadata": {
                    "created_date": time.strftime('%Y-%m-%d'),
                    "created_by": "auto_extraction",
                    "validation_status": "unvalidated",
                    "version": "0.1.0"
                }
            }
            candidates.append(sample)
            seq += 1

    return candidates, seq


def generate_matching_candidates(matched_pairs, seq_start=1):
    """Generate Medium matching candidates from report-approval pairs.

    Each matched pair can yield:
    - Report-approval condition matching
    - Standard applicability checks
    - Pollutant-treatment measure alignment
    """
    candidates = []
    seq = seq_start

    for pair in matched_pairs:
        project_id = pair.get("project_id", "P0001")
        report_name = pair.get("report_name", "")
        approval_title = pair.get("approval_title", "")
        industry_code = pair.get("industry_code", "C2929")
        industry_name = pair.get("industry_name", "")

        # Report-Approval condition matching
        sample = {
            "sample_id": _make_sample_id(industry_code, "matching", seq),
            "source_project_id": project_id,
            "industry_code": industry_code,
            "industry_name": industry_name,
            "task_domain": "报告-批复对应",
            "difficulty": "medium",
            "question_type": "matching",
            "question": "Cross-reference the approval conditions from '%s' with the mitigation measures in the EIA report for '%s'. Identify matched, partially matched, and missing items." % (approval_title[:80], report_name[:80]),
            "input_context": _default_context(
                project_id,
                report_text="[PLACEHOLDER: report text for %s]" % project_id,
                approval_text="[PLACEHOLDER: approval text for %s]" % pair.get("approval_file", "")
            ),
            "reference_answer": "[PLACEHOLDER: matching results pending — run with real report and approval texts]",
            "expected_evidence": [
                {"source_type": "report", "source_file": "[PLACEHOLDER]", "text_span": "[PLACEHOLDER]", "reliability": "direct_match"},
                {"source_type": "approval", "source_file": "[PLACEHOLDER]", "text_span": "[PLACEHOLDER]", "reliability": "direct_match"}
            ],
            "evaluation_dimensions": {
                "professionalism": "Matching judgment must follow EIA review logic",
                "clarity": "Each condition matched/partial/missing clearly labeled",
                "feasibility": "Results directly actionable for report revision requests",
                "evidence_grounding": "Each match status must cite both report and approval text"
            },
            "need_human_review": True,
            "review_notes": "Auto-generated from matched pair. Replace PLACEHOLDER texts with real report and approval documents.",
            "metadata": {
                "created_date": time.strftime('%Y-%m-%d'),
                "created_by": "auto_extraction",
                "validation_status": "unvalidated",
                "version": "0.1.0"
            }
        }
        candidates.append(sample)
        seq += 1

    return candidates, seq


def generate_knowledge_candidates(industry_codes, seq_start=1):
    """Generate Simple knowledge candidates about standards, regulations, and industry classification."""
    candidates = []
    seq = seq_start

    # Standard citation knowledge questions per industry
    for ic in industry_codes:
        sample = {
            "sample_id": _make_sample_id(ic, "knowledge", seq),
            "source_project_id": "P0001",
            "industry_code": ic,
            "industry_name": "[PLACEHOLDER: load from project_index]",
            "task_domain": "标准引用",
            "difficulty": "simple",
            "question_type": "knowledge",
            "question": "List the national, provincial, and industry emission standards typically applicable to industry %s EIA reports. For each standard, specify what pollutants or environmental elements it covers." % ic,
            "input_context": _default_context(
                "P0001",
                standard_text="[PLACEHOLDER: relevant standard clauses for %s]" % ic,
                historical_context="[PLACEHOLDER: industry commonality data for %s from multi-industry analysis]" % ic
            ),
            "reference_answer": "[PLACEHOLDER: compile from standards library and industry commonality analysis]",
            "expected_evidence": [
                {"source_type": "standard", "source_file": "[PLACEHOLDER]", "text_span": "[PLACEHOLDER]", "reliability": "direct_match"}
            ],
            "evaluation_dimensions": {
                "professionalism": "Standard codes and names must be accurate",
                "clarity": "Standards organized by environmental element",
                "feasibility": "Knowledge directly usable for standard citation review",
                "evidence_grounding": "All standards verifiable in standards library"
            },
            "need_human_review": True,
            "review_notes": "Auto-generated knowledge candidate. Verify standard applicability with domain expert.",
            "metadata": {
                "created_date": time.strftime('%Y-%m-%d'),
                "created_by": "auto_extraction",
                "validation_status": "unvalidated",
                "version": "0.1.0"
            }
        }
        candidates.append(sample)
        seq += 1

    return candidates, seq


def generate_reasoning_candidates(industry_codes, review_rules, seq_start=1):
    """Generate Hard reasoning candidates based on multi-industry patterns."""
    candidates = []
    seq = seq_start

    if not review_rules:
        log("No review rules available, skipping reasoning candidates")
        return candidates, seq

    # review_rules is a list of {industry_code, industry_name, rules: [...]}
    rules_by_industry = {}
    for entry in review_rules:
        ic = entry.get("industry_code", "")
        if ic not in rules_by_industry:
            rules_by_industry[ic] = []
        rules_by_industry[ic].extend(entry.get("rules", []))

    for ic in industry_codes:
        rules_for_industry = rules_by_industry.get(ic, [])
        if not rules_for_industry:
            continue

        rule_summary = "; ".join([r.get("check_point", str(r)[:100]) for r in rules_for_industry[:5]])

        sample = {
            "sample_id": _make_sample_id(ic, "reasoning", seq),
            "source_project_id": "P0001",
            "industry_code": ic,
            "industry_name": "[PLACEHOLDER: load from project_index]",
            "task_domain": "行业经验归纳",
            "difficulty": "hard",
            "question_type": "reasoning",
            "question": "Based on review patterns from multiple %s industry projects, identify potential missing review points that a reviewer should check but that are commonly overlooked in EIA reports for this industry. Use the following industry rules as reference: %s" % (ic, rule_summary[:500]),
            "input_context": _default_context(
                "P0001",
                historical_context="Industry review rules for %s: %s" % (ic, json.dumps(rules_for_industry[:5], ensure_ascii=False))
            ),
            "reference_answer": "[PLACEHOLDER_EXPERT_JUDGMENT: requires expert synthesis of industry patterns into actionable review checkpoints]",
            "expected_evidence": [
                {"source_type": "historical_case", "source_file": "all_industries_review_rules.json", "text_span": "[PLACEHOLDER]", "reliability": "expert_judgment"}
            ],
            "evaluation_dimensions": {
                "professionalism": "Reasoning must be grounded in real industry patterns",
                "clarity": "Review checkpoints should be specific and actionable",
                "feasibility": "Identified missing points must be practically checkable in real reviews",
                "evidence_grounding": "Each checkpoint must reference historical case patterns"
            },
            "need_human_review": True,
            "review_notes": "Hard reasoning sample requiring expert synthesis. Review rules from multi-industry analysis provide starting point but require expert interpretation.",
            "metadata": {
                "created_date": time.strftime('%Y-%m-%d'),
                "created_by": "auto_extraction",
                "validation_status": "unvalidated",
                "version": "0.1.0"
            }
        }
        candidates.append(sample)
        seq += 1

    return candidates, seq


def generate_evaluation_candidates(seq_start=1, count=3):
    """Generate Hard evaluation (meta-evaluation) candidates."""
    candidates = []
    seq = seq_start

    eval_scenarios = [
        {
            "domain": "废水",
            "scenario": "AI-generated review comment on wastewater treatment measure adequacy",
        },
        {
            "domain": "废气",
            "scenario": "AI-generated review comment on waste gas emission standard compliance",
        },
        {
            "domain": "危废",
            "scenario": "AI-generated review comment on hazardous waste management completeness",
        },
    ]

    for i, scenario in enumerate(eval_scenarios):
        if i >= count:
            break
        sample = {
            "sample_id": _make_sample_id("C2929", "evaluation", seq),
            "source_project_id": "P0001",
            "industry_code": "C2929",
            "industry_name": "塑料零件及其他塑料制品制造",
            "task_domain": scenario["domain"],
            "difficulty": "hard",
            "question_type": "evaluation",
            "question": "Evaluate the quality of the following AI-generated review comment on %s: [PLACEHOLDER_AI_RESPONSE]. Score on professionalism, clarity, feasibility, and evidence grounding (10-100 each)." % scenario["scenario"],
            "input_context": _default_context(
                "P0001",
                report_text="[PLACEHOLDER: relevant report section]",
                approval_text="[PLACEHOLDER: relevant approval condition]",
                standard_text="[PLACEHOLDER: relevant standard clauses]"
            ),
            "reference_answer": "[PLACEHOLDER_EXPERT_JUDGMENT: requires expert evaluation of AI-generated review comment quality]",
            "expected_evidence": [
                {"source_type": "report", "source_file": "[PLACEHOLDER]", "text_span": "[PLACEHOLDER]", "reliability": "expert_judgment"}
            ],
            "evaluation_dimensions": {
                "professionalism": "Evaluation must correctly identify domain errors in AI response",
                "clarity": "Evaluation breakdown by dimension must be structured",
                "feasibility": "Evaluation must provide actionable feedback for improving AI responses",
                "evidence_grounding": "Score justifications must reference source documents"
            },
            "need_human_review": True,
            "review_notes": "Meta-evaluation sample. Requires: (1) real AI-generated review comment, (2) expert evaluation of that comment, (3) cross-validation with source documents.",
            "metadata": {
                "created_date": time.strftime('%Y-%m-%d'),
                "created_by": "auto_extraction",
                "validation_status": "unvalidated",
                "version": "0.1.0"
            }
        }
        candidates.append(sample)
        seq += 1

    return candidates, seq


def generate_calculation_candidates(projects, seq_start=1, count=3):
    """Generate Medium calculation candidates for emission quantity verification."""
    candidates = []
    seq = seq_start

    calc_types = [
        ("废气", "Verify the SO2 emission quantity calculation: check formula correctness, parameter values, and unit consistency"),
        ("废水", "Verify the COD emission quantity calculation: check if the production scale, discharge coefficient, and concentration values are correctly applied"),
        ("危废", "Calculate the expected hazardous waste (waste activated carbon) generation based on organic waste gas treatment capacity and activated carbon replacement frequency"),
    ]

    for i, (domain, question_template) in enumerate(calc_types):
        if i >= count:
            break
        proj = projects[i] if i < len(projects) else {"project_id": "P0001", "industry_code": "C2929"}
        sample = {
            "sample_id": _make_sample_id(proj.get("industry_code", "C2929"), "calculation", seq),
            "source_project_id": proj.get("project_id", "P0001"),
            "industry_code": proj.get("industry_code", "C2929"),
            "industry_name": proj.get("industry_name", "[PLACEHOLDER]"),
            "task_domain": domain,
            "difficulty": "medium",
            "question_type": "calculation",
            "question": question_template,
            "input_context": _default_context(
                proj.get("project_id", "P0001"),
                report_text="[PLACEHOLDER: emission calculation section from report with formulas and parameters]",
                standard_text="[PLACEHOLDER: relevant calculation methods from technical guidelines (HJ series)]"
            ),
            "reference_answer": "[PLACEHOLDER: calculation result with formula, parameters, assumptions — requires expert verification]",
            "expected_evidence": [
                {"source_type": "report", "source_file": "[PLACEHOLDER]", "text_span": "[PLACEHOLDER: formula and parameter values]", "reliability": "direct_match"},
                {"source_type": "standard", "source_file": "[PLACEHOLDER: HJ technical guideline]", "text_span": "[PLACEHOLDER: calculation method]", "reliability": "direct_match"}
            ],
            "evaluation_dimensions": {
                "professionalism": "Calculation method must follow prescribed technical guidelines",
                "clarity": "Formula, parameters, assumptions, and result must be clearly presented",
                "feasibility": "Calculation result usable for verifying report's own calculations",
                "evidence_grounding": "Formula source and parameter values must be traceable"
            },
            "need_human_review": True,
            "review_notes": "Auto-generated calculation candidate. Replace PLACEHOLDER with real emission data from project report. Requires expert to verify calculation correctness.",
            "metadata": {
                "created_date": time.strftime('%Y-%m-%d'),
                "created_by": "auto_extraction",
                "validation_status": "unvalidated",
                "version": "0.1.0"
            }
        }
        candidates.append(sample)
        seq += 1

    return candidates, seq


# ====== OUTPUT ======

def write_candidates_jsonl(candidates, output_path):
    """Write candidates to JSONL file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for c in candidates:
            f.write(json.dumps(c, ensure_ascii=False) + '\n')
    log("Written %d candidates to %s" % (len(candidates), output_path))


def write_needs_review_csv(candidates, output_path):
    """Write candidates flagged for human review to CSV for expert workflow."""
    review_items = [c for c in candidates if c.get("need_human_review")]

    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "sample_id", "source_project_id", "industry_code", "task_domain",
            "difficulty", "question_type", "review_notes", "validation_status"
        ])
        for item in review_items:
            writer.writerow([
                item["sample_id"],
                item["source_project_id"],
                item.get("industry_code", ""),
                item["task_domain"],
                item["difficulty"],
                item["question_type"],
                item.get("review_notes", ""),
                item.get("metadata", {}).get("validation_status", "unvalidated")
            ])

    log("Written %d review-needed items to %s" % (len(review_items), output_path))


def compute_statistics(candidates):
    """Compute summary statistics for generated candidates."""
    stats = {
        "total_candidates": len(candidates),
        "by_difficulty": Counter(c["difficulty"] for c in candidates),
        "by_question_type": Counter(c["question_type"] for c in candidates),
        "by_task_domain": Counter(c["task_domain"] for c in candidates),
        "by_industry": Counter(c.get("industry_code", "?") for c in candidates),
        "need_human_review": sum(1 for c in candidates if c.get("need_human_review")),
        "by_validation": Counter(c.get("metadata", {}).get("validation_status", "?") for c in candidates),
    }
    return stats


def print_statistics(stats):
    """Print summary statistics."""
    log("\n--- Generation Statistics ---")
    log("Total candidates: %d" % stats["total_candidates"])
    log("Need human review: %d" % stats["need_human_review"])
    log("\nBy difficulty:")
    for diff, count in sorted(stats["by_difficulty"].items()):
        log("  %s: %d" % (diff, count))
    log("\nBy question type:")
    for qtype, count in sorted(stats["by_question_type"].items()):
        log("  %s: %d" % (qtype, count))
    log("\nBy task domain:")
    for domain, count in sorted(stats["by_task_domain"].items()):
        log("  %s: %d" % (domain, count))
    log("\nBy industry:")
    for ic, count in sorted(stats["by_industry"].items()):
        log("  %s: %d" % (ic, count))


# ====== MAIN ======

def main():
    parser = argparse.ArgumentParser(
        description="EIA Benchmark Dataset Builder (ELLE-inspired)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_eia_benchmark_dataset.py
  python build_eia_benchmark_dataset.py --industry C2929 --max-samples 50
  python build_eia_benchmark_dataset.py --difficulty simple --question-type extraction
  python build_eia_benchmark_dataset.py --task-domain 废气 --max-samples 20
  python build_eia_benchmark_dataset.py --dry-run
        """
    )
    parser.add_argument("--industry", type=str, default=None,
                        help="Industry code filter (e.g., C2929, C3360)")
    parser.add_argument("--difficulty", type=str, default=None,
                        choices=["simple", "medium", "hard"],
                        help="Difficulty level filter")
    parser.add_argument("--question-type", type=str, default=None,
                        choices=["knowledge", "extraction", "matching", "reasoning", "evaluation", "calculation"],
                        help="Question type filter")
    parser.add_argument("--task-domain", type=str, default=None,
                        help="Task domain filter (Chinese name, e.g., 废气, 废水, 危废)")
    parser.add_argument("--max-samples", type=int, default=None,
                        help="Maximum number of candidates to generate")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate inputs without writing output files")
    parser.add_argument("--output", type=str, default=None,
                        help="Custom output path for candidates JSONL")

    args = parser.parse_args()

    log("=" * 60)
    log("EIA Benchmark Dataset Builder")
    log("Based on ELLE-QA methodology (Guo et al., 2024)")
    log("=" * 60)

    # Load source data
    log("\n--- Loading Source Data ---")
    projects = load_jsonl(PROJECT_INDEX_FILE)
    matched_pairs = load_jsonl(MATCHED_PAIRS_FILE)
    review_rules = load_json(REVIEW_RULES_FILE)
    schema = load_schema()
    taxonomy = load_taxonomy()

    log("Projects loaded: %d" % len(projects))
    log("Matched pairs loaded: %d" % len(matched_pairs))
    log("Review rules loaded: %s" % ("yes (%d industries)" % len(review_rules) if review_rules else "no"))
    log("Schema loaded: %s" % ("yes" if schema else "no"))
    log("Taxonomy loaded: %s" % ("yes" if taxonomy else "no"))

    # Filter projects by industry
    if args.industry:
        projects = [p for p in projects if p.get("industry_code") == args.industry]
        industry_codes = [args.industry]
        log("Filtered to industry %s: %d projects" % (args.industry, len(projects)))
    else:
        industry_codes_set = set()
        for p in projects:
            ic = p.get("industry_code")
            if ic:
                industry_codes_set.add(ic)
        industry_codes = sorted(industry_codes_set) if industry_codes_set else ["C2929"]
        log("Industries found: %d" % len(industry_codes))

    if not projects and not args.dry_run:
        log("WARNING: No projects loaded. Generating minimal candidates with placeholder data.")
        # Create a minimal placeholder project to enable generation
        projects = [{"project_id": "P0001", "industry_code": "C2929",
                      "industry_name": "塑料零件及其他塑料制品制造"}]

    if not matched_pairs:
        log("WARNING: No matched pairs loaded. Matching candidates will be limited.")

    # Generate candidates by question type
    log("\n--- Generating Candidates ---")
    all_candidates = []

    # Determine which types to generate
    types_to_generate = [args.question_type] if args.question_type else [
        "extraction", "matching", "knowledge", "reasoning", "evaluation", "calculation"
    ]

    seq = 1

    if "extraction" in types_to_generate:
        log("Generating extraction candidates...")
        ext_candidates, seq = generate_extraction_candidates(
            projects, args.task_domain, seq
        )
        all_candidates.extend(ext_candidates)
        log("  Generated %d extraction candidates" % len(ext_candidates))

    if "matching" in types_to_generate:
        log("Generating matching candidates...")
        pairs_to_use = matched_pairs
        if args.industry:
            pairs_to_use = [p for p in pairs_to_use if p.get("industry_code") == args.industry]
        if args.max_samples and len(pairs_to_use) > args.max_samples:
            pairs_to_use = pairs_to_use[:args.max_samples]
        match_candidates, seq = generate_matching_candidates(pairs_to_use, seq)
        all_candidates.extend(match_candidates)
        log("  Generated %d matching candidates" % len(match_candidates))

    if "knowledge" in types_to_generate and not args.task_domain:
        log("Generating knowledge candidates...")
        know_candidates, seq = generate_knowledge_candidates(industry_codes[:10], seq)
        all_candidates.extend(know_candidates)
        log("  Generated %d knowledge candidates" % len(know_candidates))

    if "reasoning" in types_to_generate and not args.task_domain:
        log("Generating reasoning candidates...")
        reason_candidates, seq = generate_reasoning_candidates(industry_codes[:5], review_rules, seq)
        all_candidates.extend(reason_candidates)
        log("  Generated %d reasoning candidates" % len(reason_candidates))

    if "evaluation" in types_to_generate and not args.task_domain:
        log("Generating evaluation candidates...")
        eval_count = 3
        eval_candidates, seq = generate_evaluation_candidates(seq, eval_count)
        all_candidates.extend(eval_candidates)
        log("  Generated %d evaluation candidates" % len(eval_candidates))

    if "calculation" in types_to_generate and not args.task_domain:
        log("Generating calculation candidates...")
        calc_count = 3
        calc_candidates, seq = generate_calculation_candidates(projects[:3], seq, calc_count)
        all_candidates.extend(calc_candidates)
        log("  Generated %d calculation candidates" % len(calc_candidates))

    # Apply difficulty filter
    if args.difficulty:
        all_candidates = [c for c in all_candidates if c["difficulty"] == args.difficulty]
        log("Filtered to difficulty=%s: %d candidates" % (args.difficulty, len(all_candidates)))

    # Apply max samples limit
    if args.max_samples and len(all_candidates) > args.max_samples:
        all_candidates = all_candidates[:args.max_samples]
        log("Limited to %d candidates" % args.max_samples)

    # Compute statistics
    stats = compute_statistics(all_candidates)
    print_statistics(stats)

    # Output
    if args.dry_run:
        log("\n[Dry run] No files written.")
        return

    if not all_candidates:
        log("\nNo candidates generated. Check input data availability.")
        return

    # Write candidates JSONL
    output_jsonl = args.output or (OUTPUT_DIR / "eia_benchmark_candidates.jsonl")
    output_jsonl = Path(output_jsonl)
    write_candidates_jsonl(all_candidates, output_jsonl)

    # Write review-needed CSV
    review_csv = SUMMARY_DIR / "eia_benchmark_needs_review.csv"
    write_needs_review_csv(all_candidates, review_csv)

    # Write generation summary
    summary = {
        "generated_at": time.strftime('%Y-%m-%dT%H:%M:%S'),
        "args": vars(args),
        "statistics": {
            "total_candidates": stats["total_candidates"],
            "by_difficulty": dict(stats["by_difficulty"]),
            "by_question_type": dict(stats["by_question_type"]),
            "by_task_domain": dict(stats["by_task_domain"]),
            "by_industry": dict(stats["by_industry"]),
            "need_human_review": stats["need_human_review"],
        },
        "output_files": {
            "candidates_jsonl": str(output_jsonl),
            "needs_review_csv": str(review_csv),
        }
    }
    summary_path = SUMMARY_DIR / "generation_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    log("Generation summary saved to %s" % summary_path)

    log("\nDone. Next steps:")
    log("  1. Review generated candidates in %s" % output_jsonl)
    log("  2. Replace PLACEHOLDER texts with real report/approval/standard content")
    log("  3. Validate auto-extracted facts against source documents")
    log("  4. Flag samples needing expert review in %s" % review_csv)
    log("  5. Run expert review workflow on flagged samples")
    log("  6. Merge validated samples into final benchmark dataset")


if __name__ == '__main__':
    main()
