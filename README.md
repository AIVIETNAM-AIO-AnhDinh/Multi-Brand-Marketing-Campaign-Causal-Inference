# Beauty Campaign Analytics — Multi-Brand Causal & Uplift Framework

End-to-end marketing analytics project on three Indian beauty/cosmetics e-commerce brand
campaign datasets (**Purplle**, **Nykaa**, **Tira**), covering Jul 2024 – Jun 2025. Link to datasets: https://www.kaggle.com/datasets/sshriya08/multi-brand-marketing-campaign-performance-dataset

The descriptive layer (per-brand KPIs, channel/campaign-type, audience/segment,
cross-brand comparison) is already covered by the existing HTML report. This project
extends that work into **diagnostic, causal, and prescriptive** territory.

## Framing & honest limitations

The three brand CSVs have suspiciously identical summary statistics (same row count,
near-identical mean ROI ~2.7, near-identical loss share ~46%, identical audience
sets). They are almost certainly drawn from the same synthetic generator. Therefore:

- We frame the project as a **multi-brand portfolio**: a framework demonstrated on
  three brand datasets, not a competitive benchmark.
- All causal effects are estimated and reported with **explicit assumptions and
  sensitivity analyses** — not as ground truth about real brand performance.
- The closing section of the written report explicitly maps how this framework
  would generalize to real brand telemetry.

## Methodology

The analysis is layered: each stage answers a sharper question than the last, and the
output of each stage is the input to the next. All stages query a single DuckDB
warehouse so transformations are defined once and reused everywhere.

### Stage 1 — Data warehouse (DuckDB + SQL views)

The three brand CSVs (~166,665 rows total) are loaded into a single DuckDB database
by `src/data_loader.py`. Three SQL files transform the raw data into analysis-ready
views: `01_stg_campaigns.sql` (staging — typed columns, derived per-row metrics like
`ctr`, `conv_rate`, `roi_rev_over_cost`, and the `is_loss_making` flag),
`02_campaigns_enriched.sql` (joins to the festival calendar dimension), and
`03_mart_funnel.sql` (pre-aggregated funnel-rate marts at varying grains). Defining
metrics in SQL once — rather than recomputing per notebook — eliminates the most
common cross-notebook bug: a metric that subtly differs across analyses.

### Stage 2 — EDA & data quality 

Five checks: row counts and brand mix; **ROI-formula verification** (comparing the
supplied `roi_reported` against two candidate structural formulas); the loss-making
profile by campaign type × audience × channel mode; funnel-integrity violations and
duplicate IDs; and time-series + festival-window concentration. The ROI-verification
step is the most important — it determines whether downstream models can treat
`roi_reported` as a literal multiplier or only as an ordinal index.

### Stage 3 — Statistical group-difference testing (ANOVA + Tukey HSD)

For each categorical grouping (campaign type, target audience, language, brand) we
run a one-way ANOVA on `roi_reported`, report the F-statistic, p-value, and
**η² effect size**, then follow with Tukey's HSD for pairwise comparisons that
correct for the multiple-comparisons problem. With ~166k rows any difference would
be flagged as significant by raw p-values, so we lean on η² (variance explained)
to gauge *practical* significance rather than statistical.

### Stage 4 — Causal inference pipeline (the flagship)

The causal chapter is a **flexible framework** that accepts any binary treatment
definition and returns five triangulated effect estimates with diagnostics and
sensitivity analyses. It runs in seven phases:

**Phase 1 — Pre-specification.** Treatments, outcome, confounders, and estimand are
fixed in code *before* any model is fit. Three pre-specified treatments live in a
`TREATMENTS` dictionary: `influencer_vs_other`, `multi_vs_single`,
`festival_vs_not`. The outcome is `conv_rate = conversions / impressions` (bounded
[0,1], avoids the ROI synthetic-noise issue). The confounder set is restricted to
pre-treatment campaign attributes (`target_audience`, `customer_segment`,
`language`, `brand`, `duration_days`, `log_acq_cost`, `in_festival_window`). A
`FORBIDDEN_MEDIATORS` constant lists post-treatment funnel quantities
(impressions, clicks, leads, conversions, revenue, engagement_score) that the
pipeline *refuses* to accept as confounders — this guardrail prevents the most
common mistake in observational causal analysis.

