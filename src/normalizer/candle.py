from __future__ import annotations

import calendar
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]+-[A-Z0-9]+$")
INTERVAL_PATTERN = re.compile(r"^([1-9][0-9]*)(mon|m|h|d|w)$")


def normalize_symbol(raw_symbol: str) -> str:
    symbol = raw_symbol.strip().upper().replace("/", "-").replace("_", "-")
    parts = symbol.split("-")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Invalid symbol: {raw_symbol}")
    normalized = f"{parts[0]}-{parts[1]}"
    if not SYMBOL_PATTERN.fullmatch(normalized):
        raise ValueError(f"Invalid symbol: {raw_symbol}")
    return normalized


def to_utc_ms(value: Any, unit: str = "ms") -> int:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            value = int(stripped)
        else:
            dt = datetime.fromisoformat(stripped.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            value = int(dt.timestamp() * 1000)
            unit = "ms"

    if isinstance(value, float):
        value = int(value)

    if not isinstance(value, int):
        raise ValueError(f"Unsupported timestamp type: {type(value)}")

    if unit == "s":
        value = value * 1000
    elif unit != "ms":
        raise ValueError(f"Unsupported timestamp unit: {unit}")

    if value < 0:
        raise ValueError("Timestamp must be >= 0")
    return value


def interval_to_ms(interval: str) -> int:
    match = INTERVAL_PATTERN.fullmatch(interval)
    if not match:
        raise ValueError(f"Invalid interval: {interval}")
    amount = int(match.group(1))
    unit = match.group(2)
    if unit == "mon":
        raise ValueError("Use month-aware close-time derivation for 'mon' intervals")
    unit_ms = {"m": 60_000, "h": 3_600_000, "d": 86_400_000, "w": 604_800_000}
    return amount * unit_ms[unit]


def _add_calendar_months_ms(open_time_ms: int, months: int) -> int:
    dt = datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc)
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    target = dt.replace(year=year, month=month, day=day)
    return int(target.timestamp() * 1000)


def _first(data: Mapping[str, Any], keys: tuple[str, ...], required: bool = True) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    if required:
        raise KeyError(f"Missing required keys: {keys}")
    return None


def normalize_candle(
    exchange: str,
    symbol: str,
    interval: str,
    raw: Mapping[str, Any],
    source_time_unit: str = "ms",
    ingestion_time_ms: int | None = None,
) -> dict[str, Any]:
    normalized_symbol = normalize_symbol(symbol)
    interval_match = INTERVAL_PATTERN.fullmatch(interval)
    if not interval_match:
        raise ValueError(f"Invalid interval: {interval}")
    interval_amount = int(interval_match.group(1))
    interval_unit = interval_match.group(2)

    open_time_ms = to_utc_ms(
        _first(raw, ("open_time", "openTime", "timestamp", "t")), source_time_unit
    )
    close_time_raw = _first(raw, ("close_time", "closeTime", "T"), required=False)
    if close_time_raw is None:
        if interval_unit == "mon":
            close_time_ms = _add_calendar_months_ms(open_time_ms, interval_amount) - 1
        else:
            close_time_ms = open_time_ms + interval_to_ms(interval) - 1
    else:
        close_time_ms = to_utc_ms(close_time_raw, source_time_unit)

    candle = {
        "exchange": exchange.strip().lower(),
        "symbol": normalized_symbol,
        "interval": interval,
        "open_time_ms": open_time_ms,
        "close_time_ms": close_time_ms,
        "open": float(_first(raw, ("open", "o"))),
        "high": float(_first(raw, ("high", "h"))),
        "low": float(_first(raw, ("low", "l"))),
        "close": float(_first(raw, ("close", "c"))),
        "volume_base": float(_first(raw, ("volume_base", "volume", "v"))),
        "volume_quote": None,
        "trade_count": None,
        "ingestion_time_ms": ingestion_time_ms
        if ingestion_time_ms is not None
        else int(datetime.now(tz=timezone.utc).timestamp() * 1000),
    }

    qv = _first(raw, ("volume_quote", "quote_volume", "qv", "q"), required=False)
    if qv is not None:
        candle["volume_quote"] = float(qv)
    tc = _first(raw, ("trade_count", "trades", "n"), required=False)
    if tc is not None:
        candle["trade_count"] = int(tc)

    if candle["low"] > candle["high"]:
        raise ValueError("low cannot be greater than high")
    if not (candle["low"] <= candle["open"] <= candle["high"]):
        raise ValueError("open must be within [low, high]")
    if not (candle["low"] <= candle["close"] <= candle["high"]):
        raise ValueError("close must be within [low, high]")
    if candle["open_time_ms"] >= candle["close_time_ms"]:
        raise ValueError("open_time_ms must be less than close_time_ms")
    if candle["volume_base"] < 0:
        raise ValueError("volume_base must be >= 0")
    if candle["volume_quote"] is not None and candle["volume_quote"] < 0:
        raise ValueError("volume_quote must be >= 0")
    if candle["trade_count"] is not None and candle["trade_count"] < 0:
        raise ValueError("trade_count must be >= 0")

    return candle


def validate_candle_against_schema(
    candle: Mapping[str, Any], schema_path: str | Path
) -> None:
    from jsonschema import validate

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    validate(instance=dict(candle), schema=schema)
