# OpenClaw / Claude Code 执行任务书：环评智能审核经验库整理与迭代构建

> 适用场景：本任务书用于交给 OpenClaw / Claude Code 执行。目标不是单纯整理文件，而是模拟政府环评审核经办人的真实审查流程，把历史环评报告、批复、初审问题、地方政策和经验规则整理为可复用、可验证、可迭代的“环评审核经验库”。

---

## 0. 核心目标

本项目要解决的问题是：

```text
真实环评经办人在审核报告表时，会按“项目身份—空间准入—功能区划—工程分析—源强核算—治理设施—危废风险—附表一致性—批后监管”的顺序进行审查。

经验库的作用，是把这种隐性审核经验结构化为：
项目特征 → 触发审核点 → 查报告位置 → 调用依据 → 输出审核提示 → 记录人工复核结果。
```

最终要形成一套可供论文复现实验使用的材料：

1. 经验库构建流程说明；
2. 原始数据清单与数据类型说明；
3. 环评报告字段抽取结果；
4. C2929 塑料注塑类项目审核经验对；
5. OpenClaw / Claude Code 可执行的审核 Skill；
6. 记忆文件与迭代日志；
7. 测试运行结果与效果评价表。

---

## 1. 工作区目录结构

请在当前项目根目录下创建以下目录：

```text
/eia_experience_review_project/
├── 00_memory/
│   ├── MEMORY.md
│   ├── TASK_BOARD.md
│   ├── ITERATION_LOG.md
│   ├── RULE_CHANGELOG.md
│   └── FAILURE_CASES.md
│
├── 01_raw_data/
│   ├── reports_final/
│   ├── reports_initial_review/
│   ├── approvals/
│   ├── acceptance_announcements/
│   ├── standards_policies/
│   ├── local_spatial_control/
│   └── benchmark_dataset/
│
├── 02_parsed_data/
│   ├── markdown_reports/
│   ├── extracted_tables/
│   ├── figures_index/
│   └── metadata/
│
├── 03_structured_outputs/
│   ├── project_profiles/
│   ├── pollutant_chains/
│   ├── standard_matching/
│   ├── spatial_control_matching/
│   └── consistency_checks/
│
├── 04_experience_library/
│   ├── schemas/
│   ├── experience_pairs/
│   ├── evidence_grading/
│   ├── review_rules/
│   └── comment_templates/
│
├── 05_skills/
│   └── eia-review-experience-skill/
│       └── SKILL.md
│
├── 06_test_runs/
│   ├── shengzhiqiang_case/
│   └── batch_tests/
│
└── 07_reports/
    ├── data_manifest.md
    ├── methodology_for_thesis.md
    ├── review_workflow_mapping.md
    ├── evaluation_report.md
    └── final_summary.md
```

---

## 2. 必须上传或放入工作区的文件

### 2.1 已有文件：优先放入 `01_raw_data/`

请把以下文件按类型复制到对应目录，不要改动原文件内容。

#### A. 终审环评报告

放入：`01_raw_data/reports_final/`

```text
终稿-佛山市盛之强电器有限公司建设项目.docx
fda1494e-6abf-4d39-88a6-5e302d7f111f.docx
```

用途：作为已发布、相对规范的报告样本，用于抽取“标准写法、完整链条、正样本审核路径”。

---

#### B. 三线一单与地方空间管控资料

放入：`01_raw_data/local_spatial_control/`

```text
#4_三线一单_补全说明.md
#4_三线一单_补全文件清单.md
#4_三线一单_顺德管控单元_Dify导入版.json
#4_三线一单_顺德管控单元_完整.csv
#4_三线一单_顺德管控单元_完整.json
#4_三线一单_顺德管控单元_完整.jsonl
#4_三线一单_顺德管控单元准入清单.md
```

用途：建立“坐标/管控单元编号 → 管控要求 → 审核提示”的地方准入库。

---

#### C. 经验规则库文件

放入：`01_raw_data/benchmark_dataset/` 或 `04_experience_library/source_rules/`

```text
experience_rules_A_verified.json
experience_rules_B_candidate.json
experience_rules_C_observation.json
experience_rules_all.json
experience_rules_by_industry.md
experience_rules_summary.csv
final_experience_library_report.md
industry_experience_base.json
db_experience_data_assessment.md
```

