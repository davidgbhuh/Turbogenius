"""KRX 공공 데이터 API를 통한 ETF 전종목 조회 및 기간별 수익률 계산."""

from datetime import datetime, timedelta
import requests
import pandas as pd
import streamlit as st

_API_URL = "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
_HEADERS = {
    "Referer": "https://data.krx.co.kr/contents/MDC/MDI/mdiBoardDetail/index.cmd?menuId=MDC0201020506",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}

# 기간별 영업일 오프셋 (주말·한국 공휴일 미반영, 근사값)
_PERIOD_DAYS = {"1W": 5, "1M": 22, "3M": 66, "1Y": 252}


def _nearest_trading_date(base: datetime, cal_days_back: int = 0) -> str:
    """base에서 cal_days_back 달력일 이전의 가장 가까운 평일을 YYYYMMDD로 반환."""
    d = base - timedelta(days=cal_days_back)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")


def _fetch_raw(trd_dd: str) -> list[dict] | None:
    """KRX에서 해당 날짜 ETF 전종목 JSON을 가져온다.

    KRX 데이터가 없는 날짜(공휴일 등)이면 None 반환.
    """
    payload = {
        "bld": "dbms/MDC/STAT/standard/MDCSTAT04301",
        "locale": "ko_KR",
        "trdDd": trd_dd,
        "share": "1",
        "money": "1",
        "csvxls_isNo": "false",
    }
    try:
        resp = requests.post(_API_URL, headers=_HEADERS, data=payload, timeout=10)
        if resp.status_code != 200:
            return None
        body = resp.json()
        rows = body.get("OutBlock_1") or body.get("output") or []
        return rows if rows else None
    except Exception:
        return None


def _fetch_with_retry(target: datetime, max_back: int = 7) -> tuple[list[dict], str] | tuple[None, None]:
    """target 날짜부터 최대 max_back 달력일 이전까지 재시도하여 데이터를 가져온다.

    Returns:
        (rows, actual_date_str) or (None, None)
    """
    for back in range(max_back + 1):
        d = target - timedelta(days=back)
        if d.weekday() >= 5:
            continue
        dd = d.strftime("%Y%m%d")
        rows = _fetch_raw(dd)
        if rows:
            return rows, dd
    return None, None


def _parse_price(raw: dict) -> float:
    try:
        return float(str(raw.get("TDD_CLSPRC", "0")).replace(",", "") or 0)
    except (ValueError, TypeError):
        return 0.0


def _rows_to_price_map(rows: list[dict]) -> dict[str, float]:
    """KRX rows → {code: price} 딕셔너리."""
    result = {}
    for r in rows:
        code = r.get("ISU_SRT_CD", "")
        if not (code and len(code) == 6 and code.isdigit()):
            continue
        price = _parse_price(r)
        if price > 0:
            result[code] = price
    return result


@st.cache_data(ttl=3600)
def fetch_etf_list() -> pd.DataFrame:
    """KRX ETF 전종목 리스트(당일 기준)를 반환합니다.

    Returns:
        DataFrame — columns: code, name, price, change, volume, mktcap(억원)
    """
    rows, _ = _fetch_with_retry(datetime.now())
    if not rows:
        return pd.DataFrame(columns=["code", "name", "price", "change", "volume", "mktcap"])

    records = []
    for r in rows:
        code = r.get("ISU_SRT_CD", "")
        if not (code and len(code) == 6 and code.isdigit()):
            continue
        try:
            price  = float(str(r.get("TDD_CLSPRC", "0")).replace(",", "") or 0)
            change = float(str(r.get("FLUC_RT", "0")).replace(",", "") or 0)
            volume = int(str(r.get("ACC_TRDVOL", "0")).replace(",", "") or 0)
            mktcap = round(float(str(r.get("MKTCAP", "0")).replace(",", "") or 0) / 1e8, 1)
        except (ValueError, TypeError):
            price = change = volume = mktcap = 0

        records.append({
            "code":   code,
            "name":   r.get("ISU_ABBRV", ""),
            "price":  price,
            "change": change,
            "volume": volume,
            "mktcap": mktcap,
        })

    return pd.DataFrame(records)


@st.cache_data(ttl=3600)
def fetch_etf_performance_krx(codes: tuple[str, ...]) -> pd.DataFrame:
    """KRX API로 ETF 기간별 수익률을 계산합니다.

    오늘/1주전/1개월전/3개월전/1년전 날짜의 종가 스냅샷을 각각 가져와
    수익률을 계산합니다 (총 최대 5회 API 호출).

    Args:
        codes: 6자리 종목코드 튜플.

    Returns:
        DataFrame — columns: Ticker, Price, 1W (%), 1M (%), 3M (%), 1Y (%)
    """
    now = datetime.now()

    # 각 기간별 날짜 설정 (달력일 기준 → KRX는 자동 재시도로 영업일 맞춤)
    period_cal_days = {"1W": 7, "1M": 31, "3M": 92, "1Y": 365}

    # 현재 스냅샷
    today_rows, _ = _fetch_with_retry(now)
    today_map = _rows_to_price_map(today_rows) if today_rows else {}

    # 과거 스냅샷
    past_maps: dict[str, dict[str, float]] = {}
    for label, cal_days in period_cal_days.items():
        target = now - timedelta(days=cal_days)
        past_rows, _ = _fetch_with_retry(target)
        past_maps[label] = _rows_to_price_map(past_rows) if past_rows else {}

    results = []
    for code in codes:
        current = today_map.get(code)

        def ret(label: str) -> float | None:
            if current is None:
                return None
            base = past_maps[label].get(code)
            if not base:
                return None
            return round((current / base - 1) * 100, 2)

        results.append({
            "Ticker":  code,
            "Price":   current,
            "1W (%)":  ret("1W"),
            "1M (%)":  ret("1M"),
            "3M (%)":  ret("3M"),
            "1Y (%)":  ret("1Y"),
        })

    return pd.DataFrame(results)


def get_name_map() -> dict[str, str]:
    """종목코드 → ETF 공식 이름 딕셔너리."""
    df = fetch_etf_list()
    if df.empty:
        return {}
    return dict(zip(df["code"], df["name"]))


def get_price_map() -> dict[str, float]:
    """종목코드 → 당일 종가 딕셔너리."""
    df = fetch_etf_list()
    if df.empty:
        return {}
    return {row["code"]: row["price"] for _, row in df.iterrows() if row["price"] > 0}
