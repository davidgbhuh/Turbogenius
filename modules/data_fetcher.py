"""Fetch stock price and company info.

Primary source: FinanceDataReader (KRX) — works reliably on cloud servers.
Fallback: yfinance for company metadata.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from config import TICKER_SUFFIX

try:
    import FinanceDataReader as fdr
    _FDR_AVAILABLE = True
except ImportError:
    _FDR_AVAILABLE = False


def _period_to_dates(period: str) -> tuple[str, str]:
    """Convert yfinance period string to (start, end) date strings."""
    end = datetime.today()
    mapping = {
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "2y": 730,
        "5y": 1825,
    }
    days = mapping.get(period, 365)
    start = end - timedelta(days=days)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _fetch_fdr(ticker: str, period: str) -> pd.DataFrame:
    """Fetch OHLCV via FinanceDataReader (KRX)."""
    start, end = _period_to_dates(period)
    df = fdr.DataReader(ticker, start, end)
    if df.empty:
        return pd.DataFrame()
    # Normalize column names
    rename = {}
    for col in df.columns:
        col_lower = col.lower()
        if col_lower == "open":
            rename[col] = "Open"
        elif col_lower == "high":
            rename[col] = "High"
        elif col_lower == "low":
            rename[col] = "Low"
        elif col_lower in ("close", "adj close"):
            rename[col] = "Close"
        elif col_lower == "volume":
            rename[col] = "Volume"
    df = df.rename(columns=rename)
    needed = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    if "Close" not in needed:
        return pd.DataFrame()
    df = df[needed].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df.dropna(subset=["Close"])


def _fetch_yfinance(ticker: str, market: str, period: str) -> pd.DataFrame:
    """Fetch OHLCV via yfinance as fallback."""
    suffix = TICKER_SUFFIX.get(market, ".KS")
    yt = yf.Ticker(f"{ticker}{suffix}")
    df = yt.history(period=period)
    if df.empty:
        return pd.DataFrame()
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


@st.cache_data(ttl=300)
def fetch_ohlcv(ticker: str, market: str, period: str) -> pd.DataFrame:
    """Return OHLCV DataFrame for the given ticker and period.

    Tries FinanceDataReader first (reliable on cloud), falls back to yfinance.

    Args:
        ticker: KRX 6-digit ticker code.
        market: 'KOSPI' or 'KOSDAQ'.
        period: yfinance period string (e.g. '1mo', '1y').

    Returns:
        DataFrame with columns [Open, High, Low, Close, Volume].
        Returns empty DataFrame on failure.
    """
    if _FDR_AVAILABLE:
        try:
            df = _fetch_fdr(ticker, period)
            if not df.empty:
                return df
        except Exception:
            pass

    try:
        return _fetch_yfinance(ticker, market, period)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def get_company_info(ticker: str, market: str) -> dict:
    """Return basic company info dict from yfinance.

    Keys include: name, sector, industry, market_cap, per, pbr,
    dividend_yield, description.
    """
    try:
        suffix = TICKER_SUFFIX.get(market, ".KS")
        yt = yf.Ticker(f"{ticker}{suffix}")
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
