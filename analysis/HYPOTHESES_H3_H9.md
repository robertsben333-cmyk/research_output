# H3 and H9 with the real inputs

The first pass used sector membership as a stand-in for retail tilt and left H9 untested. This is
the rebuild: the four-component tilt exactly as specified, and Google search interest as the
attention series.

## The tilt

`analysis/tilt.py` builds it: churn (median daily dollar volume over the prior 20 sessions, divided
by market cap, in percent), market cap (shares outstanding times the entry price, entered inverted),
entry price (inverted), and 20-day realised annualised volatility. Each becomes a percentile over the
whole sample, the available percentiles are averaged, at least two must be present. Components travel
in `retail_parts`.

Over 840 events it produces a median tilt of 51.5 with quartiles at 33.6 and 64.9. The underlying
medians are churn 0.96%, market cap $17,124m, price $82.01, volatility 37.9.

**That is a different universe from the one the hypothesis was built on.** The reference set had a
median market cap of $692m and a median price of $12.42; this archive is 25× larger by cap and 6.6×
higher by price, with similar churn and lower volatility. Because the tilt is a within-sample
percentile, its median still lands near 50 — but a name scoring 70 here would score far lower in the
reference set. The absolute cut of 52 does not transfer, so both it and the within-sample splits are
reported.

## H3 · are consumer-tilted names more predictable?

| Split | Sample | High | Low | Diff | t |
|---|---|---|---|---|---|
| tilt ≥ 52 (their cut) | traded book, 130 | 49 · 59.2% · +3.33% | 81 · 58.0% · +0.97% | +2.36pp | 1.30 |
| tilt ≥ 52 | all 462 events | 218 · 50.9% · +1.48% | 244 · 54.5% · +0.51% | +0.97pp | 1.06 |
| above sample median | traded book | 65 · 53.8% · +2.21% | 65 · 63.1% · +1.51% | +0.70pp | 0.45 |
| top vs bottom quartile | traded book | 33 · 63.6% · +4.62% | 33 · 72.7% · +1.25% | +3.36pp | 1.46 |

The direction matches the original at roughly half the strength, and nothing reaches significance.
But the hit-rate column is the tell, and it points the other way from the return column.

**Tilt does not buy accuracy. It buys amplitude.**

| | n | Hit rate | Avg abs. move | Avg signed return | Median signed return |
|---|---|---|---|---|---|
| tilt ≥ 52 | 218 | 50.9% | 8.73% | +1.48% | +0.26% |
| tilt < 52 | 244 | 54.5% | 5.30% | +0.51% | +0.52% |

High-tilt names are called correctly *less* often — 50.9% is a coin flip — but they move 8.7% instead
of 5.3%, so the winners are larger. The raw move is flat in both groups (−0.09% and +0.04%), so this
is not drift being levered up; and the agents behave differently on these names, calling only 52% of
them long against 75% for the low-tilt half.

The positive mean does not survive contact with the outliers:

| High-tilt sample | Mean |
|---|---|
| all 218 | +1.48% |
| drop the best 1 | +1.30% |
| drop the best 3 | +0.97% |
| drop the best 5 | +0.68% |

Five names out of 218 (CMTL +41.7%, VRA +36.5%, VNCE +36.1%, TEAM +32.7%, HTFL +32.7%) carry the
difference. On the median — the measure outliers cannot move — high tilt is *worse*: +0.26% against
+0.52%. **H3 does not hold here.** What the tilt actually selects is volatility, and a volatility
screen raises variance in both directions.

### The interaction with the floor

The original located the effect in tilt combined with the conviction floor rather than in tilt alone.
That shape does reappear:

| | n | Hit rate | Avg |
|---|---|---|---|
| high tilt, passes the filter | 36 | 61.1% | +3.48% |
| high tilt, below the filter | 182 | 48.9% | +1.09% |
| low tilt, passes the filter | 74 | 55.4% | +0.46% |
| low tilt, below the filter | 170 | 54.1% | +0.53% |

High tilt above the floor is the only cell that beats its row and its column. At n = 36 this is one
cell of a 2×2 chosen after the fact, and the same five outliers sit inside it, so it is a lead to
test on new events, not a result.

### Which component carries the number

Median split on each component, retail-looking half against the other (all 462 events):

| Component | Retail half | Other half | t |
|---|---|---|---|
| low price | +1.56% | +0.38% | 1.32 |
| small cap | +1.25% | +0.72% | 0.59 |
| volatility | +1.21% | +0.74% | 0.52 |
| churn | +1.21% | +0.76% | 0.49 |

Low price is the strongest of the four, which matches the literature marker the spec cites. All four
point the same way and none is significant on its own.

## H9 · search traffic

Google Trends is reachable from this environment, so H9 is testable after all. Daily interest for
`<TICKER> stock` from 1 May to 18 September 2026 is being collected per ticker. Results are appended
below once the pull completes.
