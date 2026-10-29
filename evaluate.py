"""Record every returned chunk and objective evidence checks, not an LLM judge."""
import json
from pathlib import Path
from search import load, retrieve

CASES=[
 {'q':'宁波银行2024年营业收入是多少？','filter':'宁波银行','facts':[('宁波银行','66,631')], 'reference':'66,631百万元，2024年年报PDF第9页'},
 {'q':'中信银行2024年营业收入是多少？','filter':'中信银行','facts':[('中信银行','213,646')], 'reference':'213,646百万元，2024年年报PDF第16页'},
 {'q':'浦发银行2024年营业收入是多少？','filter':'浦发银行','facts':[('浦发银行','170,748')], 'reference':'170,748百万元，2024年年报PDF第19页'},
 {'q':'青岛银行2024年末不良贷款率是多少？','filter':'青岛银行','facts':[('青岛银行','1.14')], 'reference':'1.14%，2024年年报PDF第9页'},
 {'q':'苏州银行2025年末不良贷款率是多少？','filter':'苏州银行','facts':[('苏州银行','0.82')], 'reference':'0.82%，2025年年报PDF第6或8页'},
 {'q':'上海银行2025年营业收入是多少？','filter':'上海银行','facts':[('上海银行','54,761,019')], 'reference':'54,761,019千元，2025年年报PDF第16页'},
 {'q':'成都银行2024年末不良贷款率是多少？','filter':'成都银行','facts':[('成都银行','0.66')], 'reference':'0.66%，2024年年报PDF第9页'},
 {'q':'北京银行2024年末拨备覆盖率是多少？','filter':'北京银行','facts':[('北京银行','208.75')], 'reference':'208.75%，2024年年报PDF第7页'},
 {'q':'比较成都银行和中信银行2024年末不良贷款率，谁更低？','filter':None,'facts':[('成都银行','0.66'),('中信银行','1.16')], 'reference':'成都0.66%，中信1.16%；成都更低。成都PDF第9页，中信PDF第10页'},
 {'q':'宁波银行和浦发银行2024年归母净利润谁更高？','filter':None,'facts':[('宁波银行','27,127'),('浦发银行','45,257')], 'reference':'宁波27,127百万元，浦发45,257百万元；浦发更高。宁波PDF第9页，浦发PDF第19页'}
]

def main():
    idx=load(); out=[]
    for n,case in enumerate(CASES,1):
        results=retrieve(idx,case['q'],6,case['filter'])
        matches={company:any(x['company']==company and value in x['text'] for x in results) for company,value in case['facts']}
        out.append({'id':n,**case,'literal_matches':matches,'retrieved':results})
        print(n, matches, ' | '.join(f"{x['id']}({x['kind']})" for x in results),flush=True)
    path=Path(__file__).parent/'outputs'/'evaluation.json'
    path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__': main()
