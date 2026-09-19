"""Backtest of the ranked earnings predictions in history/*.json.

Rule set (as specified):
  - take a position when |direction_score| > 35 and reversal_risk < 40
  - long if the score is positive, short if negative
  - enter at 20:00 CET on the last session before the announcement
  - exit AMC names at the next market open, BMO names at 19:30 CET on the day
    of the announcement
  - at most 40% of equity in any one stock on any one day

Prices come from Yahoo Finance hourly bars (regular session only). All times in
the sample fall inside US/EU summer time, so CET/CEST is ET + 6h:
20:00 CET = 14:00 ET, 19:30 CET = 13:30 ET.

Usage: python3 analysis/backtest.py  (writes analysis/trades.csv)
"""
import collections
import csv
import datetime as dt
import glob
import json
import math
import os
import re
import statistics
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "analysis", ".pricecache")
ET = dt.timezone(dt.timedelta(hours=-4))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120"}

SCORE_MIN = 35.0      # strictly greater, absolute
REVERSAL_MAX = 40     # strictly less
MAX_WEIGHT = 0.40

# Generated after 20:00 CET, so it was not available at the entry time.
IGNORE_FILES = {"US1-2026-07-21-1829.json"}

MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
AMC_PAT = re.compile(r"\bamc\b|after\s+[\w\.]*\s*(market\s+)?clos|post-?close", re.I)
BMO_PAT = re.compile(
    r"\bbmo\b|before\s+(the\s+)?(u\.s\.\s+)?(market\s+|nyse\s+|nasdaq\s+)?(open|hours)|pre-?market", re.I)


def parse_date(s):
    m = re.search(r"(20\d\d)-(\d\d)-(\d\d)", s)
    if m:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})\b", s, re.I)
    if not m:
        return None
    year = 2026
    m2 = re.search(r",\s*(20\d\d)", s[m.end():m.end() + 8])
    if m2:
        year = int(m2.group(1))
    return dt.date(year, MONTHS[m.group(1)[:3].lower()], int(m.group(2)))


def parse_session(s):
    a, b = AMC_PAT.search(s), BMO_PAT.search(s)
    if a and b:
        return "AMC" if a.start() < b.start() else "BMO"
    if a:
        return "AMC"
    if b:
        return "BMO"
    m = re.search(r"(\d{1,2}):(\d\d)\s*(a\.m\.|am|p\.m\.|pm)\s*ET", s, re.I)
    if m:
        h, ap = int(m.group(1)), m.group(3).lower()
        if ap.startswith("a") and h <= 9:
            return "BMO"
        if ap.startswith("p") and 4 <= h < 9:
            return "AMC"
    m = re.search(r"\b(\d{1,2}):(\d\d)\s*ET\b", s, re.I)
    if m:
        mins = int(m.group(1)) * 60 + int(m.group(2))
        if mins < 9 * 60 + 30:
            return "BMO"
        if mins >= 16 * 60:
            return "AMC"
    return None


def load_predictions():
    rows = []
    for path in sorted(glob.glob(os.path.join(ROOT, "history", "*.json"))):
        base = os.path.basename(path)
        if base in IGNORE_FILES:
            continue
        m = re.match(r"(US\d)-(\d{4}-\d\d-\d\d)(?:-\d{4})?\.json", base)
        if not m:
            continue
        agent, rep_date = m.group(1), dt.date.fromisoformat(m.group(2))
        nxt = rep_date + dt.timedelta(days=1)
        while nxt.weekday() >= 5:
            nxt += dt.timedelta(days=1)
        doc = json.load(open(path))
        for r in doc.get("ranked_companies") or []:
            timing = r.get("timing", "")
            session, date = parse_session(timing), parse_date(timing)
            # fall back on the report window when the timing string is terse
            if session is None and date is not None:
                session = "AMC" if date == rep_date else ("BMO" if date == nxt else None)
            if date is None and session is not None:
                date = rep_date if session == "AMC" else nxt
            if session is None or date is None:
                raise ValueError(f"unparsed timing in {base}: {timing!r}")
            rows.append(dict(agent=agent, file=base, gts=doc.get("generation_timestamp", ""),
                             ticker=r["ticker"], company=r.get("company", ""), timing=timing,
                             session=session, event_date=date.isoformat(),
                             score=float(r["direction_score"]), rev=int(r["reversal_risk"]),
                             call=r.get("direction_call"), conf=r.get("confidence"),
                             disparity=r.get("disparity"), evidence=r.get("evidence_quality"),
                             nsrc=len(r.get("key_sources") or [])))
    return rows


