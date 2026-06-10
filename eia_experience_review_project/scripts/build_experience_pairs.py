#!/usr/bin/env python3
"""Build C2929 experience pairs from existing rules + Round 2 findings."""

import json, os

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJ, "04_experience_library", "source_rules")
OUT = os.path.join(PROJ, "04_experience_library", "experience_pairs")
SCHEMA = os.path.join(PROJ, "04_experience_library", "schemas")

# Load existing rules
all_rules = []
for level, fname in [
    ("A", "experience_rules_A_verified.json"),
    ("B", "experience_rules_B_candidate.json"),
    ("C", "experience_rules_C_observation.json"),
]:
    with open(os.path.join(SRC, fname), "r", encoding="utf-8") as f:
        data = json.load(f)
    for r in data:
        if "C2929" in r.get("industry_code", ""):
            r["_source_level"] = level
            all_rules.append(r)

print(f"Existing C2929 rules: {len(all_rules)}")

# Convert existing rules to experience_pair schema
pairs = []
for r in all_rules:
    element = r.get("element", "")
    level = r["_source_level"]
    conf = r.get("confidence", 0)

    if level == "A" and conf >= 0.8:
        auto = "auto_rule"
    elif level in ("A", "B"):
        auto = "strong_hint"
    else:
        auto = "human_attention"

    features = ["C2929", "塑料零件制造"]
    if element == "废气":
        features.extend(["VOCs排放", "活性炭吸附"])
    if element == "废水":
        features.append("生活污水")
    if element == "危废":
        features.extend(["废矿物油", "废活性炭"])

    pair = {
        "experience_id": f"EXP_{r['rule_id']}",
        "industry_code": "C2929",
        "industry_name": "塑料零件及其他塑料制品制造",
        "project_features": list(set(features)),
        "trigger_condition": r.get("trigger_condition", []),
        "review_module": element,
        "review_checkpoints": r.get("review_checkpoints", []),
        "evidence_source_type": (
            ["地方规范", "历史批复", "终审报告"] if level == "A"
            else ["历史批复", "终审报告"] if level == "B"
            else ["终审报告"]
        ),
        "evidence_source_file": [],
        "evidence_level": level,
        "automation_level": auto,
        "failure_risk": [],
        "suggested_comment_template": "",
        "_confidence": conf,
        "_source": f"existing_rule_{level}",
    }
    pairs.append(pair)

