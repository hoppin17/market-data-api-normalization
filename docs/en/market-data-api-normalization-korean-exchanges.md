Market Data API Normalization for Korean Exchanges

## Why This Project

Korean exchanges expose heterogeneous public APIs with inconsistent:
- Symbol formats (BASE-QUOTE vs QUOTE-BASE)
- Timestamp semantics (UTC vs KST, start vs end time)
- Quote-volume / trade-amount field definitions
- Rate limit policies

Without normalization, cross-exchange analytics requires repetitive, exchange-specific preprocessing.

This project defines a unified schema and transformation policy to make market data immediately analytics-ready.

This document covers only **pair list** and **candle chart** endpoints from the **Public APIs** of Upbit, Bithumb, Coinone, Korbit, and GOPAX.
Different request params and response formats are normalized into the schema below.

---

## 1. User Decisions (Final)

- **Normalized symbol format**: `{BASE}-{QUOTE}` (traded asset first, quote currency second). Example: `BTC-KRW`. Case-insensitive.
- **Normalized candle fields**: `open_time_ms`, `close_time_ms`, `open`, `high`, `low`, `close`, `volume_base`, `ingestion_time_ms` (required), with `volume_quote`, `trade_count` as optional.
- **time policy**: UTC, unit **ms**, canonical basis is candle open time.
- **close time policy**: if source close time is missing, derive with `open_time_ms + interval_ms - 1`; for `mon`, derive by calendar-month rollover in UTC and subtract 1ms.
- **Supported candle intervals**: in the 1m to 1d range, fill in supported intervals and per-interval request method (URL/params differences) by exchange.

---

## 2. Exchange Symbol -> Normalized Format Rules

Normalized format is `{BASE}-{QUOTE}` (for example, `BTC-KRW`).
Rules below describe how each exchange symbol is transformed into this format.

| Exchange | API symbol example | Conversion rule to normalized format |
|--------|----------------|------------------------|
| Upbit | `"KRW-BTC"`, `"KRW-ETH"` (`market` field, **QUOTE-BASE**) | API is QUOTE-BASE. Split by `-`, swap order to BASE-QUOTE. Example: `KRW-BTC` -> `BTC-KRW`. Normalize case if needed. |
| Bithumb | `"KRW-BTC"`, `"KRW-ETH"` (`market` field, **QUOTE-BASE**) | Same as Upbit. QUOTE-BASE -> BASE-QUOTE by swapping parts. |
| Coinone | `markets` array with `quote_currency` and `target_currency` | Compose as `{target_currency}-{quote_currency}`. Example: `BTC`+`KRW` -> `BTC-KRW`. |
| Korbit | `data[].symbol` like `"btc_krw"` (**BASE_QUOTE**, underscore) | Replace `_` with `-`, uppercase if needed. Example: `btc_krw` -> `BTC-KRW`. Optional tradable filter: `status === "launched"`. |
| GOPAX | array with `name` like `"ETH-KRW"` (**BASE-QUOTE**) | Already normalized. Use `name` directly or compose from `baseAsset` + `-` + `quoteAsset`. |

---

## 3. Normalized Schema

Unless explicitly documented otherwise, timestamps are assumed to be UTC.

### 3.1 Pair (Market) List

- **Format**: `list[str]`
- **Each element**: normalized symbol format `{BASE}-{QUOTE}`. Case-insensitive.

### 3.2 Single Candle

- **Required fields**: `exchange`, `symbol`, `interval`, `open_time_ms`, `close_time_ms`, `open`, `high`, `low`, `close`, `volume_base`, `ingestion_time_ms`
- **Optional fields**: `volume_quote`, `trade_count`
- **Mapping policy**: exchange trade amount fields (for example, `candle_acc_trade_price`, `quote_volume`) are mapped to `volume_quote` when present.
- **Types**: time fields are integer (ms), OHLC and volume are float, `trade_count` is integer or null. Time is UTC.

---

## 4. Base URL and Symbol Format Comparison

