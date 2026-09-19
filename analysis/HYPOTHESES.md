# H1–H9 re-tested on this archive

The nine hypotheses were built on a different prediction machine. This is a replication on the
US1/US2 archive: 1,084 predictions, 12 June – 15 September 2026.

Two samples are used. The **traded book** is the 130 positions the score > 35 / reversal < 40 rule
produces after collapsing both agents onto one call per event. **All directional events** is every
event where at least one agent made a non-neutral call, deduplicated the same way: 462 events, which
buys statistical power at the cost of testing calls the rule would never have traded.

Percentages are the average signed return per event. `t` is a Welch two-sample statistic unless the
row says paired, in which case it is a paired t on the per-event difference.

| Hypothesis | Sample | Group A | Group B | Diff | t | Verdict |
|---|---|---|---|---|---|---|
| H1 · BMO more predictable than AMC | traded book | BMO 82 · +1.29% | AMC 48 · +2.84% | −1.55pp | −0.96 | no effect |
| H2a · AMC worth more sold at the open than the close | paired, 48 | open | close | +0.15pp | 0.20 | no effect |
| H2b · BMO worth more sold at the close than the open | paired, 82 | close | open | +0.61pp | 1.14 | weak |
| H2b′ · BMO close vs the 19:30 CET exit actually used | paired, 82 | close | 19:30 CET | +0.08pp | 0.45 | no effect |
| H3 · consumer-facing names more predictable | traded book | consumer 32 · +3.99% | other 98 · +1.17% | +2.82pp | 1.34 | weak |
| H4 · one sector carries the result | traded book | Healthcare 13 · +4.71% | Comm. Svcs 5 · −1.56% | spread 6.3pp | — | weak |
| H5 · the call pays more pointing with the price | 462 events | with price · +0.29% | against · +1.65% | −1.36pp | −1.53 | reverses |
| H6 · the conviction floor works | 462 events | \|score\| ≥ 45 · +0.06% | \|score\| < 45 · +1.11% | −1.06pp | −0.75 | no effect |
| H6′ · reversal risk under 40 works | 462 events | rev < 40 · +0.92% | rev ≥ 40 · +1.00% | −0.09pp | −0.10 | no effect |
| H7 · more findings means a better prediction | 462 events | ≥ 4 sources · +2.14% | < 4 · +0.76% | +1.38pp | 1.04 | no effect |
| H8 · the edge is in the thinly traded names | traded book | below median · +2.36% | above · +1.36% | +1.00pp | 0.64 | no effect |
| H9 · heavy search traffic means a worse trade | — | no search data in this archive | — | — | — | untestable |

## Where this archive has no equivalent field

H3's `retail_tilt`, H5's `lean`, H6's `impact_sum`, H7's finding count and H9's search series do not
exist here. Proxies were used and are named in the table: consumer sectors for retail tilt, the
five-session pre-event drift aligned with the call for lean, `|direction_score|` and `reversal_risk`
for the conviction floor, and the number of cited sources for finding count. H9 has no proxy. A proxy
failing is weaker evidence than the real field failing.

## What replicated

Almost nothing. H2b keeps its sign and roughly its size but stays inside the noise, and the version
that matters for this book — close versus the 19:30 CET exit already in use — is flat, so there is no
exit change to make. H3 and H4 point the same way as the originals but at half the claimed strength,
and H4 is the multiple-testing trap the original write-up already flagged: with eleven sectors the
best one is always good.

Two results deserve attention because they contradict the source set:

**H6 does not replicate, and it was the anchor.** Neither half of the conviction floor separates
anything here. Sorting on `|score| ≥ 45` gives +0.06% against +1.11% for the weaker calls, and
reversal risk under 40 gives +0.92% against +1.00% for everything above it. The rule the whole book
is built on is inert at the margin — not harmful, just not doing work.

**H5 reverses.** Calls pointing with the five-session drift earned +0.29%; calls pointing against it
earned +1.65%. In this archive the calls that fade recent price action are the better ones, which is
the opposite of the source finding, though at t = −1.53 it is not established either.

## The test that does pass

| Approach | Events | Hit rate | Avg per event |
|---|---|---|---|
| Long every event, ignoring the call | 462 | 49.8% | −0.03% |
| Following the direction call | 462 | 52.8% | +0.97% |
| — of which the long calls | 297 | 52.2% | +0.73% |
| — of which the short calls | 165 | 53.9% | +1.40% |
| Only events passing both thresholds | 110 | 57.3% | +1.45% |

Holding every name long over the same windows returns nothing. Following the direction call earns
about a point per event. Across all 462 events the direction score correlates with the realised move
at r = +0.096 (t = 2.06) — faint, but real, and it is the only component of the method that survives
testing. The threshold filter adds +0.63pp on top of that (t = 0.66), which is not established.

Reproduce with `python3 analysis/enrich.py && python3 analysis/hypotheses.py`.
