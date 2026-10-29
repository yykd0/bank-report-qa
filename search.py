import math, pickle
from pathlib import Path
import numpy as np
from sklearn.preprocessing import normalize
from text_utils import tokens

ROOT=Path(__file__).resolve().parent
def load():
    # Compatibility with an index produced by an earlier direct-script run.
    import __main__
    __main__.tokens = tokens
    with (ROOT/'data'/'index'/'index.pkl').open('rb') as f: return pickle.load(f)

def retrieve(index, question, k=5, company=None):
    chunks=index['chunks']; N=len(chunks); lengths=index['lengths']; avg=lengths.mean()
    scores=np.zeros(N, dtype='float32')
    for term in set(tokens(question)):
        df=index['df'].get(term,0)
        if not df: continue
        idf=math.log(1+(N-df+0.5)/(df+0.5))
        for i,f in enumerate(index['freq']):
            tf=f.get(term,0)
            if tf: scores[i]+=idf*tf*2.2/(tf+1.2*(0.25+0.75*lengths[i]/avg))
    q=index['vectorizer'].transform([question]); v=normalize(index['svd'].transform(q))
    dense=index['embeddings'] @ v[0]
    ids=[i for i,c in enumerate(chunks) if not company or c['company']==company]
    if not ids: return []
    # Reciprocal-rank fusion, avoiding arbitrary score calibration.
    b=sorted(ids,key=lambda i:scores[i],reverse=True)
    d=sorted(ids,key=lambda i:dense[i],reverse=True)
    fused={i:1/(60+r) for r,i in enumerate(b,1)}
    for r,i in enumerate(d,1): fused[i]+=1/(60+r)
    ordered=sorted(ids,key=lambda i:fused[i],reverse=True)
    return [{**chunks[i], 'bm25':round(float(scores[i]),3), 'vector':round(float(dense[i]),3), 'rrf':round(fused[i],6)} for i in ordered[:k]]
