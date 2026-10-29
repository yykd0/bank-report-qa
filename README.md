# 银行财报问答：混合检索实验

以巨潮资讯公布的 11 家银行年报或半年报全文为样本，按 PDF 物理页提取文本与自动识别表格，使用中文 BM25 和 LSA 稠密向量的倒数排名融合检索。问答页面展示可溯源原文摘录，不虚构生成式回答。记录了 10 题检索结果，包括两道跨公司比较。

## 文件

- `reports.json` / `checksums.json`：公司、报告期间、原始 PDF 地址及文件哈希；原始 PDF 不纳入仓库。
- `download.py`：下载并校验 PDF 格式。
- `build_index.py`：按页切块、识别表格、建立索引。
- `search.py` / `app.py`：混合检索与 Streamlit 页面。
- `evaluate.py`：题目、人工核对的参考值及 top-6 原文结果；结果写入 `outputs/evaluation.json`。
- `outputs/`：评测、截图和一页结论（如已生成）。

## 运行

Python 3.10 以上。运行环境需能够访问巨潮资讯；建立索引会处理三千余页，耗时依 CPU 和 PDF 内容而异。

```shell
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
python download.py
python build_index.py
python evaluate.py
streamlit run app.py
```

网页可选择单家公司或“全部”，并显示每个证据块的公司、报告、章节、PDF 物理页码和原报告链接。默认不需要 API key；如果需要生成文字回答，可设置环境变量 `QA_API_KEY`、`QA_BASE_URL`（兼容 Chat Completions 的 API 根路径）和 `QA_MODEL` 后启动页面。此时问题和检索摘录会发送给配置的服务商，生成回答仍需核对来源。本次评测使用不调用模型的摘录模式，未测试外部模型。`data/pdf/` 和 `data/index/` 均不提交；`.env` 被忽略。索引是本地 pickle，不要加载不可信来源的索引文件。

## 方法与边界

- 样本包含 8 份 2024 年报、2 份 2025 年报和 1 份 2025 年半年报。跨期比较必须注意年份和年度/半年度差异。
- PDF 页码是阅读器物理页码，可能与印刷页码不同。章节由标题正则推断，可能缺失或误判；正文每 900 字开始一个最多 1100 字的块。
- 表格通过 PyMuPDF 检测并保留行列、空单元格及首行；复杂跨页、合并单元格、无框线表格和多栏页面不能保证识别，引用数字前须回看原 PDF。页内正文也保留以便兜底。
- 向量是本语料 TF-IDF 经截断 SVD 得到的 LSA 向量，并非预训练语义嵌入；关键词召回为 BM25，两个排序以 RRF 融合。默认展示原文摘录；它不会自动完成跨公司计算、综合或给出完整排名。
- `evaluate.py` 中的字面命中只是快速核对辅助：数字相同不代表口径正确，表头和单位也必须可读；对照记录以人工逐条查看结果为准。
