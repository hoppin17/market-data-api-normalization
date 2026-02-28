한국 거래소 캔들 API 정규화 작업 정리

## 프로젝트 목적

국내 거래소의 공개 API는 다음 항목에서 서로 일관되지 않습니다:
- 심볼 형식 (BASE-QUOTE vs QUOTE-BASE)
- 타임스탬프 의미 (UTC vs KST, 시작 시각 vs 종료 시각)
- 거래대금 정의
- 호출 제한 정책

정규화가 없으면 거래소별 전처리를 반복적으로 구현해야 하므로 교차 거래소 분석 효율이 크게 떨어집니다.

이 프로젝트는 마켓 데이터를 즉시 분석 가능한 형태로 만들기 위해
통합 스키마와 변환 정책을 정의합니다.

업비트, 빗썸, 코인원, 코빗, 고팩스의 **Public API** 중 **페어 목록**과 **캔들 차트**만 다룹니다.  
거래소별로 다른 params·응답 형태를 아래 정규 스키마로 통일해 사용합니다.

---

## 1. 사용자 결정 사항 (확정)

- **정규 심볼 형식**: `{BASE}-{QUOTE}` (거래 대상이 앞, 거래 단위가 뒤). 예: `BTC-KRW`. 대소문자 구분 없음.
- **정규 캔들 필드**: `open_time_ms`, `close_time_ms`, `open`, `high`, `low`, `close`, `volume_base`, `ingestion_time_ms`(필수), `volume_quote`, `trade_count`(선택).
- **시간 정책**: UTC, 단위 **ms**, 기준은 캔들 시작 시각(candle open time).
- **종료 시각 정책**: 원본에 종료 시각이 없으면 `open_time_ms + interval_ms - 1`로 계산하고, `mon`은 UTC 기준 달력 월 증가 후 1ms를 빼서 계산.
- **지원 캔들 주기**: 1m ~ 1d 범위에서, **거래소별로** 지원하는 주기와 **주기별 요청 방식**(URL·params 차이)을 아래 표에 채움.

---

## 2. 거래소별 심볼 → 정규 형식 변환 규칙

정규 형식은 `{BASE}-{QUOTE}` (예: `BTC-KRW`). 각 거래소 API가 반환하는 심볼을 이 형식으로 변환할 때의 규칙을 채운다.

| 거래소 | API 반환 예시 | → 정규 형식 변환 규칙 |
|--------|----------------|------------------------|
| 업비트 | `"KRW-BTC"`, `"KRW-ETH"` 등 (각 요소의 `market` 필드. **QUOTE-BASE** 순) | API는 QUOTE-BASE 순이므로 `-`로 분리 후 순서 교환 → BASE-QUOTE. 예: `KRW-BTC` → `BTC-KRW`. 필요 시 대소문자 통일. |
| 빗썸 | `"KRW-BTC"`, `"KRW-ETH"` 등 (각 요소의 `market` 필드. **QUOTE-BASE** 순) | 업비트와 동일. API는 QUOTE-BASE 순이므로 `-`로 분리 후 순서 교환 → BASE-QUOTE. 예: `KRW-BTC` → `BTC-KRW`. 필요 시 대소문자 통일. |
| 코인원 | `markets` 배열. 각 요소: `quote_currency`(예: KRW), `target_currency`(예: BTC). 마켓 기준 통화가 quote, 거래 대상이 base. | 정규 형식은 BASE-QUOTE. API가 `target_currency`(BASE)와 `quote_currency`(QUOTE)를 따로 주므로 `{target_currency}-{quote_currency}`로 조합. 예: `BTC`+`KRW` → `BTC-KRW`. API는 대문자 반환, 필요 시 대소문자 통일. |
| 코빗 | `data` 배열. 각 요소: `symbol`(예: `"btc_krw"`, **BASE_QUOTE** 순, 언더스코어 구분), `status`(launched/stopped). | 정규 형식은 BASE-QUOTE이자 `-` 구분. API는 `symbol`이 `{base}_{quote}`(소문자)이므로 `_`를 `-`로 치환. 예: `btc_krw` → `BTC-KRW`. 필요 시 대문자 통일. 거래 가능만 쓰면 `status === "launched"` 필터. |
| 고팩스 | 루트가 배열. 각 요소: `name`(예: `"ETH-KRW"`, **BASE-QUOTE** 순), `baseAsset`, `quoteAsset`, `id`, `baseAssetScale`, `quoteAssetScale` 등. | API의 `name`이 이미 정규 형식(BASE-QUOTE, `-` 구분). 그대로 사용. 또는 `baseAsset`+`-`+`quoteAsset` 조합. 대소문자 통일 시 유지(API는 대문자 반환). |

