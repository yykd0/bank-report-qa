from pathlib import Path
import fitz

root=Path(__file__).resolve().parent
doc=fitz.open(); page=doc.new_page(width=595,height=842)
font='C:/Windows/Fonts/msyh.ttc'
page.insert_font(fontname='cjkfont',fontfile=font)
page.insert_text((45,58),'银行财报问答：改进与评测结论',fontname='cjkfont',fontsize=19,color=(0.1,0.18,0.29))
page.draw_line((45,73),(550,73),color=(0.2,0.42,0.65),width=1)
text='''样本与方法
选取巨潮资讯 11 家上市银行的财报全文，共 3,472 个 PDF 页面。按页切分正文和检测到的表格，以 BM25 与 LSA 向量进行混合检索。样本含 8 份 2024 年报、2 份 2025 年报和 1 份 2025 年半年报；比较时必须区分期间和口径。

本次改进
页面基于 PDF 坐标对齐多年份表头、指标行和数值，核对单位后直接输出答案及可点击的原报告页码。跨公司问题逐家公司召回，并把不同金额单位换算后比较；任一所需公司证据不足时，不给出完整排名。实现使用可检查的规则，并未调用大模型。

实际评测
沿用原 10 道题：上一版直接完整回答 0/10；新版对预先核对的答案、单位、比较结论及引用的检查为 10/10。新增两道覆盖全部 11 家银行的全景题均未完整回答：不良率覆盖 7 家，营收排名覆盖 10 家，缺失项均明确标出且未给出完整排名。另有 8 道补充题和 8 道拒答检查均通过。逐题结果与召回块见 evaluation.md；小样本不代表任意问题的准确率。

典型案例与局限
比较 2024 年不良贷款率时，成都银行 0.66%，中信银行 1.16%，页面给出成都较低并分别引用对应报告页。江苏银行只有 2025 年半年报，不能当作 2025 全年营业收入，因此拒答。跨页、合并单元格、扫描件和复杂多栏表格仍可能漏检或错位；规则仅搜索前 60 页财务摘要，且目前不支持多指标、跨年变化及细分贷款口径。引用数字前仍应回看原 PDF。

结论
追溯财报事实、定位数字出处及更新资料，适合建库；跨公司题还需要分公司召回、对齐年份及单位，再计算。微调更适合学习稳定的表达口径，不应作为持续变化的财报事实唯一来源。本实验未训练模型，不能据此声称微调效果。'''
remaining=page.insert_textbox(fitz.Rect(45,90,550,790),text,fontname='cjkfont',fontsize=10.5,lineheight=1.35,color=(0.13,0.16,0.2))
if remaining<0: raise RuntimeError(f'Content does not fit: {remaining}')
doc.subset_fonts(); doc.save(root/'outputs'/'一页结论.pdf',garbage=4,deflate=True)
print('created one-page PDF; spare height',remaining)
