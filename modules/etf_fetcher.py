"""한국 ETF 시세 및 기간별 수익률 조회.

1순위: KRX 공공 API (krx_data.py) — 현재가 + 1W/1M/3M/1Y 수익률
2순위: yfinance — KRX 데이터 조회 실패 시 fallback
"""

import streamlit as st
import yfinance as yf
import pandas as pd

from modules.krx_data import fetch_etf_performance_krx


def _to_yf_ticker(ticker: str) -> str:
    ticker = ticker.strip()
    if "." not in ticker and ticker.isdigit():
        return f"{ticker}.KS"
    return ticker


def _fetch_yf_close(yf_tickers: list[str]) -> pd.DataFrame:
    try:
        raw = yf.download(
            yf_tickers,
            period="1y",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        if raw.empty:
            return pd.DataFrame()
        if isinstance(raw.columns, pd.MultiIndex):
            return raw["Close"]
        return raw[["Close"]].rename(columns={"Close": yf_tickers[0]})
    except Exception:
        return pd.DataFrame()


def _yf_performance(tickers: tuple) -> pd.DataFrame:
    """yfinance로 현재가 + 수익률 계산 (KRX 실패 시 fallback)."""
    yf_tickers = [_to_yf_ticker(t) for t in tickers]
    close = _fetch_yf_close(yf_tickers)

    results = []
    for orig, yf_t in zip(tickers, yf_tickers):
        if not close.empty and yf_t in close.columns:
            prices = close[yf_t].dropna()
        else:
            prices = pd.Series(dtype=float)

        current = float(prices.iloc[-1]) if not prices.empty else None

        def ret(n: int) -> float | None:
            if len(prices) >= n + 1:
                base = float(prices.iloc[-(n + 1)])
                last = float(prices.iloc[-1])
                return round((last / base - 1) * 100, 2) if base else None
            return None

        perf_1y = ret(252)
        if perf_1y is None and len(prices) >= 2:
            base, last = float(prices.iloc[0]), float(prices.iloc[-1])
            perf_1y = round((last / base - 1) * 100, 2) if base else None

        results.append({
            "Ticker":  orig,
            "Price":   current,
            "1W (%)":  ret(5),
            "1M (%)":  ret(21),
            "3M (%)":  ret(63),
            "1Y (%)":  perf_1y,
        })

    return pd.DataFrame(results)


@st.cache_data(ttl=1800)
def fetch_etf_performance(tickers: tuple) -> pd.DataFrame:
    """KRX ETF 티커 목록의 현재가 및 기간별 수익률을 반환합니다.

    KRX API 우선 사용. KRX에서 데이터를 가져오지 못한 종목은
    yfinance로 보완합니다.

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

    # KRX에서 현재가가 하나도 없으면 yfinance로 전환
    if krx_df.empty or krx_df["Price"].isna().all():
        return _yf_performance(tickers)

    # KRX에서 일부 종목만 누락된 경우: yfinance로 해당 종목 보완
    missing = krx_df[krx_df["Price"].isna()]["Ticker"].tolist()
    if missing:
        yf_df = _yf_performance(tuple(missing))
        if not yf_df.empty:
            yf_map = yf_df.set_index("Ticker").to_dict("index")
            for i, row in krx_df.iterrows():
                if row["Ticker"] in yf_map:
                    for col in ["Price", "1W (%)", "1M (%)", "3M (%)", "1Y (%)"]:
                        krx_df.at[i, col] = yf_map[row["Ticker"]].get(col)

    return krx_df
