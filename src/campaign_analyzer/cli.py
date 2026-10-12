"""Command line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .insights import generate_insights
from .loader import DataError, load_campaigns
from .metrics import by_campaign, by_day, clean_number, summarize
from .report import build_report
from .sample_data import generate_sample


def _parse_mapping(pairs: list[str]) -> dict[str, str]:
    mapping = {}
    for pair in pairs:
        name, separator, header = pair.partition("=")
        if not separator or not name or not header:
            raise DataError(f"Invalid --map value '{pair}'. Use name=Header.")
        mapping[name.strip()] = header.strip()
    return mapping


def _analyze(args: argparse.Namespace) -> int:
    result = load_campaigns(args.csv, _parse_mapping(args.map))
    summary = summarize(result.data)
    campaigns = by_campaign(result.data)
    insights = generate_insights(result.data, currency=args.currency)

    html = build_report(summary, campaigns, by_day(result.data), insights, result.warnings,
                        currency=args.currency, title=args.title)
    Path(args.output).write_text(html, encoding="utf-8")
    print(f"Report written to {args.output}")

    if args.json:
        payload = {
            "summary": {k: clean_number(v) if isinstance(v, float) else v
                        for k, v in summary.items()},
            "insights": [item.__dict__ for item in insights],
            "warnings": result.warnings,
        }
        Path(args.json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Summary written to {args.json}")

    for text in result.warnings:
        print(f"Warning: {text}", file=sys.stderr)
    return 0


def _sample(args: argparse.Namespace) -> int:
    generate_sample(days=args.days, seed=args.seed).to_csv(args.output, index=False)
    print(f"Synthetic sample data written to {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="campaign-analyzer",
        description="Turn an ad campaign CSV export into KPIs, insights, and an HTML report.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    analyze = commands.add_parser("analyze", help="analyze a CSV file and write a report")
    analyze.add_argument("csv", help="path to the campaign CSV file")
    analyze.add_argument("-o", "--output", default="report.html", help="HTML report path")
    analyze.add_argument("--json", help="also write the summary and insights as JSON")
    analyze.add_argument("--currency", default="USD", help="currency label (default: USD)")
    analyze.add_argument("--title", default="Campaign report", help="report title")
    analyze.add_argument("--map", action="append", default=[], metavar="NAME=HEADER",
                         help="map a column, for example spend='Amount spent (PKR)'")
    analyze.set_defaults(handler=_analyze)

    sample = commands.add_parser("sample", help="write synthetic demo data")
    sample.add_argument("-o", "--output", default="sample_campaigns.csv")
    sample.add_argument("--days", type=int, default=60)
    sample.add_argument("--seed", type=int, default=42)
    sample.set_defaults(handler=_sample)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except DataError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
