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

### By month

| | US1 | US2 | Combined |
|---|---|---|---|
| June | −3.0% | −2.5% | −4.1% |
| July | +18.9% | +9.0% | +15.0% |
| August | +8.3% | +30.1% | +41.4% |
| September (to 15th) | −0.2% | +2.7% | +6.3% |

No reports exist between 25 June and 18 July, so that stretch is flat by construction.

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
