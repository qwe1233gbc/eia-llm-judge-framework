# 环评历史数据库（EIA Historical Database）

## 概述

本数据库从佛山市环评审批管理平台数据库中提取，包含 **536 条 QA 问答对**，覆盖废气治理领域的审批要求与技术审查经验。

## 数据来源

| 来源表 | 数据量 | 字段 | 说明 |
|--------|:------:|------|------|
| `hp_approve_info` | 424 条 | `APPROVE_OPINION` | 环评批复意见（含排放标准、治理要求） |
| `hp_approve_tech` | 112 条 | `REPLY_NOTE` | 技术审查专家意见（含修改要求） |
| **合计** | **536 条** | | |

## 文件结构

```
data/historical_db/
├── qa_experience_base.jsonl   ← QA问答对（536条）
├── README.md                  ← 本文件
└── extract_from_db.py         ← 数据提取脚本
```

## QA 格式

```json
{
  "qa_id": "DB_QA_00001_废气",
  "pair_id": "db_pair_00001",
  "level": "区级",
  "region": "广东省佛山市顺德区",
  "company": "公司名称",
  "project_type": "一般项目",
  "element": "废气",
  "review_point": "审批要求与报告支撑核查",
  "question": "【区级】某公司该项目废气的收集形式、治理设施、排放标准和排放参数是什么？",
  "answer": "批复要求：...",
  "standards_normalized": [...],
  "approval_evidence": [...],
  "benchmark_metadata": {"task_domain": "废气", "difficulty": "simple", ...},
  "quality_score": 80,
  "need_human_review": true
}
```

## 局限性

- 所有 QA 对由脚本自动提取，**未经人工审核**
- 部分批复意见使用旧版标准编码，需注意时效性
- 仅有 `approval_evidence`，缺少 `report_evidence`