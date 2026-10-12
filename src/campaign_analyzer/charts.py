"""Charts are drawn with matplotlib and returned as base64 PNG text for the HTML report."""

from __future__ import annotations

import base64
import io

import matplotlib

matplotlib.use("Agg")  # Draw without a screen, so it also works on servers.
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

BLUE, ORANGE, GREEN, GREY = "#4f46e5", "#f59e0b", "#10b981", "#6b7185"


def _encode(figure: plt.Figure) -> str:
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=130, bbox_inches="tight")
    plt.close(figure)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def daily_chart(daily: pd.DataFrame, currency: str) -> str:
    figure, axis = plt.subplots(figsize=(8, 3.2))
    axis.plot(daily["date"], daily["spend"], color=BLUE, linewidth=2, label=f"Spend ({currency})")
    axis.set_ylabel(f"Spend ({currency})", color=BLUE)
    second = axis.twinx()
    has_results = daily["conversions"].sum() > 0
    column = "conversions" if has_results else "clicks"
    second.plot(daily["date"], daily[column], color=ORANGE, linewidth=2, label=column.title())
    second.set_ylabel(column.title(), color=ORANGE)
    # Start both axes at zero, so small day to day noise does not look like a big swing.
    axis.set_ylim(bottom=0)
    second.set_ylim(bottom=0)
    axis.set_title("Daily spend and " + column)
    axis.grid(alpha=0.2)
    figure.autofmt_xdate()
    return _encode(figure)


def spend_chart(campaigns: pd.DataFrame, currency: str) -> str:
    ordered = campaigns.sort_values("spend")
    figure, axis = plt.subplots(figsize=(8, max(2.2, 0.55 * len(ordered) + 1)))
    axis.barh(ordered["campaign"], ordered["spend"], color=BLUE)
    axis.set_xlabel(f"Spend ({currency})")
    axis.set_title("Spend by campaign")
    axis.grid(axis="x", alpha=0.2)
    return _encode(figure)


def efficiency_chart(campaigns: pd.DataFrame) -> str | None:
    """ROAS when revenue is tracked, otherwise cost per result. None when neither exists."""
    if campaigns["revenue"].sum() > 0:
        column, title, color = "roas", "Return on ad spend (ROAS) by campaign", GREEN
    elif campaigns["conversions"].sum() > 0:
        column, title, color = "cpa", "Cost per result by campaign (lower is better)", ORANGE
    else:
        return None
    data = campaigns.dropna(subset=[column]).sort_values(column)
    if data.empty:
        return None
    figure, axis = plt.subplots(figsize=(8, max(2.2, 0.55 * len(data) + 1)))
    axis.barh(data["campaign"], data[column], color=color)
    axis.set_title(title)
    if column == "roas":
        axis.axvline(1, color=GREY, linestyle="--", linewidth=1)  # Break-even line.
    axis.grid(axis="x", alpha=0.2)
    return _encode(figure)
