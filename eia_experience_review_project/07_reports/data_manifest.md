# Data Manifest — 环评智能审核经验库项目

> 生成日期: 2026-06-10 | 项目根目录: `E:\eia_experience_review_project\`

---

## 一、终审环评报告 (`01_raw_data/reports_final/`)

| 文件 | 大小 | 类型 | 用途 |
|------|------|------|------|
| 终稿-佛山市盛之强电器有限公司建设项目.docx | ~15MB | docx | 核心测试案例：C2929 塑料注塑类报告表，用于抽取项目画像、审核流程标注、经验规则触发验证 |

**状态**: [READY] 1/1 已到位
**缺失**: `fda1494e-6abf-4d39-88a6-5e302d7f111f.docx`（任务书中提到的另一个报告，未找到）

---

## 二、三线一单与地方空间管控 (`01_raw_data/local_spatial_control/`)

| 文件 | 类型 | 用途 |
|------|------|------|
| #4_三线一单_顺德管控单元_完整.json | json | 25个管控单元的完整数据（结构化） |
| #4_三线一单_顺德管控单元_完整.jsonl | jsonl | 同上，行式格式 |
| #4_三线一单_顺德管控单元_完整.csv | csv | 同上，表格格式 |
| #4_三线一单_顺德管控单元_Dify导入版.json | json | Dify 工作流导入格式 |
| #4_三线一单_顺德管控单元准入清单.md | md | 管控单元准入清单（Markdown） |
| 三线一单_顺德管控单元准入清单.md | md | 准入清单（另一个版本） |
| #4_三线一单_补全说明.md | md | 补全三线一单数据的说明 |
| #4_三线一单_补全文件清单.md | md | 需要补全的文件清单 |

**状态**: [READY] 8/8 已到位

---

## 三、标准条款库与政策准入库 (`01_raw_data/standards_policies/`)

| 文件 | 类型 | 用途 |
|------|------|------|
| standard_clause_library_from_reports.jsonl | jsonl | 从11份报告中抽取的标准条款库（原始版） |
| policy_admission_clause_library.jsonl | jsonl | 政策准入库（原始版） |
| policy_admission_clause_library_checked.jsonl | jsonl | 政策准入库（人工修正版） |

**状态**: [READY] 3/3 已到位
**缺失**: `standard_clause_library_from_reports_checked.jsonl`（人工修正版标准条款库，未放入但可从 `E:\软件\standard_clause_output_checked\` 补充）

---

## 四、基准数据集 (`01_raw_data/benchmark_dataset/`)

| 文件 | 类型 | 用途 |
|------|------|------|
| sample_eia_benchmark.jsonl | jsonl | EIA benchmark 样例 |
| qa_v4_final_verified.jsonl | jsonl | QA v4 最终验证集 |

**状态**: [READY] 2/2 已到位

---

## 五、经验规则库 (`04_experience_library/source_rules/`)

| 文件 | 类型 | 用途 |
|------|------|------|
| experience_rules_all.json | json | 全部经验规则 |
| experience_rules_A_verified.json | json | A级：已验证规则（可作强规则） |
| experience_rules_B_candidate.json | json | B级：候选规则（需人工复核） |
| experience_rules_C_observation.json | json | C级：观察规则（仅人工关注） |
| experience_rules_summary.csv | csv | 规则汇总统计 |
| experience_rules_by_industry.md | md | 按行业分类的经验规则 |
| final_experience_library_report.md | md | 经验库最终报告 |
| db_experience_data_assessment.md | md | 数据库经验数据评估 |
| industry_experience_base.json | json | 行业经验库基础数据 |

**状态**: [READY] 9/9 已到位

---

## 六、建议后续补充的数据（当前缺失）

| 优先级 | 数据类型 | 用途 | 可能位置 |
|--------|---------|------|---------|
| P0 | 初审环评报告（未修改版） | 负样本，抽取真实错误 | `E:\华南理工项目\环评知识库文件\` |
| P0 | 退改意见 / 技术审查意见 | 抽取真实审核问题 | `E:\openclaw_archive\workspace\agent\workspace\ai_packages_extracted\` |
| P1 | 批复文件 | 抽取政府管理要求 | `E:\软件\环评原始数据\顺德区批复\` |
| P1 | 受理公告 | 项目清单与公开信息 | 顺德区政府网站 |
| P1 | 声/水环境功能区划文件 | 空间管控验证 | 待确认位置 |
| P2 | 塑料行业产排污系数手册 | 源强核算验证 | 生态环境部官网 |
| P2 | 顺德区生态环境状况公报 | 环境质量现状验证 | 顺德区政府网站 |
| P2 | 年度环境质量公报 | 功能区划验证 | 佛山市生态环境局 |

---

## 七、目录结构总览

```
eia_experience_review_project/     (23 files, 113 MB)
├── TASK_BOOK.md                   ← 完整任务书
├── 00_memory/                     ← 记忆文件（本轮初始化）
├── 01_raw_data/                   ← 23 个原始数据文件
├── 02_parsed_data/                ← 待填充（解析结果）
├── 03_structured_outputs/         ← 待填充（结构化输出）
├── 04_experience_library/         ← 9 个经验规则 + schema待建
├── 05_skills/                     ← 待填充（Skill）
├── 06_test_runs/                  ← 待填充（测试案例）
└── 07_reports/                    ← 本文件 + 后续报告
```