**Phase 2 — Pre-flight checks.** Three guards before any model is fit: the
mediator guardrail (raises if a forbidden variable slipped in), a minimum
sample-size check per treatment arm, and a positivity check (flags any cell of
the categorical confounder space where treated or control rows are missing).

**Phase 3 — Cross-fitted nuisance models.** Two models are fit in a 5-fold
cross-fitting loop. The **propensity model** is a regularized logistic regression
estimating `ê(X) = P(T = 1 | X)`. The **outcome model** is a linear regression
estimating `μ̂_T(X) = E[Y | T, X]`, fit separately on the treated and control arms
(T-learner pattern). Cross-fitting — predicting on each fold using a model that
never saw that fold's rows — removes the regularization bias that breaks classical
inference when ML models are used as nuisance learners.

**Phase 4 — Five triangulated estimators.** All five are computed from the cached
nuisance arrays so they share inputs:

- **Naive difference** — `Y[T=1].mean() - Y[T=0].mean()`. Confounded baseline.
- **Matched ATT** — for each treated campaign, find its nearest-neighbor control
  by propensity score; report the mean treated-minus-control difference.
- **IPW ATE** — inverse-propensity weighting: each row is weighted by `1 / ê(X)`
  if treated, `1 / (1 − ê(X))` if control.
- **Outcome regression ATE (g-computation)** — `(μ̂₁(X) − μ̂₀(X)).mean()`.
- **AIPW ATE (headline)** — the *doubly-robust* combination:
  `(μ̂₁ − μ̂₀) + T(Y − μ̂₁)/ê(X) − (1 − T)(Y − μ̂₀)/(1 − ê(X))`. Consistent if
  *either* the propensity model or the outcome model is correctly specified, not
  both. CIs computed via 500-iteration bootstrap on the cached AIPW influence
  terms.

**Phase 5 — Diagnostics.** Propensity-overlap histogram (treated vs control
densities across the score range), calibration curve (predicted vs empirical
treatment rate per propensity bin), and a standardized-mean-difference balance
table showing each confounder's |SMD| before and after matching. Rule of thumb:
|SMD| < 0.1 = well-balanced.

**Phase 6 — Sensitivity.** Three robustness checks. The **caliper sweep** re-runs
matching at five caliper widths and reports the matched ATT for each — a stable
estimate across calipers is evidence of robustness. The **placebo test** shuffles
treatment labels at random and re-runs the AIPW; the placebo ATE should be near
zero, which is the unit test that the pipeline isn't fabricating effects. The
**E-value** quantifies how strong an unmeasured confounder would need to be to
overturn the headline estimate.

**Phase 7 — Reporting.** A five-row forest plot per treatment with 95% CIs, plus
a markdown findings file (`reports/causal_findings_<treatment>.md`) containing
the results table, sensitivity tables, and explicit caveats. The orchestrator
loops Phases 2–7 across all pre-specified treatments and concatenates results
into `reports/causal_summary.csv`.

## Results & analysis

The pipeline was executed end-to-end on the full 166,665-row dataset. The
headline finding is uniform across stages and treatments: **no detectable
structural effects exist in this dataset**, at any layer of analysis.

### Data quality (Stage 2)

The three brands' marginal distributions are statistically indistinguishable:
mean ROI of 2.71, 2.68, and 2.67 (range across brands: 0.04), and loss share of
0.458, 0.461, and 0.459 (range: 0.003), each with sample sizes of exactly 55,555.
Combined with identical date ranges, identical audience/language/campaign-type
sets, this is strong evidence that the three CSVs were drawn from a shared
synthetic generator. The project is therefore framed as a *multi-brand portfolio
methodology demonstration*, not a competitive-benchmark study.

The supplied `ROI` column does not equal `Revenue / Acquisition_Cost`: median
absolute difference of 1,761 against either candidate formula, but a Spearman
correlation of 0.90. Conclusion: `roi_reported` is a noisy ordinal index, not a
literal multiplier. For interpretability we use `conv_rate` as the primary
outcome in all causal modeling and keep `roi_reported` only for ranking
campaigns.

46% of campaigns are loss-making (ROI < 1). The loss share is uniformly ~0.46
across every (campaign_type × audience × channel_mode) cell — the top-15
worst-performing cells differ from the overall mean by less than 3 percentage
points. There is no segment that concentrates losses. The festival-window vs
non-festival-window comparison is also flat (2.685 vs 2.698 mean ROI;
0.4592 vs 0.4600 loss share). Both findings indicate the synthetic generator did
not encode segment-specific structural effects.

