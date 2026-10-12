import io

import pytest

from campaign_analyzer.loader import DataError, load_campaigns, resolve_columns
from conftest import csv_text


def test_reads_the_minimum_columns_and_fills_the_optional_ones():
    result = load_campaigns(csv_text(["2026-10-01,Spring Sale,1000,25,12.5"]))
    row = result.data.iloc[0]
    assert (row["campaign"], row["impressions"], row["clicks"], row["spend"]) == (
        "Spring Sale", 1000, 25, 12.5)
    assert row["conversions"] == 0 and row["revenue"] == 0 and row["ad_set"] == "(none)"
    assert result.warnings == []


def test_recognizes_common_export_headers_in_any_case():
    header = "Day,Campaign name,Ad set name,IMPRESSIONS,Link clicks,Amount spent (USD),Results"
    result = load_campaigns(csv_text(["2026-10-01,A,Set 1,500,10,5,2"], header))
    row = result.data.iloc[0]
    assert (row["ad_set"], row["clicks"], row["spend"], row["conversions"]) == ("Set 1", 10, 5, 2)


def test_removes_currency_symbols_and_thousands_separators():
    result = load_campaigns(csv_text(['2026-10-01,A,"12,500",300,"$1,234.50"']))
    assert result.data.iloc[0]["impressions"] == 12500
    assert result.data.iloc[0]["spend"] == 1234.50


def test_skips_rows_with_bad_dates_names_or_numbers_and_says_so():
    rows = [
        "2026-10-01,A,100,5,1",
        "not a date,A,100,5,1",
        "2026-10-02,,100,5,1",
        "2026-10-03,A,abc,5,1",
    ]
    result = load_campaigns(csv_text(rows))
    assert len(result.data) == 1
    assert len(result.warnings) == 3


def test_missing_required_columns_lists_what_is_missing_and_what_was_found():
    with pytest.raises(DataError) as error:
        load_campaigns(csv_text(["2026-10-01,A,5"], "date,campaign,clicks"))
    message = str(error.value)
    assert "impressions" in message and "spend" in message
    assert "date, campaign, clicks" in message


def test_manual_mapping_overrides_the_header_guess():
    header = "date,campaign,impressions,clicks,Cost in PKR"
    result = load_campaigns(csv_text(["2026-10-01,A,100,5,40"], header),
                            {"spend": "cost in pkr"})
    assert result.data.iloc[0]["spend"] == 40


def test_mapping_errors_are_clear():
    with pytest.raises(DataError, match="not in the file"):
        resolve_columns(["date"], {"spend": "Nope"})
    with pytest.raises(DataError, match="Unknown column name"):
        resolve_columns(["date"], {"colour": "date"})


def test_negative_numbers_are_rejected():
    with pytest.raises(DataError, match="negative"):
        load_campaigns(csv_text(["2026-10-01,A,100,5,-3"]))


def test_empty_and_header_only_files_are_rejected():
    with pytest.raises(DataError, match="empty"):
        load_campaigns(io.StringIO(""))
    with pytest.raises(DataError, match="no rows"):
        load_campaigns(csv_text([]))


def test_a_missing_file_is_reported_without_a_traceback():
    with pytest.raises(DataError, match="File not found"):
        load_campaigns("does-not-exist.csv")


def test_warns_when_clicks_exceed_impressions():
    result = load_campaigns(csv_text(["2026-10-01,A,10,50,1"]))
    assert any("more clicks than impressions" in text for text in result.warnings)


def test_every_row_bad_means_an_error():
    with pytest.raises(DataError, match="No usable rows"):
        load_campaigns(csv_text(["not a date,A,1,1,1"]))
