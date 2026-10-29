import re
import streamlit as st
from qa_engine import answer_question
from search import load

st.set_page_config(page_title='银行财报问答',layout='wide')
st.title('银行财报问答')
st.caption('11 家上市银行 · BM25 + LSA 向量检索 · PDF 表格坐标还原')
st.info('支持明确公司、一个年份的营业收入、归母净利润、不良贷款率、拨备覆盖率等指标和同指标比较。结果取自报告表格；不确定时会说明证据不足。报告期、口径和单位请核对原文。')
@st.cache_resource
def cached(): return load()
try: index=cached()
except FileNotFoundError:
    st.error('索引尚未构建。请先运行 download.py 和 build_index.py。'); st.stop()
companies=sorted({c['company'] for c in index['chunks']})
company=st.selectbox('选择公司（跨公司提问选全部）',['全部']+companies)
question=st.text_input('输入问题',value='比较成都银行和中信银行2024年末不良贷款率，谁更低？')
if st.button('检索并回答',type='primary') and question.strip():
    with st.spinner('正在逐家公司查找、还原表格并核对年份…'):
        result=answer_question(index,question,company)
    sources=result['sources']
    def link_citation(match):
        i=int(match.group(1))-1
        if 0<=i<len(sources):
            c=sources[i]
            return f'[[{i+1}]]({c["url"]}#page={c["page"]})'
        return match.group(0)
    st.subheader('回答')
    st.markdown(re.sub(r'\[(\d+)\]',link_citation,result['answer']))
    st.caption('回答基于坐标还原的财报表格和确定性计算；角标可直接打开报告。页码为 PDF 物理页。')
    st.subheader('来源与召回证据')
    for i,c in enumerate(sources,1):
        label=f"[{i}] {c['company']} · {c['period']} · PDF 第 {c['page']} 页 · {c['kind']}"
        with st.expander(label,expanded=i<=len(result['facts'])):
            st.caption(c['section'])
            st.text(c['text'])
            st.markdown(f"[打开原始报告]({c['url']}#page={c['page']})　块 ID：`{c['id']}`")
            if 'bm25' in c: st.caption(f"BM25 {c['bm25']} · 向量 {c['vector']} · RRF {c['rrf']}")
    if result.get('missing'): st.warning('未覆盖：'+ '、'.join(result['missing'])+'。不要据此推断完整行业排名。')
