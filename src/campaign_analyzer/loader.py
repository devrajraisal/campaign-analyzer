"""Read a campaign CSV, find the columns we need, and clean the values."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import IO

import pandas as pd

REQUIRED = ("date", "campaign", "impressions", "clicks", "spend")
OPTIONAL = ("ad_set", "reach", "conversions", "revenue")
NUMERIC = ("impressions", "clicks", "spend", "reach", "conversions", "revenue")

# Header names are matched case-insensitively. These are common names used by ad platform
# exports. Any other header can be mapped by hand with the --map option.
ALIASES: dict[str, tuple[str, ...]] = {
    "date": ("date", "day", "reporting starts"),
    "campaign": ("campaign", "campaign name", "campaign_name"),
    "ad_set": ("ad_set", "ad set", "ad set name", "adset", "adset_name"),
    "impressions": ("impressions",),
    "reach": ("reach",),
    "clicks": ("clicks", "link clicks", "link_clicks", "clicks (all)"),
    "spend": ("spend", "amount spent", "amount spent (usd)", "cost"),
    "conversions": ("conversions", "results", "purchases", "leads"),
    "revenue": ("revenue", "purchase conversion value", "conversion value"),
}


class DataError(ValueError):
    """The file cannot be analyzed. The message explains what to fix."""


@dataclass
class LoadResult:
    data: pd.DataFrame
    warnings: list[str] = field(default_factory=list)


def _normalize(name: object) -> str:
    return re.sub(r"\s+", " ", str(name).strip().lower())


def resolve_columns(headers: list[str], column_map: dict[str, str] | None = None) -> dict[str, str]:
    """Return {canonical name: header in the file}."""
    lookup = {_normalize(h): h for h in headers}
    overrides = column_map or {}
    unknown = [name for name in overrides if name not in REQUIRED + OPTIONAL]
    if unknown:
        raise DataError(f"Unknown column name in the mapping: {', '.join(unknown)}")

    mapping: dict[str, str] = {}
    for canonical in REQUIRED + OPTIONAL:
        if canonical in overrides:
            header = overrides[canonical]
            if _normalize(header) not in lookup:
                raise DataError(f"Column '{header}' (mapped to {canonical}) is not in the file.")
            mapping[canonical] = lookup[_normalize(header)]
            continue
        for alias in ALIASES[canonical]:
            if alias in lookup:
                mapping[canonical] = lookup[alias]
                break

    missing = [name for name in REQUIRED if name not in mapping]
    if missing:
        raise DataError(
            f"Missing required columns: {', '.join(missing)}. "
            f"Columns found: {', '.join(headers)}. "
            "Use --map name=Header to point to the right column."
        )
    return mapping


def _to_number(series: pd.Series) -> pd.Series:
    # Removes currency symbols and thousands separators, so "$1,234.50" becomes 1234.50.
    cleaned = series.astype("string").str.replace(r"[^0-9.\-]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")


def load_campaigns(source: str | IO[str], column_map: dict[str, str] | None = None) -> LoadResult:
    try:
        raw = pd.read_csv(source, dtype=str, keep_default_na=False)
    except FileNotFoundError as error:
        raise DataError(f"File not found: {source}") from error
    except pd.errors.EmptyDataError as error:
        raise DataError("The file is empty.") from error
    if raw.empty:
        raise DataError("The file has a header but no rows.")

    mapping = resolve_columns(list(raw.columns), column_map)
    df = pd.DataFrame({name: raw[header] for name, header in mapping.items()})
    for name in OPTIONAL:
        if name not in df:
            df[name] = "" if name == "ad_set" else 0
    warnings: list[str] = []

    df["date"] = pd.to_datetime(df["date"], errors="coerce", format="mixed")
    invalid_dates = int(df["date"].isna().sum())
    if invalid_dates:
        warnings.append(f"Skipped {invalid_dates} row(s) with a missing or invalid date.")
        df = df[df["date"].notna()]

    df["campaign"] = df["campaign"].str.strip()
    blank = int((df["campaign"] == "").sum())
    if blank:
        warnings.append(f"Skipped {blank} row(s) with no campaign name.")
        df = df[df["campaign"] != ""]
    df["ad_set"] = df["ad_set"].astype(str).str.strip().replace("", "(none)")

    for name in NUMERIC:
        df[name] = _to_number(df[name])
    unreadable = int(df[list(REQUIRED[2:])].isna().any(axis=1).sum())
    if unreadable:
        warnings.append(f"Skipped {unreadable} row(s) with unreadable numbers.")
        df = df.dropna(subset=list(REQUIRED[2:]))
    df[list(OPTIONAL[1:])] = df[list(OPTIONAL[1:])].fillna(0)

    if (df[list(NUMERIC)] < 0).any().any():
        raise DataError("The file contains negative numbers. Check the export settings.")
    if df.empty:
        raise DataError("No usable rows were found after cleaning the data.")

    too_many_clicks = int((df["clicks"] > df["impressions"]).sum())
    if too_many_clicks:
        warnings.append(f"{too_many_clicks} row(s) have more clicks than impressions.")

    df["date"] = df["date"].dt.normalize()
    return LoadResult(df.reset_index(drop=True), warnings)
