"""Fallback: crop questions from the official 試題分析 PDF when the paper PDF is unusable.
Usage: python3 tools/crop/crop_ana.py 113 social   (needs work/y113/pdf/ana_social.pdf and key.json from build_year.py)"""
import fitz, re, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crop import _W
from PIL import Image, ImageOps
Y, key = sys.argv[1], sys.argv[2]
base = os.path.join(_W, f'y{Y}') + '/'; OUT = os.path.join(_W, 'img') + '/'; Z = 2.4; os.makedirs(OUT, exist_ok=True)
d = fitz.open(base + f'pdf/ana_{key}.pdf')
keyans = json.load(open(base + 'key.json'))[key]; N = len(keyans)
L = []
for pi, p in enumerate(d):
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans']).strip()
            if t: L.append((pi, l['bbox'], t))
qpos = {}; goal = {}; hdr = []
for pi, bb, t in L:
    m = re.fullmatch(r'第\s*(\d+)\s*題', t)
    if m and int(m.group(1)) <= N and int(m.group(1)) not in qpos: qpos[int(m.group(1))] = (pi, bb)
    m = re.search(r'回答第?\s*(\d+)\s*(?:至|～|~|－|-)\s*(\d+)\s*題', t)
    if m: hdr.append((int(m.group(1)), int(m.group(2)), pi, bb))
for pi, bb, t in L:
    if t.startswith('評量目標'):
        for q, (qp, qb) in qpos.items():
            if qp == pi and qb[1] < bb[1] and q not in goal: goal[q] = (pi, bb); break
def save(im, name):
    bb = ImageOps.invert(im).point(lambda v: 255 if v > 25 else 0).getbbox()
    im = im.crop((max(0, bb[0]-8), max(0, bb[1]-6), min(im.width, bb[2]+8), min(im.height, bb[3]+6))).quantize(16)
    fn = f'{Y}_{key}_{name}.png'; im.save(OUT + fn, optimize=True); return fn
def clip(pi, x0, y0, x1, y1):
    pix = d[pi].get_pixmap(matrix=fitz.Matrix(Z, Z), clip=fitz.Rect(x0, y0, x1, y1), colorspace=fitz.csGRAY)
    return Image.frombytes('L', (pix.width, pix.height), pix.samples)
items = []; gmap = {}
for a, b, pi, bb in hdr:
    qp, qb = qpos[a]
    im = clip(pi, 40, bb[1] - 3, d[pi].rect.width - 40, (qb[1] - 3) if qp == pi else d[pi].rect.height - 50)
    fn = save(im, f'p{a}')
    for q in range(a, b + 1): gmap[q] = (fn, f'{a}～{b}')
for q in range(1, N + 1):
    pi, qb = qpos[q]; gp, gb = goal[q]; assert gp == pi, q
    # find the 題目 label to set left edge
    lab = [bb for (pj, bb, t) in L if pj == pi and t == '題目' and qb[1] < bb[1] < gb[1]]
    x0 = lab[0][2] + 4 if lab else 90
    # mask: draw page region
    im = clip(pi, x0, qb[3] + 2, d[pi].rect.width, gb[1] - 2)
    # remove table border lines: whiten thin full-height/width dark lines at edges
    w, h = im.size; px = im.load()
    for x in range(w):
        if sum(1 for yy in range(h) if px[x, yy] < 120) > 0.85 * h:
            for yy in range(h): px[x, yy] = 255
    for yy in range(h):
        if sum(1 for x in range(w) if px[x, yy] < 120) > 0.85 * w:
            for x in range(w): px[x, yy] = 255
    it = dict(n=q, img=save(im, f'q{q:02d}'), ans=keyans[str(q)] if isinstance(list(keyans)[0], str) else keyans[q])
    if q in gmap: it['passage'], it['group'] = gmap[q]
    items.append(it)
allit = json.load(open(base + 'items.json')); allit[key] = dict(items=items, source='analysis')
json.dump(allit, open(base + 'items.json', 'w'), ensure_ascii=False, indent=1)
print(key, len(items), 'groups', [(a, b) for a, b, *_ in hdr])
