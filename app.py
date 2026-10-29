import streamlit as st
from search import load, retrieve
from answer import generate

st.set_page_config(page_title='银行财报问答',layout='wide')
st.title('银行财报问答')
st.caption('11 家上市银行 · 巨潮资讯报告全文 · BM25 + LSA 向量混合检索')
st.info('默认展示可核验的原文摘录；配置模型后可生成带引用的回答。报告期间并不完全相同；比较时请核对年份、口径和单位。页码是 PDF 阅读器的物理页码。')
@st.cache_resource
def cached(): return load()
try: index=cached()
except FileNotFoundError:
    st.error('索引尚未构建。请先运行 download.py 和 build_index.py。'); st.stop()
companies=sorted({c['company'] for c in index['chunks']})
company=st.selectbox('选择公司（跨公司提问选全部）',['全部']+companies)
question=st.text_input('输入问题',value='成都银行2024年末不良贷款率是多少？')
if st.button('检索并回答',type='primary') and question.strip():
    results=retrieve(index,question,k=6,company=None if company=='全部' else company)
    st.subheader('回答')
    try:
        response=generate(question,results)
        if response: st.write(response)
        else: st.write('当前为原文摘录模式，请结合下列证据核对答案。配置模型后可生成文字回答。')
    except Exception as exc:
        st.warning(f'模型调用失败，请使用原文证据核对：{type(exc).__name__}')
    st.subheader('检索证据')
    st.write('跨公司问题请逐家公司核对；这些摘录不保证覆盖全部公司。')
    for i,c in enumerate(results,1):
        st.markdown(f"**[{i}] {c['company']} · {c['period']} · PDF 第 {c['page']} 页 · {c['section']} · {c['kind']}**")
        st.text(c['text'])
        st.markdown(f"[打开原始报告]({c['url']}#page={c['page']})　块 ID：`{c['id']}` · BM25 {c['bm25']} · 向量 {c['vector']}")
        st.divider()
