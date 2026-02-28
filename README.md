# market-data-api-normalization

Documentation-driven market data API normalization framework for Korean cryptocurrency exchanges.

## What This Is
- A normalization framework and schema design project
- Analytics-ready unification of heterogeneous public market data APIs
- Documentation-first architecture with validation references

## What This Is Not
- Trading bot
- Strategy engine
- Production trading system

## Scope (Current)
- Exchanges: Upbit, Bithumb, Coinone, Korbit, GOPAX
- APIs: market (pair) listing and candles (OHLCV)

## Coverage Summary
| Category | Included | Not Included |
|---|---|---|
| Exchanges | Upbit, Bithumb, Coinone, Korbit, GOPAX | Global exchanges outside current scope |
| Public APIs | Market list, Candle OHLCV | Orderbook, Trades, Ticker depth variants not yet mapped |
| Private APIs | None | Orders, balances, deposits/withdrawals, account auth flows |
| Trading Features | None | Bot logic, strategy execution, portfolio/risk engine |
| Production Ops | Schema + docs + normalization module | Live streaming infra, SLO/SLA operations, alert pipelines |

## Core Rules
- Symbol format: `{BASE}-{QUOTE}`
- Candle time fields: `open_time_ms` and `close_time_ms` (UTC milliseconds)
- Canonical candle time basis: candle open time
- Volume fields: required `volume_base`, optional `volume_quote`
- Optional market activity field: `trade_count`

## Before/After Example
Before (exchange-style payload):
```json
{
  "market": "KRW-BTC",
  "candle_date_time_utc": "2025-01-09T00:00:00",
  "opening_price": 100000000.0,
  "high_price": 101000000.0,
  "low_price": 99000000.0,
  "trade_price": 100500000.0,
  "candle_acc_trade_volume": 12.34,
  "candle_acc_trade_price": 1240000000.0
}
```

After (normalized candle):
```json
{
  "exchange": "upbit",
  "symbol": "BTC-KRW",
  "interval": "1d",
  "open_time_ms": 1736380800000,
  "close_time_ms": 1736467199999,
  "open": 100000000.0,
  "high": 101000000.0,
  "low": 99000000.0,
  "close": 100500000.0,
  "volume_base": 12.34,
  "volume_quote": 1240000000.0,
  "trade_count": null,
  "ingestion_time_ms": 1736467205000
}
```

## Docs Structure
- `docs/en/`: English public documentation
- `docs/ko/`: Korean public documentation
- `docs/internal/`: internal design notes

## Key Documents
- English public guide: `docs/en/market-data-api-normalization-korean-exchanges.md`
- Korean public guide: `docs/ko/market-data-api-normalization-korean-exchanges.md`
- Internal notes (EN): `docs/internal/internal-design-notes-korean-exchanges.en.md`
- Internal notes (KO): `docs/internal/internal-design-notes-korean-exchanges.ko.md`

## Next Direction
Keep this framework extensible for future global exchange integration while preserving consistent normalization policy.