# Add 6 new rules from Round 2 findings
new_rules = [
    {
        "experience_id": "EXP_C2929_SPATIAL_001",
        "industry_code": "C2929",
        "industry_name": "塑料零件及其他塑料制品制造",
        "project_features": ["C2929", "新建", "顺德区"],
        "trigger_condition": [
            "项目位于顺德区",
            "项目为报告表类",
        ],
        "review_module": "三线一单空间管控",
        "review_checkpoints": [
            "管控单元编号是否正确",
            "是否逐条对应管控单元的具体管控要求（不仅是三线层面）",
            "产业限制类条款（如1-3）是否逐一分析",
            "大气限制类条款（如1-4）是否逐一分析",
            "污染物排放管控条款（如3-7）是否逐一分析",
        ],
        "evidence_source_type": ["地方规范"],
        "evidence_source_file": [
            "#4_三线一单_顺德管控单元准入清单.md",
            "佛环(2024)20号",
        ],
        "evidence_level": "A",
        "automation_level": "strong_hint",
        "failure_risk": [
            "管控单元错误",
            "遗漏限制类条款",
            "仅做三线层面分析未逐条对照",
        ],
        "suggested_comment_template": "请逐条对照项目所在管控单元(ZH44060620002)的区域布局管控、污染物排放管控和环境风险防控要求，补充逐条符合性分析。",
        "_confidence": 0.9,
        "_source": "round2_finding_F05",
    },
    {
        "experience_id": "EXP_C2929_AIR_002",
        "industry_code": "C2929",
        "industry_name": "塑料零件及其他塑料制品制造",
        "project_features": ["C2929", "注塑", "VOCs排放", "顺德区"],
        "trigger_condition": [
            "项目位于大气不达标区",
            "项目新增VOCs排放",
        ],
        "review_module": "废气源强与总量控制",
        "review_checkpoints": [
            "是否引用最新环境质量公报",
            "是否说明大气不达标因子（当前为O3）",
            "是否提出区域削减替代方案",
            "VOCs新增量是否满足替代比例要求",
        ],
        "evidence_source_type": ["地方规范", "历史批复"],
        "evidence_source_file": [
            "顺环委办(2023)19号",
            "顺德区VOCs总量管理方案",
        ],
        "evidence_level": "A",
        "automation_level": "strong_hint",
        "failure_risk": [
            "未提出削减替代方案",
            "替代比例不满足1:2要求",
            "替代来源不在顺德区内",
        ],
        "suggested_comment_template": "项目所在区域为大气不达标区(O3超标)，请说明本项目新增VOCs排放的区域削减替代方案，明确替代来源、替代量和替代比例。",
        "_confidence": 0.9,
        "_source": "round2_finding_F06",
    },
    {
        "experience_id": "EXP_C2929_MATBAL_001",
        "industry_code": "C2929",
        "industry_name": "塑料零件及其他塑料制品制造",
        "project_features": ["C2929", "注塑", "新建"],
        "trigger_condition": [
            "报告表包含产品方案和设备清单",
            "报告表包含原辅材料表",
        ],
        "review_module": "产能与物料平衡",
        "review_checkpoints": [
            "原料年用量是否完整列出",
            "产品产量+边角料+次品=原料用量是否闭合",
            "边角料比例是否在行业典型值范围内（注塑3-5%）",
            "设备理论产能是否与实际产量匹配",
            "破碎回用量是否单独统计",
        ],
        "evidence_source_type": ["终审报告", "行业技术文件"],
        "evidence_source_file": [],
        "evidence_level": "B",
        "automation_level": "strong_hint",
        "failure_risk": [
            "原料用量缺失",
            "边角料比例异常（>8%）",
            "产能-原料-产品不闭合",
        ],
        "suggested_comment_template": "请补充各类塑料原料的年用量，并核算产品产量+边角料+次品是否与原料总用量闭合。当前边角料比例偏高，请说明原因。",
        "_confidence": 0.7,
        "_source": "round2_finding_F01",
    },
    {
        "experience_id": "EXP_C2929_PROC_003",
        "industry_code": "C2929",
        "industry_name": "塑料零件及其他塑料制品制造",
        "project_features": ["C2929", "注塑", "模具维修", "机加工"],
        "trigger_condition": [
            "报告设备清单包含磨床/铣床/车床等机加工设备",
            "报告存在模具维修工序",
        ],
        "review_module": "危废识别",
        "review_checkpoints": [
            "模具维修是否使用切削液/冷却液",
            "废切削液是否列入危废清单（HW09 900-006-09）",
            "废切削液产生量是否核算",
            "金属边角料是否识别",
            "含油金属屑是否识别",
        ],
        "evidence_source_type": ["终审报告", "历史批复", "专家经验"],
        "evidence_source_file": ["国家危险废物名录(2025年版)"],
        "evidence_level": "A",
        "automation_level": "auto_rule",
        "failure_risk": [
            "遗漏废切削液",
            "遗漏含油金属屑",
            "危废代码错误",
        ],
        "suggested_comment_template": "模具维修工序使用切削液，应识别废切削液(HW09 900-006-09)并核算产生量，委托有资质单位处置。",
        "_confidence": 0.95,
        "_source": "round2_finding_F02",
    },
    {
        "experience_id": "EXP_C2929_WW_001",
        "industry_code": "C2929",
        "industry_name": "塑料零件及其他塑料制品制造",
        "project_features": ["C2929", "注塑", "间接冷却水"],
        "trigger_condition": [
            "报告存在注塑冷却工序",
            "报告将间接冷却水排入雨水管网",
        ],
        "review_module": "废水排放去向",
        "review_checkpoints": [
            "冷却水是否仅用于间接冷却（不与产品/原料接触）",
            "冷却水排水是否含有添加剂（阻垢剂/杀菌剂等）",
            "排入雨水管网是否符合顺德区现行口径",
            "是否取得排水许可证",
        ],
        "evidence_source_type": ["地方规范", "专家经验"],
        "evidence_source_file": [],
        "evidence_level": "B",
        "automation_level": "strong_hint",
        "failure_risk": [
            "冷却水含添加剂排雨水",
            "地方口径不允许",
            "排水证过期",
        ],
        "suggested_comment_template": "间接冷却水排入雨水管网需确认符合顺德区现行管理口径。如冷却水中含有阻垢剂、杀菌剂等添加剂，应作为生产废水处理。",
        "_confidence": 0.7,
        "_source": "round2_finding_F08",
    },
    {
        "experience_id": "EXP_C2929_AC_001",
        "industry_code": "C2929",
        "industry_name": "塑料零件及其他塑料制品制造",
        "project_features": ["C2929", "注塑", "活性炭吸附", "VOCs治理"],
        "trigger_condition": [
            "报告废气治理采用活性炭吸附",
            "报告位于顺德区",
        ],
        "review_module": "活性炭治理设施参数",
        "review_checkpoints": [
            "活性炭类型是否明确（蜂窝炭/柱状炭）",
            "碘值是否>=800mg/g（佛环函(2024)70号要求）",
            "过滤风速是否<=0.6m/s（蜂窝炭）/<=0.4m/s（柱状炭）",
            "停留时间是否>=0.5s",
            "年用炭量是否核算",
            "废活性炭产生量是否=年用炭量+吸附量",
            "更换周期是否明确",
            "过滤风速或停留时间接近边界值时是否标注风险",
        ],
        "evidence_source_type": ["地方规范", "专家经验", "历史批复"],
        "evidence_source_file": ["佛环函(2024)70号"],
        "evidence_level": "A",
        "automation_level": "auto_rule",
        "failure_risk": [
            "碘值不满足>=800",
            "过滤风速超标",
            "停留时间不足",
            "参数接近边界未标注",
            "废活性炭量核算错误",
        ],
        "suggested_comment_template": "请明确活性炭类型和碘值(应>=800mg/g)，并核实过滤风速和停留时间满足佛环函(2024)70号要求。当前参数接近边界值，建议提高设计余量。",
        "_confidence": 0.95,
        "_source": "round2_finding_F03",
    },
]

