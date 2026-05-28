# ELLE Dataset Construction Methodology — Transfer Analysis for EIA Experience Base

**Source**: Guo et al., "Environmental large language model Evaluation (ELLE) dataset: A Benchmark for Evaluating Generative AI applications in Eco-environment Domain" (2025)

**Purpose**: Extract the 5 key ideas from ELLE's dataset construction methodology and map them to the EIA report review experience base.

---

## Idea 1: Three-Tier Classification System

### What ELLE does

Every QA pair is tagged with 3 independent dimensions:

| Dimension | Values | Purpose |
|-----------|--------|---------|
| **Domain** (16 subjects) | Environmental Geology, Environmental Chemistry, Water Environment... | Ensures disciplinary coverage |
| **Difficulty** (3 levels) | Simple (18.8%), Medium (43.1%), Hard (38.1%) | Enables granular capability assessment |
| **Type** (3 types) | Knowledge (50%), Calculation (7.6%), Reasoning (28.8%) | Tests different cognitive skills |

This 3D classification is what makes ELLE more than just a list of questions — it turns the dataset into an **analytical instrument** that can measure *where* a model fails (which domain? which difficulty? which type?).

### How to apply to EIA experience base

Replace ELLE's 3 dimensions with EIA-specific equivalents:

| ELLE Dimension | EIA Experience Base Dimension | EIA Values |
|----------------|------------------------------|------------|
| Domain (16 subjects) | **Industry** (82 codes) | C2929 塑料零件制造, C3360 金属表面处理... |
| Difficulty (3 levels) | **Severity** (3 levels) | high(审批>50%), medium(审批30-50%), low(<30%) |
| Type (3 types) | **Element** (5 types) | 废水, 废气, 噪声, 固废, 危废 |

**Key insight**: Just as ELLE's "Domain × Difficulty × Type" creates a 3D evaluation space, your "Industry × Severity × Element" creates a 3D **experience space**. Each cell in this space represents a specific审查经验.

### Current implementation

Your `industry_experience_base.json` already organizes by Industry → Element → Standards with frequency. Adding the Severity dimension (derived from approval_rate) completes the 3D structure.

---

## Idea 2: Controlled Data Sourcing Strategy

### What ELLE does

ELLE uses two complementary sourcing strategies:

| Source | Difficulty | Quantity | Quality Control |
|--------|-----------|----------|----------------|
| **Expert questionnaire** | Medium-Hard | Majority of 1,130 | Expert identity verification + peer review |
| **Open-source materials** | Medium | Supplementary | Source verification + cross-check |

This dual-sourcing ensures:
- Expert questions provide **depth** and **domain authority**
- Open-source materials provide **breadth** and **coverage**

### How to apply to EIA experience base

Your equivalent dual-sourcing strategy:

| Source | What it provides | Your Data |
|--------|-----------------|-----------|
| **Government approval documents (批复文件)** | Actual审查结论 (high authority) | 2,406份批复 → 1,963条审查条件 |
| **EIA reports (环评报告)** | 报告引用标准 (practical coverage) | 2,640份受理公告 → full.md |

**Key insight**: ELLE's expert + textbook combination is analogous to your approval + report combination. The approval documents are the "expert judgments" (政府审批专家 wrote them), and the reports are the "open-source materials" (what practitioners actually do). The **gap between them** is where your审查经验 lives.

### Why your data is stronger than ELLE's

| Aspect | ELLE | You |
|--------|------|-----|
| Expert source | Survey questionnaires | **Real government approval decisions** |
| Expert authority | Self-reported expertise | **Legal authority (政府公章)** |
| Ground truth | Expert consensus | **Actual regulatory requirements** |
| Scale | 1,130 QA pairs | 49 review rules (expandable) |

---

## Idea 3: Three-Round Cross-Validation → Evidence-Based Validation

### What ELLE does

```
Round 1: Independent expert evaluation (each QA pair reviewed by 1 group)
Round 2: Cross-review by different expert group
Round 3: Flag disagreements → consensus meeting
```

This is necessary because ELLE's data has no objective ground truth — it's all expert opinion.

### How to apply to EIA experience base

