import fitz, re, json, sys, io
from PIL import Image, ImageOps

SUBJ = {
    'chinese': dict(name='國文', n=42, groups=[(24,25),(26,29),(30,32),(33,34),(35,36),(37,38),(39,40),(41,42)]),
    'english': dict(name='英語（閱讀）', n=43, groups=[(20,21),(22,23),(24,26),(27,28),(29,31),(32,34),(35,39),(40,43)]),
    'math':    dict(name='數學', n=25, groups=[(23,25)]),
    'social':  dict(name='社會', n=54, groups=[(44,45),(46,48),(49,51),(52,54)]),
    'science': dict(name='自然', n=50, groups=[(42,43),(44,45),(46,47),(48,50)]),
}
ZOOM = 2.0
import os
_W = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'work')
SRC = os.path.join(_W, 'y115', 'pdf') + '/'
OUT = os.path.join(_W, 'img') + '/'

def lines(p):
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans']).strip()
            if t: yield t, l['bbox']

def footer_top(p):
    top = p.rect.height - 50
    for t, bb in lines(p):
        if bb[1] > 700 and ((re.fullmatch(r'\d{1,2}', t) and abs((bb[0] + bb[2]) / 2 - p.rect.width / 2) < 30) or '請翻頁' in t or '請檢查' in t):
            top = min(top, bb[1] - 4)
    return top

def answers():
    t = fitz.open(SRC + 'answer.pdf')
    rows = {}
    for p in t:
        for line in p.get_text().split('\n'):
            pass
    import subprocess
    txt = subprocess.run(['pdftotext', '-layout', SRC + 'answer.pdf', '-'], capture_output=True, text=True).stdout
    res = {k: {} for k in ['chinese', 'english', 'listen', 'math', 'social', 'science']}
    for line in txt.split('\n'):
        m = re.match(r'^\s+(\d{1,2})\s{3,}(.*)$', line)
        if not m: continue
        q = int(m.group(1)); rest = m.group(2)
        letters = [(mm.start(), mm.group()) for mm in re.finditer(r'[ABCD]', rest)]
        # column positions decide subject
        cols = {}
        for pos, L in letters:
            cols[pos] = L
        res.setdefault('_raw', {})[q] = rest
    return txt

