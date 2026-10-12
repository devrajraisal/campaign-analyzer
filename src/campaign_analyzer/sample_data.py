"""Generate synthetic campaign data, so the tool can be tried without a real export.

The numbers are made up by a seeded random generator. They are only for demos and tests,
and they are built to contain a few realistic problems for the insights to find:
no conversions on one campaign, ad fatigue on another, and a drop in the last week.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

# name, daily budget, CPM, click rate, conversion rate, average order value
CAMPAIGNS = [
    ("Retargeting - Cart Abandoners", 40.0, 6.0, 0.022, 0.060, 38.0),
    ("Lookalike 1% - Purchasers", 90.0, 11.0, 0.012, 0.025, 42.0),
    ("Broad - Video Views", 70.0, 3.5, 0.004, 0.0, 0.0),
    ("Interest - Streetwear", 60.0, 9.0, 0.010, 0.012, 40.0),
    ("Brand Awareness", 30.0, 4.5, 0.006, 0.003, 35.0),
]
AD_SETS = ("Audience A", "Audience B")


def generate_sample(days: int = 60, seed: int = 42, start: date | None = None) -> pd.DataFrame:
    if days < 1:
        raise ValueError("days must be at least 1")
    rng = np.random.default_rng(seed)
    first_day = pd.Timestamp(start or date(2026, 8, 1))
    rows = []
    for day_index in range(days):
        current = first_day + pd.Timedelta(day_index, unit="D")
        progress = day_index / max(days - 1, 1)
        for name, budget, cpm, click_rate, conv_rate, order_value in CAMPAIGNS:
            click_factor, conv_factor = 1.0, 1.0
            frequency = 1.3
            if name.startswith("Retargeting"):
                # The small retargeting audience sees the same ads more and more often,
                # and in the last week results fall because of ad fatigue.
                frequency = 1.4 + 2.8 * progress
                if day_index >= days - 7:
                    click_factor, conv_factor = 0.85, 0.6
            for ad_set in AD_SETS:
                spend = budget / 2 * rng.uniform(0.9, 1.1)
                impressions = int(spend / cpm * 1000)
                clicks = int(rng.binomial(impressions, click_rate * click_factor))
                conversions = int(rng.binomial(clicks, conv_rate * conv_factor))
                revenue = round(conversions * order_value * rng.uniform(0.9, 1.1), 2)
                rows.append({
                    "date": current.date().isoformat(),
                    "campaign": name,
                    "ad_set": ad_set,
                    "impressions": impressions,
                    "reach": int(impressions / frequency),
                    "clicks": clicks,
                    "spend": round(spend, 2),
                    "conversions": conversions,
                    "revenue": revenue,
                })
    return pd.DataFrame(rows)
