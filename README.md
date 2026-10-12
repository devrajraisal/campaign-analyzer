# Campaign Analyzer

A command line tool that turns an ad campaign CSV export into KPIs, plain language insights, and a single HTML report with charts.

I built it from my digital marketing work. Looking at a spreadsheet of impressions, clicks, and spend rarely answers the real questions: which campaign wastes money, which one is getting tired, and is the account getting better or worse this week. This tool answers those with a few simple, readable rules.

> The sample data in this project is **synthetic**. It is produced by a seeded random generator and built to contain a few realistic problems. It is not real campaign data.

## Features

- Reads a CSV export and recognises common column names, or lets you map your own columns
- Cleans the data: currency symbols, thousands separators, bad dates, and negative numbers are handled, and every skipped row is reported
- Calculates CTR, CPC, CPM, conversion rate, cost per result (CPA), and ROAS, by account, by campaign, and by day
- Finds problems with transparent rules (listed below)
- Writes one self contained HTML report with summary cards, insights, charts, and a campaign table, plus an optional JSON summary
- Has a built in generator for demo data

## Quick start

You need Python 3.10 or newer.

```bash
git clone https://github.com/devrajraisal/campaign-analyzer.git
cd campaign-analyzer
python -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"

campaign-analyzer sample -o sample_campaigns.csv
campaign-analyzer analyze sample_campaigns.csv -o report.html --json summary.json
```

Open `report.html` in a browser.

## Using your own data

```bash
campaign-analyzer analyze my_export.csv --currency PKR --title "March campaigns"
```

Required columns: `date`, `campaign`, `impressions`, `clicks`, `spend`.
Optional columns: `ad_set`, `reach`, `conversions`, `revenue`.

Header names are matched without caring about case. Besides the names above, the tool also recognises common export headings such as `Campaign name`, `Link clicks`, `Amount spent (USD)`, `Results`, and `Purchase conversion value`. These names are based on common ad platform exports and have not been checked against every real export, so if a header is not recognised, map it yourself:

```bash
campaign-analyzer analyze export.csv --map spend="Amount spent (PKR)" --map conversions="Leads"
```

Dates are easiest in `YYYY-MM-DD` format. Rows that cannot be read are skipped, and the report lists how many.

## Metrics

| Metric | Formula |
| --- | --- |
| CTR | clicks / impressions |
| CPC | spend / clicks |
| CPM | spend / impressions x 1000 |
| Conversion rate | conversions / clicks |
| Cost per result (CPA) | spend / conversions |
| ROAS | revenue / spend |

When a denominator is zero, the result is shown as `n/a` instead of a misleading number. If the file has no revenue at all, ROAS is not reported.

## Insights

Each insight comes from one simple rule, so it is easy to explain and to change.

| Insight | Rule | Default |
| --- | --- | --- |
| Best and weakest return | Compares campaigns that hold a meaningful share of spend, by ROAS, or by cost per result when there is no revenue | 5% of spend |
| No conversions | A campaign with a meaningful share of spend and zero conversions, in a file that tracks conversions | 5% of spend |
| Week on week trend | Compares the last 7 days with the 7 days before, using cost per result, or CTR without conversions. Needs at least 14 days | 15% change |
| High frequency | Impressions divided by reach over the last 7 days, per campaign | above 3 |

The insights are prompts for a closer look. They do not test for statistical significance, so a small campaign with few clicks can swing a lot by chance.

### Example

On the synthetic sample (60 days, seed 42), the tool reports:

- Account cost per result is up 42% week on week
- No conversions: Broad - Video Views
- High ad frequency: Retargeting - Cart Abandoners
- Best return: Retargeting - Cart Abandoners (ROAS of about 7.7x)

These match the problems built into the sample data, which is what the tests check.

## Project structure

```
src/campaign_analyzer/
  loader.py       Reads and cleans the CSV, and finds the columns
  metrics.py      Rates and summaries
  insights.py     The insight rules
  charts.py       Matplotlib charts, returned as base64 images
  report.py       Builds the HTML report
  sample_data.py  Synthetic data generator
  cli.py          Command line interface
tests/            pytest suite
```

## Design decisions

- **Pure functions on DataFrames.** Loading, metrics, insights, and reporting are separate steps that pass data forward, so each step is easy to test alone.
- **Clear errors instead of tracebacks.** Bad input produces a message that says what is wrong and how to fix it, with exit code 2.
- **Safe reports.** Everything that comes from the file is escaped before it goes into the HTML, so a campaign named `<script>` cannot run code. A test covers this.
- **Honest numbers.** Zero denominators become `n/a`, JSON never contains `NaN`, and chart axes start at zero.
- **Reach is not added up across days.** Unique reach is not additive, so frequency is only estimated per campaign over a recent window.

## Development

```bash
ruff check .
pytest
```

The suite has 42 tests. They were run with warnings treated as errors against pandas 3.0 and pandas 2.3. GitHub Actions runs the lint and the tests on Python 3.10, 3.12, and 3.13.

## Limits

- One currency per file. The currency label is only text, and nothing is converted.
- The rules are simple and the thresholds are defaults, not industry standards.
- The reports were checked by reading the output and the charts, not by opening them in every browser.

## License

MIT. See the `LICENSE` file.
