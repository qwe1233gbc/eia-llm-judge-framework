# EIA Review LLM-as-a-Judge Evaluation Framework

基于 [Chen et al. 2026, ES&T](https://doi.org/10.1021/acs.est.5c09526) 论文方法迁移的环评报告大模型辅助审核评估框架。

## 文件说明

| 文件 | 类型 | 说明 |
|------|------|------|
| `eia_llm_judge_prompt.md` | Prompt | LLM-as-a-Judge 评分 Prompt（7维度 10-100分） |
| `eia_judge_schema.json` | Schema | 评分输出 JSON Schema |
| `eia_benchmark_schema.json` | Schema | 测试集四维分类 Schema |
| `sample_eia_eval_set.jsonl` | 数据 | 5 条 C2929 塑料零件行业测试样本 |
| `run_eia_judge_eval.py` | 脚本 | 评估脚本（mock + 真实 API 预留） |
| `statistical_validation.py` | 脚本 | 统计验证脚本（Bootstrap CI / t-test / Wilcoxon / Cohen's d） |
| `eia_judge_results.jsonl` | 结果 | Mock 评估结果 |
| `eia_judge_summary.csv` | 结果 | 评估维度汇总 |
| `statistical_validation_demo.md` | 报告 | 统计验证演示报告 |
| `statistical_validation_demo.csv` | 数据 | 统计验证数据 |
| `paper_transfer_notes.md` | 文档 | 论文方法迁移笔记 |
| `eia_benchmark_design.md` | 文档 | 测试集框架设计 |
| `eia_error_case_analysis_template.md` | 文档 | 错误案例分析模板（12种错误类型） |
| `eia_agent_workflow_design.md` | 文档 | Agent 工作流设计（6步审核流程） |
| `final_summary.md` | 文档 | 最终总结 |
| `data/qa_pairs/qa_batch_full.json` | 数据 | 区级（顺德）419条 QA 对（五维分类） |
| `data/qa_pairs/foshan_qa.json` | 数据 | 市级（佛山）149条 QA 对 |
| `prompts/eia_review_expert_prompt.md` | Prompt | **环评审核专家智能体 System Prompt** |

### 五维分类体系

每条 QA 对含五维标签：

| 维度 | 字段 | 说明 |
|------|------|------|
| ① 层级 | `level` | 区级 / 市级 |
| ② 行业 | `industry_code` | C2929 / C3360 / ... |
| ③ 要素 | `element` | 废水/废气/噪声/固废/危废 |
| ④ 项目类型 | `project_type` | 新建/扩建/迁建/技改 |
| ⑤ 审核要点 | `review_point_primary` | 生态部第14号令十一项审查要点 RP01-RP11 |

## 使用方法

```bash
# Mock 评估（无需 API）
python run_eia_judge_eval.py

# 统计验证
python statistical_validation.py

# 真实 API 评估（需配置 .env 文件）
# OPENAI_API_KEY=sk-xxx 或 ANTHROPIC_API_KEY=sk-ant-xxx
python run_eia_judge_eval.py
```

## ELLE-inspired EIA Benchmark Construction

基于 [ELLE-QA Benchmark](https://github.com/CEEAI/elle) (Guo et al., 2024) 数据集构建方法论迁移的环评审核评测基准构造框架。

### 设计理念

ELLE-QA 是生态与环境科学领域首个 LLM 评估基准数据集（1,130 QA pairs, 16 环境学科, 3 难度等级, 3 问题类型）。本框架将其方法论迁移至环评报告审核领域，并根据环评审核的实际需求进行了扩展：

| 维度 | ELLE-QA | EIA-Review-Benchmark |
|------|---------|---------------------|
| 领域分类 | 16 环境学科 | 14 环评审核任务域 |
| 难度等级 | Simple/Medium/Hard | Simple/Medium/Hard（环评特定定义） |
| 问题类型 | Knowledge/Calculation/Reasoning | + Extraction/Matching/Evaluation（6 类） |
| 评估维度 | Professionalism/Clarity/Feasibility | + Evidence Grounding（4 维度） |
| 数据来源 | 专家问卷 + 教材/考试 | 真实环评报告 + 批复文件 + 国家标准 |
| 验证方式 | 3 轮专家交叉审查 | 证据溯源验证 + 专家审查兜底 |
| 核心创新 | — | **证据可追溯性**（每条结论必须链接到源文本） |

### 文件结构

```
eia-llm-judge-framework/
├── schemas/
│   ├── eia_benchmark_sample_schema.json   # 单条样本 JSON Schema
│   └── eia_benchmark_taxonomy.yaml        # 分类体系（任务域/难度/问题类型/评估维度）
├── data/
│   └── sample_eia_benchmark.jsonl         # 10 条示例样本（覆盖全部 6 种问题类型）
├── scripts/
│   └── build_eia_benchmark_dataset.py     # 数据集构建脚本
├── docs/
│   ├── eia_benchmark_construction_plan.md  # 基准构造计划
│   └── papers/
│       └── ELLE_dataset_construction_notes.md  # ELLE 论文学习笔记
└── outputs/
    └── elle_dataset_transfer/
        ├── final_summary.md               # 迁移工作总结
        └── generation_summary.json         # 生成统计
```

### 使用方法

```bash
# 生成基准候选样本
python scripts/build_eia_benchmark_dataset.py

# 按行业筛选
python scripts/build_eia_benchmark_dataset.py --industry C2929

# 按难度和问题类型筛选
python scripts/build_eia_benchmark_dataset.py --difficulty medium --question-type matching

# 按任务域筛选
python scripts/build_eia_benchmark_dataset.py --task-domain 废气 --max-samples 20

# 干跑验证（不写文件）
python scripts/build_eia_benchmark_dataset.py --dry-run
```

### 14 个环评审核任务域

| # | 任务域 | 说明 |
|---|--------|------|
| 1 | 行业识别 | GB/T 4754-2017 行业代码与名称识别 |
| 2 | 标准引用 | 国家标准、地方标准、行业标准提取与校验 |
| 3 | 废水 | 废水污染物、治理措施、排放标准 |
| 4 | 废气 | 废气排放源、污染物 (VOCs/颗粒物/SO2/NOx)、治理技术 |
| 5 | 噪声 | 噪声源、预测值、控制措施 (GB12348-2008) |
| 6 | 固废 | 一般工业固废产生、贮存、处置 |
| 7 | 危废 | 危险废物分类 (HW 代码)、贮存要求、处置资质 |
| 8 | 环境风险 | 风险源识别、事故情景分析、应急预案 |
| 9 | 排污许可 | 许可排放量、监测要求、合规报告 |
| 10 | 总量控制 | COD/NH3-N/SO2/NOx/VOCs 总量指标 |
| 11 | 竣工环保验收 | 验收条件与程序 |
| 12 | 重大变动 | 项目变更是否构成重大变动的判定 |
| 13 | 报告-批复对应 | 报告内容与批复条件的交叉比对 |
| 14 | 行业经验归纳 | 跨项目审核模式与规则归纳 |

### 4 维度评估体系

| 维度 | 权重 | 说明 |
|------|------|------|
| Professionalism (专业性) | 35% | 行业判断、标准引用、污染-治理逻辑 |
| Evidence Grounding (证据可追溯性) | 30% | 每条结论必须可追溯到源文本 |
| Feasibility (可行性) | 20% | 审核建议可转化为实际修改意见 |
| Clarity (清晰性) | 15% | 输出结构清晰，审核人员可快速定位问题 |

### 构造阶段

| 阶段 | 状态 | 产出 |
|------|------|------|
| Phase 1: 框架设计 | ✅ 完成 | Schema, Taxonomy, 10 示例样本, Builder 脚本骨架 |
| Phase 2: 自动生成 | 待启动 | 500+ 自动生成和验证的样本 |
| Phase 3: 专家标注 | 待启动 | 200+ 专家验证样本 |
| Phase 4: 基准发布 | 待启动 | Train/Dev/Test 划分, 排行榜 |

## 参考

- Chen et al. (2026). *Leveraging LLMs for Environmental Complexity: Structured Fine-Tuning Data Sets and Deployment Strategies*. Environmental Science & Technology. DOI: [10.1021/acs.est.5c09526](https://doi.org/10.1021/acs.est.5c09526)
- Guo et al. (2024). *Environmental large language model Evaluation (ELLE) dataset: A Benchmark for Evaluating Generative AI applications in Eco-environment Domain*. [ELLE GitHub](https://github.com/CEEAI/elle)
