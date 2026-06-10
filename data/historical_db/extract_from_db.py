"""环评历史数据库 — 从达梦数据库提取 QA 问答对"""
import dmPython, json, re, os

DB_CONFIG = {"server":"172.16.168.163","port":5236,"user":"SYSDBA","password":"SYSDBA001","autoCommit":True}

def get_region_full(regions, code):
    parts = []
    while code and code != '0':
        if code in regions: parts.insert(0, regions[code]['name']); code = regions[code]['parent']
        else: break
    return ''.join(parts)

def main():
    conn = dmPython.connect(**DB_CONFIG); cursor = conn.cursor()
    cursor.execute("SELECT CODE,NAME,PARENT_CODE FROM HYCX_HB.dic_region")
    regions = {str(r[0]):{'name':str(r[1]),'parent':str(r[2])} for r in cursor.fetchall() if r[0]}
    cursor.execute("SELECT VALUE,LABEL FROM HYCX_HB.hp_dic WHERE IS_ENABLED=1")
    dic = {str(r[0]):str(r[1]) for r in cursor.fetchall() if r[0]}
    cursor.execute("SELECT UNIQUE_ID,NAME FROM HYCX_HB.hp_apply_unit WHERE IS_DELETE=0")
    units = {str(r[0]):str(r[1]) for r in cursor.fetchall() if r[0]}

    qa_pairs = []
    cursor.execute("""
        SELECT m.SP_ID,m.REGION_CODE,m.ITEM_TYPE,m.APPLY_UNIT_ID,
               a.APPROVE_OPINION,a.VOCS_EMISSION,a.AIR_STANDARD_ID,a.LEGAL_BASIS
        FROM HYCX_HB.hp_main_info m
        INNER JOIN HYCX_HB.hp_approve_info a ON m.SP_ID=a.SP_ID AND a.IS_DELETE=0
        WHERE a.APPROVE_OPINION IS NOT NULL AND LENGTH(CAST(a.APPROVE_OPINION AS VARCHAR))>30
        AND m.IS_DELETE=0 FETCH FIRST 1000 ROWS ONLY""")
    for r in cursor.fetchall():
        try: op = str(r[4] or ''); ve = str(r[5] or ''); lb = str(r[7] or '')
        except: continue
        if len(op)<30 or not re.search(r'废气|VOCs|NMHC|排气筒|吸附|活性炭|集气罩|无组织|排放浓度|DB44',op,re.I): continue
        co = units.get(str(r[3] or ''),''); rg = get_region_full(regions,str(r[1] or ''))
        pt = dic.get(str(r[2] or ''),'')
        standards = []
        if str(r[6] or ''): standards.append({"standard_code":str(r[6]),"standard_name":"","source":"approval_answer"})
        for pat in [r'[A-Z]{1,6}\s*\d{3,6}[-—]\d{4}',r'[A-Z]{1,6}\s*\d{3,6}[-—]\d{2}',r'[A-Z]+\s*\d+[-—]{1,2}\d+']:
            for m in re.finditer(pat,op):
                sc=m.group().strip().replace(' ','')
                if not any(s['standard_code']==sc for s in standards): standards.append({"standard_code":sc,"standard_name":"","source":"approval_answer"})
        q = f"【区级】{co}（{pt}）该项目废气的污染因子、治理设施、排气筒参数和排放标准是什么？"
        if re.search(r'集气罩|收集|密闭|风量',op,re.I): q = f"【区级】{co}（{pt}）该项目废气收集方式和处理措施是什么，执行什么排放标准？"
        elif re.search(r'VOCs|NMHC|甲苯|有机废气',op,re.I): q = f"【区级】{co}（{pt}）该项目涉及哪些VOCs污染因子，废气治理设施和排放标准是什么？"
        a = f"批复要求：{op[:1000]}"
        if ve: a += f"\nVOCs排放数据：{ve[:100]}"
        if lb: a += f"\n法律依据：{lb[:200]}"
        qa_pairs.append({"qa_id":f"DB_QA_{len(qa_pairs)+1:05d}_废气","pair_id":f"db_pair_{len(qa_pairs)+1:05d}",
            "level":"区级","region":rg,"company":co,"project_name":"","industry_code":"","industry_name":"",
            "project_type":pt,"report_type":"报告表","element":"废气","review_point":"审批要求与报告支撑核查",
            "question":q,"answer":a,"standards_normalized":standards[:10],
            "approval_evidence":[{"source_file":"approval.md","text":op[:500],"char_start":0,"char_end":min(len(op),500)}],
            "report_evidence":[],"answer_terms":list(set(re.findall(r'[A-Z]+[\d\-/]+',op)[:15])),
            "evidence_alignment":{"level":"medium","reason":"database_extraction"},
            "benchmark_metadata":{"task_domain":"废气","difficulty":"simple","question_type":"extraction","cognitive_level":"L1_fact","evaluation_dimensions":["professionalism","clarity","feasibility","evidence_grounding"]},
            "quality_score":80,"quality_issues":["no_report_evidence","db_auto_extracted"],"need_human_review":True})

    cursor.execute("""SELECT t.SP_ID,t.REPLY_NOTE,t.REPLY_RESULT,m.REGION_CODE,m.ITEM_TYPE,m.APPLY_UNIT_ID
        FROM HYCX_HB.hp_approve_tech t LEFT JOIN HYCX_HB.hp_main_info m ON t.SP_ID=m.SP_ID
        WHERE t.REPLY_NOTE IS NOT NULL AND LENGTH(CAST(t.REPLY_NOTE AS VARCHAR))>30 FETCH FIRST 500 ROWS ONLY""")
    for r in cursor.fetchall():
        try: rn = str(r[1] or ''); rr = str(r[2] or '')
        except: continue
        if len(rn)<20 or not re.search(r'废气|VOCs|NMHC|有机|臭气|粉尘|颗粒物|排气筒|吸附|活性炭',rn,re.I): continue
        co = units.get(str(r[5] or ''),''); rg = get_region_full(regions,str(r[3] or '')); pt = dic.get(str(r[4] or ''),'')
        q = f"【区级】{co}（{pt}）该项目的废气部分有哪些技术审查意见？"
        qa_pairs.append({"qa_id":f"DB_TECH_{len(qa_pairs)+1:05d}_废气","pair_id":f"db_tech_pair_{len(qa_pairs)+1:05d}",
            "level":"区级","region":rg,"company":co,"project_name":"","industry_code":"","industry_name":"",
            "project_type":pt,"report_type":"报告表","element":"废气","review_point":"技术审查意见与整改要求",
            "question":q,"answer":f"审查结论：{rr}\n审查意见：{rn[:800]}","standards_normalized":[],
            "approval_evidence":[{"source_file":"tech_review.md","text":rn[:500],"char_start":0,"char_end":min(len(rn),500)}],
            "report_evidence":[],"answer_terms":[],
            "evidence_alignment":{"level":"high","reason":"tech_review_extraction"},
            "benchmark_metadata":{"task_domain":"废气","difficulty":"medium","question_type":"extraction","cognitive_level":"L2_analysis","evaluation_dimensions":["professionalism","clarity","feasibility","evidence_grounding"]},
            "quality_score":85,"quality_issues":["no_report_evidence"],"need_human_review":True})

    out_path = os.path.join(os.path.dirname(__file__),"qa_experience_base.jsonl")
    with open(out_path,'w',encoding='utf-8') as f:
        for qa in qa_pairs: f.write(json.dumps(qa,ensure_ascii=False)+'\n')
    print(f"完成！共 {len(qa_pairs)} 条 QA 对，输出: {out_path} ({os.path.getsize(out_path)/1024:.1f} KB)")
    cursor.close(); conn.close()

if __name__ == "__main__": main()