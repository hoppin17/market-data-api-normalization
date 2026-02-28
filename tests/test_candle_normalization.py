from pathlib import Path
import sys

import pytest
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from normalizer.candle import (  # noqa: E402
    normalize_candle,
    normalize_symbol,
    to_utc_ms,
    validate_candle_against_schema,
)


SCHEMA_PATH = ROOT / "schemas" / "unified_candle.schema.json"


def test_normalize_symbol():
    assert normalize_symbol("btc/usdt") == "BTC-USDT"
    assert normalize_symbol("eth_usd") == "ETH-USD"
    with pytest.raises(ValueError):
        normalize_symbol("btcusdt")


def test_to_utc_ms():
    assert to_utc_ms(1_700_000_000, "s") == 1_700_000_000_000
    assert to_utc_ms("1700000000000") == 1_700_000_000_000
    assert to_utc_ms("2025-01-09T00:00:00Z") == 1_736_380_800_000


def test_normalize_candle_and_schema_validation():
    raw = {
        "openTime": 1736384400000,
        "o": "100.0",
        "h": "110.0",
        "l": "95.0",
        "c": "105.0",
        "v": "12.5",
        "q": "1300.0",
        "n": 120
    }
    candle = normalize_candle("binance", "btc/usdt", "1m", raw, source_time_unit="ms")
    assert candle["symbol"] == "BTC-USDT"
    assert candle["close_time_ms"] == 1736384459999
    validate_candle_against_schema(candle, SCHEMA_PATH)


def test_schema_rejects_invalid_symbol():
    invalid_candle = {
        "exchange": "binance",
        "symbol": "BTCUSDT",
        "interval": "1m",
        "open_time_ms": 1736384400000,
        "close_time_ms": 1736384459999,
        "open": 100.0,
        "high": 110.0,
        "low": 95.0,
        "close": 105.0,
        "volume_base": 12.5,
        "ingestion_time_ms": 1736384460200
    }
    with pytest.raises(ValidationError):
        validate_candle_against_schema(invalid_candle, SCHEMA_PATH)
