"""Rule based insights. Every rule is simple, and its thresholds can be changed."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .formatting import money, multiple, percent
from .metrics import by_campaign, ratio

SEVERITY_ORDER = {"warning": 0, "good": 1, "info": 2}


@dataclass(frozen=True)
class Insight:
    kind: str
    severity: str  # "warning", "good", or "info"
    title: str
    detail: str


def _leaders(campaigns: pd.DataFrame, min_share: float, currency: str) -> list[Insight]:
    pool = campaigns[campaigns["spend_share"] >= min_share]
    if len(pool) < 2:
        return []
    if pool["revenue"].sum() > 0:
        ranked = pool.sort_values("roas", ascending=False)
        best, worst = ranked.iloc[0], ranked.iloc[-1]
        return [
            Insight("leader", "good", f"Best return: {best['campaign']}",
                    f"ROAS of {multiple(best['roas'])} on {money(best['spend'], currency)} spend."),
            Insight("laggard", "warning", f"Weakest return: {worst['campaign']}",
                    f"ROAS of {multiple(worst['roas'])} on "
                    f"{money(worst['spend'], currency)} spend."),
        ]
    if pool["conversions"].sum() > 0:
        ranked = pool[pool["conversions"] > 0].sort_values("cpa")
        if len(ranked) < 2:
            return []
        best, worst = ranked.iloc[0], ranked.iloc[-1]
        return [
            Insight("leader", "good", f"Cheapest results: {best['campaign']}",
                    f"Cost per result of {money(best['cpa'], currency)}."),
            Insight("laggard", "warning", f"Most expensive results: {worst['campaign']}",
                    f"Cost per result of {money(worst['cpa'], currency)}."),
        ]
    return []


def _wasted_spend(campaigns: pd.DataFrame, min_share: float, currency: str) -> list[Insight]:
    # Only meaningful when the file tracks conversions at all.
    if campaigns["conversions"].sum() <= 0:
        return []
    wasted = campaigns[(campaigns["spend_share"] >= min_share) & (campaigns["conversions"] == 0)]
    return [
        Insight("waste", "warning", f"No conversions: {row['campaign']}",
                f"Spent {money(row['spend'], currency)} ({percent(row['spend_share'], 1)} of the "
                "budget) with no conversions. Review the audience, the creative, or the goal.")
        for _, row in wasted.iterrows()
    ]


def _trend(df: pd.DataFrame, change_limit: float) -> list[Insight]:
    last_day = df["date"].max()
    recent = df[df["date"] > last_day - pd.Timedelta(7, unit="D")]
    previous = df[(df["date"] <= last_day - pd.Timedelta(7, unit="D"))
                  & (df["date"] > last_day - pd.Timedelta(14, unit="D"))]
    if df["date"].nunique() < 14 or previous.empty:
        return []

    use_cpa = df["conversions"].sum() > 0
    label = "cost per result" if use_cpa else "click-through rate"

    def value(part: pd.DataFrame) -> float | None:
        if use_cpa:
            return ratio(part["spend"].sum(), part["conversions"].sum())
        return ratio(part["clicks"].sum(), part["impressions"].sum())

    now, before = value(recent), value(previous)
    # A zero baseline gives no meaningful percentage, so there is nothing to compare against.
    if now is None or before is None or before == 0:
        return []
    change = (now - before) / before
    if abs(change) < change_limit:
        return []
    # For cost, lower is better. For click-through rate, higher is better.
    worse = change > 0 if use_cpa else change < 0
    direction = "up" if change > 0 else "down"
    return [Insight("trend", "warning" if worse else "good",
                    f"Account {label} is {direction} {abs(change) * 100:.0f}% week on week",
                    "Compared with the previous 7 days.")]


def _frequency(df: pd.DataFrame, limit: float) -> list[Insight]:
    last_day = df["date"].max()
    recent = df[(df["date"] > last_day - pd.Timedelta(7, unit="D")) & (df["reach"] > 0)]
    if recent.empty:
        return []
    totals = recent.groupby("campaign")[["impressions", "reach"]].sum()
    insights = []
    for campaign, row in totals.iterrows():
        frequency = row["impressions"] / row["reach"]
        if frequency > limit:
            insights.append(Insight(
                "frequency", "warning", f"High ad frequency: {campaign}",
                f"People saw these ads about {frequency:.1f} times per day on average in the last "
                "7 days. Refresh the creative or widen the audience to avoid ad fatigue."))
    return insights


def generate_insights(
    df: pd.DataFrame,
    *,
    currency: str = "USD",
    min_spend_share: float = 0.05,
    trend_change: float = 0.15,
    frequency_limit: float = 3.0,
) -> list[Insight]:
    campaigns = by_campaign(df)
    insights = [
        *_leaders(campaigns, min_spend_share, currency),
        *_wasted_spend(campaigns, min_spend_share, currency),
        *_trend(df, trend_change),
        *_frequency(df, frequency_limit),
    ]
    if not insights:
        insights.append(Insight("info", "info", "No issues found",
                                "None of the checks found a problem in this data."))
    return sorted(insights, key=lambda item: SEVERITY_ORDER[item.severity])

