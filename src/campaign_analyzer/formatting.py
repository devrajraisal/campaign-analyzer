"""Small helpers that turn numbers into readable text."""

from __future__ import annotations

import math


def _missing(value: float | None) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def money(value: float | None, currency: str = "USD") -> str:
    return "n/a" if _missing(value) else f"{value:,.2f} {currency}"


def percent(value: float | None, digits: int = 2) -> str:
    return "n/a" if _missing(value) else f"{value * 100:.{digits}f}%"


def whole(value: float | None) -> str:
    return "n/a" if _missing(value) else f"{value:,.0f}"


def multiple(value: float | None) -> str:
    return "n/a" if _missing(value) else f"{value:.2f}x"
