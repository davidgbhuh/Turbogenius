"""Fetch stock price and company info via yfinance."""

import streamlit as st
import yfinance as yf
import pandas as pd
from config import TICKER_SUFFIX


def _yfin_ticker(ticker: str, market: str) -> yf.Ticker:
    suffix = TICKER_SUFFIX.get(market, ".KS")
    return yf.Ticker(f"{ticker}{suffix}")


@st.cache_data(ttl=300)
def fetch_ohlcv(ticker: str, market: str, period: str) -> pd.DataFrame:
    """Return OHLCV DataFrame for the given ticker and period.

    Args:
        ticker: KRX 6-digit ticker code.
        market: 'KOSPI' or 'KOSDAQ'.
        period: yfinance period string (e.g. '1mo', '1y').

    Returns:
        DataFrame with columns [Open, High, Low, Close, Volume].
        Returns empty DataFrame on failure.
    """
    try:
        yt = _yfin_ticker(ticker, market)
        df = yt.history(period=period)
        if df.empty:
            return pd.DataFrame()
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def get_company_info(ticker: str, market: str) -> dict:
    """Return basic company info dict from yfinance.

    Keys include: name, sector, industry, market_cap, per, pbr,
    dividend_yield, description.
    """
    try:
        yt = _yfin_ticker(ticker, market)
        info = yt.info
        return {
            "name": info.get("longName") or info.get("shortName", ticker),
            "sector": info.get("sector", "-"),
            "industry": info.get("industry", "-"),
            "market_cap": info.get("marketCap"),
            "per": info.get("trailingPE"),
            "pbr": info.get("priceToBook"),
            "dividend_yield": info.get("dividendYield"),
            "description": info.get("longBusinessSummary", ""),
            "website": info.get("website", ""),
            "employees": info.get("fullTimeEmployees"),
        }
    except Exception:
        return {"name": ticker}
