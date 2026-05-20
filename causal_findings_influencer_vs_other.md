# Causal findings — influencer_vs_other

**Outcome:** `conv_rate` (= conversions / impressions)
**Treatment:** as defined by `TREATMENTS['influencer_vs_other']`
**Confounders:** target_audience, customer_segment, language, brand, duration_days, log_acq_cost, in_festival_window
**Forbidden mediators:** impressions, clicks, leads, conversions, revenue, engagement_score, roi_reported, roi_rev_over_cost, ctr, lead_to_conv

## Results

| method                     | estimand   |    estimate |         ci_lo |         ci_hi |   n_t |    n_c |
|:---------------------------|:-----------|------------:|--------------:|--------------:|------:|-------:|
| Naive diff                 | naive      | 3.72004e-06 | nan           | nan           | 33503 | 133162 |
| Matched ATT (caliper=None) | ATT        | 2.01897e-05 | nan           | nan           | 33503 |  33503 |
| IPW ATE                    | ATE        | 7.2996e-05  | nan           | nan           | 33503 | 133162 |
| Outcome reg ATE            | ATE        | 5.32329e-05 | nan           | nan           |    -1 |     -1 |
| AIPW ATE (headline)        | ATE        | 5.59556e-05 |  -3.86131e-05 |   0.000160505 | 33503 | 133162 |

## Sensitivity — caliper sweep

| caliper   |   matched_att |   n_pairs |
|:----------|--------------:|----------:|
| None      |   2.01897e-05 |     33503 |
| 0.1       |   2.01897e-05 |     33503 |
| 0.05      |   2.01897e-05 |     33503 |
| 0.01      |   2.01897e-05 |     33503 |
| 0.005     |   2.01897e-05 |     33503 |

## Sensitivity — placebo runs

- Run 1: ATE = -0.000041
- Run 2: ATE = -0.000020

## Caveats

- Observational data — estimates assume no unmeasured confounders.
- Synthetic dataset; effects are expected to be near zero.
- AIPW CIs use the fast bootstrap (no per-iteration refit).