Your data has **objective ground truth** (the actual approval documents), so you can replace ELLE's subjective validation with evidence-based validation:

| ELLE Step | Your Equivalent |
|-----------|----------------|
| Expert evaluation | **Auto-check**: Does the standard appear in the approval text? |
| Cross-review | **Cross-source verification**: Does the same pattern appear across multiple approvals? |
| Consensus meeting | **Statistical threshold**: >=80% = strong commonality, >=60% = general |

**Key insight**: ELLE needs 3-round expert review because QA pair quality is subjective. Your审查规则 are *objectively verifiable* — either the approval cited the standard or it didn't. This means you can scale your validation automatically to thousands of approvals, which ELLE cannot.

---

## Idea 4: Dataset as an Analytical Instrument

### What ELLE does

ELLE publishes their dataset with a **public leaderboard** that tracks model performance across the 3 classification dimensions. This turns the dataset from a static collection into a **diagnostic tool**:

```
LLM-X Score: 82.4/100
  By Domain:    Environmental Ecology: 85.1, Water: 79.3, Air: 81.2...
  By Difficulty: Simple: 91.2, Medium: 83.5, Hard: 72.6
  By Type:      Knowledge: 88.4, Reasoning: 78.9, Calculation: 75.2
```

### How to apply to EIA experience base

Your experience base can serve a similar diagnostic function — but instead of diagnosing LLMs, it diagnoses **EIA report quality**:

```
EIA Report X — Compliance Assessment:
  C2929 塑料零件制造:
    By Element:  废气: 85%, 废水: 72%, 噪声: 90%, 固废: 45%, 危废: 50%
    Strong Common Standards Met:  4/6 (67%)
    Missing: GB18599-2001 (固废), GB18597-2023 (危废)
```

This shifts the experience base from a passive knowledge repository to an **active audit tool**.

---

## Idea 5: Web-Based Interactive Exploration

### What ELLE does

The elle.ceeai.net website provides:
1. **Search** across all 1,130 questions
2. **Filter by 3 dimensions** (Domain, Difficulty, Type)
3. **Card-based display** with badges for metadata
4. **Bilingual toggle** (Chinese/English)
5. **GitHub link** for full dataset access

This turns the dataset into an accessible resource that researchers can explore without downloading.

### How to apply to EIA experience base

Your experience base website should provide:
1. **Search** across all review rules
2. **Filter by 3 dimensions** (Industry, Severity, Element)
3. **Card-based display** with frequency bars + gap indicators
4. **Industry detail pages** with full standard frequency tables
5. **Comparison view**: report standards vs approval standards side-by-side

---

## Synthesis: Action Plan

### Phase 1: Complete the 3D Classification (已完成)

- [x] Element (废水/废气/噪声/固废/危废) — extracted from approval conditions
- [x] Industry (C2929, C3360...) — mapped via approval_title matching
- [x] Severity (approval_rate %) — calculated from frequency statistics

### Phase 2: Build the Structured Dataset (当前)

- [x] 49 review rules generated
- [x] 59 industry experience bases built
- [ ] Add evidence links (which approval files support each rule)
- [ ] Add report_approval gap calculation per rule

### Phase 3: Web-Based Experience Base (未来)

- [ ] Static HTML page with search + 3D filter (clone ELLE website pattern)
- [ ] GitHub Pages deployment
- [ ] Link from eia-llm-judge-framework README

---

## Comparison Table: ELLE vs EIA Experience Base

| Feature | ELLE-QA Benchmark | EIA Experience Base |
|---------|------------------|---------------------|
| Core unit | Question-Answer pair (1,130) | **Review rule** (49, expandable) |
| Classification | Domain × Difficulty × Type | **Industry × Severity × Element** |
| Data source | Expert survey + textbooks | **Government approvals + EIA reports** |
| Ground truth | Expert consensus | **Legal documents (verifiable)** |
| Validation | 3-round expert review | **Statistical frequency + evidence traceability** |
| Publication | Web + GitHub | GitHub (planned) |
| Purpose | Evaluate LLMs | **Audit EIA report quality** |

---

*Generated: 2026-05-28 | EIA-LLM-Judge-Framework*
