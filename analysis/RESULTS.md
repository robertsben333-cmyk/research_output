# Backtest of the ranked earnings predictions

Source: the 132 report files in `history/` (1,084 ranked predictions, 13 June – 17 September 2026).
Two agents produced them: **US1** (618 predictions) and **US2** (466).

## Rules applied

| | |
|---|---|
| Entry filter | `\|direction_score\| > 35` and `reversal_risk < 40` |
| Direction | long on a positive score, short on a negative one |
| Entry | 20:00 CET on the last session before the announcement |
| Exit | AMC names at the next market open; BMO names at 19:30 CET on announcement day |
| Sizing | equal weight, capped at 40% of equity per stock per day |
| Costs | none (no commission, spread or borrow) |

182 of 1,084 predictions pass the filter; after removing repeats of the same company-event within
an agent, 157 positions remain. All 157 could be priced.

Prices are Yahoo Finance hourly regular-session bars. Everything falls inside summer time, so
CET = ET + 6h. 19:30 CET (13:30 ET) and the market open are exact bar boundaries; 20:00 CET falls
inside the 13:30–14:30 ET bar, so entry uses that bar's midpoint. Pricing the entry at 13:30 or
14:30 instead moves the aggregate result by less than 1.1 percentage points, so this does not drive
anything below.

Sizing note: the 40% cap only binds when fewer than three names qualify. On a one-name day the book
is 40% invested, on a two-name day 80%, from three names up 100% split equally.

## Results

| | US1 | US2 | Both combined |
|---|---|---|---|
| Positions | 91 | 66 | 130 |
| Entry days | 33 | 29 | 36 |
| Total return | **+24.6%** | **+42.0%** | **+65.9%** |
| Hit rate | 54.9% | 63.6% | 58.5% |
| Average trade | +1.21% | +1.91% | +1.86% |
| Median trade | +0.86% | +1.08% | +1.49% |
| Best day | +13.2% | +15.0% | +13.2% |
| Worst day | −9.6% | −12.7% | −9.6% |
| Max drawdown | −12.3% | −14.6% | −9.6% |

SPY returned +2.4% over the same window (12 June – 15 September 2026).

The combined book is the union of both agents' calls: 26 events were picked by both (counted once),
one event (OLLI, 2 September BMO) had the two agents on opposite sides and was dropped. Running the
two agents as separate accounts and splitting capital 50/50 between them gives +33.3% instead of
+65.9%; the union does better because pooling raises the number of names per day, which lifts the
share of capital actually deployed.

## Starting with $10,000

| | US1 | US2 | Combined |
|---|---|---|---|
| Final value | $12,464 | $14,196 | **$16,588** |
| Profit | +$2,464 | +$4,196 | +$6,588 |

Compounded across entry days, idle cash earning nothing. Trades are in USD; no FX effect is modelled.

## Did the change in reasoning effort show up?

US2 was moved to extra-high reasoning effort and US1 to standard at some point in the sample. Nothing
in the report files records the setting, so the date has to be read off the outcome series.

Over the whole sample US2 is the better forecaster: 54.1% hit rate against US1's 48.7%, and +0.42%
per directional call against +0.15%. Weekly hit rates:

| Week of | US1 n | US1 hit | US2 n | US2 hit |
|---|---|---|---|---|
| 8 Jun | 4 | 50% | — | — |
| 15 Jun | 12 | 50% | 7 | 43% |
| 22 Jun | 19 | 26% | 12 | 33% |
| 13 Jul | — | — | 3 | 100% |
| 20 Jul | 33 | 52% | 56 | 50% |
| 27 Jul | 55 | 56% | 53 | 60% |
| 3 Aug | 90 | 48% | 29 | 52% |
| 10 Aug | 67 | 49% | 48 | 50% |
| 17 Aug | 47 | 43% | 30 | 60% |
| 24 Aug | 76 | 55% | 56 | 59% |
| 31 Aug | 70 | 53% | 44 | 48% |
| 7 Sep | 30 | 27% | 26 | 58% |
| 14 Sep | 16 | 56% | 11 | 64% |

From the week of 17 August onward US2 beats US1 in four weeks out of five, but scanning every
possible break date finds no clean split: the strongest is 13 August at t = 1.92, short of
significance and flattered by the fact that the scan chose it. The June weeks are poor for both
agents, which does most of the work in any early split. **The gap is real over the full sample; the
moment it opened is not identifiable from this data.** Supply the actual switch date and the test
becomes a pre-specified one rather than a search.

### By month

| | US1 | US2 | Combined |
|---|---|---|---|
| June | −3.0% | −2.5% | −4.1% |
| July | +18.9% | +9.0% | +15.0% |
| August | +8.3% | +30.1% | +41.4% |
| September (to 15th) | −0.2% | +2.7% | +6.3% |

No reports exist between 25 June and 18 July, so that stretch is flat by construction.

### Positions per entry day

Entry day is the session on which capital goes in at 20:00 CET: an AMC event on that day, or a BMO
event the following session. `w` is the weight each name gets; `invested` is the share of equity the
combined book has at work that day, which is below 100% only when fewer than three names qualify.