---

## 3. 정규 스키마
별도 문서화된 예외가 없다면, 타임스탬프는 UTC 기준으로 가정합니다.

### 3.1 페어(마켓) 목록

- **형식**: `list[str]`
- **각 요소**: 위에서 정한 정규 심볼 형식 (`{BASE}-{QUOTE}`). 대소문자 구분 없음.

### 3.2 캔들 한 봉

- **필수 필드**: `exchange`, `symbol`, `interval`, `open_time_ms`, `close_time_ms`, `open`, `high`, `low`, `close`, `volume_base`, `ingestion_time_ms`
- **선택 필드**: `volume_quote`, `trade_count`
- **매핑 정책**: 거래소의 거래대금 계열 필드(예: `candle_acc_trade_price`, `quote_volume`)가 있으면 `volume_quote`로 매핑.
- **타입**: 시간 필드는 정수(ms), OHLC·거래량은 float, `trade_count`는 integer 또는 null. 모든 시각 UTC 기준.


---

## 4. Base URL · 심볼 형식 비교

| 거래소 | Base URL | 마켓 목록 반환 형식 | 캔들 요청 시 심볼 형식 |
|--------|----------|---------------------|-------------------------|
| 업비트 | `https://api.upbit.com/v1` | 최상위 배열. 각 요소: `market`, `korean_name`, `english_name` (선택 시 `market_event` 등) | API 요청 시에는 업비트 형식 사용: query `market`에 `"KRW-BTC"`(QUOTE-BASE). 내부 정규 심볼은 `BTC-KRW`(BASE-QUOTE)로 보관·사용하고, API 호출 시 `KRW-BTC`로 역변환해 전달. |
| 빗썸 | `https://api.bithumb.com/v1` | 최상위 배열. 각 요소: `market`, `korean_name`, `english_name` (선택 시 `market_warning`: NONE/CAUTION 등) | 업비트와 동일. API는 QUOTE-BASE(예: KRW-BTC). 내부 정규 심볼은 BASE-QUOTE(예: BTC-KRW)로 보관·사용, 캔들 등 API 호출 시 `market`에 역변환해 전달. |
| 코인원 | `https://api.coinone.co.kr` | 루트 객체. `result`, `error_code`, `server_time`, `markets`(배열). 각 요소: `quote_currency`, `target_currency`, `price_unit`, `qty_unit`, `maintenance_status`, `trade_status`, `order_types` 등. | 정규 심볼은 BASE-QUOTE(예: BTC-KRW). 캔들 요청 시 path에 `quote_currency`(QUOTE, 예: KRW), `target_currency`(BASE, 예: BTC) 사용. 정규 심볼 `BTC-KRW` → path `/public/v2/chart/KRW/BTC`. |
| 코빗 | `https://api.korbit.co.kr` | 루트 객체. `success`, `data`(배열). 각 요소: `symbol`(예: btc_krw), `status`(launched/stopped). | 정규 심볼은 BASE-QUOTE(예: BTC-KRW). 캔들 요청 시 query `symbol`에 `{base}_{quote}` 소문자(예: btc_krw). 정규 `BTC-KRW` → `btc_krw` 역변환. |
| 고팩스 | `https://api.gopax.co.kr` | 루트가 배열. 각 요소: `id`, `name`(예: ETH-KRW), `baseAsset`, `quoteAsset`, `baseAssetScale`, `quoteAssetScale`, `priceMin`, `restApiOrderAmountMin`, `makerFeePercent`, `takerFeePercent` 등. | 정규 심볼과 동일. path에 `TradingPair`(예: BTC-KRW) 사용. GET `/trading-pairs/BTC-KRW/candles`. `name` 필드 그대로 path에 넣으면 됨. |

