"""Fetch ETF price and performance data via yfinance."""

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime


@st.cache_data(ttl=1800)
def fetch_etf_performance(tickers: tuple) -> pd.DataFrame:
    """Download 1-year OHLCV for *tickers* and compute performance returns.

    Args:
        tickers: Tuple of ETF ticker strings (tuple so it's hashable for cache).

    Returns:
        DataFrame with columns:
            Ticker, Price (USD), 1W (%), 1M (%), 3M (%), 1Y (%)
        Rows are in the same order as *tickers*.
        Missing values are NaN.
    """
    if not tickers:
        return pd.DataFrame()

    ticker_list = list(tickers)

    try:
        # Batch download — much faster than per-ticker calls
        raw = yf.download(
            ticker_list,
            period="1y",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception:
        return pd.DataFrame()

    if raw.empty:
        return pd.DataFrame()

    # yfinance returns MultiIndex columns when multiple tickers,
    # single-level when only one ticker.
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
    else:
        # Single ticker — wrap in a DataFrame with ticker as column name
        close = raw[["Close"]].rename(columns={"Close": ticker_list[0]})

    results = []
    for ticker in ticker_list:
        if ticker not in close.columns:
            results.append(_empty_row(ticker))
            continue

        prices = close[ticker].dropna()
        if prices.empty:
            results.append(_empty_row(ticker))
            continue

        current = float(prices.iloc[-1])

        def ret(n: int):
            if len(prices) >= n + 1:
                base = float(prices.iloc[-n - 1])
                return (current / base - 1) * 100 if base else None
            return None

        perf_1w = ret(5)
        perf_1m = ret(21)
        perf_3m = ret(63)
        perf_1y = ret(252)
        if perf_1y is None and len(prices) >= 2:
            base = float(prices.iloc[0])
            perf_1y = (current / base - 1) * 100 if base else None

        results.append({
            "Ticker": ticker,
            "Price": current,
            "1W (%)": round(perf_1w, 2) if perf_1w is not None else None,
            "1M (%)": round(perf_1m, 2) if perf_1m is not None else None,
            "3M (%)": round(perf_3m, 2) if perf_3m is not None else None,
            "1Y (%)": round(perf_1y, 2) if perf_1y is not None else None,
        })

    return pd.DataFrame(results)


def _empty_row(ticker: str) -> dict:
    return {"Ticker": ticker, "Price": None, "1W (%)": None,
            "1M (%)": None, "3M (%)": None, "1Y (%)": None}


@st.cache_data(ttl=3600)
def fetch_etf_names(tickers: tuple) -> dict:
    """Return {ticker: long_name} mapping using yfinance .info.

    Falls back to ticker string if info is unavailable.
    """
    names = {}
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            names[ticker] = (
                info.get("longName") or info.get("shortName") or ticker
            )
        except Exception:
            names[ticker] = ticker
    return names