| Entry day | US1 | w | US2 | w | Combined | w | Invested |
|---|---|---|---|---|---|---|---|
| 2026-06-12 | 1 | 40% | — | — | 1 | 40% | 40% |
| 2026-06-15 | 1 | 40% | — | — | 1 | 40% | 40% |
| 2026-06-23 | — | — | 1 | 40% | 1 | 40% | 40% |
| 2026-06-24 | 2 | 40% | 1 | 40% | 2 | 40% | 80% |
| 2026-07-20 | 3 | 33% | 5 | 20% | 5 | 20% | 100% |
| 2026-07-21 | — | — | 3 | 33% | 3 | 33% | 100% |
| 2026-07-22 | 1 | 40% | 2 | 40% | 3 | 33% | 100% |
| 2026-07-27 | 4 | 25% | 3 | 33% | 5 | 20% | 100% |
| 2026-07-28 | 4 | 25% | — | — | 4 | 25% | 100% |
| 2026-07-29 | 3 | 33% | 2 | 40% | 4 | 25% | 100% |
| 2026-07-30 | 3 | 33% | 1 | 40% | 4 | 25% | 100% |
| 2026-07-31 | — | — | 2 | 40% | 2 | 40% | 80% |
| 2026-08-03 | 1 | 40% | — | — | 1 | 40% | 40% |
| 2026-08-04 | 5 | 20% | — | — | 5 | 20% | 100% |
| 2026-08-05 | 3 | 33% | 3 | 33% | 3 | 33% | 100% |
| 2026-08-06 | 5 | 20% | — | — | 5 | 20% | 100% |
| 2026-08-07 | 3 | 33% | 2 | 40% | 5 | 20% | 100% |
| 2026-08-10 | 4 | 25% | 4 | 25% | 6 | 17% | 100% |
| 2026-08-11 | 3 | 33% | 3 | 33% | 5 | 20% | 100% |
| 2026-08-12 | 5 | 20% | 3 | 33% | 7 | 14% | 100% |
| 2026-08-13 | 1 | 40% | 2 | 40% | 3 | 33% | 100% |
| 2026-08-17 | 1 | 40% | — | — | 1 | 40% | 40% |
| 2026-08-18 | 3 | 33% | 2 | 40% | 5 | 20% | 100% |
| 2026-08-19 | 3 | 33% | 2 | 40% | 3 | 33% | 100% |
| 2026-08-20 | 2 | 40% | 2 | 40% | 3 | 33% | 100% |
| 2026-08-24 | 1 | 40% | 1 | 40% | 1 | 40% | 40% |
| 2026-08-25 | 5 | 20% | 1 | 40% | 6 | 17% | 100% |
| 2026-08-26 | 5 | 20% | 4 | 25% | 7 | 14% | 100% |
| 2026-08-27 | 3 | 33% | 4 | 25% | 7 | 14% | 100% |
| 2026-08-31 | 1 | 40% | 1 | 40% | 2 | 40% | 80% |
| 2026-09-01 | 3 | 33% | 1 | 40% | 2 | 40% | 80% |
| 2026-09-02 | 5 | 20% | 3 | 33% | 7 | 14% | 100% |
| 2026-09-03 | 2 | 40% | 1 | 40% | 3 | 33% | 100% |
| 2026-09-08 | 2 | 40% | 5 | 20% | 5 | 20% | 100% |
| 2026-09-11 | 1 | 40% | 1 | 40% | 1 | 40% | 40% |
| 2026-09-14 | 2 | 40% | 1 | 40% | 2 | 40% | 80% |

| | US1 | US2 | Combined |
|---|---|---|---|
| Entry days | 33 | 29 | 36 |
| Positions | 91 | 66 | 130 |
| Average per day | 2.8 | 2.3 | 3.6 |
| Busiest day | 5 | 5 | 7 |
| Single-name days | 9 | 10 | 7 |
| Average capital deployed | 81% | 74% | 86% |

The 40% cap binds on 14 of US1's 33 days, 18 of US2's 29 and 12 of the combined 36, leaving those
days partly in cash. On 1 September the combined count (2) is lower than either agent's because the
OLLI direction conflict removes that name from the combined book.

### Where the return comes from

AMC positions, held from 20:00 CET into the next open, did most of the work: 48 combined positions,
+2.84% average, 65% hit rate. BMO positions, held from the previous afternoon to 19:30 CET on the
day, averaged +1.29% with a 55% hit rate.

Direction is almost entirely long. Only 7 of 130 combined positions were shorts (score below −35 with
reversal risk under 40 is rare), and they averaged +4.85%, so the short leg is too small to judge.

Events both agents flagged did worse than events only one of them flagged: 26 shared positions
averaged −0.37%, US1-only averaged +1.84%, US2-only +3.20%. Agreement between the two agents was not
a quality signal in this sample.

## Caveats

- 33 and 29 entry days is a small sample, and the outcome is concentrated. Three days (6 August,
  13 August, 8 September) carry most of the combined gain: drop them and +65.9% becomes +19.0%.
- No transaction costs, no slippage, no borrow cost on the shorts. Several names are small caps
  (RFIL, HTFL, SUNB, DAKT) where an earnings-gap fill at the printed price is optimistic.
- The filter itself comes from the same data it is tested on. The threshold pair (35 / 40) was given,
  not fitted here, but it has never been validated out of sample.
- Concentration drives the result more than the signal does. Sizing the top two names by score at 40%
  each instead of equal-weighting everything turns US1 into −4.4% while US2 rises to +49.9%.
- Prices are unadjusted for dividends within the holding window. Over one overnight hold this is
  immaterial for almost every name.

## Files

- `backtest.py` — the full pipeline (parse reports, download prices, simulate). Re-run with
  `python3 analysis/backtest.py`.
- `trades.csv` — all 157 positions with entry/exit prices, weights and returns.