---

## 5. 페어 목록 API (거래소별)

| 항목 | 업비트 | 빗썸 | 코인원 | 코빗 | 고팩스 |
|------|--------|------|--------|------|--------|
| Method + 경로 | GET `/v1/market/all` | GET `/v1/market/all` | GET `/public/v2/markets/{quote_currency}` (path param. 예: KRW → `/public/v2/markets/KRW`) | GET `/v2/currencyPairs` | GET `/trading-pairs` |
| 쿼리 params | `is_details` (boolean, 선택, 기본 false). true면 유의/주의종목 등 상세 정보 포함 | `isDetails` (boolean, 선택, 기본 false). true면 유의종목(`market_warning`) 등 상세 정보 포함. 주의종목은 경보제 API 참고 | 없음(path param만 사용) | 없음 | 없음 |
| 응답 목록 경로 | 루트가 배열 (array of objects) | 루트가 배열 (array of objects) | 루트 객체의 `markets` 배열 (array of objects) | 루트 객체의 `data` 배열 (array of objects) | 루트가 배열 (array of objects) |
| 심볼 추출 방법 | 각 요소의 `market` 필드 | 각 요소의 `market` 필드 | 각 요소의 `target_currency`와 `quote_currency`를 `{target_currency}-{quote_currency}`로 조합(정규 형식 BASE-QUOTE). 예: BTC-KRW | 각 요소의 `symbol` 필드. `_`를 `-`로 치환 후 대문자 통일 → BASE-QUOTE(예: btc_krw → BTC-KRW) | 각 요소의 `name` 필드(이미 BASE-QUOTE 형식, 예: ETH-KRW). 또는 `baseAsset`+`-`+`quoteAsset` |
| 필터 조건(KRW 등) | KRW 마켓만 쓰면 `market.startsWith("KRW-")` | KRW 마켓만 쓰면 `market.startsWith("KRW-")` (BTC 마켓 등도 있음) | path param `quote_currency`에 `KRW` 지정 시 KRW 마켓만 반환. 예: `/public/v2/markets/KRW` | KRW 마켓만 쓰면 `symbol.endsWith("_krw")` 또는 정규 변환 후 QUOTE가 KRW인 것만. 거래 가능만 쓰면 `status === "launched"` | KRW 마켓만 쓰면 `quoteAsset === "KRW"` 또는 `name.endsWith("-KRW")` |
| 성공 판별 | HTTP 200. 400 시 error object | HTTP 200. 400 시 error object | HTTP 200 이고 `result === "success"`, `error_code === "0"`. 에러 시 `result === "error"`, `error_code`·`error_msg` 반환(예: 108 Unknown CryptoCurrency) | HTTP 200 이고 `success === true`. 에러 시 `success === false` 및 에러 정보. | HTTP 200. 응답이 배열이면 성공. 에러 시 별도 형식일 수 있음(문서 확인). |

---

## 6. 캔들 API — 주기별 (거래소별)

1m ~ 1d 구간에서 **거래소별 지원 주기**와 **주기별 엔드포인트·params·응답**을 채운다.  
주기마다 URL·파라미터가 다를 수 있으므로, "해당 거래소가 어떻게 하는지"를 아래 블록 또는 표에 정리한다.

### 6.1 거래소별 지원 주기 요약

