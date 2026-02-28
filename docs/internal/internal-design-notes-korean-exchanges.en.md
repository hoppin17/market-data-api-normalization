Internal Design Notes: Public API Standardization for Korean Exchanges

> This document contains detailed implementation notes and validation records created during the normalization design process.

**Objective**: Unify **Public APIs (pair list and candles)** across Upbit, Bithumb, Coinone, Korbit, and GOPAX into one **normalized schema**, so every exchange can be consumed using the same symbol format and candle fields.

---

## 1. What We Did and Why

| Step | Description |
|------|------|
| **Define normalized schema** | Symbol format `{BASE}-{QUOTE}` (e.g., BTC-KRW), candle fields `timestamp`(ms), open, high, low, close, volume, trade_value, and UTC-ms timestamp policy. |
| **Create guide documentation** | Organized per-exchange **pair-list API, candle API, symbol conversion rules, base URL, and rate limits** using tables and blocks. |

Because exchanges differ in URL, params, and response structure, the guide includes both **conversion rules for normalized usage** and **interval-specific endpoints, candle shape mapping, pagination, and 429 handling**.

---

## 2. Completion Status

### 2.1 Guide document

- **§1 User decisions**: finalized normalized symbol, trade_value, timestamp policy, and supported interval range.
- **§2 Exchange symbol -> normalized conversion**: completed for all 5 exchanges (API examples + conversion rules).
- **§4 Base URL and symbol format comparison**: completed for all 5 exchanges.
- **§5 Pair-list API**: completed method/path, params, response path, symbol extraction, filters (KRW, etc.), and success criteria for all exchanges.
- **§6.1 Supported interval summary**: completed supported intervals (1m to 1d, etc.) and notes for all exchanges.
- **§6.2 Common candle items**: completed method/path, symbol location, time params, pagination, limits/ranges, response path, candle structure, normalized mapping, timestamp/trade-value/sort/429 handling for all exchanges.
- **§6.3 Per-interval details**: detailed candle blocks added for Upbit, Bithumb, Coinone, Korbit, and GOPAX.
- **§7 Exceptions and limits**: completed rate limits, 429 behavior, and remaining-quota headers for all exchanges. **No remaining placeholders.**

### 2.2 Validation script

- **Scope**: all 5 exchanges. Title: "Korean 5-Exchange API Validation".
- **Checks** (12 total):
  - Upbit: market list, 1m candle, daily candle
  - Bithumb: market list, 1m candle, daily candle
  - Coinone: market list (KRW), candle (1m, KRW/BTC)
  - Korbit: currency pair list (`currencyPairs`), candle (1m, `btc_krw`)
  - GOPAX: trading pair list (`trading-pairs`), candle (1m, `BTC-KRW`, `start/end/interval=1`)

---

## 3. Exchange Summary (Guide + Validation Basis)

| Exchange | Pair list | Candles | Rate limit | Validation |
|--------|-----------|------|------------|------|
| **Upbit** | GET /v1/market/all, `market`(QUOTE-BASE) | minute/day candles, `to`/`count`, `candle_acc_trade_price` | 10 req/s (IP) | market + minute + daily passed |
| **Bithumb** | GET /v1/market/all, same format | `to` (KST), `candle_acc_trade_price` | 150 req/s (IP) | market + minute + daily passed |
| **Coinone** | GET /public/v2/markets/KRW, `markets[]`, `target_currency`, `quote_currency` | GET /public/v2/chart/KRW/BTC, `interval`/`size`, `chart[]`, `quote_volume` | 1200 req/min (IP), `error_code 4`, `Public-Ratelimit-Remaining` | market + candle(1m) passed |
| **Korbit** | GET /v2/currencyPairs, `data[]`, `symbol(btc_krw)` | GET /v2/candles, `symbol`/`interval`/`start`/`end`/`limit`, `data[]` | 50 req/s (IP), `Ratelimit` header | market + candle(1m) passed |
| **GOPAX** | GET /trading-pairs, `name`(BASE-QUOTE) | GET /trading-pairs/BTC-KRW/candles, `start`/`end`/`interval`/`limit`, array of arrays `[ts,low,high,open,close,vol]` | 20 req/s (IP), `x-gopax-ip-addr-*` headers | market + candle(1m) passed |
