"""한국 ETF 시세 및 퍼포먼스 데이터 조회 (yfinance)."""

import streamlit as st
import yfinance as yf
import pandas as pd


def _to_yf_ticker(ticker: str) -> str:
    """KRX 6자리 코드를 yfinance 티커로 변환 (예: 069500 → 069500.KS)."""
    ticker = ticker.strip()
    if "." not in ticker and ticker.isdigit():
        return f"{ticker}.KS"
    return ticker


@st.cache_data(ttl=1800)
def fetch_etf_performance(tickers: tuple) -> pd.DataFrame:
    """KRX ETF 티커 목록의 현재가 및 기간별 수익률을 반환합니다.

    Args:
        tickers: ETF 티커 튜플 (6자리 코드, 예: ('069500', '379800')).

    Returns:
        DataFrame — 컬럼: Ticker, Name, Price (KRW), 1W (%), 1M (%), 3M (%), 1Y (%)
    """
    if not tickers:
        return pd.DataFrame()

    yf_tickers = [_to_yf_ticker(t) for t in tickers]

    try:
        raw = yf.download(
            yf_tickers,
            period="1y",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception:
        return pd.DataFrame()

    if raw.empty:
        return pd.DataFrame()

    # 단일 티커: 단순 DataFrame, 복수 티커: MultiIndex
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
    else:
        close = raw[["Close"]].rename(columns={"Close": yf_tickers[0]})

    results = []
    for orig, yf_t in zip(tickers, yf_tickers):
        if yf_t not in close.columns:
            results.append(_empty_row(orig))
            continue

        prices = close[yf_t].dropna()
        if prices.empty:
            results.append(_empty_row(orig))
            continue

        current = float(prices.iloc[-1])

        def ret(n: int):
            if len(prices) >= n + 1:
                base = float(prices.iloc[-(n + 1)])
                return round((current / base - 1) * 100, 2) if base else None
            return None

        perf_1y = ret(252)
        if perf_1y is None and len(prices) >= 2:
            base = float(prices.iloc[0])
            perf_1y = round((current / base - 1) * 100, 2) if base else None

        results.append({
            "Ticker": orig,
            "Price": current,
            "1W (%)": ret(5),
            "1M (%)": ret(21),
            "3M (%)": ret(63),
            "1Y (%)": perf_1y,
        })

    return pd.DataFrame(results)


def _empty_row(ticker: str) -> dict:
    return {
        "Ticker": ticker, "Price": None,
        "1W (%)": None, "1M (%)": None,
        "3M (%)": None, "1Y (%)": None,
    }
