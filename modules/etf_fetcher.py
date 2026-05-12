"""한국 ETF 시세 및 기간별 수익률 조회.

1순위: KRX 공공 API (krx_data.py) — 전종목 일괄 스냅샷 (1W/1M/3M/1Y)
2순위: KIS OpenAPI (kis_api.py) — 종목별 일봉으로 누락분 보완
"""

import pandas as pd
import streamlit as st

from modules.krx_data import fetch_etf_performance_krx
from modules.kis_api import (
    get_current_price as kis_current_price,
    get_daily_prices as kis_daily_prices,
    is_configured as kis_is_configured,
)


def _kis_performance(tickers: tuple[str, ...]) -> pd.DataFrame:
    """KIS 일별 시세로 현재가 + 1W/1M/3M/1Y 수익률 계산."""
    results = []
    for t in tickers:
        info = kis_current_price(t)
        current = info.get("price") if info else None

        df = kis_daily_prices(t, period="D", count=260)
        if df.empty:
            results.append({
                "Ticker": t, "Price": current,
                "1W (%)": None, "1M (%)": None,
                "3M (%)": None, "1Y (%)": None,
            })
            continue

        closes = df["close"].dropna().tolist()
        if current is None and closes:
            current = closes[-1]

        def ret(n: int) -> float | None:
            if len(closes) >= n + 1 and closes[-(n + 1)] > 0:
                return round((closes[-1] / closes[-(n + 1)] - 1) * 100, 2)
            return None

        perf_1y = ret(252)
        if perf_1y is None and len(closes) >= 2 and closes[0] > 0:
            perf_1y = round((closes[-1] / closes[0] - 1) * 100, 2)

        results.append({
            "Ticker": t,
            "Price":  current,
            "1W (%)": ret(5),
            "1M (%)": ret(21),
            "3M (%)": ret(63),
            "1Y (%)": perf_1y,
        })

    return pd.DataFrame(results)


@st.cache_data(ttl=1800)
def fetch_etf_performance(tickers: tuple) -> pd.DataFrame:
    """KRX 종목코드 목록의 현재가 및 기간별 수익률을 반환합니다.

    1차: KRX API (전종목 스냅샷) → 빠르고 정확
    2차: KIS OpenAPI (개별 일봉)  → KRX 누락분 보완

    Args:
        tickers: 6자리 KRX 종목코드 튜플.

    Returns:
        DataFrame — Ticker, Price, 1W (%), 1M (%), 3M (%), 1Y (%)
    """
    if not tickers:
        return pd.DataFrame()

    # 1차: KRX API
    try:
        krx_df = fetch_etf_performance_krx(tickers)
    except Exception:
        krx_df = pd.DataFrame()

    # KRX 전체 실패 → KIS로 전환 (KIS 설정 시에만)
    if krx_df.empty or krx_df["Price"].isna().all():
        if kis_is_configured():
            return _kis_performance(tickers)
        return krx_df if not krx_df.empty else pd.DataFrame(
            [{"Ticker": t, "Price": None,
              "1W (%)": None, "1M (%)": None,
              "3M (%)": None, "1Y (%)": None} for t in tickers]
        )

    # KRX 일부 누락 → KIS로 보완
    missing = krx_df[krx_df["Price"].isna()]["Ticker"].tolist()
    if missing and kis_is_configured():
        kis_df = _kis_performance(tuple(missing))
        if not kis_df.empty:
            kis_map = kis_df.set_index("Ticker").to_dict("index")
            for i, row in krx_df.iterrows():
                if row["Ticker"] in kis_map:
                    for col in ["Price", "1W (%)", "1M (%)", "3M (%)", "1Y (%)"]:
                        krx_df.at[i, col] = kis_map[row["Ticker"]].get(col)

    return krx_df