pairs.extend(new_rules)

# Save JSONL
os.makedirs(OUT, exist_ok=True)
jsonl_path = os.path.join(OUT, "experience_pairs_C2929.jsonl")
with open(jsonl_path, "w", encoding="utf-8") as f:
    for p in pairs:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

# Save schema
os.makedirs(SCHEMA, exist_ok=True)
schema = {
    "name": "experience_pair_schema",
    "version": "1.0",
    "description": "环评审核经验对schema - 用于C2929塑料注塑类报告表",
    "fields": {
        "experience_id": "规则唯一标识, 格式: EXP_{industry}_{module}_{seq}",
        "industry_code": "国民经济行业分类代码",
        "industry_name": "行业名称",
        "project_features": "项目特征标签列表",
        "trigger_condition": "触发条件列表 - 当报告满足这些条件时触发该规则",
        "review_module": "审核模块名称",
        "review_checkpoints": "审核检查点列表",
        "evidence_source_type": "证据来源类型列表",
        "evidence_source_file": "证据来源文件列表",
        "evidence_level": "证据等级: A/B/C",
        "automation_level": "自动化等级: auto_rule/strong_hint/human_attention",
        "failure_risk": "常见失败模式列表",
        "suggested_comment_template": "建议修改意见模板",
    },
}
with open(os.path.join(SCHEMA, "experience_pair_schema.json"), "w", encoding="utf-8") as f:
    json.dump(schema, f, ensure_ascii=False, indent=2)

# Count
a_count = sum(1 for p in pairs if p["evidence_level"] == "A")
b_count = sum(1 for p in pairs if p["evidence_level"] == "B")
c_count = sum(1 for p in pairs if p["evidence_level"] == "C")
auto_count = sum(1 for p in pairs if p["automation_level"] == "auto_rule")
hint_count = sum(1 for p in pairs if p["automation_level"] == "strong_hint")
attn_count = sum(1 for p in pairs if p["automation_level"] == "human_attention")

print()
print(f"Total C2929 experience pairs: {len(pairs)}")
print(f"  Converted existing: {len(pairs) - 6}")
print(f"  New from Round 2: 6")
print()
print(f"Evidence level: A={a_count}, B={b_count}, C={c_count}")
print(f"Automation: auto_rule={auto_count}, strong_hint={hint_count}, human_attention={attn_count}")
print()
print("Outputs:")
print(f"  {jsonl_path}")
print(f"  {os.path.join(SCHEMA, 'experience_pair_schema.json')}")