| 거래소 | 지원 주기(예: 1m, 5m, 1h, 1d) | 비고 |
|--------|--------------------------------|------|
| 업비트 | **분캔들**: 1, 3, 5, 10, 15, 30, 60, 240분. **일캔들**: 1d. | 분캔들·일캔들 모두 해당 구간에 체결이 있을 때만 봉 생성(체결 없으면 응답에 없음). |
| 빗썸 | **분캔들**: 1, 3, 5, 10, 15, 30, 60, 240분. **일캔들**: 1d. | `to` 파라미터는 기본 KST 기준. 응답의 `timestamp`는 캔들 종료 시각(KST 기준) ms. |
| 코인원 | **분캔들**: 1m, 3m, 5m, 10m, 15m, 30m. **시간캔들**: 1h, 2h, 4h, 6h. **일캔들**: 1d. (추가: 1w, 1mon) | 단일 엔드포인트. query `interval`로 주기 지정. `timestamp`·`size`는 UTC ms 기준. 응답 `is_last`로 마지막 캔들 여부 확인. |
| 코빗 | **분캔들**: 1, 5, 15, 30, 60(1h), 240(4h)분. **일캔들**: 1D. **주캔들**: 1W. query `interval`에 숫자 또는 1D·1W. | 단일 엔드포인트 GET `/v2/candles`. `start`·`end`(선택, timestamp ms)로 구간 지정. 미지정 시 start=상장 시점, end=현재. 응답은 과거→최신 순(오름차순). |
| 고팩스 | **분캔들**: 1, 5, 30분. **일캔들**: 1440(1일). query `interval`에 분 단위: 1, 5, 30, 1440. | GET `/trading-pairs/{TradingPair}/candles`. path에 심볼(예: BTC-KRW) 그대로. `start`·`end`(필수, ms). 응답은 배열의 배열, 봉 순서 [timestamp, low, high, open, close, volume]. |

### 6.2 캔들 공통 항목 (주기별로 거래소 열에 채움)

아래는 **한 주기(예: 1h)** 기준 예시. 주기마다 표를 복제하거나 거래소별 블록으로 채운다.