### Statistical group differences (Stage 3)

All four ANOVAs failed to reject the null hypothesis of equal means:

| Grouping       | F     | p     | η²     | Verdict                       |
|----------------|-------|-------|--------|-------------------------------|
| Campaign type  | 1.115 | 0.347 | 0.0000 | No detectable difference      |
| Target audience| 0.391 | 0.816 | 0.0000 | No detectable difference      |
| Language       | 1.718 | 0.161 | 0.0000 | No detectable difference      |
| Brand          | 1.164 | 0.312 | 0.0000 | No detectable difference      |

Every Tukey HSD pairwise comparison across all four ANOVAs returned
`reject = False`. The η² effect sizes round to 0.0000 in every test — meaning
none of these categorical groupings explains even 0.01% of the variance in
`roi_reported`. With n = 166,665 the statistical test had enormous power; the
failure to detect *anything* is itself the result.

### Causal estimates — Influencer vs Other (Stage 4)

Five estimators on conversion rate, with the headline AIPW estimate's 95% CI:

| Method                       | Estimand | Estimate    | 95% CI                |
|------------------------------|----------|-------------|-----------------------|
| Naive difference             | naive    | +0.000004   | —                     |
| Matched ATT (no caliper)     | ATT      | +0.000020   | —                     |
| IPW ATE                      | ATE      | +0.000073   | —                     |
| Outcome regression ATE       | ATE      | +0.000053   | —                     |
| **AIPW ATE (headline)**      | **ATE**  | **+0.000056** | **[−0.000039, +0.000161]** |

All five estimators converge in the same neighborhood — point estimates within
±0.00007 of each other — which is the cross-validation pattern you want when
multiple methods agree. On a base conversion rate of ~0.0187, the AIPW point
estimate represents a ~0.3% relative effect, and the 95% CI cleanly straddles
zero. The propensity score range is also unusually tight (`ê(X) ∈ [0.18, 0.22]`),
meaning the pre-treatment confounders barely predict whether a campaign was run
as Influencer or not — further evidence that there is no structural selection
process in the synthetic data.

### Sensitivity results

**Caliper sweep** — the matched ATT is exactly +0.00002 across all five caliper
widths tested (no trim, 0.10, 0.05, 0.01, 0.005). Perfectly stable; no estimate
sensitivity to the matching threshold.

**Placebo test** — random shuffling of treatment labels produced AIPW ATEs of
−0.000041 and −0.000020 across two placebo runs. Both are within the noise
neighborhood of the real estimate, confirming the pipeline does not fabricate
effects on data with no treatment structure. This is the most important
diagnostic in the entire report — it proves the framework is *internally valid*.

**E-value** — 1.01 against the naive risk-ratio proxy of 1.0002. Interpretation:
an unmeasured confounder would only need a risk ratio of 1.01 with both
treatment and outcome to fully explain away the estimated effect. The threshold
is so low because the effect itself is so close to zero — there is essentially
nothing to overturn.

### What this means

Three concurrent layers of analysis — descriptive (EDA), inferential (ANOVA),
and causal (AIPW with full sensitivity) — independently converge on the same
conclusion: this dataset contains no detectable structural effects between the
campaign-attribute treatments and either ROI or conversion rate. The synthetic
generator behind these three "brand" CSVs draws features and outcomes
near-independently, producing a dataset that is excellent for *demonstrating
the analytical framework* and useless for drawing real conclusions about beauty
e-commerce marketing.

This is the welcome result, not the disappointing one. A pipeline that returns
null effects on data with no structural signal — and confirms its own validity
via the placebo test — is correctly implemented. The same code, applied to real
brand telemetry, would surface the genuine effects that this synthetic data is
designed to obscure. The framework, the discipline (pre-specified confounders,
mediator guardrails, triangulated estimators, mandatory diagnostics, sensitivity
analyses), and the reproducible warehouse → notebook → report pipeline are the
deliverable.


## Deliverables checklist

- [x] DuckDB database with staging, enriched, and mart layers
- [x] EDA report: data quality + ROI formula verification
- [x] Statistical testing layer (ANOVA + Tukey HSD with η² effect sizes)
- [x] Causal pipeline: pre-specified treatments, cross-fitted nuisance models,
      five triangulated estimators, full diagnostic suite, sensitivity analyses
- [x] Forest plots + per-treatment markdown findings files
