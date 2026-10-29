from pathlib import Path
import fitz

root=Path(__file__).resolve().parent
doc=fitz.open(); page=doc.new_page(width=595,height=842)
font='C:/Windows/Fonts/msyh.ttc'
page.insert_font(fontname='cjkfont',fontfile=font)
page.insert_text((45,58),'银行财报问答：一页实验结论',fontname='cjkfont',fontsize=19,color=(0.1,0.18,0.29))
page.draw_line((45,73),(550,73),color=(0.2,0.42,0.65),width=1)
text='''实验范围与方法
使用巨潮资讯 11 家上市银行的财报全文：8 份 2024 年年报、2 份 2025 年年报、1 份 2025 年半年报，共解析 3,472 个 PDF 页面，形成 6,442 个正文或表格块（其中表格块 1,613 个）。按 PDF 物理页标注公司、报告、章节；BM25 与 TF-IDF／SVD（LSA）向量排序用 RRF 融合。默认页面展示原文摘录，未接入模型生成。

真实评测：10 题，包含 2 题跨公司比较
八道单公司指标题均召回可人工核对的正确证据，但页面没有生成完整答案，故只能记为部分完成。严格按“页面直接给出完整答案”计，0/10；不能将数字命中当成答对。跨公司第 9 题召回两家数值，却未计算谁更低；第 10 题漏召回浦发银行所需数值，也未给出比较结论。每题的前 6 块、参考值和判断见 evaluation.md / evaluation.json。

主要失误与原因
跨公司查询存在证据不均衡，前 6 块被同一公司占满；检索排序不会自行汇总或执行比较。PDF 的双栏、图表及跨列文本可能乱序；自动表格识别有错位、缺表头和跨页问题。章节为规则推断，并非人工逐页校验。不同报告的时间跨度和单位也不同，不能不加核对地横比。

结论与下一步
需要追溯财报原文、查单项指标和核对出处时，知识库合适：可以返回报告及页码，并随新报告更新。跨公司全景或排名需要先分公司召回、统一期间和单位、结构化表格，再计算并引用证据。微调更适合学习董秘口吻，不适合作为不断更新的财报事实唯一来源；本实验没有进行 LoRA 对照，因此不声称验证了微调效果。

当前交付状态
检索页面与十题证据记录已运行；生成式回答接口未经实际模型测试，复杂表格未全面还原。以上限制应保留在提交说明中。'''
rect=fitz.Rect(45,90,550,790)
remaining=page.insert_textbox(rect,text,fontname='cjkfont',fontsize=10.5,lineheight=1.35,color=(0.13,0.16,0.2))
if remaining<0: raise RuntimeError(f'Content does not fit on one page: {remaining}')
doc.subset_fonts(); doc.save(root/'outputs'/'一页结论.pdf',garbage=4,deflate=True)
print('created one page, spare height',remaining)