| Exchange | Base URL | Market list response format | Candle request symbol format |
|--------|----------|---------------------|-------------------------|
| Upbit | `https://api.upbit.com/v1` | Root array. Items include `market`, `korean_name`, `english_name` | API request uses Upbit symbol (`KRW-BTC`, QUOTE-BASE). Internally store normalized `BTC-KRW` and reverse-convert for requests. |
| Bithumb | `https://api.bithumb.com/v1` | Root array. Items include `market`, `korean_name`, `english_name` | Same as Upbit: reverse-convert normalized BASE-QUOTE to QUOTE-BASE for API calls. |
| Coinone | `https://api.coinone.co.kr` | Root object with `markets` array | Candle path uses `quote_currency` and `target_currency`: `BTC-KRW` -> `/public/v2/chart/KRW/BTC`. |
| Korbit | `https://api.korbit.co.kr` | Root object with `data` array | Candle query uses lowercase `symbol={base}_{quote}`: `BTC-KRW` -> `btc_krw`. |
| GOPAX | `https://api.gopax.co.kr` | Root array with `name`, `baseAsset`, `quoteAsset`, etc. | Normalized symbol matches API path `TradingPair` directly. |

---

## 5. Pair List API by Exchange

| Item | Upbit | Bithumb | Coinone | Korbit | GOPAX |
|------|--------|------|--------|------|--------|
| Method + path | GET `/v1/market/all` | GET `/v1/market/all` | GET `/public/v2/markets/{quote_currency}` | GET `/v2/currencyPairs` | GET `/trading-pairs` |
| Query params | `is_details` (optional) | `isDetails` (optional) | none | none | none |
| Response list path | root array | root array | `markets` array in root object | `data` array in root object | root array |
| Symbol extraction | `market` field | `market` field | `target_currency` + `quote_currency` | `symbol` with `_` -> `-` + uppercase | `name` (or `baseAsset-quoteAsset`) |
| KRW filter | `market.startsWith("KRW-")` | `market.startsWith("KRW-")` | path param `KRW` | `symbol.endsWith("_krw")` or normalized QUOTE=KRW | `quoteAsset === "KRW"` or `name.endsWith("-KRW")` |
| Success criteria | HTTP 200 | HTTP 200 | HTTP 200 and `result=="success"`, `error_code=="0"` | HTTP 200 and `success===true` | HTTP 200 and array body |

---

## 6. Candle API by Interval (Exchange)

### 6.1 Supported intervals summary

| Exchange | Supported intervals | Notes |
|--------|--------------------------------|------|
| Upbit | Minutes: 1,3,5,10,15,30,60,240. Day: 1d. | Candle exists only when trades occurred in interval. |
| Bithumb | Minutes: 1,3,5,10,15,30,60,240. Day: 1d. | `to` defaults to KST semantics; response `timestamp` is candle end time in KST ms. |
| Coinone | 1m,3m,5m,10m,15m,30m,1h,2h,4h,6h,1d (+1w,1mon) | Single endpoint; `interval` chooses granularity. UTC ms timestamps. |
| Korbit | 1,5,15,30,60,240,1D,1W | Single endpoint `/v2/candles`; ascending order (oldest -> newest). |
| GOPAX | 1,5,30,1440(1d) | `start` and `end` required. Response candle shape: `[timestamp, low, high, open, close, volume]`. |

### 6.2 Common candle fields by exchange

| Item | Upbit | Bithumb | Coinone | Korbit | GOPAX |
|------|--------|------|--------|------|--------|
| Method + path | Minute: `/v1/candles/minutes/{unit}` Day: `/v1/candles/days` | Same as Upbit | `/public/v2/chart/{quote_currency}/{target_currency}` | `/v2/candles` | `/trading-pairs/{TradingPair}/candles` |
| Symbol location | query `market=KRW-BTC` | query `market=KRW-BTC` | path `quote/target` | query `symbol=btc_krw` | path `TradingPair=BTC-KRW` |
| Time params | `to` (optional ISO), `count`(max 200) | same, `to` interpreted in KST by default | `interval` required, optional `timestamp` UTC ms, `size` up to 500 | `interval` required, optional `start/end`, required `limit` up to 200 | required `start/end/interval`, optional `limit` up to 1024 |
| Response list path | root array | root array | `chart` array | `data` array | root array of arrays |
| Candle mapping | `open/high/low/close` <- `opening_price/high_price/low_price/trade_price`; `volume_base` <- `candle_acc_trade_volume`; `volume_quote` <- `candle_acc_trade_price`; `trade_count` <- `null` | same | `open/high/low/close` <- `open/high/low/close`; `volume_base` <- `target_volume`; `volume_quote` <- `quote_volume`; `trade_count` <- `null` | `open/high/low/close` <- `open/high/low/close`; `volume_base` <- `volume`; `volume_quote` <- `null`; `trade_count` <- `null` | `open/high/low/close` <- `[3]/[2]/[1]/[4]`; `volume_base` <- `[5]`; `volume_quote` <- `null`; `trade_count` <- `null` |
| Normalized time mapping | `open_time_ms` <- parse `candle_date_time_utc`; `close_time_ms` <- `open_time_ms + interval_ms - 1` | same (`timestamp` in payload is KST candle end) | `open_time_ms` <- `timestamp`; `close_time_ms` <- `open_time_ms + interval_ms - 1` | `open_time_ms` <- `timestamp` (assume UTC if undocumented); derive `close_time_ms` | `open_time_ms` <- `[0]` (assume UTC if undocumented); derive `close_time_ms` |
| volume_quote availability | provided (`candle_acc_trade_price`) | provided (`candle_acc_trade_price`) | provided (`quote_volume`) | not provided (`null`) | not provided (`null`) |
| Sort order | newest first | newest first | newest first | oldest first | oldest first |
| 429/rate limit handling | candle group 10 req/s | public 150 req/s | 1200 req/min, check `Public-Ratelimit-Remaining` | 50 req/s, check `Ratelimit` headers | 20 req/s IP, check `x-gopax-*weight` headers |

