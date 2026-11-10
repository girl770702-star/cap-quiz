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

# ---- 自然科重點筆記 (data/notes/): optional; page hides the button when absent ----
notes = None
if os.path.exists(D('data', 'notes', 'science.json')):
    import re, collections, xml.etree.ElementTree as ET
    nd = json.load(open(D('data', 'notes', 'science.json')))
    cls = json.load(open(D('data', 'notes', 'science_class.json')))
    unit_defs = json.load(open(D('data', 'notes', 'units.json')))
    sci = {q['id']: q for q in bank['science']}
    OK_TAGS = {'p', 'ul', 'ol', 'li', 'b', 'br', 'sub', 'sup', 'span', 'table', 'thead', 'tbody', 'tr', 'th', 'td'}
    def chk_html(h, where):
        for m in re.finditer(r'<\s*/?\s*([a-zA-Z0-9]+)', h):
            if m.group(1).lower() not in OK_TAGS: err.append(f'notes {where}: tag <{m.group(1)}> not allowed')
        if re.search(r'\bon\w+\s*=|style\s*=|javascript:', h, re.I): err.append(f'notes {where}: style/event attribute not allowed')
    def split_svgs(s, where):
        SV = r'<svg\b.*?</svg>'
        parts = re.findall(SV, s, re.S)
        if not parts or re.sub(SV, '', s, flags=re.S).strip():
            err.append(f'notes {where}: svg field must contain only <svg>...</svg> elements'); return []
        for x in parts:
            if re.search(r'<\s*(script|image|style|foreignObject)|\bon\w+\s*=', x, re.I) or re.search(r"href\s*=\s*[\"'](?!#)", x, re.I):
                err.append(f'notes {where}: unsafe svg')
            try: ET.fromstring(x)
            except ET.ParseError as e: err.append(f'notes {where}: svg not well-formed ({e})')
        return parts
    svg_n = [0]
    def uniq_svg(s):
        """Several inline SVGs share one page: prefix every id (e.g. the arrow marker) so references never hit a hidden or other figure."""
        svg_n[0] += 1; pre = f's{svg_n[0]}-'
        ids = set(re.findall(r'\bid="([^"]+)"', s))
        for i in ids:
            s = s.replace(f'id="{i}"', f'id="{pre}{i}"').replace(f'url(#{i})', f'url(#{pre}{i})').replace(f'href="#{i}"', f'href="#{pre}{i}"')
        return s
    written = {u['id']: u for u in nd['units']}
    for u in nd['units']:
        if u['id'] not in {d['id'] for d in unit_defs}: err.append(f'notes: unknown unit {u["id"]}')
    notes = {'units': []}
    for d in unit_defs:
        yrs = collections.Counter(); qids = []
        for qid, v in cls.items():
            if v['u'] == d['id']: yrs[qid.split('-')[0]] += 1; qids.append(qid)
        qids.sort(key=lambda i: (int(i.split('-')[0]), int(i.split('-')[2])))
        prs = [sci[i]['pr'] for i in qids if i in sci and 'pr' in sci[i]]
        e = dict(id=d['id'], g=d['g'], name=d['name'], n=len(qids), yrs=dict(yrs), qs=qids,
                 pr=round(sum(prs) / len(prs)) if len(prs) >= 2 else None, prn=len(prs))
        w = written.get(d['id'])
        if w:
            e['core'] = w.get('core', '')
            e['points'] = []; e['traps'] = []
            for k, p in enumerate(w.get('points', [])):
                loc = f'{d["id"]} point {k + 1}'
                chk_html(p['html'], loc)
                parts = split_svgs(p['svg'], loc) if p.get('svg') else []
                for i in p.get('qs', []):
                    if cls.get(i, {}).get('u') != d['id']: err.append(f'notes {loc}: {i} is not a {d["id"]} question')
                pp = {k2: p[k2] for k2 in ('t', 'html', 'svg', 'qs') if p.get(k2)}
                if parts: pp['svg'] = [uniq_svg(x) for x in parts]
                e['points'].append(pp)
            for k, p in enumerate(w.get('traps', [])):
                loc = f'{d["id"]} trap {k + 1}'
                for i in p.get('qs', []):
                    if cls.get(i, {}).get('u') != d['id']: err.append(f'notes {loc}: {i} is not a {d["id"]} question')
                e['traps'].append({k2: p[k2] for k2 in ('t', 'd', 'qs') if p.get(k2)})
        notes['units'].append(e)

ids = [q['id'] for s in SUB for q in bank[s]]
if len(ids) != len(set(ids)): err.append('duplicate ids')
if err:
    print('\n'.join(err[:30])); sys.exit(1)

T = D('tools', 'template')
head = open(os.path.join(T, 'head.html')).read().replace('</style>', open(os.path.join(T, 'extra.css')).read() + '</style>')
js = json.dumps(dict(bank=bank, packs=packs, notes=notes),ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
body = open(os.path.join(T, 'body.html')).read().replace('__BANK__', js)
page = ('<!doctype html>\n<html lang="zh-Hant"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>body{margin:0}</style></head><body>\n' + head + body + '\n</body></html>\n')
open(D('docs', 'index.html'), 'w').write(page)
n_exp = {s: sum(1 for q in bank[s] if q.get('exp')) for s in SUB}
print('OK', {s: len(bank[s]) for s in SUB}, 'with explanation:', n_exp)
