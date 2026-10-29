import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'outputs/evaluation.json').read_text(encoding='utf-8'))
out=['# 财报问答逐题评测','',
     '2026-10-29。原10题与上一版相同；另外增加两道11家公司全景题，以及同义问法、跨年列、跨单位、未收录公司与不支持口径等独立检查。',
     '判断方法：将实际生成的答案、提取的值、单位、比较结果及引用，与预先核对的报告数值逐项比对；拒答题要求不输出事实。以下是程序化检查，不代表对所有问题或所有表格的准确率。',
     '上一版严格按页面给出完整答案为 0/10；新版结果如下。']
for group in ('原10题','全景题','补充题','拒答题'):
    items=[x for x in data if x['group']==group]
    out += ['',f'## {group}：{sum(x["correct"] for x in items)}/{len(items)}','']
    for x in items:
        r=x['result']
        verdict='通过' if x['correct'] else '未完成（部分结果可核对，已拒绝完整比较）' if x.get('safe_partial') else '未通过'
        out += [f'### {x["id"]}. {x["question"]}',f'结果：{verdict}；参考：{x["reference"]}', '',r['answer'],'']
        if r.get('facts'):
            out.append('用于回答的表格行：')
            for f in r['facts']:
                out.append(f'- {f["id"]}｜{f["period"]}｜PDF第{f["page"]}页｜{f["text"].replace(chr(10), "；")}')
        if r.get('recall'):
            out.append('分公司混合检索召回块：')
            for name,chunks in r['recall'].items():
                out.append(f'- {name}：'+ '、'.join(f'{c["id"]}（{c["kind"]}）' for c in chunks))
        out.append('')
out += ['完整结果（含每个召回块原文、分数及链接）见 `evaluation.json`；上一版记录保留为 `evaluation-baseline.md` / `evaluation-baseline.json`。',
        '局限：表格仍可能因为跨页、合并单元格、双栏或扫描件失败；仅在找到可信的同页多年份表头、指标行、数值对齐及单位时回答。样本中江苏银行只有半年报，不用于全年比较。']
(ROOT/'outputs/evaluation.md').write_text('\n'.join(out)+'\n',encoding='utf-8')
