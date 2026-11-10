"""Build docs/index.html from data/.  Run from repo root:  python3 tools/build.py"""
import json, glob, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)
SUB = ['chinese', 'english', 'math', 'social', 'science']

src = json.load(open(D('data', 'questions.json')))
packs = src['packs']
exp = {}
for f in glob.glob(D('data', 'explanations', '*', '*.json')):
    y = os.path.basename(os.path.dirname(f)); s = os.path.basename(f)[:-5]
    exp[(y, s)] = json.load(open(f))
meta = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(D('data', 'meta', '*.json'))}

bank = {s: [] for s in SUB}
err = []
for q in src['questions']:
    y, n = q['y'], str(q['n']); s = q['id'].split('-')[1]
    q = dict(q)
    if q['img'] not in packs.get(q['pk'], {}): err.append(f"missing image {q['img']}")
    e = exp.get((y, s), {}).get(n)
    if e:
        if not isinstance(e, str) or not e.strip(): err.append(f'bad explanation {q["id"]}')
        q['exp'] = e
    m = meta.get(y, {}).get(s, {}).get(n)
    if m: q['goal'] = m.get('goal', ''); q['pr'] = m['pr']
    # lv: 0 基礎, 1 中等, 2 較難 (by national pass rate); 3 中等以上 (Claude's own judgement: only years without pass-rate data, and it got an explanation)
    if 'pr' in q: q['lv'] = 0 if q['pr'] >= 60 else (1 if q['pr'] >= 40 else 2)
    elif (y, s) in exp: q['lv'] = 3 if q.get('exp') else 0
    bank[s].append(q)
for (y, s), m in exp.items():
    ids = {str(q['n']) for q in bank[s] if q['y'] == y}
    for n in m:
        if n not in ids: err.append(f'explanation for unknown question {y}-{s}-{n}')

for f in sorted(glob.glob(D('data', 'ak', '*.json'))):
    d = json.load(open(f)); s = d['subject']; tag = os.path.basename(f)[:-5]
    pas = {q['grp']: q['passage'] for q in d['qs'] if q.get('grp') and q.get('passage')}
    for q in d['qs']:
        assert q['ans'] in 'ABCD' and len(q['opts']) == 4, (f, q['n'])
        pre = 'ak' if tag.endswith('_1') else f'ak{tag.split("_")[-1]}'
        e = dict(id=f'{pre}-{s}-{q["n"]}', y='ak', n=q['n'], html=q['html'], opts=q['opts'], ans=q['ans'], exp=q['exp'], topic=q.get('topic', ''))
        if q.get('grp'): e['grp'] = f'{pre}-{s}-{q["grp"]}'; e['passage'] = pas[q['grp']]
        bank[s].append(e)

ids = [q['id'] for s in SUB for q in bank[s]]
if len(ids) != len(set(ids)): err.append('duplicate ids')
if err:
    print('\n'.join(err[:30])); sys.exit(1)

T = D('tools', 'template')
head = open(os.path.join(T, 'head.html')).read().replace('</style>', open(os.path.join(T, 'extra.css')).read() + '</style>')
js = json.dumps(dict(bank=bank, packs=packs), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
body = open(os.path.join(T, 'body.html')).read().replace('__BANK__', js)
page = ('<!doctype html>\n<html lang="zh-Hant"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>body{margin:0}</style></head><body>\n' + head + body + '\n</body></html>\n')
open(D('docs', 'index.html'), 'w').write(page)
n_exp = {s: sum(1 for q in bank[s] if q.get('exp')) for s in SUB}
print('OK', {s: len(bank[s]) for s in SUB}, 'with explanation:', n_exp)
