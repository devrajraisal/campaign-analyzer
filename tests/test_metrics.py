import math

import pandas as pd

from campaign_analyzer.loader import load_campaigns
from campaign_analyzer.metrics import add_rates, by_campaign, by_day, clean_number, ratio, summarize
from conftest import csv_text


def test_ratio_never_divides_by_zero():
    assert ratio(10, 4) == 2.5
    assert ratio(10, 0) is None


def test_rates_follow_the_standard_formulas():
    df = pd.DataFrame([{"impressions": 10000, "clicks": 200, "spend": 100.0,
                        "conversions": 10, "revenue": 400.0}])
    row = add_rates(df).iloc[0]
    assert math.isclose(row["ctr"], 0.02)
    assert math.isclose(row["cpc"], 0.5)
    assert math.isclose(row["cpm"], 10.0)
    assert math.isclose(row["conv_rate"], 0.05)
    assert math.isclose(row["cpa"], 10.0)
    assert math.isclose(row["roas"], 4.0)


def test_zero_denominators_give_nan_not_infinity():
    df = pd.DataFrame([{"impressions": 0, "clicks": 0, "spend": 5.0, "conversions": 0,
                        "revenue": 0.0}])
    row = add_rates(df).iloc[0]
    assert all(math.isnan(row[name]) for name in ["ctr", "cpc", "cpm", "conv_rate", "cpa"])
    assert row["roas"] == 0


def test_summary_totals_and_flags():
    rows = ["2026-10-01,A,1000,20,10", "2026-10-02,B,3000,40,30"]
    summary = summarize(load_campaigns(csv_text(rows)).data)
    assert summary["spend"] == 40 and summary["clicks"] == 60 and summary["impressions"] == 4000
    assert summary["days"] == 2 and summary["campaigns"] == 2
    assert (summary["start"], summary["end"]) == ("2026-10-01", "2026-10-02")
    assert summary["has_conversions"] is False and summary["has_revenue"] is False
    assert summary["cpa"] is None and summary["roas"] is None


def test_campaign_table_is_sorted_and_shares_add_up(sample_df):
    table = by_campaign(sample_df)
    assert table["spend"].is_monotonic_decreasing
    assert math.isclose(table["spend_share"].sum(), 1.0)
    assert len(table) == 5


def test_daily_table_has_one_row_per_day_in_order(sample_df):
    daily = by_day(sample_df)
    assert len(daily) == 60
    assert daily["date"].is_monotonic_increasing


def test_clean_number_turns_nan_into_none():
    assert clean_number(float("nan")) is None
    assert clean_number(2.5) == 2.5
    assert clean_number(None) is None