def fetch_prices(tickers):
    os.makedirs(CACHE, exist_ok=True)
    p1 = int(dt.datetime(2026, 6, 5).timestamp())
    p2 = int(dt.datetime(2026, 9, 19, 23).timestamp())
    session = requests.Session()
    session.headers.update(UA)
    for ticker in tickers:
        fn = os.path.join(CACHE, f"{ticker}.json")
        if os.path.exists(fn) and os.path.getsize(fn) > 200:
            continue
        url = (f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
               f"?period1={p1}&period2={p2}&interval=1h&includePrePost=false")
        for attempt in range(4):
            try:
                res = session.get(url, timeout=30).json().get("chart", {}).get("result")
                if res:
                    json.dump(res[0], open(fn, "w"))
                    break
            except Exception:
                pass
            time.sleep(2 * (attempt + 1))
        else:
            raise RuntimeError(f"no price data for {ticker}")
        time.sleep(0.35)


def load_bars(tickers):
    px = {}
    for ticker in tickers:
        doc = json.load(open(os.path.join(CACHE, f"{ticker}.json")))
        quote = doc["indicators"]["quote"][0]
        bars = collections.defaultdict(dict)
        for i, stamp in enumerate(doc.get("timestamp") or []):
            loc = dt.datetime.fromtimestamp(stamp, ET)
            bars[loc.date().isoformat()][loc.strftime("%H:%M")] = (
                quote["open"][i], quote["close"][i])
        px[ticker] = dict(bars)
    return px


def build_trades(rows, px):
    calendar = {d for t in px for d in px[t]}

    def shift(day, step):
        x = dt.date.fromisoformat(day)
        for _ in range(10):
            x += dt.timedelta(days=step)
            if x.isoformat() in calendar:
                return x.isoformat()
        return None

    def bar(t, d, k):
        return px.get(t, {}).get(d, {}).get(k)

    qualified = [r for r in rows if abs(r["score"]) > SCORE_MIN and r["rev"] < REVERSAL_MAX]
    best = {}
    for r in qualified:
        entry_day = r["event_date"] if r["session"] == "AMC" else shift(r["event_date"], -1)
        if entry_day is None:
            continue
        r = dict(r, entry_day=entry_day)
        key = (r["agent"], r["ticker"], r["event_date"], r["session"])
        if key not in best or r["gts"] > best[key]["gts"]:
            best[key] = r

    trades = []
    for r in sorted(best.values(), key=lambda x: (x["entry_day"], x["agent"], x["ticker"])):
        # 20:00 CET sits inside the 13:30-14:30 ET bar; use its midpoint
        b = bar(r["ticker"], r["entry_day"], "13:30")
        if not b or not b[0] or not b[1]:
            raise RuntimeError(f"no entry bar for {r['ticker']} {r['entry_day']}")
        entry = (b[0] + b[1]) / 2
        if r["session"] == "AMC":
            exit_day = shift(r["event_date"], 1)
            xb = bar(r["ticker"], exit_day, "09:30")
        else:
            exit_day = r["event_date"]
            xb = bar(r["ticker"], exit_day, "13:30")
        if not xb or not xb[0]:
            raise RuntimeError(f"no exit bar for {r['ticker']} {exit_day}")
        exit_px = xb[0]
        side = 1 if r["score"] > 0 else -1
        trades.append(dict(r, entry_px=entry, exit_px=exit_px, exit_day=exit_day,
                           side=side, ret=side * (exit_px / entry - 1)))
    return trades


def simulate(trades):
    by_day = collections.defaultdict(list)
    for t in trades:
        by_day[t["entry_day"]].append(t)
    equity, curve = 1.0, []
    for day in sorted(by_day):
        pos = by_day[day]
        weight = min(MAX_WEIGHT, 1.0 / len(pos))
        day_ret = sum(weight * p["ret"] for p in pos)
        equity *= 1 + day_ret
        curve.append((day, len(pos), weight, day_ret, equity))
    return curve


