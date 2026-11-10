"""Export question images as PNG so they can be viewed.
Usage (repo root):
  python3 tools/show.py 113-math-12            # one question (plus its passage if in a group)
  python3 tools/show.py 113 math               # a whole year-subject
Writes to /tmp/show/ and prints answers.  Needs Pillow."""
import json, os, sys, io
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = json.load(open(os.path.join(ROOT, 'data', 'questions.json')))
packs = src['packs']; out = os.environ.get('SHOW_OUT', '/tmp/show'); os.makedirs(out, exist_ok=True)
_buf = {}
def png(pk, name):
    if pk not in _buf: _buf[pk] = open(os.path.join(ROOT, 'docs', 'pk', pk + '.wasm'), 'rb').read()
    o, l, w, h = packs[pk][name]
    p = os.path.join(out, name + '.png')
    Image.open(io.BytesIO(_buf[pk][o:o + l])).save(p); return p
a = sys.argv[1:]
sel = [q for q in src['questions'] if (q['id'] == a[0] if len(a) == 1 else (q['y'] == a[0] and q['id'].split('-')[1] == a[1]))]
seen = set()
for q in sel:
    if q.get('pimg') and q['pimg'] not in seen:
        seen.add(q['pimg']); print('passage', q['grp'], png(q['pk'], q['pimg']))
    print(q['id'], 'ans', q['ans'], png(q['pk'], q['img']))