用途：作为已有经验库基础，按证据等级 A/B/C 重构为可解释经验对。

---

#### D. 标准条款库、政策准入库、测试集

放入：`01_raw_data/standards_policies/` 和 `01_raw_data/benchmark_dataset/`

```text
policy_admission_clause_library.jsonl
policy_admission_clause_library_checked.jsonl
standard_clause_library_from_reports.jsonl
sample_eia_benchmark.jsonl
```

用途：

- 标准库：用于判断执行标准、污染物限值、标准适用性；
- 政策库：用于判断产业准入、三线一单、地方政策；
- 测试集：用于验证经验库是否真的能提高审核效果。

---

### 2.2 建议后续补充的数据

以下数据如果有，应优先补充，因为它们对“证明经验库有用”最重要。

```text
1. 初审环评报告：还没有改好的报告，最适合做负样本；
2. 退改意见 / 技术审查意见：最适合抽取真实问题；
3. 批复文件：最适合抽取政府最终管理要求；
4. 受理公告：用于补充项目清单、项目状态、公开来源；
5. 顺德区环评系统历史数据库：用于批量统计行业、标准、污染物、批复要求；
6. 年度环境质量公报：佛山市、顺德区及各区；
7. 声环境功能区划、水环境功能区划、污水厂服务范围资料；
8. 塑料行业产排污系数手册、广东/上海/台湾等地方系数资料；
9. 佛山/顺德 VOCs、活性炭、总量替代、工业废水地方口径文件。
```

---

## 3. OpenClaw 记忆机制设计

OpenClaw 的记忆不要依赖对话上下文，要落到文件系统。请使用 `00_memory/` 下的 Markdown 文件作为长期记忆。

### 3.1 `MEMORY.md`：稳定项目记忆

每次任务开始前先读取，任务结束后更新。内容包括：

```text
项目研究主题：面向环评智能审核的领域经验库构建方法研究。
当前聚焦行业：C2929 塑料零件及其他塑料制品制造，尤其是塑料注塑类报告表。
核心科学问题：历史审核经验能否被结构化，并提升低经验审核者关键问题识别能力。
经验库定位：不是自动审批，而是辅助小白经办人发现高风险审核点。
证据等级策略：A级可作为强规则，B级作为强提示，C级只作为人工关注项。
当前重点案例：佛山市盛之强电器有限公司建设项目。
```

### 3.2 `TASK_BOARD.md`：任务看板

格式：

```markdown
# Task Board

## Doing
- [ ] 解析盛之强终稿报告
- [ ] 抽取项目画像
- [ ] 映射经办人审核流程

## Done
- [ ] 建立目录结构
- [ ] 整理原始数据清单

## Next
- [ ] 构建 C2929 经验对 schema
- [ ] 编写 eia-review-experience-skill
```

### 3.3 `ITERATION_LOG.md`：迭代日志

每次执行必须追加，不允许覆盖。

格式：

```markdown
## Iteration YYYY-MM-DD HH:mm

### Input
- 本轮使用的文件：
- 本轮用户目标：

### Actions
- 完成了什么解析：
- 生成了什么结构化文件：
- 修改了哪些规则：

### Findings
- 新发现的审核点：
- 发现的文件问题：
- 发现的规则冲突：

### Outputs
- 输出文件路径：

### Next
- 下一轮应继续做什么：
```

### 3.4 `RULE_CHANGELOG.md`：规则变更日志

用于记录经验规则的新增、修改、降级、删除。

```markdown
## Rule Change YYYY-MM-DD

- rule_id:
- action: add / update / downgrade / remove
- old_version:
- new_version:
- reason:
- evidence:
- reviewer:
```

### 3.5 `FAILURE_CASES.md`：失败案例库

用于记录系统误判、漏判、幻觉、证据不足的情况。

```markdown
## Failure Case ID

### Case
- 报告名称：
- 行业：
- 审核模块：

### Failure Type
- 漏判 / 误报 / 依据错 / 数值算错 / 标准误配 / 证据不足

### Cause
- 原因分析：

### Fix
- 修正规则：
- 是否更新 Skill：
```

---

## 4. 迭代机制设计

每次执行必须按以下循环进行，不允许一次性生成最终结论。

