"""Score every prediction in history/ against the realised move.

Adds alternative exits (open / 19:30 CET / close), five-session pre-event drift and
pre-event dollar volume, so the hypothesis tests in hypotheses.py can run.
Writes analysis/.cache/enriched.json.
"""
import os,sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.join(ROOT,'analysis'))
D=os.path.join(ROOT,'analysis','.cache')+os.sep
CACHE=os.path.join(ROOT,'analysis','.pricecache')
os.makedirs(D,exist_ok=True)
import json,collections,statistics,math,datetime as dt
import backtest as B
ET=dt.timezone(dt.timedelta(hours=-4))


def load_full(tickers):
    px={}
    for t in tickers:
        doc=json.load(open(os.path.join(CACHE,f'{t}.json')))
        q=doc['indicators']['quote'][0]
        bars=collections.defaultdict(dict)
        for i,s in enumerate(doc.get('timestamp') or []):
            loc=dt.datetime.fromtimestamp(s,ET)
            bars[loc.date().isoformat()][loc.strftime('%H:%M')]=(q['open'][i],q['close'][i],q['volume'][i])
        px[t]=dict(bars)
    return px

rows=B.load_predictions()
tick=sorted({r['ticker'] for r in rows})
px=load_full(tick)
cal=sorted({d for t in px for d in px[t]})
calset=set(cal)
def shift(day,step,n=1):
    x=dt.date.fromisoformat(day)
    c=0
    for _ in range(20):
        x+=dt.timedelta(days=step)
        if x.isoformat() in calset:
            c+=1
            if c==n: return x.isoformat()
    return None
def day_bars(t,d): return px.get(t,{}).get(d,{})
def sess_close(t,d):
    b=day_bars(t,d)
    ks=sorted(b)
    return b[ks[-1]][1] if ks else None
def sess_open(t,d):
    b=day_bars(t,d).get('09:30')
    return b[0] if b else None
def dollar_vol(t,d):
    b=day_bars(t,d); tot=0
    for k,v in b.items():
        if v[2] and v[1]: tot+=v[2]*v[1]
    return tot or None

out=[]
for r in rows:
    ed=r['event_date']; tk=r['ticker']
    entry_day = ed if r['session']=='AMC' else shift(ed,-1)
    if not entry_day: continue
    b=day_bars(tk,entry_day).get('13:30')
    if not b or not b[0] or not b[1]: continue
    entry=(b[0]+b[1])/2
    side=1 if r['score']>0 else (-1 if r['score']<0 else 0)
    if r['session']=='AMC':
        xday=shift(ed,1)
    else:
        xday=ed
    if not xday: continue
    p_open=sess_open(tk,xday); p_1330=(day_bars(tk,xday).get('13:30') or [None])[0]; p_close=sess_close(tk,xday)
    if not (p_open and p_close): continue
    base_exit = p_open if r['session']=='AMC' else p_1330
    if not base_exit: continue
    # pre-event 5-session momentum up to entry
    d5=shift(entry_day,-1,5)
    pre=sess_close(tk,d5) if d5 else None
    mom=(entry/pre-1) if pre else None
    # liquidity: median dollar volume over the 5 sessions before entry
    dvs=[]
    for k in range(1,6):
        dd=shift(entry_day,-1,k)
        if dd:
            v=dollar_vol(tk,dd)
            if v: dvs.append(v)
    dv=statistics.median(dvs) if dvs else None
    out.append(dict(r,entry_day=entry_day,exit_day=xday,entry_px=entry,
        px_open=p_open,px_1330=p_1330,px_close=p_close,
        side=side,
        ret=side*(base_exit/entry-1),
        ret_open=side*(p_open/entry-1),
        ret_1330=side*(p_1330/entry-1) if p_1330 else None,
        ret_close=side*(p_close/entry-1),
        move=(base_exit/entry-1),
        mom=mom,dollar_vol=dv,
        nsrc=len(r.get('key_sources') or [])))
json.dump(out,open(D+'enriched.json','w'),default=str)
print('enriched',len(out),'of',len(rows))
print('with mom',sum(1 for r in out if r['mom'] is not None),'with dv',sum(1 for r in out if r['dollar_vol']))
