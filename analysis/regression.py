"""Everything in one model: what survives when the variables compete?

Dependent variable is the signed return of the trade, in percent. One observation per earnings
event, taken once across both agents (the higher-conviction call wins, direction conflicts drop).

Predictors are the things the hypothesis set names, standardised so coefficients are comparable:
the two filter scores, disparity, the retail tilt and its components, cited sources, the aligned
pre-event drift, session, side, agent, and the Google search level ratio where it exists.
Interactions are pre-specified from H1-H9 rather than swept, because 462 observations cannot carry
a full pairwise sweep.

Standard errors are clustered by entry day: events entered on the same afternoon share a market.

Three guards against reading noise:
  - a permutation test that gives the multiple-testing-corrected |t| threshold
  - an out-of-sample split, fitted on the earlier 60% of entry days and scored on the rest
  - an F-test of the whole model against an intercept

Run analysis/enrich.py, analysis/tilt.py first. Writes analysis/.cache/regression.json.
"""
import os, sys, json, math, collections, statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'analysis'))
D = os.path.join(ROOT, 'analysis', '.cache') + os.sep

import numpy as np
import pandas as pd
import statsmodels.api as sm
import search_h9 as SH

ORDINAL = {'low': 1.0, 'low-medium': 1.5, 'medium-low': 1.5, 'medium': 2.0,
           'medium-high': 2.5, 'high-medium': 2.5, 'high': 3.0, 'strong': 3.5,
           'very high': 3.5, 'weak': 1.0, 'moderate': 2.0}


def ordinal(v):
    return ORDINAL.get(str(v).strip().lower()) if v else None


SEED = 20260919
N_PERM = 2000
TRAIN_FRAC = 0.60


def build_frame():
    events = json.load(open(D + 'enriched.json'))
    tilt = json.load(open(D + 'tilt.json'))
    sectors = json.load(open(D + 'sectors.json'))
    series = {}
    for e in events:
        key = '|'.join([e['agent'], e['ticker'], e['event_date'], e['session']])
        t = tilt.get(key) or {}
        e.update(tilt=t.get('tilt'), churn=t.get('churn'), mcap=t.get('mcap'),
                 px=t.get('price'), vol20=t.get('vol'))
        if e['ticker'] not in series:
            series[e['ticker']] = SH.load_series(e['ticker'])
        r = SH.ratio(series[e['ticker']], e['entry_day']) if series[e['ticker']] else None
        e['search_peak'], e['search_level'] = r if r else (None, None)
        e['sector'] = sectors.get(e['ticker'])

    grouped = collections.defaultdict(list)
    for e in events:
        if e['side'] != 0:
            grouped[(e['ticker'], e['event_date'], e['session'])].append(e)
    rows = []
    for v in grouped.values():
        if len({x['side'] for x in v}) > 1:
            continue
        rows.append(sorted(v, key=lambda x: -abs(x['score']))[0])

    df = pd.DataFrame([dict(
        ret=100 * r['ret'], entry_day=r['entry_day'], ticker=r['ticker'], sector=r['sector'],
        abs_score=abs(r['score']), rev=r['rev'], disparity=r.get('disparity'),
        tilt=r['tilt'], churn=r['churn'], vol20=r['vol20'], nsrc=r['nsrc'],
        confidence=ordinal(r.get('conf')), evidence=ordinal(r.get('evidence')),
        log_mcap=math.log(r['mcap']) if r['mcap'] else None,
        log_price=math.log(r['px']) if r['px'] else None,
        mom_aligned=100 * r['side'] * r['mom'] if r['mom'] is not None else None,
        search_level=r['search_level'],
        is_bmo=1.0 * (r['session'] == 'BMO'), is_short=1.0 * (r['side'] == -1),
        agent_us2=1.0 * (r['agent'] == 'US2'),
        passes=1.0 * (abs(r['score']) > 35 and r['rev'] < 40),
    ) for r in rows])
    return df.sort_values('entry_day').reset_index(drop=True)


def zscore(df, cols):
    out = df.copy()
    for c in cols:
        s = out[c].astype(float)
        out[c] = (s - s.mean()) / s.std(ddof=0)
    return out