### 6.3 Per-exchange candle details

#### Upbit

| Category | Minute candles | Day candles |
|------|--------|--------|
| URL | `GET /v1/candles/minutes/{unit}` | `GET /v1/candles/days` |
| Path param | `unit`: 1,3,5,10,15,30,60,240 | — |
| Query | `market`(required), `to`(optional), `count`(optional, max 200) | Same + optional `converting_price_unit=KRW` |
| Note | No candle is created if no trades occur in that interval. | Daily candle is based on UTC 00:00. |

#### Bithumb

| Category | Minute candles | Day candles |
|------|--------|--------|
| URL | `GET /v1/candles/minutes/{unit}` | `GET /v1/candles/days` |
| Path param | `unit`: 1,3,5,10,15,30,60,240 | — |
| Query | `market`, `to`(KST-oriented), `count` | Same + `convertingPriceUnit=KRW` |
| Note | Normalize timestamp from `candle_date_time_utc` for UTC-open-time policy. | Daily candle is UTC 00:00 based. |

#### Coinone

| Category | Content |
|------|------|
| URL | `GET /public/v2/chart/{quote_currency}/{target_currency}` |
| Query | `interval` required, optional `timestamp` (UTC ms), optional `size` (1~500, default 200) |
| Response | root object with `result`, `error_code`, `is_last`, `chart[]` |
| Note | `is_last===true` means last available page for the requested range. |

#### Korbit

| Category | Content |
|------|------|
| URL | `GET /v2/candles` |
| Query | `symbol` required, `interval` required, optional `start/end`, `limit` required (1~200) |
| Response | root object with `success`, `data[]` |
| Note | Ascending time order; trade value not provided. |

#### GOPAX

| Category | Content |
|------|------|
| URL | `GET /trading-pairs/{TradingPair}/candles` |
| Query | `start` required, `end` required, `interval` required (`1/5/30/1440`), optional `limit` up to 1024 |
| Response | array of candles: `[timestamp, low, high, open, close, volume]` |
| Note | Index order must be mapped carefully (`low/high/open/close`). |

---

## 7. Exceptions and Limits

- **Upbit**: max 10 req/s (IP), candle APIs share candle group quota.
- **Bithumb**: public APIs max 150 req/s.
- **Coinone**: V2 public APIs max 1200 req/min per IP. On over-limit: `error_code: "4"`, `error_msg: "Blocked user access"`.
- **Korbit**: public APIs max 50 req/s per IP. Rate headers: `Ratelimit`, `Ratelimit-Policy`.
- **GOPAX**: public APIs max 20 req/s per IP for endpoints used in this guide (`/trading-pairs`, candle endpoint).

---

## 8. How to Fill This Doc URL by URL

- **Input**: `exchange / feature / GET URL` (+ params, valid values, response format, sample if known).
- **Feature examples**: pair list, candle 1m, candle 1h, candle 1d.
- **Output**: fill relevant cells with params, possible values, and response schema. For pair-list endpoints, also update the symbol-to-normalized-format rule table.
