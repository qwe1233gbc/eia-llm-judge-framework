# -*- coding: utf-8 -*-
"""
给 QA 对添加第5维度：审核要点
基于关键词规则将每条 QA 对映射到生态环境部第14号令十一项审查要点
"""
import sys, os, json, re
sys.stdout.reconfigure(encoding='utf-8')

# 十一项审查要点及其关键词规则
REVIEW_POINTS = [
    {
        "id": "RP01",
        "name": "产业政策与规划相符性",
        "keywords": ["产业政策", "规划环评", "相符性", "选址", "布局", "生态保护红线", "三线一单", "准入"]
    },
    {
        "id": "RP02",
        "name": "区域环境质量",
        "keywords": ["环境质量", "功能区划", "达标区", "不达标区", "环境容量", "现状监测", "本底值"]
    },
    {
        "id": "RP03",
        "name": "污染防治措施",
        "keywords": ["污染防治", "治理措施", "处理工艺", "排放标准", "废气处理", "废水处理", "固废处置",
                     "噪声防治", "除尘", "吸附", "脱硝", "脱硫", "污水处理", "排气筒", "排放浓度",
                     "执行.*标准", "GB[123]"]
    },
    {
        "id": "RP04",
        "name": "生态保护措施",
        "keywords": ["生态保护", "生态修复", "敏感区", "生态影响", "植被", "水土保持", "绿化"]
    },
    {
        "id": "RP05",
        "name": "改建扩建以新带老",
        "keywords": ["以新带老", "改建", "技术改造", "原有污染", "淘汰", "搬迁"]
    },
    {
        "id": "RP06",
        "name": "振动和电磁污染",
        "keywords": ["振动", "电磁", "电磁辐射", "工频", "射频"]
    },
    {
        "id": "RP07",
        "name": "公众参与",
        "keywords": ["公众参与", "信息公开", "公众意见", "公示", "听证"]
    },
    {
        "id": "RP08",
        "name": "环境风险防范",
        "keywords": ["环境风险", "应急预案", "风险防范", "泄漏", "事故", "应急池", "风险管理"]
    },
    {
        "id": "RP09",
        "name": "总量控制指标",
        "keywords": ["总量控制", "排放总量", "总量指标", "污染物排放总量", "控制指标"]
    },
    {
        "id": "RP10",
        "name": "评价因子完整性",
        "keywords": ["评价因子", "污染因子", "遗漏", "源强核算", "污染源"]
    },
    {
        "id": "RP11",
        "name": "预测评价方法",
        "keywords": ["预测", "评价方法", "预测模型", "估算", "计算", "模式", "数学模型"]
    },
]

# Element → 默认关联的审核要点
ELEMENT_TO_RP = {
    "废水": "RP03",
    "废气": "RP03",
    "噪声": "RP03",
    "固废": "RP03",
    "危废": "RP03",
    "振动": "RP06",
    "电磁": "RP06",
}

# Project type → 关联的审核要点
PROJECT_TYPE_TO_RP = {
    "扩建": "RP05",
    "迁建": "RP05",
    "技改": "RP05",
}


def classify_review_point(qa):
    """对单条 QA 对进行分类，返回匹配的审核要点列表"""
    text = (qa.get("question", "") + " " + qa.get("answer", "") + " " +
            " ".join(qa.get("standards", [])))
    text = text.lower()
    matched = []

    # 1. 项目类型匹配
    pt = qa.get("project_type", "")
    if pt in PROJECT_TYPE_TO_RP:
        rp_id = PROJECT_TYPE_TO_RP[pt]
        for rp in REVIEW_POINTS:
            if rp["id"] == rp_id and rp not in matched:
                matched.append((rp["id"], rp["name"]))
                break

    # 2. 要素匹配
    elem = qa.get("element", "")
    if elem in ELEMENT_TO_RP:
        rp_id = ELEMENT_TO_RP[elem]
        for rp in REVIEW_POINTS:
            if rp["id"] == rp_id and (rp["id"], rp["name"]) not in matched:
                matched.append((rp["id"], rp["name"]))
                break

    # 3. 关键词匹配
    for rp in REVIEW_POINTS:
        for kw in rp["keywords"]:
            if re.search(kw, text):
                if (rp["id"], rp["name"]) not in matched:
                    matched.append((rp["id"], rp["name"]))
                break

    if not matched:
        # 默认：污染防治措施（最通用的维度）
        matched.append(("RP03", "污染防治措施"))

    return matched


def process_file(input_path, output_path, label):
    with open(input_path, encoding='utf-8') as f:
        qas = json.load(f)

    print(f"\n=== {label}: {len(qas)} 条 QA 对 ===")
    rp_stats = {}

    for qa in qas:
        rps = classify_review_point(qa)
        rp_names = [rp[1] for rp in rps]
        qa["review_points"] = rp_names
        qa["review_point_primary"] = rp_names[0] if rp_names else "污染防治措施"

        for rp_name in rp_names:
            rp_stats[rp_name] = rp_stats.get(rp_name, 0) + 1

    print("\n审核要点分布：")
    for rp in sorted(REVIEW_POINTS, key=lambda x: x["id"]):
        count = rp_stats.get(rp["name"], 0)
        bar = "█" * (count // 5) if count else ""
        print(f"  {rp['id']} {rp['name']}: {count:4d} {bar}")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(qas, f, ensure_ascii=False, indent=2)
    print(f"\n已保存: {output_path}")


if __name__ == '__main__':
    # 处理区级数据
    process_file(
        r"E:\软件\outputs\qa_batch_full\qa_batch_full.json",
        r"E:\软件\outputs\qa_batch_full\qa_batch_full.json",
        "区级（顺德）"
    )

    # 处理市级数据
    process_file(
        r"E:\软件\outputs\qa_foshan\foshan_qa.json",
        r"E:\软件\outputs\qa_foshan\foshan_qa.json",
        "市级（佛山）"
    )
