** 국내 거래소 Public API 표준화 설계 노트
internal-design-notes-korean-exchanges

> This document contains detailed implementation notes and validation records created during the normalization design process.

**목적**: 업비트·빗썸·코인원·코빗·고팍스의 **Public API(페어 목록·캔들)** 를 하나의 **정규 스키마**로 통일해, 어떤 거래소든 동일한 심볼 형식·캔들 필드로 사용할 수 있게 하기 위함.


---

## 1. 무엇을 위해 어떻게 했는지

| 단계 | 내용 |
|------|------|
| **정규 스키마 정의** | 심볼 `{BASE}-{QUOTE}`(예: BTC-KRW), 캔들 필드 `timestamp`(ms)·open·high·low·close·volume·trade_value, timestamp UTC ms로 통일. |
| **가이드 문서 작성** | 5거래소별로 **페어 목록 API·캔들 API·심볼 변환 규칙·Base URL·Rate limit**을 표와 블록으로 정리. |


거래소마다 URL·params·응답 형식이 다르므로, 가이드에는 **정규 형식으로 쓰기 위한 변환 규칙**과 **주기별 엔드포인트·한 봉 구조·페이징·429 대응**을 모두 적어 두었습니다.

---

## 2. 어디까지 완료됐는지

### 2.1 가이드 문서

- **§1 사용자 결정 사항**: 정규 심볼·trade_value·timestamp·지원 주기 범위 확정.
- **§2 거래소별 심볼 → 정규 형식 변환**: 5거래소 모두 채움 (API 반환 예시 + 변환 규칙).
- **§4 Base URL·심볼 형식 비교**: 5거래소 Base URL, 마켓 목록 반환 형식, 캔들 요청 시 심볼 형식 채움.
- **§5 페어 목록 API**: 5거래소 Method+경로, params, 응답 경로, 심볼 추출, 필터(KRW 등), 성공 판별 채움.
- **§6.1 지원 주기 요약**: 5거래소 지원 주기(1m~1d 등) 및 비고 채움.
- **§6.2 캔들 공통 항목**: 5거래소 Method+경로, 심볼 넣는 곳, 시간 params, 페이징, 최대/구간, 응답 경로, 한 봉 구조, 정규 매핑, 타임스탬프·거래대금·정렬·429 대응 채움.
- **§6.3 주기별 상세**: 업비트·빗썸·코인원·코빗·고팍스 각각 캔들 상세 블록 추가됨.
- **§7 예외·제한**: 5거래소 Rate limit·429·잔량 헤더 등 모두 채움. **(채우기) 없음.**

### 2.2 검증 스크립트

- **대상**: 5거래소 전체. 제목은 "국내 5거래소 API 검증".
- **검사 항목** (총 12개):
  - 업비트: 마켓 목록, 분봉(1m), 일봉
  - 빗썸: 마켓 목록, 분봉(1m), 일봉
  - 코인원: 마켓 목록(KRW), 캔들(1m, KRW/BTC)
  - 코빗: 거래쌍 목록(currencyPairs), 캔들(1m, btc_krw)
  - 고팍스: 거래쌍 목록(trading-pairs), 캔들(1m, BTC-KRW, start/end/interval=1)


---

## 3. 거래소별 요약 (가이드·검증 기준)

| 거래소 | 페어 목록 | 캔들 | Rate limit | 검증 |
|--------|-----------|------|------------|------|
| **업비트** | GET /v1/market/all, market(QUOTE-BASE) | 분/일캔들, to·count, candle_acc_trade_price | 10회/초(IP) | 마켓·분봉·일봉 통과 |
| **빗썸** | GET /v1/market/all, 동일 형식 | to(KST), candle_acc_trade_price | 150회/초(IP) | 마켓·분봉·일봉 통과 |
| **코인원** | GET /public/v2/markets/KRW, markets[]·target_currency·quote_currency | GET /public/v2/chart/KRW/BTC, interval·size, chart[]·quote_volume | 1200회/분(IP), error_code 4, Public-Ratelimit-Remaining | 마켓·캔들(1m) 통과 |
| **코빗** | GET /v2/currencyPairs, data[]·symbol(btc_krw) | GET /v2/candles, symbol·interval·start·end·limit, data[] | 50회/초(IP), Ratelimit 헤더 | 마켓·캔들(1m) 통과 |
| **고팍스** | GET /trading-pairs, name(BASE-QUOTE) | GET /trading-pairs/BTC-KRW/candles, start·end·interval·limit, 배열의 배열 [ts,low,high,open,close,vol] | 20회/초(IP), x-gopax-ip-addr-* 헤더 | 마켓·캔들(1m) 통과 |
