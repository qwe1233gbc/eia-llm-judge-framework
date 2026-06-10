qa_v4 清洗完成：

输入 qa_v3 样本数: 963
qa_v4_verified: 193
qa_v4_needs_human_review: 272
qa_v4_rejected: 498

主要问题：
- 项目/批复错配: 428
- question 与 element 不一致: 963
- standards 缺失: 73
- evidence_alignment low/none: 549

ELLE-style benchmark 分布：
- task_domain:
  - 废气: 290
  - 废水: 180
  - 噪声: 180
  - 危废: 130
  - 固废: 128
  - 综合审核: 48
  - 总量控制: 7
- difficulty:
  - medium: 692
  - simple: 271
- question_type:
  - extraction: 914
  - reasoning: 42
  - calculation: 7
- cognitive_level:
  - L1_fact: 914
  - L3_review_reasoning: 42
  - L2_alignment: 7