```text
读取 MEMORY.md
        ↓
读取 TASK_BOARD.md
        ↓
确认本轮任务目标
        ↓
处理本轮输入文件
        ↓
生成结构化输出
        ↓
运行规则或审核模拟
        ↓
记录发现的问题
        ↓
更新 ITERATION_LOG.md
        ↓
必要时更新 RULE_CHANGELOG.md / FAILURE_CASES.md
        ↓
更新 TASK_BOARD.md
```

### 4.1 每轮最小输出

每轮至少输出：

```text
1. 本轮完成了什么；
2. 生成了哪些文件；
3. 发现了哪些审核点或规则问题；
4. 哪些内容证据不足；
5. 下一轮应处理什么。
```

### 4.2 不允许的行为

```text
1. 不允许直接覆盖原始文件；
2. 不允许把 C 级规则当成确定性规则；
3. 不允许输出“合格/不合格”而不给证据；
4. 不允许只给总结，不给文件路径；
5. 不允许把终审报告中的结论直接当成事实，必须能追溯到报告章节或外部依据；
6. 不允许把经验库等同于标准库，必须区分法规标准、地方口径、历史经验、人工关注项。
```

---

## 5. 文档解析流程

### 5.1 对 Word 报告

优先使用 Python `python-docx` 或 Markdown 转换工具：

```text
输入：docx
输出：
- markdown_reports/{project_id}.md
- extracted_tables/{project_id}_tables.json
- metadata/{project_id}_metadata.json
```

必须保留：

```text
章节标题；
表格标题；
表格内容；
附图名称；
附件名称；
污染物排放量；
标准名称；
经纬度；
行业类别；
工艺流程；
产污环节。
```

### 5.2 对 PDF 报告

如后续有 PDF 报告，用 MinerU 解析：

```text
PDF → Markdown + Tables + Images
```

输出要求同上。

### 5.3 对批复、受理公告、退改意见

按文本类型分别抽取：

```text
批复：抽取审批要求、废水/废气/噪声/固废/总量/排污许可/验收要求；
受理公告：抽取项目名称、建设单位、地点、报告类型、公告时间；
退改意见：抽取问题类型、问题描述、修改要求、对应报告章节；
初审报告：抽取错误项，与终稿报告对齐。
```

---

## 6. 经办人审核流程映射

请把每份报告按真实经办人的审核流程映射，而不是按模型问答随意抽取。

### 6.1 标准审核顺序

```text
1. 项目身份审查
2. 报告类型与专项评价审查
3. 经纬度与三线一单审查
4. 规划、规划环评、产业准入审查
5. 功能区划和环境质量现状审查
6. 敏感点识别审查：500m大气、50m声环境
7. 工程组成审查
8. 产能与原辅料平衡审查
9. 工艺流程与产污环节审查
10. 执行标准适用性审查
11. 废水源强与排放去向审查
12. 废气源强与污染因子审查
13. 废气收集系统审查
14. 活性炭治理设施参数审查
15. 噪声源强与厂界达标审查
16. 固废和危废代码审查
17. 环境风险识别与防范措施审查
18. 自行监测、排污许可、验收、台账审查
19. 附图附件完整性审查
20. 附表与全文一致性审查
```

### 6.2 每一步输出格式

```json
{
  "step_id": "S01",
  "step_name": "项目身份审查",
  "report_location": "一、建设项目基本情况",
  "extracted_evidence": [],
  "review_question": [],
  "risk_points": [],
  "experience_rules_triggered": [],
  "need_human_check": true,
  "suggested_comment": ""
}
```

---

## 7. 经验对结构化 schema

请把经验对统一整理为 JSONL，每行一条规则。

文件路径：

```text
04_experience_library/experience_pairs/experience_pairs_C2929.jsonl
```

Schema：

