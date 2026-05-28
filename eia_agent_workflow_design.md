# 环评报告大模型辅助审核 Agent 工作流设计

Adapted from Chen et al. 2026 ES&T Agentic Workflow (Task Recognition → Tool Calling → Generation → Self-Reflection → Final Output).

---

## 0. 总体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    EIA Review Agent                         │
│                                                             │
│  Input: 新环评报告 + 批复文件（可选）                         │
│     │                                                       │
│     ▼                                                       │
│  Step 1: 行业识别 (Industry Classification)                 │
│     │                                                       │
│     ▼                                                       │
│  Step 2: 检索同行业历史案例 (Retrieve Similar Cases)        │
│     │                                                       │
│     ▼                                                       │
│  Step 3: 抽取高频规律 (Extract Common Patterns)             │
│     │   - 高频标准 | 高频污染因子 | 高频治理措施 | 批复要求  │
│     ▼                                                       │
│  Step 4: 对照审核 (Cross-Check New Report)                  │
│     │   - 标准对比 | 污染因子检查 | 措施完整性 | 批复对应   │
│     ▼                                                       │
│  Step 5: 自我反思 (Self-Reflection)                         │
│     │   - 证据检查 | 幻觉检查 | 完整性检查                  │
│     ▼                                                       │
│  Step 6: 评分 (LLM-as-a-Judge) [Optional]                   │
│     │                                                       │
│     ▼                                                       │
│  Output: 审核建议 + 风险点 + 依据 + 相似案例                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Step 1: 行业识别

### 输入
- 环评报告全文 (Markdown, 来自 MinerU 解析)
- GB/T 4754-2017 行业代码本

### 处理逻辑
1. 从报告 HTML 表格中提取"国民经济行业类别"字段（第一优先级）
2. 如无明确字段，从项目名称、产品方案、工艺描述、原辅材料推断（第二优先级）
3. 正则匹配: `C\d{4}` 或 `\d{4}` 格式行业代码
4. 匹配代码本获取行业全称

### 输出
```json
{
  "industry_code": "C2929",
  "industry_name": "塑料零件及其他塑料制品制造",
  "confidence": 0.95,
  "source": "explicit_field",
  "evidence": "报告原文: 国民经济行业类别 C2929塑料零件及其他塑料制品制造"
}
```

### 可能错误
- 代码本无对应条目 → 标记 UNKNOWN
- 多行业项目 → 取主行业
- HTML 解析失败 → 降级到文本搜索

### 质量控制
- confidence < 0.85 → 人工复核
- UNKNOWN → 进入 `needs_manual_review.csv`

---

## 2. Step 2: 检索同行业历史案例

### 输入
- 行业代码 (Step 1 输出)
- 项目索引 (`project_index.csv`)
- 行业规律库 (Phase 3 输出)

### 处理逻辑
1. 从 `project_index.csv` 按 industry_code 筛选同行业项目
2. 如果项目数 ≥ 5: 加载该行业的共通规律分析结果
3. 如果项目数 < 5: 上卷到大类（3-digit），扩大检索范围
4. 如果仍有不足: 提示样本不足，降级为纯标准驱动审核

### 输出
```json
{
  "industry_code": "C2929",
  "similar_project_count": 61,
  "pattern_available": true,
  "pattern_source": "outputs/eia_pair_commonality/C2929_塑料零件/industry_commonality_summary.md",
  "top_standards": ["GB31572-2015", "DB44/26-2001", ...],
  "top_pollutants": {"废气": ["VOCs", "非甲烷总烃", ...], "危废": ["废活性炭", ...]},
  "top_measures": {"废气": ["活性炭吸附", "集气罩收集", ...]},
  "review_rules": ["RULE_C2929_001", "RULE_C2929_002", ...]
}
```

### 可能错误
- 行业代码不规范 → 标准化到 4-digit
- 新旧代码本版本差异 → 仅使用 2017 版
- 大类比小类差异大 → 提示行业差异风险

### 质量控制
- 检索到的案例数 < 5 → 标记为"小样本行业"
- 大类和原始小类差异 > 30% → 提示信号

---

## 3. Step 3: 抽取高频规律

### 输入
- 同行业项目集合
- Phase 2 抽取结果: `report_extracted_facts.jsonl`
- Phase 3 分析结果: `industry_commonality_summary.md`
- 批复条件: `approval_extracted_conditions.jsonl`

