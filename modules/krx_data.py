"""KRX 공공 데이터 API를 통한 ETF 전종목 조회."""

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


def _prev_trading_day(date: datetime, offset: int = 0) -> str:
    """date에서 offset 영업일 전 날짜를 YYYYMMDD 문자열로 반환."""
    d = date - timedelta(days=offset)
    # 주말 건너뜀
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")


def _fetch_raw(trd_dd: str) -> list[dict] | None:
    """KRX에서 ETF 전종목 JSON을 가져온다."""
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
        return body.get("OutBlock_1") or body.get("output") or None
    except Exception:
        return None


@st.cache_data(ttl=3600)
def fetch_etf_list() -> pd.DataFrame:
    """KRX ETF 전종목 리스트를 반환합니다.

    Returns:
        DataFrame with columns:
            code      - 6자리 종목코드
            name      - ETF 약칭
            price     - 당일 종가 (KRW, float)
            change    - 전일 대비 등락률 (%)
            volume    - 거래량
            mktcap    - 시가총액 (억원)
    """
    now = datetime.now()
    rows = None
    for offset in range(5):  # 최대 5 영업일 이전까지 시도
        trd_dd = _prev_trading_day(now, offset)
        rows = _fetch_raw(trd_dd)
        if rows:
            break

    if not rows:
        return pd.DataFrame(columns=["code", "name", "price", "change", "volume", "mktcap"])

    records = []
    for r in rows:
        try:
            price = float(str(r.get("TDD_CLSPRC", "0")).replace(",", "") or 0)
            change = float(str(r.get("FLUC_RT", "0")).replace(",", "") or 0)
            volume = int(str(r.get("ACC_TRDVOL", "0")).replace(",", "") or 0)
            mktcap_raw = str(r.get("MKTCAP", "0")).replace(",", "")
            mktcap = round(float(mktcap_raw or 0) / 1e8, 1)  # 원 → 억원
        except (ValueError, TypeError):
            price = change = volume = mktcap = 0

        records.append({
            "code":   r.get("ISU_SRT_CD", ""),
            "name":   r.get("ISU_ABBRV", ""),
            "price":  price,
            "change": change,
            "volume": volume,
            "mktcap": mktcap,
        })

    df = pd.DataFrame(records)
    df = df[df["code"].str.match(r"^\d{6}$", na=False)]
    return df.reset_index(drop=True)


def get_name_map() -> dict[str, str]:
    """종목코드 → ETF 이름 딕셔너리를 반환합니다."""
    df = fetch_etf_list()
    if df.empty:
        return {}
    return dict(zip(df["code"], df["name"]))


def get_price_map() -> dict[str, float]:
    """종목코드 → 당일 종가 딕셔너리를 반환합니다."""
    df = fetch_etf_list()
    if df.empty:
        return {}
    return {row["code"]: row["price"] for _, row in df.iterrows() if row["price"] > 0}
