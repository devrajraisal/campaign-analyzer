"""Advertising metrics. Every rate returns NaN or None when the denominator is zero."""

from __future__ import annotations

import math

import pandas as pd

SUMS = ["impressions", "clicks", "spend", "conversions", "revenue"]


def ratio(numerator: float, denominator: float) -> float | None:
    """Divide, returning None instead of raising or returning infinity."""
    if not denominator:
        return None
    return float(numerator) / float(denominator)


def _series_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator / denominator.where(denominator != 0)


def add_rates(df: pd.DataFrame) -> pd.DataFrame:
    """Add CTR, CPC, CPM, conversion rate, CPA, and ROAS columns to summed data."""
    out = df.copy()
    out["ctr"] = _series_ratio(out["clicks"], out["impressions"])
    out["cpc"] = _series_ratio(out["spend"], out["clicks"])
    out["cpm"] = _series_ratio(out["spend"], out["impressions"]) * 1000
    out["conv_rate"] = _series_ratio(out["conversions"], out["clicks"])
    out["cpa"] = _series_ratio(out["spend"], out["conversions"])
    out["roas"] = _series_ratio(out["revenue"], out["spend"])
    return out


def clean_number(value: float | None) -> float | None:
    """Convert NaN to None so results can be written as JSON."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def summarize(df: pd.DataFrame) -> dict:
    totals = {name: float(df[name].sum()) for name in SUMS}
    summary: dict = {
        **totals,
        "ctr": ratio(totals["clicks"], totals["impressions"]),
        "cpc": ratio(totals["spend"], totals["clicks"]),
        "cpm": (
            ratio(totals["spend"], totals["impressions"]) * 1000 if totals["impressions"] else None
        ),
        "conv_rate": ratio(totals["conversions"], totals["clicks"]),
        "cpa": ratio(totals["spend"], totals["conversions"]),
        # Without any revenue column there is no ROAS to report, so 0.0 would be misleading.
        "roas": ratio(totals["revenue"], totals["spend"]) if totals["revenue"] > 0 else None,
        "start": df["date"].min().date().isoformat(),
        "end": df["date"].max().date().isoformat(),
        "days": int(df["date"].nunique()),
        "campaigns": int(df["campaign"].nunique()),
        "has_conversions": totals["conversions"] > 0,
        "has_revenue": totals["revenue"] > 0,
    }
    return summary


def by_campaign(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("campaign", as_index=False)[SUMS].sum()
    grouped = add_rates(grouped)
    total_spend = grouped["spend"].sum()
    grouped["spend_share"] = grouped["spend"] / total_spend if total_spend else 0.0
    return grouped.sort_values("spend", ascending=False).reset_index(drop=True)


def by_day(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("date", as_index=False)[SUMS].sum()
    return add_rates(grouped).sort_values("date").reset_index(drop=True)
