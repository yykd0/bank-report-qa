"""Re-run baseline, held-out cases, and abstention checks against PDF references."""
from decimal import Decimal
import json, re
from pathlib import Path
from qa_engine import answer_question
from search import load

CASES=[
 {'q':'宁波银行2024年营业收入是多少？','facts':{'宁波银行':('66631','百万元')},'reference':'2024年年报 PDF 第9页'},
 {'q':'中信银行2024年营业收入是多少？','facts':{'中信银行':('213646','百万元')},'reference':'2024年年报 PDF 第16页'},
 {'q':'浦发银行2024年营业收入是多少？','facts':{'浦发银行':('170748','百万元')},'reference':'2024年年报 PDF 第19页'},
 {'q':'青岛银行2024年末不良贷款率是多少？','facts':{'青岛银行':('1.14','%')},'reference':'2024年年报 PDF 第9页'},
 {'q':'苏州银行2025年末不良贷款率是多少？','facts':{'苏州银行':('0.82','%')},'reference':'2025年年报 PDF 第15页'},
 {'q':'上海银行2025年营业收入是多少？','facts':{'上海银行':('54761019','千元')},'reference':'2025年年报 PDF 第16页'},
 {'q':'成都银行2024年末不良贷款率是多少？','facts':{'成都银行':('0.66','%')},'reference':'2024年年报 PDF 第15页'},
 {'q':'北京银行2024年末拨备覆盖率是多少？','facts':{'北京银行':('208.75','%')},'reference':'2024年年报 PDF 第25页'},
 {'q':'比较成都银行和中信银行2024年末不良贷款率，谁更低？','facts':{'成都银行':('0.66','%'),'中信银行':('1.16','%')},'winner':'成都银行','direction':'较低','reference':'成都 PDF 第15页、中信 PDF 第18页'},
 {'q':'宁波银行和浦发银行2024年归母净利润谁更高？','facts':{'宁波银行':('27127','百万元'),'浦发银行':('45257','百万元')},'winner':'浦发银行','direction':'较高','reference':'宁波 PDF 第9页、浦发 PDF 第19页'},
]
HOLDOUT=[
 {'q':'宁波银行2023年营业收入是多少？','facts':{'宁波银行':('61585','百万元')},'reference':'宁波2024年年报 PDF 第9页'},
 {'q':'上海银行2024年营业收入是多少？','facts':{'上海银行':('52985550','千元')},'reference':'上海2025年年报 PDF 第16页'},
 {'q':'苏州银行2024年末不良贷款率是多少？','facts':{'苏州银行':('0.83','%')},'reference':'苏州2025年年报 PDF 第15页'},
 {'q':'苏州银行与成都银行2024年末不良贷款率谁更低？','facts':{'苏州银行':('0.83','%'),'成都银行':('0.66','%')},'winner':'成都银行','direction':'较低','reference':'苏州 PDF 第15页、成都 PDF 第15页'},
 {'q':'宁波银行和青岛银行2024年营业收入谁更高？','facts':{'宁波银行':('66631','百万元'),'青岛银行':('13497534','千元')},'winner':'宁波银行','direction':'较高','reference':'宁波 PDF 第9页、青岛 PDF 第8页；比较前换算单位'},
 {'q':'宁波银行2024年的营收是多少？','facts':{'宁波银行':('66631','百万元')},'reference':'宁波2024年年报 PDF 第9页；同义问法'},
 {'q':'成都银行2024年不良率是多少？','facts':{'成都银行':('0.66','%')},'reference':'成都2024年年报 PDF 第15页；同义问法'},
 {'q':'苏州银行2024年营业收入是多少？','facts':{'苏州银行':('12223786','千元')},'reference':'苏州2025年年报 PDF 第12页；居中表头与数字的坐标偏移'},
]
PANORAMA=[
 {'q':'这11家银行2024年末不良贷款率分别是多少？','facts':{'中信银行':('1.16','%'),'北京银行':('1.31','%'),'平安银行':('1.06','%'),'成都银行':('0.66','%'),'杭州银行':('0.76','%'),'苏州银行':('0.83','%'),'青岛银行':('1.14','%')},'missing':['上海银行','宁波银行','江苏银行','浦发银行'],'reference':'11家银行的2024年指标；当前能核对7家，其余4家证据不足'},
 {'q':'所有银行2024年营业收入排名','facts':{'上海银行':('52985550','千元'),'中信银行':('213646','百万元'),'北京银行':('69917','百万元'),'宁波银行':('66631','百万元'),'平安银行':('146695','百万元'),'成都银行':('22981527','千元'),'杭州银行':('38381172','千元'),'浦发银行':('170748','百万元'),'苏州银行':('12223786','千元'),'青岛银行':('13497534','千元')},'missing':['江苏银行'],'reference':'11家银行的2024年营收；当前能核对10家，江苏银行缺全年报告'},
]
ABSTAIN=[
 {'q':'江苏银行2025年营业收入是多少？','reason':'只有半年报，不能当成全年数值'},
 {'q':'工商银行2024年营业收入是多少？','reason':'不在本次样本中'},
 {'q':'中信银行2024年核心一级资本充足率是多少？','reason':'不能误作资本充足率'},
 {'q':'成都银行2023和2024年不良贷款率变化是多少？','reason':'多年份变化计算暂不支持'},
 {'q':'成都银行2024年上半年营业收入是多少？','reason':'不能用年报全年数冒充半年数'},
 {'q':'成都银行2024年个人贷款不良贷款率是多少？','reason':'不能把全行指标当作个人贷款指标'},
 {'q':'成都银行2024年营业收入和归母净利润是多少？','reason':'暂不支持同一问题里的多个指标'},
 {'q':'工商银行2024年营业收入是多少？','selection':'成都银行','reason':'不得用下拉框内公司的数值冒充未收录公司'},
]