| 항목 | 업비트 | 빗썸 | 코인원 | 코빗 | 고팩스 |
|------|--------|------|--------|------|--------|
| Method + 경로 | **분캔들**: GET `/v1/candles/minutes/{unit}` (unit=1,3,5,10,15,30,60,240). **일캔들**: GET `/v1/candles/days`. | **분캔들**: GET `/v1/candles/minutes/{unit}` (unit=1,3,5,10,15,30,60,240). **일캔들**: GET `/v1/candles/days`. | GET `/public/v2/chart/{quote_currency}/{target_currency}` (주기 공통. query `interval`로 1m, 3m, 5m, 10m, 15m, 30m, 1h, 2h, 4h, 6h, 1d 등 지정) | GET `/v2/candles` (주기 공통. query `interval`로 1,5,15,30,60,240,1D,1W) | GET `/trading-pairs/{TradingPair}/candles` (path에 심볼 예: BTC-KRW. query `interval`: 1, 5, 30, 1440 분) |
| 심볼 넣는 곳(path/query) | query `market` (예: `KRW-BTC`) | query `market` (예: `KRW-BTC`) | path `quote_currency`(QUOTE, 예: KRW), `target_currency`(BASE, 예: BTC). 정규 심볼 BTC-KRW → `/chart/KRW/BTC` | query `symbol` (예: `btc_krw`. 정규 BTC-KRW → 소문자+`_` 변환) | path `TradingPair`(예: `BTC-KRW`. 정규 심볼 그대로 사용) |
| 시간 관련 params | `to` (string, 선택): 종료 시각 이전 캔들 조회. ISO 8601 (예: `2025-06-24T04:56:53Z`). 미지정 시 최근 캔들. `count` (int, 선택, 기본 1, 최대 200): 조회 개수. 일캔들 선택: `converting_price_unit=KRW` 시 원화 환산 종가 반환. | `to` (string, 선택): 마지막 캔들 시각(exclusive). ISO 8601 (`yyyy-MM-dd HH:mm:ss` 또는 `yyyy-MM-ddTHH:mm:ss`). **기본 KST**. 미지정 시 최근 캔들. `count` (int, 선택, 기본 1, 최대 200). 일캔들 선택: `convertingPriceUnit=KRW` 시 원화 환산 종가 `converted_trade_price` 반환. | `interval`(필수, enum): 1m, 3m, 5m, 10m, 15m, 30m, 1h, 2h, 4h, 6h, 1d, 1w, 1mon. `timestamp`(선택, number): 마지막 캔들 타임스탬프(UTC ms). 미지정 시 최근 캔들. `size`(선택, 1~500, 기본 200): 조회 개수. | `interval`(필수): 1, 5, 15, 30, 60, 240, 1D, 1W. `start`(선택, number): 조회 시작 시각 ms. 미지정 시 상장 시점부터. `end`(선택, number): 조회 종료 시각 ms, start보다 커야 함. 미지정 시 현재까지. `limit`(필수, 1~200): 조회 건수. | `start`(필수, number): 시작 시각 ms. `end`(필수, number): 종료 시각 ms. `interval`(필수): 1, 5, 30, 1440(분). `limit`(선택, 기본 1024, 최대 1024): 조회 건수. |
| 페이징 방식 | `to`를 과거 시각으로 넣어 재요청. 응답은 최신순이므로 마지막 봉의 시작 시각 이전을 `to`로 지정. | 동일. `to`를 과거(KST)로 넣어 재요청. 응답 최신순. | `timestamp`를 직전 응답의 가장 과거 봉의 `timestamp`로 넣어 재요청. 응답 최신순. `is_last === true`면 마지막 구간. | `start`·`end`로 구간 지정. 과거 추가 조회 시 `end`를 직전 응답의 최소(가장 과거) `timestamp`로, `start`는 더 과거로. 응답은 과거→최신 순. | `start`·`end`로 구간 지정. 추가 조회 시 구간을 나누어 요청. 응답은 start~end 구간 내 과거→최신 순. |
| 요청당 최대 / 구간 제한 | 최대 200개/요청. 문서상 구간 상한 별도 명시 없음. | 최대 200개/요청. 문서상 구간 상한 별도 명시 없음. | 최대 500개/요청(`size`). 문서상 구간 상한 별도 명시 없음. | 최대 200개/요청(`limit`). `start`·`end`로 구간 제한. | 최대 1024개/요청(`limit`, 기본 1024). `start`·`end` 필수로 구간 지정. |
| 응답 배열 경로 | 루트가 배열 (array of objects) | 루트가 배열 (array of objects) | 루트 객체의 `chart` 배열 (array of objects) | 루트 객체의 `data` 배열 (array of objects) | 루트가 배열 (array of arrays). 각 봉이 배열. |
| 한 봉 구조(필드/인덱스) | `market`, `candle_date_time_utc`, `candle_date_time_kst`, `opening_price`, `high_price`, `low_price`, `trade_price`, `timestamp`(ms), `candle_acc_trade_price`, `candle_acc_trade_volume`, `unit`(분캔들만). 일캔들 추가: `prev_closing_price`, `change_price`, `change_rate`, (선택)`converted_trade_price`. | 업비트와 동일. `market`, `candle_date_time_utc`, `candle_date_time_kst`, `opening_price`, `high_price`, `low_price`, `trade_price`, `timestamp`(ms, **캔들 종료 시각 KST**), `candle_acc_trade_price`, `candle_acc_trade_volume`, `unit`(분캔들만). 일캔들 추가: `prev_closing_price`, `change_price`, `change_rate`, (선택)`converted_trade_price`. | `timestamp`(ms), `open`, `high`, `low`, `close`, `target_volume`(종목 거래량), `quote_volume`(원화 거래 금액). 모두 UTC ms·NumberString. | `timestamp`(ms, 캔들 시작 시각), `open`, `high`, `low`, `close`, `volume`. 거래대금 미제공 → `close*volume` 사용. | 배열 6개 요소: `[0]` timestamp(ms, 구간 시작), `[1]` low, `[2]` high, `[3]` open, `[4]` close, `[5]` volume(base 자산). 거래대금 미제공. |
| 정규 필드 매핑 | `open/high/low/close` <- `opening_price/high_price/low_price/trade_price`; `volume_base` <- `candle_acc_trade_volume`; `volume_quote` <- `candle_acc_trade_price`; `trade_count` <- `null` | 동일 (`timestamp`는 KST 종료시각이므로 정규 시간에는 직접 미사용) | `open/high/low/close` <- `open/high/low/close`; `volume_base` <- `target_volume`; `volume_quote` <- `quote_volume`; `trade_count` <- `null` | `open/high/low/close` <- `open/high/low/close`; `volume_base` <- `volume`; `volume_quote` <- `null`; `trade_count` <- `null` | `open/high/low/close` <- `[3]/[2]/[1]/[4]`; `volume_base` <- `[5]`; `volume_quote` <- `null`; `trade_count` <- `null` |
| 정규 시간 매핑 | `open_time_ms` <- `candle_date_time_utc` 파싱; `close_time_ms` <- `open_time_ms + interval_ms - 1` (`mon`은 UTC 달력 월 증가 후 1ms 차감) | 동일 (`timestamp` 필드는 KST 종료시각 참고용) | `open_time_ms` <- `timestamp`; `close_time_ms` <- `open_time_ms + interval_ms - 1` (`mon`은 UTC 달력 월 증가 후 1ms 차감) | `open_time_ms` <- `timestamp`(UTC 미명시 시 UTC 가정); `close_time_ms` 계산 | `open_time_ms` <- `[0]`(UTC 미명시 시 UTC 가정); `close_time_ms` 계산 |
| volume_quote 제공 여부 | 제공 (`candle_acc_trade_price`) | 제공 (`candle_acc_trade_price`) | 제공 (`quote_volume`) | 미제공 (`null`) | 미제공 (`null`) |
| 타임스탬프 단위 | ms. `candle_date_time_utc`: 캔들 구간 시작(UTC). `timestamp`: 해당 봉 마지막 틱 저장 시각(ms). | ms. `candle_date_time_utc`: 캔들 구간 시작(UTC). `candle_date_time_kst`: 캔들 구간 시작(KST). `timestamp`: 캔들 **종료** 시각(KST 기준) ms. | ms, **UTC**. 요청 `timestamp`·응답 `timestamp` 모두 Unix time ms. | ms. 문서상 "캔들 시작 시각(timestamp)". 시간대가 명시되지 않은 경우 UTC로 가정한다 (Assumed UTC unless documented otherwise). | ms. 문서상 "구간 시작 시간". 시간대가 명시되지 않은 경우 UTC로 가정한다 (Assumed UTC unless documented otherwise). |
| 거래대금(API 제공 여부) | 제공. `candle_acc_trade_price` (누적 거래 금액) | 제공. `candle_acc_trade_price` (누적 거래 금액) | 제공. `quote_volume` (해당 종목 원화 거래 금액) | 미제공. 정책에 따라 `close * volume` 사용. | 미제공. 정책에 따라 `close * volume` 사용. |
| 정렬 방향 | 최신순 (지정한 `to` 이전 캔들) | 최신순 (지정한 `to` 이전 캔들) | 최신순. `timestamp` 미지정 시 최근 캔들부터, 지정 시 해당 시각 이전 캔들. | 과거→최신 순(오름차순). `start`·`end` 미지정 시 상장 시점~현재. | 과거→최신 순. start~end 구간 내. |
| 429 대응 | [캔들 그룹] 내 초당 10회 제한. 429 시 재시도 전 대기 필요(문서상 대기 시간 미명시). | Public API 초당 150회. 초과 시 API 일시 제한. 재시도 전 대기(문서상 구체적 대기 시간 미명시). | V2 기준 1200/분(IP). 초과 시 `error_code: "4"`, `error_msg: "Blocked user access"`. 잔여 건수는 헤더 `Public-Ratelimit-Remaining`. **초과 후 대기 시간·Retry-After 미제공** — 다음 분 또는 헤더 확인 후 재시도. | Public API 50회/초(IP). 초과 시 429. 잔량·초기화 시간은 헤더 `Ratelimit`(remaining, limit, reset), `Ratelimit-Policy`. 재시도 시 reset 경과 후 또는 remaining 확인 후. | 공개 API IP당 20회/초(1초 구간). 잔량은 헤더 `x-gopax-ip-addr-used-weight`, `x-gopax-ip-addr-left-weight`. 초과 시 429. (캔들·거래쌍 목록은 예외 대상 아님) |