def fit(df, terms, label, interactions=()):
    d = df.dropna(subset=[t for t in terms if t in df.columns] + ['ret']).copy()
    cont = [t for t in terms if d[t].nunique() > 2]
    d = zscore(d, cont)
    for a, b in interactions:
        d[f'{a}:{b}'] = d[a] * d[b]
    cols = list(terms) + [f'{a}:{b}' for a, b in interactions]
    X = sm.add_constant(d[cols].astype(float))
    m = sm.OLS(d['ret'].astype(float), X).fit(
        cov_type='cluster', cov_kwds={'groups': d['entry_day']})
    print(f"\n{'=' * 78}\n{label}\n  n={int(m.nobs)}  clusters={d['entry_day'].nunique()}  "
          f"R2={m.rsquared:.4f}  adj R2={m.rsquared_adj:.4f}  "
          f"F p-value={m.f_pvalue:.3f}\n{'=' * 78}")
    print(f"  {'term':<26}{'coef':>9}{'std err':>10}{'t':>8}{'p':>8}")
    order = m.params.abs().sort_values(ascending=False).index
    for k in order:
        print(f"  {k:<26}{m.params[k]:>9.3f}{m.bse[k]:>10.3f}{m.tvalues[k]:>8.2f}{m.pvalues[k]:>8.3f}")
    pr2 = permutation_r2(d, cols, m.rsquared)
    print(f"  permutation p-value for the model's R2: {pr2:.3f}  "
          f"(cluster-robust F on {d['entry_day'].nunique()} clusters over-rejects; trust this one)")
    hi, med = permutation_threshold(d, cols)
    if hi == hi:
        print(f"  permutation null over {len(cols)} terms: |t| = {hi:.2f} is the 95th percentile "
              f"by chance alone (median {med:.2f})")
        flagged = [k for k in cols if abs(m.tvalues[k]) >= hi]
        print(f"  clears that bar: {', '.join(flagged) if flagged else 'nothing'}")
    return m, d, cols


def permutation_threshold(d, cols, n=N_PERM):
    """Max |t| under the null, so we know what |t| a sweep of this width produces by chance."""
    rng = np.random.default_rng(SEED)
    X = sm.add_constant(d[cols].astype(float)).values
    y = d['ret'].astype(float).values
    if np.linalg.matrix_rank(X) < X.shape[1]:
        return float('nan'), float('nan')
    xtx_inv = np.linalg.inv(X.T @ X)
    hat = xtx_inv @ X.T
    dof = len(y) - X.shape[1]
    maxes = []
    for _ in range(n):
        yp = rng.permutation(y)
        b = hat @ yp
        resid = yp - X @ b
        s2 = resid @ resid / dof
        se = np.sqrt(np.diag(xtx_inv) * s2)
        maxes.append(np.max(np.abs(b[1:] / se[1:])))
    maxes = np.sort(maxes)
    return maxes[int(0.95 * n)], maxes[int(0.50 * n)]


def permutation_r2(d, cols, r2_obs, n=N_PERM):
    """How often does a shuffled outcome produce an R2 this large? The honest joint test:
    cluster-robust F on ~43 clusters over-rejects, this does not."""
    rng = np.random.default_rng(SEED)
    X = sm.add_constant(d[cols].astype(float)).values
    y = d['ret'].astype(float).values
    hat = np.linalg.pinv(X)
    hits = 0
    for _ in range(n):
        yp = rng.permutation(y)
        resid = yp - X @ (hat @ yp)
        r2 = 1 - (resid @ resid) / ((yp - yp.mean()) @ (yp - yp.mean()))
        hits += r2 >= r2_obs
    return (hits + 1) / (n + 1)


