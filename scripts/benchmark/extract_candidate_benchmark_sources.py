#!/usr/bin/env python3
"""Extract candidate benchmark sources from Shunde EIA database.

Outputs:
  data/benchmark_exploration/candidate_benchmark_items.jsonl
  data/benchmark_exploration/candidate_projects_for_benchmark.csv
  data/benchmark_exploration/benchmark_exploration_stats.md
"""

import os, json, csv, sys, glob
from collections import Counter

# Paths
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AUDIT_PACKAGES = "E:/openclaw_archive/workspace/agent/workspace/ai_packages_extracted/ai_packages"
CLEAN_PAIRS = os.path.join(BASE, "data", "clean_pairs")
OUT_DIR = os.path.join(BASE, "data", "benchmark_exploration")


def analyze_audit_packages():
    """Step 1: Analyze all audit opinion packages."""
    results = []
    if not os.path.exists(AUDIT_PACKAGES):
        print(f"WARNING: Audit packages dir not found: {AUDIT_PACKAGES}")
        return results

    for d in sorted(os.listdir(AUDIT_PACKAGES)):
        ppath = os.path.join(AUDIT_PACKAGES, d)
        if not os.path.isdir(ppath):
            continue
        mf = os.path.join(ppath, "manifest.json")
        bf = os.path.join(ppath, "body.md")
        cf = os.path.join(ppath, "comments.jsonl")

        if not os.path.exists(mf):
            continue

        with open(mf, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        # Read body for industry detection
        content = ""
        if os.path.exists(bf):
            with open(bf, "r", encoding="utf-8") as f:
                content = f.read(20000)

        # Detect features
        is_c2929 = "C2929" in content or "C2929" in d
        has_injection = "注塑" in content
        has_vocs = any(kw in content for kw in ["VOCs", "非甲烷总烃", "NMHC"])
        has_ac = "活性炭" in content
        has_hw = any(kw in content for kw in ["危废", "危险废物"])
        has_wastewater = any(kw in content for kw in ["废水", "生活污水", "冷却水"])

        # Count comments
        comment_count = manifest.get("comment_count", 0)
        comments = []
        if os.path.exists(cf) and comment_count > 0:
            with open(cf, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        comments.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

        result = {
            "doc_id": d,
            "doc_path": ppath,
            "comment_count": comment_count,
            "table_count": manifest.get("table_count", 0),
            "figure_count": manifest.get("figure_count", 0),
            "is_c2929": is_c2929,
            "has_injection_molding": has_injection,
            "has_vocs": has_vocs,
            "has_activated_carbon": has_ac,
            "has_hazardous_waste": has_hw,
            "has_wastewater": has_wastewater,
            "comments": comments,
            "content_preview": content[:500],
        }

        # Determine benchmark value
        if is_c2929 and has_vocs and has_ac and comment_count >= 10:
            result["benchmark_potential"] = "high"
            result["recommended_use"] = "real_error_benchmark"
        elif (has_vocs or has_ac) and comment_count >= 5:
            result["benchmark_potential"] = "medium"
            result["recommended_use"] = "real_error_benchmark"
        elif comment_count >= 3:
            result["benchmark_potential"] = "low"
            result["recommended_use"] = "experience_rule_source"
        else:
            result["benchmark_potential"] = "low"
            result["recommended_use"] = "metadata_only"

        results.append(result)

    return results


def analyze_clean_pairs():
    """Step 2: Analyze clean report-approval pairs."""
    results = []
    if not os.path.exists(CLEAN_PAIRS):
        return results

    for pd in sorted(os.listdir(CLEAN_PAIRS)):
        pp = os.path.join(CLEAN_PAIRS, pd)
        if not os.path.isdir(pp):
            continue
        mf = os.path.join(pp, "pair_metadata.json")
        if not os.path.exists(mf):
            continue

        with open(mf, "r", encoding="utf-8") as f:
            meta = json.load(f)

        has_report = os.path.exists(os.path.join(pp, "report.md"))
        has_approval = os.path.exists(os.path.join(pp, "approval.md"))

        results.append({
            "pair_id": pd,
            "project_name": meta.get("project_name", ""),
            "company": meta.get("company", ""),
            "match_score": meta.get("match_score", 0),
            "has_report": has_report,
            "has_approval": has_approval,
            "approval_date": meta.get("approval_date", ""),
            "pair_path": pp,
        })

    return results


def generate_stats(audit_results, pair_results):
    """Step 3: Generate statistics."""
    stats = {
        "total_audit_packages": len(audit_results),
        "total_comments": sum(r["comment_count"] for r in audit_results),
        "total_clean_pairs": len(pair_results),
        "complete_pairs": sum(1 for r in pair_results if r["has_report"] and r["has_approval"]),
        "c2929_projects": sum(1 for r in audit_results if r["is_c2929"]),
        "injection_projects": sum(1 for r in audit_results if r["has_injection_molding"]),
        "vocs_projects": sum(1 for r in audit_results if r["has_vocs"]),
        "ac_projects": sum(1 for r in audit_results if r["has_activated_carbon"]),
        "hw_projects": sum(1 for r in audit_results if r["has_hazardous_waste"]),
        "high_potential": sum(1 for r in audit_results if r["benchmark_potential"] == "high"),
        "medium_potential": sum(1 for r in audit_results if r["benchmark_potential"] == "medium"),
        "real_error_candidates": sum(
            1 for r in audit_results if "real_error" in r.get("recommended_use", "")
        ),
    }
    return stats


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=== Step 1: Analyzing audit packages ===")
    audit_results = analyze_audit_packages()
    print(f"  Found {len(audit_results)} audit packages")

    print("=== Step 2: Analyzing clean pairs ===")
    pair_results = analyze_clean_pairs()
    print(f"  Found {len(pair_results)} clean pairs")

    print("=== Step 3: Generating statistics ===")
    stats = generate_stats(audit_results, pair_results)

    # Save candidate items JSONL
    items_path = os.path.join(OUT_DIR, "candidate_benchmark_items.jsonl")
    with open(items_path, "w", encoding="utf-8") as f:
        for r in audit_results:
            item = {
                "candidate_id": f'CAND_{r["doc_id"][:20]}',
                "project_id": r["doc_id"][:40],
                "project_name": r["doc_id"],
                "industry_code": "C2929" if r["is_c2929"] else "UNKNOWN",
                "town": "顺德区",
                "source_type": "real_error",
                "benchmark_potential": r["benchmark_potential"],
                "comment_count": r["comment_count"],
                "features": {
                    "injection": r["has_injection_molding"],
                    "vocs": r["has_vocs"],
                    "activated_carbon": r["has_activated_carbon"],
                    "hazardous_waste": r["has_hazardous_waste"],
                },
            }
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"  Saved: {items_path}")

    # Save CSV
    csv_path = os.path.join(OUT_DIR, "candidate_projects_for_benchmark.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = [
            "project_id", "project_name", "company_name", "town",
            "industry_code", "benchmark_potential", "recommended_use",
            "comment_count", "has_injection_molding", "has_vocs",
            "has_activated_carbon", "has_hazardous_waste",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in audit_results:
            writer.writerow({
                "project_id": r["doc_id"][:40],
                "project_name": r["doc_id"],
                "company_name": "",
                "town": "顺德区",
                "industry_code": "C2929" if r["is_c2929"] else "",
                "benchmark_potential": r["benchmark_potential"],
                "recommended_use": r["recommended_use"],
                "comment_count": r["comment_count"],
                "has_injection_molding": r["has_injection_molding"],
                "has_vocs": r["has_vocs"],
                "has_activated_carbon": r["has_activated_carbon"],
                "has_hazardous_waste": r["has_hazardous_waste"],
            })
    print(f"  Saved: {csv_path}")

    # Save stats JSON
    stats_path = os.path.join(OUT_DIR, "exploration_stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {stats_path}")

    # Print summary
    print()
    print("=" * 50)
    print("EXPLORATION SUMMARY")
    print("=" * 50)
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print()
    print(f"Output directory: {OUT_DIR}")


if __name__ == "__main__":
    main()