### 6.3 주기별 상세 (필요 시 복제)

- **캔들 1m**, **캔들 3m**, **캔들 5m**, **캔들 10m**, **캔들 15m**, **캔들 30m**, **캔들 1h**, **캔들 1d** 등 주기마다 위와 같은 표를 두거나, 거래소별로 "주기 → 경로/params" 요약을 블록으로 채운다.

#### 업비트 캔들 상세

| 구분 | 분캔들 | 일캔들 |
|------|--------|--------|
| **URL** | `GET /v1/candles/minutes/{unit}` | `GET /v1/candles/days` |
| **Path param** | `unit`: 1, 3, 5, 10, 15, 30, 60, 240 (분) | — |
| **Query** | `market`(필수), `to`(선택, ISO 8601), `count`(선택, 기본 1, 최대 200) | 동일 + `converting_price_unit`(선택, 예: KRW → 원화 환산 종가 `converted_trade_price` 반환) |
| **응답** | 배열. 각 봉: `market`, `candle_date_time_utc`, `candle_date_time_kst`, `opening_price`, `high_price`, `low_price`, `trade_price`, `timestamp`(ms), `candle_acc_trade_price`, `candle_acc_trade_volume`, `unit` | 위와 동일 + `prev_closing_price`, `change_price`, `change_rate`, (선택)`converted_trade_price` |
| **비고** | 해당 분/일 구간에 체결이 없으면 해당 봉 미생성(응답에 없음) | 동일. 일캔들은 UTC 0시 기준. |

