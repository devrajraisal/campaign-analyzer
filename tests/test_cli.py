import json

from campaign_analyzer.cli import main


def make_sample(tmp_path, days=30):
    path = tmp_path / "sample.csv"
    assert main(["sample", "-o", str(path), "--days", str(days)]) == 0
    return path


def test_sample_then_analyze_writes_a_report_and_json(tmp_path, capsys):
    csv = make_sample(tmp_path, days=40)
    report, summary = tmp_path / "out.html", tmp_path / "out.json"
    code = main(["analyze", str(csv), "-o", str(report), "--json", str(summary),
                 "--currency", "PKR", "--title", "Demo"])
    assert code == 0
    html = report.read_text(encoding="utf-8")
    assert "<title>Demo</title>" in html and "PKR" in html
    payload = json.loads(summary.read_text(encoding="utf-8"))
    assert payload["summary"]["campaigns"] == 5
    assert payload["summary"]["spend"] > 0
    assert any(item["kind"] == "waste" for item in payload["insights"])
    assert "Report written" in capsys.readouterr().out


def test_json_output_has_no_nan_values(tmp_path):
    csv = tmp_path / "plain.csv"
    csv.write_text("date,campaign,impressions,clicks,spend\n2026-10-01,A,0,0,5\n")
    summary = tmp_path / "s.json"
    assert main(["analyze", str(csv), "-o", str(tmp_path / "r.html"), "--json", str(summary)]) == 0
    text = summary.read_text()
    assert "NaN" not in text and json.loads(text)["summary"]["ctr"] is None


def test_missing_file_gives_a_friendly_error_and_exit_code_2(tmp_path, capsys):
    code = main(["analyze", str(tmp_path / "nope.csv")])
    assert code == 2
    assert "Error: File not found" in capsys.readouterr().err


def test_bad_columns_give_exit_code_2(tmp_path, capsys):
    csv = tmp_path / "bad.csv"
    csv.write_text("a,b\n1,2\n")
    assert main(["analyze", str(csv)]) == 2
    assert "Missing required columns" in capsys.readouterr().err


def test_map_option_selects_a_column_and_bad_values_are_rejected(tmp_path, capsys):
    csv = tmp_path / "pk.csv"
    csv.write_text("date,campaign,impressions,clicks,Kharcha\n2026-10-01,A,1000,20,300\n")
    out = tmp_path / "r.html"
    assert main(["analyze", str(csv), "-o", str(out), "--map", "spend=Kharcha"]) == 0
    assert "300.00" in out.read_text(encoding="utf-8")
    assert main(["analyze", str(csv), "--map", "oops"]) == 2
    assert "Use name=Header" in capsys.readouterr().err


def test_warnings_are_printed_to_stderr(tmp_path, capsys):
    csv = tmp_path / "w.csv"
    csv.write_text("date,campaign,impressions,clicks,spend\n2026-10-01,A,10,50,1\n")
    assert main(["analyze", str(csv), "-o", str(tmp_path / "r.html")]) == 0
    assert "more clicks than impressions" in capsys.readouterr().err


def test_sample_rejects_invalid_days(tmp_path, capsys):
    assert main(["sample", "-o", str(tmp_path / "x.csv"), "--days", "0"]) == 2
    assert "days must be at least 1" in capsys.readouterr().err
