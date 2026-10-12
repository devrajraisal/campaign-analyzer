from campaign_analyzer.insights import generate_insights
from campaign_analyzer.loader import load_campaigns
from campaign_analyzer.metrics import by_campaign, by_day, summarize
from campaign_analyzer.report import build_report
from conftest import csv_text


def render(df, warnings=(), title="Test report"):
    return build_report(summarize(df), by_campaign(df), by_day(df), generate_insights(df),
                        list(warnings), title=title)


def test_report_has_all_sections_and_three_charts(sample_df):
    html = render(sample_df)
    for heading in ("Insights", "Trends", "Campaigns"):
        assert f"<h2>{heading}</h2>" in html
    assert html.count("data:image/png;base64,") == 3
    assert "ROAS" in html and "Cost per result" in html


def test_report_is_self_contained(sample_df):
    html = render(sample_df)
    assert "http://" not in html and "https://" not in html
    assert "<script" not in html


def test_text_from_the_file_is_escaped():
    rows = ['2026-10-01,"<script>alert(1)</script>",1000,20,10']
    df = load_campaigns(csv_text(rows)).data
    html = render(df, warnings=["<b>bad</b>"], title="<i>x</i>")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<b>bad</b>" not in html and "<i>x</i>" not in html


def test_conversion_columns_are_hidden_when_there_is_no_conversion_data():
    df = load_campaigns(csv_text(["2026-10-01,A,1000,20,10"])).data
    html = render(df)
    assert "Cost/result" not in html and "ROAS" not in html


def test_data_notes_appear_only_when_there_are_warnings(sample_df):
    assert "Data notes" not in render(sample_df)
    assert "Data notes" in render(sample_df, warnings=["Skipped 2 rows"])
