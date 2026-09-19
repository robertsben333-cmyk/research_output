"""H9: does heavy search interest before the print make for a worse trade?

Google Trends daily interest for "<TICKER> stock", 1 May - 18 Sep 2026, one series per ticker
(analysis/.cache/trends). For each event:

  baseline  median interest over the 30 days ending 6 days before entry
  peak      highest interest over the 5 days up to and including entry day
  ratio     peak / baseline      - how far above normal the run-up spiked
  level     median of those 5 days / baseline - how busy the name was overall

The peak ratio is above 1 by construction, so a cut at 0.88 can only be read against the level
ratio, which is centred on 1. Both are reported.

Trends rescales each series to 0-100 within the requested window, and thin terms come back as
mostly zeros. A series whose baseline is zero, or that has fewer than 20 non-zero days, counts as
not measured - which systematically keeps the liquid half of the universe.

Run analysis/enrich.py first.
"""
import os, sys, json, statistics, math, collections, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'analysis'))
D = os.path.join(ROOT, 'analysis', '.cache') + os.sep
TRENDS = os.path.join(D, 'trends')

BASE_WINDOW, BASE_GAP, PEAK_WINDOW, MIN_NONZERO = 30, 6, 5, 20


def load_series(ticker):
    fn = os.path.join(TRENDS, ticker + '.json')
    if not os.path.exists(fn):
        return None
    s = json.load(open(fn)).get('series') or {}
    return {k: v for k, v in s.items()} or None


def ratio(series, entry_day):
    days = sorted(series)
    if sum(1 for d in days if series[d] > 0) < MIN_NONZERO:
        return None
    e = dt.date.fromisoformat(entry_day)
    peak_win = [series[d] for d in days
                if 0 <= (e - dt.date.fromisoformat(d)).days < PEAK_WINDOW]
    base_win = [series[d] for d in days
                if BASE_GAP <= (e - dt.date.fromisoformat(d)).days < BASE_GAP + BASE_WINDOW]
    if len(peak_win) < 3 or len(base_win) < 15:
        return None
    base = statistics.median(base_win)
    if base <= 0:
        return None
    return max(peak_win) / base, statistics.median(peak_win) / base


def welch(a, b):
    va, vb = statistics.variance(a) / len(a), statistics.variance(b) / len(b)
    return (statistics.mean(b) - statistics.mean(a)) / math.sqrt(va + vb)


def desc(rows):
    r = [x['ret'] for x in rows]
    return len(r), 100 * sum(1 for x in r if x > 0) / len(r), 100 * statistics.mean(r), 100 * statistics.median(r)


def main():
    events = json.load(open(D + 'enriched.json'))
    tilt = json.load(open(D + 'tilt.json'))
    series = {}
    for e in events:
        t = e['ticker']
        if t not in series:
            series[t] = load_series(t)
        r = ratio(series[t], e['entry_day']) if series[t] else None
        e['search'], e['search_level'] = r if r else (None, None)
        e['tilt'] = (tilt.get('|'.join([e['agent'], e['ticker'], e['event_date'], e['session']])) or {}).get('tilt')

    def ded(rows):
        g = collections.defaultdict(list)
        for r in rows:
            g[(r['ticker'], r['event_date'], r['session'])].append(r)
        return [sorted(v, key=lambda x: -abs(x['score']))[0]
                for v in g.values() if len({x['side'] for x in v}) == 1]

    directional = ded([r for r in events if r['side'] != 0])
    traded = ded([r for r in events if abs(r['score']) > 35 and r['rev'] < 40])
    for name, sample in (('TRADED BOOK', traded), ('ALL DIRECTIONAL EVENTS', directional)):
        have = [r for r in sample if r['search'] is not None]
        print(f"\n{'=' * 72}\n{name}: {len(have)} of {len(sample)} events have a usable search series\n{'=' * 72}")
        if len(have) < 12:
            print('  too few to test')
            continue
        med = statistics.median([r['search'] for r in have])
        print(f"  search ratio: median {med:.2f}, quartiles "
              f"{statistics.quantiles([r['search'] for r in have], n=4)[0]:.2f} / "
              f"{statistics.quantiles([r['search'] for r in have], n=4)[2]:.2f}")
        lmed = statistics.median([r['search_level'] for r in have])
        print(f"  level ratio:  median {lmed:.2f}")
        for label, cut, key in (('peak ratio, sample median %.2f' % med, med, 'search'),
                                ('level ratio, their cut 0.88', 0.88, 'search_level'),
                                ('level ratio, sample median %.2f' % lmed, lmed, 'search_level')):
            quiet = [r for r in have if r[key] < cut]
            loud = [r for r in have if r[key] >= cut]
            if len(quiet) < 5 or len(loud) < 5:
                continue
            nq, hq, mq, dq = desc(quiet)
            nl, hl, ml, dl = desc(loud)
            t = welch([r['ret'] for r in loud], [r['ret'] for r in quiet])
            print(f"\n  split at {label}")
            print(f"    quiet  (< cut)  n={nq:<4} hit {hq:>5.1f}%  avg {mq:>+6.2f}%  median {dq:>+6.2f}%")
            print(f"    loud   (>= cut) n={nl:<4} hit {hl:>5.1f}%  avg {ml:>+6.2f}%  median {dl:>+6.2f}%")
            print(f"    -> quiet minus loud {mq - ml:>+6.2f}pp   t={t:>5.2f}")
        xs = [r['search'] for r in have]
        ys = [r['ret'] for r in have]
        mx, my = statistics.mean(xs), statistics.mean(ys)
        sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
        sy = math.sqrt(sum((y - my) ** 2 for y in ys))
        r = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)
        print(f"\n  correlation of search ratio with the trade's return: r={r:+.3f}  "
              f"t={r * math.sqrt((len(xs) - 2) / (1 - r * r)):+.2f}")


if __name__ == '__main__':
    main()
