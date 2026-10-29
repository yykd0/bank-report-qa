"""Optional OpenAI-compatible answer synthesis, using only retrieved evidence."""
import json, os
from urllib.request import Request, urlopen

def generate(question, results):
    key=os.environ.get('QA_API_KEY')
    base=os.environ.get('QA_BASE_URL','').rstrip('/')
    model=os.environ.get('QA_MODEL')
    if not (key and base and model): return None
    sources='\n\n'.join(f"[{i}] {c['company']} {c['period']} PDF第{c['page']}页\n{c['text']}" for i,c in enumerate(results,1))
    data={'model':model,'temperature':0,'messages':[
        {'role':'system','content':'仅依据提供的财报摘录回答；每项事实附对应的 [数字] 引用。不要编造、不要把不同年份混为同一年度。资料不足就说不足。表格混乱或单位不明须说明，不要猜测。'},
        {'role':'user','content':f'问题：{question}\n\n证据：\n{sources}'}]}
    req=Request(base+'/chat/completions',data=json.dumps(data,ensure_ascii=False).encode(),headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'})
    with urlopen(req,timeout=90) as response:
        return json.load(response)['choices'][0]['message']['content']