```json
{
  "experience_id": "EXP_C2929_AIR_001",
  "industry_code": "C2929",
  "industry_name": "塑料零件及其他塑料制品制造",
  "project_features": [
    "注塑",
    "塑料粒原料",
    "活性炭吸附",
    "非甲烷总烃",
    "臭气浓度"
  ],
  "trigger_condition": [
    "报告设备清单存在注塑机",
    "工艺流程存在注塑/熔融成型",
    "废气治理设施存在活性炭吸附"
  ],
  "review_module": "废气源强与治理设施",
  "review_checkpoints": [
    "是否识别非甲烷总烃和臭气浓度",
    "是否说明废气收集方式",
    "是否核算收集效率",
    "是否说明活性炭风量、风速、停留时间、装填量和更换频次",
    "是否核算废活性炭产生量"
  ],
  "evidence_source_type": [
    "终审报告",
    "历史批复",
    "地方规范",
    "专家经验"
  ],
  "evidence_source_file": [],
  "evidence_level": "A/B/C",
  "automation_level": "auto_rule / strong_hint / human_attention",
  "failure_risk": [
    "收集效率取值过高",
    "活性炭参数缺失",
    "废活性炭量未闭合"
  ],
  "suggested_comment_template": "请补充注塑废气收集系统设计参数，包括集气罩形式、罩口距离、控制风速、收集效率取值依据，并补充活性炭装填量、更换周期及废活性炭产生量核算。"
}
```

---

## 8. 证据等级规则

### A级：可作为强规则

满足以下条件之一：

```text
1. 来自明确法规、标准、地方正式文件；
2. 来自已核验的批复或专家意见；
3. 多个历史案例一致，且有原文证据支撑；
4. 已经过人工复核。
```

使用方式：可以作为自动审核规则或强约束提示。

### B级：强提示

满足：

```text
1. 来自多个历史案例，但证据尚未完全复核；
2. 与经办人经验一致，但缺少正式依据；
3. 可用于提醒人工关注。
```

使用方式：输出“建议复核”，不能直接判错。

### C级：观察项

满足：

```text
1. 单个案例观察；
2. 未经过原文证据审计；
3. 可能受行业、区域、时间影响。
```

使用方式：只输出“人工关注项”，不得作为确定性结论。

---

## 9. Skill 编写任务

请在以下位置生成 OpenClaw Skill：

```text
05_skills/eia-review-experience-skill/SKILL.md
```

Skill 目标：

```text
当用户提供一份环评报告时，该 Skill 按真实经办人的审核顺序进行结构化审查，调用经验库、标准库、三线一单库，输出“审核流程标注表 + 风险问题清单 + 需人工复核项 + 经验规则命中情况”。
```

### 9.1 SKILL.md 建议内容

```markdown
---
name: eia-review-experience-skill
description: 按政府环评审核经办人的真实流程，对建设项目环评报告表进行结构化初审，特别适用于顺德区塑料注塑类项目。
---

# 环评报告经验库辅助审核 Skill

## 使用时机

当用户上传或指定一份建设项目环境影响报告表，并希望模拟政府环评经办人进行初审时，使用本 Skill。

## 核心原则

1. 不直接输出“通过/不通过”；
2. 按真实经办人审核流程逐步审查；
3. 所有问题必须对应报告位置、依据来源和经验规则；
4. A级规则可作为强规则，B级规则作为强提示，C级规则只能作为人工关注项；
5. 输出必须区分“确定问题”“疑似问题”“人工复核项”；
6. 不得把终稿报告中的自我结论直接当成事实，必须核正文、表格、附图、附表一致性。

## 审核顺序

1. 项目身份审查；
2. 报告类型与专项评价审查；
3. 经纬度与三线一单审查；
4. 规划、规划环评、产业准入审查；
5. 功能区划和环境质量现状审查；
6. 500m大气敏感点和50m声环境敏感点审查；
7. 工程组成、原辅料、设备、产能审查；
8. 工艺流程和产污环节审查；
9. 执行标准适用性审查；
10. 废水、废气、噪声、固废、危废、风险逐项审查；
11. 活性炭治理设施参数审查；
12. 排污许可、验收、台账和监督检查清单审查；
13. 附表与全文一致性审查。

## 输出格式

输出以下五个部分：

### 1. 项目画像

- 项目名称：
- 地点：
- 坐标：
- 行业类别：
- 工艺：
- 主要污染物：
- 重点审核模块：

### 2. 经办人审核流程标注表

| 审核步骤 | 报告位置 | 抽取证据 | 经办人核查问题 | 命中经验规则 | 风险等级 | 是否需人工复核 |
|---|---|---|---|---|---|---|

### 3. 风险问题清单

| 问题编号 | 问题类型 | 问题描述 | 报告位置 | 判断依据 | 证据等级 | 修改建议 |
|---|---|---|---|---|---|---|

### 4. 人工复核项

列出模型不能直接判断、需要 GIS、图件、地方系统、专家确认的内容。

### 5. 经验库迭代建议

指出哪些规则需要新增、升级、降级或人工复核。
```