#### 빗썸 캔들 상세

| 구분 | 분캔들 | 일캔들 |
|------|--------|--------|
| **URL** | `GET /v1/candles/minutes/{unit}` | `GET /v1/candles/days` |
| **Path param** | `unit`: 1, 3, 5, 10, 15, 30, 60, 240 (분) | — |
| **Query** | `market`(필수), `to`(선택, KST 기준 ISO 8601), `count`(선택, 기본 1, 최대 200) | 동일 + `convertingPriceUnit`(선택, KRW 시 원화 환산 종가 `converted_trade_price` 반환) |
| **응답** | 배열. 각 봉: 업비트와 동일 필드. `timestamp`는 캔들 종료 시각(KST) ms. | 위와 동일 + `prev_closing_price`, `change_price`, `change_rate`, (선택)`converted_trade_price` |
| **비고** | `to` 기본 KST. 정규 시간은 `open_time_ms` 기준이므로 `candle_date_time_utc` 파싱 사용 권장. | 일캔들 UTC 0시 기준. |

#### 코인원 캔들 상세

| 구분 | 내용 |
|------|------|
| **URL** | `GET /public/v2/chart/{quote_currency}/{target_currency}` (모든 주기 공통) |
| **Path param** | `quote_currency`: 마켓 기준 통화(예: KRW). `target_currency`: 종목 심볼(예: BTC). 정규 심볼 BTC-KRW → `/chart/KRW/BTC` |
| **Query** | `interval`(필수): 1m, 3m, 5m, 10m, 15m, 30m, 1h, 2h, 4h, 6h, 1d, 1w, 1mon. `timestamp`(선택, UTC ms): 마지막 캔들 타임스탬프. `size`(선택, 1~500, 기본 200) |
| **응답** | 루트 객체. `result`, `error_code`, `is_last`, `chart`(배열). 각 봉: `timestamp`, `open`, `high`, `low`, `close`, `target_volume`, `quote_volume` |
| **비고** | timestamp·요청 모두 UTC ms. `is_last === true`면 해당 구간 마지막. 107 에러 시 `interval` 누락. |

#### 코빗 캔들 상세

| 구분 | 내용 |
|------|------|
| **URL** | `GET /v2/candles` (모든 주기 공통) |
| **Query** | `symbol`(필수, 예: btc_krw). `interval`(필수): 1, 5, 15, 30, 60, 240, 1D, 1W. `start`(선택, ms): 조회 시작 시각. 미지정 시 상장 시점부터. `end`(선택, ms): 조회 종료 시각(start보다 커야 함). 미지정 시 현재까지. `limit`(필수, 1~200): 조회 건수. |
| **응답** | 루트 객체. `success`, `data`(배열). 각 봉: `timestamp`, `open`, `high`, `low`, `close`, `volume`. 거래대금 미제공. |
| **비고** | 응답은 과거→최신 순(오름차순). 정규 시간은 `open_time_ms`(UTC 가정) 기준으로 매핑하고 `close_time_ms`를 파생 계산. `volume_quote`는 미제공(`null`). |