### 处理逻辑
1. 加载该行业的共通标准（强共性 ≥80%、一般共性 60-80%）
2. 加载各环境要素的高频污染因子（≥60%）
3. 加载各环境要素的高频治理措施（≥60%）
4. 加载批复中高频出现的条件类型
5. 为每项规律附带 evidence（原文出处 + 出现频次）

### 输出
```json
{
  "common_standards": [
    {
      "code": "GB31572-2015",
      "ratio": 1.0,
      "level": "强共性",
      "evidence": "10/10 项目引用",
      "sample_projects": ["P0007", "P0033"]
    }
  ],
  "common_pollutants": {
    "废气": [
      {"name": "VOCs", "ratio": 1.0, "evidence": "10/10"},
      {"name": "非甲烷总烃", "ratio": 1.0, "evidence": "10/10"}
    ]
  },
  "common_measures": {
    "废气": [
      {"name": "活性炭吸附", "ratio": 1.0},
      {"name": "集气罩收集", "ratio": 1.0}
    ]
  },
  "common_approval_requirements": [
    {"type": "危废", "content": "危废须规范暂存并委托有资质单位处置", "ratio": 1.0}
  ]
}
```

### 可能错误
- 从错误行业加载了规律 → 核对行业代码
- 频率统计受样本量影响 → 提供置信区间

### 质量控制
- 所有规律附带频次和样本量
- < 5 个项目的行业规则标注"小样本，仅供参考"

---

## 4. Step 4: 对照审核

### 输入
- 新报告的全部抽取结果
- 同行业高频规律 (Step 3 输出)
- 批复要求（如有）
- 标准文件摘要

### 处理逻辑
1. **标准对比**: 新报告引用的标准与行业高频标准对比，标记缺失的标准
2. **污染因子检查**: 按环境要素逐一检查新报告是否覆盖了行业高频污染因子
3. **措施完整性**: 检查新报告中的治理措施是否与行业高频措施一致
4. **批复对应**: 如果提供了批复，检查报告是否回应了批复中的每项要求
5. **数值一致性**: 检查报告中污染物排放浓度是否在标准限值内

### 输出
```json
{
  "missing_standards": [
    {"code": "GB14554-93", "reason": "行业100%引用，新报告未引用，可能遗漏臭气浓度标准"}
  ],
  "missing_pollutants": [
    {"element": "废气", "pollutant": "臭气浓度", "industry_ratio": 1.0}
  ],
  "insufficient_measures": [
    {"element": "废气", "report_measure": "活性炭吸附", "industry_common": "二级活性炭吸附", "gap": "未明确活性炭级数"}
  ],
  "approval_gaps": [
    {"approval_item": "排污许可证申领", "report_status": "完全缺失"}
  ],
  "risk_points": [
    {"level": "HIGH", "description": "缺少排污许可/环保验收相关说明，可能导致审批不通过"}
  ]
}
```

### 可能错误
- 行业规律不适应该项目 → 检查项目特殊性声明
- 误报缺失 → 检查是否因报告类型不同（报告书 vs 报告表）

### 质量控制
- 每个缺失标记附带行业出现频率
- 区分 "必须关注" (强共性缺失) 和 "建议关注" (一般共性缺失)

---

## 5. Step 5: 自我反思 (Self-Reflection)

仿照论文中 Agent 的自我反思环节。

### 输入
- Step 4 的审核建议
- 原始报告文本
- 行业规律原文证据

### 检查项

| 检查项 | 检查方法 | 如果不通过 |
|--------|---------|-----------|
| 证据扎根检查 | 每条建议是否有报告/批复/标准原文支撑 | 标记 unsupported_claims |
| 幻觉检查 | 是否编造了不存在的标准编号、公司名、数值 | 回到 Step 4 重新生成 |
| 完整性检查 | 是否覆盖了所有环境要素 | 补充遗漏要素 |
| 逻辑一致性 | 前后结论是否矛盾 | 修正矛盾 |
| 行业特殊性 | 项目是否有不同于行业典型情况的特征 | 调整建议优先级 |

