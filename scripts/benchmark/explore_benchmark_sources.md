# Benchmark 数据源探索 — 查询逻辑记录

> 当前数据为文件系统 + 结构化JSON，非SQL数据库。
> 以下记录探索中使用的文件过滤和聚合逻辑，等价于SQL查询。

---

## "表"结构定义

### audit_packages (30行)
```sql
-- 等价于: 从 ai_packages 目录读取所有 manifest.json
SELECT doc_id, comment_count, table_count, figure_count
FROM audit_packages
WHERE comment_count > 0;
```

### comments (502行)
```sql
-- 等价于: 从所有 comments.jsonl 汇总
SELECT c.comment_id, c.comment_text, p.doc_id
FROM comments c
JOIN audit_packages p ON c.doc_id = p.doc_id;
```

### clean_pairs (85行)
```sql
-- 等价于: 从 clean_pairs 目录读取所有 pair_metadata.json
SELECT pair_id, company_name, project_name, match_score, report_path, approval_path
FROM clean_pairs
WHERE has_report = true AND has_approval = true;
```

---

## 探索查询

### Q1: 筛选C2929塑料注塑类且有VOCs治理的项目
```sql
SELECT doc_id, comment_count
FROM audit_packages
WHERE body_text LIKE '%C2929%'
  AND body_text LIKE '%注塑%'
  AND body_text LIKE '%活性炭%'
  AND body_text LIKE '%非甲烷总烃%'
  AND comment_count >= 5;
-- 结果: 6个项目
```

### Q2: 统计各行业的批注数量分布
```sql
SELECT
  CASE
    WHEN body_text LIKE '%C2929%' THEN 'C2929塑料零件'
    WHEN body_text LIKE '%塑料%' THEN '塑料制品业'
    WHEN body_text LIKE '%五金%' OR body_text LIKE '%金属%' THEN '金属制品业'
    WHEN body_text LIKE '%涂料%' OR body_text LIKE '%化工%' THEN '化工'
    ELSE '其他'
  END AS industry_group,
  COUNT(*) AS project_count,
  SUM(comment_count) AS total_comments
FROM audit_packages
GROUP BY industry_group
ORDER BY total_comments DESC;
```

### Q3: 查找有多个版本的同一项目
```sql
-- 等价于: 按项目名相似度匹配
SELECT
  SUBSTRING(doc_id, 1, 30) AS base_name,
  COUNT(*) AS version_count,
  GROUP_CONCAT(doc_id) AS versions
FROM audit_packages
GROUP BY base_name
HAVING COUNT(*) > 1;
-- 结果: 启卓塑料(2版本), 百洛电器(2版本)
```

### Q4: 构建 version_diff benchmark 的候选
```sql
SELECT a1.doc_id AS pre_revision, a2.doc_id AS post_revision
FROM audit_packages a1
JOIN audit_packages a2
  ON a1.base_name = a2.base_name
WHERE a1.doc_id < a2.doc_id
  AND a1.comment_count > 0;
```

---

## 实际执行方式

由于数据不在SQL数据库中，使用以下等价方式:

```bash
# Q1: 筛选C2929项目
grep -l "C2929" ai_packages/*/body.md | wc -l

# Q2: 统计批注总数
python -c "sum json.load(open(f))['comment_count'] for f in glob('ai_packages/*/manifest.json')"

# Q3: 找多版本项目
ls ai_packages/ | sed 's/(修改意见).*//' | sort | uniq -c | sort -rn | head -10

# Q4: 提取C2929批注文本
python extract_candidate_benchmark_sources.py --filter-c2929 --output comments_c2929.jsonl
```
