import hashlib, json
from pathlib import Path
from urllib.request import Request, urlopen

root = Path(__file__).resolve().parent
checksums = json.loads((root / 'checksums.json').read_text(encoding='utf-8'))
for item in json.loads((root / 'reports.json').read_text(encoding='utf-8')):
    dest = root / 'data' / 'pdf' / (item['company'] + '.pdf')
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == checksums[item['company']]['sha256']:
        print('cached and verified', dest.name, flush=True); continue
    req = Request(item['url'], headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.cninfo.com.cn/'})
    with urlopen(req, timeout=120) as response:
        data = response.read()
    if not data.startswith(b'%PDF-'):
        raise ValueError(f'Not a PDF: {item["url"]}')
    if hashlib.sha256(data).hexdigest() != checksums[item['company']]['sha256']:
        raise ValueError(f'PDF checksum changed: {item["url"]}; inspect before use')
    dest.write_bytes(data)
    print(dest.name, len(data), flush=True)
