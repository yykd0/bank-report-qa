"""Conservative coordinate-based reconstruction for simple financial tables.

Only emits a fact if an exact metric row, an explicit multi-year header, and
one value aligned with that header can all be found on the same PDF page.
"""
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import fitz

ROOT=Path(__file__).resolve().parent
YEAR=re.compile(r'^20\d{2}$')
NUMBER=re.compile(r'^[-−]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?$')
METRICS={
 '归母净利润':['归属于母公司股东的净利润','归属于本行股东的净利润','归属于上市公司股东的净利润'],
 '营业收入':['营业收入'],
 '不良贷款率':['不良贷款率'],
 '拨备覆盖率':['拨备覆盖率'],
 '净利息收益率':['净利息收益率'],
 '资本充足率':['资本充足率'],
 '总资产':['总资产','资产总额'],
}
RATIO={'不良贷款率','拨备覆盖率','净利息收益率','资本充足率'}
UNITS={'百万元':Decimal('1000000'),'千元':Decimal('1000'),'万元':Decimal('10000'),'亿元':Decimal('100000000'),'元':Decimal('1')}

def metric_for(question):
    if any(s in question for s in ('归母净利润','归母利润','归属于母公司股东的净利润','归属于本行股东的净利润','归属于上市公司股东的净利润')):
        return '归母净利润'
    if '营收' in question: return '营业收入'
    if '不良率' in question: return '不良贷款率'
    return next((m for m in METRICS if m in question),None)

def company_names(index,question,selection=None):
    companies=sorted({c['company'] for c in index['chunks']})
    mentioned=sorted((c for c in companies if c in question),key=question.index)
    if mentioned: return mentioned
    return [selection] if selection and selection!='全部' else []

def grouped_words(page):
    words=sorted(page.get_text('words'),key=lambda w:(w[1],w[0]))
    rows=[]
    for w in words:
        # Different font baselines in a single printed row can differ slightly.
        candidates=[r for r in rows[-8:] if abs(r['y']-w[1])<=3.5]
        if candidates: candidates[-1]['words'].append(w)
        else: rows.append({'y':w[1],'words':[w]})
    for row in rows: row['words'].sort(key=lambda w:w[0])
    return sorted(rows,key=lambda r:r['y'])

def header_columns(row):
    words=row['words']; columns=[]
    for i,w in enumerate(words):
        t=w[4].strip()
        if not YEAR.fullmatch(t): continue
        edge=w[2]
        for following in words[i+1:]:
            s=following[4].strip()
            if YEAR.fullmatch(s) or following[0]-edge>12: break
            if re.fullmatch(r'(?:年|年\d{1,2}|月\d{1,2}|月|日|\d{1,2}|年度|年末|年初)',s): edge=following[2]
            else: break
        columns.append((int(t),edge))
    # A year repeated within a header makes mapping ambiguous.
    if len(columns)<2 or len({y for y,_ in columns})!=len(columns): return []
    return columns

def find_unit(rows,position):
    for row in reversed(rows[max(0,position-35):position+1]):
        text=''.join(w[4] for w in row['words'])
        if '单位' not in text and '人民币' not in text: continue
        for unit in ('百万元','千元','万元','亿元'):
            if unit in text: return unit
    return None

def row_label_matches(row,metric):
    text=''.join(w[4] for w in row['words'] if w[0]<row['words'][0][0]+210)
    text=re.sub(r'\s+','',text)
    for alias in METRICS[metric]:
        if text.startswith(alias):
            tail=text[len(alias):]
            # Do not confuse revenue ratios or adjusted profit with the requested metric.
            if tail.startswith(('比','占','比例','增速','增长率','的扣除','扣除','同比')): continue
            return alias
    return None

def align_values(columns,values):
    def with_offset(offset,tolerance):
        matched=[]
        for y,edge in columns:
            close=sorted((abs(x-edge-offset),s,x) for s,x in values if abs(x-edge-offset)<tolerance)
            if not close or (len(close)>1 and close[1][0]-close[0][0]<2): return None
            matched.append((y,close[0][1],close[0][2]))
        return matched if len({x for _,_,x in matched})==len(matched) else None
    aligned=with_offset(0,28)
    if aligned: return aligned
    # Some PDFs center year headings far left of right-aligned numeric columns.
    # Require three columns and a unique, consistently shifted assignment.
    if len(columns)<3: return None
    assignments={}
    for _,x in values:
        offset=x-columns[0][1]
        if abs(offset)>80: continue
        candidate=with_offset(offset,6)
        if candidate: assignments[tuple((y,v,pos) for y,v,pos in candidate)]=candidate
    return next(iter(assignments.values())) if len(assignments)==1 else None

def page_facts(page,metric,year):
    rows=grouped_words(page); facts=[]
    for ri,row in enumerate(rows):
        label=row_label_matches(row,metric)
        if not label: continue
        headers=[]
        for h in range(max(0,ri-45),ri):
            columns=header_columns(rows[h])
            if columns and any(y==year for y,_ in columns) and row['y']-rows[h]['y']<260:
                headers.append((h,columns))
        if not headers: continue
        hi,columns=headers[-1]
        if '季度' in ''.join(w[4] for rr in rows[hi:ri] for w in rr['words']): continue
        values=[]
        for w in row['words']:
            s=w[4].strip().replace('−','-')
            if NUMBER.fullmatch(s) and w[0]>row['words'][0][0]+45:
                values.append((s,w[2]))
        aligned=align_values(columns,values)
        if aligned:
            text=next(s for y,s,_ in aligned if y==year); unit='%' if metric in RATIO else find_unit(rows,ri)
            if not unit: continue
            try: value=Decimal(text.replace(',','').rstrip('%'))
            except InvalidOperation: continue
            header=' | '.join(str(y) for y,_,_ in aligned)
            data=' | '.join(v for _,v,_ in aligned)
            facts.append({'metric':metric,'year':year,'value':str(value),'unit':unit,
                          'row_label':label,'table':f'项目 | {header}\n{label} | {data}\n单位：{unit}',
                          'header_y':round(rows[hi]['y'],1),'row_y':round(row['y'],1)})
    return facts

def get_fact(index,company,metric,year):
    chunks=[c for c in index['chunks'] if c['company']==company]
    if not chunks: return None
    report=chunks[0]
    # Half-year disclosures do not establish an annual value.
    if '半年度' in report['period']: return None
    # Prefer compact financial-summary pages; candidates remain tied to indexed text.
    pages=sorted({c['page'] for c in chunks if c['page']<=60 and any(x in c['text'] for x in METRICS[metric])})
    path=ROOT/'data'/'pdf'/f'{company}.pdf'
    if not path.exists(): return None
    with fitz.open(path) as doc:
        for pno in pages:
            for fact in page_facts(doc[pno-1],metric,year):
                # Metadata comes from the indexed page; the reconstructed row is evidence.
                page_chunk=next(c for c in chunks if c['page']==pno)
                return {**fact,'company':company,'period':report['period'],'url':report['url'],
                        'page':pno,'section':page_chunk['section'],'kind':'坐标还原表格',
                        'id':f'{company}-p{pno}-row-{int(fact["row_y"])}',
                        'text':fact['table']}
    return None