def out_of_sample(df, terms, interactions, label):
    d = df.dropna(subset=list(terms) + ['ret']).copy()
    days = sorted(d['entry_day'].unique())
    cut = days[int(TRAIN_FRAC * len(days))]
    cont = [t for t in terms if d[t].nunique() > 2]
    mu = d[d['entry_day'] < cut][cont].mean()
    sd = d[d['entry_day'] < cut][cont].std(ddof=0)
    d[cont] = (d[cont] - mu) / sd
    for a, b in interactions:
        d[f'{a}:{b}'] = d[a] * d[b]
    cols = list(terms) + [f'{a}:{b}' for a, b in interactions]
    tr, te = d[d['entry_day'] < cut], d[d['entry_day'] >= cut]
    m = sm.OLS(tr['ret'].astype(float), sm.add_constant(tr[cols].astype(float))).fit()
    pred = m.predict(sm.add_constant(te[cols].astype(float), has_constant='add'))
    y = te['ret'].astype(float)
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - tr['ret'].mean()) ** 2).sum())
    picked = te[pred > 0]
    print(f"\n--- out of sample: {label} ---")
    print(f"  trained on {len(tr)} events before {cut}, tested on {len(te)} from {cut} on")
    print(f"  out-of-sample R2 = {1 - ss_res / ss_tot:+.4f}   "
          f"(negative means worse than just predicting the training mean)")
    print(f"  correlation of prediction with outcome: r = {np.corrcoef(pred, y)[0, 1]:+.3f}")
    if len(picked):
        print(f"  trade only where the model predicts a gain: n={len(picked)}  "
              f"avg {picked['ret'].mean():+.2f}%  hit {100 * (picked['ret'] > 0).mean():.1f}%")
    print(f"  trade everything in the test window:      n={len(te)}  "
          f"avg {y.mean():+.2f}%  hit {100 * (y > 0).mean():.1f}%")


def main():
    df = build_frame()
    print(f"events: {len(df)}   with tilt: {df['tilt'].notna().sum()}   "
          f"with search: {df['search_level'].notna().sum()}   "
          f"with disparity: {df['disparity'].notna().sum()}")

    main_terms = ['abs_score', 'rev', 'disparity', 'confidence', 'evidence', 'tilt', 'nsrc',
                  'mom_aligned', 'is_bmo', 'is_short', 'agent_us2']
    m1, d1, c1 = fit(df, main_terms, 'MODEL 1 - main effects only')

    inter = [('tilt', 'passes'), ('abs_score', 'rev'), ('is_bmo', 'tilt'),
             ('mom_aligned', 'abs_score')]
    m2, d2, c2 = fit(df, main_terms + ['passes'], 'MODEL 2 - with the pre-specified interactions',
                     interactions=inter)

    comp_terms = ['abs_score', 'rev', 'disparity', 'confidence', 'evidence',
                  'churn', 'log_mcap', 'log_price', 'vol20',
                  'nsrc', 'mom_aligned', 'is_bmo', 'is_short', 'agent_us2']
    fit(df, comp_terms, 'MODEL 3 - tilt broken into its four components')

    search_terms = main_terms + ['search_level']
    fit(df, search_terms, 'MODEL 4 - search subsample',
        interactions=[('search_level', 'tilt')])

    out_of_sample(df, main_terms, [], 'model 1 terms')
    out_of_sample(df, main_terms + ['passes'], inter, 'model 2 terms')
    out_of_sample(df.dropna(subset=['search_level']), search_terms,
                  [('search_level', 'tilt')], 'model 4 terms, search subsample')

    print('\n--- is the out-of-sample failure one unlucky split? ---')
    d = df.dropna(subset=main_terms + ['ret']).copy()
    days = sorted(d['entry_day'].unique())
    for frac in (0.4, 0.5, 0.6, 0.7, 0.8):
        cut = days[int(frac * len(days))]
        cont = [t for t in main_terms if d[t].nunique() > 2]
        z = d.copy()
        mu, sd = z[z['entry_day'] < cut][cont].mean(), z[z['entry_day'] < cut][cont].std(ddof=0)
        z[cont] = (z[cont] - mu) / sd
        tr, te = z[z['entry_day'] < cut], z[z['entry_day'] >= cut]
        mm = sm.OLS(tr['ret'].astype(float),
                    sm.add_constant(tr[main_terms].astype(float))).fit()
        pr = mm.predict(sm.add_constant(te[main_terms].astype(float), has_constant='add'))
        y = te['ret'].astype(float)
        r = np.corrcoef(pr, y)[0, 1]
        ss = 1 - float(((y - pr) ** 2).sum()) / float(((y - tr['ret'].mean()) ** 2).sum())
        print(f"  train {int(frac * 100)}% (cut {cut}, test n={len(te):>3}): "
              f"OOS R2 {ss:>+7.3f}   r {r:>+6.3f}")

    json.dump({'n': len(df), 'r2_main': m1.rsquared, 'r2_inter': m2.rsquared,
               'perm_t95': hi, 'perm_t95_inter': hi2},
              open(D + 'regression.json', 'w'))


if __name__ == '__main__':
    main()