def run(key, cfg=None, src=None, out=None, prefix=''):
    global SRC, OUT
    if src: SRC = src
    if out: OUT = out
    cfg = cfg or SUBJ[key]; d = fitz.open(SRC + key + '.pdf')
    N = cfg['n']
    # collect all candidate lines (page, y0, y1, text, x0)
    L = []
    for pi in range(1, len(d)):
        for t, bb in lines(d[pi]):
            L.append((pi, bb[1], bb[3], t, bb[0]))
    L.sort(key=lambda x: (x[0], x[1]))
    starts = {}; idx = 0
    for q in range(1, N + 1):
        while idx < len(L):
            pi, y0, y1, t, x0 = L[idx]
            if x0 < 112 and re.match(r'^%d\s*[.．]' % q, t):
                starts[q] = (pi, y0 - 3); idx += 1; break
            idx += 1
        else:
            raise SystemExit(f'{key}: cannot find q{q}')
    # stop marker after last question
    stop = None
    for pi, y0, y1, t, x0 in L:
        if (pi, y0) > starts[N] and ('非選擇題' in t or '試題結束' in t or '到此結束' in t):
            stop = (pi, y0 - 3); break
    if True:
        dl = [(pi, y1) for pi, y0, y1, t, x0 in L if (pi, y0) > starts[N] and '(D)' in t]
        stop = (dl[0][0], dl[0][1] + 8) if dl else (starts[N][0], None)
    if cfg.get('groups') is None:
        gs = []
        for pi, y0, y1, t, x0 in L:
            m = re.search(r'(\d+)\s*[～~至\-－]\s*(\d+)\s*題', t) if re.search(r'回答|作答', t) else re.match(r'^\((\d+)\s*[-–]\s*(\d+)\)$', t)
            if m:
                a, b = int(m.group(1)), int(m.group(2))
                if 1 <= a < b <= N and (a, b) not in gs: gs.append((a, b))
        cfg = dict(cfg, groups=gs)
        print(key, 'groups', gs)
    # passage starts
    passage = {}
    for a, b in cfg['groups']:
        prev = starts[a - 1] if a > 1 else (1, 40)
        # find header line between prev and starts[a]
        ps = None
        for pi, y0, y1, t, x0 in L:
            if prev < (pi, y0) < starts[a] and (re.search(r'回答|作答', t) and re.search(r'\d', t) or re.match(r'^[一二三四]、', t)):
                ps = (pi, y0 - 3); break
        if ps is None:
            # end of (D) option of previous question
            dl = [(i, pi, y1) for i, (pi, y0, y1, t, x0) in enumerate(L) if prev < (pi, y0) < starts[a] and '(D)' in t]
            if dl:
                i, pi_, y1_ = dl[0]
                ps = (pi_, y1_ + 6)
                j = i + 1; last = (pi_, y1_)
                while j < len(L):
                    lp, ly0, ly1, lt, lx0 = L[j]
                    if lp == last[0] and ly0 > 700 and (re.fullmatch(r'\d{1,2}', lt) or '請翻頁' in lt): j += 1; continue
                    same = lp == last[0] and ly0 < last[1] + 12
                    nextp = lp == last[0] + 1 and ly0 < 80
                    if (same or nextp) and not lt.startswith('(') and lx0 > 80 and len(lt) < 60 and (lp, ly0) < starts[a]:
                        ps = (lp, ly1 + 6); last = (lp, ly1); j += 1
                    else: break
            else:
                ps = prev
        passage[a] = ps
    gfirst = {a for a, b in cfg['groups']}
    # side figures that start above a question's number line: extend that question upward,
    # blanking the left column (previous question's text) and blanking the figure in the previous crop
    qtop = {}; masks = []
    for q in range(1, N + 1):
        pi, y = starts[q]; p = d[pi]; W = p.rect.width
        if q in gfirst: continue
        optfloor = 0
        if q > 1 and starts[q - 1][0] == pi:
            ol = [ly1 for (pj, ly0, ly1, t, lx0) in L if pj == pi and starts[q - 1][1] < ly0 < y and re.match(r'^\s*[\(（][A-DＡ-Ｄ][\)）]', t)]
            if ol: optfloor = max(ol) + 2
        boxes = []
        for b in p.get_text('dict')['blocks']:
            x0, y0, x1, y1 = b['bbox']
            if x0 <= W * 0.40: continue
            if b['type'] == 0:
                txt = ''.join(''.join(s['text'] for s in l['spans']) for l in b.get('lines', []))
                if re.match(r'^\s*[\(（][A-DＡ-Ｄ][\)）]', txt): continue
                if y0 < optfloor: continue
            boxes.append((y0, y1, x0))
        for dr in p.get_drawings():
            r = dr['rect']
            c = dr.get('color') or (0, 0, 0)
            if c[0] > 0.9 and 0.55 < c[1] < 0.8: continue
            if r.height > 8 and r.x0 > W * 0.40: boxes.append((r.y0, r.y1, r.x0))
        lower = starts[q - 1][1] + 16 if (q > 1 and starts[q - 1][0] == pi) else 40
        if q > 1 and starts[q - 1][0] == pi:
            dl = [ly0 for (pj, ly0, ly1, t, lx0) in L if pj == pi and starts[q - 1][1] < ly0 < y and re.match(r'^\s*[\(（][DＤ][\)）]', t)]
            if dl and key == "english": lower = max(lower, max(dl) - 22)
        top = y; xs = W
        while True:
            more = [(y0, x0) for (y0, y1, x0) in boxes if lower < y0 < top - 1 and y1 > (max(top + 4, y + 18) if key == 'english' else top + 4)]
            if not more: break
            top = min(m[0] for m in more); xs = min([xs] + [m[1] for m in more])
        cap = []
        for (cy0, cy1, cx0) in boxes:
            if not (lower < cy0 < top - 1 and top - 14 < cy1 <= top + 4 and cy1 - cy0 < 25): continue
            above = [b for b in boxes if b[0] < cy0 - 2 and b[1] > cy0 - 8]
            below = [b for b in boxes if cy1 - 2 <= b[0] <= cy1 + 22 and b[1] > y + 4]
            if not above and below: cap.append((cy0, cx0))
        if cap: top = min(c[0] for c in cap); xs = min([xs] + [c[1] for c in cap])
        if top < y - 1:
            # include all right-side boxes starting within [top, y)
            xs = min([xs] + [x0 for (y0, y1, x0) in boxes if top - 1 <= y0 < y and y1 > y])
            # never hide the previous question's own text lines that reach into the figure column
            intr = [ly1 for (pj, ly0, ly1, t, lx0) in L if pj == pi and top - 2 <= ly0 < y - 2 and lx0 < xs - 3 and lx0 >= W * 0.3]
            if intr: top = max(intr) + 2
        if top < y - 1:
            qtop[q] = (pi, top - 3)
            masks.append(dict(owner=q, pi=pi, y0=top - 4, y1=y + 1, x0=0, x1=xs - 3))
            masks.append(dict(owner=-q, pi=pi, y0=top - 4, y1=y + 1, x0=xs - 3, x1=W))
    print(key, 'extended', {q: round(starts[q][1] - qtop[q][1]) for q in qtop})
    marks = sorted([v for v in starts.values()] + list(passage.values()) + [stop if stop[1] is not None else (stop[0] + 1, 0)])

    def nxt(pos):
        for m in marks:
            if m > pos: return m
        return (len(d), 0)

    def segs(a, b):
        """regions from pos a until pos b (exclusive)"""
        out = []; pi, y = a
        while True:
            p = d[pi]; bottom = footer_top(p)
            if b[0] == pi:
                if b[1] > y + 5: out.append((pi, y, b[1]))
                break
            out.append((pi, y, bottom))
            pi += 1; y = 28
            if pi >= len(d) or (pi > b[0]): break
        return out

    def render(regs, name, q=None):
        from PIL import ImageDraw
        ims = []
        for pi, y0, y1 in regs:
            p = d[pi]; clip = fitz.Rect(40, y0, p.rect.width - 40, y1)
            pix = p.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=clip, colorspace=fitz.csRGB)
            rgb = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
            import numpy as np
            a = np.asarray(rgb).astype(int)
            pinkmask = (a[:,:,0] - a[:,:,1] > 30) & (a[:,:,0] > 150)
            g = np.asarray(rgb.convert('L')).copy(); g[pinkmask] = 255
            im = Image.fromarray(g.astype('uint8'), 'L')
            dr = ImageDraw.Draw(im)
            for m in masks:
                if m['pi'] != pi or m['y1'] <= y0 or m['y0'] >= y1: continue
                if m['owner'] == q or (m['owner'] < 0 and -m['owner'] != q):
                    dr.rectangle([(m['x0'] - 40) * ZOOM, (m['y0'] - y0) * ZOOM, (m['x1'] - 40) * ZOOM, (m['y1'] - y0) * ZOOM], fill=255)
            inv = ImageOps.invert(im).point(lambda v: 255 if v > 25 else 0)
            bb = inv.getbbox()
            if not bb: continue
            im = im.crop((0, max(0, bb[1] - 6), im.width, min(im.height, bb[3] + 6)))
            ims.append(im)
        if not ims: return None
        W = max(i.width for i in ims); H = sum(i.height for i in ims) + 10 * (len(ims) - 1)
        canvas = Image.new('L', (W, H), 255); y = 0
        for i in ims: canvas.paste(i, (0, y)); y += i.height + 10
        # trim left/right whitespace consistently
        bb = ImageOps.invert(canvas).point(lambda v: 255 if v > 25 else 0).getbbox()
        canvas = canvas.crop((max(0, bb[0] - 8), 0, min(W, bb[2] + 8), H))
        canvas = canvas.quantize(16)
        fn = f'{prefix}{key}_{name}.png'; canvas.save(OUT + fn, optimize=True)
        return fn

    items = []
    gmap = {}
    for a, b in cfg['groups']:
        fn = render(segs(passage[a], starts[a]), f'p{a}')
        for q in range(a, b + 1): gmap[q] = (fn, f'{a}～{b}')
    for q in range(1, N + 1):
        fn = render(segs(qtop.get(q, starts[q]), nxt(starts[q])), f'q{q:02d}', q)
        it = dict(n=q, img=fn)
        if q in gmap: it['passage'] = gmap[q][0]; it['group'] = gmap[q][1]
        items.append(it)
    return items

if __name__ == '__main__':
    import os; os.makedirs(OUT, exist_ok=True)
    data = {}
    for k in SUBJ:
        data[k] = dict(name=SUBJ[k]['name'], items=run(k))
        print(k, len(data[k]['items']))
    json.dump(data, open(os.path.join(_W, 'items_default.json'), 'w'), ensure_ascii=False, indent=1)
