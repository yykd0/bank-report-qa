"""Extract all pages and detected tables, then build BM25 and LSA indices."""
import contextlib, io, json, os, pickle, re
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import fitz
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from text_utils import tokens

ROOT=Path(__file__).resolve().parent
INDEX=ROOT/'data'/'index'
SECTION=re.compile(r'^(第[一二三四五六七八九十百\d]+[章节篇]\s*[^\n]{1,35}|[一二三四五六七八九十]+[、.]\s*[^\n]{2,30})$')

def extract(report):
    cache=INDEX/'pages'/f'{report["company"]}.json'
    if cache.exists(): return report['company'],json.loads(cache.read_text(encoding='utf-8'))
    path=ROOT/'data'/'pdf'/f'{report["company"]}.pdf'
    doc=fitz.open(path); chunks=[]; section='未识别章节'
    for n,page in enumerate(doc,1):
        lines=[re.sub(r'\s+',' ',x).strip() for x in page.get_text('text',sort=True).splitlines() if x.strip()]
        for line in lines:
            if SECTION.match(line): section=line
        body='\n'.join(lines)
        for start in range(0,len(body),900):
            text=body[start:start+1100]
            if len(text.strip())>=40:
                chunks.append(dict(company=report['company'],period=report['period'],url=report['url'],page=n,section=section,kind='正文',text=text,id=f'{report["company"]}-p{n}-t{start//900}'))
        try:
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()): tables=page.find_tables().tables
            for ti,table in enumerate(tables):
                rows=table.extract()
                if len(rows)<2: continue
                width=max(len(row) for row in rows)
                clean=[[re.sub(r'\s+',' ',str(v or '')).strip() for v in row]+['']*(width-len(row)) for row in rows]
                for start in range(1,len(clean),12):
                    text='\n'.join(' | '.join(row) for row in [clean[0]]+clean[start:start+12])
                    if len(text)>=30: chunks.append(dict(company=report['company'],period=report['period'],url=report['url'],page=n,section=section,kind='表格',text=text,id=f'{report["company"]}-p{n}-table{ti}-{start}'))
        except Exception as exc: print('table warning',report['company'],n,type(exc).__name__,flush=True)
    cache.parent.mkdir(parents=True,exist_ok=True)
    temp=cache.with_suffix('.tmp'); temp.write_text(json.dumps(chunks,ensure_ascii=False),encoding='utf-8'); temp.replace(cache)
    return report['company'],chunks

def main():
    reports=json.loads((ROOT/'reports.json').read_text(encoding='utf-8'))
    INDEX.mkdir(parents=True,exist_ok=True); chunks=[]
    with ProcessPoolExecutor(max_workers=min(4,os.cpu_count() or 1)) as pool:
        jobs=[pool.submit(extract,r) for r in reports]
        for future in as_completed(jobs):
            company,items=future.result(); chunks.extend(items); print(company,'chunks',len(items),flush=True)
    chunks.sort(key=lambda c:c['id']); print('Tokenizing',len(chunks),'chunks',flush=True)
    corpus=[tokens(c['text']) for c in chunks]
    df=Counter(t for doc in corpus for t in set(doc))
    vec=TfidfVectorizer(tokenizer=tokens,token_pattern=None,lowercase=False,min_df=2,max_features=30000,sublinear_tf=True)
    X=vec.fit_transform([c['text'] for c in chunks]); print('Fitting vectors',X.shape,flush=True)
    svd=TruncatedSVD(n_components=96,random_state=42,n_iter=4)
    embeddings=normalize(svd.fit_transform(X)).astype('float32')
    bundle={'chunks':chunks,'freq':[Counter(d) for d in corpus],'df':df,'lengths':np.array([len(d) for d in corpus]),'vectorizer':vec,'svd':svd,'embeddings':embeddings}
    with (INDEX/'index.pkl').open('wb') as f: pickle.dump(bundle,f,protocol=pickle.HIGHEST_PROTOCOL)
    print('DONE',len(chunks),'chunks',sum(c['kind']=='表格' for c in chunks),'table chunks',flush=True)

if __name__=='__main__': main()
