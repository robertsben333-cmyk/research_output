"""Retail tilt: a proxy for how much of the trading in a name looks like consumer money.

No free ownership source exists (Yahoo's holders breakdown sits behind a crumb, 13F data is
quarterly and institutional only), so four observable things that all point the same way:

  churn      daily dollar volume over market cap, in percent - a name that turns over a large
             share of itself every day is being traded, not held
  small cap  institutional mandates have floors, so a $200m company is bought mainly by people
             (entered inverted: smaller is higher)
  low price  under roughly $20 is where retail concentrates, the most cited retail marker in the
             literature (also inverted)
  volatility 20-day realised, annualised

Each is turned into a percentile over the whole sample and the four percentiles are averaged,
giving 0-100. At least two of the four must be available or the tilt is null. The components
travel along in retail_parts so it is visible which one carries the number.

Writes analysis/.cache/tilt.json. Run analysis/enrich.py first.
"""
import os, sys, json, math, statistics, collections, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'analysis'))
D = os.path.join(ROOT, 'analysis', '.cache') + os.sep
DAILY = os.path.join(D, 'daily')

VOL_WINDOW = 20
CHURN_WINDOW = 20
MIN_PARTS = 2


def load_daily(ticker):
    """date -> (close, volume) from the cached daily bars."""
    doc = json.load(open(os.path.join(DAILY, ticker + '.json')))
    q = doc['indicators']['quote'][0]
    out = {}
    for i, stamp in enumerate(doc.get('timestamp') or []):
        day = dt.datetime.utcfromtimestamp(stamp).date().isoformat()
        c, v = q['close'][i], q['volume'][i]
        if c:
            out[day] = (c, v or 0)
    return out


def percentile_ranks(values):
    """value -> percentile 0-100, ties averaged. None values are skipped."""
    present = sorted(v for v in values if v is not None)
    n = len(present)
    if n < 2:
        return {}
    ranks, i = {}, 0
    while i < n:
        j = i
        while j + 1 < n and present[j + 1] == present[i]:
            j += 1
        ranks[present[i]] = 100.0 * ((i + j) / 2) / (n - 1)
        i = j + 1
    return ranks


def build():
    events = json.load(open(D + 'enriched.json'))
    shares = json.load(open(D + 'shares.json'))
    daily = {}
    raw = []
    for e in events:
        t = e['ticker']
        if t not in daily:
            try:
                daily[t] = load_daily(t)
            except Exception:
                daily[t] = {}
        bars = daily[t]
        days = sorted(d for d in bars if d < e['entry_day'])
        price = e['entry_px']
        info = shares.get(t) or {}
        so = info.get('shares')
        mcap = so * price if so else info.get('mcap')

        win = days[-CHURN_WINDOW:]
        dvs = [bars[d][0] * bars[d][1] for d in win if bars[d][1]]
        churn = (100.0 * statistics.median(dvs) / mcap) if (dvs and mcap) else None

        vwin = days[-(VOL_WINDOW + 1):]
        rets = [math.log(bars[vwin[i + 1]][0] / bars[vwin[i]][0])
                for i in range(len(vwin) - 1) if bars[vwin[i]][0] > 0]
        vol = (100 * statistics.stdev(rets) * math.sqrt(252)) if len(rets) >= 10 else None

        raw.append(dict(key=(e['agent'], e['ticker'], e['event_date'], e['session']),
                        churn=churn, mcap=mcap, price=price, vol=vol))

    ranks = {k: percentile_ranks([r[k] for r in raw]) for k in ('churn', 'mcap', 'price', 'vol')}
    out = {}
    for r in raw:
        parts = {}
        for k, invert in (('churn', False), ('mcap', True), ('price', True), ('vol', False)):
            v = r[k]
            if v is None or v not in ranks[k]:
                continue
            p = ranks[k][v]
            parts[k] = round(100.0 - p if invert else p, 1)
        tilt = round(statistics.mean(parts.values()), 1) if len(parts) >= MIN_PARTS else None
        out['|'.join(r['key'])] = dict(tilt=tilt, retail_parts=parts,
                                       churn=r['churn'], mcap=r['mcap'],
                                       price=r['price'], vol=r['vol'])
    json.dump(out, open(D + 'tilt.json', 'w'))

    tilts = [v['tilt'] for v in out.values() if v['tilt'] is not None]
    tilts.sort()
    def q(p):
        return tilts[int(p * (len(tilts) - 1))]
    print(f"{len(out)} events, tilt on {len(tilts)}")
    print(f"tilt   median {q(.5):.1f}   quartiles {q(.25):.1f} / {q(.75):.1f}")
    for k, fmt in (('churn', '{:.2f}%'), ('mcap', '${:,.0f}m'), ('price', '${:.2f}'), ('vol', '{:.1f}')):
        vals = sorted(v[k] for v in out.values() if v[k] is not None)
        m = vals[len(vals) // 2]
        print(f"  median {k:<6} " + fmt.format(m / 1e6 if k == 'mcap' else m))
    miss = collections.Counter(len(v['retail_parts']) for v in out.values())
    print('  components available:', dict(sorted(miss.items())))


if __name__ == '__main__':
    build()
