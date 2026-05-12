"""한국 ETF 시세 및 퍼포먼스 데이터 조회.

현재가: KRX 공공 API (krx_data.py)
기간별 수익률: yfinance (KRX 데이터 없는 경우 fallback)
"""

import streamlit as st
import yfinance as yf
import pandas as pd

from modules.krx_data import get_price_map


def _to_yf_ticker(ticker: str) -> str:
    """KRX 6자리 코드를 yfinance 티커로 변환 (예: 069500 → 069500.KS)."""
    ticker = ticker.strip()
    if "." not in ticker and ticker.isdigit():
        return f"{ticker}.KS"
    return ticker


def _fetch_yf_close(yf_tickers: list[str]) -> pd.DataFrame:
    """yfinance로 1년치 종가 데이터를 가져온다. 실패 시 빈 DataFrame."""
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
        # 단일 티커
        return raw[["Close"]].rename(columns={"Close": yf_tickers[0]})
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=1800)
def fetch_etf_performance(tickers: tuple) -> pd.DataFrame:
    """KRX ETF 티커 목록의 현재가 및 기간별 수익률을 반환합니다.

    현재가: KRX API 우선, 없으면 yfinance 최신가.
    수익률(1W/1M/3M/1Y): yfinance 일별 종가 기반.

    Args:
        tickers: ETF 티커 튜플 (6자리 코드).

    Returns:
        DataFrame — 컬럼: Ticker, Price, 1W (%), 1M (%), 3M (%), 1Y (%)
    """
    if not tickers:
        return pd.DataFrame()

    # KRX 현재가
    krx_prices = get_price_map()

    # yfinance 수익률 계산
    yf_tickers = [_to_yf_ticker(t) for t in tickers]
    close = _fetch_yf_close(yf_tickers)

    results = []
    for orig, yf_t in zip(tickers, yf_tickers):
        # 현재가: KRX 우선
        krx_price = krx_prices.get(orig)

        if not close.empty and yf_t in close.columns:
            prices = close[yf_t].dropna()
        else:
            prices = pd.Series(dtype=float)

        # yfinance 현재가 (KRX 없을 때 fallback)
        yf_price = float(prices.iloc[-1]) if not prices.empty else None
        current_price = krx_price if krx_price else yf_price

        def ret(n: int):
            if len(prices) >= n + 1:
                base = float(prices.iloc[-(n + 1)])
                last = float(prices.iloc[-1])
                return round((last / base - 1) * 100, 2) if base else None
            return None

        perf_1y = ret(252)
        if perf_1y is None and len(prices) >= 2:
            base = float(prices.iloc[0])
            last = float(prices.iloc[-1])
            perf_1y = round((last / base - 1) * 100, 2) if base else None

        results.append({
            "Ticker":  orig,
            "Price":   current_price,
            "1W (%)":  ret(5),
            "1M (%)":  ret(21),
            "3M (%)":  ret(63),
            "1Y (%)":  perf_1y,
        })

    return pd.DataFrame(results)


def _empty_row(ticker: str) -> dict:
    return {
        "Ticker": ticker, "Price": None,
        "1W (%)": None, "1M (%)": None,
        "3M (%)": None, "1Y (%)": None,
    }
