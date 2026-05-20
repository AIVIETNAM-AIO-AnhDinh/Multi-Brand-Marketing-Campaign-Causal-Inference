-- Enriched: join campaigns to the festival calendar
CREATE OR REPLACE VIEW campaigns_enriched AS
SELECT
    c.*,
    cal.dow,
    cal.is_weekend,
    cal.month,
    cal.quarter,
    cal.year,
    cal.iso_week,
    cal.festival_name        AS launched_on_festival,
    cal.festival_window_name AS in_festival_window_name,
    cal.in_festival_window
FROM stg_campaigns c
LEFT JOIN dim_calendar cal
  ON c.campaign_date = cal.date;
