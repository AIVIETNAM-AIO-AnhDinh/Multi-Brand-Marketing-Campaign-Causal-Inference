"""Indian festival + e-commerce sale-period calendar for Jul 2024 – Jun 2025.

Builds a daily calendar dimension with festival windows so we can isolate the
seasonality structure of campaign performance without needing to enrich with
external data.

The festival windows use approximate lead/trail days that reflect when brands
typically *run* campaigns around each event, not just the date itself.
Adjust if you have better priors.
"""
from __future__ import annotations

import pandas as pd

# Format: (date, name, type, lead_days, trail_days)
# type: "festival" = cultural / religious event
#       "ecommerce_sale" = retail sale window (Big Billion Days, Republic Day sales, etc.)
FESTIVALS: list[tuple[str, str, str, int, int]] = [
    ("2024-08-15", "Independence Day Sales", "ecommerce_sale", 7, 3),
    ("2024-08-19", "Raksha Bandhan", "festival", 5, 1),
    ("2024-08-26", "Janmashtami", "festival", 3, 1),
    ("2024-09-07", "Ganesh Chaturthi", "festival", 5, 2),
    ("2024-09-15", "Onam", "festival", 7, 2),
    ("2024-10-03", "Navratri Start", "festival", 3, 9),
    ("2024-10-12", "Dussehra", "festival", 2, 1),
    ("2024-10-20", "Karwa Chauth", "festival", 5, 1),
    ("2024-10-31", "Diwali", "festival", 10, 3),
    ("2024-11-03", "Bhai Dooj", "festival", 1, 1),
    ("2024-12-25", "Christmas", "festival", 7, 2),
    ("2025-01-01", "New Year", "festival", 3, 1),
    ("2025-01-13", "Lohri", "festival", 1, 1),
    ("2025-01-14", "Pongal/Makar Sankranti", "festival", 2, 1),
    ("2025-01-26", "Republic Day Sales", "ecommerce_sale", 7, 3),
    ("2025-02-14", "Valentine's Day", "festival", 5, 1),
    ("2025-03-14", "Holi", "festival", 3, 1),
    ("2025-03-30", "Ugadi/Gudi Padwa", "festival", 2, 1),
    ("2025-03-31", "Eid al-Fitr", "festival", 3, 1),
    ("2025-04-30", "Akshaya Tritiya", "festival", 5, 1),
    ("2025-05-15", "Wedding/Summer Sales", "ecommerce_sale", 14, 14),
    ("2025-06-07", "Eid al-Adha", "festival", 3, 1),
]


def build_calendar(start: str = "2024-07-01", end: str = "2025-06-30") -> pd.DataFrame:
    """Build a daily calendar with festival window flags."""
    dates = pd.date_range(start, end, freq="D")
    cal = pd.DataFrame({"date": dates})
    cal["dow"] = cal["date"].dt.day_name()
    cal["dow_num"] = cal["date"].dt.dayofweek
    cal["month"] = cal["date"].dt.month
    cal["quarter"] = cal["date"].dt.quarter
    cal["year"] = cal["date"].dt.year
    cal["iso_week"] = cal["date"].dt.isocalendar().week.astype(int)
    cal["is_weekend"] = cal["dow_num"] >= 5
    cal["festival_name"] = pd.NA
    cal["festival_type"] = pd.NA
    cal["in_festival_window"] = False
    cal["festival_window_name"] = pd.NA

    for raw_date, name, ftype, lead, trail in FESTIVALS:
        d = pd.Timestamp(raw_date)
        window_start = d - pd.Timedelta(days=lead)
        window_end = d + pd.Timedelta(days=trail)
        in_window = (cal["date"] >= window_start) & (cal["date"] <= window_end)
        # don't overwrite an existing window name if the new one is shorter
        new_window = in_window & cal["festival_window_name"].isna()
        cal.loc[in_window, "in_festival_window"] = True
        cal.loc[new_window, "festival_window_name"] = name
        on_day = cal["date"] == d
        cal.loc[on_day, "festival_name"] = name
        cal.loc[on_day, "festival_type"] = ftype

    return cal


if __name__ == "__main__":
    df = build_calendar()
    print(f"Calendar covers {len(df)} days")
    print(f"  festival-window days: {df['in_festival_window'].sum()}")
    print(f"  weekend days:         {df['is_weekend'].sum()}")
    print("\nFestival anchor days:")
    print(
        df[df["festival_name"].notna()][
            ["date", "festival_name", "festival_type"]
        ].to_string(index=False)
    )
