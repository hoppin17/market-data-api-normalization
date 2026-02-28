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

## Core Rules
- Symbol format: `{BASE}-{QUOTE}`
- Timestamp: UTC milliseconds
- Canonical candle time: candle open time
- `trade_value`: exchange-provided value if available, else `close * volume`

## Docs Structure
- `docs/en/`: English public documentation
- `docs/ko/`: Korean public documentation
- `docs/internal/`: internal design notes and mixed-source records

## Key Documents
- English public guide: `docs/en/market-data-api-normalization-korean-exchanges.md`
- Korean public guide: `docs/ko/market-data-api-normalization-korean-exchanges.md`
- Internal notes (EN): `docs/internal/internal-design-notes-korean-exchanges.en.md`
- Internal notes (KO): `docs/internal/internal-design-notes-korean-exchanges.ko.md`

## Next Direction
Keep this framework extensible for future global exchange integration while preserving consistent normalization policy.
