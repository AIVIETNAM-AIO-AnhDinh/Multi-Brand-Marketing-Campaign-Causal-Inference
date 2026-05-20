-- Funnel-rate marts at varying grains
-- All rates are volume-weighted (sum of numerators / sum of denominators),
-- which is more honest than average-of-row-rates for skewed distributions.

CREATE OR REPLACE VIEW mart_funnel_by_type_channel_audience AS
SELECT
    brand,
    campaign_type,
    channel_mode,
    target_audience,
    COUNT(*)                                                          AS n_campaigns,
    SUM(impressions)                                                  AS total_impressions,
    SUM(clicks)                                                       AS total_clicks,
    SUM(leads)                                                        AS total_leads,
    SUM(conversions)                                                  AS total_conversions,
    SUM(revenue)                                                      AS total_revenue,
    SUM(acquisition_cost)                                             AS total_cost,
    SUM(clicks)::DOUBLE      / NULLIF(SUM(impressions), 0)            AS ctr_w,
    SUM(leads)::DOUBLE       / NULLIF(SUM(clicks), 0)                 AS click_to_lead_w,
    SUM(conversions)::DOUBLE / NULLIF(SUM(leads), 0)                  AS lead_to_conv_w,
    SUM(revenue)::DOUBLE     / NULLIF(SUM(conversions), 0)            AS revenue_per_conv_w,
    SUM(revenue)::DOUBLE     / NULLIF(SUM(acquisition_cost), 0)       AS rev_to_cost_w,
    AVG(roi_reported)                                                 AS roi_avg,
    APPROX_QUANTILE(roi_reported, 0.5)                                AS roi_median,
    AVG(is_loss_making)                                               AS loss_share,
    AVG(engagement_score)                                             AS engagement_avg
FROM campaigns_enriched
GROUP BY 1, 2, 3, 4;


CREATE OR REPLACE VIEW mart_brand_monthly AS
SELECT
    brand,
    year,
    month,
    DATE_TRUNC('month', campaign_date)            AS month_start,
    COUNT(*)                                       AS n_campaigns,
    SUM(impressions)                               AS impressions,
    SUM(conversions)                               AS conversions,
    SUM(revenue)                                   AS revenue,
    SUM(acquisition_cost)                          AS cost,
    AVG(roi_reported)                              AS roi_avg,
    AVG(is_loss_making)                            AS loss_share,
    SUM(CASE WHEN in_festival_window THEN 1 ELSE 0 END) AS festival_window_campaigns
FROM campaigns_enriched
GROUP BY brand, year, month, DATE_TRUNC('month', campaign_date);


CREATE OR REPLACE VIEW mart_audience_channel_matrix AS
SELECT
    target_audience,
    channel_used,
    COUNT(*)                                       AS n_campaigns,
    AVG(roi_reported)                              AS roi_avg,
    APPROX_QUANTILE(roi_reported, 0.5)             AS roi_median,
    AVG(is_loss_making)                            AS loss_share,
    AVG(engagement_score)                          AS engagement_avg
FROM campaigns_enriched
GROUP BY 1, 2;
