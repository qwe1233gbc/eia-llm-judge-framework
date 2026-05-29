# -*- coding: utf-8 -*-
"""QA quality checker - generates behavior rules and quality scores"""
import sys, json, re
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

FILES = [
    ("quji", r"E:\软件\outputs\qa_batch_full\qa_batch_full.json"),
    ("shiji", r"E:\软件\outputs\qa_foshan\foshan_qa.json"),
]

def load():
    out = []
    for lbl, p in FILES:
        with open(p, encoding='utf-8') as f:
            for q in json.load(f):
                q["_src"] = lbl
                out.append(q)
    return out

def quality(qa):
    issues = []
    s = 100
    q = qa.get("question","")
    a = qa.get("answer","")
    if len(q) < 15: issues.append("short question"); s -= 10
    if len(a) < 20: issues.append("short answer"); s -= 10
    if not qa.get("standards"): issues.append("no standards"); s -= 20
    if not qa.get("report_evidence"): issues.append("no evidence"); s -= 20
    if qa.get("validation") != "已验证": issues.append("not validated"); s -= 10
    return max(s,10), issues

def rule(qa):
    ic = qa.get("industry_code","?")
    el = qa.get("element","?")
    pt = qa.get("project_type","?")
    stds = qa.get("standards",[])
    a = qa.get("answer","")
    base = "[%s] %s %s" % (ic, el, pt)
    if stds:
        return base + ": use " + "/".join(stds[:3])
    if "t/a" in a:
        m = re.search(r"[\d.]+t/a", a)
        return base + ": total " + (m.group() if m else "")
    if "不新增" in a or "无新增" in a:
        return base + ": no new " + el
    return base + ": see approval"

def main():
    allq = load()
    print(("="*60))
    print(("QA Quality Report - %d items" % len(allq)))
    print(("="*60))
    sc = []
    gr = {"A>=80":0,"B60-79":0,"C40-59":0,"D<40":0}
    for q in allq:
        s, iss = quality(q)
        sc.append(s)
        if s>=80: gr["A>=80"]+=1
        elif s>=60: gr["B60-79"]+=1
        elif s>=40: gr["C40-59"]+=1
        else: gr["D<40"]+=1
        q["quality_score"] = s
        q["quality_issues"] = iss
        q["behavior_rule"] = rule(q)
    avg = sum(sc)/len(sc)
    print(("Avg score: %.1f" % avg))
    for g,n in sorted(gr.items()):
        print(("  %s: %d (%.0f%%)" % (g, n, n/len(sc)*100)))
    print(("\nBy element:"))
    byel = defaultdict(list)
    for q in allq:
        byel[q.get("element","?")].append(q)
    for e,items in sorted(byel.items()):
        ns = sum(1 for i in items if not i.get("standards"))
        print(("  %s: %d items, no-std %d" % (e, len(items), ns)))
    print(("\nBehavior rules:"))
    seen = set()
    for q in allq:
        r = q.get("behavior_rule","")
        k = (q.get("industry_code",""), q.get("element",""))
        if k not in seen:
            seen.add(k)
            print(("  " + r[:120]))
    # save
    with open(r"E:\软件\outputs\qa_quality_report.json","w",encoding="utf-8") as f:
        json.dump({"summary":{"total":len(allq),"avg":round(avg,1),"grades":gr}},f,ensure_ascii=False,indent=2)
    for lbl,p in FILES:
        with open(p,encoding="utf-8") as f:
            qas = json.load(f)
        src = [q for q in allq if q.get("_src")==lbl]
        for q in qas:
            for s in src:
                if q.get("company")==s.get("company") and q.get("element")==s.get("element") and q.get("clause_index")==s.get("clause_index"):
                    q["quality_score"] = s.get("quality_score",100)
                    q["quality_issues"] = s.get("quality_issues",[])
                    q["behavior_rule"] = s.get("behavior_rule","")
                    break
        with open(p,"w",encoding="utf-8") as f:
            json.dump(qas,f,ensure_ascii=False,indent=2)
        print(("Updated: " + p))
    print(("\nDone!"))

if __name__=="__main__":
    main()