---

## 10. 盛之强案例测试任务

请以 `终稿-佛山市盛之强电器有限公司建设项目.docx` 为测试案例。

生成目录：

```text
06_test_runs/shengzhiqiang_case/
```

必须输出：

```text
project_profile.json
review_workflow_annotation.md
triggered_experience_rules.jsonl
risk_attention_list.md
calculation_check.json
consistency_check.md
human_review_needed.md
```

### 10.1 该案例必须识别出的项目画像

```text
项目名称：佛山市盛之强电器有限公司建设项目
行业类别：C2929 塑料零件及其他塑料制品制造
地点：佛山市顺德区大良街道古鉴村良勒路245号首层之一
坐标：东经113°12′23.048″，北纬22°50′32.808″
建设性质：新建
工艺：烘料、混料、注塑、冷却、修边、破碎、模具维修
主要废气：非甲烷总烃、臭气浓度、颗粒物
主要废水：生活污水、间接冷却水
主要危废：废矿物油、废油桶、废含油抹布、废活性炭
废气治理：点对点局部密闭集气罩 + 活性炭吸附 + 15m排气筒
```

### 10.2 必须触发的审核关注项

```text
1. 坐标与大良街道重点管控区 ZH44060620002 是否一致；
2. 三线一单条款是否逐条对应；
3. 厂界500m大气敏感点是否漏判；
4. 厂界50m声敏感点是否漏判；
5. 顺德支流、大气二类区、3类声功能区是否正确；
6. NMHC产污系数是否对应 C2929 注塑工序；
7. NMHC产生量、收集量、有组织排放量、无组织排放量是否闭合；
8. 收集效率65%是否与半密闭集气设施条件一致；
9. 设计风量7500m3/h是否由罩口尺寸、距离、风速推得；
10. 活性炭过滤风速0.58m/s、停留时间0.52s是否接近边界值；
11. 废活性炭1.818t/a是否由年用炭量1.728t/a和吸附量0.090t/a推得；
12. 间接冷却水排雨水管网是否符合地方口径；
13. 危废代码是否正确；
14. 风险Q值是否漏算；
15. 附表与正文、总量控制、监督检查清单是否一致。
```

---

## 11. 效果评价设计

经验库是否有用，不能只看系统有没有输出，而要看它是否能帮助小白经办人更好地发现问题。

请建立：

```text
07_reports/evaluation_report.md
```

评价指标：

```text
1. 关键问题召回率：系统/小白发现的专家标注问题数 ÷ 专家标注问题总数；
2. 误报率：专家认为不是问题的提示数 ÷ 系统提示总数；
3. 审核意见质量：0-3分，是否具体到问题、依据、修改方向；
4. 证据引用正确率：是否正确引用报告位置、标准、经验规则；
5. 审核时间：使用经验库前后完成初审所需时间；
6. 规则命中有效率：命中的经验规则中，被专家认可的比例；
7. A/B/C规则有效性差异：A级、B级、C级规则分别产生多少有效提示。
```

对照实验建议：

```text
A组：只给报告，不给经验库；
B组：给报告 + 标准库；
C组：给报告 + 标准库 + 经验库；
D组：给报告 + 错配行业/错配地区经验库，用于验证经验库不是“信息越多越好”。
```

证伪条件：

```text
如果 C组 相比 B组 没有提高关键问题召回率，说明经验库没有带来额外价值；
如果 C组 误报率显著升高，说明经验库噪声过大；
如果 C组 与 D组 效果接近，说明经验规则的行业/地区匹配没有发挥作用；
如果 C级规则大多数被专家否定，说明 C级只能作为人工关注项，不能自动判定。
```

---

## 12. 最终交付物

请最终生成以下文件：

```text
07_reports/data_manifest.md
07_reports/methodology_for_thesis.md
07_reports/review_workflow_mapping.md
04_experience_library/schemas/experience_pair_schema.json
04_experience_library/experience_pairs/experience_pairs_C2929.jsonl
05_skills/eia-review-experience-skill/SKILL.md
06_test_runs/shengzhiqiang_case/review_workflow_annotation.md
06_test_runs/shengzhiqiang_case/risk_attention_list.md
07_reports/evaluation_report.md
07_reports/final_summary.md
```

