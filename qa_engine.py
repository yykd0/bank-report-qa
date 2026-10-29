"""Grounded extractive answers for explicitly requested financial metrics."""
from decimal import Decimal
import re
from search import retrieve
from table_qa import UNITS, company_names, get_fact, metric_for

def format_value(fact):
    v=Decimal(fact['value'])
    return f'{v:,.2f}%' if fact['unit']=='%' else f'{v:,.0f}{fact["unit"]}' if v==v.to_integral_value() else f'{v:,.2f}{fact["unit"]}'

def normalized(fact):
    value=Decimal(fact['value'])
    return value if fact['unit']=='%' else value*UNITS[fact['unit']]

def answer_question(index,question,selection=None,k_per_company=2):
    companies=company_names(index,question,selection)
    known=sorted({c['company'] for c in index['chunks']})
    if selection and selection!='全部' and not any(c in question for c in known) and '银行' in question and not any(x in question for x in ('该银行','本行','这家银行')):
        companies=[]
    if not companies and any(x in question for x in ('全部银行','所有银行','各家银行','11家银行','十一家银行')):
        companies=sorted({c['company'] for c in index['chunks']})
    years=list(dict.fromkeys(re.findall(r'(?<!\d)(20\d{2})(?!\d)',question)))
    metric=metric_for(question)
    unsupported=any(x in question for x in ('同比','增长率','增幅','变化','增长','减少','差额','差距','比上年','核心一级资本充足率','一级资本充足率','半年','上半年','季度','个人贷款','对公贷款','单体','母行','预测'))
    asks_revenue=any(x in question for x in ('营业收入','营收'))
    asks_profit=any(x in question for x in ('归母净利润','归母利润','归属于母公司股东的净利润','归属于本行股东的净利润'))
    asks_quality=any(x in question for x in ('不良贷款率','不良率'))
    asks_coverage='拨备覆盖率' in question
    if sum((asks_revenue,asks_profit,asks_quality,asks_coverage))>1: unsupported=True
    if not companies or not metric or len(years)!=1 or unsupported:
        reason='请明确公司、一个年份和指标（如营业收入、不良贷款率、拨备覆盖率、归母净利润）。'
        return {'status':'需要明确问题','answer':reason,'facts':[],'sources':retrieve(index,question,k=6,company=selection if selection and selection!='全部' else None),'recall':{}}
    year=int(years[0]); facts=[]; missing=[]; recall={}; sources=[]
    for company in companies:
        fact=get_fact(index,company,metric,year)
        if fact: facts.append(fact); sources.append(fact)
        else: missing.append(company)
        company_question=question
        for other in companies:
            if other!=company: company_question=company_question.replace(other,'')
        chunks=retrieve(index,company_question,k=k_per_company,company=company)
        recall[company]=chunks
    # Source references are stable: all reconstructed rows first, then retrieval blocks.
    seen={c['id'] for c in sources}
    for chunks in recall.values():
        for c in chunks:
            if c['id'] not in seen: sources.append(c); seen.add(c['id'])
    if not facts:
        return {'status':'证据不足','answer':f'未能在所选报告中可靠还原 {year} 年{metric}的年份、数值和单位，无法作答。','facts':[],'sources':sources,'recall':recall,'missing':missing}
    lines=[f"{f['company']}：{year}年{metric}为 **{format_value(f)}** [{i}]。" for i,f in enumerate(facts,1)]
    wants_compare=len(companies)>1 and any(x in question for x in ('更高','更低','最高','最低','谁高','谁低','排名','比较'))
    if missing:
        lines.append('**证据不足：**未能可靠还原'+ '、'.join(missing)+'的数据，因此不作完整比较或排名。')
    elif wants_compare and len(facts)>1:
        low=any(x in question for x in ('更低','最低','谁低'))
        ordered=sorted(facts,key=normalized,reverse=not low)
        best=normalized(ordered[0]); winners=[f['company'] for f in ordered if normalized(f)==best]
        direction='较低' if low else '较高'
        # A generic “比较” gets a list only; do not guess the intended direction.
        if any(x in question for x in ('更高','更低','最高','最低','谁高','谁低')):
            cites=''.join(f'[{i}]' for i in range(1,len(facts)+1))
            if len(winners)==len(facts): lines.append('按上述同一指标比较，**数值相同**。'+cites)
            else: lines.append('按上述同一指标比较，**'+ '、'.join(winners)+direction+'**。'+cites)
        elif '排名' in question:
            ascending='从低到高' in question
            ordered=sorted(facts,key=normalized,reverse=not ascending)
            description='、'.join(f'{f["company"]}（{format_value(f)}）' for f in ordered)
            lines.append(f'按数值从{"低到高" if ascending else "高到低"}排列：{description}。')
    if len(companies)>1: lines.append('比较前请核对报告口径、年度和会计单位。')
    return {'status':'部分回答' if missing else '已回答','answer':'\n\n'.join(lines),'facts':facts,'sources':sources,'recall':recall,'missing':missing}