def assess(case,result):
    if 'reason' in case:
        return result['status'] in ('证据不足','需要明确问题') and not result['facts']
    actual={x['company']:x for x in result['facts']}
    if result['status']!='已回答' or set(actual)!=set(case['facts']): return False
    for company,(value,unit) in case['facts'].items():
        f=actual[company]
        if Decimal(f['value'])!=Decimal(value) or f['unit']!=unit: return False
        if not f['url'].startswith('https://static.cninfo.com.cn/') or f['page']<1: return False
        source_index=result['sources'].index(f)+1
        if f'[{source_index}]' not in result['answer']: return False
    if 'winner' in case and (case['winner']+case['direction']) not in result['answer']: return False
    return True

def assess_partial(case,result):
    if result['status']!='部分回答' or set(result.get('missing',[]))!=set(case['missing']): return False
    actual={x['company']:x for x in result['facts']}
    if set(actual)!=set(case['facts']): return False
    for company,(value,unit) in case['facts'].items():
        f=actual[company]
        if Decimal(f['value'])!=Decimal(value) or f['unit']!=unit: return False
        if f'[{result["sources"].index(f)+1}]' not in result['answer']: return False
    return '证据不足' in result['answer'] and '不作完整比较或排名' in result['answer']

def main():
    idx=load(); output=[]
    for group,cases in [('原10题',CASES),('全景题',PANORAMA),('补充题',HOLDOUT),('拒答题',ABSTAIN)]:
        for n,case in enumerate(cases,1):
            result=answer_question(idx,case['q'],case.get('selection'))
            correct=assess(case,result) if group!='全景题' else result['status']=='已回答' and assess(case,result)
            safe=assess_partial(case,result) if group=='全景题' else correct
            record={'group':group,'id':n,'question':case['q'],'reference':case.get('reference',case.get('reason')),
                    'expected':case.get('facts',{}),'winner':case.get('winner'),'direction':case.get('direction'),
                    'correct':correct,'safe_partial':safe if group=='全景题' else None,'result':result}
            output.append(record)
            print(group,n,'通过' if correct else '部分回答（安全）' if group=='全景题' and safe else '未通过',case['q'],flush=True)
    path=Path(__file__).parent/'outputs'/'evaluation.json'
    path.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    for group in ('原10题','全景题','补充题','拒答题'):
        items=[x for x in output if x['group']==group]
        print(group,sum(x['correct'] for x in items),'/',len(items),flush=True)
    if not all(x['correct'] or x.get('safe_partial') for x in output): raise SystemExit(1)

if __name__=='__main__': main()