其中 `methodology_for_thesis.md` 必须能直接服务论文方法章节，建议结构如下：

```text
1. 数据来源与类型；
2. 文档解析与章节切分；
3. 环评报告结构化字段抽取；
4. 历史审核经验对构建；
5. 证据分级机制；
6. 经验库辅助审核流程；
7. 实验验证方案；
8. 局限性与人工复核机制。
```

---

## 13. 第一轮执行指令

请 Claude Code / OpenClaw 从以下任务开始：

```text
第一轮任务：建立工作区、复制文件、生成数据清单、初始化记忆文件。

具体要求：
1. 创建 eia_experience_review_project 目录结构；
2. 将现有文件按类型复制到 01_raw_data 对应目录；
3. 生成 07_reports/data_manifest.md，说明每个文件的数据类型和用途；
4. 初始化 00_memory/MEMORY.md、TASK_BOARD.md、ITERATION_LOG.md；
5. 不做最终结论，不生成经验规则，只完成项目初始化；
6. 在 ITERATION_LOG.md 记录本轮执行过程和下一轮任务。
```

---

## 14. 第二轮执行指令

```text
第二轮任务：解析盛之强报告，并模拟经办人审核流程标注。

具体要求：
1. 解析 终稿-佛山市盛之强电器有限公司建设项目.docx；
2. 输出项目画像 project_profile.json；
3. 按20步经办人审核流程生成 review_workflow_annotation.md；
4. 每一步必须包含：报告位置、抽取证据、经办人核查问题、是否需要经验库、是否需要人工复核；
5. 暂不判断项目是否合格，只输出审核关注路径；
6. 更新 ITERATION_LOG.md。
```

---

## 15. 第三轮执行指令

```text
第三轮任务：构建 C2929 塑料注塑类经验对。

具体要求：
1. 读取 experience_rules_A/B/C、industry_experience_base、final_experience_library_report；
2. 只聚焦 C2929 和塑料注塑类项目；
3. 将已有规则转成 experience_pair_schema；
4. 区分 A/B/C 证据等级；
5. 输出 experience_pairs_C2929.jsonl；
6. 标记哪些规则可自动判断，哪些只能人工关注；
7. 更新 RULE_CHANGELOG.md 和 ITERATION_LOG.md。
```

---

## 16. 第四轮执行指令

```text
第四轮任务：编写 eia-review-experience-skill。

具体要求：
1. 在 05_skills/eia-review-experience-skill/SKILL.md 生成 Skill；
2. Skill 必须按经办人审核流程执行；
3. Skill 必须能调用经验对、三线一单库、标准库；
4. Skill 必须输出风险问题清单、人工复核项、经验规则命中情况；
5. 不允许直接给通过/不通过结论；
6. 更新 ITERATION_LOG.md。
```

---

## 17. 第五轮执行指令

```text
第五轮任务：运行盛之强案例测试。

具体要求：
1. 使用 eia-review-experience-skill 对盛之强报告进行初审；
2. 输出 triggered_experience_rules.jsonl；
3. 输出 risk_attention_list.md；
4. 输出 calculation_check.json；
5. 输出 consistency_check.md；
6. 输出 human_review_needed.md；
7. 对照经办人审核流程，检查是否覆盖15个必须触发的审核关注项；
8. 更新 FAILURE_CASES.md 和 ITERATION_LOG.md。
```

---

## 18. 最终注意事项

本项目的论文表述必须保持克制：

```text
不要写：经验库可以自动完成环评审批。
应该写：经验库可以辅助低经验审核者识别高风险审核点。

不要写：模型判断报告是否合格。
应该写：模型按经办人审核流程生成问题关注清单。

不要写：历史经验都是规则。
应该写：历史经验按证据等级分为自动规则、强提示和人工关注项。

不要写：知识库越大越好。
应该写：经验库必须可追溯、可证伪、可迭代。
```

真正的研究价值是：

```text
把政府经办人的隐性审核经验，转化为可检索、可触发、可验证、可迭代的结构化经验知识。
```
