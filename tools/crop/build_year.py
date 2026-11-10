"""Crop one year's official papers into single-question images.
Usage: python3 tools/crop/build_year.py 116 [chinese,english,...]
Needs work/y116/pdf/{answer,chinese,english,math,social,science}.pdf"""
import sys, json, re, fitz, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crop import run, _W
Y = sys.argv[1]; base = os.path.join(_W, f'y{Y}') + '/'; out = os.path.join(_W, 'img') + '/'; os.makedirs(out, exist_ok=True)
subs = sys.argv[2].split(',') if len(sys.argv) > 2 else ['chinese','english','math','social','science']
# answer key by column position
d = fitz.open(base + 'pdf/answer.pdf'); cols = {}
for p in d:
    for w in p.get_text('words'):
        t = w[4].strip('()（）')
        if t in ('國文','閱讀','聽力','數學','社會','自然'): cols.setdefault(t, (w[0]+w[2])/2)
ans = {k: {} for k in cols}
for p in d:
    words = p.get_text('words'); rows = {}
    for w in words:
        if re.fullmatch(r'\d{1,2}', w[4]) and w[0] < cols['國文'] - 20: rows[round(w[1])] = int(w[4])
    for w in words:
        if len(w[4]) == 1 and w[4] in 'ABCD':
            q = next((rows[r] for r in rows if abs(r - round(w[1])) <= 3), None)
            if q is None: continue
            xc = (w[0]+w[2])/2; k = min(cols, key=lambda c: abs(cols[c]-xc)); ans[k][q] = w[4]
m = {'國文':'chinese','閱讀':'english','數學':'math','社會':'social','自然':'science'}
key = {m[c]: ans[c] for c in m}
json.dump(key, open(base + 'key.json', 'w'))
items = json.load(open(base + 'items.json')) if os.path.exists(base + 'items.json') else {}
for k in subs:
    N = len(key[k])
    try:
        its = run(k, dict(n=N, groups=None), base + 'pdf/', out, f'{Y}_')
    except SystemExit as e:
        print('SKIP', k, e); continue
    for it in its: it['ans'] = key[k][it['n']]
    items[k] = dict(items=its)
    print(k, N)
json.dump(items, open(base + 'items.json', 'w'), ensure_ascii=False, indent=1)
