"""Replicate the H1-H9 hypotheses on this archive.

Run analysis/enrich.py first. Needs analysis/.cache/sectors.json for H3 and H4.
"""
import os,sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.join(ROOT,'analysis'))
D=os.path.join(ROOT,'analysis','.cache')+os.sep
CACHE=os.path.join(ROOT,'analysis','.pricecache')
os.makedirs(D,exist_ok=True)
import json,collections,statistics,math,datetime as dt
import backtest as B

E=json.load(open(D+'enriched.json'))
SEC=json.load(open(D+'sectors.json'))
for r in E: r['sector']=SEC.get(r['ticker'])

def dedupe(rows):
    g=collections.defaultdict(list)
    for r in rows: g[(r['ticker'],r['event_date'],r['session'])].append(r)
    out=[]
    for v in g.values():
        if len({x['side'] for x in v})>1: continue
        out.append(sorted(v,key=lambda x:-abs(x['score']))[0])
    return out

TRADED=dedupe([r for r in E if abs(r['score'])>35 and r['rev']<40])
ALL=dedupe([r for r in E if r['side']!=0])
print(f"samples: traded book n={len(TRADED)}   all directional events n={len(ALL)}")

def welch(a,b):
    if len(a)<3 or len(b)<3: return float('nan')
    va=statistics.variance(a)/len(a); vb=statistics.variance(b)/len(b)
    if va+vb==0: return float('nan')
    return (statistics.mean(b)-statistics.mean(a))/math.sqrt(va+vb)
def desc(s,key='ret'):
    v=[r[key] for r in s if r[key] is not None]
    if not v: return (0,float('nan'),float('nan'))
    return (len(v),100*sum(1 for x in v if x>0)/len(v),100*statistics.mean(v))
def split(sample,pred,la,lb,key='ret'):
    a=[r for r in sample if r[key] is not None and not pred(r)]
    b=[r for r in sample if r[key] is not None and pred(r)]
    na,ha,ma=desc(a,key); nb,hb,mb=desc(b,key)
    t=welch([r[key] for r in a],[r[key] for r in b])
    return f"  {lb:<34} n={nb:<4} hit {hb:>5.1f}%  avg {mb:>+6.2f}%\n  {la:<34} n={na:<4} hit {ha:>5.1f}%  avg {ma:>+6.2f}%\n  -> diff {mb-ma:>+6.2f}pp   t={t:>5.2f}"
def paired(sample,k1,k2,l1,l2):
    d=[r[k2]-r[k1] for r in sample if r[k1] is not None and r[k2] is not None]
    if len(d)<3: return '  n/a'
    t=statistics.mean(d)/(statistics.stdev(d)/math.sqrt(len(d)))
    return (f"  paired n={len(d)}  {l2} minus {l1}: {100*statistics.mean(d):+.2f}pp   "
            f"t={t:.2f}   {sum(1 for x in d if x>0)}/{len(d)} in favour of {l2}")

for name,S in (('TRADED BOOK',TRADED),('ALL DIRECTIONAL EVENTS',ALL)):
    print('\n'+'='*78); print(name,f'(n={len(S)})'); print('='*78)
    print('\nH1  BMO vs AMC')
    print(split(S,lambda r:r['session']=='BMO','AMC','BMO'))
    print('\nH2a AMC: exit at next open vs at next close')
    print(paired([r for r in S if r['session']=='AMC'],'ret_close','ret_open','close','open'))
    print('\nH2b BMO: exit at close vs at open (and vs 19:30 CET)')
    print(paired([r for r in S if r['session']=='BMO'],'ret_open','ret_close','open','close'))
    print(paired([r for r in S if r['session']=='BMO'],'ret_1330','ret_close','19:30 CET','close'))
    print('\nH3  consumer-facing names (proxy for retail tilt)')
    print(split(S,lambda r:r['sector'] in ('Consumer Cyclical','Consumer Defensive'),'other sectors','consumer sectors'))
    print('\nH4  sector breakdown')
    g=collections.defaultdict(list)
    for r in S: g[r['sector'] or 'unknown'].append(r)
    for k,v in sorted(g.items(),key=lambda kv:-statistics.mean([x['ret'] for x in kv[1]])):
        n,h,m=desc(v)
        if n>=4: print(f"  {k:<24} n={n:<4} hit {h:>5.1f}%  avg {m:>+6.2f}%")
    print('\nH5  call points with the 5-session pre-event drift (proxy for lean)')
    al=[r['side']*r['mom'] for r in S if r['mom'] is not None]
    cut=statistics.median(al)
    print(f"  (split at the median aligned drift, {100*cut:+.2f}%)")
    print(split(S,lambda r:r['mom'] is not None and r['side']*r['mom']>=cut,'against/flat vs price','with the price'))
    print('\nH6  conviction floor (proxy: |direction_score|)')
    print(split(S,lambda r:abs(r['score'])>=45,'|score| < 45','|score| >= 45'))
    print(split(S,lambda r:r['rev']<40,'reversal risk >= 40','reversal risk < 40'))
    print('\nH7  more sources cited')
    print(split(S,lambda r:r['nsrc']>=4,'fewer than 4 sources','4+ sources'))
    print('\nH8  thinly traded names')
    dv=sorted(r['dollar_vol'] for r in S if r['dollar_vol'])
    med=dv[len(dv)//2]
    print(f"  (median pre-event dollar volume ${med/1e6:.1f}m)")
    print(split(S,lambda r:r['dollar_vol'] and r['dollar_vol']<med,'above median volume','below median volume'))
