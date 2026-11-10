"""Read pass rates (答對率) and goals from the official 試題分析 PDFs -> data/meta/{Y}.json
Usage: python3 tools/crop/parse_ana.py 116   (needs work/y116/pdf/ana_{subject}.pdf and key.json)"""
import subprocess,re,json,sys,os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crop import _W
ROOT=os.path.dirname(_W)
Y=sys.argv[1]; base=os.path.join(_W,f'y{Y}')+'/'
key=json.load(open(base+'key.json'))
out={}
for k in ['chinese','english','math','social','science']:
    if not os.path.exists(base+f'pdf/ana_{k}.pdf'): print('no analysis pdf for',k); continue
    txt=subprocess.run(['pdftotext','-layout',base+f'pdf/ana_{k}.pdf','-'],capture_output=True,text=True).stdout
    parts=re.split(r'\n\s*第\s*(\d+)\s*題\s*\n',txt); res={}; N=len(key[k])
    for i in range(1,len(parts),2):
        n=int(parts[i]); body=parts[i+1]
        if n in res or n>N: continue
        goal=re.search(r'評量目標[：:]\s*(.+?)\n\s*(命題依據|學習表現)',body,re.S)
        goal=re.sub(r'\s+','',goal.group(1)) if goal else ''
        a=re.search(r'\n\s*([ABCD])\s+(0\.\d+|1\.0+)\s+(-?0\.\d+)',body)
        res[n]=dict(goal=goal,ans=a.group(1) if a else None,p=float(a.group(2)) if a else None)
    out[k]=res
    kk=key[k]; g=lambda n: kk.get(str(n), kk.get(n))
    print(k,len(res),'missing',[n for n in range(1,N+1) if n not in res],'mismatch',[n for n,v in res.items() if v['ans']!=g(n)],'nogoal',[n for n,v in res.items() if not v['goal']])
json.dump(out,open(base+'ana.json','w'),ensure_ascii=False,indent=1)
if not out: sys.exit('no analysis PDFs found; nothing written')
meta={k:{str(n):dict(goal=v['goal'],pr=round(v['p']*100)) for n,v in r.items() if v['p'] is not None} for k,r in out.items()}
json.dump(meta,open(os.path.join(ROOT,'data','meta',f'{Y}.json'),'w'),ensure_ascii=False,indent=0)
print('wrote data/meta/'+Y+'.json')
