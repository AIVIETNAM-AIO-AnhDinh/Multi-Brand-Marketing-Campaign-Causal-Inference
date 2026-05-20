import numpy as np
import pandas as pd

def bootstrap_ci(values, statistic=np.mean, n_resamples=2000, ci=95, seed=7):
    """Return (point, lo, hi) using the percentile method."""
    rng = np.random.default_rng(seed)
    values = np.asarray(values)
    values = values[~np.isnan(values)]
    if len(values) == 0:
        return np.nan, np.nan, np.nan
    point = statistic(values)
    # vectorized resampling: build an (n_resamples × len(values)) index matrix
    idx = rng.integers(0, len(values), size=(n_resamples, len(values)))
    boot = statistic(values[idx], axis=1)
    alpha = (100 - ci) / 2
    lo, hi = np.percentile(boot, [alpha, 100 - alpha])
    return point, lo, hi
def bootstrap_summary(df, group_col, value_col):
    rows = []
    for name, sub in df.groupby(group_col):
        pt, lo, hi = bootstrap_ci(sub[value_col].values)
        rows.append({group_col: name, "n": len(sub), "mean": pt, "ci_lo": lo, "ci_hi": hi})
    return pd.DataFrame(rows)

def bootstrap_diff_ci(a, b, n_resamples=2000, ci=95, seed=7):
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a), np.asarray(b)
    ai = rng.integers(0, len(a), size=(n_resamples, len(a)))
    bi = rng.integers(0, len(b), size=(n_resamples, len(b)))
    diffs = a[ai].mean(axis=1) - b[bi].mean(axis=1)
    point = a.mean() - b.mean()
    alpha = (100 - ci) / 2
    lo, hi = np.percentile(diffs, [alpha, 100 - alpha])
    return point, lo, hi
def anova_with_effect_size(df, value_col, group_col):
    """Return F, p, eta_sq, plus the Tukey HSD table."""
    from statsmodels.formula.api import ols
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    import statsmodels.api as sm
    formula = f"{value_col} ~ C({group_col})"
    model = ols(formula, data=df).fit()
    table = sm.stats.anova_lm(model, typ=2)
    ss_between = table.loc[f"C({group_col})", "sum_sq"]
    ss_total = ss_between + table.loc["Residual", "sum_sq"]
    eta_sq = ss_between / ss_total
    F = table.loc[f"C({group_col})", "F"]
    p = table.loc[f"C({group_col})", "PR(>F)"]
    tukey = pairwise_tukeyhsd(df[value_col], df[group_col], alpha=0.05)
    return {"F": F, "p": p, "eta_sq": eta_sq, "tukey": tukey.summary(), "model": model}
def welch_anova_with_effect_size(df, value_col, group_col):
    """Return F, p, effect_size (np2), plus the Games-Howell table."""
    from pingouin import welch_anova, pairwise_gameshowell
    
    anova = welch_anova(data=df, dv=value_col, between=group_col)
    
    # Safely identify the p-value column depending on pingouin version
    if 'p-unc' in anova.columns:
        p_col = 'p-unc'
    elif 'p' in anova.columns:
        p_col = 'p'
    else:
        # Fallback to taking the first column that starts with 'p' if needed
        p_col = next((col for col in anova.columns if col.startswith('p')), None)
    
    # Pingouin's welch_anova returns 'np2' (Partial eta-squared)
    eff_size = anova["np2"].values[0] if "np2" in anova.columns else None
    
    tukey = pairwise_gameshowell(data=df, dv=value_col, between=group_col)
    
    return {
        "F": anova["F"].values[0], 
        "p": anova[p_col].values[0], 
        "np2": eff_size,  
        "tukey": tukey
    }
FORBIDDEN_MEDIATORS = [
    "impressions",
    "clicks", "leads",
    "conversions",
    "revenue",
    "engagement_score",
    "roi_reported",
    "roi_rev_over_cost",
    "ctr", "lead_to_conv",
]

def validate_confounders(confounders: list[str]) -> None:
    leaks = [c for c in confounders if c in FORBIDDEN_MEDIATORS]
    if leaks:
        raise ValueError(
            f"Mediators in confounder list: {leaks}. "
            f"Causal estimates including mediators are biased."
        )
