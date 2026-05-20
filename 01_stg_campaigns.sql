-- Staging: clean column names, parse types, add derived per-row metrics
CREATE OR REPLACE VIEW stg_campaigns AS
SELECT
    Campaign_ID                                                           AS campaign_id,
    brand,
    Campaign_Type                                                         AS campaign_type,
    Target_Audience                                                       AS target_audience,
    Customer_Segment                                                      AS customer_segment,
    Channel_Used                                                          AS channel_used,
    Language                                                              AS language,
    CAST(Duration AS INTEGER)                                             AS duration_days,
    CAST(Date AS DATE)                                                    AS campaign_date,
    CAST(Impressions AS BIGINT)                                           AS impressions,
    CAST(Clicks AS BIGINT)                                                AS clicks,
    CAST(Leads AS BIGINT)                                                 AS leads,
    CAST(Conversions AS BIGINT)                                           AS conversions,
    CAST(Revenue AS DOUBLE)                                               AS revenue,
    CAST(Acquisition_Cost AS DOUBLE)                                      AS acquisition_cost,
    CAST(ROI AS DOUBLE)                                                   AS roi_reported,
    CAST(Engagement_Score AS DOUBLE)                                      AS engagement_score,

    -- Derived per-row funnel rates
    CASE WHEN Impressions > 0 THEN Clicks::DOUBLE / Impressions END       AS ctr,
    CASE WHEN Clicks > 0      THEN Leads::DOUBLE  / Clicks END            AS click_to_lead,
    CASE WHEN Leads > 0       THEN Conversions::DOUBLE / Leads END        AS lead_to_conv,
    CASE WHEN Impressions > 0 THEN Conversions::DOUBLE / Impressions END  AS imp_to_conv,
    CASE WHEN Conversions > 0 THEN Revenue::DOUBLE / Conversions END      AS revenue_per_conv,
    CASE WHEN Impressions > 0 THEN Conversions::DOUBLE / Impressions END  AS conv_rate,
    -- Two independent ROI definitions to compare against the supplied column
    CASE WHEN Acquisition_Cost > 0
         THEN Revenue::DOUBLE / Acquisition_Cost END                      AS roi_rev_over_cost,
    CASE WHEN Acquisition_Cost > 0
         THEN (Revenue - Acquisition_Cost) / Acquisition_Cost END         AS roi_net_over_cost,

    -- Channel mode: single vs multi
    CASE WHEN Channel_Used LIKE '%,%' THEN 'multi' ELSE 'single' END       AS channel_mode,

    -- Profitability flag (reported ROI < 1 → losing money on a multiplier basis)
    CASE WHEN ROI < 1 THEN 1 ELSE 0 END                                   AS is_loss_making
FROM campaigns_raw;
