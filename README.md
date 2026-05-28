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

## 参考

- Chen et al. (2026). *Leveraging LLMs for Environmental Complexity: Structured Fine-Tuning Data Sets and Deployment Strategies*. Environmental Science & Technology. DOI: [10.1021/acs.est.5c09526](https://doi.org/10.1021/acs.est.5c09526)
