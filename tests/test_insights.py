import pandas as pd

from campaign_analyzer.insights import generate_insights
from campaign_analyzer.loader import load_campaigns
from conftest import csv_text


def titles(insights):
    return [item.title for item in insights]


def test_sample_data_triggers_each_designed_finding(sample_df):
    insights = generate_insights(sample_df)
    found = titles(insights)
    assert "Best return: Retargeting - Cart Abandoners" in found
    assert "No conversions: Broad - Video Views" in found
    assert "High ad frequency: Retargeting - Cart Abandoners" in found
    trend = [item for item in insights if item.kind == "trend"]
    assert trend and trend[0].severity == "warning"
    assert "cost per result is up" in trend[0].title


def test_warnings_come_before_good_news(sample_df):
    order = [item.severity for item in generate_insights(sample_df)]
    assert order == sorted(order, key=["warning", "good", "info"].index)


def test_no_conversion_insight_when_the_file_has_no_conversions():
    rows = [f"2026-10-{day:02d},{name},1000,20,{spend}"
            for day in range(1, 4) for name, spend in (("A", 10), ("B", 90))]
    insights = generate_insights(load_campaigns(csv_text(rows)).data)
    assert not any(item.kind == "waste" for item in insights)


def test_a_healthy_account_reports_no_issues():
    rows = [f"2026-10-{day:02d},A,1000,20,10" for day in range(1, 4)]
    insights = generate_insights(load_campaigns(csv_text(rows)).data)
    assert titles(insights) == ["No issues found"]


def test_trend_needs_two_weeks_of_data(sample_df):
    short = sample_df[sample_df["date"] < sample_df["date"].min() + pd.Timedelta(10, unit="D")]
    assert not any(item.kind == "trend" for item in generate_insights(short))


def test_thresholds_can_be_changed(sample_df):
    strict = generate_insights(sample_df, frequency_limit=10.0)
    assert not any(item.kind == "frequency" for item in strict)
    loose = generate_insights(sample_df, frequency_limit=1.0)
    assert sum(item.kind == "frequency" for item in loose) >= 2


def test_currency_label_is_used_in_the_text(sample_df):
    waste = [i for i in generate_insights(sample_df, currency="PKR") if i.kind == "waste"]
    assert waste and "PKR" in waste[0].detail


def test_a_zero_baseline_week_is_skipped_instead_of_crashing():
    # Regression test: the earlier week has no clicks, so the click-through rate baseline is 0.
    rows = [f"2026-10-{day:02d},A,1000,{0 if day <= 7 else 20},10" for day in range(1, 15)]
    insights = generate_insights(load_campaigns(csv_text(rows)).data)
    assert not any(item.kind == "trend" for item in insights)
