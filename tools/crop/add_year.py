"""Pack a cropped year into the site.
Usage: python3 tools/crop/add_year.py 116
Reads work/y116/items.json + work/img/116_*.png, writes docs/pk/116_{subject}.wasm (lossless WebP images
concatenated) and replaces that year's entries in data/questions.json. Then run: python3 tools/build.py"""
import json, os, io, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crop import _W
ROOT = os.path.dirname(_W); Y = sys.argv[1]
items = json.load(open(os.path.join(_W, f'y{Y}', 'items.json')))
qpath = os.path.join(ROOT, 'data', 'questions.json'); Q = json.load(open(qpath))
for s, v in items.items():
    pk = f'{Y}_{s}'; buf = b''; idx = {}
    def add(name):
        global buf
        if name in idx: return
        im = Image.open(os.path.join(_W, 'img', name + '.png')).convert('L'); o = io.BytesIO()
        im.save(o, 'WEBP', lossless=True, method=6); b = o.getvalue()
        idx[name] = [len(buf), len(b), im.width, im.height]; buf += b
    new = []
    for it in v['items']:
        n = it['n']; img = it['img'][:-4]; add(img)
        q = dict(id=f'{Y}-{s}-{n}', y=Y, n=n, img=img, pk=pk, ans=it['ans'])
        if it.get('passage'): q['pimg'] = it['passage'][:-4]; q['grp'] = f'{Y}-{s}-{it["group"]}'; add(q['pimg'])
        new.append(q)
    open(os.path.join(ROOT, 'docs', 'pk', pk + '.wasm'), 'wb').write(buf)
    Q['questions'] = [q for q in Q['questions'] if not (q['y'] == Y and q['id'].split('-')[1] == s)] + new
    Q['packs'][pk] = idx
    print(pk, len(new), 'questions', round(len(buf) / 1e6, 2), 'MB')
json.dump(Q, open(qpath, 'w'), ensure_ascii=False, separators=(',', ':'))
