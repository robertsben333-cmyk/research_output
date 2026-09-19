# Everything in one model

One observation per earnings event, taken once across both agents. Dependent variable is the signed
return of the trade in percent. Continuous predictors are standardised, so a coefficient reads as
"percentage points of return per standard deviation of the variable". Standard errors are clustered
by entry day, because events entered on the same afternoon share a market.

Interactions are pre-specified from the hypothesis set — tilt × floor, score × reversal, session ×
tilt, drift × conviction, search × tilt — rather than swept. With 418 usable events a full pairwise
sweep would guarantee finding something.

Reproduce with `python3 analysis/regression.py`.

## The four models

| Model | n | R² | adj R² | Permutation p for R² | Any coefficient clearing the corrected bar |
|---|---|---|---|---|---|
| 1 · main effects | 418 | 4.5% | 1.9% | 0.053 | none |
| 2 · plus the interactions | 418 | 4.8% | 1.0% | 0.206 | none |
| 3 · tilt split into components | 413 | 6.1% | 2.8% | 0.036 | none |
| 4 · search subsample | 230 | 9.4% | 3.9% | 0.056 | none |

The reported F p-values look better than this (0.039, 0.009, 0.001, 0.001) and should be ignored: a
cluster-robust Wald test on 43 clusters over-rejects badly. The permutation p-value — shuffle the
outcomes 2,000 times, count how often a model does this well by luck — is the one to read.

## Nothing localises

Strongest coefficients in each model, against the permutation bar for the largest |t| any of that
model's terms would reach by chance:

| Model | Strongest term | coef | t | Bar (95th pct under the null) |
|---|---|---|---|---|
| 1 | aligned pre-event drift | −1.22 | −1.96 | 2.85 |
| 1 | reversal risk | −1.29 | −1.60 | 2.85 |
| 2 | aligned pre-event drift | −1.20 | −1.76 | 2.96 |
| 3 | log price | −1.18 | −2.01 | 2.96 |
| 3 | aligned pre-event drift | −1.26 | −2.02 | 2.96 |
| 4 | search level ratio | −1.59 | −2.78 | 2.90 |
| 4 | aligned pre-event drift | −1.86 | −2.59 | 2.90 |

Read singly, three of these would be called significant at p < 0.05. Read as what they are — the
largest of eleven to sixteen coefficients — none of them clears the bar. The two that come closest
are the two the earlier hypothesis work already pointed at: the search level ratio (H9) and the
aligned drift (H5, with the sign reversed from the original claim in both cases where it appears).

**The interactions contribute nothing.** Model 2 adds four of them to model 1 and raises R² from
4.5% to 4.8%, which is less than the degrees of freedom cost: adjusted R² falls from 1.9% to 1.0%
and the permutation p-value degrades from 0.053 to 0.206. Every interaction term lands under |t| = 0.5.
The tilt × floor interaction that looked like the best lead in the H3 work comes in at t = 0.31 once
the main effects are controlled for.

Also worth noting: `abs_score`, `confidence` and `evidence_quality` are the weakest terms in every
model, all under |t| = 0.5. The conviction machinery does not survive being asked to compete.

## The test that settles it

Fit on the earlier entry days, predict the later ones:

| Train | Cut | Test n | Out-of-sample R² | Corr(prediction, outcome) |
|---|---|---|---|---|
| 40% | 2026-08-05 | 227 | −0.056 | +0.024 |
| 50% | 2026-08-11 | 174 | +0.017 | +0.134 |
| 60% | 2026-08-18 | 127 | −0.045 | +0.004 |
| 70% | 2026-08-26 | 82 | −0.059 | −0.053 |
| 80% | 2026-09-02 | 48 | −0.036 | −0.047 |

Negative out-of-sample R² means the model does worse than predicting the training mean for every
event. Four of five splits are negative and the correlations centre on zero.

Trading on the model's prediction does not work either. With the model-1 terms, taking only events
it predicts will gain returns +1.99% against +1.07% for taking everything — which sounds like an
edge until you see the prediction correlates +0.004 with the outcome. With the model-2 terms the
same rule returns +0.03% against +1.07%: worse than no model at all.

## What to conclude

Jointly, the variables explain 4–6% of the variance in-sample with a permutation p around 0.04–0.06.
That is a whisper, not a signal, and it does not attach to any one variable or survive being asked
to predict events it has not seen.

The practical reading: there is no weighting of these inputs that beats the simple rule already in
use. If anything is worth carrying forward it is the two terms that keep reappearing — search
quietness before the print, and calls that fade rather than follow the recent drift — and both need
to be tested on new events, with the threshold fixed in advance, before they mean anything.
