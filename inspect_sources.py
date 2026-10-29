import fitz
from pathlib import Path
terms=['不良贷款率','营业收入','归属于母公司股东的净利润','拨备覆盖率']
for p in sorted((Path(__file__).parent/'data/pdf').glob('*.pdf')):
    doc=fitz.open(p)
    print('\n###',p.stem)
    found=0
    for i in range(min(len(doc),35)):
        text=' '.join(doc[i].get_text('text',sort=True).split())
        if any(t in text for t in terms):
            print('PDF page',i+1, text[:1500])
            found+=1
            if found==2: break