def report(label, trades, curve):
    rets = [t["ret"] for t in trades]
    daily = [c[3] for c in curve]
    wins = [r for r in rets if r > 0]
    peak = eq = 1.0
    mdd = 0.0
    for d in daily:
        eq *= 1 + d
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    sd = statistics.pstdev(daily)
    print(f"\n=== {label} ===")
    print(f"positions {len(trades)} over {len(curve)} entry days")
    print(f"hit rate {100 * len(wins) / len(rets):.1f}%   avg trade {100 * statistics.mean(rets):+.2f}%"
          f"   median {100 * statistics.median(rets):+.2f}%")
    print(f"total return {100 * (curve[-1][4] - 1):+.2f}%   max drawdown {100 * mdd:.2f}%")
    print(f"best day {100 * max(daily):+.2f}%   worst day {100 * min(daily):+.2f}%"
          f"   ann. Sharpe {statistics.mean(daily) / sd * math.sqrt(252):.2f}")
    for tag in ("AMC", "BMO"):
        s = [t for t in trades if t["session"] == tag]
        if s:
            print(f"  {tag}: {len(s)} trades, avg {100 * statistics.mean([t['ret'] for t in s]):+.2f}%, "
                  f"hit {100 * sum(1 for t in s if t['ret'] > 0) / len(s):.0f}%")


def main():
    rows = load_predictions()
    qualified = [r for r in rows if abs(r["score"]) > SCORE_MIN and r["rev"] < REVERSAL_MAX]
    tickers = sorted({r["ticker"] for r in qualified})
    print(f"{len(rows)} predictions, {len(qualified)} pass the filter, {len(tickers)} tickers")
    fetch_prices(tickers)
    px = load_bars(tickers)
    trades = build_trades(rows, px)

    per_agent = {}
    for agent in sorted({t["agent"] for t in trades}):
        sub = [t for t in trades if t["agent"] == agent]
        curve = simulate(sub)
        per_agent[agent] = (sub, curve)
        report(f"Agent {agent}", sub, curve)

    grouped = collections.defaultdict(list)
    for t in trades:
        grouped[(t["ticker"], t["event_date"], t["session"])].append(t)
    union, conflicts = [], []
    for key, group in grouped.items():
        if len({g["side"] for g in group}) > 1:
            conflicts.append(key)
            continue
        union.append(sorted(group, key=lambda g: -abs(g["score"]))[0])
    union.sort(key=lambda t: (t["entry_day"], t["ticker"]))
    curve = simulate(union)
    print(f"\nshared events {sum(1 for g in grouped.values() if len({x['agent'] for x in g}) > 1)}, "
          f"direction conflicts dropped {len(conflicts)} {conflicts}")
    report("Aggregate (both agents in one account)", union, curve)

    union_keys = {(t["ticker"], t["event_date"], t["session"], t["agent"]) for t in union}
    weights = {}
    for agent, (sub, _) in per_agent.items():
        by_day = collections.defaultdict(list)
        for t in sub:
            by_day[t["entry_day"]].append(t)
        for day, pos in by_day.items():
            for p in pos:
                weights[id(p)] = min(MAX_WEIGHT, 1.0 / len(pos))
    out = os.path.join(ROOT, "analysis", "trades.csv")
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["agent", "source_file", "ticker", "company", "event_date", "session",
                    "entry_day", "exit_day", "direction_score", "reversal_risk", "direction_call",
                    "confidence", "side", "entry_price", "exit_price", "trade_return_pct",
                    "weight_in_agent_portfolio_pct", "in_aggregate_portfolio"])
        for t in trades:
            w.writerow([t["agent"], t["file"], t["ticker"], t["company"], t["event_date"],
                        t["session"], t["entry_day"], t["exit_day"], t["score"], t["rev"],
                        t["call"], t["conf"], "long" if t["side"] == 1 else "short",
                        round(t["entry_px"], 4), round(t["exit_px"], 4), round(100 * t["ret"], 3),
                        round(100 * weights[id(t)], 2),
                        (t["ticker"], t["event_date"], t["session"], t["agent"]) in union_keys])
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