### 输出
```json
{
  "reflection_passed": true,
  "evidence_check": {"total_claims": 15, "supported": 13, "unsupported": 2},
  "unsupported_claims": [
    {"claim": "项目应采用RTO燃烧处理", "reason": "报告中未提及RTO，行业规律中也未出现RTO"}
  ],
  "hallucination_check": {"hallucinated_items": 0},
  "completeness_check": {"elements_covered": 5, "elements_missed": ["土壤地下水"]},
  "revised": true,
  "revision_summary": "移除RTO建议，补充土壤地下水防渗检查"
}
```

### 可能错误
- 过度自信 → 即使证据不足也判定通过
- 误判幻觉 → 原文中确实存在但模型没找到

### 质量控制
- 自我反思失败的 case 标记 `need_human_review = true`
- 反思结果记录到日志

---

## 6. Step 6: 评分 (LLM-as-a-Judge) [Optional]

### 触发条件
- 配置了 LLM API key
- 评估模型可用

### 输入
- Step 4 的审核建议
- 参考答案（如有）
- 源证据

### 处理逻辑
使用 `prompts/eia_llm_judge_prompt.md` 中的评分 prompt，调用 LLM 评估器对审核建议评分。

### 输出
符合 `schemas/eia_judge_schema.json` 的 JSON 评估结果。

---

## 7. 最终输出格式

```json
{
  "report_id": "P0007",
  "report_name": "广东爱初达城婴童用品有限公司新建项目",
  "industry": {"code": "C2929", "name": "塑料零件及其他塑料制品制造"},
  "review_timestamp": "2026-05-28T12:00:00",
  "review_summary": {
    "overall_assessment": "基本合规，存在3项需补充的内容",
    "risk_level": "中",
    "key_issues_count": 3,
    "suggestion_count": 5
  },
  "industry_context": {
    "similar_cases_count": 61,
    "pattern_confidence": "高"
  },
  "findings": {
    "missing_standards": [...],
    "missing_pollutants": [...],
    "insufficient_measures": [...],
    "approval_gaps": [...]
  },
  "risk_points": [...],
  "suggestions": [...],
  "evidence_citations": [...],
  "similar_cases": ["P0033", "P0049", "P0052"],
  "self_reflection": {...},
  "evaluation": {...},
  "human_review_required": false,
  "review_priority": "低"
}
```

---

## 8. 目录结构与文件清单

```
E:\软件\
├── prompts/
│   └── eia_llm_judge_prompt.md          # 评分 prompt
├── schemas/
│   ├── eia_judge_schema.json             # 评分输出 schema
│   └── eia_benchmark_schema.json         # 测试集 schema
├── scripts/
│   └── paper_transfer/
│       ├── run_eia_judge_eval.py          # 评分脚本
│       └── statistical_validation.py      # 统计验证脚本
├── evaluation/
│   ├── sample_eia_eval_set.jsonl          # 样例评估数据
│   ├── eia_judge_results.jsonl            # 评估结果（脚本生成）
│   ├── eia_judge_summary.csv              # 评估汇总（脚本生成）
│   └── statistical_validation_demo.md     # 统计验证演示
├── outputs/
│   ├── eia_industry_pattern/              # 全量行业模式分析
│   ├── eia_pair_commonality/              # C2929 配对深度分析
│   └── paper_reproduction/
│       ├── paper_transfer_notes.md        # 论文迁移笔记
│       ├── eia_benchmark_design.md        # 测试集框架设计
│       ├── eia_error_case_analysis_template.md  # 错误分析模板
│       ├── eia_agent_workflow_design.md   # 本文件
│       └── final_summary.md               # 最终总结
```

---

## 9. 后续扩展方向

### 短期（可立即执行）
- 基于 5 条样本运行 mock 评估，验证评分 prompt 可用性
- 对 C3360（金属表面处理，19 项目）运行相同分析管线
- 合并 C2929/C2922/C2926/C2921 为"塑料大类"做跨小类对比

### 中期（需要更多数据）
- 扩展到全部 7 个 ≥5 项目的行业
- 建立 Neo4j 知识图谱，导入全部行业规律和三元组
- 设计 A/B 测试：案例驱动 vs 纯标准驱动审核

### 长期（需要外部资源）
- 接入真实 LLM API 运行完整 Agent 工作流
- 构建自动化标注+人工复核闭环
- 多模型对比实验（GPT-4 vs Claude vs 微调模型）
- 发表方法论论文

---

*生成时间: 2026-05-28*
*参考: Chen et al. 2026, ES&T, Agentic Workflow Design*
