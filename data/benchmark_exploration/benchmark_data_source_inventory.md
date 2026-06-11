# Benchmark 数据源清单 — 顺德历史环评数据库

> 探索日期: 2026-06-11
> 探索范围: 顺德区2023-2026年环评相关数据

---

## 数据源总览

| 数据源 | 位置 | 数量 | 类型 | Benchmark价值 |
|--------|------|------|------|--------------|
| **审核意见包** (ai_packages) | `E:\openclaw_archive\workspace\agent\workspace\ai_packages_extracted\ai_packages\` | 30个项目, 502条批注 | body.md + comments.jsonl | **P0 — real_error** |
| **审批-报告配对** (clean_pairs) | `E:\eia-llm-judge-framework\data\clean_pairs\` | 85对 (65对完整) | pair_metadata.json + report.md + approval.md | **P1 — approval_alignment + cross_check** |
| **历史数据库QA** (historical_db) | `E:\eia-llm-judge-framework\data\historical_db\` | 536条QA | qa_experience_base.jsonl | **P2 — experience_rule_source** |
| **审批文件(已解析)** (approval_mineru) | `E:\软件\approval_mineru_parsed\` | 2,406份 | approval.md (MinerU解析) | P2 |
| **审批PDF原件** | `E:\软件\2023-2026年顺德批复文件\` | ~3,195份 | PDF | P3 |
| **Obsidian审核批注** | `E:\openclaw_archive\workspace\agent\obsidian-vault\00-经验库\01-审核批注\` | 28份 | Markdown | P1 |
| **技术审查QA** (tech_review_qa) | `E:\eia-llm-judge-framework\data\tech_review_qa\` | ~100+条 | jsonl | P1 |

---

## 数据源详细结构

### 1. 审核意见包 (ai_packages) — 30个项目的修改意见

**文件结构**:
```
{project_name}/
├── manifest.json      # 元信息(comment_count, table_count, figure_count)
├── body.md            # 完整报告正文(含批注引用标记 [Cxxx])
├── comments.jsonl     # 每条批注的完整文本
├── tables.jsonl       # 提取的表格
├── figures.jsonl      # 图摘要
└── media/             # 图片文件
```

**comments.jsonl 格式**:
```json
{"comment_id": "C001", "comment_text": "补充配件尺寸...", "refs": null, "comment_type": null}
```

**行业分布**:
- C2929塑料制品: 6个项目
- 五金/金属: 3个
- 涂料/化工: 3个
- 其他制造业: 约18个

### 2. 审批-报告配对 (clean_pairs) — 85对

**pair_metadata.json 格式**:
```json
{
  "pair_id": "pair_00001",
  "company": "...",
  "project_name": "...",
  "match_score": 100.0,
  "report_source": "E:\\软件\\mineru_extracted\\...\\full.md",
  "approval_source": "E:\\软件\\环评原始数据\\顺德区批复\\...pdf"
}
```

### 3. 历史数据库QA — 536条

| 来源 | 数量 | 字段 |
|------|------|------|
| `hp_approve_info.APPROVE_OPINION` | 424 | 批复意见全文 |
| `hp_approve_tech.REPLY_NOTE` | 112 | 技术审查专家意见 |

---

## 数据库"表"结构 (从文件系统推断)

当前数据并非传统SQL数据库，而是文件系统中组织的结构化+半结构化数据。以下按"类表结构"描述：

| "表" | 字段 | 记录数 | 说明 |
|------|------|--------|------|
| audit_packages | doc_id, comment_count, body, comments[], tables[], figures[] | 30 | 审核意见包 |
| clean_pairs | pair_id, company_name, project_name, match_score, report_path, approval_path | 85 | 报告-批复配对 |
| qa_pairs | qa_id, pair_id, level, region, company, element, review_point, question, answer | 536 | 历史QA |
| tech_review_qa | qa_id, question, answer, region, element | ~100 | 技术审查QA |
| approval_parsed | doc_name, company, approval_date, full_text | 2,406 | 已解析批复 |
| approval_pdfs | doc_name, file_size, date | ~3,195 | 批复PDF原件 |
| obsidian_notes | title, content, tags | 28 | 审核批注笔记 |

**关键发现**:
- **没有独立的"审核意见表"** — 审核意见嵌入在 ai_packages 的 comments.jsonl 中
- **没有"版本链表"** — 但可以从 project_name 的相似度推断多版本
- **没有"项目元数据表"** — 元数据分散在各文件的 manifest/basename/metadata 中
