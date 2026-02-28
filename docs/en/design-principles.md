# Public API Normalization Design (v0)

## 1. Symbol Standard
- Canonical format: `{BASE}-{QUOTE}`.
- Uppercase only.
- Allow raw separators `/`, `_`, `-`; normalize to `-`.
- Reject ambiguous symbols that cannot be split into exactly two assets.

## 2. Time Standard
- All timestamps use UTC epoch milliseconds.
- Candle time reference:
  - `open_time_ms`: interval start (inclusive)
  - `close_time_ms`: interval end (inclusive)
- When source provides only open timestamp, derive close time by interval.

## 3. Candle Schema Policy
- Required: exchange, symbol, interval, open_time_ms, close_time_ms, open, high, low, close, volume_base, ingestion_time_ms
- Optional: volume_quote, trade_count
- Numeric values must be finite and non-negative where applicable.

## 4. Rate Limit Handling
- Keep per-exchange config as data, not hardcoded sleep scattered in logic.
- Distinguish:
  - Request rate (requests/sec or requests/min)
  - Weight-based limits
  - Burst allowance
- Call principles:
  - Prefer deterministic polling schedules
  - Add retry with bounded exponential backoff
  - Emit explicit throttling events/metrics

## 5. Cross-Exchange Integrity Checks
- Symbol collision checks after normalization.
- Missing candle detection by expected interval continuity.
- Sanity checks:
  - `low <= open/high/close <= high`
  - `open_time_ms < close_time_ms`
  - Non-negative volumes