#### 고팩스 캔들 상세

| 구분 | 내용 |
|------|------|
| **URL** | `GET /trading-pairs/{TradingPair}/candles` (path에 심볼 예: BTC-KRW) |
| **Query** | `start`(필수, ms): 시작 시각. `end`(필수, ms): 종료 시각. `interval`(필수): 1, 5, 30, 1440(분). `limit`(선택, 기본 1024, 최대 1024) |
| **응답** | 루트가 배열. 각 봉은 **배열 6개**: `[timestamp(구간 시작 ms), low, high, open, close, volume]`. volume은 base 자산 단위. 거래대금 미제공. |
| **비고** | 응답 봉 순서가 low→high→open→close 이므로 인덱스 [1]low, [2]high, [3]open, [4]close, [5]volume 매핑 필요. `volume_quote`는 미제공(`null`). |

---

## 7. 예외 · 제한

- **업비트**: 초당 최대 10회 호출(IP 단위). [마켓 그룹]·[캔들 그룹] 각각 내에서 요청 횟수 공유. 캔들 API는 [캔들 그룹] 제한 적용. 429 시 재시도 전 대기 필요(문서상 구체적 대기 시간 미명시).
- **빗썸**: Public API **초당 최대 150회**. 초과 시 API 사용 일시 제한(429 등). 문서상 제한 해제 대기 시간은 확인 필요.
- **코인원**: Public API **V2** 분당 최대 **1200회**(요청 IP 기준). V1은 분당 600회(IP 기준). 가이드에서 사용하는 마켓·캔들 API는 V2(`/public/v2/`)이므로 **1200/분** 적용. 요청 제한 초과 시 응답 body에 `result: "error"`, `error_code: "4"`, `error_msg: "Blocked user access"` 반환. 잔여 요청 건수는 응답 헤더 **`Public-Ratelimit-Remaining`**(1분 기준, 잔여 가능할 때만 포함)으로 확인 가능. **초과 후 구체적 대기 시간·Retry-After는 문서에 없음** — 재시도 시 다음 분(또는 헤더로 잔여 건수 확인 후) 대기하는 방식 권장.
- **코빗**: Public API **초당 50회**(IP 기준). 초과 시 429 Too Many Requests. 제한 초과로 인한 불이익은 제한 해제될 때까지 정상 응답을 받지 못하는 것뿐. 잔여 요청 수는 응답 헤더 **`Ratelimit`**의 `remaining`(남은 횟수), `limit`(최대), `reset`(초기화까지 남은 초). **`Ratelimit-Policy`** 헤더에 정책(최대 횟수; 시간 윈도우 초) 표시. (Private API는 회원 계정 기준 별도 제한: 주문 30/초, 취소 30/초, 입출금 5/초, 그 외 50/초)
- **고팩스**: 공개 API는 **IP당** 최근 1초 구간 기준 기본 **최대 20회**. (예외: FOK 주문·GET /trades?deepSearch=false → 2회/초, GET /trading-pairs/…/book·GET /trades?deepSearch=true → 1회/초. 가이드에서 쓰는 `/trading-pairs`, `/trading-pairs/{TradingPair}/candles`는 **20회/초** 적용.) 응답 헤더로 잔량 확인: **`x-gopax-ip-addr-used-weight`**, **`x-gopax-ip-addr-left-weight`** (공개 API), `x-gopax-api-key-used-weight`, `x-gopax-api-key-left-weight`(개인 API). 초과 시 **429** 반환.

---

## 8. URL 하나씩 채우는 방법

- **입력**: `거래소 / 기능 / GET URL` (+ params·가능 값·응답 형식·샘플 중 아는 만큼).
- **기능**: 페어 목록, 캔들 1m, 캔들 1h, 캔들 1d 등.
- **출력**: 이 문서의 해당 표 셀에 "params 무엇을 쓰는지, 어떤 값이 가능한지, 응답이 어떤 형식인지"를 정리해 반영. 페어 목록인 경우 **거래소별 심볼 → 정규 형식 변환 규칙** 표의 해당 행도 함께 채움.
